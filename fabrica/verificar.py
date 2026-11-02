"""`python -m fabrica verificar` — confere se tudo está pronto e diz o que falta."""
from __future__ import annotations

import shutil
import subprocess

from . import config

OK, FALTA, AVISO = "✅", "❌", "⚠️ "


def _linha(icone: str, titulo: str, dica: str = "") -> bool:
    print(f"{icone} {titulo}")
    if dica:
        print(f"     ↳ {dica}")
    return icone != FALTA


def rodar() -> int:
    cfg = config.carregar()
    tudo_ok = True
    print("\n🔎 Verificando a fábrica...\n")

    # ffmpeg
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        _linha(OK, "ffmpeg instalado")
    else:
        tudo_ok &= _linha(FALTA, "ffmpeg não encontrado",
                          "Windows: winget install ffmpeg | Mac: brew install ffmpeg | Linux: sudo apt install ffmpeg")

    # IA de texto
    prov = cfg.get_path("llm.provedor")
    if prov == "anthropic":
        if config.env("ANTHROPIC_API_KEY"):
            _linha(OK, "Chave da Anthropic configurada (roteiros com Claude)")
        else:
            tudo_ok &= _linha(FALTA, "Falta a ANTHROPIC_API_KEY no arquivo .env",
                              "Crie em https://console.anthropic.com/settings/keys  — ou use llm.provedor: \"claude_code\"")
    elif prov == "claude_code":
        if shutil.which("claude"):
            _linha(OK, "Claude Code encontrado (roteiros pela sua assinatura)")
        else:
            tudo_ok &= _linha(FALTA, "llm.provedor é claude_code mas o comando `claude` não existe",
                              "Instale o Claude Code ou troque para anthropic")
    else:
        _linha(AVISO, f"IA de texto em modo '{prov}' (roteiros de exemplo, não reais)")

    # Voz
    voz = cfg.get_path("voz.provedor")
    if voz == "elevenlabs" and not config.env("ELEVENLABS_API_KEY"):
        tudo_ok &= _linha(FALTA, "Falta ELEVENLABS_API_KEY no .env")
    elif voz == "elevenlabs" and not cfg.get_path("voz.elevenlabs_voice_id"):
        tudo_ok &= _linha(FALTA, "Falta voz.elevenlabs_voice_id no config.yaml")
    elif voz == "demo":
        _linha(AVISO, "Voz em modo demo (áudio mudo)")
    else:
        _linha(OK, f"Voz: {voz} ({cfg.get_path('voz.edge_voz') if voz == 'edge' else 'ElevenLabs'})")

    # Imagens
    img = cfg.get_path("imagens.provedor")
    if img == "openai" and not config.env("OPENAI_API_KEY"):
        tudo_ok &= _linha(FALTA, "Falta OPENAI_API_KEY no .env")
    elif img == "demo":
        _linha(AVISO, "Imagens em modo demo (fundos abstratos)")
    else:
        _linha(OK, f"Imagens: {img}")

    # YouTube
    modo = cfg.get_path("youtube.modo")
    secret = config.caminho(cfg.get_path("youtube.client_secret"))
    token = config.caminho(cfg.get_path("youtube.token"))
    if modo != "real":
        _linha(AVISO, "YouTube em modo SIMULADO (nada é enviado de verdade)",
               "Quando conectar o canal, troque youtube.modo para \"real\" no config.yaml")
    if not secret.exists():
        _linha(FALTA if modo == "real" else AVISO, f"Credencial do Google não encontrada em {secret}",
               "Siga a seção 'Conectar o YouTube' do README")
        tudo_ok &= modo != "real"
    elif not token.exists():
        _linha(FALTA if modo == "real" else AVISO, "Canal ainda não autorizado",
               "Rode: python -m fabrica youtube-login")
        tudo_ok &= modo != "real"
    else:
        try:
            from . import youtube

            youtube.servico()
            _linha(OK, "YouTube autorizado")
        except Exception as e:
            tudo_ok &= _linha(FALTA, f"Token do YouTube inválido: {e}", "Rode: python -m fabrica youtube-login")

    # Canal configurado?
    if cfg.get_path("canal.nome") == "Mistérios Sem Resposta":
        _linha(AVISO, "config.yaml ainda está com o canal de exemplo",
               "Edite canal.nome, canal.nicho, canal.publico e canal.tom")

    print()
    if tudo_ok:
        print("🚀 Tudo pronto! Rode: python -m fabrica painel")
    else:
        print("👆 Resolva os itens com ❌ e rode de novo: python -m fabrica verificar")
    return 0 if tudo_ok else 1

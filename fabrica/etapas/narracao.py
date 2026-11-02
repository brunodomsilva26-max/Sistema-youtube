"""Agente 3 — NARRAÇÃO: transforma cada bloco do roteiro em voz (TTS).

Provedores:
- edge        -> vozes neurais da Microsoft, grátis (pacote edge-tts)
- elevenlabs  -> vozes premium (ELEVENLABS_API_KEY)
- demo        -> áudio silencioso com a duração estimada (para testes)
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import requests

from .. import config, estado, midia


def falar(texto: str, saida: Path) -> float:
    """Gera um mp3 com o texto e devolve a duração em segundos."""
    cfg = config.carregar()
    prov = cfg.get_path("voz.provedor", "edge")
    saida.parent.mkdir(parents=True, exist_ok=True)
    if prov == "edge":
        _edge(texto, saida, cfg)
    elif prov == "elevenlabs":
        _elevenlabs(texto, saida, cfg)
    elif prov == "demo":
        dur = max(1.5, len(texto.split()) / 2.6)
        midia.ffmpeg("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{dur:.2f}",
                     "-c:a", "libmp3lame", "-b:a", "96k", str(saida))
    else:
        raise ValueError(f"Provedor de voz desconhecido: {prov}")
    return midia.duracao(saida)


def _edge(texto: str, saida: Path, cfg) -> None:
    import edge_tts

    async def _run():
        com = edge_tts.Communicate(
            texto,
            cfg.get_path("voz.edge_voz", "pt-BR-AntonioNeural"),
            rate=cfg.get_path("voz.edge_velocidade", "+0%"),
        )
        await com.save(str(saida))

    asyncio.run(_run())


def _elevenlabs(texto: str, saida: Path, cfg) -> None:
    chave = config.env("ELEVENLABS_API_KEY")
    voz = cfg.get_path("voz.elevenlabs_voice_id")
    if not chave or not voz:
        raise RuntimeError("Defina ELEVENLABS_API_KEY no .env e voz.elevenlabs_voice_id no config.yaml")
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voz}",
        headers={"xi-api-key": chave, "accept": "audio/mpeg"},
        json={
            "text": texto,
            "model_id": cfg.get_path("voz.elevenlabs_modelo", "eleven_multilingual_v2"),
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8},
        },
        timeout=180,
    )
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:300]}")
    saida.write_bytes(r.content)


def executar(p: estado.Projeto, feedback: str | None = None) -> None:
    blocos = p.roteiro["blocos"]
    duracoes, arquivos = [], []
    for i, b in enumerate(blocos):
        arq = p.arquivo(f"audio/bloco_{i:03}.mp3")
        duracoes.append(falar(b["narracao"], arq))
        arquivos.append(arq)
        p.set_etapa("narracao", "rodando", f"bloco {i + 1}/{len(blocos)}")
    midia.concatenar(arquivos, p.arquivo("audio/narracao.mp3"), recodificar_audio=True)
    p.dados["duracoes"] = duracoes
    p.salvar()

"""Agente 1 — PAUTA: sugere temas novos para o canal, sem repetir os anteriores."""
from __future__ import annotations

from .. import config, estado, llm

SCHEMA = {
    "type": "object",
    "properties": {
        "pautas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tema": {"type": "string", "description": "título de trabalho do vídeo"},
                    "angulo": {"type": "string", "description": "o recorte/gancho que torna o vídeo único"},
                    "por_que_funciona": {"type": "string"},
                },
                "required": ["tema", "angulo", "por_que_funciona"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["pautas"],
    "additionalProperties": False,
}


def sistema_canal() -> str:
    c = config.carregar()["canal"]
    return (
        f"Você é a equipe de conteúdo do canal de YouTube \"{c['nome']}\" (canal dark, sem rosto, "
        f"narrado por voz). Nicho: {c['nicho']}. Público: {c['publico']}. Idioma: {c['idioma']}. "
        f"Tom: {c['tom']}. Você domina retenção de audiência, títulos com alto CTR e storytelling."
    )


def gerar(quantidade: int = 5, criar_projetos: bool = True) -> list[dict]:
    anteriores = [p["tema"] for p in estado.listar()][:80]
    prompt = (
        f"Sugira {quantidade} pautas NOVAS de vídeos longos para o canal.\n"
        "Priorize temas com alta curiosidade, potencial de busca e que rendam bons Shorts.\n"
        "Evite repetir ou se aproximar demais destes temas já feitos:\n"
        + "\n".join(f"- {t}" for t in anteriores or ["(nenhum ainda)"])
    )
    dados = llm.gerar_json(sistema_canal(), prompt, SCHEMA, tarefa="pauta")
    pautas = dados["pautas"][:quantidade]
    if criar_projetos:
        for item in pautas:
            estado.criar(item["tema"], item.get("angulo", ""), origem="agente_pauta")
    return pautas

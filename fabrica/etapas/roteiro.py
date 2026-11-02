"""Agente 2 — ROTEIRO: escreve o roteiro em blocos (narração + descrição de cena),
título, descrição, tags, conceito da thumbnail e os roteiros dos Shorts.

Também cuida das revisões pedidas por você no painel.
"""
from __future__ import annotations

import json

from .. import config, estado, llm
from .pauta import sistema_canal

_FALA = {
    "type": "object",
    "properties": {
        "texto": {"type": "string"},
        "cena": {"type": "integer", "description": "índice (0-based) do bloco do vídeo longo cuja imagem ilustra esta fala"},
    },
    "required": ["texto", "cena"],
    "additionalProperties": False,
}
_SHORT = {
    "type": "object",
    "properties": {
        "titulo": {"type": "string"},
        "descricao": {"type": "string"},
        "falas": {"type": "array", "items": _FALA},
    },
    "required": ["titulo", "descricao", "falas"],
    "additionalProperties": False,
}
_THUMB = {
    "type": "object",
    "properties": {
        "texto": {"type": "string", "description": "2 a 4 palavras, MAIÚSCULAS, chocantes"},
        "destaque": {"type": "string", "description": "a palavra do texto que fica em amarelo"},
        "prompt": {"type": "string", "description": "prompt em inglês da imagem de fundo"},
    },
    "required": ["texto", "destaque", "prompt"],
    "additionalProperties": False,
}
_BLOCO = {
    "type": "object",
    "properties": {
        "narracao": {"type": "string", "description": "texto falado, 2 a 4 frases"},
        "cena": {"type": "string", "description": "prompt em inglês da imagem que ilustra o bloco"},
    },
    "required": ["narracao", "cena"],
    "additionalProperties": False,
}
SCHEMA = {
    "type": "object",
    "properties": {
        "titulo": {"type": "string"},
        "descricao": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "blocos": {"type": "array", "items": _BLOCO},
        "thumbnail": _THUMB,
        "shorts": {"type": "array", "items": _SHORT},
    },
    "required": ["titulo", "descricao", "tags", "blocos", "thumbnail", "shorts"],
    "additionalProperties": False,
}


def _regras() -> str:
    c = config.carregar()["canal"]
    palavras = int(c.get("duracao_minutos", 8) * 150)
    return f"""Regras do roteiro:
- Cerca de {palavras} palavras de narração no total (≈{c.get('duracao_minutos', 8)} min).
- Divida em blocos de 25 a 45 palavras; cada bloco vira UMA imagem na tela.
- O campo "cena" de cada bloco é um prompt de imagem em INGLÊS, visual e concreto
  (sem texto escrito na imagem, sem rostos de pessoas reais famosas, sem violência gráfica).
- Título com alto CTR (até 70 caracteres), sem clickbait mentiroso.
- Descrição com 2 parágrafos + 3 hashtags; tags: 10 a 15.
- Thumbnail: texto de 2 a 4 palavras + palavra de destaque + prompt de imagem em inglês.
- {c.get('quantidade_shorts', 3)} Shorts de 35 a 55 segundos (90 a 130 palavras cada), cada um
  com gancho na primeira frase e reaproveitando imagens do vídeo (campo "cena" = índice do bloco).
- Fatos devem ser verdadeiros; quando algo for teoria ou lenda, diga que é.
{c.get('instrucoes_extras', '')}"""


def gerar(p: estado.Projeto, feedback: str | None = None) -> dict:
    if feedback and p.roteiro:
        prompt = (
            f"Este é o roteiro atual do vídeo:\n{json.dumps(p.roteiro, ensure_ascii=False)}\n\n"
            f"O dono do canal pediu esta alteração:\n\"{feedback}\"\n\n"
            "Reescreva o roteiro completo aplicando a alteração, mantendo o que não foi criticado.\n\n"
            + _regras()
        )
    else:
        prompt = f"Escreva o roteiro completo do vídeo.\nTema: {p['tema']}\n"
        if p.get("angulo"):
            prompt += f"Ângulo: {p['angulo']}\n"
        prompt += "\n" + _regras()
    r = llm.gerar_json(sistema_canal(), prompt, SCHEMA, tarefa="roteiro")
    _validar(r)
    p.dados["roteiro"] = r
    p.salvar()
    return r


def _validar(r: dict) -> None:
    n = len(r["blocos"])
    if n == 0:
        raise ValueError("Roteiro sem blocos")
    for s in r["shorts"]:
        for f in s["falas"]:
            f["cena"] = max(0, min(n - 1, int(f["cena"])))


# ------------------------------------------------------------ revisões parciais
def revisar_parte(p: estado.Projeto, parte: str, feedback: str) -> None:
    """Reescreve só a parte do roteiro ligada à etapa (cenas, shorts ou thumbnail)."""
    r = p.roteiro
    if parte == "thumbnail":
        schema, atual = _THUMB, r["thumbnail"]
    elif parte == "shorts":
        schema = {
            "type": "object",
            "properties": {"shorts": {"type": "array", "items": _SHORT}},
            "required": ["shorts"],
            "additionalProperties": False,
        }
        atual = {"shorts": r["shorts"], "quantidade_blocos": len(r["blocos"])}
    elif parte == "cenas":
        schema = {
            "type": "object",
            "properties": {"cenas": {"type": "array", "items": {"type": "string"}}},
            "required": ["cenas"],
            "additionalProperties": False,
        }
        atual = {"cenas": [b["cena"] for b in r["blocos"]]}
    else:
        return
    prompt = (
        f"Roteiro do vídeo \"{r['titulo']}\".\nParte atual ({parte}):\n"
        f"{json.dumps(atual, ensure_ascii=False)}\n\n"
        f"Alteração pedida pelo dono do canal: \"{feedback}\"\n"
        f"Devolva a parte '{parte}' reescrita (mesmo formato, mesma quantidade de itens quando for lista de cenas)."
    )
    novo = llm.gerar_json(sistema_canal(), prompt, schema, tarefa=f"revisar_{parte}")
    if parte == "thumbnail":
        r["thumbnail"] = novo
    elif parte == "shorts":
        r["shorts"] = novo["shorts"]
        _validar(r)
    elif parte == "cenas":
        for b, c in zip(r["blocos"], novo["cenas"]):
            b["cena"] = c
    p.salvar()


CLASSIFICAR = {
    "type": "object",
    "properties": {
        "etapa": {"type": "string", "enum": estado.ETAPAS},
        "motivo": {"type": "string"},
    },
    "required": ["etapa", "motivo"],
    "additionalProperties": False,
}


def classificar_alteracao(feedback: str) -> str:
    """Descobre qual agente deve resolver o pedido de alteração."""
    prompt = (
        "O dono do canal revisou um vídeo e pediu esta alteração:\n"
        f"\"{feedback}\"\n\n"
        "Qual é a PRIMEIRA etapa da linha de produção que precisa ser refeita?\n"
        "- roteiro: texto falado, título, descrição, fatos, estrutura, tamanho\n"
        "- narracao: voz, ritmo, pronúncia (sem mudar o texto)\n"
        "- cenas: imagens do vídeo\n"
        "- montagem: legendas, transições, música, cortes\n"
        "- shorts: os vídeos curtos\n"
        "- thumbnail: a capa / miniatura"
    )
    try:
        return llm.gerar_json("Você roteia pedidos numa produtora de vídeo.", prompt, CLASSIFICAR, tarefa="classificar")["etapa"]
    except Exception:
        t = feedback.lower()
        for etapa, chaves in [
            ("thumbnail", ["thumb", "capa", "miniatura"]),
            ("shorts", ["short"]),
            ("cenas", ["imagem", "imagens", "cena", "visual"]),
            ("narracao", ["voz", "narra", "pronúncia", "pronuncia"]),
            ("montagem", ["legenda", "música", "musica", "transição", "corte"]),
        ]:
            if any(c in t for c in chaves):
                return etapa
        return "roteiro"

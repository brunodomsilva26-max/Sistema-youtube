"""Camada de IA de texto: gera JSON estruturado a partir de um prompt.

Provedores:
- anthropic   -> API oficial da Anthropic (precisa ANTHROPIC_API_KEY)
- claude_code -> usa o CLI `claude -p` (aproveita sua assinatura do Claude Code)
- demo        -> respostas prontas, para testar a fábrica sem gastar nada
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess

from . import config


class ErroLLM(RuntimeError):
    pass


def gerar_json(sistema: str, prompt: str, schema: dict, tarefa: str = "") -> dict:
    cfg = config.carregar()
    provedor = cfg.get_path("llm.provedor", "anthropic")
    if provedor == "anthropic":
        return _anthropic(sistema, prompt, schema)
    if provedor == "claude_code":
        return _claude_code(sistema, prompt, schema)
    if provedor == "demo":
        from . import demo

        return demo.resposta(tarefa, prompt)
    raise ErroLLM(f"Provedor de LLM desconhecido: {provedor}")


# ---------------------------------------------------------------- Anthropic
def _anthropic(sistema: str, prompt: str, schema: dict) -> dict:
    import anthropic

    cfg = config.carregar()
    client = anthropic.Anthropic()
    try:
        resp = client.beta.messages.create(
            model=cfg.get_path("llm.modelo", "claude-opus-5-5"),
            max_tokens=16000,
            system=sistema,
            messages=[{"role": "user", "content": prompt}],
            output_config={
                "effort": cfg.get_path("llm.esforco", "medium"),
                "format": {"type": "json_schema", "schema": schema},
            },
            # Se o modelo recusar por política, a API tenta outro modelo automaticamente
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError as e:
        raise ErroLLM("ANTHROPIC_API_KEY inválida ou ausente (veja o .env)") from e
    except anthropic.RateLimitError as e:
        raise ErroLLM("Limite de uso da API atingido; tente de novo em instantes") from e
    except anthropic.APIStatusError as e:
        raise ErroLLM(f"Erro da API Anthropic ({e.status_code}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise ErroLLM("Sem conexão com a API Anthropic") from e

    if resp.stop_reason == "refusal":
        raise ErroLLM("O modelo recusou este tema. Ajuste a pauta.")
    if resp.stop_reason == "max_tokens":
        raise ErroLLM("Resposta cortada por tamanho; reduza a duração do vídeo.")
    texto = next((b.text for b in resp.content if b.type == "text"), "")
    return json.loads(texto)


# ---------------------------------------------------------------- Claude Code CLI
def _claude_code(sistema: str, prompt: str, schema: dict) -> dict:
    if not shutil.which("claude"):
        raise ErroLLM("CLI `claude` não encontrado. Instale o Claude Code ou use provedor anthropic.")
    pedido = (
        f"{sistema}\n\n{prompt}\n\n"
        "Responda SOMENTE com um objeto JSON válido (sem markdown, sem comentários) "
        f"que siga exatamente este JSON Schema:\n{json.dumps(schema, ensure_ascii=False)}"
    )
    r = subprocess.run(
        ["claude", "-p", "--output-format", "json"],
        input=pedido,
        capture_output=True,
        text=True,
        timeout=900,
    )
    if r.returncode != 0:
        raise ErroLLM(f"claude -p falhou: {r.stderr.strip()[:500]}")
    try:
        texto = json.loads(r.stdout).get("result", "")
    except json.JSONDecodeError:
        texto = r.stdout
    return extrair_json(texto)


def extrair_json(texto: str) -> dict:
    texto = re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.M).strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        ini, fim = texto.find("{"), texto.rfind("}")
        if ini >= 0 and fim > ini:
            return json.loads(texto[ini : fim + 1])
        raise ErroLLM("A IA não devolveu JSON válido")

"""Carrega config.yaml + variáveis de ambiente (.env)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent

try:  # .env é opcional
    from dotenv import load_dotenv

    load_dotenv(RAIZ / ".env")
except ImportError:  # pragma: no cover
    pass


class Config(dict):
    """dict com acesso por caminho: cfg.get_path("voz.provedor")."""

    def get_path(self, caminho: str, padrao=None):
        atual = self
        for parte in caminho.split("."):
            if not isinstance(atual, dict) or parte not in atual:
                return padrao
            atual = atual[parte]
        return atual


@lru_cache(maxsize=1)
def carregar() -> Config:
    arquivo = Path(os.environ.get("FABRICA_CONFIG", RAIZ / "config.yaml"))
    with open(arquivo, encoding="utf-8") as f:
        dados = yaml.safe_load(f) or {}
    return Config(dados)


def env(nome: str, padrao: str | None = None) -> str | None:
    return os.environ.get(nome, padrao)


def caminho(rel: str) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else RAIZ / p

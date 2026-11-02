"""Estado persistente de cada projeto (um vídeo + seus shorts).

Cada projeto vive em projetos/<id>/ com um projeto.json e todos os arquivos
gerados (áudio, imagens, vídeo, shorts, thumbnail).
"""
from __future__ import annotations

import json
import re
import threading
import unicodedata
from datetime import datetime
from pathlib import Path

from . import config

# Ordem da linha de produção (cada uma é um "agente")
ETAPAS = ["roteiro", "narracao", "cenas", "montagem", "shorts", "thumbnail"]

# Se uma etapa for refeita, quais outras precisam ser refeitas junto
DEPENDENTES = {
    "roteiro": ["roteiro", "narracao", "cenas", "montagem", "shorts", "thumbnail"],
    "narracao": ["narracao", "montagem", "shorts"],
    "cenas": ["cenas", "montagem", "shorts"],
    "montagem": ["montagem"],
    "shorts": ["shorts"],
    "thumbnail": ["thumbnail"],
}

# Status do projeto
NA_FILA = "na_fila"                    # aguardando a fábrica produzir
PRODUZINDO = "produzindo"
AGUARDANDO = "aguardando_aprovacao"    # pronto para você revisar
ALTERACAO = "alteracao_solicitada"     # você pediu mudança
APROVADO = "aprovado"                  # vai ser enviado ao YouTube
PUBLICANDO = "publicando"
AGENDADO = "agendado"                  # enviado e programado no YouTube
DESCARTADO = "descartado"
ERRO = "erro"

ROTULOS = {
    NA_FILA: "Na fila",
    PRODUZINDO: "Produzindo",
    AGUARDANDO: "Aguardando aprovação",
    ALTERACAO: "Alteração solicitada",
    APROVADO: "Aprovado",
    PUBLICANDO: "Publicando",
    AGENDADO: "Agendado",
    DESCARTADO: "Descartado",
    ERRO: "Erro",
}

_lock = threading.RLock()


def pasta_projetos() -> Path:
    p = config.caminho(config.carregar().get_path("fabrica.pasta_projetos", "projetos"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def slug(texto: str, limite: int = 40) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t[:limite].strip("-") or "video"


class Projeto:
    def __init__(self, dados: dict):
        self.dados = dados

    # ---------- atalhos ----------
    @property
    def id(self) -> str:
        return self.dados["id"]

    @property
    def pasta(self) -> Path:
        return pasta_projetos() / self.id

    @property
    def status(self) -> str:
        return self.dados["status"]

    @property
    def roteiro(self) -> dict | None:
        return self.dados.get("roteiro")

    def arquivo(self, rel: str) -> Path:
        p = self.pasta / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def __getitem__(self, k):
        return self.dados[k]

    def get(self, k, padrao=None):
        return self.dados.get(k, padrao)

    # ---------- persistência ----------
    def salvar(self) -> None:
        with _lock:
            self.dados["atualizado_em"] = agora()
            self.pasta.mkdir(parents=True, exist_ok=True)
            tmp = self.pasta / "projeto.json.tmp"
            tmp.write_text(json.dumps(self.dados, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.pasta / "projeto.json")

    def log(self, msg: str) -> None:
        self.dados.setdefault("historico", []).append({"em": agora(), "msg": msg})
        self.salvar()

    def set_status(self, status: str, msg: str | None = None) -> None:
        self.dados["status"] = status
        if msg:
            self.log(msg)
        else:
            self.salvar()

    def set_etapa(self, etapa: str, status: str, detalhe: str = "") -> None:
        self.dados["etapas"][etapa] = {"status": status, "detalhe": detalhe, "em": agora()}
        self.salvar()

    def etapas_pendentes(self) -> list[str]:
        return [e for e in ETAPAS if self.dados["etapas"][e]["status"] != "ok"]

    def invalidar(self, etapa: str) -> list[str]:
        refazer = DEPENDENTES[etapa]
        for e in refazer:
            self.dados["etapas"][e] = {"status": "pendente", "detalhe": "", "em": agora()}
        self.salvar()
        return refazer


# ---------- coleção ----------
def criar(tema: str, angulo: str = "", origem: str = "manual") -> Projeto:
    with _lock:
        base = f"{datetime.now():%Y%m%d-%H%M%S}-{slug(tema)}"
        pid, n = base, 2
        while (pasta_projetos() / pid).exists():
            pid, n = f"{base}-{n}", n + 1
        p = Projeto(
            {
                "id": pid,
                "tema": tema,
                "angulo": angulo,
                "origem": origem,
                "status": NA_FILA,
                "criado_em": agora(),
                "etapas": {e: {"status": "pendente", "detalhe": "", "em": agora()} for e in ETAPAS},
                "alteracoes": [],
                "historico": [],
            }
        )
        p.log(f"Pauta criada: {tema}")
        return p


def carregar(pid: str) -> Projeto:
    with _lock:
        arq = pasta_projetos() / pid / "projeto.json"
        if not arq.exists():
            raise KeyError(pid)
        return Projeto(json.loads(arq.read_text(encoding="utf-8")))


def listar() -> list[Projeto]:
    with _lock:
        projetos = []
        for arq in sorted(pasta_projetos().glob("*/projeto.json")):
            try:
                projetos.append(Projeto(json.loads(arq.read_text(encoding="utf-8"))))
            except (json.JSONDecodeError, OSError):
                continue
        return sorted(projetos, key=lambda p: p.get("criado_em", ""), reverse=True)

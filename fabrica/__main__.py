"""Linha de comando da fábrica.

  python -m fabrica painel               # abre o painel de aprovação + liga a fábrica
  python -m fabrica pauta -n 5           # agente de pauta sugere 5 vídeos e coloca na fila
  python -m fabrica novo "tema" [-a "ângulo"]
  python -m fabrica worker               # só a fábrica, sem painel
  python -m fabrica rodar                # processa toda a fila e sai
  python -m fabrica status
  python -m fabrica aprovar <id> [--quando "2026-11-10T18:00"]
  python -m fabrica alterar <id> "o que mudar" [--etapa thumbnail]
  python -m fabrica retomar <id>
  python -m fabrica youtube-login
  python -m fabrica verificar            # confere se está tudo configurado
"""
from __future__ import annotations

import argparse
import sys

from . import estado, pipeline


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="fabrica", description="Fábrica de canal dark no YouTube")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("painel")
    s.add_argument("--porta", type=int, default=8000)
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--sem-worker", action="store_true")

    s = sub.add_parser("pauta")
    s.add_argument("-n", type=int, default=5)

    s = sub.add_parser("novo")
    s.add_argument("tema")
    s.add_argument("-a", "--angulo", default="")

    sub.add_parser("worker")
    sub.add_parser("rodar")
    sub.add_parser("status")

    s = sub.add_parser("aprovar")
    s.add_argument("id")
    s.add_argument("--quando", default=None)

    s = sub.add_parser("alterar")
    s.add_argument("id")
    s.add_argument("pedido")
    s.add_argument("--etapa", default="auto", choices=["auto", *estado.ETAPAS])

    s = sub.add_parser("retomar")
    s.add_argument("id")

    sub.add_parser("youtube-login")
    sub.add_parser("verificar")

    a = ap.parse_args(argv)

    if a.cmd == "painel":
        from .painel.app import rodar

        rodar(a.host, a.porta, worker=not a.sem_worker)
    elif a.cmd == "pauta":
        from .etapas import pauta

        for item in pauta.gerar(a.n):
            print(f"➕ {item['tema']} — {item['angulo']}")
    elif a.cmd == "novo":
        p = estado.criar(a.tema, a.angulo)
        print(f"➕ {p.id}")
    elif a.cmd == "worker":
        pipeline.worker()
    elif a.cmd == "rodar":
        pipeline.recuperar_interrompidos()
        while pipeline.passo():
            pass
        print("✅ Fila vazia.")
    elif a.cmd == "status":
        for p in estado.listar():
            titulo = (p.roteiro or {}).get("titulo") or p["tema"]
            etapas = " ".join(
                {"ok": "✔", "rodando": "…", "erro": "✖"}.get(p["etapas"][e]["status"], "·") for e in estado.ETAPAS
            )
            print(f"{estado.ROTULOS[p.status]:<22} [{etapas}] {p.id}  {titulo}")
            if p.get("erro"):
                print(f"{'':<22}  ↳ {p['erro']}")
    elif a.cmd == "aprovar":
        p = estado.carregar(a.id)
        pipeline.aprovar(p, a.quando)
        print("👍 Aprovado. A fábrica vai publicar e agendar.")
    elif a.cmd == "alterar":
        p = estado.carregar(a.id)
        etapa = pipeline.pedir_alteracao(p, a.pedido, a.etapa)
        print(f"✏️  Alteração enviada para o agente de {etapa}.")
    elif a.cmd == "retomar":
        pipeline.retomar(estado.carregar(a.id))
        print("🔁 Recolocado na fila.")
    elif a.cmd == "verificar":
        from . import verificar

        return verificar.rodar()
    elif a.cmd == "youtube-login":
        from . import youtube

        print(f"✅ Conectado ao canal: {youtube.login()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

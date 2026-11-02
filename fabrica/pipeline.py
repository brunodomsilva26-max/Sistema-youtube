"""Orquestrador: a "fábrica". Move cada projeto pela linha de produção,
aplica as alterações que você pedir e publica o que você aprovar."""
from __future__ import annotations

import threading
import time
import traceback
from datetime import datetime

from . import agenda, config, estado, youtube
from .etapas import cenas, montagem, narracao, roteiro, shorts, thumbnail

EXECUTORES = {
    "roteiro": roteiro.gerar,
    "narracao": narracao.executar,
    "cenas": cenas.executar,
    "montagem": montagem.executar,
    "shorts": shorts.executar,
    "thumbnail": thumbnail.executar,
}

# Qual projeto/etapa cada agente está tocando agora (para o painel "Fábrica")
atividade: dict[str, dict] = {}
_trava = threading.Lock()


def produzir(p: estado.Projeto, feedback: str | None = None) -> None:
    """Roda todas as etapas pendentes do projeto."""
    p.set_status(estado.PRODUZINDO)
    for etapa in p.etapas_pendentes():
        atividade[etapa] = {"projeto": p.id, "titulo": (p.roteiro or {}).get("titulo", p["tema"]), "desde": time.time()}
        p.set_etapa(etapa, "rodando")
        try:
            if etapa == "roteiro":
                roteiro.gerar(p, feedback)
            else:
                EXECUTORES[etapa](p, feedback)
            p.set_etapa(etapa, "ok")
            p.log(f"Etapa {etapa} concluída")
        except Exception as e:
            p.set_etapa(etapa, "erro", str(e)[:500])
            p.dados["erro"] = f"{etapa}: {e}"
            p.set_status(estado.ERRO, f"Erro na etapa {etapa}: {e}")
            traceback.print_exc()
            return
        finally:
            atividade.pop(etapa, None)
    p.dados.pop("erro", None)
    p.set_status(estado.AGUARDANDO, "Pronto para aprovação ✅")


def pedir_alteracao(p: estado.Projeto, feedback: str, etapa: str = "auto") -> str:
    if etapa == "auto":
        etapa = roteiro.classificar_alteracao(feedback)
    p.dados.setdefault("alteracoes", []).append({"em": estado.agora(), "pedido": feedback, "etapa": etapa, "feita": False})
    p.dados["alteracao_pendente"] = {"pedido": feedback, "etapa": etapa}
    p.set_status(estado.ALTERACAO, f"Alteração pedida ({etapa}): {feedback}")
    return etapa


def aplicar_alteracao(p: estado.Projeto) -> None:
    alt = p.dados.pop("alteracao_pendente")
    etapa, feedback = alt["etapa"], alt["pedido"]
    try:
        if etapa in ("cenas", "shorts", "thumbnail"):
            roteiro.revisar_parte(p, etapa, feedback)
    except Exception as e:
        p.dados["erro"] = f"revisão {etapa}: {e}"
        p.set_status(estado.ERRO, f"Erro ao revisar {etapa}: {e}")
        return
    p.invalidar(etapa)
    for a in p.dados.get("alteracoes", []):
        a["feita"] = True
    produzir(p, feedback if etapa == "roteiro" else None)


def aprovar(p: estado.Projeto, publicar_em: str | None = None) -> None:
    if publicar_em:
        p.dados["publicar_em_manual"] = publicar_em
    p.set_status(estado.APROVADO, "Aprovado por você 👍")


def publicar(p: estado.Projeto) -> None:
    r = p.roteiro
    gerados = p.get("shorts_gerados", [])
    data_video, datas_shorts = agenda.proximos(len(gerados))
    if p.get("publicar_em_manual"):
        data_video = datetime.fromisoformat(p["publicar_em_manual"]).replace(tzinfo=data_video.tzinfo)
    p.set_status(estado.PUBLICANDO, f"Enviando ao YouTube (estreia {data_video:%d/%m %H:%M})")

    def prog(x):
        p.dados["upload_progresso"] = x
        p.salvar()

    ag = {"modo": config.carregar().get_path("youtube.modo", "simulado"), "shorts": []}
    vid = youtube.enviar(p.pasta / "video.mp4", r["titulo"], r["descricao"], r["tags"], data_video,
                         p.pasta / "thumbnail.jpg", prog)
    ag["video"] = {"id": vid, "publicar_em": data_video.isoformat(), "url": f"https://youtu.be/{vid}"}
    for s, quando in zip(gerados, datas_shorts):
        desc = f"{s['descricao']}\n\nVídeo completo: https://youtu.be/{vid}\n#shorts"
        sid = youtube.enviar(p.pasta / s["arquivo"], s["titulo"][:90] + " #shorts", desc, r["tags"], quando, None, prog)
        ag["shorts"].append({"id": sid, "titulo": s["titulo"], "publicar_em": quando.isoformat(),
                             "url": f"https://youtube.com/shorts/{sid}"})
    p.dados["agendamento"] = ag
    p.set_status(estado.AGENDADO, f"Agendado no YouTube para {data_video:%d/%m/%Y %H:%M} 🗓️")


def proxima_tarefa() -> tuple[str, estado.Projeto] | None:
    projetos = list(reversed(estado.listar()))  # mais antigos primeiro
    for status, acao in [(estado.APROVADO, "publicar"), (estado.ALTERACAO, "alterar"), (estado.NA_FILA, "produzir")]:
        for p in projetos:
            if p.status == status and (acao != "alterar" or p.get("alteracao_pendente")):
                return acao, p
    return None


def passo() -> bool:
    """Executa uma tarefa da fila. Devolve True se fez algo."""
    with _trava:
        tarefa = proxima_tarefa()
        if not tarefa:
            return False
        acao, p = tarefa
        try:
            if acao == "publicar":
                publicar(p)
            elif acao == "alterar":
                aplicar_alteracao(p)
            else:
                produzir(p)
        except Exception as e:
            traceback.print_exc()
            p.dados["erro"] = str(e)
            # publicação que falhou volta para "aprovado" só se for re-tentada manualmente
            p.set_status(estado.ERRO, f"Erro: {e}")
        return True


def retomar(p: estado.Projeto) -> None:
    """Depois de um erro, recoloca o projeto na fila no ponto certo."""
    p.dados.pop("erro", None)
    if all(p["etapas"][e]["status"] == "ok" for e in estado.ETAPAS):
        p.set_status(estado.APROVADO, "Nova tentativa de publicação")
    else:
        p.set_status(estado.NA_FILA, "Recolocado na fila")


def recuperar_interrompidos() -> None:
    """Se a fábrica foi desligada no meio de um trabalho, retoma de onde parou."""
    for p in estado.listar():
        if p.status == estado.PRODUZINDO:
            for e in estado.ETAPAS:
                if p["etapas"][e]["status"] == "rodando":
                    p["etapas"][e]["status"] = "pendente"
            p.set_status(estado.NA_FILA, "Retomando produção interrompida")
        elif p.status == estado.PUBLICANDO:
            p.set_status(estado.APROVADO, "Retomando publicação interrompida")


def worker(parar: threading.Event | None = None) -> None:
    intervalo = config.carregar().get_path("fabrica.intervalo_worker_segundos", 5)
    recuperar_interrompidos()
    print("🏭 Fábrica ligada. Aguardando trabalho...")
    while not (parar and parar.is_set()):
        if not passo():
            time.sleep(intervalo)

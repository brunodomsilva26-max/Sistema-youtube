"""Painel web: aprovação, fábrica (agentes trabalhando) e agenda."""
from __future__ import annotations

import threading
import time
from pathlib import Path

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_from_directory, url_for

from .. import config, estado, pipeline

app = Flask(__name__)
app.secret_key = config.env("FABRICA_SECRET", "fabrica-local")

AGENTES = [
    ("pauta", "Pauta", "🧭", "#3b82f6"),
    ("roteiro", "Roteiro", "✍️", "#8b5cf6"),
    ("narracao", "Narração", "🎙️", "#ec4899"),
    ("cenas", "Cenas", "🎨", "#f97316"),
    ("montagem", "Montagem", "🎬", "#10b981"),
    ("shorts", "Shorts", "📱", "#06b6d4"),
    ("thumbnail", "Thumbnail", "🖼️", "#eab308"),
    ("publicacao", "Publicação", "🚀", "#ef4444"),
]


@app.context_processor
def _globais():
    return {"ROTULOS": estado.ROTULOS, "ETAPAS": estado.ETAPAS, "canal": config.carregar()["canal"]}


def _titulo(p) -> str:
    return (p.roteiro or {}).get("titulo") or p["tema"]


app.jinja_env.globals["titulo"] = _titulo


def _contagem(projetos):
    c = {k: 0 for k in estado.ROTULOS}
    for p in projetos:
        c[p.status] += 1
    return c


@app.get("/")
def aprovacao():
    projetos = estado.listar()
    fila = [p for p in projetos if p.status == estado.AGUARDANDO]
    em_producao = [p for p in projetos if p.status in (estado.NA_FILA, estado.PRODUZINDO, estado.ALTERACAO, estado.APROVADO, estado.PUBLICANDO)]
    erros = [p for p in projetos if p.status == estado.ERRO]
    return render_template("aprovacao.html", fila=fila, em_producao=em_producao, erros=erros,
                           c=_contagem(projetos), aba="aprovacao")


@app.get("/fabrica")
def fabrica():
    return render_template("fabrica.html", agentes=AGENTES, aba="fabrica")


@app.get("/api/fabrica")
def api_fabrica():
    projetos = estado.listar()
    estados = {}
    for chave, *_ in AGENTES:
        estados[chave] = {"status": "ocioso", "texto": "esperando trabalho"}
    for etapa, info in list(pipeline.atividade.items()):
        try:
            det = estado.carregar(info["projeto"])["etapas"][etapa].get("detalhe", "")
        except KeyError:
            det = ""
        estados[etapa] = {"status": "trabalhando", "texto": f"{info['titulo'][:40]} {('— ' + det) if det else ''}"}
    for p in projetos:
        if p.status == estado.PUBLICANDO:
            estados["publicacao"] = {"status": "trabalhando", "texto": f"enviando {_titulo(p)[:40]}"}
    fila = sum(1 for p in projetos if p.status == estado.NA_FILA)
    if fila:
        estados["pauta"] = {"status": "pronto", "texto": f"{fila} pauta(s) na fila"}
    return jsonify({"agentes": estados, "contagem": _contagem(projetos), "ts": time.time()})


@app.get("/agenda")
def agenda():
    itens = []
    for p in estado.listar():
        ag = p.get("agendamento")
        if not ag:
            continue
        itens.append({"quando": ag["video"]["publicar_em"], "tipo": "Vídeo", "titulo": _titulo(p),
                      "url": ag["video"]["url"], "modo": ag["modo"], "id": p.id})
        for s in ag.get("shorts", []):
            itens.append({"quando": s["publicar_em"], "tipo": "Short", "titulo": s["titulo"],
                          "url": s["url"], "modo": ag["modo"], "id": p.id})
    itens.sort(key=lambda x: x["quando"])
    return render_template("agenda.html", itens=itens, aba="agenda")


@app.get("/projeto/<pid>")
def projeto(pid):
    try:
        p = estado.carregar(pid)
    except KeyError:
        abort(404)
    return render_template("projeto.html", p=p, aba="aprovacao")


@app.get("/midia/<pid>/<path:arquivo>")
def midia(pid, arquivo):
    pasta = estado.pasta_projetos() / pid
    if not (pasta / arquivo).resolve().is_relative_to(pasta.resolve()):
        abort(403)
    resp = send_from_directory(pasta, arquivo, conditional=True)
    resp.headers["Cache-Control"] = "no-cache"
    return resp


# ------------------------------------------------------------------ ações
@app.post("/projeto/<pid>/aprovar")
def acao_aprovar(pid):
    p = estado.carregar(pid)
    if p.status != estado.AGUARDANDO:
        flash("Esse vídeo não está aguardando aprovação.")
    else:
        pipeline.aprovar(p, request.form.get("quando") or None)
        flash("👍 Aprovado! A fábrica vai subir no YouTube e deixar agendado.")
    return redirect(url_for("aprovacao"))


@app.post("/projeto/<pid>/alterar")
def acao_alterar(pid):
    p = estado.carregar(pid)
    pedido = (request.form.get("pedido") or "").strip()
    if not pedido:
        flash("Escreva o que precisa mudar.")
        return redirect(url_for("projeto", pid=pid))
    etapa = pipeline.pedir_alteracao(p, pedido, request.form.get("etapa", "auto"))
    flash(f"✏️ Pedido enviado para o agente de {etapa}. Ele já vai resolver.")
    return redirect(url_for("aprovacao"))


@app.post("/projeto/<pid>/descartar")
def acao_descartar(pid):
    estado.carregar(pid).set_status(estado.DESCARTADO, "Descartado por você")
    flash("🗑️ Vídeo descartado.")
    return redirect(url_for("aprovacao"))


@app.post("/projeto/<pid>/retomar")
def acao_retomar(pid):
    pipeline.retomar(estado.carregar(pid))
    flash("🔁 Recolocado na fila.")
    return redirect(url_for("aprovacao"))


@app.post("/pautas")
def acao_pautas():
    tema = (request.form.get("tema") or "").strip()
    if tema:
        estado.criar(tema, request.form.get("angulo", ""))
        flash("➕ Pauta adicionada na fila.")
    else:
        n = int(request.form.get("n", 3))

        def _gerar():
            from ..etapas import pauta

            pipeline.atividade["pauta"] = {"projeto": "", "titulo": f"pensando em {n} pautas", "desde": time.time()}
            try:
                pauta.gerar(n)
            except Exception as e:
                print(f"Erro no agente de pauta: {e}")
            finally:
                pipeline.atividade.pop("pauta", None)

        threading.Thread(target=_gerar, daemon=True).start()
        flash(f"🧭 Agente de pauta pensando em {n} vídeos novos...")
    return redirect(url_for("aprovacao"))


def rodar(host: str = "127.0.0.1", porta: int = 8000, worker: bool = True) -> None:
    if worker:
        threading.Thread(target=pipeline.worker, daemon=True).start()
    print(f"🖥️  Painel em http://{host}:{porta}")
    app.run(host=host, port=porta, debug=False, threaded=True)

"""Calcula os próximos horários livres de publicação (vídeos e shorts)."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import config, estado


def _fuso() -> ZoneInfo:
    return ZoneInfo(config.carregar().get_path("agenda.fuso", "America/Sao_Paulo"))


def ocupados() -> set[str]:
    usados = set()
    for p in estado.listar():
        ag = p.get("agendamento") or {}
        if ag.get("video"):
            usados.add(ag["video"]["publicar_em"])
        for s in ag.get("shorts", []):
            usados.add(s["publicar_em"])
    return usados


def _slots(dias: list[int] | None, horarios: list[str], inicio: datetime):
    tz = _fuso()
    dia = inicio.date()
    for _ in range(400):
        if dias is None or dia.weekday() in dias:
            for h in sorted(horarios):
                hh, mm = map(int, h.split(":"))
                t = datetime(dia.year, dia.month, dia.day, hh, mm, tzinfo=tz)
                if t > inicio:
                    yield t
        dia += timedelta(days=1)


def proximos(qtd_shorts: int) -> tuple[datetime, list[datetime]]:
    cfg = config.carregar()
    usados = ocupados()
    agora = datetime.now(_fuso()) + timedelta(hours=1)  # margem para processamento do YouTube

    video = next(
        t for t in _slots(cfg.get_path("agenda.dias_videos", [0, 2, 4]),
                          [cfg.get_path("agenda.horario_videos", "18:00")], agora)
        if t.isoformat() not in usados
    )
    usados.add(video.isoformat())
    shorts = []
    for t in _slots(None, cfg.get_path("agenda.horarios_shorts", ["12:00"]), video):
        if len(shorts) >= qtd_shorts:
            break
        if t.isoformat() not in usados:
            shorts.append(t)
            usados.add(t.isoformat())
    return video, shorts

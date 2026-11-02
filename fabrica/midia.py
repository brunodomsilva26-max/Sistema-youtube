"""Utilitários de áudio/vídeo (ffmpeg) e legendas."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path


class ErroFFmpeg(RuntimeError):
    pass


def ffmpeg(*args: str) -> None:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise ErroFFmpeg(f"ffmpeg falhou: {r.stderr.strip()[-800:]}")


def duracao(arquivo: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(arquivo)],
        capture_output=True,
        text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError as e:
        raise ErroFFmpeg(f"Não consegui medir a duração de {arquivo}") from e


def concatenar(arquivos: list[Path], saida: Path, recodificar_audio: bool = False) -> None:
    lista = saida.with_suffix(".txt")
    lista.write_text("".join(f"file '{a.resolve()}'\n" for a in arquivos), encoding="utf-8")
    extra = ["-c:a", "libmp3lame", "-b:a", "192k"] if recodificar_audio else ["-c", "copy"]
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(lista), *extra, str(saida))
    lista.unlink(missing_ok=True)


# ------------------------------------------------------------------ legendas
def _tempo_srt(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def quebrar_frases(texto: str, max_palavras: int) -> list[str]:
    palavras = texto.split()
    pedacos, atual = [], []
    for w in palavras:
        atual.append(w)
        if len(atual) >= max_palavras or re.search(r"[.!?…]$", w):
            pedacos.append(" ".join(atual))
            atual = []
    if atual:
        pedacos.append(" ".join(atual))
    # junta pedaços muito curtos
    final: list[str] = []
    for pz in pedacos:
        if final and len(pz.split()) <= 2 and len(final[-1].split()) + len(pz.split()) <= max_palavras + 2:
            final[-1] += " " + pz
        else:
            final.append(pz)
    return final


def gerar_srt(trechos: list[tuple[str, float]], saida: Path, max_palavras: int = 7) -> None:
    """trechos = [(texto, duracao_segundos)] em sequência."""
    linhas, inicio, n = [], 0.0, 1
    for texto, dur in trechos:
        partes = quebrar_frases(texto, max_palavras) or [texto]
        total = sum(len(x) for x in partes) or 1
        t = inicio
        for parte in partes:
            d = dur * len(parte) / total
            linhas.append(f"{n}\n{_tempo_srt(t)} --> {_tempo_srt(t + d)}\n{parte}\n")
            n, t = n + 1, t + d
        inicio += dur
    saida.write_text("\n".join(linhas), encoding="utf-8")


def escapar_filtro(caminho: Path) -> str:
    """Escapa caminho para uso dentro de filtros do ffmpeg (subtitles=...)."""
    s = str(caminho.resolve())
    return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")

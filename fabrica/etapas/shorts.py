"""Agente 6 — SHORTS: cria os vídeos verticais (1080x1920, até 59s) a partir do roteiro.

Cada fala do short é narrada e ilustrada com uma imagem do vídeo longo,
com fundo desfocado e legenda grande.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .. import estado, midia
from . import montagem, narracao

FPS = 30
W, H = 1080, 1920
LIMITE = 59.0


def segmento_vertical(imagem: Path, dur: float, saida: Path, idx: int) -> None:
    frames = max(1, int(round(dur * FPS)))
    zoom = "min(zoom+0.0012,1.25)" if idx % 2 == 0 else "if(eq(on,0),1.25,max(zoom-0.0012,1.0))"
    filtro = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=25:2,"
        f"eq=brightness=-0.15[bg];"
        f"[0:v]scale={W * 2}:-2,zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={W}x{int(W * 9 / 16) // 2 * 2}:fps={FPS}[fg];"
        f"[bg]fps={FPS}[bgf];[bgf][fg]overlay=(W-w)/2:(H-h)/2-120,format=yuv420p[v]"
    )
    midia.ffmpeg(
        "-loop", "1", "-i", str(imagem), "-filter_complex", filtro, "-map", "[v]",
        "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-r", str(FPS), str(saida),
    )


def executar(p: estado.Projeto, feedback: str | None = None) -> None:
    pasta = p.pasta / "shorts"
    if pasta.exists():
        shutil.rmtree(pasta)
    resultado = []
    shorts = p.roteiro["shorts"]
    for s_idx, short in enumerate(shorts):
        base = f"shorts/{s_idx + 1}"
        audios, segs, trechos, total = [], [], [], 0.0
        for f_idx, fala in enumerate(short["falas"]):
            p.set_etapa("shorts", "rodando", f"short {s_idx + 1}/{len(shorts)} — fala {f_idx + 1}")
            aud = p.arquivo(f"{base}/fala_{f_idx:02}.mp3")
            dur = narracao.falar(fala["texto"], aud)
            if total + dur > LIMITE and audios:
                aud.unlink(missing_ok=True)
                break
            seg = p.arquivo(f"{base}/seg_{f_idx:02}.mp4")
            segmento_vertical(p.pasta / f"cenas/cena_{fala['cena']:03}.jpg", dur, seg, f_idx)
            audios.append(aud)
            segs.append(seg)
            trechos.append((fala["texto"], dur))
            total += dur
        audio = p.arquivo(f"{base}/audio.mp3")
        midia.concatenar(audios, audio, recodificar_audio=True)
        mudo = p.arquivo(f"{base}/mudo.mp4")
        midia.concatenar(segs, mudo)
        srt = p.arquivo(f"{base}/legenda.srt")
        midia.gerar_srt(trechos, srt, max_palavras=4)
        final = p.arquivo(f"shorts/short_{s_idx + 1}.mp4")
        montagem.finalizar(mudo, audio, srt, final, vertical=True)
        shutil.rmtree(p.pasta / base, ignore_errors=True)
        resultado.append({"arquivo": f"shorts/short_{s_idx + 1}.mp4", "titulo": short["titulo"],
                          "descricao": short["descricao"], "duracao": round(total, 1)})
    p.dados["shorts_gerados"] = resultado
    p.salvar()

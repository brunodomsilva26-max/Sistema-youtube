"""Agente 5 — MONTAGEM: junta imagens + narração + legendas (+ música) no vídeo final 1080p.

Cada imagem ganha um movimento de câmera (efeito Ken Burns) com a duração
exata do trecho de narração correspondente.
"""
from __future__ import annotations

from pathlib import Path

from .. import config, estado, midia

FPS = 30

# movimentos de câmera alternados para o vídeo não ficar monótono
MOVIMENTOS = [
    # zoom in no centro
    ("min(zoom+0.0007,1.18)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    # zoom out
    ("if(eq(on,0),1.18,max(zoom-0.0007,1.0))", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    # pan para a direita
    ("1.15", "(iw-iw/zoom)*on/{n}", "ih/2-(ih/zoom/2)"),
    # pan para a esquerda
    ("1.15", "(iw-iw/zoom)*(1-on/{n})", "ih/2-(ih/zoom/2)"),
]


def segmento_ken_burns(imagem: Path, dur: float, saida: Path, idx: int, w: int = 1920, h: int = 1080) -> None:
    frames = max(1, int(round(dur * FPS)))
    z, x, y = MOVIMENTOS[idx % len(MOVIMENTOS)]
    x, y = x.format(n=frames), y.format(n=frames)
    filtro = (
        f"scale={w * 3 // 2}:{h * 3 // 2}:force_original_aspect_ratio=increase,crop={w * 3 // 2}:{h * 3 // 2},"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={FPS},"
        f"format=yuv420p"
    )
    midia.ffmpeg(
        "-loop", "1", "-i", str(imagem), "-vf", filtro, "-frames:v", str(frames),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(FPS), str(saida),
    )


def estilo_legenda(vertical: bool = False) -> str:
    fonte = Path(config.carregar().get_path("video.fonte", "")).stem.split("-")[0] or "Sans"
    if vertical:
        return (f"FontName={fonte},FontSize=16,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
                "BorderStyle=1,Outline=3,Shadow=0,Alignment=2,MarginV=90")
    return (f"FontName={fonte},FontSize=20,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
            "BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=40")


def finalizar(video_mudo: Path, audio: Path, srt: Path | None, saida: Path, vertical: bool = False) -> None:
    """Coloca áudio (narração + música opcional) e legendas queimadas."""
    cfg = config.carregar()
    musica = cfg.get_path("video.musica_fundo") or ""
    musica_path = config.caminho(musica) if musica else None
    entradas = ["-i", str(video_mudo), "-i", str(audio)]
    filtros = []
    if srt and cfg.get_path("video.legendas", True):
        fontsdir = midia.escapar_filtro(Path(cfg.get_path("video.fonte", "/usr/share/fonts")).parent)
        filtros.append(
            f"[0:v]subtitles='{midia.escapar_filtro(srt)}':fontsdir='{fontsdir}':"
            f"force_style='{estilo_legenda(vertical)}'[v]"
        )
        vmap = "[v]"
    else:
        vmap = "0:v"
    if musica_path and musica_path.exists():
        entradas += ["-stream_loop", "-1", "-i", str(musica_path)]
        vol = cfg.get_path("video.volume_musica", 0.1)
        filtros.append(f"[2:a]volume={vol}[m];[1:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]")
        amap = "[a]"
    else:
        amap = "1:a"
    args = [*entradas]
    if filtros:
        args += ["-filter_complex", ";".join(filtros)]
    args += ["-map", vmap, "-map", amap, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
             "-movflags", "+faststart", str(saida)]
    midia.ffmpeg(*args)


def executar(p: estado.Projeto, feedback: str | None = None) -> None:
    blocos = p.roteiro["blocos"]
    duracoes = p.dados["duracoes"]
    segmentos = []
    for i, dur in enumerate(duracoes):
        p.set_etapa("montagem", "rodando", f"cena {i + 1}/{len(blocos)}")
        seg = p.arquivo(f"montagem/seg_{i:03}.mp4")
        segmento_ken_burns(p.pasta / f"cenas/cena_{i:03}.jpg", dur, seg, i)
        segmentos.append(seg)
    p.set_etapa("montagem", "rodando", "juntando e legendando")
    mudo = p.arquivo("montagem/video_mudo.mp4")
    midia.concatenar(segmentos, mudo)
    srt = p.arquivo("video.srt")
    midia.gerar_srt([(b["narracao"], d) for b, d in zip(blocos, duracoes)], srt)
    finalizar(mudo, p.pasta / "audio/narracao.mp3", srt, p.arquivo("video.mp4"))
    for s in segmentos:
        s.unlink(missing_ok=True)
    mudo.unlink(missing_ok=True)

"""Agente 7 — THUMBNAIL: imagem de fundo gerada por IA + texto grande com contorno,
uma palavra em destaque (amarelo), no padrão de canal dark. 1280x720."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from .. import config, estado
from .cenas import gerar_imagem

W, H = 1280, 720


def _fonte(tamanho: int) -> ImageFont.FreeTypeFont:
    for caminho in [
        config.carregar().get_path("video.fonte", ""),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(caminho, tamanho)
        except OSError:
            continue
    return ImageFont.load_default(tamanho)


def _quebrar(palavras: list[str], fonte, largura_max: int, draw) -> list[list[str]]:
    linhas, atual = [], []
    for w in palavras:
        teste = " ".join(atual + [w])
        if atual and draw.textlength(teste, font=fonte) > largura_max:
            linhas.append(atual)
            atual = [w]
        else:
            atual.append(w)
    if atual:
        linhas.append(atual)
    return linhas


def compor(fundo_path, texto: str, destaque: str, saida) -> None:
    cfg = config.carregar()
    cor_txt = cfg.get_path("thumbnail.cor_texto", "#FFFFFF")
    cor_dest = cfg.get_path("thumbnail.cor_destaque", "#FFD400")

    img = Image.open(fundo_path).convert("RGB").resize((W, H))
    img = ImageEnhance.Contrast(img).enhance(1.25)
    img = ImageEnhance.Color(img).enhance(1.2)
    # degradê escuro à esquerda para o texto respirar
    sombra = Image.new("L", (W, H))
    ds = ImageDraw.Draw(sombra)
    for x in range(W):
        ds.line([(x, 0), (x, H)], fill=int(max(0, 200 * (1 - x / (W * 0.75)))))
    img.paste(Image.new("RGB", (W, H), (0, 0, 0)), (0, 0), sombra)

    d = ImageDraw.Draw(img)
    palavras = texto.upper().split()
    destaque = destaque.upper().strip()
    if destaque.strip(".,!?") not in [w.strip(".,!?") for w in palavras]:
        destaque = palavras[0] if palavras else ""
    largura_max = int(W * 0.62)
    tamanho = 170
    while tamanho > 60:
        fonte = _fonte(tamanho)
        linhas = _quebrar(palavras, fonte, largura_max, d)
        altura = len(linhas) * tamanho * 1.05
        if len(linhas) <= 3 and altura < H * 0.8 and all(
            d.textlength(" ".join(l), font=fonte) <= largura_max for l in linhas
        ):
            break
        tamanho -= 8
    y = (H - altura) / 2
    contorno = max(6, tamanho // 14)
    for linha in linhas:
        x = 50
        for w in linha:
            cor = cor_dest if w.strip(".,!?") == destaque.strip(".,!?") else cor_txt
            d.text((x + 6, y + 8), w, font=fonte, fill=(0, 0, 0))  # sombra
            d.text((x, y), w, font=fonte, fill=cor, stroke_width=contorno, stroke_fill=(0, 0, 0))
            x += d.textlength(w + " ", font=fonte)
        y += tamanho * 1.05
    img.save(saida, quality=95)


def executar(p: estado.Projeto, feedback: str | None = None) -> None:
    t = p.roteiro["thumbnail"]
    fundo = p.arquivo("thumb_fundo.jpg")
    gerar_imagem(t["prompt"], fundo, W, H)
    compor(fundo, t["texto"], t["destaque"], p.arquivo("thumbnail.jpg"))

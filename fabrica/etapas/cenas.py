"""Agente 4 — CENAS: gera uma imagem para cada bloco do roteiro.

Provedores:
- pollinations -> grátis, sem chave (image.pollinations.ai)
- openai       -> gpt-image-1 (OPENAI_API_KEY)
- demo         -> imagens geradas localmente (para testes)
"""
from __future__ import annotations

import base64
import hashlib
import io
import random
import textwrap
import time
import urllib.parse
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from .. import config, estado


def gerar_imagem(prompt: str, saida: Path, largura: int = 1920, altura: int = 1080) -> Path:
    cfg = config.carregar()
    prov = cfg.get_path("imagens.provedor", "pollinations")
    estilo = cfg.get_path("imagens.estilo", "")
    completo = f"{prompt}, {estilo}" if estilo else prompt
    saida.parent.mkdir(parents=True, exist_ok=True)

    if prov == "pollinations":
        dados = _pollinations(completo, largura, altura)
    elif prov == "openai":
        dados = _openai(completo, largura, altura, cfg)
    elif prov == "demo":
        _demo(prompt, saida, largura, altura)
        return saida
    else:
        raise ValueError(f"Provedor de imagem desconhecido: {prov}")

    img = Image.open(io.BytesIO(dados)).convert("RGB")
    _cobrir(img, largura, altura).save(saida, quality=92)
    return saida


def _cobrir(img: Image.Image, w: int, h: int) -> Image.Image:
    """Redimensiona e corta para preencher exatamente w x h."""
    escala = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * escala), round(img.height * escala)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def _pollinations(prompt: str, w: int, h: int) -> bytes:
    seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
    url = (
        "https://image.pollinations.ai/prompt/"
        + urllib.parse.quote(prompt)
        + f"?width={w}&height={h}&nologo=true&seed={seed}&model=flux"
    )
    ultimo = ""
    for tentativa in range(4):
        try:
            r = requests.get(url, timeout=180)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                return r.content
            ultimo = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            ultimo = str(e)
        time.sleep(2 ** (tentativa + 1))
    raise RuntimeError(f"Pollinations não gerou a imagem ({ultimo})")


def _openai(prompt: str, w: int, h: int, cfg) -> bytes:
    chave = config.env("OPENAI_API_KEY")
    if not chave:
        raise RuntimeError("Defina OPENAI_API_KEY no .env")
    tamanho = "1536x1024" if w > h else ("1024x1536" if h > w else "1024x1024")
    r = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {chave}"},
        json={"model": cfg.get_path("imagens.openai_modelo", "gpt-image-1"), "prompt": prompt, "size": tamanho, "n": 1},
        timeout=300,
    )
    if r.status_code != 200:
        raise RuntimeError(f"OpenAI {r.status_code}: {r.text[:300]}")
    return base64.b64decode(r.json()["data"][0]["b64_json"])


def _demo(prompt: str, saida: Path, w: int, h: int) -> None:
    rnd = random.Random(prompt)
    c1 = tuple(rnd.randint(10, 80) for _ in range(3))
    c2 = tuple(rnd.randint(60, 170) for _ in range(3))
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(c1, c2)))
    for _ in range(25):
        x, y, r = rnd.randint(0, w), rnd.randint(0, h), rnd.randint(20, h // 4)
        d.ellipse((x - r, y - r, x + r, y + r), outline=(255, 255, 255, 40), width=2)
    try:
        fonte = ImageFont.truetype(config.carregar().get_path("video.fonte", ""), max(24, h // 22))
    except OSError:
        fonte = ImageFont.load_default()
    texto = "\n".join(textwrap.wrap(prompt, 40)[:4])
    d.multiline_text((w * 0.06, h * 0.7), texto, font=fonte, fill=(235, 235, 235))
    img.save(saida, quality=90)


def executar(p: estado.Projeto, feedback: str | None = None) -> None:
    blocos = p.roteiro["blocos"]
    for i, b in enumerate(blocos):
        p.set_etapa("cenas", "rodando", f"imagem {i + 1}/{len(blocos)}")
        gerar_imagem(b["cena"], p.arquivo(f"cenas/cena_{i:03}.jpg"))

"""Respostas prontas para o modo demo (testar a fábrica inteira sem chaves de API)."""
from __future__ import annotations

import random

_BLOCOS = [
    ("Em 1872, um navio foi encontrado à deriva no meio do Atlântico. As velas estavam abertas, a carga intacta. Mas não havia ninguém a bordo.",
     "an abandoned 19th century sailing ship drifting on a foggy ocean"),
    ("O nome dele era Mary Celeste. E até hoje ninguém conseguiu explicar o que aconteceu com as dez pessoas que estavam ali.",
     "old wooden ship nameplate covered in sea salt, close up"),
    ("Os marinheiros que encontraram o navio relataram algo estranho: a mesa estava posta, como se a tripulação tivesse saído às pressas.",
     "a dinner table inside an old ship cabin, candles, plates left untouched"),
    ("O bote salva-vidas tinha desaparecido. E o diário de bordo parava de repente, nove dias antes.",
     "an open captain logbook with old handwriting, dim lantern light"),
    ("Teorias não faltam: motim, piratas, um maremoto, até monstros marinhos. Mas nenhuma delas explica todos os detalhes.",
     "giant shadowy sea creature beneath a small ship, stormy night"),
    ("Se você tem uma teoria, deixa aqui nos comentários. E se inscreve, porque o próximo mistério é ainda mais estranho.",
     "a lighthouse beam cutting through fog at night"),
]


def resposta(tarefa: str, prompt: str) -> dict:
    if tarefa == "pauta":
        temas = [
            ("O navio fantasma Mary Celeste", "a tripulação que sumiu sem deixar rastro"),
            ("O incidente do Passo Dyatlov", "nove alpinistas e uma barraca rasgada por dentro"),
            ("O voo 19 no Triângulo das Bermudas", "cinco aviões que sumiram em um dia claro"),
            ("A Ilha das Bonecas no México", "a lenda por trás das bonecas penduradas"),
            ("O sinal Wow! de 1977", "72 segundos que nunca se repetiram"),
        ]
        random.shuffle(temas)
        return {"pautas": [{"tema": t, "angulo": a, "por_que_funciona": "curiosidade alta"} for t, a in temas]}
    if tarefa == "classificar":
        return {"etapa": "roteiro", "motivo": "demo"}
    blocos = [{"narracao": n, "cena": c} for n, c in _BLOCOS]
    thumb = {"texto": "NINGUÉM SOBREVIVEU?", "destaque": "NINGUÉM", "prompt": "ghost ship in dark fog, eerie green light"}
    shorts = [
        {"titulo": "O navio que apareceu sem ninguém", "descricao": "O mistério do Mary Celeste.",
         "falas": [{"texto": _BLOCOS[0][0], "cena": 0}, {"texto": _BLOCOS[2][0], "cena": 2}, {"texto": _BLOCOS[3][0], "cena": 3}]},
        {"titulo": "A mesa posta no navio fantasma", "descricao": "Ninguém explica.",
         "falas": [{"texto": _BLOCOS[2][0], "cena": 2}, {"texto": _BLOCOS[4][0], "cena": 4}]},
    ]
    if tarefa == "revisar_thumbnail":
        return {**thumb, "texto": "SUMIRAM NO MAR"}
    if tarefa == "revisar_shorts":
        return {"shorts": shorts}
    if tarefa == "revisar_cenas":
        return {"cenas": [c + ", darker" for _, c in _BLOCOS]}
    return {
        "titulo": "O Navio Fantasma Que Ninguém Consegue Explicar",
        "descricao": "Em 1872 o Mary Celeste foi encontrado vazio no meio do oceano.\n\n#misterio #historia #mariaceleste",
        "tags": ["mary celeste", "mistério", "navio fantasma", "história", "casos não resolvidos"],
        "blocos": blocos,
        "thumbnail": thumb,
        "shorts": shorts,
    }

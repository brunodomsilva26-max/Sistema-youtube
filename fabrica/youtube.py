"""Integração com a API oficial do YouTube (Data API v3).

Primeira vez: `python -m fabrica youtube-login` abre o navegador para você autorizar
o canal; o token fica salvo em credenciais/token.json.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from . import config

ESCOPOS = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


def _credenciais(interativo: bool = False):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    cfg = config.carregar()
    token = config.caminho(cfg.get_path("youtube.token", "credenciais/token.json"))
    secret = config.caminho(cfg.get_path("youtube.client_secret", "credenciais/client_secret.json"))
    creds = None
    if token.exists():
        creds = Credentials.from_authorized_user_file(str(token), ESCOPOS)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token.write_text(creds.to_json())
    if not creds or not creds.valid:
        if not interativo:
            raise RuntimeError("YouTube não autorizado. Rode: python -m fabrica youtube-login")
        if not secret.exists():
            raise RuntimeError(f"Coloque o client_secret.json do Google Cloud em {secret}")
        flow = InstalledAppFlow.from_client_secrets_file(str(secret), ESCOPOS)
        creds = flow.run_local_server(port=0, open_browser=True)
        token.parent.mkdir(parents=True, exist_ok=True)
        token.write_text(creds.to_json())
    return creds


def servico(interativo: bool = False):
    from googleapiclient.discovery import build

    return build("youtube", "v3", credentials=_credenciais(interativo), cache_discovery=False)


def login() -> str:
    yt = servico(interativo=True)
    canal = yt.channels().list(part="snippet", mine=True).execute()
    itens = canal.get("items", [])
    return itens[0]["snippet"]["title"] if itens else "(sem canal)"


def enviar(video: Path, titulo: str, descricao: str, tags: list[str], publicar_em: datetime,
           thumbnail: Path | None = None, progresso=None) -> str:
    """Envia o vídeo como privado com publicação programada. Devolve o videoId."""
    from googleapiclient.http import MediaFileUpload

    cfg = config.carregar()
    if cfg.get_path("youtube.modo", "simulado") != "real":
        return f"simulado-{abs(hash((str(video), titulo))) % 10**8}"

    yt = servico()
    corpo = {
        "snippet": {
            "title": titulo[:100],
            "description": descricao[:4900],
            "tags": tags[:30],
            "categoryId": str(cfg.get_path("youtube.categoria_id", "27")),
            "defaultLanguage": cfg.get_path("youtube.idioma_audio", "pt-BR"),
            "defaultAudioLanguage": cfg.get_path("youtube.idioma_audio", "pt-BR"),
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": publicar_em.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": bool(cfg.get_path("youtube.conteudo_sintetico", True)),
        },
    }
    midia = MediaFileUpload(str(video), chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=corpo, media_body=midia)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status and progresso:
            progresso(int(status.progress() * 100))
    vid = resp["id"]
    if thumbnail and thumbnail.exists():
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumbnail), mimetype="image/jpeg")).execute()
        except Exception as e:  # canal sem verificação não pode trocar thumbnail
            if progresso:
                progresso(f"thumbnail não aplicada: {e}")
    return vid

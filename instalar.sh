#!/usr/bin/env bash
# Instalador da Fábrica (Mac / Linux)
set -e
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "❌ Instale o Python 3.10+ em https://www.python.org/downloads/"; exit 1; }
if ! command -v ffmpeg >/dev/null; then
  if command -v brew >/dev/null; then brew install ffmpeg
  elif command -v apt >/dev/null; then sudo apt install -y ffmpeg
  else echo "⚠️  Instale o ffmpeg manualmente: https://ffmpeg.org/download.html"; fi
fi
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
[ -f .env ] || cp .env.example .env
mkdir -p credenciais
echo "✅ Instalado. Agora abra o arquivo .env e cole sua chave."
python -m fabrica verificar || true

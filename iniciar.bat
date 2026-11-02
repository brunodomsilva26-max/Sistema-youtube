@echo off
cd /d "%~dp0"
chcp 65001 >nul
call .venv\Scripts\activate.bat
start "" http://127.0.0.1:8000
python -m fabrica painel

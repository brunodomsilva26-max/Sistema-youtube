@echo off
REM Instalador da Fabrica (Windows)
cd /d "%~dp0"
chcp 65001 >nul
where python >nul 2>nul || (echo Instale o Python 3.10+ em https://www.python.org/downloads/ marcando "Add to PATH" & pause & exit /b 1)
where ffmpeg >nul 2>nul || winget install -e --id Gyan.FFmpeg
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -q --upgrade pip
pip install -q -r requirements.txt
if not exist .env copy .env.example .env >nul
if not exist credenciais mkdir credenciais
echo.
echo Instalado. Agora abra o arquivo .env e cole sua chave.
python -m fabrica verificar
pause

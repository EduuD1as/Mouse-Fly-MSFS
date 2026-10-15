@echo off
cd /d "%~dp0"
if not exist .venv python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt pyinstaller
.venv\Scripts\pyinstaller --noconfirm --clean --onefile --windowed --name "Mouse-Fly-MSFS" --icon assets\icon.ico --add-data "assets\icon.ico;assets" --collect-data customtkinter --exclude-module PIL --distpath . --workpath build main.py
rmdir /s /q build
del /q Mouse-Fly-MSFS.spec
echo.
echo Executavel gerado: "%~dp0Mouse-Fly-MSFS.exe"

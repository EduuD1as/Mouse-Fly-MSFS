@echo off
if not exist .venv python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt pyinstaller
.venv\Scripts\pyinstaller --noconfirm --clean --onefile --windowed --name "Mouse-Fly-MSFS" --icon assets\icon.ico --add-data "assets\icon.ico;assets" --collect-data customtkinter --exclude-module PIL main.py

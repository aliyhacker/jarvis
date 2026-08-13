@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM Sanal ortam varsa onu kullan, yoksa sistem Python'u
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\pythonw.exe" main.py
) else (
    start "" pythonw main.py
)

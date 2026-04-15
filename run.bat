@echo off
REM Ejecutar servidor Flask ActivosEQ
cd /d "%~dp0"
.venv\Scripts\python.exe app.py
pause

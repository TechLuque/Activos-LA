@echo off
REM Ejecutar servidor Flask ActivosLA
cd /d "%~dp0"
.venv\Scripts\python.exe app.py
pause

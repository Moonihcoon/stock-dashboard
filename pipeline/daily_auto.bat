@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set "PY="
if exist "%~dp0python_path.txt" set /p PY=<"%~dp0python_path.txt"
if defined PY if not exist "%PY%" set "PY="
if not defined PY exit /b 1
"%PY%" run_all.py

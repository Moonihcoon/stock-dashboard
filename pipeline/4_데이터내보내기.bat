@echo off
title 급등주 대시보드 - 키움 데이터 내보내기
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set "PY="
if exist "%~dp0python_path.txt" set /p PY=<"%~dp0python_path.txt"
if not defined PY (
  echo 파이썬 위치를 찾지 못했습니다.
  pause
  exit /b
)
echo 2020년 이후 키움 시세 전체를 바탕화면 stock\export 폴더로 내보냅니다 (3~5분)
"%PY%" export_data.py
start "" "%~dp0..\..\export"
echo 끝났습니다.
pause

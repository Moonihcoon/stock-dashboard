@echo off
title 급등주 대시보드 - 지금 실행
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set "PY="
if exist "%~dp0python_path.txt" set /p PY=<"%~dp0python_path.txt"
if defined PY if not exist "%PY%" set "PY="
if not defined PY (
    echo 파이썬 위치를 찾지 못했습니다. 바탕화면 stock 폴더의 설치_및_첫실행.bat 을 먼저 실행하세요.
    pause
    exit /b
)
echo 키움 시세 받기 - 통계 계산 - 대시보드 만들기 - GitHub 업로드 순서로 진행합니다.
echo 15~40분 정도 걸립니다. 창을 닫지 마세요.
echo.
"%PY%" run_all.py
echo.
echo 끝났습니다. 기록은 work 폴더의 log.txt 에 있습니다.
pause

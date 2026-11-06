@echo off
title 급등주 대시보드 - 전 종목 1분봉 받기
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
schtasks /query /tn "StockMinuteAll" >nul 2>&1
if errorlevel 1 (
  schtasks /create /tn "StockMinuteAll" /tr "\"%~dp0minute_all_auto.bat\"" /sc daily /st 21:10 /f >nul
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 30); Set-ScheduledTask -TaskName 'StockMinuteAll' -Settings $s | Out-Null"
  echo 매일 21:10 에 자동으로 이어 받기(업데이트)하도록 등록했습니다.
)
echo 전 종목 1분봉을 받습니다. 처음에는 15~28시간 걸립니다.
echo 창을 닫거나 PC가 꺼져도, 다시 실행하면(또는 매일 21:10 자동으로) 이어서 받습니다.
echo PC가 절전 모드로 들어가지 않게 해 주세요.
echo.
"%PY%" minute_all.py
echo 끝났습니다. 바탕화면 stock\minute_all 폴더를 확인하세요.
pause

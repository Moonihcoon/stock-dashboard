@echo off
title 급등주 대시보드 - 매일 자동 실행 등록
cd /d "%~dp0"
schtasks /create /tn "StockDashboardDaily" /tr "\"%~dp0daily_auto.bat\"" /sc weekly /d MON,TUE,WED,THU,FRI /st 16:40 /f
if errorlevel 1 (
    echo [오류] 등록에 실패했습니다. 이 화면을 캡처해서 Claude에게 보여 주세요.
) else (
    echo.
    echo [완료] 평일 오후 4시 40분마다 자동으로 실행됩니다. PC가 켜져 있고 로그인돼 있어야 합니다.
    echo        지우려면: schtasks /delete /tn StockDashboardDaily /f
)
pause

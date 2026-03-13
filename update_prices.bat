@echo off
chcp 65001 >nul
echo ========================================
echo   주식 가격 업데이트 중...
echo ========================================
cd /d "%~dp0"
python collectors/update_prices.py
echo.
echo 완료!
pause

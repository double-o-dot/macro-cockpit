@echo off
echo ============================================
echo   Macro Cockpit - Local Dev Server
echo   http://localhost:3000 에서 접속하세요
echo   종료: Ctrl+C
echo ============================================
cd /d "%~dp0docs"
python -m http.server 3000

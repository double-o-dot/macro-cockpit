@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  [1/2] Building static data...
python build_static.py
if errorlevel 1 (
    echo  BUILD FAILED
    pause
    exit /b 1
)
echo.
echo  [2/2] Pushing to GitHub...
git add docs/
git commit -m "update dashboard data %date% %time:~0,5%"
git push
echo.
echo  Deploy complete!
pause

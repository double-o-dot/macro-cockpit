@echo off
chcp 65001 >nul
cd /d "%~dp0"
python price_alert.py >> logs\price_alert_run.log 2>&1

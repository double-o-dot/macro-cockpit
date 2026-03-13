@echo off
chcp 65001 >nul
cd /d C:\Users\LENOVO1430\ClaudeCode\Invest
python briefing.py >> logs\briefing.log 2>&1

@echo off
title VASTX Wearable Logger

echo ==========================================
echo Starting VASTX Wearable Logger...
echo ==========================================

cd /d "%~dp0"

python\python.exe -m streamlit run app\app.py

pause
@echo off
echo ==========================================
echo Installing VASTX portable dependencies...
echo ==========================================

python -m pip install --target packages -r requirements.txt

echo.
echo Installation complete.
pause
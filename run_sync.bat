@echo off
cd /d "%~dp0"
if not exist data mkdir data
echo ===== %date% %time% ===== >> data\sync.log
".venv\Scripts\python.exe" sync.py >> data\sync.log 2>&1

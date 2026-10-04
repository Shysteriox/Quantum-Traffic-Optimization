@echo off
cd /d "%~dp0"
python -m venv .venv
if errorlevel 1 exit /b 1
.venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
.venv\Scripts\python real_city_sim.py
if errorlevel 1 exit /b 1
.venv\Scripts\python check_model.py
if errorlevel 1 exit /b 1
.venv\Scripts\python city_video.py

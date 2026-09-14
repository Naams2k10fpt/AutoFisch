@echo off
chcp 65001 > nul
title Fisch Multi-Rod Auto Fishing Bot
cd /d "%~dp0"

echo ========================================================
echo        FISCH MULTI-ROD AUTO FISHING BOT
echo   (Default Rod Bar Hover + Tranquility Rod 4-Lane)
echo ========================================================
echo.
echo Checking dependencies...
python -m pip install -q mss opencv-python pydirectinput keyboard

echo.
echo Starting Macro GUI...
start pythonw main.py
if errorlevel 1 (
    echo Pythonw failed, running with standard python:
    python main.py
)

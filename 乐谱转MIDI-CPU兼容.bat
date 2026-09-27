@echo off
chcp 65001 >nul
title HOMR 乐谱转 MIDI (CPU 兼容)
cd /d "%~dp0homr_gui"
echo ============================================
echo   HOMR 乐谱转 MIDI - CPU 兼容模式
echo ============================================
echo.
".venv\Scripts\python.exe" "homr_gui_cpu.py"
echo.
pause

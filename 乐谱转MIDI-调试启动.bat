@echo off
chcp 65001 >nul
title HOMR 调试启动
cd /d "%~dp0homr_gui"
echo ============================================
echo   HOMR 调试模式（显示完整日志）
echo ============================================
echo.
".venv\Scripts\python.exe" "homr_gui.py"
echo.
pause

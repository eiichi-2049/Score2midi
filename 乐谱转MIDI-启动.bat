@echo off
chcp 65001 >nul
title HOMR 乐谱转 MIDI
cd /d "%~dp0homr_gui"
echo ============================================
echo   HOMR 乐谱转 MIDI - 图形界面
echo ============================================
echo.
echo 启动中... 首次运行会自动下载 AI 模型，请耐心等待。
echo.
".venv\Scripts\pythonw.exe" "homr_gui.py"
if errorlevel 1 (
  echo.
  echo 启动失败，请改用「乐谱转MIDI-调试启动.bat」查看错误信息。
  pause
)

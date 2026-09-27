@echo off
chcp 65001 >nul
title 批量乐谱图片转 MIDI
cd /d "%~dp0"
if "%~1"=="" (
  echo 用法: 把图片或文件夹拖到本 bat 上
  echo 或:   转换命令行.bat 图片.png 乐谱图片\
  pause
  exit /b 1
)
"%~dp0homr_gui\.venv\Scripts\python.exe" "%~dp0img2midi.py" %*
echo.
pause

@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Score2MIDI Portable
cd /d "%~dp0"
set "ROOT=%cd%"
set "PY=%ROOT%\homr_gui\.venv\Scripts\python.exe"

echo ============================================
echo   Score to MIDI - Portable GUI
echo   http://127.0.0.1:8765/
echo ============================================
echo.

if not exist "%PY%" (
  echo [ERROR] venv not found: homr_gui\.venv
  echo Copy the whole folder and keep the structure.
  pause
  exit /b 1
)

echo [1/2] Check models...
"%PY%" -c "import sys; sys.path.insert(0,r'%ROOT%\homr_gui'); from homr.segmentation.config import segnet_path_onnx; from homr.transformer.configs import default_config as c; from pathlib import Path; ps=[segnet_path_onnx,c.filepaths.encoder_path,c.filepaths.decoder_path]; miss=[p for p in ps if not Path(p).exists()]; print('OK models ready' if not miss else 'MISSING: '+str(miss)); raise SystemExit(1 if miss else 0)"
if errorlevel 1 (
  echo Downloading missing models...
  "%PY%" "%ROOT%\download_models.py"
)

echo [2/2] Start server and open browser...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\open_gui.ps1" -Root "%ROOT%" -Port 8765
if errorlevel 1 (
  echo.
  echo [TIP] Open manually: http://127.0.0.1:8765/
)

echo.
echo URL: http://127.0.0.1:8765/
echo Server runs in a minimized window. Close that window to stop it.
echo.
pause
endlocal
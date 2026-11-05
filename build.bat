@echo off
rem Builds ScriptOverlay.exe (+ its _internal folder) at the root of this folder. Needs Python 3.
rem The app's data (games added, tables, OCR model, settings) is in data\ and is not touched.
rem To share: zip ScriptOverlay.exe + _internal.
chcp 65001 >nul
cd /d "%~dp0"
tasklist /fi "imagename eq ScriptOverlay.exe" | find /i "ScriptOverlay.exe" >nul && (echo Close Script Overlay first. & pause & exit /b 1)
python -m pip install --upgrade -r requirements.txt pyinstaller || goto :err
python -m PyInstaller --noconfirm --clean --windowed --name ScriptOverlay ^
  --distpath build\out --workpath build\work --specpath build ^
  --add-data "%~dp0resources;resources" ^
  --collect-all sudachipy --collect-data sudachidict_core --collect-all frida ^
  ScriptOverlay.pyw || goto :err
if exist "_internal" rmdir /s /q "_internal"
if exist "ScriptOverlay.exe" del /q "ScriptOverlay.exe"
move "build\out\ScriptOverlay\_internal" "_internal" >nul || goto :err
move "build\out\ScriptOverlay\ScriptOverlay.exe" "ScriptOverlay.exe" >nul || goto :err
rem old place of the .exe (before 04/11/2026)
if exist "dist" rmdir /s /q "dist"
echo.
echo Done: ScriptOverlay.exe
pause
exit /b 0
:err
echo Build failed.
pause
exit /b 1

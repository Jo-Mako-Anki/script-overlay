@echo off
rem Makes release\ScriptOverlay.zip, the file to post on GitHub (Releases): the app with everything a player needs
rem (game files .sop, saved GameFAQs guide, OCR program and model) and nothing personal or for developers (no settings, logs,
rem Excel/CSV tables, backups, build files, config.lua, python tools).
rem Run build.bat first if the code changed.
chcp 65001 >nul
cd /d "%~dp0"
if not exist "ScriptOverlay.exe" (echo ScriptOverlay.exe not found: run build.bat first. & pause & exit /b 1)
if not exist "_internal" (echo _internal folder not found: run build.bat first. & pause & exit /b 1)

set "STAGE=%TEMP%\ScriptOverlay_release"
set "APP=%STAGE%\Script Overlay"
if exist "%STAGE%" rmdir /s /q "%STAGE%"
mkdir "%APP%" || goto :err

copy /y "ScriptOverlay.exe" "%APP%\" >nul || goto :err
copy /y "README.md" "%APP%\" >nul || goto :err
robocopy "_internal" "%APP%\_internal" /E /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :err
rem game folders: readers, info data, maps, saved guides. No tables, no python tools. The .sop of P5R and Pokopia
rem go in data\tables (below); the one of Crystal also stays here: Script Viewer (mGBA) reads it from here.
robocopy "Games" "%APP%\Games" /S /NFL /NDL /NJH /NJS /NP ^
  /XF *.xlsx *.xlsm *.csv *.tsv *.txt *.py *.bak kanji_viewer.lua "%CD%\Games\Persona 5 Royal\P5R.sop" "%CD%\Games\Pokopia\Pokopia.sop" ^
  /XD tools _sauvegardes __pycache__ >nul
if errorlevel 8 goto :err
rem data: the games list, the .sop files and the OCR model. Not settings.json (screen positions), logs, caches.
mkdir "%APP%\data" || goto :err
copy /y "data\games_user.json" "%APP%\data\" >nul || goto :err
robocopy "data\tables" "%APP%\data\tables" *.sop /S /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :err
robocopy "data\tessdata" "%APP%\data\tessdata" /S /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :err
rem OCR program (trimmed copy: tesseract.exe, its libraries and its licence; no training tools)
robocopy "Tesseract" "%APP%\Tesseract" /E /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :err
rem the mGBA part: no personal config.lua
robocopy "Script Viewer" "%APP%\Script Viewer" /S /NFL /NDL /NJH /NJS /NP ^
  /XF config.lua ajouter_pnj.py *.zip *.bak ^
  /XD _sauvegardes __pycache__ Games >nul
if errorlevel 8 goto :err

if not exist "release" mkdir "release"
if exist "release\ScriptOverlay.zip" del /q "release\ScriptOverlay.zip"
tar -a -c -f "release\ScriptOverlay.zip" -C "%STAGE%" "Script Overlay" || goto :err
rmdir /s /q "%STAGE%"
echo.
echo Done: release\ScriptOverlay.zip
for %%F in ("release\ScriptOverlay.zip") do echo Size: %%~zF bytes
pause
exit /b 0
:err
echo Failed.
pause
exit /b 1

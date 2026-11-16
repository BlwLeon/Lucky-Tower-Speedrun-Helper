@echo off
REM Baut dist\LuckyTowerLauncher.exe (eine Datei, ohne Konsolenfenster)
REM Mitgeliefert werden swf\ und games.json, falls vorhanden.
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller || goto :err

set EXTRA=
if exist swf\*.swf set EXTRA=%EXTRA% --add-data "swf;swf"
if exist mods\*.dll set EXTRA=%EXTRA% --add-data "mods;mods"
if exist games.json set EXTRA=%EXTRA% --add-data "games.json;."

python -m PyInstaller --noconfirm --clean --onefile --windowed --name LuckyTowerLauncher %EXTRA% launcher.py || goto :err
echo.
echo Fertig: dist\LuckyTowerLauncher.exe
pause
exit /b 0
:err
echo Build fehlgeschlagen.
pause
exit /b 1

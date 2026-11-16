#!/usr/bin/env sh
# Baut dist/LuckyTowerLauncher für macOS/Linux (mit swf/ und games.json, falls vorhanden)
set -e
cd "$(dirname "$0")"
python3 -m pip install --upgrade pyinstaller
set --
ls swf/*.swf >/dev/null 2>&1 && set -- "$@" --add-data "swf:swf"
ls mods/*.dll >/dev/null 2>&1 && set -- "$@" --add-data "mods:mods"
[ -f games.json ] && set -- "$@" --add-data "games.json:."
python3 -m PyInstaller --noconfirm --clean --onefile --windowed --name LuckyTowerLauncher "$@" launcher.py
echo "Fertig: dist/LuckyTowerLauncher"

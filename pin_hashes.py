"""
Schreibt die SHA-256-Hashes der mitgelieferten SWFs (swf/*.swf) in games.json.

Aufruf (im Repo-Ordner):  python pin_hashes.py
Danach games.json + swf/ committen. Nur so gepinnte Dateien startet der Launcher.
"""
import json
import sys
from pathlib import Path

import ltl_core as core

here = Path(__file__).resolve().parent
target = here / "games.json"
manifest = json.loads(target.read_text("utf-8")) if target.exists() else json.loads(json.dumps(core.DEFAULT_MANIFEST))
core.validate_manifest(manifest)

missing = []
for g in manifest["games"]:
    f = g.get("file")
    p = here / f if f else None
    if p and p.is_file():
        if not core.is_swf(p):
            sys.exit(f"FEHLER: {f} ist keine SWF-Datei.")
        old, g["sha256"] = g.get("sha256"), core.sha256_file(p)
        mark = "unverändert" if old == g["sha256"] else ("NEU" if not old else "GEÄNDERT")
        print(f"{g['id']:16} {g['sha256']}  {f}  [{mark}]")
    else:
        missing.append(g["id"])
        print(f"{g['id']:16} (keine Datei {f or '-'} – Hash bleibt {g.get('sha256') or 'leer'})")

target.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", "utf-8")
print(f"\ngames.json geschrieben.")
if missing:
    print("Ohne mitgelieferte Datei:", ", ".join(missing),
          "\n→ werden von der URL geladen (Hash per 'Einstellungen > Hashes exportieren' ermitteln).")

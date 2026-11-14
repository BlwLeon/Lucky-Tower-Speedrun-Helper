"""
Writes the SHA-256 hashes of the bundled SWFs (swf/*.swf) into games.json.

Usage (in the repository folder):  python pin_hashes.py
Then commit games.json + swf/. The launcher only starts pinned files.
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
            sys.exit(f"ERROR: {f} is not a SWF file.")
        old, g["sha256"] = g.get("sha256"), core.sha256_file(p)
        mark = "unchanged" if old == g["sha256"] else ("NEW" if not old else "CHANGED")
        print(f"{g['id']:16} {g['sha256']}  {f}  [{mark}]")
    else:
        missing.append(g["id"])
        print(f"{g['id']:16} (no file {f or '-'} – hash stays {g.get('sha256') or 'empty'})")

target.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", "utf-8")
print("\ngames.json written.")
if missing:
    print("Not bundled:", ", ".join(missing),
          "\n-> downloaded from their URL (get the hash via developer mode: Settings > Export hashes).")

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
_check = json.loads(json.dumps(manifest))  # Prüfung an einer Kopie (keine Zusatzfelder speichern)
_mod = (_check.get("ltu_mod") or {}).get("mod")
if _mod is not None and not _mod.get("sha256"):
    _mod["sha256"] = "0" * 64  # wird gleich berechnet
core.validate_manifest(_check)
if _check.get("ltu_mod"):
    core.validate_ltu_mod(_check["ltu_mod"])
for g in manifest.get("practice", []):
    g.pop("practice", None)
for g in manifest["games"]:
    g.pop("practice", None)

missing = []
for g in manifest["games"] + manifest.get("practice", []):
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

mod = (manifest.get("ltu_mod") or {}).get("mod")
if mod:
    p = here / mod["file"]
    if not p.is_file():
        sys.exit(f"ERROR: {mod['file']} (LTU speedrun mod) is missing.")
    if p.read_bytes()[:2] != b"MZ":
        sys.exit(f"ERROR: {mod['file']} is not a DLL.")
    old, mod["sha256"] = mod.get("sha256"), core.sha256_file(p)
    mark = "unchanged" if old == mod["sha256"] else ("NEW" if not old else "CHANGED")
    print(f"{'ltu_mod':16} {mod['sha256']}  {mod['file']}  [{mark}]")

target.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", "utf-8")
print("\ngames.json written.")
if missing:
    print("Not bundled:", ", ".join(missing),
          "\n-> downloaded from their URL (get the hash via developer mode: Settings > Export hashes).")

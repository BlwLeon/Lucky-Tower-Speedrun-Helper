# swf/

Approved game files. Their SHA-256 hashes are pinned in [`../games.json`](../games.json).

| File | Category | Source |
|---|---|---|
| `lt2_qms.swf` | Lucky Tower 2 – Glitch (QMS) | Community patch, formerly speedrun.com resource `qp84z.swf` |
| `lt2_glitchless.swf` | Lucky Tower 2 – Glitchless | Unpatched original from Flashpoint (`localflash/lucky-tower-2/lucky tower 2.swf`) |
| `lt1.swf` *(optional)* | Lucky Tower | Newgrounds release. If missing, it is downloaded from Newgrounds. |

After changing any file, run `python pin_hashes.py` and commit `games.json` together with the SWF.

The game files are © Studio Seufz and are not covered by the repository's MIT license.

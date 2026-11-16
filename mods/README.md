# mods/

| File | Purpose | Source |
|---|---|---|
| `LTUSpeedrunMod.dll` | LTU Speedrun Mod 1.0.1: BepInEx 5 plugin for Lucky Tower Ultimate, **required for top 3 runs** | [MadMouse101/LTUSpeedrunMod](https://github.com/MadMouse101/LTUSpeedrunMod) (MIT, see `LICENSE-LTUSpeedrunMod.txt`) |

The launcher installs it with **Lucky Tower Ultimate → INSTALL / REPAIR SPEEDRUN MOD** into `BepInEx/plugins/`. BepInEx 5.4.23.5 and the BepInEx ConfigurationManager 18.4.1 (F1 menu, needed to use the mod's settings) are downloaded from their official GitHub releases and verified by SHA-256.

After replacing the DLL, run `python pin_hashes.py` and commit `games.json` together with the DLL.

# Lucky Tower Speedrun Helper

Official speedrun launcher for the **Lucky Tower** series, maintained by the moderators of the
[Lucky Tower speedrun.com board](https://www.speedrun.com/series/Lucky_Tower_Series).

It launches **only the game versions approved for runs**. Every Flash file is checked by SHA-256 hash before it starts,
and the Flash games run in a fixed version of [Ruffle](https://github.com/ruffle-rs/ruffle).

![Main menu](docs/preview_main.png)

> **Status: test version (v0.1).** The user interface is currently in German.

## Supported games

| Game | Version used | Runs in |
|---|---|---|
| Lucky Tower | Official Newgrounds release (downloaded on first start) | Ruffle |
| Lucky Tower 2 – Glitch (QMS) | Community patch `swf/lt2_qms.swf` (bundled) | Ruffle |
| Lucky Tower 2 – Glitchless | Unpatched original from Flashpoint `swf/lt2_glitchless.swf` (bundled) | Ruffle |
| Lucky Tower Ultimate | Your Steam installation (App 1700270) | Steam |

## Features

- **Hash-locked versions**: The SHA-256 of every approved SWF is pinned in [`games.json`](games.json). Files that do not match are refused.
- **Pinned Ruffle**: The Ruffle desktop build named in `games.json` (`ruffle_tag`) is downloaded automatically from GitHub, so every runner uses the same emulator version.
- **Steam detection** for Lucky Tower Ultimate across all Steam library folders. If the game is not installed, the launcher opens the store page.
- **Launch log** (`launch_log.jsonl`): Each start records time, game, hash and Ruffle version, so moderators have something to check during verification.
- **Status bar**: Shows whether the game is running and the session time, and reports Ruffle errors with Ruffle's own output.
- **Diagnostics**: Errors are written to `crash.log`, clicks to `session.log`. If the UI freezes for more than 10 s, a thread dump goes to `crash_native.log`.
- Uses only the Python standard library.

## Usage

**Windows EXE:** Download `LuckyTowerLauncher.exe` from the releases (once published) and run it.

**From source** (Python 3.9+; on Linux you may need `sudo apt install python3-tk`):

```
git clone https://github.com/BlwLeon/Lucky-Tower-Speedrun-Helper
cd Lucky-Tower-Speedrun-Helper
python launcher.py
```

### Build the EXE yourself

- Windows: `build_windows.bat` → `dist\LuckyTowerLauncher.exe`
- macOS / Linux: `./build.sh` → `dist/LuckyTowerLauncher`

Both scripts use PyInstaller and bundle `swf/` and `games.json` into the executable.

## For moderators

### Approving a new or changed SWF

1. Put the file into `swf/` (e.g. `swf/lt2_qms.swf`).
2. Run `python pin_hashes.py`. It writes the new SHA-256 values into `games.json`.
3. Commit `swf/` and `games.json`, then build a new release.

For downloaded games (Lucky Tower 1), use **Einstellungen → Hashes exportieren** in the launcher. It downloads everything, hashes it and writes `games_pinned.json`, including the current Ruffle version.

### Updating without a new build

Set `"manifest_url"` in `settings.json` (in the data folder) to the raw URL of `games.json` in this repository.
The launcher then loads the current manifest on every start.

Manifest lookup order: `manifest_url` → `games.json` next to the EXE → bundled `games.json` → data folder → built-in default.

### Manifest format

```json
{
  "manifest_version": 1,
  "ruffle_tag": "nightly-2026-11-14",
  "games": [
    {
      "id": "lt2_glitchless",
      "title": "Lucky Tower 2",
      "variant": "Glitchless",
      "label": "GLITCHLESS",
      "file": "swf/lt2_glitchless.swf",
      "url": null,
      "sha256": "0c455e25e19056397bb29d31b4701d44da95402b74779e86885f86646454574a",
      "ruffle_args": [],
      "source_note": "Unpatched original from BlueMaxima's Flashpoint"
    }
  ]
}
```

- `file`: bundled file, relative to the launcher.
- `url`: download source, used only if `file` is missing. At least one of `file` and `url` must be set.
- Entries with the same `title` are grouped on one page, one button each.
- `ruffle_args` are passed to Ruffle, for example to enforce rendering settings for runs.

## Data folder

| OS | Path |
|---|---|
| Windows | `%LOCALAPPDATA%\LuckyTowerLauncher` |
| macOS | `~/Library/Application Support/LuckyTowerLauncher` |
| Linux | `~/.local/share/LuckyTowerLauncher` |

It contains `ruffle/`, a download cache in `games/`, `settings.json`, `launch_log.jsonl`, `session.log`, `crash.log` and `logs/` with Ruffle output.

## Tests

```
python tests/test_flow.py
```

This end-to-end test runs on Linux and macOS. It uses a local HTTP server and a Tk mock to cover the Ruffle install, hash checks, tampered files, empty or broken SWFs, Ruffle errors, bundled files and `pin_hashes.py`.

## Limitations

The hash check makes sure runners start the approved files through the official launcher. It is not tamper-proof against someone who modifies the launcher itself. It complements video verification and does not replace it.

## Credits & license

- Lucky Tower, Lucky Tower 2 and Lucky Tower Ultimate © Studio Seufz. The SWF files in `swf/` belong to their respective owners and are **not** covered by this repository's license. They are included only so runners can play the versions approved for the leaderboard.
- Flash emulation by [Ruffle](https://github.com/ruffle-rs/ruffle) (MIT / Apache-2.0), downloaded at runtime.
- Launcher code: [MIT License](LICENSE).

"""
Lucky Tower Launcher – Kernlogik (ohne GUI).

Kümmert sich um:
  * Manifest der offiziell zugelassenen Spielversionen (SWF-Quellen + SHA-256)
  * Download / Cache / Hash-Prüfung der SWFs
  * Installation einer passenden Ruffle-Desktop-Version von GitHub
  * Erkennung von Lucky Tower Ultimate über Steam
  * Launch-Log für Verifikationszwecke

Nur Python-Standardbibliothek.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import webbrowser
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from ltl_i18n import _

APP_NAME = "LuckyTowerLauncher"
APP_VERSION = "1.2.1"
USER_AGENT = f"{APP_NAME}/{APP_VERSION} (+https://www.speedrun.com/series/Lucky_Tower_Series)"

RUFFLE_REPO = "ruffle-rs/ruffle"
# Einzige Quelle, aus der der offizielle Modus ein neueres Manifest übernimmt
OFFICIAL_MANIFEST_URL = "https://raw.githubusercontent.com/BlwLeon/Lucky-Tower-Speedrun-Helper/main/games.json"
LTU_STEAM_APPID = "1700270"

Progress = Callable[[str, Optional[float]], None]  # (text, 0..1 oder None)

# --------------------------------------------------------------------------
# Manifest der offiziellen Versionen
# --------------------------------------------------------------------------
# sha256 = None  -> Hash ist (noch) nicht festgeschrieben. Der Launcher merkt
#                   sich dann den Hash des ersten Downloads ("trust on first
#                   use") und meldet jede spätere Abweichung.
# sha256 = "..." -> Nur exakt diese Datei darf gestartet werden.
#
# Moderatoren können die Hashes per "Einstellungen > Hashes kopieren"
# auslesen und hier (oder in einer games.json / manifest_url) eintragen.
DEFAULT_MANIFEST: dict = {
    "manifest_version": 1,
    "ruffle_tag": "nightly-2026-11-14",
    "ruffle_sha256": {
        "windows-x86_64": "d1b8bcf513075938a27c92bac34c7625e95b5dadc2652e19f1da46397046c235"
    },
    "ruffle_mirror": {
        "windows-x86_64": "https://github.com/BlwLeon/Lucky-Tower-Speedrun-Helper/releases/download/v1.0.0/ruffle-nightly-2026_11_14-windows-x86_64.zip"
    },
    "games": [
        {
            "id": "lt1",
            "title": "Lucky Tower",
            "variant": "Official",
            "label": "PLAY",
            "file": "swf/lt1.swf",
            "url": "http://uploads.ungrounded.net/551000/551891_lucky_towa_NGFINALcs3.swf",
            "sha256": "a74be05574ffe4755ad188a1ea79ca82e622af39d0a461ec978fe8ae86cb0821",
            "ruffle_args": [],
            "source_note": "Official Newgrounds release (downloaded on first start unless swf/lt1.swf is present)"
        },
        {
            "id": "lt2_qms",
            "title": "Lucky Tower 2",
            "variant": "Glitch (QMS)",
            "label": "GLITCH (QMS)",
            "file": "swf/lt2_qms.swf",
            "url": "https://www.speedrun.com/static/resource/qp84z.swf?v=7371456",
            "sha256": "cf4d70d0bff592d61d1521e8174742ee27c0aee2abeef2c6f0e8b1c03f16961e",
            "ruffle_args": [],
            "source_note": "Community patch for the glitched categories, originally hosted as speedrun.com resource qp84z.swf"
        },
        {
            "id": "lt2_glitchless",
            "title": "Lucky Tower 2",
            "variant": "Glitchless",
            "label": "GLITCHLESS",
            "file": "swf/lt2_glitchless.swf",
            "url": None,
            "sha256": "0c455e25e19056397bb29d31b4701d44da95402b74779e86885f86646454574a",
            "ruffle_args": [],
            "source_note": "Unpatched original from BlueMaxima's Flashpoint (localflash/lucky-tower-2/lucky tower 2.swf)"
        }
    ],
    "practice": [
        {
            "id": "lt1_practice",
            "title": "Lucky Tower",
            "variant": "Practice",
            "label": "PRACTICE",
            "file": "swf/lt1_practice.swf",
            "url": None,
            "sha256": "6a6e973e36b9ddb498583e2374f205a9f1cbda0586b19afd1c8d9efefbc73a89",
            "ruffle_args": [],
            "source_note": "Practice build with debug bar (room warps, QoL). Not allowed for runs."
        },
        {
            "id": "lt2_practice",
            "title": "Lucky Tower 2",
            "variant": "Practice",
            "label": "PRACTICE",
            "file": "swf/lt2_practice.swf",
            "url": None,
            "sha256": "fdee2ca6875eceddeebd1c4bc7be05e621c68fd92760f33c44040d423838c04e",
            "ruffle_args": [],
            "source_note": "Practice build (room warps, QoL). Not allowed for runs."
        }
    ],
    "ltu_mod": {
        "bepinex": {
            "version": "5.4.23.5",
            "url": "https://github.com/BepInEx/BepInEx/releases/download/v5.4.23.5/BepInEx_win_x64_5.4.23.5.zip",
            "sha256": "82f9878551030f54657792c0740d9d51a09500eeae1fba21106b0c441e6732c4"
        },
        "mod": {
            "name": "LTU Speedrun Mod",
            "version": "1.0.1",
            "file": "mods/LTUSpeedrunMod.dll",
            "sha256": "e2e73fb6a46fd44eca7e4f92c6498fa57f2b54cb94e9c9ef3bf7c9a88d83318a",
            "source": "https://github.com/MadMouse101/LTUSpeedrunMod"
        },
        "plugins": [
            {
                "name": "ConfigurationManager",
                "version": "18.4.1",
                "url": "https://github.com/BepInEx/BepInEx.ConfigurationManager/releases/download/v18.4.1/BepInEx.ConfigurationManager_BepInEx5_v18.4.1.zip",
                "sha256": "9eb19791508a2acb973dfb2bcd196c631fb53cf041c462d69d889e515115aa53",
                "check": "BepInEx/plugins/ConfigurationManager/ConfigurationManager.dll",
                "source": "https://github.com/BepInEx/BepInEx.ConfigurationManager"
            }
        ]
    }
}


# --------------------------------------------------------------------------
# Pfade & Einstellungen
# --------------------------------------------------------------------------
def data_dir() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    d = base / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def resource_dir() -> Path:
    """Ordner mit mitgelieferten Dateien (swf/, games.json). In der PyInstaller-EXE
    ist das das entpackte Bundle (sys._MEIPASS), sonst der Skriptordner."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def app_dir() -> Path:
    """Ordner der EXE bzw. des Skripts (für eine mitgelieferte games.json)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


@dataclass
class Settings:
    manifest_url: Optional[str] = None  # nur Entwicklermodus
    ruffle_tag_override: Optional[str] = None  # nur Entwicklermodus
    language: str = "en"
    fullscreen: bool = False
    extra: dict = field(default_factory=dict)

    @classmethod
    def load(cls, root: Path) -> "Settings":
        p = root / "settings.json"
        if p.exists():
            try:
                raw = json.loads(p.read_text("utf-8"))
                return cls(
                    manifest_url=raw.get("manifest_url"),
                    ruffle_tag_override=raw.get("ruffle_tag_override"),
                    language=raw.get("language") if raw.get("language") in ("en", "de") else "en",
                    fullscreen=raw.get("fullscreen") is True,
                    extra=raw.get("extra", {}),
                )
            except (OSError, ValueError):
                pass
        s = cls()
        s.save(root)
        return s

    def save(self, root: Path) -> None:
        (root / "settings.json").write_text(
            json.dumps(
                {
                    "manifest_url": self.manifest_url,
                    "ruffle_tag_override": self.ruffle_tag_override,
                    "language": self.language,
                    "fullscreen": self.fullscreen,
                    "extra": self.extra,
                },
                indent=2,
            ),
            "utf-8",
        )


# --------------------------------------------------------------------------
# HTTP-Helfer
# --------------------------------------------------------------------------
def _request(url: str, accept: Optional[str] = None) -> urllib.request.Request:
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    return urllib.request.Request(url, headers=headers)


def http_json(url: str, timeout: float = 20) -> object:
    with urllib.request.urlopen(_request(url, "application/json"), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def http_download(url: str, dest: Path, progress: Optional[Progress] = None,
                  label: str = "Download", timeout: float = 60) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(_request(url), timeout=timeout) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(64 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if progress:
                frac = (done / total) if total else None
                progress(f"{label}: {done / 1_048_576:.1f} MB", frac)
    os.replace(tmp, dest)
    return dest


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_swf(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(3) in (b"FWS", b"CWS", b"ZWS")
    except OSError:
        return False


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------
def validate_manifest(m: object) -> dict:
    """Prüft das Manifest. Practice-Versionen stehen in einer eigenen Liste "practice",
    damit ältere Launcher (≤ 1.0.1), die das Online-Manifest laden, sie ignorieren."""
    if not isinstance(m, dict) or not isinstance(m.get("games"), list):
        raise ValueError("Manifest has no 'games' list")
    practice = m.setdefault("practice", [])
    if not isinstance(practice, list):
        raise ValueError("'practice' must be a list")
    for g in practice:
        if isinstance(g, dict):
            g["practice"] = True
            g.setdefault("variant", "Practice")
            g.setdefault("label", "PRACTICE")
    for g in m["games"]:
        if isinstance(g, dict):
            g["practice"] = False
    seen: set[str] = set()
    for g in m["games"] + practice:
        if not isinstance(g, dict):
            raise ValueError(f"Invalid manifest entry: {g!r}")
        for key in ("id", "title"):
            if not isinstance(g.get(key), str) or not g[key]:
                raise ValueError(f"Manifest entry without '{key}': {g!r}")
        if not g.get("url") and not g.get("file"):
            raise ValueError(f"Manifest entry {g['id']} needs 'file' or 'url'")
        if g.get("file") and (Path(g["file"]).is_absolute() or ".." in Path(g["file"]).parts):
            raise ValueError(f"'file' must be a relative path inside the launcher folder: {g['file']!r}")
        g.setdefault("url", None)
        if not re.fullmatch(r"[a-z0-9_]+", g["id"]):
            raise ValueError(f"Invalid game id: {g['id']!r}")
        sha = g.get("sha256")
        if sha is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", str(sha)):
            raise ValueError(f"Invalid SHA-256 for {g['id']}")
        g.setdefault("variant", "")
        g.setdefault("label", g["variant"].upper() or "PLAY")
        g.setdefault("ruffle_args", [])
        if g["id"] in seen:
            raise ValueError(f"Duplicate game id: {g['id']!r}")
        seen.add(g["id"])
    return m


class NotApproved(RuntimeError):
    """Datei oder Ruffle-Version ist nicht offiziell freigegeben."""


def check_official(m: dict) -> dict:
    """Im offiziellen Modus muss jede Version per SHA-256 festgelegt sein."""
    if not m.get("ruffle_tag"):
        raise ValueError("Official manifest without pinned Ruffle version (ruffle_tag)")
    for g in m["games"]:  # Practice-Versionen dürfen ungepinnt sein (nicht für Runs zugelassen)
        if not g.get("sha256"):
            raise ValueError(f"Official manifest: {g['id']} has no pinned SHA-256")
    pins = m.get("ruffle_sha256") or {}
    if not isinstance(pins, dict) or any(not re.fullmatch(r"[0-9a-fA-F]{64}", str(v)) for v in pins.values()):
        raise ValueError("Invalid 'ruffle_sha256'")
    mod = m.get("ltu_mod")
    if mod is not None:
        validate_ltu_mod(mod)
    mirrors = m.get("ruffle_mirror") or {}
    if not isinstance(mirrors, dict) or any(not str(v).startswith("https://") for v in mirrors.values()):
        raise ValueError("Invalid 'ruffle_mirror' (https URLs only)")
    return m


def load_official_manifest(log: Callable[[str], None] = print) -> tuple[dict, str]:
    """Offizieller Modus: nur das mitgelieferte Manifest (in der EXE eingebaut) bzw. das Default im Code.
    Lokale games.json-Dateien, settings.json und Overrides werden ignoriert."""
    p = resource_dir() / "games.json"
    if p.exists():
        try:
            return check_official(validate_manifest(json.loads(p.read_text("utf-8")))), "official (built-in)"
        except Exception as e:  # noqa: BLE001
            log(f"Built-in manifest invalid, using default: {e}")
    return check_official(validate_manifest(json.loads(json.dumps(DEFAULT_MANIFEST)))), "official (default)"


def fetch_remote_official(timeout: float = 6) -> dict:
    """Neueres Manifest aus dem offiziellen Repo (nur gültig, wenn vollständig gepinnt)."""
    return check_official(validate_manifest(http_json(OFFICIAL_MANIFEST_URL, timeout=timeout)))


def load_manifest(root: Path, settings: Settings, log: Callable[[str], None] = print) -> tuple[dict, str]:
    """NUR Entwicklermodus. Reihenfolge: manifest_url (remote, wird gecacht) > games.json neben der EXE
    > games.json im Datenordner > eingebautes Default-Manifest."""
    cache = root / "manifest_cache.json"
    if settings.manifest_url:
        try:
            m = validate_manifest(http_json(settings.manifest_url))
            cache.write_text(json.dumps(m, indent=2), "utf-8")
            return m, f"remote ({settings.manifest_url})"
        except Exception as e:  # noqa: BLE001
            log(f"Remote manifest could not be loaded: {e}")
            if cache.exists():
                try:
                    return validate_manifest(json.loads(cache.read_text("utf-8"))), "remote (Cache)"
                except Exception as e2:  # noqa: BLE001
                    log(f"Manifest cache broken: {e2}")
    cands = []
    for c in (app_dir() / "games.json", resource_dir() / "games.json", root / "games.json"):
        if c not in cands:
            cands.append(c)
    for cand in cands:
        if cand.exists():
            try:
                return validate_manifest(json.loads(cand.read_text("utf-8"))), str(cand)
            except Exception as e:  # noqa: BLE001
                log(f"{cand} invalid: {e}")
    return validate_manifest(json.loads(json.dumps(DEFAULT_MANIFEST))), "built-in"


# --------------------------------------------------------------------------
# Ruffle
# --------------------------------------------------------------------------
def platform_key() -> tuple[str, str]:
    """(os, arch) in Ruffle-Asset-Schreibweise."""
    if sys.platform.startswith("win"):
        osname = "windows"
    elif sys.platform == "darwin":
        osname = "macos"
    else:
        osname = "linux"
    m = platform.machine().lower()
    arch = "arm64" if m in ("arm64", "aarch64") else "x86_64"
    return osname, arch


def pick_ruffle_asset(assets: list[dict], osname: str, arch: str) -> Optional[dict]:
    """Wählt aus den Release-Assets den Desktop-Build für diese Plattform."""
    aliases = {"arm64": ("arm64", "aarch64"), "x86_64": ("x86_64", "amd64", "x64")}.get(arch, (arch,))

    def has_arch(n: str, al=aliases) -> bool:
        return any(x in n for x in al)

    best, best_score = None, -1
    for a in assets:
        name = a.get("name", "").lower()
        if not name.startswith("ruffle") or "web" in name or "extension" in name:
            continue
        if osname not in name:
            continue
        score = 0
        if osname == "windows":
            if not name.endswith(".zip"):
                continue  # .msi ignorieren – wir wollen portabel bleiben
            if has_arch(name):
                score += 10
            elif arch == "arm64" and "x86_64" in name:
                score += 1  # Windows-ARM kann x64 emulieren
            else:
                continue
        elif osname == "macos":
            if not (name.endswith(".tar.gz") or name.endswith(".dmg") or name.endswith(".zip")):
                continue
            score += 10 if "universal" in name else (8 if has_arch(name) else 0)
            if score == 0:
                continue
            if name.endswith(".tar.gz"):
                score += 1
        else:
            if not name.endswith(".tar.gz"):
                continue
            if has_arch(name):
                score += 10
            else:
                continue
        if score > best_score:
            best, best_score = a, score
    return best


def platform_id() -> str:
    o, a = platform_key()
    return f"{o}-{a}"


def find_ruffle_release(tag: Optional[str], osname: str, arch: str) -> tuple[str, dict]:
    if tag:
        rel = http_json(f"https://api.github.com/repos/{RUFFLE_REPO}/releases/tags/{tag}")
        asset = pick_ruffle_asset(rel.get("assets", []), osname, arch)
        if not asset:
            raise RuntimeError(_("Ruffle {tag} has no desktop build for {os}/{arch}", tag=tag, os=osname, arch=arch))
        return rel["tag_name"], asset
    releases = http_json(f"https://api.github.com/repos/{RUFFLE_REPO}/releases?per_page=15")
    for rel in releases:
        if rel.get("draft"):
            continue
        asset = pick_ruffle_asset(rel.get("assets", []), osname, arch)
        if asset:
            return rel["tag_name"], asset
    raise RuntimeError(_("No Ruffle desktop build found for {os}/{arch}", os=osname, arch=arch))


def _find_ruffle_exe(folder: Path) -> Optional[Path]:
    names = ("ruffle.exe", "ruffle_desktop.exe") if sys.platform.startswith("win") else ("ruffle", "ruffle_desktop")
    candidates = []
    for p in folder.rglob("*"):
        if p.is_file() and p.name.lower() in names:
            candidates.append(p)
    if not candidates:
        return None
    # macOS: bevorzugt die Binary im .app-Bundle
    candidates.sort(key=lambda p: (".app/Contents/MacOS" not in p.as_posix(), len(p.parts)))
    return candidates[0]


def _safe_extract(archive: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    name = archive.name.lower()
    if name.endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            for member in z.namelist():
                dest = (target / member).resolve()
                if not str(dest).startswith(str(target.resolve())):
                    raise RuntimeError(_("Unsafe path in archive: {name}", name=member))
            z.extractall(target)
    elif name.endswith(".tar.gz") or name.endswith(".tgz"):
        with tarfile.open(archive, "r:gz") as t:
            if hasattr(tarfile, "data_filter"):
                t.extractall(target, filter="data")
            else:
                for m in t.getmembers():
                    dest = (target / m.name).resolve()
                    if not str(dest).startswith(str(target.resolve())) or m.issym() or m.islnk():
                        raise RuntimeError(_("Unsafe entry in archive: {name}", name=m.name))
                t.extractall(target)
    elif name.endswith(".dmg") and sys.platform == "darwin":
        mnt = Path(tempfile.mkdtemp(prefix="ltl_dmg_"))
        subprocess.run(["hdiutil", "attach", "-nobrowse", "-readonly", "-mountpoint", str(mnt), str(archive)],
                       check=True, capture_output=True)
        try:
            for app in mnt.glob("*.app"):
                shutil.copytree(app, target / app.name, symlinks=True)
        finally:
            subprocess.run(["hdiutil", "detach", str(mnt)], capture_output=True)
    else:
        raise RuntimeError(_("Unknown archive format: {name}", name=archive.name))


class RuffleManager:
    def __init__(self, root: Path):
        self.root = root / "ruffle"
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_file = self.root / "installed.json"

    def installed(self) -> Optional[dict]:
        if not self.state_file.exists():
            return None
        try:
            st = json.loads(self.state_file.read_text("utf-8"))
            if Path(st["exe"]).exists():
                return st
        except (OSError, ValueError, KeyError):
            pass
        return None

    def verify(self, st: dict, pins: Optional[dict]) -> Optional[bool]:
        """True/False wenn für diese Plattform ein Fingerabdruck festgelegt ist, sonst None."""
        pin = (pins or {}).get(platform_id())
        if not pin:
            return None
        try:
            return sha256_file(Path(st["exe"])) == pin.lower()
        except OSError:
            return False

    def ensure(self, wanted_tag: Optional[str], progress: Progress, force_check: bool = False,
               pins: Optional[dict] = None, reinstall: bool = False, mirrors: Optional[dict] = None) -> dict:
        """Stellt sicher, dass Ruffle installiert ist.
        - Gepinnter Tag: genau diese Version (bei pins zusätzlich per SHA-256 der Binary geprüft).
        - Kein Tag (nur Entwicklermodus): vorhandene Version reicht; force_check sucht nach Updates."""
        cur = self.installed()
        if cur and not reinstall:
            if wanted_tag and cur["tag"] == wanted_tag:
                ok = self.verify(cur, pins)
                if ok is not False:
                    return cur
                progress(_("Ruffle was modified – reinstalling …"), None)
            elif not wanted_tag and not force_check:
                return cur
        osname, arch = platform_key()
        progress(_("Looking for Ruffle release on GitHub …"), None)
        try:
            tag, asset = find_ruffle_release(wanted_tag, osname, arch)
        except Exception:  # noqa: BLE001
            # Ruffle-Release nicht (mehr) verfügbar: Spiegel aus dem Launcher-Release nutzen.
            # Nur mit festgelegtem Fingerabdruck – die Binary wird danach geprüft.
            mirror = (mirrors or {}).get(platform_id())
            if not (wanted_tag and mirror and (pins or {}).get(platform_id())):
                raise
            progress(_("Ruffle release not reachable – using mirror …"), None)
            tag, asset = wanted_tag, {"name": mirror.rsplit("/", 1)[-1], "browser_download_url": mirror}
        if cur and cur["tag"] == tag and not reinstall and self.verify(cur, pins) is not False:
            progress(_("Ruffle {tag} is up to date.", tag=tag), 1.0)
            return cur
        with tempfile.TemporaryDirectory(prefix="ltl_") as td:
            arc = Path(td) / asset["name"]
            http_download(asset["browser_download_url"], arc, progress, f"Ruffle {tag}")
            digest = str(asset.get("digest") or "")
            if digest.startswith("sha256:") and sha256_file(arc) != digest[7:].lower():
                raise NotApproved(_("Ruffle download does not match GitHub's checksum."))
            progress(_("Extracting Ruffle …"), None)
            dest = self.root / re.sub(r"[^A-Za-z0-9._-]", "_", tag)
            if dest.exists():
                shutil.rmtree(dest)
            _safe_extract(arc, dest)
        exe = _find_ruffle_exe(dest)
        if not exe:
            raise RuntimeError(_("Ruffle binary not found after extracting"))
        if not sys.platform.startswith("win"):
            exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        st = {"tag": tag, "asset": asset["name"], "exe": str(exe), "installed_at": int(time.time())}
        if self.verify(st, pins) is False:
            raise NotApproved(_("Ruffle {tag} ({platform}) does not match the official fingerprint.", tag=tag, platform=platform_id()))
        self.state_file.write_text(json.dumps(st, indent=2), "utf-8")
        # Alte Versionen aufräumen
        for d in self.root.iterdir():
            if d.is_dir() and d != dest:
                shutil.rmtree(d, ignore_errors=True)
        progress(_("Ruffle {tag} installed.", tag=tag), 1.0)
        return st


# --------------------------------------------------------------------------
# SWF-Verwaltung
# --------------------------------------------------------------------------
def _game_name(game: dict) -> str:
    return f"{game['title']} {game.get('variant') or ''}".strip()


class HashMismatch(Exception):
    pass


class SwfManager:
    def __init__(self, root: Path, strict: bool = True):
        """strict=True (offizieller Modus): Es zählen ausschließlich die Hashes aus dem Manifest.
        strict=False (Entwicklermodus): ungepinnte Dateien werden beim ersten Laden gemerkt."""
        self.strict = strict
        self.root = root / "games"
        self.root.mkdir(parents=True, exist_ok=True)
        self.tofu_file = self.root / "known_hashes.json"

    def _tofu(self) -> dict:
        try:
            return json.loads(self.tofu_file.read_text("utf-8"))
        except (OSError, ValueError):
            return {}

    def _save_tofu(self, d: dict) -> None:
        self.tofu_file.write_text(json.dumps(d, indent=2), "utf-8")

    def path_for(self, game: dict) -> Path:
        """Cache-Pfad für heruntergeladene / importierte Dateien."""
        return self.root / f"{game['id']}.swf"

    @staticmethod
    def bundled_path(game: dict) -> Optional[Path]:
        """Mitgelieferte Datei (neben der EXE oder im Bundle), falls vorhanden."""
        if not game.get("file"):
            return None
        for base in (app_dir(), resource_dir()):
            p = base / game["file"]
            if p.is_file():
                return p
        return None

    def local_path(self, game: dict) -> Path:
        return self.bundled_path(game) or self.path_for(game)

    @staticmethod
    def _source_key(game: dict) -> str:
        return game.get("url") or f"file:{game.get('file')}"

    def expected_hash(self, game: dict) -> tuple[Optional[str], str]:
        """(hash, quelle) – quelle ist 'manifest', 'erster Download' oder 'keiner'."""
        if game.get("sha256"):
            return game["sha256"].lower(), "manifest"
        if self.strict or self.bundled_path(game):
            # Mitgelieferte Dateien werden nur über games.json gepinnt (pin_hashes.py)
            return None, "none"
        known = self._tofu().get(game["id"])
        if known and known.get("url") == self._source_key(game):
            return known["sha256"], "first download"
        return None, "none"

    def status(self, game: dict) -> dict:
        bundled = self.bundled_path(game)
        p = bundled or self.path_for(game)
        exp, src = self.expected_hash(game)
        if not p.exists():
            return {"cached": False, "bundled": False, "sha256": None, "expected": exp, "source": src, "ok": None}
        h = sha256_file(p)
        return {"cached": True, "bundled": bool(bundled), "sha256": h, "expected": exp, "source": src,
                "ok": (h == exp) if exp else None}

    def ensure(self, game: dict, progress: Progress, redownload: bool = False) -> tuple[Path, str, str]:
        """Gibt (pfad, sha256, verifikation) zurück. Wirft HashMismatch bei Abweichung."""
        bundled = self.bundled_path(game)
        if bundled:
            self._require_swf(bundled, _("Bundled file {file}", file=game.get("file")))
            return self._verify(game, bundled)
        p = self.path_for(game)
        if redownload or not p.exists():
            if not game.get("url"):
                raise RuntimeError(_("Bundled file is missing: {file}\nPlease download the launcher again.",
                                     file=game.get("file")))
            tmp = p.with_name(p.name + ".new")
            http_download(game["url"], tmp, progress, f"{game['title']} {game.get('variant', '')}".strip())
            if not is_swf(tmp):
                tmp.unlink(missing_ok=True)
                raise RuntimeError(_("The downloaded file is not a SWF (source blocked or changed?)"))
            os.replace(tmp, p)
        self._require_swf(p, _("Saved file {file}", file=p.name))
        return self._verify(game, p)

    @staticmethod
    def _require_swf(p: Path, what: str) -> None:
        if not is_swf(p):
            size = p.stat().st_size if p.exists() else 0
            raise RuntimeError(_("{what} is not a valid SWF ({size} bytes) – probably an incomplete download. "
                                 "Please replace it.", what=what, size=size))

    def fetch_raw(self, game: dict, progress: Progress) -> Path:
        """NUR Entwicklermodus (Hash-Export): Datei holen, ohne gegen einen Hash zu prüfen."""
        if self.strict:
            raise NotApproved(_("Only available in developer mode."))
        bundled = self.bundled_path(game)
        if bundled:
            self._require_swf(bundled, _("Bundled file {file}", file=game.get("file")))
            return bundled
        p = self.path_for(game)
        if game.get("url"):
            tmp = p.with_name(p.name + ".new")
            try:
                http_download(game["url"], tmp, progress, f"{game['title']} {game.get('variant', '')}".strip())
                os.replace(tmp, p)
            except Exception:  # noqa: BLE001 – Quelle offline: vorhandene (z. B. manuell gewählte) Datei nutzen
                if not p.exists():
                    raise
        self._require_swf(p, _("File {file}", file=p.name))
        return p

    def import_local(self, game: dict, src: Path) -> tuple[Path, str, str]:
        """Manuell gewählte SWF übernehmen (z. B. wenn die Quelle offline ist).
        Wird nur akzeptiert, wenn sie zum Hash passt (falls einer bekannt ist)."""
        if not is_swf(src):
            raise RuntimeError(_("The selected file is not a SWF."))
        exp, src_kind = self.expected_hash(game)
        if exp is None and self.strict:
            raise NotApproved(_("{game}: no officially approved version on record.", game=_game_name(game)))
        h = sha256_file(src)
        if exp and h != exp:
            raise HashMismatch(_("File does not match the official version ({src}).\nExpected: {exp}\nFound: {got}",
                                 src=_(src_kind), exp=exp, got=h))
        shutil.copyfile(src, self.path_for(game))
        return self._verify(game, self.path_for(game))

    def _verify(self, game: dict, p: Path) -> tuple[Path, str, str]:
        h = sha256_file(p)
        exp, src = self.expected_hash(game)
        if exp is None and game.get("practice"):
            return p, h, "practice"
        if exp is None and self.strict:
            raise NotApproved(_("{game}: no officially approved version on record – launch not allowed.",
                                game=_game_name(game)))
        if exp is None and self.bundled_path(game) == p:
            return p, h, "bundled, not pinned"
        if exp is None:
            t = self._tofu()
            t[game["id"]] = {"url": self._source_key(game), "sha256": h, "first_seen": int(time.time())}
            self._save_tofu(t)
            return p, h, "not pinned (hash remembered)"
        if h != exp:
            raise HashMismatch(_("SHA-256 does not match the official version!\nExpected ({src}): {exp}\nFound: {got}",
                                 src=_(src), exp=exp, got=h))
        return p, h, "verified" if src == "manifest" else "same as first download"

    def clear(self) -> None:
        """Löscht nur heruntergeladene Dateien. Festgelegte Hashes bleiben davon unberührt."""
        for f in self.root.glob("*.swf"):
            f.unlink(missing_ok=True)
        if not self.strict:
            self.tofu_file.unlink(missing_ok=True)


# --------------------------------------------------------------------------
# Steam / Lucky Tower Ultimate
# --------------------------------------------------------------------------
def steam_roots() -> list[Path]:
    roots: list[Path] = []
    if sys.platform.startswith("win"):
        try:
            import winreg  # type: ignore

            for hive, key, val in (
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
            ):
                try:
                    with winreg.OpenKey(hive, key) as k:
                        roots.append(Path(winreg.QueryValueEx(k, val)[0]))
                except OSError:
                    pass
        except ImportError:
            pass
        pf = os.environ.get("ProgramFiles(x86)") or r"C:\Program Files (x86)"
        roots.append(Path(pf) / "Steam")
    elif sys.platform == "darwin":
        roots.append(Path.home() / "Library" / "Application Support" / "Steam")
    else:
        h = Path.home()
        roots += [h / ".steam" / "steam", h / ".local" / "share" / "Steam",
                  h / ".var" / "app" / "com.valvesoftware.Steam" / "data" / "Steam",
                  h / "snap" / "steam" / "common" / ".local" / "share" / "Steam"]
    seen, out = set(), []
    for r in roots:
        try:
            key = str(r.resolve()).lower()
        except OSError:
            continue
        if key not in seen and r.exists():
            seen.add(key)
            out.append(r)
    return out


def parse_library_folders(vdf_text: str) -> list[Path]:
    paths = re.findall(r'"path"\s+"([^"]+)"', vdf_text)
    if not paths:  # sehr altes Format: "1" "D:\\SteamLibrary"
        paths = re.findall(r'^\s*"\d+"\s+"([^"]+)"', vdf_text, re.M)
    return [Path(p.replace("\\\\", "\\")) for p in paths]


def parse_acf(text: str) -> dict:
    return dict(re.findall(r'^\s*"(\w+)"\s+"([^"]*)"', text, re.M))


def find_steam_game(appid: str = LTU_STEAM_APPID) -> Optional[dict]:
    for root in steam_roots():
        libs = [root]
        vdf = root / "steamapps" / "libraryfolders.vdf"
        if vdf.exists():
            try:
                libs += parse_library_folders(vdf.read_text("utf-8", errors="replace"))
            except OSError:
                pass
        for lib in libs:
            acf = lib / "steamapps" / f"appmanifest_{appid}.acf"
            if acf.exists():
                try:
                    info = parse_acf(acf.read_text("utf-8", errors="replace"))
                except OSError:
                    info = {}
                installdir = lib / "steamapps" / "common" / info.get("installdir", "Lucky Tower Ultimate")
                return {
                    "appid": appid,
                    "name": info.get("name", "Lucky Tower Ultimate"),
                    "buildid": info.get("buildid"),
                    "path": str(installdir),
                    "installed": installdir.exists(),
                }
    return None


def open_uri(uri: str) -> None:
    if sys.platform.startswith("win"):
        os.startfile(uri)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", uri])
    else:
        try:
            subprocess.Popen(["xdg-open", uri])
        except FileNotFoundError:
            webbrowser.open(uri)


def launch_steam_game(appid: str = LTU_STEAM_APPID) -> None:
    open_uri(f"steam://rungameid/{appid}")


def open_steam_store(appid: str = LTU_STEAM_APPID) -> None:
    try:
        open_uri(f"steam://store/{appid}")
    except OSError:
        webbrowser.open(f"https://store.steampowered.com/app/{appid}/")


# --------------------------------------------------------------------------
# Lucky Tower Ultimate: Speedrun-Mod (BepInEx 5)
# --------------------------------------------------------------------------
# Manifest-Abschnitt "ltu_mod" (getrennt von "games", ältere Launcher ignorieren ihn):
#   "ltu_mod": {
#     "bepinex": {"version": "5.4.23.5", "url": "...BepInEx_win_x64_5.4.23.5.zip", "sha256": "..."},
#     "mod": {"name": "LTU Speedrun Mod", "version": "1.0.1", "file": "mods/LTUSpeedrunMod.dll", "sha256": "..."},
#     "plugins": [  # zusätzliche BepInEx-Plugins (Zip mit BepInEx/plugins/... wird in den Spielordner entpackt)
#       {"name": "ConfigurationManager", "version": "18.4.1", "url": "...zip", "sha256": "...",
#        "check": "BepInEx/plugins/ConfigurationManager/ConfigurationManager.dll"}
#     ]
#   }
MOD_DLL_NAME = "LTUSpeedrunMod.dll"


def validate_ltu_mod(mod: object) -> dict:
    if not isinstance(mod, dict):
        raise ValueError("'ltu_mod' must be an object")
    bep, dll = mod.get("bepinex"), mod.get("mod")
    if not isinstance(bep, dict) or not isinstance(dll, dict):
        raise ValueError("'ltu_mod' needs 'bepinex' and 'mod'")
    if not str(bep.get("url", "")).startswith("https://"):
        raise ValueError("'ltu_mod.bepinex.url' must be an https URL")
    f = dll.get("file")
    if not f or Path(f).is_absolute() or ".." in Path(f).parts:
        raise ValueError("'ltu_mod.mod.file' must be a relative path inside the launcher folder")
    for part, name in ((bep, "bepinex"), (dll, "mod")):
        if not re.fullmatch(r"[0-9a-fA-F]{64}", str(part.get("sha256") or "")):
            raise ValueError(f"'ltu_mod.{name}.sha256' must be pinned")
    plugins = mod.setdefault("plugins", [])
    if not isinstance(plugins, list):
        raise ValueError("'ltu_mod.plugins' must be a list")
    for p in plugins:
        if not isinstance(p, dict) or not p.get("name"):
            raise ValueError("'ltu_mod.plugins' entries need a 'name'")
        if not str(p.get("url", "")).startswith("https://"):
            raise ValueError(f"'ltu_mod.plugins.{p['name']}.url' must be an https URL")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", str(p.get("sha256") or "")):
            raise ValueError(f"'ltu_mod.plugins.{p['name']}.sha256' must be pinned")
        chk = p.get("check")
        if not chk or Path(chk).is_absolute() or ".." in Path(chk).parts or not chk.startswith("BepInEx/plugins/"):
            raise ValueError(f"'ltu_mod.plugins.{p['name']}.check' must be a path below BepInEx/plugins/")
    return mod


class ModError(RuntimeError):
    """Installation der Speedrun-Mod nicht möglich."""


class LtuModManager:
    def __init__(self, root: Path, spec: Optional[dict]):
        self.cache = root / "ltu_mod"
        self.spec = spec

    # ---- Spielordner untersuchen
    @staticmethod
    def game_info(game_dir: Path) -> dict:
        """Prüft, ob BepInEx 5 (x64, Mono) passt."""
        data_dirs = [d for d in game_dir.glob("*_Data") if d.is_dir()]
        exe = None
        for d in data_dirs:
            cand = game_dir / (d.name[:-5] + ".exe")
            if cand.exists():
                exe = cand
                break
        mono = any((d / "Managed" / "Assembly-CSharp.dll").exists() for d in data_dirs)
        il2cpp = (game_dir / "GameAssembly.dll").exists()
        arch = None
        if exe:
            try:
                with open(exe, "rb") as fh:
                    fh.seek(0x3C)
                    pe = struct.unpack("<I", fh.read(4))[0]
                    fh.seek(pe)
                    if fh.read(4) == b"PE\0\0":
                        machine = struct.unpack("<H", fh.read(2))[0]
                        arch = {0x8664: "x64", 0x14C: "x86", 0xAA64: "arm64"}.get(machine, hex(machine))
            except (OSError, struct.error):
                arch = None
        return {"exe": str(exe) if exe else None, "mono": mono and not il2cpp, "il2cpp": il2cpp, "arch": arch}

    def bundled_dll(self) -> Optional[Path]:
        if not self.spec:
            return None
        f = self.spec["mod"]["file"]
        for base in (app_dir(), resource_dir()):
            p = base / f
            if p.is_file():
                return p
        return None

    def available(self) -> bool:
        return bool(self.spec) and self.bundled_dll() is not None

    def status(self, game_dir: Path) -> dict:
        """installed: BepInEx + Mod vorhanden und Mod-DLL entspricht dem Fingerabdruck."""
        plugins = game_dir / "BepInEx" / "plugins"
        bep = (game_dir / "BepInEx" / "core" / "BepInEx.dll").exists() and (game_dir / "winhttp.dll").exists()
        mod_files = sorted(plugins.rglob(MOD_DLL_NAME)) if plugins.exists() else []
        want = (self.spec or {}).get("mod", {}).get("sha256", "").lower()
        mod_ok = bool(mod_files) and len(mod_files) == 1 and want and sha256_file(mod_files[0]) == want
        extras = (self.spec or {}).get("plugins", [])
        known = {Path(p["check"]).as_posix() for p in extras}
        missing_plugins = [p["name"] for p in extras if not (game_dir / p["check"]).is_file()]
        others = []
        if plugins.exists():
            others = sorted(rel for rel in (str(p.relative_to(plugins)).replace("\\", "/") for p in plugins.rglob("*.dll")
                                            if p.name != MOD_DLL_NAME)
                            if f"BepInEx/plugins/{rel}" not in known)
        if bep and mod_ok and not missing_plugins:
            state = "installed"
        elif bep and mod_ok:
            state = "incomplete"
        elif bep and mod_files:
            state = "modified"
        elif bep or mod_files:
            state = "incomplete"
        else:
            state = "missing"
        return {"state": state, "bepinex": bep, "mod_files": [str(p) for p in mod_files],
                "other_plugins": others, "missing_plugins": missing_plugins,
                "plugins": {p["name"]: p.get("version") for p in extras},
                "mod_version": (self.spec or {}).get("mod", {}).get("version"),
                "bepinex_version": (self.spec or {}).get("bepinex", {}).get("version")}

    # ---- Installation / Reparatur
    def _verified_zip(self, part: dict, label: str, progress: Progress) -> Path:
        want = part["sha256"].lower()
        self.cache.mkdir(parents=True, exist_ok=True)
        dest = self.cache / part["url"].rsplit("/", 1)[-1]
        if dest.exists() and sha256_file(dest) == want:
            return dest
        http_download(part["url"], dest, progress, label)
        if sha256_file(dest) != want:
            dest.unlink(missing_ok=True)
            raise NotApproved(_("{name} download does not match the official fingerprint.", name=label))
        return dest

    def _bepinex_zip(self, progress: Progress) -> Path:
        bep = self.spec["bepinex"]
        return self._verified_zip(bep, f"BepInEx {bep.get('version', '')}".strip(), progress)

    def install(self, game_dir: Path, progress: Progress) -> dict:
        if not self.spec:
            raise ModError(_("No speedrun mod is defined in the version list."))
        dll_src = self.bundled_dll()
        if not dll_src:
            raise ModError(_("The speedrun mod file is missing from the launcher. Please download the launcher again."))
        if sha256_file(dll_src) != self.spec["mod"]["sha256"].lower():
            raise NotApproved(_("The bundled speedrun mod does not match the official fingerprint."))
        info = self.game_info(game_dir)
        if not info["exe"]:
            raise ModError(_("Lucky Tower Ultimate was not found in {path}.", path=game_dir))
        if info["il2cpp"] or not info["mono"]:
            raise ModError(_("This Lucky Tower Ultimate build is not a Unity Mono game – BepInEx 5 cannot be installed. "
                             "Please contact the moderators."))
        if info["arch"] != "x64":
            raise ModError(_("Unsupported game architecture ({arch}). Please contact the moderators.",
                             arch=info["arch"] or "?"))
        zpath = self._bepinex_zip(progress)
        extra_zips = [(p, self._verified_zip(p, f"{p['name']} {p.get('version', '')}".strip(), progress))
                      for p in self.spec.get("plugins", [])]
        progress(_("Installing BepInEx …"), None)
        try:
            _safe_extract(zpath, game_dir)
            plugins = game_dir / "BepInEx" / "plugins"
            plugins.mkdir(parents=True, exist_ok=True)
            # Doppelte/alte Kopien der Mod deaktivieren (sonst lädt BepInEx evtl. zwei Versionen)
            target = plugins / MOD_DLL_NAME
            for old in plugins.rglob(MOD_DLL_NAME):
                if old != target:
                    old.rename(old.with_name(old.name + ".disabled"))
            progress(_("Installing {mod} …", mod=self.spec["mod"].get("name", "LTU Speedrun Mod")), None)
            shutil.copyfile(dll_src, target)
            for p, z in extra_zips:
                progress(_("Installing {mod} …", mod=p["name"]), None)
                check = game_dir / p["check"]
                # Alte Kopien (z. B. ConfigurationManager.dll direkt in plugins/) deaktivieren
                for old in plugins.rglob(check.name):
                    if old.resolve() != check.resolve():
                        old.rename(old.with_name(old.name + ".disabled"))
                _safe_extract(z, game_dir)
        except PermissionError as e:
            raise ModError(_("Files in the game folder are in use. Please close Lucky Tower Ultimate and try again.\n\n{e}",
                             e=e)) from e
        st = self.status(game_dir)
        if st["state"] != "installed":
            raise ModError(_("Installation could not be verified (state: {state}).", state=st["state"]))
        progress(_("Speedrun mod installed."), 1.0)
        return st


# --------------------------------------------------------------------------
# Start & Launch-Log
# --------------------------------------------------------------------------
def launch_swf(ruffle_exe: str, swf: Path, extra_args: list[str],
               log_path: Optional[Path] = None) -> subprocess.Popen:
    cmd = [ruffle_exe, *extra_args, str(swf)]
    kwargs: dict = {"cwd": str(swf.parent), "stdin": subprocess.DEVNULL}
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(log_path, "w", encoding="utf-8", errors="replace")
        kwargs["stdout"] = fh
        kwargs["stderr"] = subprocess.STDOUT
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | NEW_PROCESS_GROUP
    try:
        return subprocess.Popen(cmd, **kwargs)
    finally:
        if log_path:
            fh.close()  # der Kindprozess hat sein eigenes Handle


def tail(path: Path, lines: int = 15) -> str:
    try:
        return "\n".join(path.read_text("utf-8", errors="replace").strip().splitlines()[-lines:])
    except OSError:
        return ""


def write_launch_log(root: Path, entry: dict) -> None:
    entry = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "launcher": APP_VERSION, **entry}
    with open(root / "launch_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def open_folder(path: Path) -> None:
    open_uri(str(path))

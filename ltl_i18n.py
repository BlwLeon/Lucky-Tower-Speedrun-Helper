"""
Lucky Tower Launcher – Übersetzungen / translations.

English is the source language. German translations are looked up by the English text.
Usage:  _("Starting {name} …", name=x)
"""
from __future__ import annotations

LANGUAGES = ("en", "de")
_lang = "en"


def set_language(lang: str) -> None:
    global _lang
    _lang = lang if lang in LANGUAGES else "en"


def get_language() -> str:
    return _lang


def _(text: str, **kw) -> str:
    if _lang == "de":
        text = DE.get(text, text)
    return text.format(**kw) if kw else text


DE: dict[str, str] = {
    # ---- window / scene
    "[DEVELOPER MODE]": "[ENTWICKLERMODUS]",
    "DEVELOPER MODE – for moderators only, not valid for runs":
        "ENTWICKLERMODUS – nur für Moderatoren, nicht für Runs zugelassen",
    "DEV": "DEV",
    "Official": "Offiziell",

    # ---- main menu
    "{n} official version(s): {list}": "{n} offizielle Version(en): {list}",
    "Standard": "Standard",
    "Steam version": "Steam-Version",
    "SETTINGS": "EINSTELLUNGEN",
    "Ruffle, downloads, language": "Ruffle, Downloads, Sprache",

    # ---- game page
    "PLAY": "SPIELEN",
    "BACK": "ZURÜCK",
    "officially approved ✓ (SHA-256 {h}…)": "offiziell freigegeben ✓ (SHA-256 {h}…)",
    "SHA-256 {h}… ({src})": "SHA-256 {h}… ({src})",
    "not approved": "nicht freigegeben",
    "SHA-256 not pinned yet": "SHA-256 noch nicht festgelegt",
    "bundled": "mitgeliefert",
    "available locally": "lokal vorhanden",
    "downloaded on start": "wird beim Start geladen",
    "Source: {src}": "Quelle: {src}",
    "first download": "erster Download",

    # ---- ultimate page
    "Found: {path}": "Gefunden: {path}",
    "Build {id}": "Build {id}",
    "PLAY (STEAM)": "SPIELEN (STEAM)",
    "OPEN STEAM STORE": "IM STEAM-STORE ÖFFNEN",
    "No Steam installation of app {id} found": "Keine Steam-Installation von App {id} gefunden",
    "ULTIMATE – NOT INSTALLED": "ULTIMATE – NICHT INSTALLIERT",
    "SEARCH AGAIN": "ERNEUT SUCHEN",
    "Search Steam libraries again": "Steam-Bibliotheken neu durchsuchen",

    # ---- settings page
    "Installed: {tag}": "Installiert: {tag}",
    "none": "keins",
    "pinned: {tag}": "festgelegt: {tag}",
    "latest version": "neueste Version",
    "UPDATE RUFFLE": "RUFFLE AKTUALISIEREN",
    "EXPORT HASHES": "HASHES EXPORTIEREN",
    "Downloads all SWFs, computes SHA-256 and saves games_pinned.json (incl. Ruffle hash)":
        "Lädt alle SWFs, berechnet SHA-256 und speichert games_pinned.json (inkl. Ruffle-Fingerabdruck)",
    "RELOAD DOWNLOADS": "DOWNLOADS NEU LADEN",
    "Deletes downloaded SWFs and remembered hashes": "Löscht heruntergeladene SWFs und gemerkte Hashes",
    "OPEN DATA FOLDER": "DATENORDNER ÖFFNEN",
    "REPAIR RUFFLE": "RUFFLE REPARIEREN",
    "reinstalls the official version": "installiert die offizielle Version neu",
    "Re-downloads games – only the official versions are accepted":
        "Lädt heruntergeladene Spiele neu – es werden weiterhin nur die offiziellen Versionen akzeptiert",
    "Version list: {src}": "Versionsliste: {src}",
    "LANGUAGE: ENGLISH": "SPRACHE: DEUTSCH",
    "Switch to German / Auf Deutsch umschalten": "Auf Englisch umschalten / Switch to English",

    # ---- status / launching
    "Error – see message.": "Fehler – siehe Meldung.",
    "Error": "Fehler",
    "Starting {name} …": "Starte {name} …",
    "▶ {name} running  ·  {detail}": "▶ {name} läuft  ·  {detail}",
    "✖ {name}: Ruffle exited with an error (code {code})": "✖ {name}: Ruffle wurde mit Fehler beendet (Code {code})",
    "(no output)": "(keine Ausgabe)",
    "Ruffle error": "Ruffle-Fehler",
    "{name} could not be started (exit code {code}).\n\nLast Ruffle output:\n{out}\n\nLog: {log}":
        "{name} konnte nicht gestartet werden (Exit-Code {code}).\n\nLetzte Ruffle-Ausgabe:\n{out}\n\nLog: {log}",
    "▶ {other} running  ·  {name} closed": "▶ {other} läuft  ·  {name} beendet",
    "{name} closed  ·  play time {m}:{s} min": "{name} beendet  ·  Spielzeit {m}:{s} min",
    "{msg}\n\nThis file is not an approved version and will not be started.":
        "{msg}\n\nDiese Datei ist keine zugelassene Version und wird nicht gestartet.",
    "Version mismatch": "Version stimmt nicht",
    "{msg}\n\nThe local file was modified or is outdated.\nDownload it again from the official source now?":
        "{msg}\n\nDie lokale Datei wurde verändert oder ist veraltet.\nJetzt von der offiziellen Quelle neu herunterladen?",
    "Download failed": "Download fehlgeschlagen",
    "The official source is not reachable:\n{msg}\n\nSelect a locally saved SWF instead?\n"
    "(It is checked against the official hash.)":
        "Die offizielle Quelle ist nicht erreichbar:\n{msg}\n\nStattdessen eine lokal gespeicherte SWF auswählen?\n"
        "(Sie wird gegen den offiziellen Hash geprüft.)",
    "{title} – choose SWF": "{title} – SWF wählen",
    "All files": "Alle Dateien",
    "Starting Lucky Tower Ultimate via Steam …": "Lucky Tower Ultimate wird über Steam gestartet …",
    "Steam could not be opened:\n{e}": "Steam konnte nicht geöffnet werden:\n{e}",
    "Ruffle {tag} reinstalled and verified.": "Ruffle {tag} neu installiert und geprüft.",
    "Ruffle {tag} ready.": "Ruffle {tag} bereit.",
    "Delete all downloaded SWFs and remembered hashes?": "Alle heruntergeladenen SWFs und gemerkten Hashes löschen?",
    "Delete downloaded games and download them again on next start?\n(The official versions stay pinned.)":
        "Heruntergeladene Spiele löschen und beim nächsten Start neu laden?\n(Die offiziellen Versionen bleiben festgelegt.)",
    "Reload downloads": "Downloads neu laden",
    "Cache cleared – games will be downloaded again on next start.":
        "Cache geleert – Spiele werden beim nächsten Start neu geladen.",
    "Hashes exported to {dest} (also copied to clipboard).": "Hashes exportiert nach {dest} (auch in der Zwischenablage).",
    "Hashes exported": "Hashes exportiert",
    "Saved: {dest}\nCopy the values into games.json in the repository to pin these versions.":
        "Gespeichert: {dest}\nWerte in die games.json im Repo übernehmen, um diese Versionen festzuschreiben.",
    "Official version list updated from GitHub.": "Offizielle Versionsliste von GitHub aktualisiert.",
    "Unexpected error ({where}):\n{err}\n\nDetails in:\n{log}": "Unerwarteter Fehler ({where}):\n{err}\n\nDetails stehen in:\n{log}",
    "Lucky Tower Launcher – error": "Lucky Tower Launcher – Fehler",
    "Language: English": "Sprache: Deutsch",

    # ---- core: progress
    "Ruffle was modified – reinstalling …": "Ruffle wurde verändert – wird neu installiert …",
    "Looking for Ruffle release on GitHub …": "Suche Ruffle-Release auf GitHub …",
    "Ruffle release not reachable – using mirror …": "Ruffle-Release nicht erreichbar – nutze Spiegel …",
    "Ruffle {tag} is up to date.": "Ruffle {tag} ist aktuell.",
    "Extracting Ruffle …": "Entpacke Ruffle …",
    "Ruffle {tag} installed.": "Ruffle {tag} installiert.",

    # ---- core: errors
    "Ruffle {tag} has no desktop build for {os}/{arch}": "Ruffle {tag} hat keinen Desktop-Build für {os}/{arch}",
    "No Ruffle desktop build found for {os}/{arch}": "Kein Ruffle-Desktop-Build für {os}/{arch} gefunden",
    "Ruffle download does not match GitHub's checksum.": "Ruffle-Download stimmt nicht mit der Prüfsumme von GitHub überein.",
    "Ruffle binary not found after extracting": "Ruffle-Binary nach dem Entpacken nicht gefunden",
    "Ruffle {tag} ({platform}) does not match the official fingerprint.":
        "Ruffle {tag} ({platform}) entspricht nicht dem offiziellen Fingerabdruck.",
    "Bundled file is missing: {file}\nPlease download the launcher again.":
        "Mitgelieferte Datei fehlt: {file}\nBitte den Launcher neu herunterladen.",
    "The downloaded file is not a SWF (source blocked or changed?)":
        "Die heruntergeladene Datei ist keine SWF (Quelle blockiert oder geändert?)",
    "{what} is not a valid SWF ({size} bytes) – probably an incomplete download. Please replace it.":
        "{what} ist keine gültige SWF ({size} Bytes) – vermutlich unvollständig heruntergeladen. Bitte ersetzen.",
    "Bundled file {file}": "Mitgelieferte Datei {file}",
    "Saved file {file}": "Gespeicherte Datei {file}",
    "File {file}": "Datei {file}",
    "Only available in developer mode.": "Nur im Entwicklermodus verfügbar.",
    "The selected file is not a SWF.": "Die gewählte Datei ist keine SWF.",
    "{game}: no officially approved version on record.": "{game}: keine offiziell freigegebene Version hinterlegt.",
    "{game}: no officially approved version on record – launch not allowed.":
        "{game}: keine offiziell freigegebene Version hinterlegt – Start nicht erlaubt.",
    "File does not match the official version ({src}).\nExpected: {exp}\nFound: {got}":
        "Datei passt nicht zur offiziellen Version ({src}).\nErwartet: {exp}\nGefunden: {got}",
    "SHA-256 does not match the official version!\nExpected ({src}): {exp}\nFound: {got}":
        "SHA-256 stimmt nicht mit der offiziellen Version überein!\nErwartet ({src}): {exp}\nGefunden: {got}",
    "Unsafe path in archive: {name}": "Unsicherer Pfad im Archiv: {name}",
    "Unsafe entry in archive: {name}": "Unsicherer Eintrag im Archiv: {name}",
    "Unknown archive format: {name}": "Unbekanntes Archivformat: {name}",

    # ---- practice (1.1.0)
    "PRACTICE": "PRACTICE",
    "+ practice version": "+ Practice-Version",
    "Practice version with room warps and QoL features – NOT valid for runs":
        "Practice-Version mit Raum-Warps und QoL-Features – NICHT für Runs zugelassen",
    "Practice version": "Practice-Version",
    "{name} is a PRACTICE version with room warps and QoL features.\n\n"
    "It is for practicing only. Runs played on this version are INVALID "
    "and will be rejected on the leaderboard.\n\nStart the practice version?":
        "{name} ist eine PRACTICE-Version mit Raum-Warps und QoL-Features.\n\n"
        "Sie ist nur zum Üben gedacht. Runs auf dieser Version sind UNGÜLTIG "
        "und werden auf dem Leaderboard abgelehnt.\n\nPractice-Version starten?",
    "PRACTICE – not valid for runs": "PRACTICE – nicht für Runs zugelassen",
    "practice": "Practice",

    # ---- LTU speedrun mod (1.2.0)
    "{name} download does not match the official fingerprint.":
        "{name}-Download stimmt nicht mit dem offiziellen Fingerabdruck überein.",
    "Speedrun mod: {list} missing – please repair": "Speedrun-Mod: {list} fehlt – bitte reparieren",
    "Installs BepInEx {bv}, {mod} {v} and {extras} into the game folder":
        "Installiert BepInEx {bv}, {mod} {v} und {extras} in den Spielordner",
    "This installs BepInEx {bv}, {mod} {v} and {extras} into:\n{path}\n\nPlease close Lucky Tower Ultimate first.\nContinue?":
        "Damit werden BepInEx {bv}, {mod} {v} und {extras} installiert in:\n{path}\n\nBitte Lucky Tower Ultimate vorher schließen.\nFortfahren?",
    "In game: F1 = ConfigurationManager (mod settings), F2 = fast restart":
        "Im Spiel: F1 = ConfigurationManager (Mod-Einstellungen), F2 = Schneller Neustart",
    "BepInEx download does not match the official fingerprint.":
        "BepInEx-Download stimmt nicht mit dem offiziellen Fingerabdruck überein.",
    "No speedrun mod is defined in the version list.": "In der Versionsliste ist keine Speedrun-Mod hinterlegt.",
    "The speedrun mod file is missing from the launcher. Please download the launcher again.":
        "Die Speedrun-Mod fehlt im Launcher. Bitte den Launcher neu herunterladen.",
    "The bundled speedrun mod does not match the official fingerprint.":
        "Die mitgelieferte Speedrun-Mod entspricht nicht dem offiziellen Fingerabdruck.",
    "Lucky Tower Ultimate was not found in {path}.": "Lucky Tower Ultimate wurde in {path} nicht gefunden.",
    "This Lucky Tower Ultimate build is not a Unity Mono game – BepInEx 5 cannot be installed. "
    "Please contact the moderators.":
        "Diese Lucky-Tower-Ultimate-Version ist kein Unity-Mono-Spiel – BepInEx 5 kann nicht installiert werden. "
        "Bitte an die Moderatoren wenden.",
    "Unsupported game architecture ({arch}). Please contact the moderators.":
        "Nicht unterstützte Spiel-Architektur ({arch}). Bitte an die Moderatoren wenden.",
    "Installing BepInEx …": "Installiere BepInEx …",
    "Installing {mod} …": "Installiere {mod} …",
    "Files in the game folder are in use. Please close Lucky Tower Ultimate and try again.\n\n{e}":
        "Dateien im Spielordner sind in Benutzung. Bitte Lucky Tower Ultimate schließen und erneut versuchen.\n\n{e}",
    "Installation could not be verified (state: {state}).": "Installation konnte nicht bestätigt werden (Status: {state}).",
    "Speedrun mod installed.": "Speedrun-Mod installiert.",
    "INSTALL SPEEDRUN MOD": "SPEEDRUN-MOD INSTALLIEREN",
    "REPAIR SPEEDRUN MOD": "SPEEDRUN-MOD REPARIEREN",
    "Speedrun mod: installed ✓ ({mod} {v}, BepInEx {bv})": "Speedrun-Mod: installiert ✓ ({mod} {v}, BepInEx {bv})",
    "Speedrun mod: modified or outdated – please repair": "Speedrun-Mod: verändert oder veraltet – bitte reparieren",
    "Speedrun mod: incomplete – please repair": "Speedrun-Mod: unvollständig – bitte reparieren",
    "Speedrun mod: not installed (required for top 3 runs)": "Speedrun-Mod: nicht installiert (Pflicht für Top-3-Runs)",
    "Speedrun mod not available in this launcher version": "Speedrun-Mod in dieser Launcher-Version nicht verfügbar",
    "Other plugins: {list}": "Weitere Plugins: {list}",
    "Installs BepInEx {bv} and {mod} {v} into the game folder": "Installiert BepInEx {bv} und {mod} {v} in den Spielordner",
    "Install speedrun mod": "Speedrun-Mod installieren",
    "This installs BepInEx {bv} and {mod} {v} into:\n{path}\n\nPlease close Lucky Tower Ultimate first.\nContinue?":
        "Damit werden BepInEx {bv} und {mod} {v} installiert in:\n{path}\n\nBitte Lucky Tower Ultimate vorher schließen.\nFortfahren?",
    "{mod} {v} is installed and verified.": "{mod} {v} ist installiert und geprüft.",
    "SPEEDRUN MOD ✓": "SPEEDRUN-MOD ✓",
    "STEAM FOLDER": "STEAM-ORDNER",
    "DATA FOLDER": "DATENORDNER",
    "Opens the Lucky Tower Ultimate installation folder": "Öffnet den Installationsordner von Lucky Tower Ultimate",
    "Lucky Tower Ultimate is not installed": "Lucky Tower Ultimate ist nicht installiert",
    "FULLSCREEN: ON": "VOLLBILD: AN",
    "FULLSCREEN: OFF": "VOLLBILD: AUS",
    "Start Lucky Tower 1 & 2 in fullscreen (Ruffle --fullscreen)": "Lucky Tower 1 & 2 im Vollbild starten (Ruffle --fullscreen)",
    "Fullscreen: on": "Vollbild: an",
    "Fullscreen: off": "Vollbild: aus",
    "LANGUAGE: EN": "SPRACHE: DE",

    # ---- verification codes (shown in status bar)
    "verified": "verifiziert",
    "same as first download": "wie erster Download",
    "bundled, not pinned": "mitgeliefert, nicht gepinnt",
    "not pinned (hash remembered)": "nicht gepinnt (Hash gemerkt)",
}

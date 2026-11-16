"""
Lucky Tower Launcher – GUI (tkinter), styled after the Lucky Tower 2 main menu.
Start:  python launcher.py   (moderators: python launcher.py --dev)
"""
from __future__ import annotations

import faulthandler
import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
import traceback
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable, Optional

import ltl_core as core
import ltl_i18n
from ltl_i18n import _

W, H = 900, 600

# Farbpalette
SKY_TOP, SKY_BOTTOM = "#a9d8ef", "#e4f4fb"
HILL_LIGHT, HILL_LIGHT_EDGE = "#7dbf4e", "#4c8a2b"
HILL_DARK, HILL_DARK_EDGE = "#5f8f37", "#3c6322"
STONE, STONE_DARK, STONE_EDGE = "#7b7c84", "#5f6068", "#34353b"
ROOF, ROOF_EDGE = "#8f2f2f", "#4d1717"
BTN, BTN_HOVER, BTN_EDGE = "#5b3b22", "#7c5330", "#2c1b0e"
BTN_DISABLED = "#6d6158"
BTN_PRACTICE, BTN_PRACTICE_HOVER, BTN_PRACTICE_LINE = "#2d5f6e", "#3d7d91", "#4a7f8f"
CREAM = "#f6ecd2"
INK = "#2c1b0e"
BAR = "#3b2614"


def pick_font(*families: str) -> str:
    avail = {f.lower() for f in tkfont.families()}
    for f in families:
        if f.lower() in avail:
            return f
    return "TkDefaultFont"


def lerp_color(c1: str, c2: str, t: float) -> str:
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


class Launcher:
    def __init__(self, root: tk.Tk):
        self.root = root
        # Entwicklermodus nur für Moderatoren: python launcher.py --dev  (oder LTL_DEV=1)
        self.dev = "--dev" in sys.argv or os.environ.get("LTL_DEV") == "1"
        root.resizable(False, False)
        self.cv = tk.Canvas(root, width=W, height=H, highlightthickness=0, bg=SKY_BOTTOM)
        self.cv.pack()

        self.f_title = (pick_font("Georgia", "DejaVu Serif", "Times New Roman"), 30, "bold")
        self.f_btn = (pick_font("Trebuchet MS", "Verdana", "DejaVu Sans", "Helvetica"), 15, "bold")
        self.f_btn_half = (self.f_btn[0], 11, "bold")
        self.f_small = (pick_font("Segoe UI", "Verdana", "DejaVu Sans", "Helvetica"), 9)
        self.f_info = (pick_font("Segoe UI", "Verdana", "DejaVu Sans", "Helvetica"), 10, "bold")

        # Kernobjekte
        self.data = core.data_dir()
        self._install_crash_handlers()
        self.settings = core.Settings.load(self.data)
        ltl_i18n.set_language(self.settings.language)
        self._set_title()
        self.ruffle = core.RuffleManager(self.data)
        self.swfs = core.SwfManager(self.data, strict=not self.dev)
        if self.dev:
            self.manifest, self.manifest_src = core.load_manifest(self.data, self.settings, self._log)
        else:
            self.manifest, self.manifest_src = core.load_official_manifest(self._log)

        self.q: "queue.Queue[Callable[[], None]]" = queue.Queue()
        self.busy = False
        self.running: dict = {}
        self.page_stack: list[Callable[[], None]] = []
        self.status_text = ""
        self.progress: Optional[float] = None

        self._draw_scene()
        root.bind("<Escape>", lambda e: self.back())
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.show_main()
        self._refresh_status()
        self.root.after(40, self._tick)
        if not self.dev:
            threading.Thread(target=self._check_remote_manifest, daemon=True).start()

    def _set_title(self) -> None:
        self.root.title(f"Lucky Tower Launcher {core.APP_VERSION}" + (f"  {_('[DEVELOPER MODE]')}" if self.dev else ""))

    def _check_remote_manifest(self) -> None:
        """Übernimmt ein neueres offizielles Manifest aus dem GitHub-Repo (nur vollständig gepinnt)."""
        try:
            remote = core.fetch_remote_official()
        except Exception as e:  # noqa: BLE001
            self.post(lambda m=str(e): self.trail(f"Official online manifest not available: {m}"))
            return
        if remote == self.manifest:
            return

        def apply():
            if self.busy:
                self.root.after(500, apply)
                return
            self.manifest, self.manifest_src = remote, "official (GitHub)"
            self.trail("Official manifest taken over from GitHub")
            self.set_status(_("Official version list updated from GitHub."), None)
            self._refresh_page()
        self.post(apply)

    # ------------------------------------------------------------------ crash
    def _install_crash_handlers(self) -> None:
        """Jeder unbehandelte Fehler landet in crash.log und als Meldung statt eines stillen Absturzes."""
        self._session = self.data / "session.log"
        try:
            prev = self._session.read_text("utf-8", errors="replace").rstrip().splitlines()
            if self._session.stat().st_size > 300_000:
                self._session.write_text("\n".join(prev[-2000:]) + "\n", "utf-8")
            unclean = bool(prev) and not prev[-1].endswith(("END", "ENDE"))
        except OSError:
            unclean = False
        self.trail(f"START Launcher {core.APP_VERSION}, Python {sys.version.split()[0]}, "
                   f"Tk {self.root.tk.call('info', 'patchlevel')}, {sys.platform}")
        if unclean:
            self.trail("Note: previous session ended unexpectedly (crash / freeze / task manager)")
        try:
            # Harte Abstürze (Access Violation usw.) und Einfrieren > 10 s: Stack aller Threads protokollieren
            self._fh = open(self.data / "crash_native.log", "a", encoding="utf-8")
            self._fh.write(f"\n=== Session {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            self._fh.flush()
            faulthandler.enable(self._fh)
        except (OSError, RuntimeError, ValueError):
            self._fh = None

        def report(exc_type, exc, tb, where: str) -> None:
            text = "".join(traceback.format_exception(exc_type, exc, tb))
            self.trail(f"ERROR [{where}] {exc_type.__name__}: {exc}")
            try:
                with open(self.data / "crash.log", "a", encoding="utf-8") as f:
                    f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} [{where}] "
                            f"Launcher {core.APP_VERSION}, Python {sys.version.split()[0]}\n{text}\n")
            except OSError:
                pass
            msg = _("Unexpected error ({where}):\n{err}\n\nDetails in:\n{log}", where=where,
                    err=f"{exc_type.__name__}: {exc}", log=self.data / "crash.log")
            if threading.current_thread() is threading.main_thread():
                messagebox.showerror(_("Lucky Tower Launcher – error"), msg)
            else:
                self.post(lambda: messagebox.showerror(_("Lucky Tower Launcher – error"), msg))

        self.root.report_callback_exception = lambda t, e, tb: report(t, e, tb, "GUI")
        sys.excepthook = lambda t, e, tb: report(t, e, tb, "main thread")
        threading.excepthook = lambda a: report(a.exc_type, a.exc_value, a.exc_traceback, "background")
        self._report = report

    def trail(self, msg: str) -> None:
        """Sitzungsprotokoll (session.log): Start, Klicks, Fehler, Ende."""
        try:
            with open(self._session, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}\n")
        except OSError:
            pass

    def close(self) -> None:
        self.trail("END")
        try:
            faulthandler.cancel_dump_traceback_later()
        except Exception:  # noqa: BLE001
            pass
        self.root.destroy()

    # ------------------------------------------------------------------ util
    def _log(self, msg: str) -> None:
        print(msg)

    def post(self, fn: Callable[[], None]) -> None:
        self.q.put(fn)

    def _tick(self) -> None:
        # Nächsten Tick zuerst planen – so läuft der Watchdog auch während offener Dialoge weiter
        self.root.after(40, self._tick)
        if self._fh:
            faulthandler.dump_traceback_later(10, repeat=False, file=self._fh)
        try:
            while True:
                self.q.get_nowait()()
        except queue.Empty:
            pass
        # Wolken treiben lassen
        for cid, speed in self.clouds:
            self.cv.move(cid, speed, 0)
            x1 = (self.cv.bbox(cid) or (0, 0, 0, 0))[0]
            if x1 > W + 20:
                bx1, _y1, bx2, _y2 = self.cv.bbox(cid)
                self.cv.move(cid, -(W + (bx2 - bx1) + 60), 0)

    def run_bg(self, work: Callable[[], object]) -> None:
        if self.busy:
            return
        self.busy = True
        self._render_buttons()

        def wrapper():
            followup = None
            try:
                followup = work()
            except Exception as e:  # noqa: BLE001
                try:
                    with open(self.data / "crash.log", "a", encoding="utf-8") as f:
                        f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} [action]\n{traceback.format_exc()}\n")
                except OSError:
                    pass
                msg = str(e) or type(e).__name__
                followup = lambda: (self.set_status(_("Error – see message."), None),  # noqa: E731
                                    messagebox.showerror(_("Error"), msg))
            finally:
                def done():
                    self.busy = False
                    self._render_buttons()
                self.post(done)
                if callable(followup):
                    self.post(followup)

        threading.Thread(target=wrapper, daemon=True).start()

    def bg_progress(self, text: str, frac: Optional[float]) -> None:
        self.post(lambda: self.set_status(text, frac))

    # ---------------------------------------------------------------- szene
    def _draw_scene(self) -> None:
        cv = self.cv
        horizon = 430
        for y in range(0, horizon, 4):
            cv.create_rectangle(0, y, W, y + 4, outline="", fill=lerp_color(SKY_TOP, SKY_BOTTOM, y / horizon))
        cv.create_rectangle(0, horizon, W, H, outline="", fill=SKY_BOTTOM)

        # Wolken
        self.clouds = []
        for i, (x, y, s, sp) in enumerate([(80, 70, 1.0, 0.25), (640, 50, 1.3, 0.18),
                                           (380, 140, 0.8, 0.32), (820, 170, 0.9, 0.22)]):
            tag = f"cloud{i}"
            for dx, dy, r in ((0, 0, 28), (30, -12, 34), (64, 0, 28), (30, 8, 30)):
                r *= s
                cv.create_oval(x + dx * s - r, y + dy * s - r, x + dx * s + r, y + dy * s + r,
                               fill="white", outline="", tags=(tag,))
            self.clouds.append((tag, sp))

        # Hintere Hügel
        cv.create_oval(-260, 330, 330, 900, fill=HILL_LIGHT, outline=HILL_LIGHT_EDGE, width=4)
        cv.create_oval(570, 320, 1160, 900, fill=HILL_LIGHT, outline=HILL_LIGHT_EDGE, width=4)
        # Büsche
        for bx, by, r in ((40, 400, 26), (85, 385, 22), (800, 380, 24), (850, 395, 28), (760, 405, 18)):
            cv.create_oval(bx - r, by - r, bx + r, by + r, fill="#5aa33a", outline=HILL_LIGHT_EDGE, width=3)

        # Zentraler Burgberg
        cv.create_oval(205, 225, 695, 980, fill=HILL_DARK, outline=HILL_DARK_EDGE, width=5)
        # Weg zur Burg
        cv.create_polygon(432, 282, 468, 282, 540, 600, 360, 600, fill="#8a6a43", outline="#5c4329",
                          width=3, smooth=False)

        self._draw_castle(450, 284)

        # Titel
        self._outlined_text(W // 2, 34, "LUCKY TOWER LAUNCHER", self.f_title, CREAM, INK, 3)
        if self.dev:
            self.cv.create_rectangle(0, 62, W, 84, fill="#a8322d", outline="")
            self.banner_id = self.cv.create_text(W // 2, 73, text=_("DEVELOPER MODE – for moderators only, not valid for runs"),
                                                 fill="white", font=self.f_info)

        # Statusleiste
        cv.create_rectangle(0, H - 30, W, H, fill=BAR, outline="")
        self.status_id = cv.create_text(12, H - 15, anchor="w", text="", fill=CREAM, font=self.f_small)
        self.right_id = cv.create_text(W - 12, H - 15, anchor="e", text="", fill="#cdb894", font=self.f_small)
        self.pbar_id = cv.create_rectangle(0, H - 32, 0, H - 30, fill="#e0b25a", outline="")

    def _draw_castle(self, cx: int, base: int) -> None:
        cv = self.cv

        def tower(x1, y1, x2, y2, roof_h, window=True):
            cv.create_rectangle(x1, y1, x2, y2, fill=STONE, outline=STONE_EDGE, width=3)
            cv.create_polygon(x1 - 7, y1, (x1 + x2) / 2, y1 - roof_h, x2 + 7, y1,
                              fill=ROOF, outline=ROOF_EDGE, width=3)
            if window:
                wx = (x1 + x2) / 2
                cv.create_rectangle(wx - 4, y1 + 12, wx + 4, y1 + 26, fill="#2a2a30", outline="")

        # Türme hinten
        tower(cx - 58, base - 150, cx - 22, base - 70, 34)
        tower(cx + 22, base - 138, cx + 58, base - 70, 30)
        tower(cx - 18, base - 178, cx + 18, base - 90, 34)  # Bergfried
        # Hauptmauer mit Zinnen
        l, r, top = cx - 105, cx + 105, base - 72
        step = 15
        for x in range(l, r, step * 2):
            cv.create_rectangle(x, top - 11, x + step, top, fill=STONE, outline=STONE_EDGE, width=3)
        cv.create_rectangle(l, top, r, base, fill=STONE, outline=STONE_EDGE, width=3)
        for y in range(top + 16, base - 4, 18):
            off = 0 if (y // 18) % 2 else 15
            for x in range(l + 8 + off, r - 10, 30):
                cv.create_line(x, y, x + 13, y, fill=STONE_DARK, width=2)
        # Ecktürme vorne
        tower(cx - 132, base - 118, cx - 92, base, 40)
        tower(cx + 92, base - 118, cx + 132, base, 40)
        # Tor
        cv.create_oval(cx - 20, base - 62, cx + 20, base - 22, fill="#3a2614", outline=STONE_EDGE, width=3)
        cv.create_rectangle(cx - 20, base - 42, cx + 20, base, fill="#3a2614", outline=STONE_EDGE, width=3)
        cv.create_rectangle(cx - 17, base - 44, cx + 17, base - 2, fill="#3a2614", outline="")
        for x in (cx - 10, cx, cx + 10):
            cv.create_line(x, base - 56, x, base, fill="#1f140a", width=2)

    def _outlined_text(self, x, y, text, font, fill, outline, w=2, tags=()):
        for dx in (-w, 0, w):
            for dy in (-w, 0, w):
                if dx or dy:
                    self.cv.create_text(x + dx, y + dy, text=text, font=font, fill=outline, tags=tags)
        return self.cv.create_text(x, y, text=text, font=font, fill=fill, tags=tags)

    def _round_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.cv.create_polygon(pts, smooth=True, **kw)

    # ---------------------------------------------------------------- seiten
    def _set_page(self, subtitle: str, buttons: list[tuple[str, Callable[[], None], str, bool]]) -> None:
        """buttons: (label, aktion, hover-info, aktiviert)"""
        self.subtitle = subtitle
        self.buttons = buttons
        self.info_default = ""
        self._render_buttons()

    def _render_buttons(self) -> None:
        """self.buttons: Einträge sind (label, aktion, info, aktiv[, stil]) oder eine Liste
        aus zwei solchen Tupeln = eine Zeile mit zwei halben Knöpfen."""
        cv = self.cv
        cv.delete("ui")
        if getattr(self, "subtitle", ""):
            self._outlined_text(W // 2, 300, self.subtitle, self.f_info, CREAM, INK, 2, tags=("ui",))
        n = len(self.buttons)
        bw = 310
        bh, gap = (40, 10) if n <= 4 else ((34, 6) if n == 5 else (30, 5))
        y0 = 318 if n <= 5 else 312
        self.flat_buttons = []  # [(tag, eintrag)] – auch für Tests
        for i, entry in enumerate(self.buttons):
            y = y0 + i * (bh + gap)
            if isinstance(entry, list):
                half = (bw - 8) // 2
                cells = [(f"btn{i}_{j}", e, W // 2 - bw // 2 + j * (half + 8), half, self.f_btn_half)
                         for j, e in enumerate(entry)]
            else:
                cells = [(f"btn{i}", entry, W // 2 - bw // 2, bw, self.f_btn)]
            for tag, (label, action, info, enabled, *style), x1, w, font in cells:
                self.flat_buttons.append((tag, (label, action, info, enabled, *style)))
                practice = bool(style) and style[0] == "practice"
                base, line = (BTN_PRACTICE, BTN_PRACTICE_LINE) if practice else (BTN, "#7b5636")
                x2 = x1 + w
                active = enabled and not self.busy
                body = self._round_rect(x1, y, x2, y + bh, 14, fill=base if active else BTN_DISABLED,
                                        outline=BTN_EDGE, width=3, tags=("ui", tag))
                cv.create_line(x1 + 14, y + 6, x2 - 14, y + 6, fill=line if active else "#7f746b",
                               width=2, tags=("ui", tag))
                cv.create_text((x1 + x2) // 2, y + bh // 2 + 1, text=label, font=font,
                               fill=CREAM if active else "#c9bfae", tags=("ui", tag))
                # Infotext auch bei deaktivierten Knöpfen (erklärt, warum)
                cv.tag_bind(tag, "<Enter>", lambda e, b=body, inf=info, p=practice, a=active: self._hover(b, True, inf, p, a))
                cv.tag_bind(tag, "<Leave>", lambda e, b=body, p=practice, a=active: self._hover(b, False, "", p, a))
                if active:
                    cv.tag_bind(tag, "<Button-1>", lambda e, a=action, lb=label: (self.trail(f"Click: {lb}"), a()))
                else:
                    cv.tag_unbind(tag, "<Button-1>")
        self.info_bg = self._round_rect(70, H - 76, W - 70, H - 36, 12, fill="#f3e6c4", outline=BTN_EDGE,
                                        width=2, tags=("ui",), state="hidden")
        self.info_id = cv.create_text(W // 2, H - 56, text="", font=self.f_small, fill=INK,
                                      tags=("ui",), width=W - 120, justify="center")

    def button(self, label: str) -> tuple:
        """(tag, eintrag) eines Knopfes nach Beschriftung."""
        for tag, e in self.flat_buttons:
            if e[0] == label:
                return tag, e
        raise KeyError(label)

    def _hover(self, body, on: bool, info: str, practice: bool = False, active: bool = True) -> None:
        if active:
            if practice:
                self.cv.itemconfigure(body, fill=BTN_PRACTICE_HOVER if on else BTN_PRACTICE)
            else:
                self.cv.itemconfigure(body, fill=BTN_HOVER if on else BTN)
            self.cv.configure(cursor="hand2" if on else "")
        self.cv.itemconfigure(self.info_id, text=info if on else "")
        self.cv.itemconfigure(self.info_bg, state="normal" if (on and info) else "hidden")

    def go(self, page: Callable[[], None]) -> None:
        self.page_stack.append(page)
        page()

    def back(self) -> None:
        if len(self.page_stack) > 1 and not self.busy:
            self.page_stack.pop()
            self.page_stack[-1]()

    def _groups(self) -> dict[str, list[dict]]:
        groups: dict[str, list[dict]] = {}
        for g in self.manifest["games"]:
            groups.setdefault(g["title"], []).append(g)
        return groups

    def show_main(self) -> None:
        self.page_stack = [self._main_page]
        self._main_page()

    def _main_page(self) -> None:
        btns = []
        for title, games in self._groups().items():
            info = _("{n} official version(s): {list}", n=len(games),
                     list=", ".join(g.get("variant") or _("Standard") for g in games))
            if self._practice_for(title):
                info += "  ·  " + _("+ practice version")
            btns.append((title.upper(), lambda t=title: self.go(lambda: self._game_page(t)), info, True))
        btns.append(("LUCKY TOWER ULTIMATE", lambda: self.go(self._ultimate_page), _("Steam version"), True))
        btns.append((_("SETTINGS"), lambda: self.go(self._settings_page), _("Ruffle, downloads, language"), True))
        self._set_page("", btns)

    def _practice_for(self, title: str) -> list[dict]:
        return [p for p in self.manifest.get("practice", []) if p["title"] == title]

    def _game_page(self, title: str) -> None:
        games = self._groups()[title]
        btns = []
        for g in games:
            st = self.swfs.status(g)
            if st["expected"] and st["source"] == "manifest":
                ver = _("officially approved ✓ (SHA-256 {h}…)", h=st["expected"][:12])
            elif st["expected"]:
                ver = _("SHA-256 {h}… ({src})", h=st["expected"][:12], src=_(st["source"]))
            else:
                ver = _("not approved") if not self.dev else _("SHA-256 not pinned yet")
            if st.get("bundled"):
                cached = _("bundled")
            elif st["cached"]:
                cached = _("available locally")
            else:
                cached = _("downloaded on start")
            quelle = g.get("file") if st.get("bundled") else (g.get("url") or g.get("file"))
            info = f"{g.get('variant') or title}  ·  {cached}  ·  {ver}\n" + _("Source: {src}", src=quelle)
            btns.append((_(g.get("label") or "PLAY"), lambda g=g: self.launch(g), info, True))
        for p in self._practice_for(title):
            info = _("Practice version with room warps and QoL features – NOT valid for runs") + "\n" + \
                _("Source: {src}", src=p.get("file") or p.get("url"))
            btns.append((_(p.get("label") or "PRACTICE"), lambda p=p: self.launch(p), info, True, "practice"))
        btns.append((_("BACK"), self.back, "", True))
        self._set_page(title.upper(), btns)

    @property
    def ltu_mod(self) -> core.LtuModManager:
        return core.LtuModManager(self.data, self.manifest.get("ltu_mod"))

    def _mod_status_text(self, st: dict) -> str:
        spec = self.manifest.get("ltu_mod") or {}
        name = spec.get("mod", {}).get("name", "LTU Speedrun Mod")
        text = {
            "installed": _("Speedrun mod: installed ✓ ({mod} {v}, BepInEx {bv})", mod=name,
                           v=st.get("mod_version"), bv=st.get("bepinex_version")),
            "modified": _("Speedrun mod: modified or outdated – please repair"),
            "incomplete": (_("Speedrun mod: {list} missing – please repair", list=", ".join(st["missing_plugins"]))
                           if st.get("missing_plugins") else _("Speedrun mod: incomplete – please repair")),
            "missing": _("Speedrun mod: not installed (required for top 3 runs)"),
        }[st["state"]]
        if st.get("other_plugins"):
            text += "\n" + _("Other plugins: {list}", list=", ".join(st["other_plugins"]))
        return text

    def _mod_extras(self) -> str:
        plugins = (self.manifest.get("ltu_mod") or {}).get("plugins") or []
        return ", ".join(f"{p['name']} {p.get('version', '')}".strip() for p in plugins)

    def _ultimate_page(self) -> None:
        found = core.find_steam_game()
        if found:
            info = _("Found: {path}", path=found["path"]) + (
                "  ·  " + _("Build {id}", id=found["buildid"]) if found.get("buildid") else "")
            mod = self.ltu_mod
            spec = self.manifest.get("ltu_mod") or {}
            if mod.spec:
                st = mod.status(Path(found["path"]))
                info += "\n" + self._mod_status_text(st)
            btns = [(_("PLAY (STEAM)"), self.launch_ultimate, info, True)]
            if mod.available():
                st = mod.status(Path(found["path"]))
                m = spec["mod"]
                extras = self._mod_extras()
                if extras:
                    minfo = _("Installs BepInEx {bv}, {mod} {v} and {extras} into the game folder",
                              bv=spec["bepinex"].get("version"), mod=m.get("name", "LTU Speedrun Mod"),
                              v=m.get("version"), extras=extras)
                else:
                    minfo = _("Installs BepInEx {bv} and {mod} {v} into the game folder", bv=spec["bepinex"].get("version"),
                              mod=m.get("name", "LTU Speedrun Mod"), v=m.get("version"))
                minfo += "\n" + self._mod_status_text(st)
                label = _("REPAIR SPEEDRUN MOD") if st["state"] != "missing" else _("INSTALL SPEEDRUN MOD")
                btns.append((label, lambda p=found["path"]: self.install_ltu_mod(Path(p)), minfo, True))
            else:
                btns.append((_("INSTALL SPEEDRUN MOD"), lambda: None,
                             _("Speedrun mod not available in this launcher version"), False))
            sub = "LUCKY TOWER ULTIMATE"
        else:
            btns = [(_("OPEN STEAM STORE"), lambda: core.open_steam_store(),
                     _("No Steam installation of app {id} found", id=core.LTU_STEAM_APPID), True)]
            sub = _("ULTIMATE – NOT INSTALLED")
        btns.append((_("SEARCH AGAIN"), self._ultimate_page, _("Search Steam libraries again"), True))
        btns.append((_("BACK"), self.back, "", True))
        self._set_page(sub, btns)

    def _settings_page(self) -> None:
        cur = self.ruffle.installed()
        pinned = self._wanted_ruffle_tag()
        rinfo = _("Installed: {tag}", tag=cur["tag"] if cur else _("none")) + "  ·  " + (
            _("pinned: {tag}", tag=pinned) if pinned else _("latest version"))
        found = core.find_steam_game()
        folders = [
            (_("DATA FOLDER"), lambda: core.open_folder(self.data), str(self.data), True),
            (_("STEAM FOLDER"), (lambda p=found["path"]: core.open_folder(Path(p))) if found else (lambda: None),
             (_("Opens the Lucky Tower Ultimate installation folder") + f"\n{found['path']}") if found
             else _("Lucky Tower Ultimate is not installed"), bool(found)),
        ]
        prefs = [
            (_("FULLSCREEN: ON") if self.settings.fullscreen else _("FULLSCREEN: OFF"), self.toggle_fullscreen,
             _("Start Lucky Tower 1 & 2 in fullscreen (Ruffle --fullscreen)"), True),
            (_("LANGUAGE: EN"), self.toggle_language, _("Switch to German / Auf Deutsch umschalten"), True),
        ]
        if self.dev:
            btns = [
                (_("UPDATE RUFFLE"), self.update_ruffle, rinfo, True),
                (_("EXPORT HASHES"), self.export_hashes,
                 _("Downloads all SWFs, computes SHA-256 and saves games_pinned.json (incl. Ruffle hash)"), True),
                (_("RELOAD DOWNLOADS"), self.clear_cache, _("Deletes downloaded SWFs and remembered hashes"), True),
                folders,
                prefs,
                (_("BACK"), self.back, f"Manifest: {self.manifest_src}", True),
            ]
        else:
            btns = [
                (_("REPAIR RUFFLE"), self.reinstall_ruffle, rinfo + "  ·  " + _("reinstalls the official version"), True),
                (_("RELOAD DOWNLOADS"), self.clear_cache,
                 _("Re-downloads games – only the official versions are accepted"), True),
                folders,
                prefs,
                (_("BACK"), self.back, _("Version list: {src}", src=self.manifest_src), True),
            ]
        self._set_page(_("SETTINGS"), btns)

    def toggle_fullscreen(self) -> None:
        self.settings.fullscreen = not self.settings.fullscreen
        try:
            self.settings.save(self.data)
        except OSError:
            pass
        self.trail(f"Fullscreen: {self.settings.fullscreen}")
        self.set_status(_("Fullscreen: on") if self.settings.fullscreen else _("Fullscreen: off"), None)
        self._refresh_page()

    def toggle_language(self) -> None:
        new = "de" if ltl_i18n.get_language() == "en" else "en"
        ltl_i18n.set_language(new)
        self.settings.language = new
        try:
            self.settings.save(self.data)
        except OSError:
            pass
        self.trail(f"Language: {new}")
        self._set_title()
        if self.dev:
            self.cv.itemconfigure(self.banner_id, text=_("DEVELOPER MODE – for moderators only, not valid for runs"))
        self.set_status(_("Language: English"), None)
        self._refresh_page()

    # ---------------------------------------------------------------- status
    def set_status(self, text: str, frac: Optional[float]) -> None:
        self.status_text, self.progress = text, frac
        self._refresh_status()

    def _refresh_status(self) -> None:
        self.cv.itemconfigure(self.status_id, text=self.status_text)
        cur = self.ruffle.installed()
        mode = _("DEV") if self.dev else _("Official")
        self.cv.itemconfigure(self.right_id, text=f"{mode}  ·  Ruffle: {cur['tag'] if cur else '—'}  ·  v{core.APP_VERSION}")
        w = int(W * self.progress) if self.progress is not None else 0
        self.cv.coords(self.pbar_id, 0, H - 32, w, H - 30)

    # ---------------------------------------------------------------- aktionen
    def _wanted_ruffle_tag(self) -> Optional[str]:
        if self.dev:
            return self.settings.ruffle_tag_override or self.manifest.get("ruffle_tag")
        return self.manifest["ruffle_tag"]

    def _ruffle_pins(self) -> Optional[dict]:
        # Fingerabdrücke gelten nur für die im Manifest festgelegte Ruffle-Version
        if self._wanted_ruffle_tag() == self.manifest.get("ruffle_tag"):
            return self.manifest.get("ruffle_sha256")
        return None

    def _ruffle_ready(self, **kw) -> dict:
        mirrors = self.manifest.get("ruffle_mirror") if self._ruffle_pins() else None
        st = self.ruffle.ensure(self._wanted_ruffle_tag(), self.bg_progress, pins=self._ruffle_pins(),
                                mirrors=mirrors, **kw)
        if not self.dev and self.ruffle.verify(st, self._ruffle_pins()) is None:
            st = dict(st, verification="ruffle binary not pinned for this platform")
        return st

    def launch(self, game: dict) -> None:
        name = f"{game['title']} – {game.get('variant') or _('Standard')}"
        practice = bool(game.get("practice"))
        if practice:
            self.trail(f"Practice warning shown: {game['id']}")
            if not messagebox.askokcancel(
                    _("Practice version"),
                    _("{name} is a PRACTICE version with room warps and QoL features.\n\n"
                      "It is for practicing only. Runs played on this version are INVALID "
                      "and will be rejected on the leaderboard.\n\nStart the practice version?", name=name),
                    icon="warning"):
                self.trail(f"Practice start cancelled: {game['id']}")
                return

        def work(redownload: bool = False, local: Optional[Path] = None):
            rs = self._ruffle_ready()
            try:
                if local:
                    swf, h, ver = self.swfs.import_local(game, local)
                else:
                    swf, h, ver = self.swfs.ensure(game, self.bg_progress, redownload=redownload)
            except core.NotApproved:
                raise
            except core.HashMismatch as e:
                if redownload or local or self.swfs.bundled_path(game) or not game.get("url"):
                    raise RuntimeError(_("{msg}\n\nThis file is not an approved version and will not be started.", msg=e))
                msg = str(e)
                return lambda: self._ask_redownload(msg, work)
            except Exception as e:  # noqa: BLE001  (Download fehlgeschlagen)
                if local or self.swfs.path_for(game).exists() or not game.get("url"):
                    raise
                msg = str(e)
                return lambda: self._ask_local(game, msg, work)
            self.bg_progress(_("Starting {name} …", name=name), None)
            log_path = self.data / "logs" / f"ruffle_{game['id']}.log"
            args = list(game.get("ruffle_args") or [])
            if self.settings.fullscreen and "--fullscreen" not in args:
                args.append("--fullscreen")
            proc = core.launch_swf(rs["exe"], swf, args, log_path)
            core.write_launch_log(self.data, {
                "game": game["id"], "url": game.get("url"), "file": game.get("file"),
                "sha256": h, "verification": ver, "ruffle": rs["tag"],
                "ruffle_verification": rs.get("verification", "ok"),
                "mode": "dev" if self.dev else "official",
                "practice": practice,
                "fullscreen": self.settings.fullscreen,
                "build": "exe" if getattr(sys, "frozen", False) else "source",
                "manifest": self.manifest_src})
            detail = f"SHA-256 {h[:12]}… ({_(ver)})  ·  Ruffle {rs['tag']}"
            if practice:
                detail = _("PRACTICE – not valid for runs") + "  ·  " + detail
            self._watch(proc, name, detail, log_path)
            return self._refresh_page

        self.run_bg(work)

    def _watch(self, proc, name: str, detail: str, log_path: Path) -> None:
        """Statusleiste folgt dem Ruffle-Prozess: läuft → beendet / Fehler."""
        self.running[name] = proc
        self.bg_progress(_("▶ {name} running  ·  {detail}", name=name, detail=detail), None)
        started = time.time()

        def wait():
            code = proc.wait()
            dur = time.time() - started

            def done():
                self.running.pop(name, None)
                if code != 0 and dur < 15:
                    self.set_status(_("✖ {name}: Ruffle exited with an error (code {code})", name=name, code=code), None)
                    out = core.tail(log_path) or _("(no output)")
                    messagebox.showerror(_("Ruffle error"), _(
                        "{name} could not be started (exit code {code}).\n\nLast Ruffle output:\n{out}\n\nLog: {log}",
                        name=name, code=code, out=out, log=log_path))
                elif self.running:
                    other = next(iter(self.running))
                    self.set_status(_("▶ {other} running  ·  {name} closed", other=other, name=name), None)
                else:
                    m, sec = divmod(int(dur), 60)
                    self.set_status(_("{name} closed  ·  play time {m}:{s} min", name=name, m=m, s=f"{sec:02d}"), None)
            self.post(done)

        threading.Thread(target=wait, daemon=True).start()

    def _refresh_page(self) -> None:
        if self.page_stack:
            self.page_stack[-1]()

    def _ask_redownload(self, msg, work) -> None:
        if messagebox.askyesno(_("Version mismatch"), _(
                "{msg}\n\nThe local file was modified or is outdated.\nDownload it again from the official source now?",
                msg=msg)):
            self.run_bg(lambda: work(redownload=True))

    def _ask_local(self, game, msg, work) -> None:
        if messagebox.askyesno(_("Download failed"), _(
                "The official source is not reachable:\n{msg}\n\nSelect a locally saved SWF instead?\n"
                "(It is checked against the official hash.)", msg=msg)):
            p = filedialog.askopenfilename(title=_("{title} – choose SWF", title=game["title"]),
                                           filetypes=[("Flash", "*.swf"), (_("All files"), "*.*")])
            if p:
                self.run_bg(lambda: work(local=Path(p)))

    def launch_ultimate(self) -> None:
        try:
            entry = {"game": "ltu", "steam_appid": core.LTU_STEAM_APPID,
                     "mode": "dev" if self.dev else "official",
                     "build": "exe" if getattr(sys, "frozen", False) else "source"}
            found = core.find_steam_game()
            if found and self.ltu_mod.spec:
                st = self.ltu_mod.status(Path(found["path"]))
                entry.update({"buildid": found.get("buildid"), "speedrun_mod": st["state"],
                              "speedrun_mod_version": st["mod_version"], "bepinex": st["bepinex_version"],
                              "other_plugins": st["other_plugins"], "plugins": st.get("plugins", {}),
                              "missing_plugins": st.get("missing_plugins", [])})
            core.launch_steam_game()
            core.write_launch_log(self.data, entry)
            self.set_status(_("Starting Lucky Tower Ultimate via Steam …"), None)
        except OSError as e:
            messagebox.showerror(_("Error"), _("Steam could not be opened:\n{e}", e=e))

    def install_ltu_mod(self, game_dir: Path) -> None:
        spec = self.manifest["ltu_mod"]
        m = spec["mod"]
        name = m.get("name", "LTU Speedrun Mod")
        extras = self._mod_extras()
        if extras:
            q = _("This installs BepInEx {bv}, {mod} {v} and {extras} into:\n{path}\n\n"
                  "Please close Lucky Tower Ultimate first.\nContinue?",
                  bv=spec["bepinex"].get("version"), mod=name, v=m.get("version"), extras=extras, path=game_dir)
        else:
            q = _("This installs BepInEx {bv} and {mod} {v} into:\n{path}\n\nPlease close Lucky Tower Ultimate first.\nContinue?",
                  bv=spec["bepinex"].get("version"), mod=name, v=m.get("version"), path=game_dir)
        if not messagebox.askokcancel(_("Install speedrun mod"), q):
            return

        def work():
            st = self.ltu_mod.install(game_dir, self.bg_progress)
            self.trail(f"Speedrun mod installed: {st['mod_version']} / BepInEx {st['bepinex_version']}")
            done = _("{mod} {v} is installed and verified.", mod=name, v=st["mod_version"])
            if any(p.get("name") == "ConfigurationManager" for p in spec.get("plugins") or []):
                done += "  ·  " + _("In game: F1 = ConfigurationManager (mod settings), F2 = fast restart")
            self.bg_progress(done, 1.0)
            return self._refresh_page
        self.run_bg(work)

    def reinstall_ruffle(self) -> None:
        def work():
            st = self._ruffle_ready(reinstall=True)
            self.bg_progress(_("Ruffle {tag} reinstalled and verified.", tag=st["tag"]), None)
            return self._refresh_page
        self.run_bg(work)

    def update_ruffle(self) -> None:
        def work():
            st = self.ruffle.ensure(self._wanted_ruffle_tag(), self.bg_progress, force_check=True, pins=self._ruffle_pins())
            self.bg_progress(_("Ruffle {tag} ready.", tag=st["tag"]), None)
            return self._refresh_page
        self.run_bg(work)

    def clear_cache(self) -> None:
        q = (_("Delete all downloaded SWFs and remembered hashes?") if self.dev else
             _("Delete downloaded games and download them again on next start?\n(The official versions stay pinned.)"))
        if messagebox.askyesno(_("Reload downloads"), q):
            self.swfs.clear()
            self.set_status(_("Cache cleared – games will be downloaded again on next start."), None)

    def export_hashes(self) -> None:
        def work():
            out = json.loads(json.dumps(self.manifest))
            ruffle = self.ruffle.installed()
            lines = []
            if ruffle:
                out["ruffle_tag"] = ruffle["tag"]
                pins = dict(out.get("ruffle_sha256") or {})
                pins[core.platform_id()] = core.sha256_file(Path(ruffle["exe"]))
                out["ruffle_sha256"] = pins
                lines.append(f"Ruffle {ruffle['tag']} ({core.platform_id()}): {pins[core.platform_id()]}")
            for g in out["games"] + out.get("practice", []):
                g.pop("practice", None)
                p = self.swfs.fetch_raw(g, self.bg_progress)
                h = core.sha256_file(p)
                g["sha256"] = h
                lines.append(f"{g['id']}: {h}")
            dest = self.data / "games_pinned.json"
            dest.write_text(json.dumps(out, indent=2, ensure_ascii=False), "utf-8")
            text = json.dumps(out, indent=2, ensure_ascii=False)

            def finish():
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.set_status(_("Hashes exported to {dest} (also copied to clipboard).", dest=dest), 1.0)
                messagebox.showinfo(_("Hashes exported"), "\n".join(lines) + "\n\n" + _(
                    "Saved: {dest}\nCopy the values into games.json in the repository to pin these versions.", dest=dest))
            return finish
        self.run_bg(work)


def main() -> None:
    root = tk.Tk()
    Launcher(root)
    root.mainloop()


if __name__ == "__main__":
    main()

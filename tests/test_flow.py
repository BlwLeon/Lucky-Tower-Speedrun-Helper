"""End-to-End-Test (Linux/macOS): Kernlogik + GUI-Ablauf mit Tk-Mock und lokalem HTTP-Server.
Aufruf: python tests/test_flow.py"""
import os, sys, io, json, tarfile, zipfile, tempfile, threading, time, pathlib, http.server, functools
tmp = tempfile.mkdtemp(); os.environ["HOME"]=tmp; os.environ["XDG_DATA_HOME"]=tmp+"/data"
HERE=pathlib.Path(__file__).resolve().parent
sys.path[:0]=[str(HERE/"fake_tk"), str(HERE.parent)]
import ltl_core as core
# Tests unabhängig vom echten Repo-Inhalt (games.json, swf/) halten
_isolated=pathlib.Path(tmp,"empty_app"); _isolated.mkdir()
core.app_dir=lambda: _isolated; core.resource_dir=lambda: _isolated

# --- 1. Asset-Auswahl mit realistischen Ruffle-Namen
assets=[{"name":n} for n in [
 "ruffle-nightly-2026_11_10-linux-x86_64.tar.gz","ruffle-nightly-2026_11_10-linux-aarch64.tar.gz",
 "ruffle-nightly-2026_11_10-macos-universal.tar.gz","ruffle-nightly-2026_11_10-windows-x86_64.zip",
 "ruffle-nightly-2026_11_10-windows-x86_64.msi","ruffle-nightly-2026_11_10-windows-arm64.zip",
 "ruffle-nightly-2026_11_10-web-selfhosted.zip","ruffle-nightly-2026_11_10-firefox-unsigned.xpi",
 "ruffle-nightly-2026_11_10-web-extension.zip"]]
P=lambda o,a: (core.pick_ruffle_asset(assets,o,a) or {}).get("name")
assert P("windows","x86_64").endswith("windows-x86_64.zip")
assert P("windows","arm64").endswith("windows-arm64.zip")
assert P("macos","arm64").endswith("macos-universal.tar.gz")
assert P("linux","x86_64").endswith("linux-x86_64.tar.gz")
assert P("linux","arm64").endswith("aarch64.tar.gz")
print("asset-pick ok")

# --- 2. Steam-Parsing
vdf='"libraryfolders"\n{\n\t"0"\n\t{\n\t\t"path"\t\t"C:\\\\Program Files (x86)\\\\Steam"\n\t}\n\t"1"\n\t{\n\t\t"path"\t\t"D:\\\\SteamLibrary"\n\t}\n}'
libs=core.parse_library_folders(vdf); assert [str(l) for l in libs]==["C:\\Program Files (x86)\\Steam","D:\\SteamLibrary"], libs
assert core.parse_acf('"AppState"\n{\n\t"appid"\t\t"1700270"\n\t"installdir"\t\t"Lucky Tower Ultimate"\n}')["installdir"]=="Lucky Tower Ultimate"
print("steam-parse ok")

# --- 3. Lokaler Server: SWFs + Ruffle-Archiv
srv=pathlib.Path(tmp,"srv"); srv.mkdir()
(srv/"lt1.swf").write_bytes(b"CWS\x0a"+os.urandom(2000))
(srv/"fake.swf").write_bytes(b"<html>cloudflare</html>")
fake_ruffle=b"#!/bin/sh\necho \"$@\" > \"$(dirname \"$0\")/called.txt\"\n"
buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode="w:gz") as t:
    ti=tarfile.TarInfo("ruffle"); ti.size=len(fake_ruffle); ti.mode=0o644; t.addfile(ti,io.BytesIO(fake_ruffle))
    ti=tarfile.TarInfo("LICENSE.md"); ti.size=3; t.addfile(ti,io.BytesIO(b"MIT"))
(srv/"ruffle-nightly-2026_11_10-linux-x86_64.tar.gz").write_bytes(buf.getvalue())
H=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(srv))
class Q(H.func):
    def log_message(self,*a): pass
s=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(Q,directory=str(srv))); port=s.server_port
threading.Thread(target=s.serve_forever,daemon=True).start()
base=f"http://127.0.0.1:{port}"
for k in ("http_proxy","https_proxy","HTTP_PROXY","HTTPS_PROXY"): os.environ.pop(k,None)
os.environ["NO_PROXY"]="127.0.0.1"

releases=[{"tag_name":"nightly-2026-11-12","draft":False,"assets":[{"name":"ruffle-nightly-2026_11_12-web-selfhosted.zip","browser_download_url":"x"}]},
          {"tag_name":"nightly-2026-11-10","draft":False,"assets":[{"name":"ruffle-nightly-2026_11_10-linux-x86_64.tar.gz","browser_download_url":base+"/ruffle-nightly-2026_11_10-linux-x86_64.tar.gz"}]}]
core.http_json=lambda url,timeout=20: releases if "releases?" in url else releases[1]
root=core.data_dir()
rm=core.RuffleManager(root); msgs=[]
st=rm.ensure(None, lambda t,f: msgs.append(t))
assert st["tag"]=="nightly-2026-11-10" and os.access(st["exe"],os.X_OK), st
assert rm.ensure(None, lambda t,f:None)["tag"]=="nightly-2026-11-10"
print("ruffle install ok:", st["exe"].replace(tmp,"~"))

# --- 4. SWF: TOFU, Manipulation, gepinnter Hash, Nicht-SWF
sm=core.SwfManager(root, strict=False)
g={"id":"lt1","title":"Lucky Tower","url":base+"/lt1.swf","sha256":None}
p,h,v=sm.ensure(g,lambda t,f:None); assert v.startswith("not pinned"), v
p,h2,v=sm.ensure(g,lambda t,f:None); assert v=="same as first download" and h2==h
p.write_bytes(p.read_bytes()+b"x")
try: sm.ensure(g,lambda t,f:None); raise SystemExit("mismatch not detected")
except core.HashMismatch: pass
p,_,v=sm.ensure(g,lambda t,f:None,redownload=True); assert v=="same as first download"
g2=dict(g,sha256=h); assert sm.ensure(g2,lambda t,f:None)[2]=="verified"
g3=dict(g,sha256="0"*64)
try: sm.ensure(g3,lambda t,f:None); raise SystemExit("pinned mismatch not detected")
except core.HashMismatch: pass
try: sm.ensure({"id":"bad","title":"x","url":base+"/fake.swf","sha256":None},lambda t,f:None); raise SystemExit("non-swf accepted")
except RuntimeError as e: assert "not a SWF" in str(e)
# lokaler Import gegen Pin
try: sm.import_local(g3, srv/"lt1.swf"); raise SystemExit("bad local accepted")
except core.HashMismatch: pass
assert sm.import_local(g2, srv/"lt1.swf")[2]=="verified"
print("swf verify ok")

# --- 5. Manifest-Validierung
core.validate_manifest(json.loads(json.dumps(core.DEFAULT_MANIFEST)))
assert all(g["sha256"] for g in core.DEFAULT_MANIFEST["games"]) and core.DEFAULT_MANIFEST["ruffle_tag"]
for bad in ({"games":[{"id":"A B","title":"x","url":"u"}]}, {"games":[{"id":"a","title":"x","url":"u","sha256":"zz"}]}):
    try: core.validate_manifest(bad); raise SystemExit("bad manifest accepted")
    except ValueError: pass
print("manifest ok")

# --- 6. Kompletter Launch über die GUI (Mock-Tk)
import tkinter as tk, launcher
from tkinter import messagebox
launched=[]
class FakeProc:
    def __init__(self, code=0, delay=0.05): self.code, self.delay = code, delay
    def wait(self): time.sleep(self.delay); return self.code
next_proc=[FakeProc()]
def fake_launch(exe,swf,args,log_path=None):
    launched.append((exe,str(swf),args))
    if log_path: log_path.parent.mkdir(parents=True,exist_ok=True); log_path.write_text("ERROR ruffle: Invalid SWF\n")
    return next_proc[0]
core.launch_swf=fake_launch
mf=json.loads(json.dumps(core.DEFAULT_MANIFEST))
for gm in mf["games"]: gm.update(url=base+"/lt1.swf", sha256=None, file=None)
mf["games"][2]["url"]=base+"/missing.swf"; mf["ruffle_tag"]=None
(root/"games.json").write_text(json.dumps(mf))
for f in (root/"games").glob("*"): f.unlink()
os.environ["LTL_DEV"]="1"   # bisherige Abläufe = Entwicklermodus (ungepinnte Test-Dateien)
r=tk.Tk(); app=launcher.Launcher(r); sys.excepthook=sys.__excepthook__
assert app.dev
assert app.manifest_src.endswith("games.json")
def pump(sec=3):
    end=time.time()+sec
    while time.time()<end:
        for fn in list(r._after): r._after.remove(fn); fn()
        if not app.busy and app.q.empty(): break
        time.sleep(0.02)
games=app.manifest["games"]
app.launch(games[1]); pump()
assert launched and launched[-1][1].endswith("lt2_qms.swf"), launched
assert "running" in app.status_text, app.status_text
time.sleep(0.2); pump(1); assert "closed" in app.status_text and "play time" in app.status_text, app.status_text
log=(root/"launch_log.jsonl").read_text().strip().splitlines(); assert json.loads(log[-1])["ruffle"]=="nightly-2026-11-10"
# Manipuliert -> Nachfrage -> Neu laden -> Start
p=root/"games"/"lt2_qms.swf"; p.write_bytes(p.read_bytes()+b"!")
messagebox.answer=True; n=len(launched); app.launch(games[1]); pump(); pump()
assert any(m[0]=="ask" and "Version mismatch" in m[1] for m in messagebox.log) and len(launched)==n+1
# Quelle offline -> lokale Datei
from tkinter import filedialog; filedialog.path=str(srv/"lt1.swf")
n=len(launched); app.launch(games[2]); pump(); pump()
assert any("Download failed" in m[1] for m in messagebox.log) and len(launched)==n+1, messagebox.log
# Hash-Export
app.export_hashes(); pump()
pinned=json.loads((root/"games_pinned.json").read_text())
assert all(len(x["sha256"])==64 for x in pinned["games"]) and pinned["ruffle_tag"]=="nightly-2026-11-10"
assert r.clip.startswith("{")
errs=[m for m in messagebox.log if m[0]=="error"]; assert not errs, errs
print("gui flow ok")

# --- 7. Mitgelieferte SWFs (swf/ neben dem Launcher)
appd=pathlib.Path(tmp,"app"); (appd/"swf").mkdir(parents=True)
(appd/"swf"/"lt2_qms.swf").write_bytes(b"FWS\x09"+os.urandom(500))
core.app_dir=lambda: appd; core.resource_dir=lambda: appd
gb={"id":"lt2_qms","title":"Lucky Tower 2","file":"swf/lt2_qms.swf","url":None,"sha256":None}
core.validate_manifest({"games":[gb]})
p,h,v=sm.ensure(gb,lambda t,f:None); assert p==appd/"swf"/"lt2_qms.swf" and v=="bundled, not pinned", v
assert sm.ensure(dict(gb,sha256=h),lambda t,f:None)[2]=="verified"
assert sm.status(dict(gb,sha256=h))["bundled"]
try: sm.ensure(dict(gb,sha256="1"*64),lambda t,f:None); raise SystemExit("bundled mismatch not detected")
except core.HashMismatch: pass
try: sm.ensure(dict(gb,id="neu_ohne_datei",file="swf/fehlt.swf"),lambda t,f:None); raise SystemExit("missing accepted")
except RuntimeError as e: assert "missing" in str(e)
# Datei fehlt, aber URL vorhanden -> Download
assert sm.ensure({"id":"lt1","title":"x","file":"swf/lt1.swf","url":base+"/lt1.swf","sha256":None},lambda t,f:None)[0]==sm.path_for({"id":"lt1"})
for bad in ({"games":[{"id":"a","title":"x"}]}, {"games":[{"id":"a","title":"x","file":"../evil.swf"}]}):
    try: core.validate_manifest(bad); raise SystemExit("bad file entry accepted")
    except ValueError: pass
# GUI: gepinnte, manipulierte Bundle-Datei -> Fehler, KEINE Download-Nachfrage
asks=len([m for m in messagebox.log if m[0]=="ask"])
app.manifest["games"][1].update(file="swf/lt2_qms.swf", sha256="2"*64)
n=len(launched); app.launch(app.manifest["games"][1]); pump()
assert len(launched)==n and len([m for m in messagebox.log if m[0]=="ask"])==asks
assert messagebox.log[-1][0]=="error" and "not an approved version" in messagebox.log[-1][2]
app.manifest["games"][1]["sha256"]=h; app.launch(app.manifest["games"][1]); pump()
assert launched[-1][1].endswith("swf/lt2_qms.swf")
assert "crash.log" in os.listdir(root)
# Absturz-Handler im GUI-Callback
r.report_callback_exception(ZeroDivisionError, ZeroDivisionError("x"), None)
assert "ZeroDivisionError" in messagebox.log[-1][2]
messagebox.log.clear()
# Leere mitgelieferte Datei (0 Bytes) -> klare Fehlermeldung, kein Start
(appd/"swf"/"lt2_glitchless.swf").write_bytes(b"")
gl=dict(app.manifest["games"][2], file="swf/lt2_glitchless.swf", sha256=None)
n=len(launched); app.launch(gl); pump()
assert len(launched)==n and "not a valid SWF (0 bytes)" in messagebox.log[-1][2], messagebox.log[-1]
# Ersetzte Datei startet danach (kein veralteter Hash gemerkt)
(appd/"swf"/"lt2_glitchless.swf").write_bytes(b"CWS\x0a"+os.urandom(300)); app.launch(gl); pump()
assert len(launched)==n+1; time.sleep(0.2); pump(1)
# Ruffle stürzt sofort ab -> Fehlerdialog mit Log
next_proc[0]=FakeProc(code=1); app.launch(gl); pump(); time.sleep(0.2); pump(1)
assert messagebox.log[-1][1]=="Ruffle error" and "Invalid SWF" in messagebox.log[-1][2], messagebox.log[-1]
assert "error" in app.status_text
next_proc[0]=FakeProc()
print("bundled ok")

# --- 8. pin_hashes.py in einer Repo-Kopie
import shutil, subprocess
repo=pathlib.Path(tmp,"repo"); shutil.copytree(HERE.parent, repo, ignore=shutil.ignore_patterns("tests","__pycache__","docs"))
(repo/"swf").mkdir(exist_ok=True); shutil.copy(appd/"swf"/"lt2_qms.swf", repo/"swf"/"lt2_qms.swf")
out=subprocess.run([sys.executable,str(repo/"pin_hashes.py")],capture_output=True,text=True,cwd=repo); assert out.returncode==0, out.stderr
gj=json.loads((repo/"games.json").read_text()); assert {g["id"]:g["sha256"] for g in gj["games"]}["lt2_qms"]==h
print("pin_hashes ok")

# --- 9. OFFIZIELLER MODUS: keine Umgehung der festgelegten Versionen
os.environ.pop("LTL_DEV")
good=b"CWS\x0a"+b"official"*100; bad=b"CWS\x0a"+b"modded!!"*100
(srv/"official.swf").write_bytes(good); (srv/"modded.swf").write_bytes(bad)
import hashlib
H=lambda b: hashlib.sha256(b).hexdigest()
offd=pathlib.Path(tmp,"offapp"); offd.mkdir()
core.app_dir=lambda: offd; core.resource_dir=lambda: offd
official={"manifest_version":1,"ruffle_tag":"nightly-2026-11-10","games":[
  {"id":"lt1","title":"Lucky Tower","variant":"Official","url":base+"/official.swf","sha256":H(good)},
  {"id":"lt2_x","title":"Lucky Tower 2","variant":"X","url":base+"/official.swf","sha256":H(good)}]}
(offd/"games.json").write_text(json.dumps(official))
# Umgehungsversuche: eigene games.json im Datenordner, manifest_url, Ruffle-Override
evil=json.loads(json.dumps(official)); evil["games"][0].update(url=base+"/modded.swf", sha256=H(bad))
(root/"games.json").write_text(json.dumps(evil))
(root/"settings.json").write_text(json.dumps({"manifest_url":base+"/evil.json","ruffle_tag_override":"nightly-hacked"}))
for f in (root/"games").glob("*"): f.unlink()
remote_calls=[]
_orig_http_json=core.http_json
def hj(url,timeout=20):
    if url==core.OFFICIAL_MANIFEST_URL: remote_calls.append(url); raise OSError("offline")
    if "evil" in url: raise SystemExit("manifest_url darf im offiziellen Modus nicht geladen werden")
    return _orig_http_json(url,timeout)
core.http_json=hj
messagebox.log.clear()
r2=tk.Tk(); app2=launcher.Launcher(r2); sys.excepthook=sys.__excepthook__
assert not app2.dev and app2.manifest_src=="official (built-in)", app2.manifest_src
assert app2.manifest["games"][0]["sha256"]==H(good) and app2._wanted_ruffle_tag()=="nightly-2026-11-10"
def pump2(sec=3):
    end=time.time()+sec
    while time.time()<end:
        for fn in list(r2._after): r2._after.remove(fn); fn()
        if not app2.busy and app2.q.empty(): break
        time.sleep(0.02)
time.sleep(0.1); pump2(); assert remote_calls, "Online-Manifest nicht geprüft"
# offizielle Datei startet
n=len(launched); app2.launch(app2.manifest["games"][0]); pump2()
assert len(launched)==n+1 and not [m for m in messagebox.log if m[0]=="error"], messagebox.log
time.sleep(0.2); pump2(1)
# Modifizierte Datei in den Cache gelegt -> Neu-Laden-Frage -> offizielle wird geladen
(root/"games"/"lt1.swf").write_bytes(bad)
messagebox.answer=True; app2.launch(app2.manifest["games"][0]); pump2(); pump2(); time.sleep(0.2); pump2(1)
assert core.sha256_file(root/"games"/"lt1.swf")==H(good)
# "Downloads neu laden" + Quelle liefert manipulierte Datei -> abgelehnt (kein neuer Hash gemerkt)
app2.clear_cache()
app2.manifest["games"][0]["url"]=base+"/modded.swf"
n=len(launched); messagebox.answer=True; app2.launch(app2.manifest["games"][0]); pump2(); pump2()
assert len(launched)==n and "SHA-256" in messagebox.log[-1][2], messagebox.log[-1]
# Manuelle Auswahl einer modifizierten Datei -> abgelehnt
app2.manifest["games"][0]["url"]=base+"/gibtsnicht.swf"; (root/"games"/"lt1.swf").unlink(missing_ok=True)
filedialog.path=str(srv/"modded.swf"); n=len(launched); app2.launch(app2.manifest["games"][0]); pump2(); pump2()
assert len(launched)==n and messagebox.log[-1][0]=="error", messagebox.log[-1]
# Ungepinnter Eintrag -> NotApproved
gun=dict(app2.manifest["games"][1], sha256=None); n=len(launched); app2.launch(gun); pump2()
assert len(launched)==n and "no officially approved version" in messagebox.log[-1][2], messagebox.log[-1]
try: core.check_official(dict(official, games=[gun])); raise SystemExit("unpinned official accepted")
except ValueError: pass
# Einstellungen: keine Hash-Export-Funktion im offiziellen Modus
app2.go(app2._settings_page)
labels=[b[0] for b in app2.buttons]; assert "EXPORT HASHES" not in labels and "UPDATE RUFFLE" not in labels and "LANGUAGE: ENGLISH" in labels, labels
try: app2.swfs.fetch_raw(app2.manifest["games"][0], lambda t,f:None); raise SystemExit("fetch_raw in strict")
except core.NotApproved: pass
# Launch-Log kennzeichnet Modus
last=json.loads((root/"launch_log.jsonl").read_text().strip().splitlines()[-1]); assert last["mode"]=="official" and last["build"]=="source"
print("official mode ok")

# --- 9b. Sprache: Standard Englisch, Umschalten auf Deutsch wird gespeichert
import ltl_i18n
assert ltl_i18n.get_language()=="en" and json.loads((root/"settings.json").read_text()).get("language","en")=="en"
app2.go(app2._settings_page)
idx=[b[0] for b in app2.buttons].index("LANGUAGE: ENGLISH"); app2.cv.click(f"btn{idx}")
assert ltl_i18n.get_language()=="de" and json.loads((root/"settings.json").read_text())["language"]=="de"
labels=[b[0] for b in app2.buttons]; assert "SPRACHE: DEUTSCH" in labels and "ZURÜCK" in labels and app2.subtitle=="EINSTELLUNGEN", labels
app2.show_main(); assert "EINSTELLUNGEN" in [b[0] for b in app2.buttons]
app2.go(lambda: app2._game_page("Lucky Tower")); assert app2.buttons[-1][0]=="ZURÜCK" and "Quelle:" in app2.buttons[0][2], app2.buttons
assert ltl_i18n._(app2.manifest["games"][0].get("label") or "PLAY") in ("SPIELEN","OFFICIAL") and ltl_i18n._("PLAY")=="SPIELEN"
# deutsche Fehlermeldungen aus dem Kern
gun2=dict(app2.manifest["games"][1], sha256=None); app2.launch(gun2); pump2()
assert "keine offiziell freigegebene Version" in messagebox.log[-1][2], messagebox.log[-1]
# Neustart übernimmt gespeicherte Sprache
r3=tk.Tk(); app3=launcher.Launcher(r3); sys.excepthook=sys.__excepthook__
assert ltl_i18n.get_language()=="de" and "EINSTELLUNGEN" in [b[0] for b in app3.buttons]
# zurück auf Englisch
app3.go(app3._settings_page); idx=[b[0] for b in app3.buttons].index("SPRACHE: DEUTSCH"); app3.cv.click(f"btn{idx}")
assert ltl_i18n.get_language()=="en" and "LANGUAGE: ENGLISH" in [b[0] for b in app3.buttons]
# alle deutschen Übersetzungen haben dieselben Platzhalter wie das Englische
import string
for en,de in ltl_i18n.DE.items():
    f=lambda t: sorted({x[1] for x in string.Formatter().parse(t) if x[1]})
    assert f(en)==f(de), (en,de)
print("language ok")

# --- 10. Ruffle-Fingerabdruck + GitHub-Prüfsumme
pid=core.platform_id()
st=rm.installed(); real=core.sha256_file(pathlib.Path(st["exe"]))
assert rm.verify(st,{pid:real}) is True and rm.verify(st,{}) is None
pathlib.Path(st["exe"]).write_bytes(b"#!/bin/sh\necho speedhack\n")      # Binary manipuliert
st2=rm.ensure("nightly-2026-11-10", lambda t,f:None, pins={pid:real})     # -> automatisch neu installiert
assert core.sha256_file(pathlib.Path(st2["exe"]))==real
try: rm.ensure("nightly-2026-11-10", lambda t,f:None, pins={pid:"0"*64}); raise SystemExit("wrong ruffle accepted")
except core.NotApproved: pass
releases[1]["assets"][0]["digest"]="sha256:"+"f"*64
try: rm.ensure("nightly-2026-11-10", lambda t,f:None, reinstall=True); raise SystemExit("digest mismatch accepted")
except core.NotApproved as e: assert "checksum" in str(e)
releases[1]["assets"][0]["digest"]="sha256:"+core.sha256_file(srv/"ruffle-nightly-2026_11_10-linux-x86_64.tar.gz")
assert rm.ensure("nightly-2026-11-10", lambda t,f:None, reinstall=True, pins={pid:real})["tag"]=="nightly-2026-11-10"
# Ruffle-Release verschwunden -> Spiegel (nur mit Pin), Binary wird geprüft
_hj=core.http_json
def gone(url,timeout=20): raise OSError("404 release deleted")
core.http_json=gone
mir={pid: base+"/ruffle-nightly-2026_11_10-linux-x86_64.tar.gz"}
assert rm.ensure("nightly-2026-11-10", lambda t,f:None, reinstall=True, pins={pid:real}, mirrors=mir)["tag"]=="nightly-2026-11-10"
try: rm.ensure("nightly-2026-11-10", lambda t,f:None, reinstall=True, mirrors=mir); raise SystemExit("mirror without pin used")
except OSError: pass
try: rm.ensure("nightly-2026-11-10", lambda t,f:None, reinstall=True, pins={pid:"1"*64}, mirrors=mir); raise SystemExit("bad mirror accepted")
except core.NotApproved: pass
core.http_json=_hj
print("ruffle pin ok")

print("ALLE TESTS OK")

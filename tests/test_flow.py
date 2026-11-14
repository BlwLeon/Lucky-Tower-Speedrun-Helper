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
sm=core.SwfManager(root)
g={"id":"lt1","title":"Lucky Tower","url":base+"/lt1.swf","sha256":None}
p,h,v=sm.ensure(g,lambda t,f:None); assert v.startswith("nicht gepinnt"), v
p,h2,v=sm.ensure(g,lambda t,f:None); assert v=="wie erster Download" and h2==h
p.write_bytes(p.read_bytes()+b"x")
try: sm.ensure(g,lambda t,f:None); raise SystemExit("mismatch not detected")
except core.HashMismatch: pass
p,_,v=sm.ensure(g,lambda t,f:None,redownload=True); assert v=="wie erster Download"
g2=dict(g,sha256=h); assert sm.ensure(g2,lambda t,f:None)[2]=="verifiziert"
g3=dict(g,sha256="0"*64)
try: sm.ensure(g3,lambda t,f:None); raise SystemExit("pinned mismatch not detected")
except core.HashMismatch: pass
try: sm.ensure({"id":"bad","title":"x","url":base+"/fake.swf","sha256":None},lambda t,f:None); raise SystemExit("non-swf accepted")
except RuntimeError as e: assert "keine SWF" in str(e)
# lokaler Import gegen Pin
try: sm.import_local(g3, srv/"lt1.swf"); raise SystemExit("bad local accepted")
except core.HashMismatch: pass
assert sm.import_local(g2, srv/"lt1.swf")[2]=="verifiziert"
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
r=tk.Tk(); app=launcher.Launcher(r); sys.excepthook=sys.__excepthook__
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
assert "läuft" in app.status_text, app.status_text
time.sleep(0.2); pump(1); assert "beendet" in app.status_text and "Spielzeit" in app.status_text, app.status_text
log=(root/"launch_log.jsonl").read_text().strip().splitlines(); assert json.loads(log[-1])["ruffle"]=="nightly-2026-11-10"
# Manipuliert -> Nachfrage -> Neu laden -> Start
p=root/"games"/"lt2_qms.swf"; p.write_bytes(p.read_bytes()+b"!")
messagebox.answer=True; n=len(launched); app.launch(games[1]); pump(); pump()
assert any(m[0]=="ask" and "Version stimmt nicht" in m[1] for m in messagebox.log) and len(launched)==n+1
# Quelle offline -> lokale Datei
from tkinter import filedialog; filedialog.path=str(srv/"lt1.swf")
n=len(launched); app.launch(games[2]); pump(); pump()
assert any("Download fehlgeschlagen" in m[1] for m in messagebox.log) and len(launched)==n+1, messagebox.log
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
p,h,v=sm.ensure(gb,lambda t,f:None); assert p==appd/"swf"/"lt2_qms.swf" and v=="mitgeliefert, nicht gepinnt", v
assert sm.ensure(dict(gb,sha256=h),lambda t,f:None)[2]=="verifiziert"
assert sm.status(dict(gb,sha256=h))["bundled"]
try: sm.ensure(dict(gb,sha256="1"*64),lambda t,f:None); raise SystemExit("bundled mismatch not detected")
except core.HashMismatch: pass
try: sm.ensure(dict(gb,id="neu_ohne_datei",file="swf/fehlt.swf"),lambda t,f:None); raise SystemExit("missing accepted")
except RuntimeError as e: assert "fehlt" in str(e)
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
assert messagebox.log[-1][0]=="error" and "keine zugelassene Version" in messagebox.log[-1][2]
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
assert len(launched)==n and "keine gültige SWF (0 Bytes)" in messagebox.log[-1][2], messagebox.log[-1]
# Ersetzte Datei startet danach (kein veralteter Hash gemerkt)
(appd/"swf"/"lt2_glitchless.swf").write_bytes(b"CWS\x0a"+os.urandom(300)); app.launch(gl); pump()
assert len(launched)==n+1; time.sleep(0.2); pump(1)
# Ruffle stürzt sofort ab -> Fehlerdialog mit Log
next_proc[0]=FakeProc(code=1); app.launch(gl); pump(); time.sleep(0.2); pump(1)
assert messagebox.log[-1][1]=="Ruffle-Fehler" and "Invalid SWF" in messagebox.log[-1][2], messagebox.log[-1]
assert "Fehler" in app.status_text
next_proc[0]=FakeProc()
print("bundled ok")

# --- 8. pin_hashes.py in einer Repo-Kopie
import shutil, subprocess
repo=pathlib.Path(tmp,"repo"); shutil.copytree(HERE.parent, repo, ignore=shutil.ignore_patterns("tests","__pycache__","docs"))
(repo/"swf").mkdir(exist_ok=True); shutil.copy(appd/"swf"/"lt2_qms.swf", repo/"swf"/"lt2_qms.swf")
out=subprocess.run([sys.executable,str(repo/"pin_hashes.py")],capture_output=True,text=True,cwd=repo); assert out.returncode==0, out.stderr
gj=json.loads((repo/"games.json").read_text()); assert {g["id"]:g["sha256"] for g in gj["games"]}["lt2_qms"]==h
print("pin_hashes ok")

print("ALLE TESTS OK")

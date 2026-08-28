#!/usr/bin/env python3
"""Valida en segundo plano que los fondos de Wallpaper Engine arrancan
con linux-wallpaperengine. Guarda el resultado en
~/.cache/wallpaper-picker/we_validated.json para que list_wallpapers.py
pueda ordenar los que funcionan primero."""
import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

THUMB_DIR = Path.home() / ".cache/wallpaper-picker"
VALIDATE_CACHE = THUMB_DIR / "we_validated.json"
WE_WORKSHOP_DIR = Path.home() / ".local/share/Steam/steamapps/workshop/content/431960"
WE_DEFAULT_DIR = Path.home() / ".local/share/Steam/steamapps/common/wallpaper_engine/projects/defaultprojects"
PID_FILE = THUMB_DIR / "we_validate.pid"
TEST_SECS = 3
# Secuencial: varias instancias en la capa background se suspenden entre si
# y darian falsos positivos.
WORKERS = 1


def engine_sig() -> str:
    exe = shutil.which("linux-wallpaperengine")
    if not exe:
        return ""
    try:
        st = Path(exe).stat()
        return f"{st.st_mtime_ns}:{st.st_size}"
    except OSError:
        return ""


def load_cache(sig: str) -> dict:
    try:
        data = json.loads(VALIDATE_CACHE.read_text())
        if data.get("engine") != sig:
            return {}
        entries = data.get("entries", {})
        return entries if isinstance(entries, dict) else {}
    except Exception:
        return {}


def first_monitor() -> str:
    try:
        out = subprocess.run(["hyprctl", "monitors", "-j"],
                             capture_output=True, text=True, timeout=5)
        data = json.loads(out.stdout)
        if data:
            return data[0].get("name", "")
    except Exception:
        pass
    return ""


def we_works(proj: Path) -> bool:
    cmd = ["linux-wallpaperengine", "--silent", "--layer", "background"]
    mon = first_monitor()
    if mon:
        cmd += ["--screen-root", mon]
    cmd.append(str(proj))
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
    except Exception:
        return False
    try:
        proc.wait(timeout=TEST_SECS)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
        return True
    return False


def main() -> int:
    sig = engine_sig()
    if not sig:
        return 0
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    if PID_FILE.exists():
        try:
            old = int(PID_FILE.read_text().strip())
            try:
                os.kill(old, 0)
                return 0
            except OSError:
                pass
        except Exception:
            pass
    PID_FILE.write_text(str(os.getpid()))
    try:
        cache = load_cache(sig)
        jobs = []
        for base in (WE_WORKSHOP_DIR, WE_DEFAULT_DIR):
            if not base.exists():
                continue
            for proj in sorted(p for p in base.iterdir() if p.is_dir()):
                if not (proj / "scene.pkg").exists() and not (proj / "project.json").exists():
                    continue
                try:
                    mtime = proj.stat().st_mtime_ns
                except OSError:
                    continue
                entry = cache.get(str(proj))
                if entry is None or entry.get("mtime") != mtime:
                    jobs.append(proj)
        if jobs:
            with ThreadPoolExecutor(max_workers=WORKERS) as ex:
                for proj, ok in zip(jobs, ex.map(we_works, jobs)):
                    try:
                        mtime = proj.stat().st_mtime_ns
                    except OSError:
                        continue
                    cache[str(proj)] = {"mtime": mtime, "ok": ok}
            VALIDATE_CACHE.write_text(json.dumps({"engine": sig, "entries": cache}))
        return 0
    finally:
        try:
            PID_FILE.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())

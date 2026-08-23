#!/usr/bin/env python3
"""Descarga fondos anime (SFW, =1920x1080) por temática desde Wallhaven."""
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

import gi

gi.require_version("Gdk", "3.0")
from gi.repository import GdkPixbuf

OUT_DIR = os.path.expanduser("~/Pictures/Wallpapers/predefinidos")
W, H = 1920, 1080
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

THEMES = {
    "alegre": "anime cherry blossom",
    "fantasia": "anime fantasy landscape",
    "oscuro": "anime dark gothic",
    "triste": "anime sad rain",
    "naturaleza": "anime forest scenery",
    "neon": "anime cyberpunk neon",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def search(paths, q):
    url = (
        "https://wallhaven.cc/api/v1/search?categories=010&purity=100"
        f"&atleast={W}x{H}&sorting=random&q=" + urllib.parse.quote(q)
    )
    data = json.loads(fetch(url))
    for it in data.get("data", []):
        paths.append(it["path"])


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)


def cover(pb):
    iw, ih = pb.get_width(), pb.get_height()
    if iw / ih > W / H:
        ch = ih
        cw = int(ch * W / H)
        sx = (iw - cw) // 2
        pb = pb.new_subpixbuf(sx, 0, cw, ch)
    else:
        cw = iw
        ch = int(cw * H / W)
        sy = (ih - ch) // 2
        pb = pb.new_subpixbuf(0, sy, cw, ch)
    return pb.scale_simple(W, H, GdkPixbuf.InterpType.BILINEAR)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, q in THEMES.items():
        paths = []
        for _ in range(3):
            try:
                search(paths, q)
                break
            except Exception as e:
                print(f"{name}: reintentando ({e})", file=sys.stderr)
        if not paths:
            print(f"{name}: SIN RESULTADOS", file=sys.stderr)
            continue
        src = os.path.join("/tmp/opencode", f"{name}.download")
        done = False
        for url in paths:
            try:
                download(url, src)
                pb = GdkPixbuf.Pixbuf.new_from_file(src)
                out = os.path.join(OUT_DIR, f"{name}.png")
                cover(pb).savev(out, "png", [], [])
                print(f"{name}: OK {pb.get_width()}x{pb.get_height()} <- {url}")
                done = True
                break
            except Exception as e:
                print(f"{name}: fallo {url} ({e})", file=sys.stderr)
        if not done:
            print(f"{name}: NO SE PUDO DESCARGAR", file=sys.stderr)


if __name__ == "__main__":
    main()
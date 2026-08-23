#!/usr/bin/env python3
"""Descarga fondos de pantalla por género (SFW, =1920x1080) desde Wallhaven."""
import json
import os
import sys
import urllib.parse
import urllib.request

import gi

gi.require_version("Gdk", "3.0")
from gi.repository import GdkPixbuf

ROOT = os.path.expanduser("~/Pictures/Wallpapers")
GENRES_DIR = os.path.join(ROOT, "genres")
THUMBS_DIR = os.path.join(ROOT, ".thumbs")
W, H = 1920, 1080
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

GENRES = {
    "naturaleza": ["nature landscape", "mountain lake landscape"],
    "ciudad": ["cyberpunk city night", "city street neon night"],
    "espacio": ["nebula deep space galaxy", "stars milky way night sky"],
    "oceano": ["ocean waves blue", "underwater sea coral"],
    "fantasia": ["fantasy castle landscape", "magical forest fog"],
    "minimalista": ["minimal mountain graphic", "minimal abstract colors"],
    "abstracto": ["colorful abstract fluid", "gradient waves colors"],
    "oscuro": ["black white portrait shadow", "dark forest"],
    "neon": ["neon signs night", "retro synthwave grid"],
    "alegre": ["colorful spring flowers", "bird flying blue sky"],
    "triste": ["rainy window", "melancholy sad"],
    "cafe": ["coffee cup", "latte art"],
}


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def search(q, page=1):
    url = (
        "https://wallhaven.cc/api/v1/search?categories=111&purity=100"
        f"&atleast={W}x{H}&sorting=random&page={page}&q=" + urllib.parse.quote(q)
    )
    return json.loads(fetch(url)).get("data", [])


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


def thumb_of(pb, path):
    tw, thh = 168, 94
    iw, ih = pb.get_width(), pb.get_height()
    if iw / ih > tw / thh:
        ch = ih
        cw = int(ch * tw / thh)
        sx = (iw - cw) // 2
        pb = pb.new_subpixbuf(sx, 0, cw, ch)
    else:
        cw = iw
        ch = int(cw * thh / tw)
        sy = (ih - ch) // 2
        pb = pb.new_subpixbuf(0, sy, cw, ch)
    pb.scale_simple(tw, thh, GdkPixbuf.InterpType.BILINEAR).savev(path, "png", [], [])


def download_genre(name, queries, want, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(THUMBS_DIR, exist_ok=True)
    existing = [f for f in os.listdir(out_dir) if f.lower().endswith((".jpg", ".png", ".jpeg", ".webp"))]
    start = len(existing)
    target = max(want, start + want)
    got = start
    page = max(1, start // 4 + 1)
    tried = set()
    while got < target and page <= 8:
        items = []
        for _ in range(3):
            try:
                items = search(queries[got % len(queries)], page)
                break
            except Exception as e:
                print(f"{name}: reintento ({e})", file=sys.stderr)
        if not items:
            page += 1
            continue
        for it in items:
            if got >= target:
                break
            path = it.get("path", "")
            if not path or path in tried:
                continue
            tried.add(path)
            try:
                raw = fetch(path, timeout=90)
                src = os.path.join("/tmp/opencode", f"{name}_src.png")
                with open(src, "wb") as f:
                    f.write(raw)
                pb = GdkPixbuf.Pixbuf.new_from_file(src)
                out = os.path.join(out_dir, f"{got:03d}.png")
                cover(pb).savev(out, "png", [], [])
                thumb_of(pb, os.path.join(THUMBS_DIR, f"{name}_{got:03d}.png"))
                print(f"{name}: #{got} OK <- {os.path.basename(path)}", file=sys.stderr)
                got += 1
            except Exception as e:
                print(f"{name}: fallo {path[:80]} ({e})", file=sys.stderr)
        page += 1
    return got


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    want = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    total = 0
    for name, queries in GENRES.items():
        if only and name != only:
            continue
        n = download_genre(name, queries, want, os.path.join(GENRES_DIR, name))
        total += n
        print(f"{name}: {n} fondos", file=sys.stderr)
    print(f"TOTAL: {total}", file=sys.stderr)


if __name__ == "__main__":
    main()
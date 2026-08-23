#!/usr/bin/env python3
"""Genera fondos animados (loop Ken Burns) desde imágenes de ~/Pictures/Wallpapers/genres/.
Salida: ~/Pictures/Wallpapers/animados/<name>.mp4
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path.home() / "Pictures/Wallpapers"
GENRES_DIR = ROOT / "genres"
ANIM_DIR = ROOT / "animados"
THUMBS_DIR = ROOT / ".thumbs"
W, H = 1920, 1080
DUR = 8
FPS = 25
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def gen_one(name, image, frames, out):
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-i", str(image),
        "-vf", (
            f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,"
            f"crop={W*2}:{H*2},"
            f"zoompan=z='min(zoom+0.0018,1.45)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
            f"format=yuv420p"
        ),
        "-t", str(DUR), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-an", str(out),
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def main():
    ANIM_DIR.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1] if len(sys.argv) > 1 else None
    made = 0
    for genre in sorted(p for p in GENRES_DIR.iterdir() if p.is_dir()):
        if only and genre.name != only:
            continue
        first = None
        for f in sorted(genre.iterdir()):
            if f.is_file() and f.suffix.lower() in IMG_EXTS:
                first = f
                break
        if not first:
            print(f"{genre.name}: sin imagen", file=sys.stderr)
            continue
        out = ANIM_DIR / f"{genre.name}.mp4"
        if out.exists():
            out.unlink()
        r = gen_one(genre.name, first, DUR * FPS, out)
        if r.returncode != 0:
            print(f"{genre.name}: ERROR {r.stderr[-300:]}", file=sys.stderr)
            continue
        thumb = THUMBS_DIR / f"animated_{genre.name}.png"
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(out), "-frames:v", "1", "-vf", "scale=168:94", str(thumb),
            ],
            capture_output=True,
        )
        print(f"{genre.name}: OK -> {out.name} ({out.stat().st_size//1024} KB)", file=sys.stderr)
        made += 1
    print(f"ANIMADOS: {made}", file=sys.stderr)


if __name__ == "__main__":
    main()
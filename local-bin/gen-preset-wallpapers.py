#!/usr/bin/env python3
"""Genera los fondos de pantalla predefinidos (1920x1080) en ~/Pictures/Wallpapers/predefinidos/."""
import math
import struct
import sys
import zlib
from pathlib import Path

W, H = 1920, 1080
OUT_DIR = Path.home() / "Pictures/Wallpapers/predefinidos"


def chunk(tag, data):
    c = struct.pack(">I", len(data)) + tag + data
    return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def write_png(path, fn):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = b""
    for y in range(H):
        row = bytearray(b"\x00")
        base = fn.colors(y)
        for x in range(W):
            r, g, b = base
            nx, ny = (x + 0.5) / W, (y + 0.5) / H
            for cx, cy, rr, (gr, gg, gb) in fn.glows:
                dx, dy = nx - cx, ny - cy
                d2 = dx * dx + dy * dy
                if d2 < 1.0:
                    t = max(0.0, 1.0 - math.sqrt(d2) / rr)
                    if t > 0:
                        f = t ** 2.0
                        r += int((gr - r) * f)
                        g += int((gg - g) * f)
                        b += int((gb - b) * f)
            row += bytes((min(r, 255), min(g, 255), min(b, 255)))
        rows += bytes(row)
        sys.stdout.write(f"\r{path.stem}: {y+1}/{H}")
        sys.stdout.flush()
    sys.stdout.write("\n")
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows, 6))
        + chunk(b"IEND", b"")
    )
    (OUT_DIR / path).write_bytes(png)


def pal(top, mid, bot, glows):
    return type("P", (), {"colors": (lambda y: _col(top, mid, bot, y)), "glows": glows})


def _col(top, mid, bot, y):
    t = y / (H - 1)
    if t < 0.5:
        f = t / 0.5
        return tuple(int(a + (b - a) * f) for a, b in zip(top, mid))
    f = (t - 0.5) / 0.5
    return tuple(int(a + (b - a) * f) for a, b in zip(mid, bot))


PRESETS = {
    "violet.png": pal(
        (58, 31, 111), (36, 19, 71), (14, 6, 38),
        [(0.78, 0.25, 0.55, (139, 92, 246)), (0.20, 0.78, 0.50, (217, 70, 239)), (0.42, 0.55, 0.70, (109, 40, 217))],
    ),
    "ocean.png": pal(
        (15, 32, 86), (23, 92, 132), (5, 18, 40),
        [(0.72, 0.30, 0.60, (34, 211, 238)), (0.25, 0.72, 0.55, (59, 130, 246)), (0.50, 0.52, 0.75, (45, 212, 191))],
    ),
    "sunset.png": pal(
        (124, 45, 18), (194, 65, 12), (42, 12, 4),
        [(0.72, 0.32, 0.60, (251, 146, 60)), (0.28, 0.68, 0.50, (236, 72, 153)), (0.50, 0.45, 0.70, (251, 191, 36))],
    ),
    "forest.png": pal(
        (17, 50, 32), (31, 96, 54), (9, 33, 22),
        [(0.32, 0.38, 0.60, (34, 197, 94)), (0.70, 0.62, 0.52, (52, 211, 153)), (0.48, 0.28, 0.62, (44, 140, 84))],
    ),
    "midnight.png": pal(
        (17, 24, 39), (30, 52, 110), (4, 7, 16),
        [(0.66, 0.30, 0.60, (99, 102, 241)), (0.25, 0.72, 0.55, (14, 165, 233)), (0.44, 0.50, 0.70, (139, 92, 246))],
    ),
    "dawn.png": pal(
        (48, 26, 52), (92, 36, 84), (26, 16, 30),
        [(0.70, 0.35, 0.60, (244, 114, 182)), (0.26, 0.68, 0.55, (251, 113, 133)), (0.50, 0.48, 0.72, (167, 139, 250))],
    ),
}

for name, fn in PRESETS.items():
    write_png(Path(name), fn)

print("Listo:", len(PRESETS), "fondos en", OUT_DIR)
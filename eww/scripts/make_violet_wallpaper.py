#!/usr/bin/env python3
"""Genera un fondo de pantalla 1920x1080 con degradado violeta y brillos radiales."""
import struct
import zlib
import math

W, H = 1920, 1080
OUT = "/home/jairo/Pictures/Wallpapers/violet-gradient.png"

def chunk(tag, data):
    c = struct.pack(">I", len(data)) + tag + data
    return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

# Base: degradado vertical
def base_color(y):
    t = y / (H - 1)
    # top -> mid -> bottom
    if t < 0.5:
        f = t / 0.5
        r = int(58 + (36 - 58) * f)
        g = int(31 + (19 - 31) * f)
        b = int(111 + (71 - 111) * f)
    else:
        f = (t - 0.5) / 0.5
        r = int(36 + (14 - 36) * f)
        g = int(19 + (6 - 19) * f)
        b = int(71 + (38 - 71) * f)
    return r, g, b

# Brillos radiales: (cx, cy, radius, color)
GLOWS = [
    (0.78, 0.25, 0.55, (139, 92, 246)),
    (0.20, 0.78, 0.50, (217, 70, 239)),
    (0.42, 0.55, 0.70, (109, 40, 217)),
]

rows = b""
for y in range(H):
    row = bytearray(b"\x00")
    base_r, base_g, base_b = base_color(y)
    for x in range(W):
        r, g, b = base_r, base_g, base_b
        nx, ny = x / W, y / H
        for cx, cy, rr, (gr, gg, gb) in GLOWS:
            dx = nx - cx
            dy = ny - cy
            d2 = dx * dx + dy * dy
            if d2 < 1.0:
                t = max(0.0, 1.0 - math.sqrt(d2) / rr)
                f = t ** 2.2
                if f > 0:
                    r += int((gr - r) * f)
                    g += int((gg - g) * f)
                    b += int((gb - b) * f)
        row += bytes((min(r, 255), min(g, 255), min(b, 255)))
    rows += bytes(row)

png = (
    b"\x89PNG\r\n\x1a\n"
    + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    + chunk(b"IDAT", zlib.compress(rows, 6))
    + chunk(b"IEND", b"")
)

with open(OUT, "wb") as f:
    f.write(png)
print("ok", OUT)
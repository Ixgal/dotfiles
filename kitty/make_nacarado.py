#!/usr/bin/env python3
"""Genera un PNG con alfa: parte superior transparente y un nacarado violeta
sutil en la parte inferior (para usarlo como background_image de kitty)."""
import struct
import zlib
import math

W, H = 1920, 1080
OUT = "/home/jairo/.config/kitty/violet-nacarado.png"

BAND_START = 0.52
ALPHA_MAX = 0.42

def chunk(tag, data):
    c = struct.pack(">I", len(data)) + tag + data
    return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

rows = b""
for y in range(H):
    row = bytearray(b"\x00")
    t = y / (H - 1)
    if t >= BAND_START:
        p = min(1.0, (t - BAND_START) / (1.0 - BAND_START))
        px = p * p
        r0, g0, b0 = 124, 58, 237
        r1, g1, b1 = 233, 213, 255
        r = r0 + (r1 - r0) * px
        g = g0 + (g1 - g0) * px
        b = b0 + (b1 - b0) * px
        for x in range(W):
            nx = x / (W - 1)
            wave = 0.5 + 0.5 * math.sin(nx * 6.283 + t * 5.0)
            sheen = 1.0 + 0.22 * wave
            highlight = math.exp(-((p - 0.84) ** 2) / 0.045)
            rr = min(235, r * sheen + 40 * highlight)
            gg = min(215, g * sheen + 60 * highlight)
            bb = min(250, b * sheen + 95 * highlight)
            a = int(255 * ALPHA_MAX * math.sin(p * math.pi / 2))
            row += bytes((int(rr), int(gg), int(bb), a))
    else:
        row += b"\x00\x00\x00\x00" * W
    rows += bytes(row)

png = (
    b"\x89PNG\r\n\x1a\n"
    + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0))
    + chunk(b"IDAT", zlib.compress(rows, 6))
    + chunk(b"IEND", b"")
)

with open(OUT, "wb") as f:
    f.write(png)
print("ok", OUT)
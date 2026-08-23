#!/usr/bin/env python3
"""Genera un PNG de 180x108 (gris) usado como placeholder de preview."""
import struct
import zlib

W, H = 180, 108

def chunk(tag: bytes, data: bytes) -> bytes:
    c = struct.pack(">I", len(data)) + tag + data
    return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

rows = b""
row = b"\x00" + b"\x2b\x2b\x2b" * W
for _ in range(H):
    rows += row

png = (
    b"\x89PNG\r\n\x1a\n"
    + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    + chunk(b"IDAT", zlib.compress(rows))
    + chunk(b"IEND", b"")
)

with open(__file__ if None else "/home/jairo/.config/eww/scripts/placeholder.png", "wb") as f:
    f.write(png)
print("ok")
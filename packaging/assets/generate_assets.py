"""Generate required installer assets (icon, BMPs, LICENSE).
Run once from project root:
    python packaging/assets/generate_assets.py
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent


# ── ICO generator (multi-resolution .ico from raw RGBA) ──────────────
def _write_ico(buf, sizes: list[tuple[int, int, bytes]]):
    """Write a .ico file with the given (w, h, png_bytes) entries."""
    count = len(sizes)
    # ICONDIR
    buf.write(struct.pack("<HHH", 0, 1, count))
    offset = 6 + 16 * count
    images: list[tuple[int, int, bytes]] = []
    for w, h, data in sizes:
        imgsize = len(data)
        buf.write(struct.pack("<BBBBHHII", w if w < 256 else 0, h if h < 256 else 0, 0, 0, 1, 32, imgsize, offset))
        offset += imgsize
        images.append((w, h, data))
    for _, _, data in images:
        buf.write(data)


def _png_rgba(w: int, h: int, pixels: list[list[tuple[int, int, int, int]]]) -> bytes:
    """Minimal RGBA PNG encoder (no compression tuning — good enough for icons)."""
    def chunk(ctype: bytes, data: bytes) -> bytes:
        c = ctype + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    raw = b""
    for y in range(h):
        raw += b"\x00"  # filter none
        for x in range(w):
            r, g, b, a = pixels[y][x]
            raw += struct.pack("BBBB", r, g, b, a)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _star_icon_pixels(size: int) -> list[list[tuple[int, int, int, int]]]:
    """A simple purple star/gem icon — Star-Learn brand."""
    # Colors
    BG = (0, 0, 0, 0)          # transparent
    PURPLE = (138, 43, 226)     # blueviolet
    PURPLE_L = (180, 120, 240)  # light
    PURPLE_D = (80, 20, 140)    # dark
    WHITE = (255, 255, 255)

    px = [[BG for _ in range(size)] for _ in range(size)]
    cx, cy = size / 2, size / 2
    r_outer = size * 0.44
    r_inner = size * 0.18

    for y in range(size):
        for x in range(size):
            dx, dy = x - cx, y - cy
            dist = (dx * dx + dy * dy) ** 0.5
            # Star shape: 5-pointed
            angle = __import__("math").atan2(dy, dx)
            # 5-point star modulation
            tip_angle = __import__("math").pi * 2 / 5
            a_mod = (angle % tip_angle) - tip_angle / 2
            star_r = r_inner + (r_outer - r_inner) * (1 - abs(a_mod) / (tip_angle / 2)) ** 2

            if dist < star_r:
                t = dist / r_outer
                # Gradient from light (center) to dark purple (edge)
                r = int(PURPLE_L[0] + (PURPLE_D[0] - PURPLE_L[0]) * t)
                g = int(PURPLE_L[1] + (PURPLE_D[1] - PURPLE_L[1]) * t)
                b = int(PURPLE_L[2] + (PURPLE_D[2] - PURPLE_L[2]) * t)
                px[y][x] = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)), 255)

    return px


def generate_icon() -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    ico_sizes: list[tuple[int, int, bytes]] = []
    for s in sizes:
        pixels = _star_icon_pixels(s)
        png_data = _png_rgba(s, s, pixels)
        ico_sizes.append((s, s, png_data))
        print(f"  Generated {s}x{s} icon layer ({len(png_data)} bytes)")

    out = HERE / "icon.ico"
    with open(out, "wb") as f:
        _write_ico(f, ico_sizes)
    print(f"[assets] Icon saved → {out}")


# ── BMP generators (164×314 sidebar, 55×55 header) ──────────────────
def _write_bmp(path: Path, w: int, h: int, color: tuple[int, int, int]) -> None:
    """24-bit BMP with solid color and a subtle gradient."""
    row_size = (w * 3 + 3) & ~3
    pixel_data = bytearray()
    for y in range(h):
        row = bytearray()
        for x in range(w):
            t_y = y / max(h - 1, 1)
            t_x = x / max(w - 1, 1)
            # Subtle gradient
            r = int(color[0] * (0.7 + 0.3 * t_y))
            g = int(color[1] * (0.7 + 0.3 * t_y) * (0.8 + 0.2 * t_x))
            b = int(color[2] * (0.7 + 0.3 * t_y) * (0.8 + 0.2 * (1 - t_x)))
            row += struct.pack("BBB", min(255, b), min(255, g), min(255, r))
        row += b"\x00" * (row_size - w * 3)
        pixel_data += row

    file_size = 14 + 40 + len(pixel_data)
    with open(path, "wb") as f:
        # BMP file header
        f.write(b"BM")
        f.write(struct.pack("<I", file_size))
        f.write(struct.pack("<HH", 0, 0))
        f.write(struct.pack("<I", 14 + 40))
        # DIB header (BITMAPINFOHEADER)
        f.write(struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(pixel_data), 2835, 2835, 0, 0))
        f.write(pixel_data)


def generate_bmps() -> None:
    purple = (100, 30, 180)
    sidebar = HERE / "installer-sidebar.bmp"
    _write_bmp(sidebar, 164, 314, purple)
    print(f"[assets] Sidebar BMP saved → {sidebar}")

    header = HERE / "installer-header.bmp"
    _write_bmp(header, 55, 55, purple)
    print(f"[assets] Header BMP saved → {header}")


# ── LICENSE ──────────────────────────────────────────────────────────
LICENSE_TEXT = """MIT License

Copyright (c) 2025 Star-Learn (星识)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def generate_license() -> None:
    out = HERE / "LICENSE.txt"
    out.write_text(LICENSE_TEXT, encoding="utf-8")
    print(f"[assets] License saved → {out}")


# ── main ─────────────────────────────────────────────────────────────
def main() -> None:
    print("[assets] Generating installer assets...")
    generate_icon()
    generate_bmps()
    generate_license()
    print("[assets] All assets generated.")


if __name__ == "__main__":
    main()

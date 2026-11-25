#!/usr/bin/env python3
"""news-image-20261125: draw a one-image summary of Wednesday 25 Nov 2026.

Flat risograph / screen-print front-page poster, 1024x1024, four colours only.
Pure standard library: zlib + struct PNG encoder, no network, no clock,
no randomness. Deterministic: two runs write byte-identical output.
"""
import os
import struct
import zlib
from math import isqrt

W, H = 1024, 1024

CREAM = (242, 232, 213)
TERRA = (196, 71, 31)
OLIVE = (46, 59, 42)
INK = (20, 18, 16)

# ---------------------------------------------------------------- canvas ----
PIX = bytearray(W * H * 3)


def fill_rect(x, y, w, h, color):
    if w <= 0 or h <= 0:
        return
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    if x0 >= x1 or y0 >= y1:
        return
    row = bytes(color) * (x1 - x0)
    for yy in range(y0, y1):
        off = (yy * W + x0) * 3
        PIX[off:off + len(row)] = row


def fill_span(y, x0, x1, color):
    if y < 0 or y >= H:
        return
    x0 = max(0, x0)
    x1 = min(W - 1, x1)
    if x0 > x1:
        return
    row = bytes(color) * (x1 - x0 + 1)
    off = (y * W + x0) * 3
    PIX[off:off + len(row)] = row


def fill_ellipse(cx, cy, rx, ry, color):
    if rx <= 0 or ry <= 0:
        return
    for dy in range(-ry, ry + 1):
        dx = isqrt(rx * rx * (ry * ry - dy * dy) // (ry * ry))
        fill_span(cy + dy, cx - dx, cx + dx, color)


def fill_circle(cx, cy, r, color):
    fill_ellipse(cx, cy, r, r, color)


def fill_rounded_rect(x0, y0, x1, y1, r, color):
    """Fill [x0,x1) x [y0,y1) with all four corners rounded by radius r."""
    for y in range(y0, y1):
        if y < y0 + r:
            dy = (y0 + r) - y
            inset = r - isqrt(r * r - dy * dy)
        elif y >= y1 - r:
            dy = y - y1 + r + 1
            inset = r - isqrt(r * r - dy * dy)
        else:
            inset = 0
        fill_rect(x0 + inset, y, (x1 - x0) - 2 * inset, 1, color)


def fill_rounded_bottom(x0, y0, x1, y1, r, color):
    """Fill rect with square top corners and rounded bottom corners."""
    for y in range(y0, y1):
        if y >= y1 - r:
            dy = y - y1 + r + 1
            inset = r - isqrt(r * r - dy * dy)
        else:
            inset = 0
        fill_rect(x0 + inset, y, (x1 - x0) - 2 * inset, 1, color)


def fill_polygon(points, color):
    """Scanline polygon fill (integer math)."""
    if len(points) < 3:
        return
    ys = [p[1] for p in points]
    for y in range(max(0, min(ys)), min(H - 1, max(ys)) + 1):
        xs = []
        n = len(points)
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                # intersection x at scanline y (integer division)
                x = x0 + (y - y0) * (x1 - x0) // (y1 - y0)
                xs.append(x)
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            fill_span(y, xs[i], xs[i + 1], color)


def draw_line(x0, y0, x1, y1, color, thick=1):
    """Bresenham line; thick draws a thick x thick block per step."""
    half = thick // 2
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        fill_rect(x - half, y - half, thick, thick, color)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def rect_outline(x, y, w, h, color, t=2):
    fill_rect(x, y, w, t, color)
    fill_rect(x, y + h - t, w, t, color)
    fill_rect(x, y, t, h, color)
    fill_rect(x + w - t, y, t, h, color)


# ------------------------------------------------------------------- font ---
# Classic 5x7 pixel font. '#' = on, '.' = off. Exactly A-Z, 0-9, space, '·'.
GLYPHS = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '·': ("00000", "00000", "00000", "01100", "01100", "00000", "00000"),
}


def text_width(text, scale):
    if not text:
        return 0
    return len(text) * 6 * scale - scale


def draw_text(text, x, top, scale, color):
    """Draw text left-aligned at (x, top). Each font pixel is scale x scale."""
    cx = x
    for ch in text:
        glyph = GLYPHS[ch]
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == '1':
                    fill_rect(cx + col * scale, top + row * scale,
                              scale, scale, color)
        cx += 6 * scale


def draw_text_center(text, cx, top, scale, color):
    draw_text(text, cx - text_width(text, scale) // 2, top, scale, color)


# ---------------------------------------------------------------- poster ----
def draw_poster():
    fill_rect(0, 0, W, H, CREAM)

    # Outer frame: 4 px terracotta outline, inset 14.
    fill_rect(14, 14, 996, 4, TERRA)
    fill_rect(14, 1006, 996, 4, TERRA)
    fill_rect(14, 14, 4, 996, TERRA)
    fill_rect(1006, 14, 4, 996, TERRA)

    # Masthead + rule.
    draw_text_center("NEWS ILLUSTRATION", 512, 44, 4, TERRA)
    fill_rect(64, 104, 896, 3, TERRA)

    # Headline + dateline.
    draw_text_center("THANKSGIVING", 512, 128, 9, INK)
    draw_text_center("EVE", 512, 205, 9, INK)
    draw_text_center("WEDNESDAY \u00b7 25 NOVEMBER 2026", 512, 292, 4, TERRA)

    # Hero panel: deep-olive rounded rectangle, x 64-960, y 340-690.
    fill_rounded_rect(64, 340, 960, 690, 18, OLIVE)

    # Three lit windows (cream rectangles near the top of the panel).
    fill_rect(150, 380, 90, 110, CREAM)
    fill_rect(455, 352, 100, 48, CREAM)
    fill_rect(760, 380, 90, 110, CREAM)

    # Autumn leaves in the panel corners (small ellipses + stem line).
    fill_ellipse(100, 362, 15, 7, TERRA)
    draw_line(100, 362, 88, 350, TERRA, 2)
    fill_ellipse(922, 362, 15, 7, CREAM)
    draw_line(922, 362, 934, 350, CREAM, 2)
    fill_ellipse(100, 592, 15, 7, CREAM)
    draw_line(100, 592, 88, 580, CREAM, 2)
    fill_ellipse(922, 592, 15, 7, TERRA)
    draw_line(922, 592, 934, 580, TERRA, 2)

    # Turkey: tail fan (5 tall ellipses, alternating terracotta / cream).
    # Centre feather is terracotta so it stays distinct from the cream
    # middle window directly above it.
    tail = [(400, 498, TERRA), (452, 462, CREAM), (512, 450, TERRA),
            (572, 462, CREAM), (624, 498, TERRA)]
    for (tx, ty, col) in tail:
        fill_ellipse(tx, ty, 32, 62, col)
    # Body: large cream ellipse, centre (512, 560).
    fill_ellipse(512, 560, 170, 95, CREAM)
    # Wing: deep-olive ellipse on the body.
    fill_ellipse(478, 572, 88, 42, OLIVE)
    # Head: cream circle at (660, 480); beak, wattle, eye.
    fill_circle(660, 480, 34, CREAM)
    fill_polygon([(688, 468), (688, 496), (716, 482)], TERRA)
    fill_ellipse(694, 504, 7, 12, TERRA)
    fill_circle(668, 470, 5, INK)

    # Long table: terracotta, x 64-960, y 610-690 (rounded bottom corners
    # to match the panel), with a 3 px cream line along its top edge.
    fill_rounded_bottom(64, 610, 960, 690, 18, TERRA)
    fill_rect(64, 610, 896, 3, CREAM)

    # Divider rule.
    fill_rect(64, 720, 896, 3, TERRA)

    # ---- Bottom story band, y 740-990 ----
    # Left: tanker icon + HORMUZ / TWO TANKERS / HIT MINES.
    fill_polygon([(76, 852), (140, 852), (132, 874), (84, 874)], INK)
    fill_rect(94, 830, 32, 24, INK)          # superstructure outline block
    fill_rect(96, 832, 28, 20, CREAM)        # superstructure
    fill_rect(122, 826, 14, 26, TERRA)       # funnel
    fill_circle(132, 812, 8, INK)            # spiked mine
    for (sx, sy) in [(132, 800), (132, 824), (120, 812), (144, 812),
                     (124, 804), (140, 804), (124, 820), (140, 820)]:
        draw_line(132, 812, sx, sy, INK, 2)
    draw_text("HORMUZ", 152, 790, 3, TERRA)
    draw_text("TWO TANKERS", 152, 822, 4, INK)
    draw_text("HIT MINES", 152, 858, 4, INK)

    # Right: warship icon + LIBYA / UKRAINE SINKS / RUSSIAN WARSHIP.
    fill_polygon([(536, 852), (596, 852), (588, 874), (544, 874)], INK)
    fill_rect(552, 836, 24, 16, TERRA)       # turret
    draw_line(576, 843, 596, 838, INK, 3)   # gun barrel
    draw_text("LIBYA", 604, 790, 3, TERRA)
    draw_text("UKRAINE SINKS", 604, 822, 4, INK)
    draw_text("RUSSIAN WARSHIP", 604, 858, 4, INK)


# -------------------------------------------------------------------- png ----
def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png():
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter type 0 on every scanline
        off = y * W * 3
        raw += PIX[off:off + W * 3]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    return png


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(out_dir, exist_ok=True)
    draw_poster()
    data = encode_png()
    with open(os.path.join(out_dir, "entry.png"), "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()

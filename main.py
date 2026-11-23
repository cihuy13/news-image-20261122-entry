#!/usr/bin/env python3
"""news-image-20261122 v1 — "Sunday 22 November 2026: the world on one page".

Single-file, stdlib-only program. Draws a newspaper front page (36 stories,
all dated Sunday 22 November 2026) as a 1024x1024 PNG and writes it to
$MAKEFUN_OUTPUT_DIR/entry.png (or /output/entry.png). No network, no local
writes, deterministic: the same bytes every run.

Text comes from glyphs.bin (a READ file beside this program): bitmaps
rasterized from DejaVu Serif / DejaVu Sans Bold at the exact sizes used here.
No sibling imports, no font files needed at run time.
"""
import os
import struct
import sys
import zlib

W, H = 1024, 1024

# --- palette ---
PAPER = (247, 242, 231)
PAPER2 = (238, 231, 214)
INK = (20, 20, 20)
RED = (179, 35, 27)
RED_DK = (140, 22, 16)
NAVY = (27, 42, 74)
NAVY2 = (38, 58, 102)
TEAL = (0, 96, 96)
GREEN = (46, 110, 58)
GOLD = (176, 124, 0)
GREY = (110, 105, 95)
GREY_LT = (200, 192, 176)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SKY_NIGHT = (16, 24, 48)
SKY_DAY = (168, 196, 214)
SEA = (52, 96, 128)
SAND = (214, 196, 150)


class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def frame(self, x, y, w, h, c, t=1):
        self.rect(x, y, w, t, c)
        self.rect(x, y + h - t, w, t, c)
        self.rect(x, y, t, h, c)
        self.rect(x + w - t, y, t, h, c)

    def hline(self, x, y, w, c, t=1):
        self.rect(x, y, w, t, c)

    def vline(self, x, y, h, c, t=1):
        self.rect(x, y, t, h, c)

    def line(self, x0, y0, x1, y1, c):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            dx = int((r * r - (yy - cy) ** 2) ** 0.5) if abs(yy - cy) <= r else 0
            self.rect(cx - dx, yy, 2 * dx + 1, 1, c)

    def ring(self, cx, cy, r, c, t=2):
        for k in range(t):
            rr = r - k
            for a in range(360):
                import math
                x = cx + int(rr * math.cos(math.radians(a)))
                y = cy + int(rr * math.sin(math.radians(a)))
                self.set(x, y, c)

    def poly(self, pts, c):
        # scanline fill of a simple polygon
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.rect(int(xs[k]), y, int(xs[k + 1]) - int(xs[k]) + 1, 1, c)

    def dot(self, cx, cy, r, c):
        self.circle(cx, cy, r, c)


def write_png(cv, path):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ, data):
        out = struct.pack(">I", len(data)) + typ + data
        out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


# --- glyphs ---
class Font:
    def __init__(self, glyphs, name, size):
        self.g = glyphs[(name, size)]
        self.size = size

    def width(self, text):
        return sum(self.g.get(ch, (0, 0, 0, 0, 0, b""))[0] for ch in text)

    def draw(self, cv, x, y_baseline, text, color):
        pen = x
        for ch in text:
            gl = self.g.get(ch)
            if gl is None:
                pen += self.size // 2
                continue
            adv, w, h, dx, dy, bits = gl
            if w and h:
                gx = pen + dx
                gy = y_baseline + dy
                for yy in range(h):
                    rowbase = yy * w
                    for xx in range(w):
                        bit = (bits[(rowbase + xx) // 8] >> (7 - ((rowbase + xx) % 8))) & 1
                        if bit:
                            cv.set(gx + xx, gy + yy, color)
            pen += adv
        return pen


def load_glyphs():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "glyphs.bin"), "rb") as f:
        data = f.read()
    assert data[:5] == b"GLYF1", "bad glyphs.bin"
    pos = 5
    (nfaces,) = struct.unpack_from("<I", data, pos)
    pos += 4
    glyphs = {}
    for _ in range(nfaces):
        nl = data[pos]
        pos += 1
        name = data[pos:pos + nl].decode()
        pos += nl
        size, nch = struct.unpack_from("<II", data, pos)
        pos += 8
        face = {}
        for _ in range(nch):
            cp, adv, w, h, dx, dy = struct.unpack_from("<IHHHhh", data, pos)
            pos += 14
            nbytes = (w * h + 7) // 8
            bits = data[pos:pos + nbytes]
            pos += nbytes
            face[chr(cp)] = (adv, w, h, dx, dy, bits)
        glyphs[(name, size)] = face
    return glyphs


def wrap(text, font, max_w, max_lines=None):
    words = text.split(" ")
    lines = []
    cur = ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if font.width(trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
            if max_lines and len(lines) >= max_lines:
                cur = ""
                break
    if cur:
        lines.append(cur)
    if max_lines:
        lines = lines[:max_lines]
    return lines


def draw_lines(cv, font, x, y_top, lines, color, leading=None):
    if leading is None:
        leading = font.size + 3
    y = y_top + font.size
    for ln in lines:
        font.draw(cv, x, y, ln, color)
        y += leading
    return y


def fit_text(text, font, max_w, max_lines):
    """Wrap, shrinking one size is not possible (fixed faces); truncate with
    ellipsis on the last line if it still overflows."""
    lines = wrap(text, font, max_w, max_lines)
    if not lines:
        return lines
    last = lines[-1]
    while font.width(last + "…") > max_w and len(last) > 1:
        last = last[:-1]
    if font.width(lines[-1]) > max_w:
        lines[-1] = last + "…"
    return lines

# --- flat-vector art: one readable subject per panel, 2-3 flat colours ---
SKY = (232, 214, 170)
FLAME = (224, 122, 26)
FLAME2 = (240, 178, 44)


def art_cop(cv, x, y, w, h):
    # COP31: conference hall at dusk, gavel over a torn pact page
    cv.rect(x, y, w, h, (44, 62, 96))
    cv.rect(x, y + h - 26, w, 26, (30, 42, 66))
    cv.rect(x + 18, y + 22, w - 36, h - 58, (247, 242, 231))
    cv.rect(x + 30, y + 34, w - 60, 4, RED)
    for i in range(4):
        cv.rect(x + 30, y + 48 + i * 9, w - 60 - i * 22, 3, (150, 142, 124))
    cv.line(x + 30, y + 48, x + w - 30, y + 84, RED)
    cv.line(x + 30, y + 84, x + w - 30, y + 48, RED)
    cv.rect(x + w // 2 - 34, y + h - 46, 68, 10, (122, 84, 42))
    cv.rect(x + w // 2 - 6, y + h - 66, 12, 22, (90, 60, 28))
    cv.circle(x + w // 2 + 52, y + 26, 12, (240, 178, 44))


def art_drones(cv, x, y, w, h):
    # Ukraine night: drone silhouettes over a broken apartment block
    cv.rect(x, y, w, h, SKY_NIGHT)
    for sx, sy in ((22, 18), (70, 34), (120, 14), (180, 30), (240, 16), (290, 36)):
        cv.circle(x + sx % w, y + sy, 2, WHITE)
    cv.rect(x + 20, y + h - 78, 74, 78, (52, 52, 66))
    cv.rect(x + 110, y + h - 58, 60, 58, (44, 44, 56))
    for r in range(4):
        for c in range(3):
            cv.rect(x + 28 + c * 22, y + h - 70 + r * 18, 10, 10, (240, 178, 44))
    cv.poly([(x + 94, y + h - 78), (x + 110, y + h - 58), (x + 94, y + h - 30),
             (x + 78, y + h - 52)], (30, 30, 40))
    # drones: small crosses with a red glow dot
    for dx, dy in ((150, 26), (210, 44), (258, 22), (120, 58)):
        cv.rect(x + dx - 8, y + dy, 16, 2, (200, 200, 210))
        cv.rect(x + dx - 1, y + dy - 6, 2, 12, (200, 200, 210))
        cv.circle(x + dx, y + dy, 3, RED)
    cv.poly([(x + 200, y + h), (x + 260, y + h - 70), (x + 300, y + h)],
            (240, 178, 44))
    cv.poly([(x + 220, y + h), (x + 262, y + h - 44), (x + 292, y + h)],
            (250, 226, 120))


def art_bahrain(cv, x, y, w, h):
    # Bahrain night: two radar dishes, fire glow at the base
    cv.rect(x, y, w, h, SKY_NIGHT)
    cv.circle(x + w - 44, y + 24, 11, (232, 226, 210))
    cv.rect(x, y + h - 34, w, 34, (38, 38, 48))
    for cx in (x + 70, x + 210):
        cv.rect(cx - 4, y + 78, 8, h - 78 - 34, (120, 124, 138))
        cv.circle(cx, y + 66, 26, (150, 156, 170))
        cv.circle(cx, y + 66, 18, SKY_NIGHT)
        cv.line(cx - 22, y + 66, cx + 22, y + 66, (150, 156, 170))
    cv.poly([(x + 30, y + h - 34), (x + 90, y + h - 84), (x + 130, y + h - 34)],
            FLAME)
    cv.poly([(x + 60, y + h - 34), (x + 96, y + h - 66), (x + 118, y + h - 34)],
            FLAME2)
    cv.rect(x + 150, y + h - 60, 110, 26, (60, 60, 72))
    for i in range(4):
        cv.rect(x + 160 + i * 26, y + h - 54, 14, 8, (240, 178, 44))


def art_house(cv, x, y, w, h):
    # US Capitol dome with a seats arc
    cv.rect(x, y, w, h, SKY_DAY)
    cv.rect(x, y + h - 22, w, 22, (120, 140, 120))
    cv.rect(x + w // 2 - 52, y + 26, 104, h - 48, WHITE)
    cv.circle(x + w // 2, y + 30, 26, WHITE)
    cv.rect(x + w // 2 - 2, y + 2, 4, 10, (90, 90, 90))
    for i in range(5):
        cv.rect(x + w // 2 - 44 + i * 18, y + 52, 8, h - 74, (200, 204, 208))
    for i in range(9):
        col = RED if i < 5 else NAVY2
        cv.circle(x + 18 + i * 15, y + h - 8, 5, col)


def art_ship(cv, x, y, w, h):
    # Warship listing in the harbour, smoke column
    cv.rect(x, y, w, h, (196, 214, 224))
    cv.rect(x, y + h - 26, w, 26, SEA)
    cv.poly([(x + 26, y + h - 26), (x + 60, y + h - 52), (x + 116, y + h - 52),
             (x + 128, y + h - 26)], (96, 104, 112))
    cv.rect(x + 66, y + h - 74, 8, 24, (70, 76, 84))
    cv.rect(x + 88, y + h - 66, 22, 14, (70, 76, 84))
    cv.circle(x + 118, y + h - 58, 10, (60, 60, 66))
    cv.circle(x + 118, y + h - 58, 5, (40, 40, 48))
    cv.circle(x + 40, y + 22, 12, (120, 124, 128))
    cv.circle(x + 52, y + 14, 9, (140, 144, 148))
    cv.poly([(x + 20, y + h - 26), (x + 46, y + h - 60), (x + 62, y + h - 26)],
            FLAME)


def art_vote(cv, x, y, w, h):
    # Ballot box with a red check
    cv.rect(x, y, w, h, (222, 230, 236))
    cv.rect(x + w // 2 - 42, y + 26, 84, 56, (250, 250, 248))
    cv.frame(x + w // 2 - 42, y + 26, 84, 56, INK, 2)
    cv.rect(x + w // 2 - 18, y + 20, 36, 8, INK)
    cv.line(x + w // 2 - 26, y + 56, x + w // 2 - 8, y + 74, RED)
    cv.line(x + w // 2 - 8, y + 74, x + w // 2 + 28, y + 38, RED)
    cv.rect(x, y + h - 14, w, 14, TEAL)


def art_race(cv, x, y, w, h):
    # Night street circuit: chequered flag, racing car silhouette
    cv.rect(x, y, w, h, (24, 24, 34))
    for r in range(3):
        for c in range(4):
            if (r + c) % 2 == 0:
                cv.rect(x + 12 + c * 12, y + 10 + r * 12, 12, 12, WHITE)
    cv.rect(x, y + h - 30, w, 30, (52, 52, 62))
    cv.rect(x + 30, y + h - 44, 92, 16, RED)
    cv.rect(x + 52, y + h - 56, 40, 12, RED)
    cv.circle(x + 48, y + h - 26, 9, BLACK)
    cv.circle(x + 48, y + h - 26, 4, (180, 180, 190))
    cv.circle(x + 104, y + h - 26, 9, BLACK)
    cv.circle(x + 104, y + h - 26, 4, (180, 180, 190))
    cv.circle(x + w - 26, y + 22, 12, (240, 178, 44))


def art_cricket(cv, x, y, w, h):
    # Cricket: green outfield, stumps, red ball, bat
    cv.rect(x, y, w, h, (126, 178, 110))
    cv.rect(x, y + h - 34, w, 34, (96, 148, 84))
    cv.rect(x + w // 2 - 26, y + h - 34, 52, 34, SAND)
    for dx in (-8, 0, 8):
        cv.rect(x + w // 2 + dx - 2, y + 22, 4, 26, (250, 244, 214))
    cv.circle(x + w - 30, y + 24, 10, RED)
    cv.line(x + 26, y + h - 20, x + 52, y + 30, (122, 84, 42))
    cv.rect(x + 46, y + 22, 12, 22, (122, 84, 42))


def art_nba(cv, x, y, w, h):
    # Basketball: hoop, backboard, ball going through
    cv.rect(x, y, w, h, (238, 226, 200))
    cv.rect(x + w - 46, y + 12, 30, 40, WHITE)
    cv.frame(x + w - 46, y + 12, 30, 40, INK, 2)
    cv.rect(x + w - 40, y + 52, 18, 4, RED)
    cv.circle(x + w - 31, y + 62, 7, (196, 120, 44))
    cv.circle(x + 34, y + 26, 16, (224, 128, 48))
    cv.line(x + 20, y + 26, x + 48, y + 26, INK)
    cv.line(x + 34, y + 12, x + 34, y + 40, INK)
    cv.rect(x, y + h - 12, w, 12, (120, 78, 40))


def art_cargo(cv, x, y, w, h):
    # Cargo ship ablaze at dusk
    cv.rect(x, y, w, h, (232, 178, 120))
    cv.circle(x + w - 30, y + 22, 16, (250, 226, 150))
    cv.rect(x, y + h - 24, w, 24, SEA)
    cv.rect(x + 14, y + h - 52, w - 28, 28, (44, 62, 96))
    for i in range(3):
        cv.rect(x + 26 + i * 40, y + h - 48, 26, 18, (150, 156, 170))
    cv.poly([(x + 40, y + h - 52), (x + 62, y + h - 84), (x + 84, y + h - 52)],
            FLAME)
    cv.poly([(x + 96, y + h - 52), (x + 112, y + h - 76), (x + 128, y + h - 52)],
            FLAME2)
    cv.circle(x + 30, y + 26, 10, (90, 90, 96))
    cv.circle(x + 44, y + 18, 8, (110, 110, 116))


def art_power(cv, x, y, w, h):
    # Pylon with a lightning bolt, dark sky
    cv.rect(x, y, w, h, (52, 62, 84))
    cv.line(x + w // 2 - 34, y + h - 12, x + w // 2, y + 18, (200, 204, 210))
    cv.line(x + w // 2 + 34, y + h - 12, x + w // 2, y + 18, (200, 204, 210))
    cv.line(x + w // 2 - 20, y + 34, x + w // 2 + 20, y + 34, (200, 204, 210))
    cv.line(x + w // 2 - 12, y + 56, x + w // 2 + 12, y + 56, (200, 204, 210))
    cv.poly([(x + w // 2 + 22, y + 12), (x + w // 2 - 2, y + 44),
             (x + w // 2 + 10, y + 44), (x + w // 2 - 14, y + 76),
             (x + w // 2 + 22, y + 36), (x + w // 2 + 8, y + 36)],
            (240, 200, 44))
    cv.rect(x, y + h - 12, w, 12, (30, 34, 48))


def art_fire(cv, x, y, w, h):
    # Factory with flames
    cv.rect(x, y, w, h, (214, 190, 160))
    cv.rect(x + 16, y + h - 52, w - 32, 52, (120, 110, 100))
    cv.rect(x + w - 34, y + 12, 12, h - 52, (96, 88, 80))
    for i in range(3):
        cv.rect(x + 26 + i * 34, y + h - 40, 18, 14, (240, 200, 90))
    cv.poly([(x + 30, y + h - 52), (x + 56, y + h - 88), (x + 82, y + h - 52)],
            FLAME)
    cv.poly([(x + 84, y + h - 52), (x + 104, y + h - 80), (x + 124, y + h - 52)],
            FLAME2)
    cv.circle(x + 26, y + 18, 9, (96, 96, 100))


def art_boat(cv, x, y, w, h):
    # Capsized boat, waves
    cv.rect(x, y, w, h, SKY_DAY)
    cv.rect(x, y + h - 34, w, 34, SEA)
    for i in range(4):
        cv.rect(x + 10 + i * 38, y + h - 30 + (i % 2) * 8, 26, 4, (220, 232, 240))
    cv.poly([(x + 30, y + h - 34), (x + 110, y + h - 34), (x + 96, y + h - 52),
             (x + 44, y + h - 52)], (122, 84, 42))
    cv.rect(x + 52, y + h - 58, 44, 8, (96, 66, 34))
    cv.circle(x + 118, y + 22, 10, (250, 226, 150))


def art_gaza(cv, x, y, w, h):
    # White aid van on a dusty road
    cv.rect(x, y, w, h, (224, 206, 176))
    cv.rect(x, y + h - 20, w, 20, (190, 170, 140))
    cv.rect(x + 22, y + h - 56, 96, 36, WHITE)
    cv.frame(x + 22, y + h - 56, 96, 36, INK, 2)
    cv.rect(x + 96, y + h - 48, 24, 28, (210, 214, 218))
    cv.circle(x + 44, y + h - 20, 9, BLACK)
    cv.circle(x + 44, y + h - 20, 4, (180, 180, 190))
    cv.circle(x + 100, y + h - 20, 9, BLACK)
    cv.circle(x + 100, y + h - 20, 4, (180, 180, 190))
    cv.circle(x + w - 28, y + 20, 11, (250, 226, 150))


def art_tennis(cv, x, y, w, h):
    # Tennis court from above: blue court, net, yellow ball
    cv.rect(x, y, w, h, (52, 110, 76))
    cv.rect(x + 18, y + 12, w - 36, h - 24, (52, 84, 150))
    cv.frame(x + 18, y + 12, w - 36, h - 24, WHITE, 2)
    cv.line(x + 18, y + h // 2, x + w - 18, y + h // 2, WHITE)
    cv.rect(x + w // 2 - 2, y + 12, 4, h - 24, WHITE)
    cv.circle(x + 34, y + 24, 9, (220, 230, 60))
    cv.line(x + 30, y + 24, x + 38, y + 24, INK)
    cv.rect(x + w - 44, y + h - 30, 26, 12, (220, 230, 60))


ARTS = {
    "cop": art_cop, "drones": art_drones, "bahrain": art_bahrain,
    "house": art_house, "ship": art_ship, "vote": art_vote,
    "race": art_race, "cricket": art_cricket, "nba": art_nba,
    "cargo": art_cargo, "power": art_power, "fire": art_fire,
    "boat": art_boat, "gaza": art_gaza, "tennis": art_tennis,
}

# --- content (own wording throughout; facts verified 22-23 Nov 2026) ---
HEROES = [
    dict(num=1, place="ANTALYA, TURKIYE", tag="CLIMATE", cert="CONFIRMED",
         art="cop", head="Climate talks collapse with no pact",
         body="The final text drops fossil fuels and the $120bn target, "
              "and admits 1.5C will be overshot.",
         src="Reuters, BBC, The Guardian"),
    dict(num=2, place="KYIV REGION, UKRAINE", tag="WAR", cert="REPORTED",
         art="drones", head="186 drones in one night over Ukraine",
         body="Air defences down or jam 161 of 186; hits at 18 sites. A block in "
              "Dymer falls: 4 killed, 14 missing.",
         src="Ukrainian Air Force, Reuters"),
    dict(num=3, place="MANAMA, BAHRAIN", tag="CLAIM", cert="CLAIM",
         art="bahrain", head="Two accounts of one night in Bahrain",
         body="IRGC says it hit two US Patriot radars in Bahrain. Bahrain says a "
              "civilian plant burned; two hurt.",
         src="IRGC statement, Bahrain Interior Ministry"),
]

MEDIUMS = [
    dict(num=4, place="WASHINGTON", tag="POLITICS", cert="CONFIRMED",
         art="house", head="Democrats take a 258th House seat",
         body="Foxx concedes in North Carolina; most since 1992.",
         src="AP, Guardian"),
    dict(num=5, place="BENGHAZI", tag="WAR", cert="CONFIRMED",
         art="ship", head="Russian warship sunk in Libyan port",
         body="Drones hit the Merkury at refuel; no side claims it.",
         src="AP, Al Jazeera"),
    dict(num=6, place="HONG KONG", tag="ELECTION", cert="CONFIRMED",
         art="vote", head="Hong Kong poll ends at 98.79%",
         body="5,640 of 5,709 vote; 856 candidates chase 723 seats.",
         src="SCMP"),
    dict(num=7, place="LAS VEGAS", tag="FORMULA 1", cert="CONFIRMED",
         art="race", head="Verstappen wins in Las Vegas",
         body="Beats Norris by 0.64s; his 75th Grand Prix win.",
         src="F1, AP"),
    dict(num=8, place="WELLINGTON", tag="CRICKET", cert="CONFIRMED",
         art="cricket", head="India declare on a record 720/9",
         body="Highest Test total in New Zealand; the lead is 352.",
         src="Reuters"),
    dict(num=9, place="SAN ANTONIO", tag="NBA", cert="CONFIRMED",
         art="nba", head="Wembanyama scores 50",
         body="50 points, 19 rebounds, 5 blocks; Spurs win 114-91.",
         src="AP"),
    dict(num=10, place="FINLAND", tag="SEA", cert="CONFIRMED",
         art="cargo", head="Burning cargo ship still adrift",
         body="Hit Saturday, still burning; 16 crew safe.",
         src="Reuters"),
    dict(num=11, place="TEHRAN", tag="ENERGY", cert="REPORTED",
         art="power", head="Iran starts rolling power cuts",
         body="Up to two hours a day as war damage bites the grid.",
         src="RFE/RL"),
    dict(num=12, place="CIKANDE", tag="FIRE", cert="CONFIRMED",
         art="fire", head="Candy-factory fire kills three",
         body="36 missing after the blaze tears through the plant.",
         src="Reuters"),
    dict(num=13, place="BAYELSA", tag="DISASTER", cert="CONFIRMED",
         art="boat", head="Mourners' boat capsizes, 24 dead",
         body="24 others rescued; the search goes on.",
         src="AP"),
    dict(num=14, place="GAZA", tag="CONFLICT", cert="REPORTED",
         art="gaza", head="Three killed in Gaza food-van strike",
         body="Witnesses say the van carried aid; army reviewing.",
         src="Al Jazeera"),
    dict(num=15, place="TURIN", tag="TENNIS", cert="CONFIRMED",
         art="tennis", head="Alcaraz wins his first ATP Finals",
         body="Beats Zverev 6-2, 7-6 to take the title.",
         src="ATP, Guardian"),
]

ALSO = [
    "Estonia to shut its Russia border on 1 Dec — Reuters",
    "EU and Indonesia sign a landmark trade deal — Reuters",
    "Marles rejects a US report on AUKUS subs — ABC",
    "Nepal PM Balendra Shah lands in Delhi — Reuters",
    "Drones strike homes near Khartoum — AFP",
    "Peru quake toll: 1 dead, 16 hurt — Reuters",
    "FBI probes a hack of its crime database — AP",
    "Belgian controllers join Monday's strike — Reuters",
    "Toxic liquor kills 19 in Manipur — Reuters",
    "Pope hosts 1,300 poor guests for lunch — Vatican News",
    "Seoul minister quits over AI exam cheating — Reuters",
    "Fighting traps Ebola medics in DR Congo — Al Jazeera",
    "Bolsonaro in intensive care in Brasilia — Reuters",
    "Marquez wins an eighth MotoGP title — Guardian",
    "Netanyahu-Eisenkot talks end with no deal — Al Jazeera",
    "England beat New Zealand 37-12 — Reuters",
    "Arsenal 2-2 Newcastle — BBC",
    "49ers beat the Vikings 35-10 — ESPN",
    "Russian helicopter enters Finnish airspace — MoD",
    "Iran talks to Qatari mediators in Doha — Al Jazeera",
    "Vyshneve: drone hits a supermarket — Ukrinform",
]

NUMBERS = [
    ("186", "DRONES FIRED AT UKRAINE"),
    ("161", "DOWNED OR JAMMED"),
    ("35%", "POWER GOAL FOR 2035"),
    ("$120bn", "ADAPTATION TARGET DROPPED"),
    ("720/9", "INDIA'S RECORD TOTAL"),
    ("98.79%", "HONG KONG TURNOUT"),
]

REGIONS = [
    ("EUROPE 10", NAVY), ("MIDDLE EAST 5", RED), ("AMERICAS 7", TEAL),
    ("ASIA-PACIFIC 5", GOLD), ("AFRICA 4", GREEN),
    ("OCEANIA 2", (90, 60, 120)), ("WORLD 3", (90, 88, 84)),
]

CERT_COLOR = {"CONFIRMED": GREEN, "REPORTED": GOLD, "CLAIM": RED}

# map: continents as flat polygons in a 300x104 box, pins (x, y) per story
MAP_POLYS = [
    [(8, 18), (30, 8), (58, 10), (66, 22), (52, 30), (58, 44), (44, 52),
     (30, 46), (14, 34)],  # North America
    [(52, 58), (66, 56), (76, 66), (68, 88), (56, 84), (48, 68)],
    # South America
    [(150, 14), (168, 10), (182, 16), (176, 28), (160, 30), (148, 22)],
    # Europe
    [(150, 40), (176, 38), (192, 50), (184, 72), (166, 82), (152, 66),
     (146, 50)],  # Africa
    [(186, 12), (230, 8), (258, 16), (262, 34), (240, 44), (224, 36),
     (206, 40), (192, 28)],  # Asia
    [(248, 76), (272, 72), (282, 82), (264, 90), (246, 86)],  # Australia
]
PINS = {1: (178, 34), 2: (168, 20), 3: (208, 56), 4: (62, 34), 5: (158, 48),
        6: (256, 58), 7: (38, 36), 8: (296, 92), 9: (48, 44), 10: (166, 10),
        11: (216, 38), 12: (248, 72), 13: (148, 62), 14: (182, 56),
        15: (148, 22)}


def centered(cv, font, y_baseline, text, color, cx=W // 2):
    w = font.width(text)
    font.draw(cv, cx - w // 2, y_baseline, text, color)


def tag_box(cv, font, x_right, y, text, color):
    w = font.width(text) + 10
    cv.rect(x_right - w, y, w, 13, color)
    font.draw(cv, x_right - w + 5, y + 10, text, WHITE)
    return w


def build():
    gl = load_glyphs()
    F = {}
    for name, size in [("SB", 64), ("SB", 30), ("SB", 19), ("SB", 15),
                       ("SB", 13), ("SB", 11), ("SR", 13), ("SR", 11),
                       ("SR", 10), ("SR", 9), ("NB", 12), ("NB", 11),
                       ("NB", 9), ("NB", 8)]:
        F[(name, size)] = Font(gl, name, size)
    cv = Canvas(W, H, PAPER)
    MX = 24
    CW = W - 2 * MX

    # top strip
    cv.rect(0, 0, W, 26, NAVY)
    centered(cv, F[("NB", 9)], 18,
             "THE WORLD IN ONE DAY  ·  36 STORIES  ·  7 REGIONS  ·  "
             "EVERY ONE DATED SUNDAY 22 NOVEMBER 2026", WHITE)
    # masthead
    centered(cv, F[("SB", 64)], 88, "Sunday 22 November 2026", INK)
    # ticker
    centered(cv, F[("SR", 13)], 112,
             "Climate talks collapse with no pact  ·  186 drones in one night "
             "over Ukraine  ·  Two accounts of one night in Bahrain", RED)
    cv.hline(MX, 120, CW, INK, 2)
    # big-number strip
    cell = CW // 6
    for i, (num, lab) in enumerate(NUMBERS):
        x = MX + i * cell
        centered(cv, F[("SB", 30)], 152, num, RED if i % 2 == 0 else NAVY,
                 cx=x + cell // 2)
        centered(cv, F[("SR", 9)], 166, lab, GREY, cx=x + cell // 2)
        if i:
            cv.vline(x, 126, 42, GREY_LT, 1)
    cv.hline(MX, 170, CW, INK, 1)
    # region bar
    rw = CW // 7
    for i, (lab, col) in enumerate(REGIONS):
        x = MX + i * rw
        w = rw if i < 6 else CW - 6 * rw
        cv.rect(x, 174, w, 18, col)
        centered(cv, F[("NB", 9)], 187, lab, WHITE, cx=x + w // 2)
    # UTC strip
    y = 206
    F[("NB", 8)].draw(cv, MX, y, "THE DAY IN UTC", RED)
    F[("SR", 9)].draw(cv, MX + 92, y,
                      "03:00 COP31 objections close  ·  06:00 COP31 approval due  ·  "
                      "08:00 161 of 186 drones downed  ·  18:13 Democrats reach "
                      "258 seats  ·  20:43 Alcaraz wins ATP Finals", INK)
    cv.hline(MX, 210, CW, INK, 1)

    # heroes
    hy, hh, hw, gap = 216, 252, 320, 8
    for i, st in enumerate(HEROES):
        x = MX + i * (hw + gap)
        cv.rect(x, hy, hw, hh, WHITE)
        cv.frame(x, hy, hw, hh, INK, 1)
        ARTS[st["art"]](cv, x + 1, hy + 1, hw - 2, 140)
        my = hy + 148
        F[("NB", 9)].draw(cv, x + 8, my + 9,
                          "%d · %s · %s" % (st["num"], st["place"], st["tag"]),
                          RED)
        tag_box(cv, F[("NB", 8)], x + hw - 8, my - 1, st["cert"],
                CERT_COLOR[st["cert"]])
        lines = fit_text(st["head"], F[("SB", 19)], hw - 16, 2)
        draw_lines(cv, F[("SB", 19)], x + 8, my + 18, lines, INK, 22)
        blines = wrap(st["body"], F[("SR", 11)], hw - 16, 2)
        draw_lines(cv, F[("SR", 11)], x + 8, my + 18 + 2 * 22 + 4, blines,
                   INK, 14)
        F[("SR", 9)].draw(cv, x + 8, hy + hh - 4, "Sources: " + st["src"], GREY)

    # mediums: 2 rows x 6
    mw = (CW - 5 * 8) // 6
    mh = 140
    for row in range(2):
        for col in range(6):
            st = MEDIUMS[row * 6 + col]
            x = MX + col * (mw + 8)
            y = 476 + row * (mh + 8)
            cv.rect(x, y, mw, mh, WHITE)
            cv.frame(x, y, mw, mh, INK, 1)
            ARTS[st["art"]](cv, x + 1, y + 1, mw - 2, 52)
            cv.rect(x + 1, y + 53, mw - 2, 14, RED)
            F[("NB", 8)].draw(cv, x + 6, y + 63,
                              "%d · %s" % (st["num"], st["place"]), WHITE)
            tag_box(cv, F[("NB", 8)], x + mw - 4, y + 3, st["cert"],
                    CERT_COLOR[st["cert"]])
            lines = fit_text(st["head"], F[("SB", 13)], mw - 12, 2)
            draw_lines(cv, F[("SB", 13)], x + 6, y + 70, lines, INK, 14)
            blines = wrap(st["body"], F[("SR", 10)], mw - 12, 2)
            draw_lines(cv, F[("SR", 10)], x + 6, y + 70 + 2 * 14 + 2, blines,
                       INK, 11)
            F[("SR", 9)].draw(cv, x + 6, y + mh - 4, st["src"], GREY)

    # ALSO + map band
    by = 770
    cv.hline(MX, by - 4, CW, INK, 1)
    F[("NB", 11)].draw(cv, MX, by + 10, "ALSO ON SUNDAY 22 NOVEMBER — 21 MORE STORIES",
                       RED)
    colw = 310
    for i, item in enumerate(ALSO):
        col = i // 11
        r = i % 11
        x = MX + col * colw
        y = by + 16 + r * 11 + 10
        num = str(16 + i)
        F[("NB", 9)].draw(cv, x, y, num, RED)
        F[("SR", 9)].draw(cv, x + F[("NB", 9)].width(num) + 4, y, item, INK)
    # map panel
    mx, mw2 = 652, 348
    cv.rect(mx, by - 4, mw2, 142, (226, 234, 240))
    cv.frame(mx, by - 4, mw2, 142, INK, 1)
    F[("NB", 9)].draw(cv, mx + 8, by + 8,
                      "WHERE IT HAPPENED — PINS MATCH STORY NUMBERS", NAVY)
    ox, oy = mx + 22, by + 18
    for poly in MAP_POLYS:
        cv.poly([(ox + px, oy + py) for px, py in poly], SAND)
    for num, (px, py) in sorted(PINS.items()):
        cx, cy = ox + px, oy + py
        cv.circle(cx, cy, 7, RED)
        s = str(num)
        F[("NB", 8)].draw(cv, cx - F[("NB", 8)].width(s) // 2, cy + 3, s, WHITE)

    # DATE CHECK
    dy = 918
    cv.frame(MX, dy, CW, 50, RED, 2)
    F[("NB", 11)].draw(cv, MX + 8, dy + 13, "DATE CHECK", RED)
    F[("SR", 10)].draw(cv, MX + 92, dy + 13,
                       "Left out because they happened on other days: 'El Chapo Isidro' "
                       "captured — Sat 21 Nov · Myanmar genocide ruling — Thu 19 Nov ·",
                       INK)
    F[("SR", 10)].draw(cv, MX + 92, dy + 25,
                       "Nvidia SEC probe — Fri 20 Nov · Kryvyi Rih missile strike — Sat 21 Nov · "
                       "Russia's 400-drone night — Fri 19-20 Nov · BepiColombo burn — Sat 21 Nov.",
                       INK)
    F[("SR", 10)].draw(cv, MX + 92, dy + 37,
                       "Bahrain strikes were late Saturday night, first reported early Sunday; "
                       "Sparta II was hit Saturday and still burning Sunday.", INK)
    # footer
    centered(cv, F[("SR", 9)], 978,
             "Sources: Reuters, BBC, The Guardian, AP, AFP, Al Jazeera, SCMP, F1, ATP, "
             "ABC, Vatican News, RFE/RL. Scenes are drawn illustrations, not photographs.",
             GREY)
    centered(cv, F[("SR", 9)], 990,
             "REPORTED = carried by the day's wires  ·  CLAIM = one side's account, "
             "labelled as such  ·  CONFIRMED = 2+ outlets", GREY)
    cv.rect(0, 1000, W, 24, NAVY)
    centered(cv, F[("NB", 9)], 1016,
             "THE WORLD IN ONE DAY  ·  SUNDAY 22 NOVEMBER 2026  ·  ONE PAGE", WHITE)
    return cv


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    cv = build()
    write_png(cv, os.path.join(outdir, "entry.png"))


if __name__ == "__main__":
    main()

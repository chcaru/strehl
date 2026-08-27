"""Contact sheet of every shipped master, for defect triage by eye.

Tonight established that the corpus-wide halo statistic certifies nothing and that the
output on three sampled subjects is good. Three is not twenty-six. This builds one image
carrying all of them so a defect that only affects a few subjects cannot hide behind a
favourable sample -- the same reason a per-subject metric needs a corpus view.

Reads the gallery's already-downsampled 8-bit JPEGs, NOT the 16-bit masters. PIL is safe
here and only here: the hazard is Pillow silently right-shifting 16-bit TIFF data to 8-bit
(23224 >> 8 = 90), which cannot apply to a file that is 8-bit on disk. Any tool touching
the masters themselves must use tifffile.
"""
import pathlib
import struct
import sys
import zlib

import numpy as np
from PIL import Image

SRC = pathlib.Path(r"C:\dev\strehl-out\VIEW-SHIP\assets")
OUT = pathlib.Path(r"C:\dev\strehl-out\ORCH-CONTACT")
COLS = 5
CELL_W = 380
LABEL_H = 14


def png_rgb(a8, path):
    h, w, _ = a8.shape
    raw = b"".join(b"\x00" + a8[i].tobytes() for i in range(h))

    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c))

    pathlib.Path(path).write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b""))


# 5x7 bitmap font, enough to label a contact sheet without a font dependency.
GLYPH = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
    "3": ["11111", "00010", "00100", "00010", "00001", "10001", "01110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
}


def draw_text(canvas, s, y, x):
    for ch in s.upper():
        g = GLYPH.get(ch)
        if g is None:
            g = GLYPH[" "]
        for r, row in enumerate(g):
            for c, bit in enumerate(row):
                if bit == "1" and y + r < canvas.shape[0] and x + c < canvas.shape[1]:
                    canvas[y + r, x + c] = 255
        x += 6
        if x >= canvas.shape[1] - 6:
            return


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    suffix = sys.argv[1] if len(sys.argv) > 1 else "--full.jpg"
    tag = "1to1" if "1to1" in suffix else "full"
    files = sorted(p for p in SRC.iterdir() if p.name.endswith(suffix))
    print(f"{len(files)} gallery renders matching '{suffix}' in {SRC}")
    if not files:
        return 1

    tiles, names = [], []
    for p in files:
        im = Image.open(p)
        if im.mode != "RGB":
            im = im.convert("RGB")
        w, h = im.size
        ch = max(1, round(CELL_W * h / w))
        tiles.append(np.asarray(im.resize((CELL_W, ch), Image.LANCZOS), dtype=np.uint8))
        names.append(p.name.replace("--SHIP-V2" + suffix, ""))
        print(f"  {names[-1]:44s} {w}x{h} -> {CELL_W}x{ch}")

    cell_h = max(t.shape[0] for t in tiles) + LABEL_H
    rows = (len(tiles) + COLS - 1) // COLS
    sheet = np.zeros((rows * cell_h, COLS * CELL_W, 3), dtype=np.uint8)
    for i, (t, nm) in enumerate(zip(tiles, names)):
        r, c = divmod(i, COLS)
        y0, x0 = r * cell_h, c * CELL_W
        sheet[y0:y0 + t.shape[0], x0:x0 + CELL_W] = t
        lab = sheet[y0 + t.shape[0]:y0 + t.shape[0] + LABEL_H, x0:x0 + CELL_W]
        draw_text(lab, f"{i:02d} {nm}"[:60], 3, 2)

    out = OUT / f"contact-sheet-{tag}.png"
    png_rgb(sheet, out)
    print(f"\n{rows} rows x {COLS} cols, {sheet.shape[1]}x{sheet.shape[0]}")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Look at the four nominated footprints in the PHOTOGRAPHS, not in the flats.

Script 09 tested the four flats-nominated motes against a 200-draw location null
on six real subjects and found exactly one of them: 29 quads at quad
(3209,116), -2.3895%, negative in 6 of 6 subjects, p = 0.0299.  The other three
read +0.3938%, +0.4127% and +0.5356% at p = 0.85, 0.85, 0.83 -- not there.
Scripts 10-12 then established that a blind search for ADDITIONAL dust cannot be
commissioned on this corpus at all: every setting sensitive enough to recover a
2.5% planted disc has a roll null returning 22 to 434 false components, and
every setting with a clean null is blind to the plant.

A number nobody looked at is a number nobody checked, so this renders all four
footprints from the pooled twelve-subject photograph residual at one common
scale, and prints an ASCII cross-section of each into the log -- because the
PNGs are gitignored and the log is the committed record.

The control tile is a location with no nominated mote, rendered at the identical
scale.  If the confirmed mote does not look different from the control, the
p-value is measuring something other than what I think it is.
"""

import json
import pathlib
import struct
import time
import zlib

import numpy as np
from scipy import ndimage

HERE = pathlib.Path(__file__).resolve().parents[1]
OUT = HERE / "out"
DATA = HERE / "data"
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:6.1f}s]", *a, flush=True)


HALF = 70
FULL_SCALE = 0.04
CONTROL_AT = (1000, 1600)  # (cy, cx), interior, no nominated mote


def write_png(path, img):
    h, w = img.shape
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(h))

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )


RAMP = " .:-=+*#%@"


def ascii_tile(tile, step):
    """Darkest = deepest dip.  -4% -> '@', 0 -> ' '."""
    out = []
    for y in range(0, tile.shape[0], step):
        row = ""
        for x in range(0, tile.shape[1], step):
            v = tile[y : y + step, x : x + step].mean()
            i = int(np.clip(-v / FULL_SCALE, 0, 1) * (len(RAMP) - 1))
            row += RAMP[i]
        out.append(row)
    return out


def main():
    S = np.load(OUT / "12-subject-stack.npy")
    D = np.median(S, axis=0)
    h, w = D.shape
    log(f"pooled photograph residual, k={S.shape[0]}, {h}x{w}, rms {np.std(D) * 100:.4f}%")

    txt = (OUT / "defect-map-ILCE-7CM2.txt").read_text(encoding="utf-8")
    m = np.zeros((h, w), bool)
    gains = {}
    for line in txt.splitlines():
        if line.startswith("d "):
            _, px, py, g = line.split()
            m[int(py), int(px)] = True
            gains[(int(px), int(py))] = float(g)
    lab, n = ndimage.label(m, structure=np.ones((3, 3)))
    comps = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        comps.append((int(ys.size), int(round(xs.mean())), int(round(ys.mean())), lab == i))
    comps.sort(key=lambda c: -c[0])

    rows = []
    for area, cx, cy, sel in comps:
        y0, x0 = max(0, cy - HALF), max(0, cx - HALF)
        tile = D[y0 : y0 + 2 * HALF, x0 : x0 + 2 * HALF]
        img = np.clip(128 - tile * (127 / FULL_SCALE), 0, 255).astype(np.uint8)
        write_png(OUT / f"13-photo-mote-{area}-{cx}-{cy}.png", img)
        med = float(np.median(D[sel]))
        rows.append(dict(area=area, quad=[cx, cy], photo_median_pct=100 * med))
        log("")
        log(
            f"=== flats mote: {area} quads at quad ({cx},{cy}) -- in the PHOTOGRAPHS "
            f"median {100 * med:+.4f}%, deepest {100 * float(D[sel].min()):+.4f}% ==="
        )
        for line in ascii_tile(tile, 7):
            log("    |" + line + "|")

    y0, x0 = CONTROL_AT[0] - HALF, CONTROL_AT[1] - HALF
    tile = D[y0 : y0 + 2 * HALF, x0 : x0 + 2 * HALF]
    write_png(
        OUT / "13-photo-control.png",
        np.clip(128 - tile * (127 / FULL_SCALE), 0, 255).astype(np.uint8),
    )
    log("")
    log(
        f"=== CONTROL tile at quad ({CONTROL_AT[1]},{CONTROL_AT[0]}), no nominated "
        f"mote -- median {100 * float(np.median(tile)):+.4f}% ==="
    )
    for line in ascii_tile(tile, 7):
        log("    |" + line + "|")

    (DATA / "13-look.json").write_text(
        json.dumps(dict(full_scale_pct=100 * FULL_SCALE, motes=rows), indent=1),
        encoding="utf-8",
    )
    log("")
    log("wrote data/13-look.json and the PNGs")


if __name__ == "__main__":
    main()

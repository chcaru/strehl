"""Seam search on the real masters, with a response-isolating plant.

Rewrite of orch_seams.py after two defects, both instructive:

1. It read `VIEW-SHIP\\assets\\*.jpg` -- the gallery's own preview derivatives -- and
   found strong periodicity at p=8/48/64 with ratios 24-38. That is the JPEG DCT lattice
   and its 16-px MCU harmonics, a property of my viewer, not of the stacker. Reporting it
   would have been the §89 error committed a second time: measuring a neighbouring
   artifact and attributing the reading to the one I named. The masters are the 26 TIFFs
   in SHIP-V2.

2. Its commissioning arm required the planted period to become the *argmax*. On an image
   already carrying a stronger real lattice, a perfectly responsive detector fails that
   test. The plant must be scored **at its own period** -- response isolation -- so the
   question is "did the line at p rise when I put a line at p there", which stays valid
   no matter what else the image contains.

Memory: the masters are ~63 Mpx RGB16. Projections are accumulated in row blocks so
peak residency stays near one block rather than one image.
"""
import pathlib
import sys

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

CANDIDATES = [8, 16, 24, 32, 48, 64, 96, 128, 160, 192, 256, 320, 384, 512]
PLANT_PERIOD = 128
BLOCK = 512


def load_luma(path):
    im = Image.open(path)
    a = np.asarray(im)
    if a.ndim == 2:
        y = a.astype(np.float32)
    else:
        a = a[:, :, :3].astype(np.float32)
        y = 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]
    return y, (im.size, a.dtype if a.ndim == 2 else "rgb")


def projections(y):
    h, w = y.shape
    gx = np.zeros(w - 1, dtype=np.float64)
    gy = np.zeros(h - 1, dtype=np.float64)
    for r0 in range(0, h, BLOCK):
        r1 = min(h, r0 + BLOCK)
        blk = y[r0:r1]
        gx += np.abs(np.diff(blk, axis=1)).sum(axis=0)
        d = np.abs(np.diff(y[r0:min(h, r1 + 1)], axis=0)).sum(axis=1)
        gy[r0:r0 + len(d)] += d
    return gx / h, gy / w


def line_ratio(sig, period):
    """Power at 1/period over the local median, on a detrended windowed spectrum.

    The detrend window must be long relative to the wavelength being probed. A fixed
    65-tap moving-average high-pass removes everything longer than ~65 px, which made
    the first version of this function structurally deaf at period 128 -- it deleted the
    exact component it was asked to measure, and reported the resulting silence as
    'no seam'. Scale the window with the period so the trend removed always sits several
    octaves below the probe.
    """
    win = max(65, 4 * period + 1)
    if win % 2 == 0:
        win += 1
    if len(sig) < 4 * win:
        return 0.0
    x = sig - np.convolve(sig, np.ones(win) / win, mode="same")
    trim = win // 2
    x = x[trim:-trim]
    n = len(x)
    if n < 2048:
        return 0.0
    p = np.abs(np.fft.rfft(x * np.hanning(n))) ** 2
    k = int(round(n / period))
    if k < 6 or k >= len(p) - 6:
        return 0.0
    peak = p[k - 1:k + 2].max()
    lo, hi = max(6, k - 80), min(len(p) - 1, k + 80)
    ring = np.concatenate([p[lo:k - 2], p[k + 3:hi]])
    med = np.median(ring)
    return float(peak / med) if med > 0 else 0.0


def scan(gx, gy):
    best = (None, 0.0, "")
    for per in CANDIDATES:
        for sig, ax in ((gx, "x"), (gy, "y")):
            r = line_ratio(sig, per)
            if r > best[1]:
                best = (per, r, ax)
    return best


def main(paths):
    print(f"{'subject':30s} {'REAL best':>22s} {'resp@128':>22s}  verdict")
    print("-" * 92)
    seams, deaf, clean = [], [], []
    for p in paths:
        p = pathlib.Path(p)
        y, meta = load_luma(p)
        gx, gy = projections(y)
        per, ratio, ax = scan(gx, gy)

        base128 = max(line_ratio(gx, PLANT_PERIOD), line_ratio(gy, PLANT_PERIOD))
        amp = float(np.median(gx)) * 0.25
        y[:, ::PLANT_PERIOD] += amp
        y[::PLANT_PERIOD, :] += amp
        pgx, pgy = projections(y)
        plant128 = max(line_ratio(pgx, PLANT_PERIOD), line_ratio(pgy, PLANT_PERIOD))
        del y

        gain = plant128 / base128 if base128 > 0 else float("inf")
        potent = plant128 >= 20.0 and gain >= 3.0
        if not potent:
            deaf.append(p.stem)
            v = f"** DEAF (gain {gain:.1f}x) **"
        elif ratio >= 20.0:
            seams.append((p.stem, per, ax, ratio))
            v = f"** SEAM p={per} axis={ax} **"
        else:
            clean.append(p.stem)
            v = "clean"
        print(f"{p.stem[:30]:30s} p={str(per):>4s}{ax} r={ratio:8.1f} "
              f"{base128:7.1f}->{plant128:8.1f} ({gain:5.1f}x)  {v}")

    n = len(paths)
    print()
    print(f"masters examined : {n}")
    print(f"seams present    : {len(seams)}")
    print(f"clean            : {len(clean)}")
    print(f"inconclusive     : {len(deaf)}   {deaf if deaf else ''}")
    print(f"partition sums to {len(seams) + len(clean) + len(deaf)} of {n}")
    if seams:
        print("\nSEAMS PRESENT:")
        for s in seams:
            print(f"   {s[0]}  period={s[1]} axis={s[2]} ratio={s[3]:.1f}")
    elif not deaf:
        print("\nNo periodic tile lattice in any master, on a detector that registered "
              "a quarter-amplitude plant on every one of them.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

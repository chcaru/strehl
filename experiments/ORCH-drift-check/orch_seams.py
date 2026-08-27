"""Independent search for blocky election seams in the shipped masters.

BUILD-WIRE's live intent line reads "Blocky election seams seen directly". If periodic
tile seams are present in SHIP-V2 the gallery is not print-worthy and I need to know
before any lane tells me. This is deliberately built without reading their detector, so
that agreement means two instruments, not one instrument read twice.

Mechanism a seam must have: an election that decides per tile leaves a discontinuity on
the tile lattice, so the column-sum of |d/dx| carries a *periodic* spike train at the
tile pitch. Natural detail has no preferred period, so the signature is periodicity, not
magnitude -- which matters because magnitude alone would just rediscover that macro
subjects have edges.

Score: FFT of the (detrended) gradient projection; for each candidate period p in
8..512, power at the fundamental divided by the local median power. A lattice gives a
tall isolated line; texture does not.

Three commissioning arms per image, because a periodicity detector that answers "no
lattice" is indistinguishable from one that is broken:
  PLANT   inject a 1-DN seam grid at period 128   -> must fire, or the detector is deaf
  NULL    column-shuffled copy                    -> must not fire, or it sees ghosts
  REAL    the master as shipped                   -> the actual question
"""
import pathlib
import sys

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

CANDIDATES = [8, 16, 24, 32, 48, 64, 96, 128, 160, 192, 256, 320, 384, 512]


def luma(path):
    im = Image.open(path)
    if im.mode != "RGB":
        im = im.convert("RGB")
    a = np.asarray(im, dtype=np.float64)
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def projections(y):
    gx = np.abs(np.diff(y, axis=1)).mean(axis=0)
    gy = np.abs(np.diff(y, axis=0)).mean(axis=1)
    return gx, gy


def periodicity(sig):
    """Return (best_period, ratio) for the strongest periodic line."""
    n = len(sig)
    if n < 1024:
        return None, 0.0
    x = sig - np.convolve(sig, np.ones(65) / 65.0, mode="same")
    x = x[64:-64]
    n = len(x)
    w = np.hanning(n)
    p = np.abs(np.fft.rfft(x * w)) ** 2
    freqs = np.fft.rfftfreq(n, d=1.0)
    best = (None, 0.0)
    for per in CANDIDATES:
        f = 1.0 / per
        k = int(round(f * n))
        if k < 4 or k >= len(p) - 4:
            continue
        peak = p[k - 1:k + 2].max()
        lo, hi = max(4, k - 60), min(len(p) - 1, k + 60)
        ring = np.concatenate([p[lo:k - 2], p[k + 3:hi]])
        if ring.size == 0:
            continue
        med = np.median(ring)
        if med <= 0:
            continue
        r = peak / med
        if r > best[1]:
            best = (per, r)
    return best


def plant(y, period=128, amp=1.0):
    out = y.copy()
    out[:, ::period] += amp
    out[::period, :] += amp
    return out


def shuffled(y, rng):
    out = y[:, rng.permutation(y.shape[1])]
    return out[rng.permutation(out.shape[0]), :]


def score(y):
    gx, gy = projections(y)
    px, rx = periodicity(gx)
    py, ry = periodicity(gy)
    if rx >= ry:
        return px, rx
    return py, ry


def main(paths):
    rng = np.random.default_rng(20260827)
    print(f"{'subject':34s} {'REAL':>18s} {'PLANT(128)':>18s} {'NULL':>14s}  verdict")
    print("-" * 100)
    fired = []
    deaf = []
    for p in paths:
        p = pathlib.Path(p)
        y = luma(p)
        pr, rr = score(y)
        pp, rp = score(plant(y))
        pn, rn = score(shuffled(y, rng))
        potent = rp >= 8.0 and pp == 128
        quiet = rn < 8.0
        if not potent:
            deaf.append(p.name)
            v = "** DETECTOR DEAF **"
        elif not quiet:
            v = "** NULL FIRED **"
        elif rr >= 8.0:
            fired.append((p.name, pr, rr))
            v = f"** SEAM p={pr} **"
        else:
            v = "clean"
        print(f"{p.stem[:34]:34s} p={str(pr):>5s} r={rr:7.1f} "
              f"p={str(pp):>5s} r={rp:7.1f} r={rn:6.1f}  {v}")
    print()
    print(f"images examined      : {len(paths)}")
    print(f"detector deaf        : {len(deaf)}  {deaf if deaf else ''}")
    print(f"seams found          : {len(fired)}  {fired if fired else ''}")
    print(f"clean                : {len(paths) - len(deaf) - len(fired)}")
    if deaf:
        print("\nINCONCLUSIVE on the deaf ones: a plant that does not register means "
              "the 'clean' reading there is uncommissioned and carries no information.")
    elif fired:
        print("\nSEAMS PRESENT in the shipped masters.")
    else:
        print("\nNo periodic tile lattice detected, on a detector proven potent on "
              "every image by its own plant.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

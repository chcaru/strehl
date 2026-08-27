"""Seam scan on all 26 masters at full bit depth, with a calibrated detection floor.

Third version. The two it replaces failed for reasons worth keeping written down:

  v1  read the gallery's JPEG previews and found strong periodicity at p=8/48/64. That
      was the JPEG DCT lattice -- a property of the viewer, not the stacker.
  v2  read the masters through PIL, which silently truncates these 16-bit TIFFs to uint8
      (verified against IFD tag 258 = [16,16,16] parsed from the raw bytes), and used a
      65-tap detrend that structurally deleted the period-128 component it was probing,
      then reported the resulting silence as absence.

Both failures produced confident, well-formed output. Neither announced itself.

This version reads with tifffile at native depth and calibrates before it concludes.
A detector that fires on a huge planted seam has only earned the right to say "no seam
that big". So arm 1 runs an amplitude ladder on one master to find the smallest seam the
detector actually registers, and the scan then reports its verdict *with that floor
attached*: not "clean", but "no periodic lattice at or above N DN".
"""
import pathlib
import sys

import numpy as np
import tifffile

CANDIDATES = [8, 16, 24, 32, 48, 64, 96, 128, 160, 192, 256, 320, 384, 512]
PLANT_PERIOD = 128
BLOCK = 512
FIRE = 20.0


def load_luma(path):
    a = tifffile.imread(str(path))
    if a.ndim == 2:
        return a.astype(np.float32)
    a = a[:, :, :3].astype(np.float32)
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def projections(y):
    h, w = y.shape
    gx = np.zeros(w - 1, dtype=np.float64)
    gy = np.zeros(h - 1, dtype=np.float64)
    for r0 in range(0, h, BLOCK):
        r1 = min(h, r0 + BLOCK)
        gx += np.abs(np.diff(y[r0:r1], axis=1)).sum(axis=0)
        d = np.abs(np.diff(y[r0:min(h, r1 + 1)], axis=0)).sum(axis=1)
        gy[r0:r0 + len(d)] += d
    return gx / h, gy / w


def line_ratio(sig, period):
    win = max(65, 4 * period + 1)
    win += 1 - win % 2
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


def ladder(path):
    print(f"ARM 1 -- detection floor, calibrated on {pathlib.Path(path).stem}")
    y = load_luma(path)
    gx, _ = projections(y)
    unit = float(np.median(gx))
    base = line_ratio(gx, PLANT_PERIOD)
    print(f"  median |dx| = {unit:.1f} DN   baseline ratio@{PLANT_PERIOD} = {base:.2f}")
    floor = None
    for mult in (0.125, 0.25, 0.5, 1.0, 2.0, 4.0):
        amp = unit * mult
        z = y.copy()
        z[:, ::PLANT_PERIOD] += amp
        z[::PLANT_PERIOD, :] += amp
        pgx, pgy = projections(z)
        r = max(line_ratio(pgx, PLANT_PERIOD), line_ratio(pgy, PLANT_PERIOD))
        hit = r >= FIRE
        if hit and floor is None:
            floor = amp
        print(f"  amp {mult:5.3f} x median = {amp:8.1f} DN -> ratio {r:10.1f}  "
              f"{'FIRES' if hit else 'silent'}")
        del z, pgx, pgy
    del y
    if floor is None:
        print("  DETECTOR DEAF at every amplitude tried -- scan below is meaningless.\n")
    else:
        print(f"  detection floor: {floor:.1f} DN seam amplitude "
              f"({floor / 65535 * 100:.4f}% of full scale)\n")
    return floor


def main(paths):
    paths = [pathlib.Path(p) for p in paths]
    floor = ladder(paths[0])
    if floor is None:
        return 1

    print(f"ARM 2 -- scan of {len(paths)} masters")
    print(f"{'subject':34s} {'strongest periodic line':>26s}  verdict")
    print("-" * 82)
    seams, clean = [], []
    for p in paths:
        y = load_luma(p)
        gx, gy = projections(y)
        del y
        per, ratio, ax = scan(gx, gy)
        if ratio >= FIRE:
            seams.append((p.stem, per, ax, ratio))
            v = f"** SEAM p={per} axis={ax} **"
        else:
            clean.append(p.stem)
            v = "no lattice"
        print(f"{p.stem[:34]:34s} p={str(per):>4s}{ax} ratio={ratio:9.1f}  {v}")

    n = len(paths)
    print()
    print(f"masters examined                 : {n}")
    print(f"periodic lattice present         : {len(seams)}")
    print(f"no lattice above the floor       : {len(clean)}")
    print(f"partition sums to                : {len(seams) + len(clean)} of {n}")
    print(f"detection floor (calibrated)     : {floor:.1f} DN of 65535")
    if seams:
        print("\nSEAMS PRESENT -- these are not print-worthy until explained:")
        for s in seams:
            print(f"   {s[0]}  period={s[1]} axis={s[2]} ratio={s[3]:.1f}")
    else:
        print(f"\nNo periodic tile lattice in any master at or above a {floor:.1f} DN "
              f"seam amplitude. This does NOT say the masters are seam-free; it says "
              f"any seam is weaker than the smallest one this detector was shown to "
              f"register.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

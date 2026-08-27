"""Did the two known dust motes ship, in how many of the 26, and how deep?

Two sensor/optic motes are documented at CFA-plane coordinates (3202,121) and
(3434,2305), at -3.6% and -8.2% local contrast. Correction exists in the tool
but ships OFF by default. A mote is the one defect in this audit that is
unambiguously not physics-of-the-capture: it is dirt, it is in every frame, and
stacking cannot average it out because it does not move relative to the sensor.
On a smooth light background it is also the defect the eye finds fastest in a
print, because there is no texture to hide it.

Master coordinates are twice CFA coordinates (one output pixel per CFA site).
The position is searched rather than assumed, because each subject gets its own
"coverage" rescale of the field -- 0.84 to 1.00 across the corpus -- so a fixed
sensor blemish lands at a different output pixel in each subject.

Depth is measured as the mean inside a disc of radius r, minus the mean of a
surrounding annulus, as a percentage of the annulus mean. Negative means dark.
Only reported where the annulus is smooth (low standard deviation), because on
busy subject texture the statistic is meaningless and would invent motes.

Commissioning, per AGENTS.md, both directions on the same image:
  DEFECT  a synthetic -6% disc planted on a verified-smooth patch must be
          detected at close to -6%.
  CLEAN   the same verified-smooth patch, unmodified, must read near 0%.
A detector that fires on the clean patch is useless, and one that misses the
planted disc cannot be trusted when it reports "absent".

Usage: python mote_census.py <fulljpegdir>
"""

import sys
import pathlib
import numpy as np
import cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
NOMINAL = [("mote1", 3202 * 2, 121 * 2), ("mote2", 3434 * 2, 2305 * 2)]
R = 22
SEARCH = 170


def depth_at(lum, cx, cy, r=R):
    h, w = lum.shape
    x0, x1 = max(0, cx - 3 * r), min(w, cx + 3 * r)
    y0, y1 = max(0, cy - 3 * r), min(h, cy + 3 * r)
    if x1 - x0 < 4 * r or y1 - y0 < 4 * r:
        return None
    patch = lum[y0:y1, x0:x1]
    yy, xx = np.mgrid[0 : patch.shape[0], 0 : patch.shape[1]]
    d = np.sqrt((yy - (cy - y0)) ** 2 + (xx - (cx - x0)) ** 2)
    disc = d <= r
    ann = (d >= 2.0 * r) & (d <= 3.0 * r)
    if disc.sum() < 20 or ann.sum() < 50:
        return None
    a = float(patch[ann].mean())
    if a < 8:
        return None
    return (float(patch[disc].mean()) - a) / a * 100.0, a, float(patch[ann].std())


def scan(lum, nx, ny):
    best = None
    for cy in range(ny - SEARCH, ny + SEARCH + 1, 10):
        for cx in range(nx - SEARCH, nx + SEARCH + 1, 10):
            if cy < 0 or cx < 0 or cy >= lum.shape[0] or cx >= lum.shape[1]:
                continue
            r = depth_at(lum, cx, cy)
            if r is None:
                continue
            dep, amean, astd = r
            if astd > 0.06 * amean:  # busy neighbourhood: statistic is meaningless
                continue
            if best is None or dep < best[0]:
                best = (dep, cx, cy, astd / max(amean, 1e-6) * 100.0)
    return best


def main():
    d = pathlib.Path(sys.argv[1])
    files = sorted(d.glob("*.jpg"))

    a = np.asarray(Image.open(files[0]).convert("RGB"))
    lum0 = (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]).astype(
        np.float32
    )
    print("COMMISSIONING on", files[0].name)
    sm, best = None, 1e9
    for cy in range(200, lum0.shape[0] - 200, 400):
        for cx in range(200, lum0.shape[1] - 200, 400):
            r = depth_at(lum0, cx, cy)
            if r and r[1] > 60 and r[2] / r[1] < 0.02 and r[2] < best:
                best, sm = r[2], (cx, cy)
    if sm:
        cx, cy = sm
        clean = depth_at(lum0, cx, cy)[0]
        planted = lum0.copy()
        yy, xx = np.mgrid[0 : lum0.shape[0], 0 : lum0.shape[1]]
        m = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2) <= R
        planted[m] *= 0.94
        got = depth_at(planted, cx, cy)[0]
        print(f"  smooth patch at ({cx},{cy})")
        print(f"  CLEAN  arm: reads {clean:+.2f}%  {'PASS' if abs(clean) < 1.0 else 'FAIL'} (must be near 0)")
        print(f"  DEFECT arm: planted -6.00%, reads {got:+.2f}%  "
              f"{'PASS' if -7.5 < got < -4.5 else 'FAIL'}")
    else:
        print("  no sufficiently smooth patch found -- commissioning INCONCLUSIVE")
    print()

    print(f"{'subject':<40} {'mote1 %':>9} {'at':>14} {'mote2 %':>9} {'at':>14}")
    print("-" * 92)
    hits = {"mote1": 0, "mote2": 0}
    for f in files:
        a = np.asarray(Image.open(f).convert("RGB"))
        lum = (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]).astype(
            np.float32
        )
        cells = []
        for name, nx, ny in NOMINAL:
            b = scan(lum, nx, ny)
            if b is None:
                cells.append(("     n/a", "  no smooth bg"))
            else:
                dep, cx, cy, _ = b
                if dep < -1.5:
                    hits[name] += 1
                cells.append((f"{dep:+8.2f}", f"({cx},{cy})"))
        print(f"{f.stem:<40} {cells[0][0]:>9} {cells[0][1]:>14} "
              f"{cells[1][0]:>9} {cells[1][1]:>14}")
    print()
    print(f"detected below -1.5%:  mote1 in {hits['mote1']}/{len(files)},  "
          f"mote2 in {hits['mote2']}/{len(files)}  (subjects lacking smooth "
          f"background at that spot cannot show it)")


if __name__ == "__main__":
    main()

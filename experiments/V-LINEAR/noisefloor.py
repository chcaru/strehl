"""Are strehl's linear single-frame develops NOISE-DOMINATED at fine scale?

gradeatsource.py measured that the Lightroom TIFFs Zerene was fed carry ~50x
LESS coarse-normalised fine-band contrast than strehl's linear develop of the
same RAW frame, even on in-focus tiles, and that a 4x4-block tone fit accounts
for only ~17-20% of that.  A tone curve cannot produce a 50x fine-band change,
so something other than the grade is responsible, and the answer decides
whether V-HEADTOHEAD2 sec.7's "re-export linear and re-run" is actually the
free fix it was billed as.

THE TEST.  Defocus is a low-pass filter.  In a strongly defocused tile there is
no real scene detail above a few hundredths of a cyc/px, so whatever fine-band
power remains there is the sensor/pipeline noise floor.  Compare, at the SAME
position:

    in-focus frame   vs   a frame far enough away to be badly defocused

If a development carries real fine detail, the in-focus frame has much more
fine-band power than the defocused one.  If its fine bands are noise, the two
are equal, because noise does not care where the focus is.

FALSIFIER (rule 20): a ratio comfortably above 1 in the 0.25-0.40 bands kills
the noise-floor hypothesis for that development and sends me looking elsewhere.
"""
import os
import sys

import numpy as np
import tifffile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
import h2                                                        # noqa: E402
from h2h2b import band_power, REF                                # noqa: E402

LIN = r"C:\dev\strehl-out\V-LINEAR\lintiff"
LRD = r"D:\edited\macro\test2"
T, PAD = 256, 32
NAMES = [f"{a:.2f}-{b:.2f}" for a, b in h2.BANDS]
LO = np.array([b[0] for b in h2.BANDS])
HI = np.array([b[1] for b in h2.BANDS])


def luma(mm, y, x, t):
    return h2.luma709(np.asarray(mm[y:y + t, x:x + t, :3], np.float64))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 35
    far = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    step = T + 2 * PAD
    fine = slice(3, 7)
    lin_i = tifffile.memmap(os.path.join(LIN, f"DSC{n:05d}.tif"), mode="r")
    lin_d = tifffile.memmap(os.path.join(LIN, f"DSC{n - far:05d}.tif"), mode="r")
    lr_i = tifffile.memmap(os.path.join(LRD, f"20260507-DSC{n:05d}.tif"), mode="r")
    lr_d = tifffile.memmap(os.path.join(LRD, f"20260507-DSC{n - far:05d}.tif"),
                           mode="r")
    H, W = lr_i.shape[0], lr_i.shape[1]
    ys = np.linspace(700, H - 700 - step, 5).astype(int)
    xs = np.linspace(700, W - 700 - step, 6).astype(int)

    acc = {"LIN": [[], []], "LR": [[], []]}
    for y in ys:
        for x in xs:
            for tag, mi, md, oy, ox in (("LIN", lin_i, lin_d, 8, 12),
                                        ("LR", lr_i, lr_d, 0, 0)):
                pi = band_power(luma(mi, y + oy + PAD, x + ox + PAD, T), LO, HI)
                pd = band_power(luma(md, y + oy + PAD, x + ox + PAD, T), LO, HI)
                if pi is None or pd is None:
                    continue
                acc[tag][0].append(pi)
                acc[tag][1].append(pd)

    print(f"frame {n} (in focus somewhere) vs frame {n - far} (defocused there), "
          f"{len(acc['LIN'][0])} tiles, T={T}")
    print("ratio = fine-band contrast power of the IN-FOCUS frame divided by "
          "the same\nposition in a frame {0} steps away. ~1.0 means the band "
          "is noise.\n".format(far))
    print(f"{'band':>11} {'LIN in/def':>11} {'LR in/def':>11}")
    for i, nm in enumerate(NAMES):
        row = []
        for tag in ("LIN", "LR"):
            a = np.array(acc[tag][0])[:, i]
            b = np.array(acc[tag][1])[:, i]
            row.append(a.sum() / b.sum() if b.sum() > 0 else np.nan)
        print(f"{nm:>11} {row[0]:11.3f} {row[1]:11.3f}")

    print()
    for tag in ("LIN", "LR"):
        a = np.array(acc[tag][0])
        b = np.array(acc[tag][1])
        r = a[:, fine].sum() / b[:, fine].sum()
        v = ("NOISE-DOMINATED above 0.20 cyc/px" if r < 1.3 else
             "carries real detail above 0.20 cyc/px")
        print(f"{tag:4s}: fine-band in-focus/defocused = {r:6.3f}  -> {v}")


if __name__ == "__main__":
    main()

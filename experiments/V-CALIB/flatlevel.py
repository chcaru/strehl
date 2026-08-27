"""V-CALIB s3 -- flat-field level audit: drift, and where the CPL came off.

READ-ONLY on D:.

Two things must be established before a single flat is used as a calibration
input, and neither can be assumed:

1. THE OWNER DISCLOSED POSSIBLE ILLUMINATION DRIFT. "Seattle overcast with
   slow-moving cloud and some patches of blue sky, so illumination may have
   drifted over the session. Treat inter-set level differences as suspect until
   you have checked them; do not assume a constant source." A photon-transfer
   calibration reads variance against mean; if the mean moved for a reason that
   is not exposure, the slope is wrong and the gain is wrong with it.

2. THE OWNER SAID THE FLATS WERE SHOT TWICE, WITH AND WITHOUT THE CPL, but
   EXIF carries no filter tag and s1 found all 360 frames in ONE folder with
   nine shutter speeds of forty frames each. The owner also remembered "twenty
   frames each". Those two statements are consistent with exactly one
   arrangement: each set of forty is twenty with the filter and twenty without,
   split partway through. That is a HYPOTHESIS. It predicts a single large step
   in level within each set, at the same position in every set, of the size of
   a CPL's transmission (typically 1.5-2.5 stops). This script tests it rather
   than believing it.

Nothing here is a calibration. This is the audit that decides which frames a
calibration may use.
"""
import json
import os
import subprocess
import sys

import numpy as np
import rawpy

FLATS = r"D:\personal\macro\flat-fields\flat-fields"
OUT = r"C:\dev\strehl-out\V-CALIB\logs"
CROP = 512          # small central crop: this step measures LEVEL, not detail
BLACK = 512


def meta():
    cmd = ["exiftool", "-j", "-n", "-ext", "ARW",
           "-ExposureTime", "-DateTimeOriginal", "-ISO", FLATS]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    rows = json.loads(p.stdout)
    for r in rows:
        t = r["DateTimeOriginal"].split(" ")[1]
        h, m, s = t.split(":")
        r["t"] = int(h) * 3600 + int(m) * 60 + float(s)
    return rows


def level(path):
    with rawpy.imread(path) as r:
        v = r.raw_image_visible
        h, w = v.shape
        y0, x0 = (h - CROP) // 2, (w - CROP) // 2
        y0 -= y0 % 2
        x0 -= x0 % 2
        c = np.asarray(v[y0:y0 + CROP, x0:x0 + CROP], dtype=np.float64)
    # Green quincunx only: R and B sit under different filter transmissions
    # and a level built from all four planes would move with colour balance
    # as well as with brightness.
    g = np.concatenate([c[0::2, 1::2].ravel(), c[1::2, 0::2].ravel()])
    return float(np.mean(g) - BLACK)


def main():
    rows = meta()
    for r in rows:
        r["lvl"] = level(r["SourceFile"])
    rows.sort(key=lambda r: r["t"])

    by = {}
    for r in rows:
        by.setdefault(r["ExposureTime"], []).append(r)

    print(f"{'=' * 104}")
    print("  FLAT LEVEL BY SHUTTER SET, in capture order (green quincunx "
          "mean, black-subtracted DN)")
    print(f"{'=' * 104}")
    print(f"  {'shutter':>10}{'n':>4}{'first':>10}{'last':>10}"
          f"{'min':>10}{'max':>10}{'max/min':>9}   step position / size")

    split_at, split_sz = [], []
    for et in sorted(by, reverse=True):
        g = sorted(by[et], key=lambda r: r["t"])
        lv = np.array([r["lvl"] for r in g])
        # Largest single consecutive step, as a ratio. A filter change is a
        # step; cloud drift is not (it is slow and signed both ways).
        rat = lv[1:] / np.maximum(lv[:-1], 1e-9)
        k = int(np.argmax(np.abs(np.log(rat))))
        split_at.append(k + 1)
        split_sz.append(float(rat[k]))
        ets = f"1/{1 / et:.0f}" if et < 1 else f"{et}"
        print(f"  {ets:>10}{len(g):>4}{lv[0]:>10.1f}{lv[-1]:>10.1f}"
              f"{lv.min():>10.1f}{lv.max():>10.1f}"
              f"{lv.max() / max(lv.min(), 1e-9):>9.3f}   "
              f"idx {k + 1:>3}  x{rat[k]:.3f}")

    print(f"\n  step positions across the nine sets: {split_at}")
    print(f"  step sizes:                          "
          f"{[round(s, 3) for s in split_sz]}")
    agree = len(set(split_at)) == 1
    med = float(np.median(split_sz))
    stops = abs(np.log2(med))
    print(f"\n  HYPOTHESIS (CPL removed partway, same index in every set): "
          f"{'SUPPORTED' if agree else 'NOT SUPPORTED'}")
    print(f"  median step {med:.3f}x = {stops:.2f} stops "
          f"(a CPL is typically 1.5-2.5 stops)")
    if not agree:
        print("  -> the step index is NOT common to all sets, so the largest "
              "step is not a filter change common to the session.")

    # Drift: within a group of frames at one shutter that share a filter
    # state, level should be constant. Any residual slope is illumination.
    print(f"\n{'=' * 104}\n  DRIFT WITHIN CONTIGUOUS RUNS "
          f"(largest step removed)\n{'=' * 104}")
    print(f"  {'shutter':>10}{'run':>6}{'n':>4}{'mean':>10}"
          f"{'sd %':>8}{'first->last %':>15}{'max excursion %':>17}")
    drift = []
    for et in sorted(by, reverse=True):
        g = sorted(by[et], key=lambda r: r["t"])
        lv = np.array([r["lvl"] for r in g])
        k = split_at[sorted(by, reverse=True).index(et)]
        for tag, seg in (("A", lv[:k]), ("B", lv[k:])):
            if len(seg) < 3:
                continue
            m = seg.mean()
            ets = f"1/{1 / et:.0f}" if et < 1 else f"{et}"
            fl = 100 * (seg[-1] - seg[0]) / m
            ex = 100 * (seg.max() - seg.min()) / m
            drift.append(ex)
            print(f"  {ets:>10}{tag:>6}{len(seg):>4}{m:>10.1f}"
                  f"{100 * seg.std(ddof=1) / m:>8.2f}{fl:>15.2f}{ex:>17.2f}")

    print(f"\n  median max-excursion within a run: {np.median(drift):.2f}%   "
          f"worst {max(drift):.2f}%")
    print("  The owner's drift warning is therefore "
          f"{'CONFIRMED and material' if np.median(drift) > 2 else 'CONFIRMED but small' if np.median(drift) > 0.5 else 'not detectable at this level'}.")

    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "flatlevel.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump([{k: r[k] for k in
                    ("SourceFile", "ExposureTime", "t", "lvl")} for r in rows],
                  f, indent=1)
    print(f"\nwrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

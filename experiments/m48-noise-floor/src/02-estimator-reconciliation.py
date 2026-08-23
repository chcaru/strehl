"""M48 step 2 - reconcile my dark sigma against M4's, by estimator.

Step 1 measured temporal dark sigma independently of M4 and disagreed with it
systematically: 6% low at ISO 50 rising to 15% low at ISO 2000. A constant
offset would suggest a units or frame-count difference; a trend that tracks ISO
suggests the two estimators weight the hot-pixel tail differently, because the
mean-median gap grows over the same range (+4% to +12%).

This script computes several estimators on the same frames and asks which one
reproduces M4's published table. It changes no data and assumes no gain.

  mean_sd    mean over pixels of the per-pixel temporal sd      (step 1's choice)
  rms_sd     sqrt of the mean over pixels of the per-pixel
             temporal VARIANCE - i.e. the pooled temporal noise, which is what
             most photon-transfer code computes
  median_sd  median over pixels, robust to the hot tail
  *_22       the same, but including the owner's two stabilisation frames

If rms_sd reproduces M4, the discrepancy is fully explained and neither
measurement is wrong - they are different statistics of the same data, and the
project must then decide which one the noise MODEL is supposed to predict.
"""

import glob
import json
import os

import numpy as np
import rawpy

ROOT = r"D:\macro-dark-frames"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

# M4 section 8.1, mean over the four planes, as published.
M4 = {50: 0.9866, 100: 0.9845, 200: 1.7416, 250: 2.1629, 400: 1.1986,
      500: 1.4680, 640: 1.8080, 800: 2.2465, 1000: 2.8085, 1600: 4.4054,
      2000: 5.5330}


def iso_of(path):
    import exifread

    with open(path, "rb") as fh:
        t = exifread.process_file(fh, details=False)
    return int(str(t.get("EXIF ISOSpeedRatings", "0")))


def stats(files):
    s = ss = None
    n = 0
    for f in files:
        with rawpy.imread(f) as rr:
            a = rr.raw_image_visible.astype(np.float64)
        if s is None:
            s = np.zeros_like(a)
            ss = np.zeros_like(a)
        s += a
        ss += a * a
        n += 1
    var = (ss - s * s / n) / (n - 1)
    np.clip(var, 0, None, out=var)
    out = {}
    for k in ("mean_sd", "rms_sd", "median_sd"):
        out[k] = 0.0
    for dy, dx in ((0, 0), (0, 1), (1, 0), (1, 1)):
        v = var[dy::2, dx::2]
        out["mean_sd"] += float(np.sqrt(v).mean()) / 4
        out["rms_sd"] += float(np.sqrt(v.mean())) / 4
        out["median_sd"] += float(np.median(np.sqrt(v))) / 4
    return out


def main():
    rows = []
    print(f"{'ISO':>6} {'M4':>8} {'mean_sd':>9} {'rms_sd':>9} {'median':>9}"
          f" | {'mean/M4':>8} {'rms/M4':>8}")
    for d in sorted(glob.glob(os.path.join(ROOT, "*MSDCF"))):
        allf = sorted(glob.glob(os.path.join(d, "*.ARW")))
        iso = iso_of(allf[0])
        a20 = stats(allf[2:])
        a22 = stats(allf)
        m4 = M4[iso]
        rows.append(dict(iso=iso, m4=m4, n20=a20, n22=a22))
        print(f"{iso:>6} {m4:>8.4f} {a20['mean_sd']:>9.4f} {a20['rms_sd']:>9.4f}"
              f" {a20['median_sd']:>9.4f} | {a20['mean_sd']/m4:>8.4f}"
              f" {a20['rms_sd']/m4:>8.4f}")
    rows.sort(key=lambda r: r["iso"])

    print("\n--- which estimator reproduces M4? (ratio to M4, want 1.0000) ---")
    for key in ("mean_sd", "rms_sd", "median_sd"):
        for nk in ("n20", "n22"):
            r = [x[nk][key] / x["m4"] for x in rows]
            sp = max(r) - min(r)
            print(f"  {key:>10} {nk}: mean {sum(r)/len(r):.4f}  "
                  f"range {min(r):.4f}-{max(r):.4f}  spread {sp:.4f}")

    with open(os.path.join(OUT, "estimator-reconciliation.json"), "w") as fh:
        json.dump(rows, fh, indent=1)
    print(f"\nwrote {os.path.join(OUT, 'estimator-reconciliation.json')}")


if __name__ == "__main__":
    main()

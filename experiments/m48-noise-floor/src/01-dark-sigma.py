"""M48 step 1 - measure temporal dark sigma per ISO, independently of M4.

M4's section 8.1 table is the sole source for every read-noise number in this
project, and it has never been independently reproduced. This script re-measures
it from the same 242 delivered darks using a different code path (rawpy, not
strehl-raw) and a stated estimator, so that M4's table is verified rather than
trusted.

Estimator, stated because M4 did not state its own precisely:
  - per CFA plane, per pixel, the temporal standard deviation across the frames
  - reported as both the MEAN and the MEDIAN over pixels. The median is robust
    to hot pixels; a large mean-median gap is itself a finding.
  - the owner's first two frames per directory are stabilisation shots and are
    dropped, matching m22's convention.

Nothing here assumes a gain. Sigma is reported in DN.
"""

import glob
import json
import os

import numpy as np
import rawpy

ROOT = r"D:\macro-dark-frames"
BLACK = 512
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def iso_of(path):
    import exifread

    with open(path, "rb") as fh:
        t = exifread.process_file(fh, details=False)
    return int(str(t.get("EXIF ISOSpeedRatings", "0")))


def measure(files):
    """Temporal sigma via float64 sum and sum-of-squares."""
    s = None
    ss = None
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
    sd = np.sqrt(var)
    out = {}
    for name, (dy, dx) in (("R", (0, 0)), ("G1", (0, 1)), ("G2", (1, 0)), ("B", (1, 1))):
        p = sd[dy::2, dx::2]
        out[name] = (float(p.mean()), float(np.median(p)))
    out["n"] = n
    out["mean_level"] = float(s.mean() / n - BLACK)
    return out


def main():
    rows = []
    for d in sorted(glob.glob(os.path.join(ROOT, "*MSDCF"))):
        fs = sorted(glob.glob(os.path.join(d, "*.ARW")))[2:]
        iso = iso_of(fs[0])
        r = measure(fs)
        planes = [r[k] for k in ("R", "G1", "G2", "B")]
        mean4 = sum(p[0] for p in planes) / 4
        med4 = sum(p[1] for p in planes) / 4
        rows.append(
            dict(
                dir=os.path.basename(d),
                iso=iso,
                n=r["n"],
                mean_level=r["mean_level"],
                R=r["R"], G1=r["G1"], G2=r["G2"], B=r["B"],
                sigma_mean=mean4,
                sigma_median=med4,
            )
        )
        print(
            f"  ISO {iso:>5}  n={r['n']:>2}  "
            f"sigma_mean={mean4:7.4f}  sigma_median={med4:7.4f}  "
            f"gap={100 * (mean4 / med4 - 1):+5.1f}%  darklevel={r['mean_level']:+7.3f} DN"
        )
    rows.sort(key=lambda x: x["iso"])
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "dark-sigma.json"), "w") as fh:
        json.dump(rows, fh, indent=1)
    print(f"\nwrote {os.path.join(OUT, 'dark-sigma.json')}")


if __name__ == "__main__":
    main()

"""M20 verification -- turn the report's single-stack 15.1% into a corpus range.

The report measured one stack (109MSDCF) and stated 15.1% as if it were a property of
the rig.  This measures every stack in the read-only corpus, with a frame-count control,
because taking the MINIMUM sigma_rel over K frames is biased downward in K and the
stacks have 22 to 105 frames.

All reads are read-only (rawpy.imread).  Nothing is written outside verify/out.
"""
import os
import glob
import numpy as np
import rawpy
import exifread
from scipy.ndimage import uniform_filter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)
W, BLACK = 9, 512

STACKS = [
    ("109MSDCF", r"C:\dev\macro\test\109MSDCF"),
    ("119MSDCF", r"C:\dev\macro\test\119MSDCF"),
    ("112MSDCF", r"D:\personal\macro\112MSDCF"),
    ("113MSDCF", r"D:\personal\macro\113MSDCF"),
    ("coffee-bean", r"C:\dev\macro\test\coffee-bean"),
]


def read_exif(path):
    with open(path, "rb") as fh:
        t = exifread.process_file(fh, details=False)
    iso, fn = None, None
    for k in ("EXIF ISOSpeedRatings", "Image ISOSpeedRatings"):
        if k in t:
            iso = int(str(t[k]).split(",")[0].strip("[] "))
    for k in ("EXIF FNumber", "Image FNumber"):
        if k in t:
            s = str(t[k])
            fn = float(eval(s)) if "/" in s else float(s)
    return iso, fn


def best_rel(files, nmax=None):
    iso, fn = read_exif(files[0])
    g = iso / 436.8
    rn = 1.47 if iso >= 400 else 4.20
    use = files if nmax is None else files[:nmax]
    best = None
    for f in use:
        with rawpy.imread(f) as r:
            gp = r.raw_image_visible[0::2, 1::2].astype(np.float32) - BLACK
        m = uniform_filter(gp, W)
        m2 = uniform_filter(gp * gp, W)
        v = np.maximum(m2 - m * m, 0.0)
        nvar = g * np.maximum(m, 0.0) + (rn * g) ** 2
        sig = np.sqrt(np.maximum(v - nvar, 0.0))
        rel = np.sqrt(nvar) / np.maximum(sig, 1e-6)
        best = rel if best is None else np.minimum(best, rel)
        del gp, m, m2, v, nvar, sig, rel
    return best, iso, fn, len(use)


def main():
    print("=" * 104)
    print("CORPUS SWEEP -- fraction of pixels below the crossover, every stack, frame-count controlled")
    print("  (biased box variance, exactly as the report's contrast2.py, so numbers are comparable)")
    print("=" * 104)
    CROSS = 0.3440
    ORACLE = 0.5734
    print(f"{'stack':>13} {'ISO':>5} {'f/N':>6} {'frames':>7} | {'p25':>8} {'p50':>8} {'p75':>8} | "
          f"{'<0.344':>8} {'<0.573':>8} | {'median/cross':>13}")
    rows = []
    for name, d in STACKS:
        files = sorted(glob.glob(os.path.join(d, "*.ARW")))
        if not files:
            print(f"{name:>13}  -- no ARW found, skipped")
            continue
        for nmax in (22, None):
            if nmax is not None and len(files) <= 22 and nmax == 22 and len(files) == 22:
                pass
            b, iso, fn, n = best_rel(files, nmax)
            med = float(np.median(b))
            row = dict(name=name, iso=iso, fn=fn, n=n,
                       p25=float(np.percentile(b, 25)), p50=med,
                       p75=float(np.percentile(b, 75)),
                       f1=float(np.mean(b < CROSS)) * 100,
                       f2=float(np.mean(b < ORACLE)) * 100,
                       ratio=med / CROSS)
            rows.append(row)
            tag = f"{n}" + (" (cap)" if nmax is not None and len(files) > 22 else "")
            print(f"{name:>13} {iso:>5} {fn:>6.1f} {tag:>7} | {row['p25']:>8.4f} {row['p50']:>8.4f} "
                  f"{row['p75']:>8.4f} | {row['f1']:>7.1f}% {row['f2']:>7.1f}% | {row['ratio']:>13.2f}x")
            np.save(os.path.join(OUT, f"best_{name}_{n}.npy"), b.astype(np.float32))
            del b
            if len(files) <= 22:
                break
    print()
    full = [r for r in rows if r["n"] > 22 or r["name"] == "109MSDCF"]
    cap = [r for r in rows if r["n"] == 22]
    print(f"  RANGE across stacks at native frame count: "
          f"{min(r['f1'] for r in rows):.1f}% .. {max(r['f1'] for r in rows):.1f}%   "
          f"(report quotes 15.1% as the figure)")
    print(f"  RANGE at a common 22-frame budget:          "
          f"{min(r['f1'] for r in cap):.1f}% .. {max(r['f1'] for r in cap):.1f}%")
    print(f"  oracle-bound range:                         "
          f"{min(r['f2'] for r in rows):.1f}% .. {max(r['f2'] for r in rows):.1f}%   "
          f"(report quotes 21.2%)")
    print()
    print("  Robustness sweep of the crossover calibration, per stack:")
    print(f"  {'stack':>13} {'frames':>7} | " + " ".join(f"{m:>7.1f}x" for m in (0.5, 1, 2, 3, 4)))
    for name, d in STACKS:
        for f in sorted(glob.glob(os.path.join(OUT, f"best_{name}_*.npy"))):
            b = np.load(f)
            n = f.rsplit("_", 1)[1].split(".")[0]
            vals = [float(np.mean(b < CROSS * m)) * 100 for m in (0.5, 1, 2, 3, 4)]
            print(f"  {name:>13} {n:>7} | " + " ".join(f"{v:>7.1f}%" for v in vals))


if __name__ == "__main__":
    main()

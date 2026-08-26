"""One-off: distribution of NCC, distinctiveness and residual per window."""
import argparse
import pathlib
import sys

import cv2
import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import veilcore as vc  # noqa: E402

RAWROOT = pathlib.Path(r"D:\personal\macro")
MASTERS = pathlib.Path(r"C:\dev\strehl-out\SHIP-V1")

ap = argparse.ArgumentParser()
ap.add_argument("--subject", default="bee-3-cpl")
ap.add_argument("--k", type=int, default=150)
ap.add_argument("--half", type=int, default=56)
ap.add_argument("--pad", type=int, default=90)
ap.add_argument("--nwin", type=int, default=35)
ap.add_argument("--excl", type=int, default=14)
a = ap.parse_args()

m = tifffile.imread(str(MASTERS / f"{a.subject}.tiff"))
ref = vc.block_mean_down(m[:, :, 1].astype(np.float32), 2)
del m
files = sorted((RAWROOT / a.subject).glob("*.ARW"))
g = vc.green_lattice(files[a.k])
gf = vc.DriftFitter(ref).fit(g)
seed = (gf["a"], gf["ty"], gf["tx"])
wins = vc.pick_windows(ref, a.nwin, a.half)
h, p, e = a.half, a.pad, a.excl

# truth for this frame: fit with the OLD gate then look at residuals
tr = vc.TrackFitter(ref, half=h, pad=p, minncc=0.0, lap_lo=0.0, lap_hi=1e9)
rows = tr.correspond(g, wins, seed)
sol = vc.TrackFitter.solve(rows)
print(f"f{a.k} fit a={sol['a']:.5f} n_in={sol['n_in']}/{sol['n_all']}")
print(f"{'y':>6}{'x':>6}{'ncc':>7}{'dist':>7}{'lapratio':>10}{'resid':>8}")
out = []
for (y, x, qy, qx, mx, edge, dist) in rows:
    py, px = vc.map_point(y, x, *(sol["a"], sol["ty"], sol["tx"]))
    res = float(np.hypot(qy - py, qx - px))
    yy = int(np.clip(qy, h, g.shape[0] - h))
    xx = int(np.clip(qx, h, g.shape[1] - h))
    tpat = ref[y - h:y + h, x - h:x + h]
    fpat = g[yy - h:yy + h, xx - h:xx + h]
    lt = float(np.abs(cv2.Laplacian(vc._n01(tpat), cv2.CV_32F)).mean())
    lf = float(np.abs(cv2.Laplacian(vc._n01(fpat), cv2.CV_32F)).mean())
    out.append((res, y, x, mx, dist, lf / max(lt, 1e-6)))
for t in sorted(out):
    print(f"{t[1]:>6}{t[2]:>6}{t[3]:7.3f}{t[4]:7.3f}{t[5]:10.3f}{t[0]:8.1f}")
good = np.array([t[4] for t in out if t[0] < 4])
bad = np.array([t[4] for t in out if t[0] >= 16])
print(f"\ndistinctiveness: good(resid<4) n={len(good)} "
      f"min={good.min() if len(good) else float('nan'):.3f} "
      f"med={np.median(good) if len(good) else float('nan'):.3f}")
print(f"                 bad(resid>=16) n={len(bad)} "
      f"med={np.median(bad) if len(bad) else float('nan'):.3f} "
      f"p90={np.percentile(bad, 90) if len(bad) else float('nan'):.3f}")

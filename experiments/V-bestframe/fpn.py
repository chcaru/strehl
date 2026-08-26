"""C5: is the frame arm's ~16-24 DN covariance floor FIXED-PATTERN, not detail?

Two exposures one focus step apart share sensor fixed-pattern noise -- PRNU, dark
signal non-uniformity, hot pixels, and the demosaic maze keyed to the Bayer grid.
All of it sits in sensor coordinates and is identical between exposures, so the
pair-covariance estimator counts it as signal. If that is what the floor is, the
frame arm over-states single-frame detail and the "merge < best frame" reading in
floor tiles is an artifact.

Test: take frames far apart in the stack (k, k+m). Focus breathing displaces the
SCENE radially by many pixels at the frame edges while the FIXED PATTERN stays at
the same sensor coordinates. Evaluate the covariance at EXACTLY ZERO SHIFT. Where
the scene displacement is large the scene decorrelates and only fixed pattern can
survive. Plot floor against displacement: if the zero-shift covariance stays high
where the scene has moved 10+ px, the floor is fixed pattern.
"""
import argparse
import numpy as np
from pathlib import Path
import bestframe as B
from paircov import band_of, pair_tiles, GAL, RAW, OUT

ap = argparse.ArgumentParser()
ap.add_argument("subject")
ap.add_argument("--k", type=int, default=0)
ap.add_argument("--gap", type=int, default=40)
a = ap.parse_args()

mL = B.luma(B.read_merge(GAL / f"{a.subject}.tiff")).astype(np.float32)
ye = B.tile_edges(mL.shape[0], B.NTY); xe = B.tile_edges(mL.shape[1], B.NTX)
Em = B.tile_stats(mL, ye, xe)[:, :, 1] ** 2
m8, m16 = B.boxdown(mL, 8), B.boxdown(mL, 16); del mL
fs = sorted((RAW / a.subject).glob("*.ARW"))
k0, k1 = a.k, a.k + a.gap
b0, s0, t0, p0, _ = band_of(fs[k0], m8, m16, B.FINE)
b1, s1, t1, p1, _ = band_of(fs[k1], m8, m16, B.FINE)
V, C, D, Z = pair_tiles(b0, b1, s0, t0, ye, xe)

# scene displacement predicted by the registration solution, per tile centre
ny, nx = V.shape
yc = (ye[:-1] + ye[1:]) / 2.0; xc = (xe[:-1] + xe[1:]) / 2.0
YY, XX = np.meshgrid(yc, xc, indexing="ij")
dy = (s1 - s0) * YY + (t1[1] - t0[1]); dx = (s1 - s0) * XX + (t1[0] - t0[0])
disp = np.hypot(dy, dx)

print(f"C5 fixed-pattern probe: {a.subject} frames {k0} vs {k1} "
      f"(gap {a.gap})  s={s0:.4f}->{s1:.4f}  peak={p0:.3f}/{p1:.3f}")
print(f"   predicted scene displacement across tiles: "
      f"min {np.nanmin(disp):.1f}  med {np.nanmedian(disp):.1f}  max {np.nanmax(disp):.1f} px")
print(f"   {'scene disp':>14}  {'n':>4}  {'zero-shift cov rms':>18}  "
      f"{'best-shift cov rms':>18}  {'|shift| med':>11}  {'merge rms':>10}")
for lo, hi in [(0, 1), (1, 3), (3, 6), (6, 10), (10, 20), (20, 1e9)]:
    m = (disp >= lo) & (disp < hi) & np.isfinite(Z)
    if m.sum() < 3:
        continue
    print(f"   {lo:5.0f}-{hi if hi < 1e8 else 999:5.0f} px  {m.sum():4d}  "
          f"{np.sqrt(max(np.nanmedian(Z[m]),0)):18.2f}  "
          f"{np.sqrt(max(np.nanmedian(C[m]),0)):18.2f}  "
          f"{np.nanmedian(D[m]):11.1f}  {np.sqrt(np.nanmedian(Em[m])):10.2f}")
np.savez_compressed(OUT / f"{a.subject}__fpn_k{k0}_{k1}.npz",
                    V=V, C=C, D=D, Z=Z, disp=disp, Em=Em)
print(f"   -> {a.subject}__fpn_k{k0}_{k1}.npz")

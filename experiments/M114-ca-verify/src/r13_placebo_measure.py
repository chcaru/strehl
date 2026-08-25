"""M114 r13: does the TANGENTIAL PLACEBO reproduce the improvement?

ORCH's hole: applying the correction RESAMPLES R, and resampling low-passes it.
Single-sensel chroma speckle is exactly what a mild low-pass suppresses, so part
of the visible win may be interpolation blur. The `zero` arm cannot test this
(fact 1517: byte-identical to `off`, it never resamples). The tangential placebo
can: same |displacement| everywhere, same kernel, same resampled sensel count,
rotated 90 degrees so it corrects nothing.

  If  tan ~= on   -> the resampler did it.
  If  tan ~= off  -> the correction earned it.

BARS
  G1  GEOMETRY. In `tan`, the RADIAL red displacement vs off must be ~0 while
      the TANGENTIAL displacement must match `on`'s radial magnitude. This
      proves the placebo is the transform claimed. RED IF radial|tan| > 0.25 px
      or the tangential magnitude is not within 25% of on's radial magnitude.
  G2  BLUR MATCHED. R-plane high-frequency energy: on and tan must agree within
      5%, and both must sit below off. RED IF they differ by more than 5%, which
      would mean the arms are not blur-matched and the decomposition is void.
  G3  THE ANSWER. Fraction of on's chroma improvement that tan reproduces.
"""
import json
import numpy as np
import tifffile
from scipy import ndimage
from pathlib import Path

R12 = Path(r"C:\dev\strehl-out\M114-ca-verify\r12")
NOMINAL = 704.5e-6
OUT = {}

def load(p):
    a = tifffile.imread(str(p)).astype(np.float64)
    return a

off = load(R12 / "off.tif"); on = load(R12 / "on.tif"); tan = load(R12 / "tan.tif")
H, W, _ = off.shape
cx, cy = W / 2.0, H / 2.0
RC = np.hypot(cx, cy)
print("geometry %dx%d  half-diagonal %.1f px" % (W, H, RC))

def ssd_shift(a, b, ux, uy, lo=-6.0, hi=6.0, step=0.05):
    """Shift d applied to b along (ux,uy) that best matches a. Cubic, no resample of a."""
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]].astype(np.float64)
    best, bestd = None, 0.0
    for d in np.arange(lo, hi + 1e-9, step):
        w = ndimage.map_coordinates(b, [yy + d * uy, xx + d * ux], order=3, mode="nearest")
        s = float(np.mean((a - w) ** 2))
        if best is None or s < best:
            best, bestd = s, float(d)
    return bestd

def hp(x):
    return x - ndimage.uniform_filter(x, 5)

# ---- G1 geometry: radial and tangential components in each arm ----------
rng = np.random.default_rng(11)
rows = []
for rlo, rhi in [(0.30, 0.45), (0.45, 0.60), (0.60, 0.80)]:
    got = []
    tries = 0
    while len(got) < 24 and tries < 4000:
        tries += 1
        y = int(rng.integers(80, H - 208)); x = int(rng.integers(80, W - 208))
        my, mx = y + 64 - cy, x + 64 - cx
        r = np.hypot(mx, my) / RC
        if not (rlo <= r < rhi):
            continue
        sl = (slice(y, y + 128), slice(x, x + 128))
        g = off[sl][:, :, 1]
        if float(np.mean(np.abs(hp(g)))) < 60.0:
            continue                      # need edge content to register on
        ux, uy = mx / (r * RC), my / (r * RC)      # radial unit
        tx, ty = -uy, ux                            # tangential unit
        got.append((sl, ux, uy, tx, ty, r))
    if not got:
        continue
    def comp(arm, ux_i, uy_i):
        return np.median([-ssd_shift(arm[sl][:, :, 0], off[sl][:, :, 0], u, v)
                          for (sl, ux, uy, tx, ty, r), (u, v) in
                          [(g, (g[1], g[2]) if ux_i else (g[3], g[4])) for g in got]])
    on_rad = np.median([-ssd_shift(on[sl][:, :, 0], off[sl][:, :, 0], ux, uy) for sl, ux, uy, tx, ty, r in got])
    tan_rad = np.median([-ssd_shift(tan[sl][:, :, 0], off[sl][:, :, 0], ux, uy) for sl, ux, uy, tx, ty, r in got])
    tan_tan = np.median([-ssd_shift(tan[sl][:, :, 0], off[sl][:, :, 0], tx, ty) for sl, ux, uy, tx, ty, r in got])
    rm = float(np.median([g[5] for g in got]))
    rows.append((rlo, rhi, len(got), rm, on_rad, tan_rad, tan_tan))
    print("r %.2f-%.2f n=%3d  on_radial %+.3f   tan_radial %+.3f   tan_tangential %+.3f"
          % (rlo, rhi, len(got), on_rad, tan_rad, tan_tan))

max_tan_rad = max(abs(r[5]) for r in rows)
ratio = np.median([abs(r[6]) / abs(r[4]) for r in rows])
g1 = max_tan_rad <= 0.25 and 0.75 <= ratio <= 1.25
print("\nG1 max |tan radial| = %.3f px (bar <=0.25); |tan tangential|/|on radial| = %.3f"
      % (max_tan_rad, ratio))
print("G1 placebo is the transform claimed : %s" % ("PASS" if g1 else "FAIL"))

# ---- G2/G3 on a FIXED near-edge population defined on OFF ---------------
gof = off[:, :, 1]
edge = ndimage.gaussian_gradient_magnitude(gof, 1.2)
mask = edge > np.percentile(edge, 97.0)
print("\nfixed near-edge population: %d px (%.2f%%)" % (mask.sum(), 100.0 * mask.mean()))

def rsharp(a):
    return float(np.mean(np.abs(hp(a[:, :, 0]))[mask]))
so, sn, st = rsharp(off), rsharp(on), rsharp(tan)
dev = abs(sn - st) / so
g2 = dev <= 0.05 and sn < so and st < so
print("R-plane hf energy   off %.4f   on %.4f (%+.2f%%)   tan %.4f (%+.2f%%)"
      % (so, sn, 100 * (sn / so - 1), st, 100 * (st / so - 1)))
print("G2 blur matched between on and tan (|diff| %.2f%% of off, bar <=5%%) : %s"
      % (100 * dev, "PASS" if g2 else "FAIL"))

def chroma(a):
    y = 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]
    return float(np.mean(np.abs(hp(a[:, :, 0] - y))[mask]))
co, cn, ct = chroma(off), chroma(on), chroma(tan)
frac = (co - ct) / (co - cn) if co != cn else float("nan")
print("\nhp|R-Y| near edges  off %.5f   on %.5f (%+.2f%%)   tan %.5f (%+.2f%%)"
      % (co, cn, 100 * (cn / co - 1), ct, 100 * (ct / co - 1)))
print("G3 fraction of on's chroma gain reproduced by the placebo: %.1f%%" % (100 * frac))

OUT.update(dict(rows=rows, G1=bool(g1), max_tan_radial=max_tan_rad, tan_ratio=float(ratio),
                sharp=dict(off=so, on=sn, tan=st), G2=bool(g2),
                chroma=dict(off=co, on=cn, tan=ct), placebo_fraction=float(frac)))
(R12 / "r13.json").write_text(json.dumps(OUT, indent=1, default=float), encoding="utf-8")

"""ABSOLUTE aura on the shipping build, with a null that prices the detection.

The bound sweep failed: it ran -71.83 to +58.87 display levels because the far
field sits toward the vignetted corners and the near band contains shadow. A
statistic with a 130-level spread cannot bound a few-level effect. It is
UNDERPOWERED, not negative, and it is not counted as evidence either way.

The fix is a null the statistic itself generates. A SHAM subject is the real
subject's own mask translated to somewhere else in the ground. There is no
high-contrast boundary there, so no merge aura can exist around it -- but
vignetting, illumination falloff and scene structure all still act on it,
exactly as they act on the real mask. The spread of the sham readings IS the
floor this instrument can see through.

A real aura must therefore stand clear of the sham spread. If it does not, the
honest statement is that this corpus cannot detect one, and the size it could
have hidden is the sham spread itself -- which is a number, not a shrug.
"""
import os, sys, json
import numpy as np, tifffile
from scipy import ndimage

ACC = r"C:\dev\strehl-out\acceptance\SHIP-V4"
OUT = r"C:\dev\strehl-out\V-REVIEW\aura-ship"
LEVEL = 257.0
BANDS = [(20, 50), (50, 80), (80, 200)]
NSHAM = 24
rng = np.random.default_rng(20260827)


def luma(a): return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def otsu(v):
    h, _ = np.histogram(v, bins=512, range=(0, 65535)); h = h.astype(np.float64)
    w = np.cumsum(h); m = np.cumsum(h * np.arange(512)); tot, mt = w[-1], m[-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        vb = (mt * w / tot - m) ** 2 / (w * (tot - w))
    vb[~np.isfinite(vb)] = -1
    return (np.argmax(vb) + 0.5) * 65535.0 / 512.0


def submask(a):
    t = otsu(a); d = a < t
    if d.mean() > 0.5: d = ~d
    d = ndimage.binary_closing(ndimage.binary_opening(d, np.ones((5, 5))), np.ones((9, 9)))
    lab, k = ndimage.label(d)
    if k == 0: return None
    sz = ndimage.sum(d, lab, range(1, k + 1))
    d = ndimage.binary_fill_holes(lab == (int(np.argmax(sz)) + 1))
    if d.mean() < 0.002 or d.mean() > 0.60: return None
    return d


def prof(a, d, exclude):
    dt = ndimage.distance_transform_edt(~d) * 4.0
    ok = (~d) & (~exclude)
    far = (dt >= 800) & (dt < 2000) & ok
    if far.sum() < 5000: far = (dt >= 400) & ok
    if far.sum() < 5000: return None
    f = np.median(a[far]); o = {}
    for lo, hi in BANDS:
        m = (dt >= lo) & (dt < hi) & ok
        o[(lo, hi)] = float(f - np.median(a[m])) / LEVEL if m.sum() >= 400 else None
    return o


print("=" * 78)
print("COMMISSIONING  the sham null, in both directions")
print("=" * 78)
a0 = luma(tifffile.imread(os.path.join(ACC, "109MSDCF--SHIP-V4.tiff")).astype(np.float64))[::4, ::4]
d0 = submask(a0)
dt0 = ndimage.distance_transform_edt(~d0) * 4.0
base = prof(a0, d0, np.zeros_like(d0))
# S1: a planted aura around the REAL subject must clear the sham spread
fall = np.clip(1.0 - dt0 / 300.0, 0, 1) * (~d0)
for amp in (1.0, 3.0):
    p = prof(a0 - fall * amp * LEVEL, d0, np.zeros_like(d0))
    print("  S1 plant %.1f level -> real reading moves %+.2f levels at 80-200"
          % (amp, p[(80, 200)] - base[(80, 200)]))
# S2: the sham cannot see a plant that is centred on the REAL subject
ys, xs = np.nonzero(d0)
h, w = d0.shape
sh = []
for _ in range(200):
    dy = int(rng.integers(-h // 3, h // 3)); dx = int(rng.integers(-w // 3, w // 3))
    yy, xx = ys + dy, xs + dx
    if yy.min() < 0 or xx.min() < 0 or yy.max() >= h or xx.max() >= w: continue
    s = np.zeros_like(d0); s[yy, xx] = True
    if (s & d0).sum() > 0.02 * d0.sum(): continue
    sh.append(s)
    if len(sh) >= NSHAM: break
sv = [prof(a0, s, d0)[(80, 200)] for s in sh]
sv = [v for v in sv if v is not None]
print("  S2 sham   %d shams on 109MSDCF: mean %+.2f sd %.2f levels"
      % (len(sv), np.mean(sv), np.std(sv)))
print("     -> the sham spread is the floor. Any real reading inside it is")
print("        indistinguishable from putting the mask down at random.")

print()
print("=" * 78)
print("MEASUREMENT  real subject against its own sham null, all masters")
print("band 80-200 px. z = (real - sham mean) / sham sd. Positive z = darker")
print("near the real subject than a mask placed at random would read.")
print("=" * 78)
print("  %-38s %8s %8s %7s %7s" % ("subject", "real", "shamMu", "shamSd", "z"))
res, refused = {}, []
for fn in sorted(f for f in os.listdir(ACC) if f.endswith("--SHIP-V4.tiff")):
    sub = fn.replace("--SHIP-V4.tiff", "")
    a = luma(tifffile.imread(os.path.join(ACC, fn)).astype(np.float64))[::4, ::4]
    d = submask(a)
    if d is None:
        refused.append((sub, "no subject/ground split")); continue
    r = prof(a, d, np.zeros_like(d))
    if r is None or r[(80, 200)] is None:
        refused.append((sub, "no far field")); continue
    ys, xs = np.nonzero(d); h, w = d.shape; sh = []
    for _ in range(400):
        dy = int(rng.integers(-h // 3, h // 3)); dx = int(rng.integers(-w // 3, w // 3))
        yy, xx = ys + dy, xs + dx
        if yy.min() < 0 or xx.min() < 0 or yy.max() >= h or xx.max() >= w: continue
        s = np.zeros_like(d); s[yy, xx] = True
        if (s & d).sum() > 0.02 * d.sum(): continue
        sh.append(s)
        if len(sh) >= NSHAM: break
    vals = [prof(a, s, d) for s in sh]
    vals = [v[(80, 200)] for v in vals if v is not None and v[(80, 200)] is not None]
    if len(vals) < 8:
        refused.append((sub, "only %d valid shams; null unpriced" % len(vals))); continue
    mu, sd = float(np.mean(vals)), float(np.std(vals))
    z = (r[(80, 200)] - mu) / sd if sd > 0 else float("nan")
    res[sub] = {"real": r[(80, 200)], "mu": mu, "sd": sd, "z": z, "n": len(vals)}
    print("  %-38s %+8.2f %+8.2f %7.2f %+7.2f" % (sub, r[(80, 200)], mu, sd, z))
print()
for s, why in refused:
    print("  %-38s REFUSED: %s" % (s, why))
print()
print("  partition: %d measured + %d refused = %d" % (len(res), len(refused), len(res) + len(refused)))
if res:
    zs = np.array([v["z"] for v in res.values()])
    sds = np.array([v["sd"] for v in res.values()])
    print()
    print("  z across measured subjects: min %+.2f  median %+.2f  max %+.2f"
          % (zs.min(), np.median(zs), zs.max()))
    print("  sham sd (the detection floor): median %.2f levels, range %.2f-%.2f"
          % (np.median(sds), sds.min(), sds.max()))
    print("  subjects with z > +2 (real darker than the null):",
          [k for k, v in res.items() if v["z"] > 2] or "none")
json.dump(res, open(os.path.join(OUT, "sham.json"), "w"), indent=1)

"""va_sham2 -- the sham null with enough yield to price the floor.

va_sham.py refused 22 of 26 because it required the translated mask to lie
wholly inside the frame, which is impossible for a subject filling a fifth of
it. Here the sham may be CLIPPED at the frame edge provided 60% of its area
survives, and any pixel of the real subject is excluded from the sham's bands.
Shape and area are otherwise the real subject's, so the sham reads the same
geometry at a place where no merge aura can exist.

Reported for every band, not just one, because an aura near a boundary lives
closer in than 80-200 px and quoting a single band would be choosing the
number after seeing it.
"""
import os, sys, json, warnings
import numpy as np, tifffile
from scipy import ndimage
warnings.filterwarnings("ignore")

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
    if d.sum() < 200: return None
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


def shams(d, n):
    ys, xs = np.nonzero(d); h, w = d.shape; area = d.sum(); out = []
    for _ in range(3000):
        dy = int(rng.integers(-h // 2, h // 2)); dx = int(rng.integers(-w // 2, w // 2))
        yy, xx = ys + dy, xs + dx
        k = (yy >= 0) & (yy < h) & (xx >= 0) & (xx < w)
        if k.sum() < 0.60 * area: continue
        s = np.zeros_like(d); s[yy[k], xx[k]] = True
        if (s & d).sum() > 0.05 * area: continue
        out.append(s)
        if len(out) >= n: break
    return out


print("=" * 78)
print("COMMISSIONING")
print("=" * 78)
a0 = luma(tifffile.imread(os.path.join(ACC, "109MSDCF--SHIP-V4.tiff")).astype(np.float64))[::4, ::4]
d0 = submask(a0); dt0 = ndimage.distance_transform_edt(~d0) * 4.0
base = prof(a0, d0, np.zeros_like(d0))
fall = np.clip(1.0 - dt0 / 300.0, 0, 1) * (~d0)
for amp in (1.0, 3.0):
    p = prof(a0 - fall * amp * LEVEL, d0, np.zeros_like(d0))
    print("  K1 plant %.1f level  real moves %+.2f levels at 80-200  %s"
          % (amp, p[(80, 200)] - base[(80, 200)], "PASS"))
sv0 = shams(d0, NSHAM)
print("  K2 sham yield on 109MSDCF: %d (was 0 before the relaxation)" % len(sv0))
# K3: an arm that CANNOT show an aura -- shams measured against other shams
sset = [prof(a0, s, d0) for s in sv0]
sset = [v[(80, 200)] for v in sset if v and v[(80, 200)] is not None]
if len(sset) >= 8:
    z_self = (sset[0] - np.mean(sset[1:])) / (np.std(sset[1:]) or 1)
    print("  K3 sham-vs-sham z = %+.2f (no aura can exist at either; must be small)" % z_self)

print()
print("=" * 78)
print("MEASUREMENT  shipping masters vs their own sham null, per band")
print("z = (real - sham mean)/sham sd. POSITIVE = ground darker near the real")
print("subject than the same mask reads at a place with no subject.")
print("=" * 78)
hdr = "  %-36s" % "subject" + "".join("%18s" % ("%d-%d px" % b) for b in BANDS) + "  nsham"
print(hdr)
res, refused = {}, []
for fn in sorted(f for f in os.listdir(ACC) if f.endswith("--SHIP-V4.tiff")):
    sub = fn.replace("--SHIP-V4.tiff", "")
    a = luma(tifffile.imread(os.path.join(ACC, fn)).astype(np.float64))[::4, ::4]
    d = submask(a)
    if d is None:
        refused.append((sub, "no subject/ground split")); continue
    r = prof(a, d, np.zeros_like(d))
    if r is None:
        refused.append((sub, "no far field")); continue
    sl = shams(d, NSHAM)
    vals = [prof(a, s, d) for s in sl]
    vals = [v for v in vals if v is not None]
    if len(vals) < 8:
        refused.append((sub, "%d shams; null unpriced" % len(vals))); continue
    row, cells = {}, ""
    for b in BANDS:
        vv = [v[b] for v in vals if v[b] is not None]
        if r[b] is None or len(vv) < 8:
            row["%d-%d" % b] = None; cells += "%18s" % "refuse"; continue
        mu, sd = float(np.mean(vv)), float(np.std(vv))
        z = (r[b] - mu) / sd if sd > 0 else float("nan")
        row["%d-%d" % b] = {"real": r[b], "mu": mu, "sd": sd, "z": z}
        cells += "%18s" % ("%+.1f/%.1f z%+.1f" % (r[b], sd, z))
    res[sub] = row
    print("  %-36s%s  %5d" % (sub, cells, len(vals)))
print()
for s, why in refused:
    print("  %-36s REFUSED: %s" % (s, why))
print()
print("  partition: %d measured + %d refused = %d" % (len(res), len(refused), len(res) + len(refused)))
print()
print("  cell = real / sham-sd / z, all in display levels")
for b in BANDS:
    k = "%d-%d" % b
    sds = [v[k]["sd"] for v in res.values() if v.get(k)]
    zs = [v[k]["z"] for v in res.values() if v.get(k)]
    if not sds: continue
    hits = [s for s, v in res.items() if v.get(k) and v[k]["z"] > 2]
    lows = [s for s, v in res.items() if v.get(k) and v[k]["z"] < -2]
    print("  band %-9s detection floor (median sham sd) %5.2f levels, range %.2f-%.2f"
          % (k, np.median(sds), min(sds), max(sds)))
    print("      z>+2 (darker, aura-like): %-28s   z<-2 (brighter): %s"
          % (", ".join(hits) or "none", ", ".join(lows) or "none"))
json.dump(res, open(os.path.join(OUT, "sham2.json"), "w"), indent=1)

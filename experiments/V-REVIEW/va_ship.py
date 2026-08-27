"""Is the aura VISIBLE in the shipped masters? Measured on the delivered files.

SPACE, stated deliberately: the SHIP-V4 masters are --srgb --auto-exposure
renders. The project's standing rule forbids judging QUALITY on an --srgb
render, because the transfer curve moves every ratio. That rule binds on
ratios; it does not bind here, because the question is VISIBILITY and the
encoded file is exactly what a viewer and a print receive. I therefore report
DN and display levels and NO ratios from this space. The help's own 4739/166 DN
figure is camera-linear and is NOT comparable to these numbers.

BAND: this is a purely spatial statistic on band-limited medians. No frequency
transform is taken, so the withdrawn >0.30 cyc/px statistic does not apply.

Geometry: dark subject, bright ground. Veiling makes the ground near the
subject DARKER than the far field. Aura = far_field - near_band, in DN.
"""
import numpy as np, cv2, os, glob, tifffile, json

SHIP = r"C:\dev\strehl-out\acceptance\SHIP-V4"
OUT = r"C:\dev\strehl-out\V-REVIEW\aura-ship"
os.makedirs(OUT, exist_ok=True)
DN_PER_LEVEL = 257.0            # 16-bit DN per 1 step of 8-bit display
RED = 2                          # analyse at 1/2 scale; bands scale with it
BANDS = [(0, 20), (20, 40), (40, 80), (80, 200), (200, 400), (400, 800)]
FARLO, FARHI = 800, 2000


def luma(a):
    return (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2])


def profile(L, plant=None):
    """L is full-res encoded luma. Returns per-band ground medians in DN."""
    s = cv2.resize(L, (L.shape[1] // RED, L.shape[0] // RED),
                   interpolation=cv2.INTER_AREA)
    u8 = np.clip(s / 257.0, 0, 255).astype(np.uint8)
    thr, _ = cv2.threshold(u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    subj = s <= thr * 257.0
    frac = subj.mean()
    if not (0.02 <= frac <= 0.60):
        return None, "subject fraction %.3f outside 0.02-0.60" % frac
    k = np.ones((5, 5), np.uint8)
    sm = cv2.morphologyEx(subj.astype(np.uint8), cv2.MORPH_OPEN, k)
    sm = cv2.morphologyEx(sm, cv2.MORPH_CLOSE, k)
    if sm.sum() < 500:
        return None, "subject too small after cleanup"
    dist = cv2.distanceTransform(1 - sm, cv2.DIST_L2, 5) * RED
    g = s.copy()
    if plant is not None:
        amp, tau = plant
        g = g * (1.0 - amp * np.exp(-dist / float(tau)))
    ground = (sm == 0)
    far = ground & (dist >= FARLO) & (dist < FARHI)
    if far.sum() < 20000:
        return None, "far field only %d px" % far.sum()
    ff = float(np.median(g[far]))
    out = {"far": ff, "farpx": int(far.sum()), "subjfrac": float(frac)}
    for lo, hi in BANDS:
        m = ground & (dist >= lo) & (dist < hi)
        out["%d-%d" % (lo, hi)] = (float(np.median(g[m])), int(m.sum())) \
            if m.sum() >= 5000 else (None, int(m.sum()))
    return out, None


def aura_of(p):
    a = tifffile.imread(p)
    L = luma(a.astype(np.float32))
    del a
    return L


print("=" * 88)
print("COMMISSION on flower-bud-alone-cpl: plant a known aura, read it back")
print("=" * 88)
Lc = aura_of(os.path.join(SHIP, "flower-bud-alone-cpl--SHIP-V4.tiff"))
base, err = profile(Lc)
print("  no plant  : far %.0f DN" % base["far"])
for lo, hi in BANDS:
    v, n = base["%d-%d" % (lo, hi)]
    if v is not None:
        print("      %-8s %8.0f DN   aura %+7.0f DN  (%+6.2f levels)"
              % ("%d-%d" % (lo, hi), v, base["far"] - v,
                 (base["far"] - v) / DN_PER_LEVEL))
print()
for amp in (0.002, 0.01, 0.05):
    pr, e = profile(Lc, plant=(amp, 120.0))
    v, _ = pr["80-200"]
    got = (pr["far"] - v)
    want = amp * pr["far"] * np.exp(-140.0 / 120.0)
    print("  plant %.1f%% tau120 -> 80-200 aura %+7.0f DN   (crude expectation %+.0f)"
          % (100 * amp, got, want))
print()
print("  ARM that CANNOT show an aura: uniform synthetic ground, same mask")
flat = np.full_like(Lc, 60000.0)
flat[Lc <= np.percentile(Lc, 20)] = 5000.0
pr, e = profile(flat)
if pr:
    v, _ = pr["80-200"]
    print("      uniform field -> 80-200 aura %+.1f DN  (must be ~0)"
          % (pr["far"] - v))
else:
    print("      refused:", e)
del Lc, flat

print()
print("=" * 88)
print("ALL 26 SHIPPED MASTERS  (aura = far field minus band, DN; + = darker near subject)")
print("=" * 88)
print("%-36s %7s %8s %8s %8s %8s %8s" %
      ("subject", "far", "0-20", "20-40", "40-80", "80-200", "200-400"))
res = {}
for p in sorted(glob.glob(os.path.join(SHIP, "*--SHIP-V4.tiff"))):
    s = os.path.basename(p).replace("--SHIP-V4.tiff", "")
    L = aura_of(p)
    pr, err = profile(L)
    del L
    if pr is None:
        print("%-36s REFUSED  %s" % (s, err))
        res[s] = {"refused": err}
        continue
    cells = []
    for lo, hi in BANDS[:5]:
        v, n = pr["%d-%d" % (lo, hi)]
        cells.append("%+8.0f" % (pr["far"] - v) if v is not None else "       -")
    print("%-36s %7.0f %s" % (s, pr["far"], " ".join(cells)))
    res[s] = {"far": pr["far"],
              "aura": {k: (pr["far"] - pr[k][0]) if pr[k][0] is not None else None
                       for k in ["%d-%d" % b for b in BANDS]}}
json.dump(res, open(os.path.join(OUT, "aura_ship.json"), "w"), indent=1)
print("\nwrote", os.path.join(OUT, "aura_ship.json"))

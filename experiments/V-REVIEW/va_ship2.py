"""Aura on the shipped masters, with a CONTAMINATION guard.

va_ship.py reported +14751 DN at 80-200 px on tweezers-cpl and -16 DN on
flower-bud-alone-cpl. That spread is not aura. Otsu splits dark subject from
bright ground, but on a subject with extended or mid-tone structure the pixels
just outside the mask ARE subject -- petals, tweezer arms, defocused stems --
and they enter the "ground" median. The same mask defect that once produced a
depression larger than the image it was measured on.

Guard: real ground is smooth, subject is textured. A band whose local texture
exceeds the far field's by more than TEXMULT is contaminated and is REFUSED,
never reported as a small aura or a large one.

SPACE: encoded --srgb, deliberately, because the question is visibility.
No ratios are taken in this space. BAND: purely spatial; no frequency
transform, so the withdrawn >0.30 cyc/px statistic does not apply.
"""
import numpy as np, cv2, os, glob, tifffile, json

SHIP = r"C:\dev\strehl-out\acceptance\SHIP-V4"
OUT = r"C:\dev\strehl-out\V-REVIEW\aura-ship"
os.makedirs(OUT, exist_ok=True)
DN_PER_LEVEL = 257.0
RED = 2
BANDS = [(0, 20), (20, 40), (40, 80), (80, 200), (200, 400)]
FARLO, FARHI = 800, 2000
TEXMULT = 2.0


def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def localsd(s):
    m = cv2.boxFilter(s, -1, (5, 5))
    m2 = cv2.boxFilter(s * s, -1, (5, 5))
    return np.sqrt(np.maximum(m2 - m * m, 0))


def analyse(L, plant=None):
    s = cv2.resize(L, (L.shape[1] // RED, L.shape[0] // RED),
                   interpolation=cv2.INTER_AREA)
    u8 = np.clip(s / 257.0, 0, 255).astype(np.uint8)
    thr, _ = cv2.threshold(u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    subj = s <= thr * 257.0
    frac = float(subj.mean())
    if not (0.02 <= frac <= 0.60):
        return None, "subject fraction %.3f" % frac
    k = np.ones((5, 5), np.uint8)
    sm = cv2.morphologyEx(subj.astype(np.uint8), cv2.MORPH_OPEN, k)
    sm = cv2.morphologyEx(sm, cv2.MORPH_CLOSE, k)
    if sm.sum() < 500:
        return None, "subject too small"
    dist = cv2.distanceTransform(1 - sm, cv2.DIST_L2, 5) * RED
    g = s.astype(np.float32)
    if plant is not None:
        amp, tau = plant
        g = g * (1.0 - amp * np.exp(-dist / float(tau)))
    tex = localsd(g)
    ground = (sm == 0)
    far = ground & (dist >= FARLO) & (dist < FARHI)
    if far.sum() < 20000:
        return None, "far field %d px" % far.sum()
    ff = float(np.median(g[far]))
    ftex = float(np.median(tex[far]))
    out = {"far": ff, "ftex": ftex, "subjfrac": frac, "bands": {}}
    for lo, hi in BANDS:
        m = ground & (dist >= lo) & (dist < hi)
        key = "%d-%d" % (lo, hi)
        if m.sum() < 5000:
            out["bands"][key] = (None, "only %d px" % int(m.sum()))
            continue
        btex = float(np.median(tex[m]))
        if btex > TEXMULT * max(ftex, 1.0):
            out["bands"][key] = (None, "contaminated tex %.0f vs far %.0f"
                                 % (btex, ftex))
            continue
        out["bands"][key] = (ff - float(np.median(g[m])), "ok")
    return out, None


print("=" * 92)
print("COMMISSION THE GUARD -- it must pass smooth aura and refuse subject")
print("=" * 92)
L = luma(tifffile.imread(
    os.path.join(SHIP, "flower-bud-alone-cpl--SHIP-V4.tiff")).astype(np.float32))
base, _ = analyse(L)
print("  far %.0f DN   far-texture %.0f DN" % (base["far"], base["ftex"]))
for amp in (0.0, 0.002, 0.01, 0.05):
    pr, _ = analyse(L, plant=(amp, 120.0) if amp else None)
    v, why = pr["bands"]["80-200"]
    print("  plant %-5s 80-200 -> %s  (%s)"
          % ("%.1f%%" % (100 * amp),
             ("%+7.0f DN = %+5.2f levels" % (v, v / DN_PER_LEVEL))
             if v is not None else "REFUSED", why))
print("  ^ the guard must NOT refuse a smooth planted aura")
print()
Lt = luma(tifffile.imread(
    os.path.join(SHIP, "tweezers-cpl--SHIP-V4.tiff")).astype(np.float32))
pt, _ = analyse(Lt)
print("  tweezers-cpl (known contaminated):")
for b in ["80-200", "200-400"]:
    v, why = pt["bands"][b]
    print("     %-8s %s  (%s)" % (b, "%+7.0f DN" % v if v is not None
                                  else "REFUSED", why))
del Lt, L

print()
print("=" * 92)
print("ALL 26 MASTERS, GUARDED. aura = far minus band. + = darker near subject")
print("=" * 92)
print("%-36s %7s %9s %9s %9s" % ("subject", "far", "40-80", "80-200", "200-400"))
res, n_meas, n_ref = {}, 0, 0
for p in sorted(glob.glob(os.path.join(SHIP, "*--SHIP-V4.tiff"))):
    s = os.path.basename(p).replace("--SHIP-V4.tiff", "")
    L = luma(tifffile.imread(p).astype(np.float32))
    pr, err = analyse(L)
    del L
    if pr is None:
        print("%-36s REFUSED (%s)" % (s, err)); res[s] = {"refused": err}
        n_ref += 1; continue
    cells = []
    any_ok = False
    for b in ["40-80", "80-200", "200-400"]:
        v, why = pr["bands"][b]
        if v is None:
            cells.append("  REFUSED")
        else:
            cells.append("%+9.0f" % v); any_ok = True
    print("%-36s %7.0f %s" % (s, pr["far"], " ".join(cells)))
    res[s] = {"far": pr["far"],
              "bands": {b: pr["bands"][b][0] for b in pr["bands"]}}
    n_meas += 1 if any_ok else 0
    n_ref += 0 if any_ok else 1
print()
print("partition: %d measured + %d refused = %d" % (n_meas, n_ref, n_meas + n_ref))
json.dump(res, open(os.path.join(OUT, "aura_guarded.json"), "w"), indent=1)

print()
print("=" * 92)
print("VISIBILITY: 1 display level = %.0f DN. Threshold for a smooth gradient")
print("in a flat bright field is about 1 level; 2 levels is unambiguous.")
print("=" * 92)
ok = [(s, d["bands"]["80-200"]) for s, d in res.items()
      if "bands" in d and d["bands"].get("80-200") is not None]
for s, v in sorted(ok, key=lambda t: -abs(t[1])):
    print("  %-36s %+8.0f DN = %+6.2f levels   %s"
          % (s, v, v / DN_PER_LEVEL,
             "VISIBLE" if abs(v) / DN_PER_LEVEL >= 2 else
             "borderline" if abs(v) / DN_PER_LEVEL >= 1 else "below threshold"))

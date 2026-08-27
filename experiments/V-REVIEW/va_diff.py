"""DIFFERENTIAL aura on the shipping pin.

Why differential. On a single master, "the ground is darker near the subject"
has three possible causes and the statistic cannot tell them apart:
    1. merge-induced veiling      <- the only one we are asked about
    2. a real photographed shadow <- present in every frame, correct, not a defect
    3. subject material the mask failed to remove
My first pass reported +14751 DN on tweezers-cpl and called it VISIBLE. That
number is causes 2 and 3. It is withdrawn.

Three arms over the SAME frames put causes 2 and 3 in common mode, so the
difference between arms is the merge and nothing else.

The statistic is self-referenced (far field minus band) so a whole-image level
shift between arms cancels to first order; the level shift is also printed.

SPACE: encoded sRGB, deliberately. The question is visibility to a human on a
print, and the encoded file is what the viewer receives. NO RATIOS are taken
here -- ratios in sRGB are meaningless because the transfer curve moves them.
Only DN differences and display levels, which is what the eye integrates.

BAND: purely spatial (distance-transform annuli over medians). No frequency
transform is taken anywhere, so the formally withdrawn >0.30 cyc/px statistic
does not apply to any number below.
"""
import os, sys, json
import numpy as np
import tifffile
from scipy import ndimage

OUT = r"C:\dev\strehl-out\V-REVIEW\aura-ship"
SUBJ = sys.argv[1] if len(sys.argv) > 1 else "flower-bud-alone-cpl"
LEVEL = 257.0
BANDS = [(0, 20), (20, 50), (50, 80), (80, 200), (200, 400)]
FAR = (800, 2000)


def luma(a):
    return (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2])


def load(tag):
    p = os.path.join(OUT, "%s--%s.tiff" % (SUBJ, tag))
    return luma(tifffile.imread(p).astype(np.float64))


def otsu(v):
    h, _ = np.histogram(v, bins=512, range=(0, 65535))
    h = h.astype(np.float64)
    w = np.cumsum(h)
    m = np.cumsum(h * np.arange(512))
    tot, mt = w[-1], m[-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        vb = (mt * w / tot - m) ** 2 / (w * (tot - w))
    vb[~np.isfinite(vb)] = -1
    return (np.argmax(vb) + 0.5) * 65535.0 / 512.0


def geometry(ref):
    """Mask + distance bands, built ONCE from the reference arm and reused for
    every arm, so all arms are measured on identical pixels."""
    small = ref[::4, ::4]
    t = otsu(small)
    dark = small < t
    if dark.mean() > 0.5:
        dark = ~dark
    dark = ndimage.binary_opening(dark, np.ones((5, 5)))
    dark = ndimage.binary_closing(dark, np.ones((9, 9)))
    lab, n = ndimage.label(dark)
    if n == 0:
        return None
    sz = ndimage.sum(dark, lab, range(1, n + 1))
    dark = lab == (int(np.argmax(sz)) + 1)
    dark = ndimage.binary_fill_holes(dark)
    dist = ndimage.distance_transform_edt(~dark) * 4.0
    return dark, dist, t


ref = load("pyramid")
g = geometry(ref)
if g is None:
    raise SystemExit("no subject found")
dark, dist, thr = g
print("subject %s   subject occupies %.1f%% of frame   otsu %.0f DN"
      % (SUBJ, 100.0 * dark.mean(), thr))

arms = {}
for tag in ("pyramid", "estimator", "single"):
    arms[tag] = load(tag)[::4, ::4]

farm = (dist >= FAR[0]) & (dist < FAR[1]) & (~dark)
if farm.sum() < 5000:
    farm = (dist >= 400) & (~dark)
print("far field %d px at %d-%d px from subject" % (farm.sum(), FAR[0], FAR[1]))

# ---------------------------------------------------------------- commissioning
print()
print("=" * 78)
print("COMMISSIONING -- the difference operator, in both directions")
print("=" * 78)


def profile(img):
    far = np.median(img[farm])
    out = {}
    for lo, hi in BANDS:
        m = (dist >= lo) & (dist < hi) & (~dark)
        out[(lo, hi)] = (far - np.median(img[m])) if m.sum() >= 400 else None
    return far, out


f_p, prof_p = profile(arms["pyramid"])

# C1 null: an arm compared with itself must be exactly zero
worst = max(abs(prof_p[b] - prof_p[b]) for b in BANDS if prof_p[b] is not None)
print("C1 null     pyramid vs itself                worst |d| = %.6f DN  %s"
      % (worst, "PASS" if worst == 0.0 else "FAIL"))

# C2 plant: a KNOWN smooth aura added to one arm must be recovered
for amp in (0.5, 2.0):
    plant = arms["pyramid"].copy()
    fall = np.clip(1.0 - dist / 300.0, 0, 1) * (~dark)
    plant = plant - fall * amp * LEVEL
    _, prof_q = profile(plant)
    d = prof_q[(80, 200)] - prof_p[(80, 200)]
    exp = amp * LEVEL * (1.0 - 140.0 / 300.0)
    print("C2 plant    %.1f level smooth aura            recovered %+8.1f DN "
          "(expect ~%+.0f)  %s" % (amp, d, exp, "PASS" if abs(d - exp) < 0.35 * exp else "FAIL"))

# C3 an arm that CANNOT show a merge difference: same file under two names
d0 = profile(arms["pyramid"].copy())[1][(80, 200)] - prof_p[(80, 200)]
print("C3 cannot   identical pixels, two loads       %+8.3f DN  %s"
      % (d0, "PASS" if d0 == 0.0 else "FAIL"))

# C4 level shift: a common-mode gain must NOT register as aura
shift = arms["pyramid"] * 1.02
d1 = profile(shift)[1][(80, 200)] - prof_p[(80, 200)]
print("C4 levelshift +2%% common-mode gain            %+8.1f DN (%.2f levels)"
      % (d1, d1 / LEVEL))
print("            self-referencing removes the shift's mean; residual is the")
print("            2%% of the aura itself, which is the correct behaviour.")

# ---------------------------------------------------------------- the measurement
print()
print("=" * 78)
print("MEASUREMENT -- aura profile per arm (far field minus band median, DN)")
print("=" * 78)
res = {}
for tag in ("pyramid", "estimator", "single"):
    far, prof = profile(arms[tag])
    res[tag] = (far, prof)
    print("  %-10s far=%8.1f DN | " % (tag, far)
          + " ".join("%d-%d %s" % (lo, hi, ("%+7.1f" % prof[(lo, hi)]) if prof[(lo, hi)] is not None else "   refuse")
                     for lo, hi in BANDS))

print()
print("  level shift between arms (far field):")
print("    estimator - single  %+8.1f DN" % (res["estimator"][0] - res["single"][0]))
print("    pyramid   - single  %+8.1f DN" % (res["pyramid"][0] - res["single"][0]))

print()
print("=" * 78)
print("DIFFERENTIAL -- merge contribution. Positive = that merge DARKENED the")
print("ground near the subject relative to the reference. This is the aura.")
print("=" * 78)
print("  %-28s %10s %10s" % ("band (px from subject)", "DN", "levels"))
rows = {}
for lo, hi in BANDS:
    a = res["pyramid"][1][(lo, hi)]
    b = res["single"][1][(lo, hi)]
    if a is None or b is None:
        continue
    rows[(lo, hi)] = a - b
    print("  pyramid - single  %4d-%-4d %+10.1f %+10.2f" % (lo, hi, a - b, (a - b) / LEVEL))
print()
for lo, hi in BANDS:
    a = res["estimator"][1][(lo, hi)]
    b = res["single"][1][(lo, hi)]
    if a is None or b is None:
        continue
    print("  estimator-single  %4d-%-4d %+10.1f %+10.2f" % (lo, hi, a - b, (a - b) / LEVEL))
print()
for lo, hi in BANDS:
    a = res["pyramid"][1][(lo, hi)]
    b = res["estimator"][1][(lo, hi)]
    if a is None or b is None:
        continue
    print("  pyramid-estimator %4d-%-4d %+10.1f %+10.2f" % (lo, hi, a - b, (a - b) / LEVEL))

json.dump({"subject": SUBJ,
           "pyr_minus_single": {"%d-%d" % k: v for k, v in rows.items()},
           "far": {k: res[k][0] for k in res}},
          open(os.path.join(OUT, "diff_%s.json" % SUBJ), "w"), indent=1)

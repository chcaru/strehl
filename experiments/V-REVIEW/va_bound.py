"""Why the single-frame reference is invalid, and the UPPER-BOUND sweep.

PART 1 tests the mechanism I claim: a single frame carries a large dark skirt
around the subject because the subject is DEFOCUSED in that frame and its dark
edge spreads. Prediction: the skirt should shrink monotonically as more frames
are merged, because merging restores a sharp edge. If it does not, my
explanation is wrong and the differential stands as originally computed.

PART 2 measures the SHIPPING masters (which I proved byte-identical to a
pyramid render on 9b05d0b7) against their own far field. That statistic is
CONFOUNDED upward by shadow and by unmasked subject, so it is not an aura
measurement -- it is an UPPER BOUND on one. A small bound is still decisive:
if the total darkening near the subject is under a display level, then the
aura contained inside it is too.
"""
import os, sys, json, subprocess
import numpy as np
import tifffile
from scipy import ndimage
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW")
import vr_lib as V

ACC = r"C:\dev\strehl-out\acceptance\SHIP-V4"
OUT = r"C:\dev\strehl-out\V-REVIEW\aura-ship"
LEVEL = 257.0
BANDS = [(20, 50), (50, 80), (80, 200), (200, 400)]
seal, n = V.corpus_seal(ACC, "SHIP-V4")
EXE, PIN = V.pin_for(seal)


def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def otsu(v):
    h, _ = np.histogram(v, bins=512, range=(0, 65535))
    h = h.astype(np.float64); w = np.cumsum(h); m = np.cumsum(h * np.arange(512))
    tot, mt = w[-1], m[-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        vb = (mt * w / tot - m) ** 2 / (w * (tot - w))
    vb[~np.isfinite(vb)] = -1
    return (np.argmax(vb) + 0.5) * 65535.0 / 512.0


def geom(small):
    t = otsu(small); dark = small < t
    if dark.mean() > 0.5: dark = ~dark
    dark = ndimage.binary_opening(dark, np.ones((5, 5)))
    dark = ndimage.binary_closing(dark, np.ones((9, 9)))
    lab, k = ndimage.label(dark)
    if k == 0: return None
    sz = ndimage.sum(dark, lab, range(1, k + 1))
    dark = ndimage.binary_fill_holes(lab == (int(np.argmax(sz)) + 1))
    if dark.mean() < 0.002 or dark.mean() > 0.75: return None
    return dark, ndimage.distance_transform_edt(~dark) * 4.0


def prof(small, dark, dist):
    far = (dist >= 800) & (dist < 2000) & (~dark)
    if far.sum() < 5000: far = (dist >= 400) & (~dark)
    if far.sum() < 5000: return None, None
    f = np.median(small[far]); out = {}
    for lo, hi in BANDS:
        m = (dist >= lo) & (dist < hi) & (~dark)
        out[(lo, hi)] = float(f - np.median(small[m])) if m.sum() >= 400 else None
    return f, out


# ------------------------------------------------------------------- PART 1
print("=" * 78)
print("PART 1  MECHANISM: is the single-frame skirt defocus bleed?")
print("=" * 78)
print("prediction: skirt shrinks monotonically as frame count rises")
SUBJ = "flower-bud-alone-cpl"
env = {k: v for k, v in os.environ.items() if not k.startswith("STREHL_")}
ref = luma(tifffile.imread(os.path.join(OUT, "%s--pyramid.tiff" % SUBJ)).astype(np.float64))[::4, ::4]
gg = geom(ref); dark, dist = gg
seq = []
for nf in (1, 5, 25, 205):
    p = os.path.join(OUT, "%s--n%d.tiff" % (SUBJ, nf))
    if nf == 205:
        p = os.path.join(OUT, "%s--pyramid.tiff" % SUBJ)
    elif nf == 1:
        p = os.path.join(OUT, "%s--single.tiff" % SUBJ)
    elif not os.path.exists(p):
        cmd = [EXE, "stack", os.path.join(r"D:\personal\macro", SUBJ), "--out", p,
               "--srgb", "--exposure=1.44", "--limit", str(nf)]
        r = subprocess.run(cmd, env=env, capture_output=True, timeout=3600)
        if r.returncode != 0:
            print(r.stderr.decode("utf-8", "replace")[-800:]); raise SystemExit(1)
        open(p + ".ok", "w").write(V._sha256(EXE))
        open(p + ".provenance.txt", "w").write(
            "binary %s\npin %s\nsha256 %s\nargv %s\nSTREHL_* cleared\n"
            % (EXE, PIN, V._sha256(EXE), " ".join(cmd)))
    a = luma(tifffile.imread(p).astype(np.float64))[::4, ::4]
    f, pr = prof(a, dark, dist)
    seq.append((nf, pr[(80, 200)]))
    print("  frames %3d   skirt at 80-200 px = %+9.1f DN (%+6.2f levels)"
          % (nf, pr[(80, 200)], pr[(80, 200)] / LEVEL))
mono = all(seq[i][1] > seq[i + 1][1] for i in range(len(seq) - 1))
print("  monotonically shrinking: %s -> %s" % (mono,
      "MECHANISM CONFIRMED. --limit 1 is NOT a zero-aura reference; it carries\n"
      "  the largest subject bleed of any arm. The pyramid-minus-single\n"
      "  differential is WITHDRAWN." if mono else "mechanism NOT confirmed"))

# ------------------------------------------------------------------- PART 2
print()
print("=" * 78)
print("PART 2  UPPER BOUND on aura, all 26 shipping masters")
print("=" * 78)
print("bound = far-field median minus band median, in display levels.")
print("It includes shadow and unmasked subject, so it OVERSTATES the aura.")
print()
print("  %-38s %8s %8s %8s %8s" % ("subject", "20-50", "50-80", "80-200", "200-400"))
files = sorted(f for f in os.listdir(ACC) if f.endswith("--SHIP-V4.tiff"))
res, refused = {}, []
for fn in files:
    sub = fn.replace("--SHIP-V4.tiff", "")
    a = luma(tifffile.imread(os.path.join(ACC, fn)).astype(np.float64))[::4, ::4]
    g = geom(a)
    if g is None:
        refused.append((sub, "no usable subject/ground split")); continue
    d, dt = g
    f, pr = prof(a, d, dt)
    if f is None:
        refused.append((sub, "no far field")); continue
    res[sub] = pr
    print("  %-38s %8s %8s %8s %8s" % (sub,
          *[("%+.2f" % (pr[b] / LEVEL)) if pr[b] is not None else "refuse" for b in BANDS]))
print()
for s, why in refused:
    print("  %-38s REFUSED: %s" % (s, why))
print()
print("  partition: %d measured + %d refused = %d  (files %d)"
      % (len(res), len(refused), len(res) + len(refused), len(files)))
json.dump({k: {"%d-%d" % b: v[b] for b in BANDS} for k, v in res.items()},
          open(os.path.join(OUT, "bound.json"), "w"), indent=1)

"""The one candidate positive: 112MSDCF / 113MSDCF read darker near the subject
than their own sham null (z +2.3, +2.1 at 80-200). Two sibling captures reading
the same way is worth a real test rather than a p-value, so: render the
estimator arm and difference it. If the SHIPPING pyramid is the darker of the
two arms here, that is a genuine pyramid aura and the verdict changes. If the
pyramid is the cleaner arm, the reading is scene structure that the sham null
cannot model, and the fat tails already say it cannot (this null reaches z -23,
so +2.3 is not a detection on its own).
"""
import os, re, sys, json, subprocess
import numpy as np, tifffile
from scipy import ndimage
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW")
import vr_lib as V

ACC = r"C:\dev\strehl-out\acceptance\SHIP-V4"
OUT = r"C:\dev\strehl-out\V-REVIEW\aura-ship"
LEVEL = 257.0
seal, _ = V.corpus_seal(ACC, "SHIP-V4")
EXE, PIN = V.pin_for(seal)
env = {k: v for k, v in os.environ.items() if not k.startswith("STREHL_")}


def luma(a): return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def otsu(v):
    h, _ = np.histogram(v, bins=512, range=(0, 65535)); h = h.astype(np.float64)
    w = np.cumsum(h); m = np.cumsum(h * np.arange(512)); tot, mt = w[-1], m[-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        vb = (mt * w / tot - m) ** 2 / (w * (tot - w))
    vb[~np.isfinite(vb)] = -1
    return (np.argmax(vb) + 0.5) * 65535.0 / 512.0


for SUB in ("112MSDCF", "113MSDCF"):
    t = open(os.path.join(ACC, "%s--SHIP-V4.tiff.provenance.txt" % SUB)).read()
    ex = re.search(r"--exposure[= ]\+?(-?[\d.]+)", t).group(1)
    p = os.path.join(OUT, "%s--estimator.tiff" % SUB)
    if not os.path.exists(p):
        cmd = [EXE, "stack", os.path.join(r"D:\personal\macro", SUB), "--out", p,
               "--srgb", "--exposure=%s" % ex, "--merge", "estimator"]
        print("  rendering %s estimator (exposure %s)" % (SUB, ex), flush=True)
        r = subprocess.run(cmd, env=env, capture_output=True, timeout=7200)
        if r.returncode != 0:
            print(r.stderr.decode("utf-8", "replace")[-1200:]); raise SystemExit(1)
        open(p + ".ok", "w").write(V._sha256(EXE))
        open(p + ".provenance.txt", "w").write(
            "binary %s\npin %s\nsha256 %s\ncorpus-seal %s\nargv %s\nSTREHL_* cleared\n"
            % (EXE, PIN, V._sha256(EXE), seal, " ".join(cmd)))
    A = luma(tifffile.imread(os.path.join(ACC, "%s--SHIP-V4.tiff" % SUB)).astype(np.float64))[::2, ::2]
    B = luma(tifffile.imread(p).astype(np.float64))[::2, ::2]
    th = otsu(A); d = A < th
    if d.mean() > 0.5: d = ~d
    d = ndimage.binary_closing(ndimage.binary_opening(d, np.ones((5, 5))), np.ones((9, 9)))
    lab, k = ndimage.label(d); sz = ndimage.sum(d, lab, range(1, k + 1))
    d = ndimage.binary_fill_holes(lab == (int(np.argmax(sz)) + 1))
    dt = ndimage.distance_transform_edt(~d) * 2.0
    fm = (dt >= 800) & (dt < 2000) & (~d)
    if fm.sum() < 5000: fm = (dt >= 400) & (~d)
    fa, fb = np.median(A[fm]), np.median(B[fm])
    print("=" * 78)
    print("%s  subject %.1f%% of frame   POSITIVE = brighter than own far field"
          % (SUB, 100 * d.mean()))
    print("=" * 78)
    print("  %10s %8s %11s %11s %11s" % ("px", "n", "pyramid", "estimator", "pyr-est"))
    worst = None
    for lo, hi in [(0, 20), (20, 50), (50, 80), (80, 200), (200, 400), (400, 800)]:
        m = (dt >= lo) & (dt < hi) & (~d)
        if m.sum() < 400: continue
        pa = (np.median(A[m]) - fa) / LEVEL
        pb = (np.median(B[m]) - fb) / LEVEL
        print("  %4d-%-5d %8d %+11.2f %+11.2f %+11.2f" % (lo, hi, m.sum(), pa, pb, pa - pb))
        if lo >= 20 and (worst is None or (pa - pb) < worst[1]):
            worst = ((lo, hi), pa - pb)
    v = "PYRAMID IS THE DARKER ARM -- genuine pyramid aura" if worst[1] < -1.0 \
        else "PYRAMID IS THE CLEANER ARM -- the sham-null positive is scene, not aura"
    print("  worst band for pyramid beyond 20 px: %s at %+.2f levels" % (worst[0], worst[1]))
    print("  --> %s" % v)
    print()

"""Is the hull clamp the cause of the exact-zero pixels, or the mitigation?

ORCH measured 723,429 blue pixels at exactly 0 (2.192%) in the pyramid arm and
proposed that the reconstruction clamps the accumulated sum. Reading the code
refutes that specific mechanism -- pyramid.rs applies the clamp exactly once,
after collapse() -- but leaves the question of whether the clamp is causing the
zeros at all.

This renders the same stack twice through the same binary, differing only in
Hull::InputRange vs Hull::Unclamped, and counts exact zeros in each.

  clamped >> unclamped  -> the clamp pins pixels to a hull floor that is itself
                           ~0, i.e. the hull is vacuous where depth varies.
  clamped << unclamped  -> the clamp is the mitigation and the undershoot is the
                           real defect; removing the clamp makes it worse.

Both readings are actionable and they prescribe opposite fixes, which is why
this has to be measured before anything is changed.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile

D = Path(r"C:\dev\strehl-out\BUILD-BLEND\clip")
ARMS = [("clamped", D / "fb-clamped.tiff"), ("unclamped", D / "fb-unclamped.tiff")]

imgs = {}
for name, p in ARMS:
    if not p.exists():
        sys.exit(f"missing {p}")
    imgs[name] = tifffile.imread(p)

shapes = {n: a.shape for n, a in imgs.items()}
if len(set(shapes.values())) != 1:
    sys.exit(f"canvases differ, not comparable: {shapes}")
h, w, _ = imgs["clamped"].shape
total = h * w
print(f"canvas {w} x {h} = {total:,} px per channel\n")

print(f"{'arm':<12}{'ch':<4}{'== 0':>12}{'pct':>9}{'<=16':>12}{'<=256':>12}")
print("-" * 61)
zeros = {}
for name, _ in ARMS:
    a = imgs[name]
    for ci, cn in enumerate("RGB"):
        ch = a[:, :, ci]
        z = int((ch == 0).sum())
        zeros[(name, cn)] = z
        print(f"{name:<12}{cn:<4}{z:>12,}{100*z/total:>8.3f}%"
              f"{int((ch <= 16).sum()):>12,}{int((ch <= 256).sum()):>12,}")
    print()

print("=" * 61)
print("VERDICT")
print("=" * 61)
for cn in "RGB":
    c, u = zeros[("clamped", cn)], zeros[("unclamped", cn)]
    if c == 0 and u == 0:
        verdict = "no zeros in either arm"
    elif c > u * 1.5:
        verdict = "the CLAMP pins them -- hull floor is itself ~0"
    elif u > c * 1.5:
        verdict = "the clamp MITIGATES -- undershoot is the real defect"
    else:
        verdict = "clamp is not the discriminator; both arms agree"
    print(f"  {cn}: clamped {c:>10,}   unclamped {u:>10,}   {verdict}")

# Where the clamped arm reads 0, what does the unclamped arm read there?
# This is the quantity that says how far the reconstruction actually undershot.
print()
print("=" * 61)
print("HOW FAR DID THE RECONSTRUCTION UNDERSHOOT?")
print("  At pixels the clamped arm pins to 0, the unclamped arm's value is the")
print("  reconstruction's own opinion. TIFF is unsigned, so a true negative")
print("  wraps or saturates -- a large count at 0 in the unclamped arm means")
print("  the undershoot went below the container floor, not that it was small.")
print("=" * 61)
for cn, ci in zip("RGB", range(3)):
    m = imgs["clamped"][:, :, ci] == 0
    if not m.any():
        print(f"  {cn}: no pinned pixels")
        continue
    u = imgs["unclamped"][:, :, ci][m]
    print(f"  {cn}: {m.sum():>10,} pinned   unclamped there: "
          f"median {np.median(u):>8.0f}  mean {u.mean():>8.0f}  "
          f"max {u.max():>7.0f}  frac still 0: {100*(u==0).mean():5.1f}%")

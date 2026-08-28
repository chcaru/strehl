"""Clipping audit of every master this lane measured.

ORCH's exposure regression blows highlights at HEAD under `--srgb --auto-exposure`.
The command line is only indirect evidence; the image is the evidence. This reads
the DECODED array of every master V-DILUTE reported a number from and states the
clipped fraction and median, so "no --auto-exposure in my scripts" is backed by
"and no master is clipped".

It also self-checks one of my own findings. I attributed the exponent 12/16
collapse (detail 0.698 / 0.543, max |delta| 41711) to f32 weight saturation above
p~10, per pyramid.rs's own comment. ORCH notes clipping manufactures overshoot
and pins pixels at the hull -- so if those arms are clipped, my attribution is
confounded and the detail collapse could be saturation of the OUTPUT rather than
of the weights. High exponents overshoot, so this is a live risk in exactly those
two arms and nowhere else.
"""
import glob
import os
import numpy as np
import tifffile

R = r"C:\dev\strehl-out\V-DILUTE\runs"
MAXV = 65535

rows = []
for p in sorted(glob.glob(os.path.join(R, "*.tif"))):
    name = os.path.basename(p)
    if name.endswith("_conf.tif") or name.startswith("_probe") or name.startswith("ROI_index"):
        continue                      # instrument artefacts, not masters
    a = tifffile.imread(p)
    clipped = 100.0 * float((a >= MAXV).mean())
    rows.append((name, clipped, int(np.median(a)), int(a.max())))

print(f"{'master':<28} {'% clipped':>10} {'median':>8} {'max':>7}  verdict")
worst = 0.0
for name, c, med, mx in rows:
    worst = max(worst, c)
    v = "BLOWN" if c > 25 else ("watch" if c > 1.0 else "clean")
    print(f"{name:<28} {c:>10.4f} {med:>8d} {mx:>7d}  {v}")
print(f"\n{len(rows)} masters, worst clipped fraction {worst:.4f}%")
print("ORCH's BLOWN threshold is >25%; his worst was couch-fibers-cpl at 92.13%.")

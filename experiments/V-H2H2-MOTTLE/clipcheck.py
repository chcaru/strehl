"""Measure clipping on the exact masters V-H2H2's concentration arms produced.

ORCH's exposure regression blows highlights only when `--auto-exposure` is
passed. This lane's arms passed neither `--srgb` nor `--auto-exposure`, so the
prediction is 0.00% clipped in all three arms. Predicting it is not measuring
it, so this reads the pixels.
"""

import glob
import os
import sys

import numpy as np
import tifffile

pat = os.path.join(os.environ["TEMP"], "vh2h2-sig", "conc-*.tif")
paths = sorted(glob.glob(pat))
if not paths:
    print(f"NO MASTERS FOUND at {pat}")
    sys.exit(2)

print(f"{'master':<16}{'dtype':<10}{'max':>8}{'median':>10}{'clip%':>10}")
worst = 0.0
for p in paths:
    a = tifffile.imread(p)
    top = 65535 if a.dtype == np.uint16 else a.max()
    clip = float((a >= top).mean() * 100.0)
    worst = max(worst, clip)
    print(
        f"{os.path.basename(p):<16}{str(a.dtype):<10}{int(a.max()):>8}"
        f"{int(np.median(a)):>10}{clip:>10.4f}"
    )

print()
print(f"worst clip across arms: {worst:.4f}%   (ORCH's BLOWN threshold is 25%)")
print("VERDICT:", "CLEAN -- case 3" if worst < 25.0 else "BLOWN -- case 2")

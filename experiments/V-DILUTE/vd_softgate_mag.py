"""Magnitude of the arm differences in the soft-gate reachability test.

A hash says "differs". It does not say "differs enough to matter", and this
project has already been burned by reading a hash as a verdict. Report the
actual pixel deltas.
"""
import io
import sys

import numpy as np
import tifffile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

D = r"D:\strehl-out\V-DILUTE\softgate"
arms = {k: tifffile.imread(rf"{D}\{k}.tiff").astype(np.float64) for k in "A Ap B C D E".split()}


def cmp(a, b, label):
    x, y = arms[a], arms[b]
    d = np.abs(x - y)
    n = int((d > 0).sum())
    frac = n / d.size
    denom = max(float(x.mean()), 1e-9)
    print(
        f"  {label:<26} {a} vs {b}:  differing samples {n:>12,} / {d.size:,} "
        f"({100*frac:6.3f}%)   max |d| {d.max():8.1f} DN   mean |d| {d.mean():8.4f} DN"
        f"   RMS/mean {np.sqrt((d**2).mean())/denom*100:7.4f}%"
    )


print("SOFT-GATE REACHABILITY -- magnitude of each arm difference")
print(f"  image {arms['A'].shape}, dtype uint16 source, mean level {arms['A'].mean():.1f} DN\n")
cmp("A", "Ap", "determinism control")
cmp("A", "B", "THE CLAIM (pyramid+gate)")
cmp("A", "C", "sensitivity (exponent)")
cmp("D", "E", "specificity (estim+gate)")
cmp("A", "D", "backend difference")

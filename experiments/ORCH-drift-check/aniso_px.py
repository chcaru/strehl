"""Convert the gate-ladder anisotropy into a residual displacement in px.

The gate effect is reported at fixed radius on a fixed tile set, so the SUBJECT
is identical between arms and cancels; only the treatment differs. That makes the
between-gate differences the trustworthy part of anisotropy.py's output. This
script turns them into a physical number by inverting the planted dose curve at
the SAME radius, rather than at the r>0.6 pooled "outer" band the controls
printed -- the outer band has angular clustering 0.42-0.62 on this subject, so
its absolute calibration is contaminated even though its deltas are not.

Only annuli whose angular clustering is low enough that the subject cannot be
impersonating a radial defect are used.
"""
import json

import numpy as np

CLUST_MAX = 0.30   # above this, tiles cluster in angle and the subject leaks in
RADII = (0.35, 0.45, 0.55)

ctrl = json.load(open("anisotropy-controls.json"))
gates = json.load(open("anisotropy.json"))

DOSES = {"identity": 0.0, "radial 1px@corner": 1.0,
         "radial 3px@corner": 3.0, "radial 10px@corner": 10.0}


def at(meas, r):
    for a in meas["annuli"]:
        if abs(a["r_mid"] - r) < 1e-6:
            return a
    return None


print(f"{'radius':>7} {'clust':>6} | {'dose->A curve at this radius'}")
curves = {}
for r in RADII:
    pts = []
    for name, dose in DOSES.items():
        a = at(ctrl[name], r)
        if a is None:
            continue
        pts.append((dose, a["A"]))
    pts.sort()
    clust = at(ctrl["identity"], r)["angular_clustering"]
    curves[r] = pts
    s = "  ".join(f"{d:g}px:{v:.4f}" for d, v in pts)
    flag = "" if clust <= CLUST_MAX else "  <-- SUBJECT-CONTAMINATED, excluded"
    print(f"{r:>7.2f} {clust:>6.3f} | {s}{flag}")

print()
print("The planted dose is defined AT THE CORNER. A scale error displaces in")
print("proportion to radius, so a dose of L px at the corner is L*r px at")
print("normalised radius r. Reported below in px AT THE CORNER for comparability.")
print()


def invert(pts, a_val):
    """Piecewise-linear inverse of the (monotone decreasing) dose->A curve."""
    d = [p[0] for p in pts]
    v = [p[1] for p in pts]
    if a_val >= v[0]:
        return 0.0
    if a_val <= v[-1]:
        return float("inf")
    for i in range(len(v) - 1):
        if v[i] >= a_val >= v[i + 1]:
            t = (v[i] - a_val) / (v[i] - v[i + 1])
            return d[i] + t * (d[i + 1] - d[i])
    return float("nan")


print(f"{'file':<22} " + " ".join(f"{f'r={r:.2f}':>12}" for r in RADII))
rows = {}
for g in gates:
    lbl = g["label"].replace("bee-3-cpl-", "").replace(".tif", "")
    cells, vals = [], {}
    for r in RADII:
        a = at(g, r)
        clust = at(ctrl["identity"], r)["angular_clustering"]
        if a is None or clust > CLUST_MAX:
            cells.append(f"{'--':>12}")
            continue
        px = invert(curves[r], a["A"])
        vals[r] = px
        cells.append(f"{px:>9.2f} px")
    rows[lbl] = vals
    print(f"{lbl:<22} " + " ".join(cells))

print()
print("These are UPPER BOUNDS on residual radial displacement, not estimates:")
print("any subject anisotropy still present at these radii inflates them, and")
print("the identity render's own reading is folded into every row. The")
print("difference between rows is the defensible quantity.")
print()
base = rows.get("g0", {})
for lbl, vals in rows.items():
    if lbl == "g0":
        continue
    d = [f"r={r:.2f}: +{vals[r] - base[r]:.2f} px" for r in RADII
         if r in vals and r in base]
    print(f"  {lbl} vs g0 -> " + ",  ".join(d))

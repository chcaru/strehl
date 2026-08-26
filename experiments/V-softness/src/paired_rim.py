"""Paired aura profile: ONE geometry, two arms.

rimprofile.py recomputes its subject mask from each image it is handed, so an
A/B through it is not strictly paired -- a treatment that moves the silhouette
threshold moves the distance bins too, and the DN columns are then read at
different places. This reads both arms through the SAME mask and the SAME
signed-distance field, taken from the reference arm.

Reports ABSOLUTE median DN per bin for each arm, per ORCH's standing rule.
"""
import sys, numpy as np, tifffile
from scipy import ndimage

ref_path, test_path = sys.argv[1], sys.argv[2]
label_a = sys.argv[3] if len(sys.argv) > 3 else "A"
label_b = sys.argv[4] if len(sys.argv) > 4 else "B"

def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p}: expected uint16, got {a.dtype}"
    return a.astype(np.float32).mean(axis=2)

la, lb = load(ref_path), load(test_path)
assert la.shape == lb.shape, (la.shape, lb.shape)
print(f"paired on {la.shape}, geometry from {label_a}")

lo, hi = np.percentile(la, [5, 95])
subject = la < 0.5 * (lo + hi)
lab, n = ndimage.label(subject)
if n > 1:
    sizes = ndimage.sum(subject, lab, range(1, n + 1))
    subject = lab == (1 + int(np.argmax(sizes)))
print(f"subject fraction {subject.mean()*100:.2f}% (from {label_a}, applied to BOTH)")

signed = ndimage.distance_transform_edt(~subject) - ndimage.distance_transform_edt(subject)
far = (signed > 600) & (signed < 1400)
ra, rb = float(np.median(la[far])), float(np.median(lb[far]))
print(f"far-field 600-1400 px: {label_a} {ra:.0f} DN   {label_b} {rb:.0f} DN   "
      f"pedestal {label_b}-{label_a} {rb-ra:+.0f} DN over {far.sum()} px")
print()

edges = [0, 4, 8, 12, 16, 20, 25, 30, 40, 50, 65, 80, 100, 125, 150,
         200, 250, 300, 400, 500, 600]
print(f"  d (px)     {label_a:>9}  {label_b:>9}   {label_b}-{label_a}   "
      f"pedestal-corrected")
ds, va, vb = [], [], []
for i in range(len(edges) - 1):
    m = (signed >= edges[i]) & (signed < edges[i + 1])
    if m.sum() < 500: continue
    a_, b_ = float(np.median(la[m])), float(np.median(lb[m]))
    ds.append(0.5*(edges[i]+edges[i+1])); va.append(a_); vb.append(b_)
    print(f"  {edges[i]:4d}-{edges[i+1]:<4d} {a_:10.0f} {b_:10.0f} {b_-a_:+9.0f}"
          f"   {(b_-rb)-(a_-ra):+9.0f}")

def peaks(vals, ds):
    out = []
    for i in range(1, len(vals)-1):
        if vals[i] >= vals[i-1] and vals[i] > vals[i+1]:
            out.append((ds[i], vals[i], vals[i] - float(min(vals[i+1:]))))
    return out

print()
for lbl, vals in ((label_a, va), (label_b, vb)):
    pk = peaks(vals, ds)
    if pk:
        d, v, p = max(pk, key=lambda t: t[2])
        print(f"  {lbl}: interior peak d={d:.0f} px, {v:.0f} DN, prominence {p:+.0f} DN"
              f"   all={[(int(x), int(z)) for x, _, z in pk]}")
    else:
        print(f"  {lbl}: NO interior peak")
print()
print(f"  max |{label_b}-{label_a}| across bins: "
      f"{max(abs(b-a) for a, b in zip(va, vb)):.0f} DN")

"""If the clamp is a CONSTANT negative level offset in the base band, then the
clamped fraction of each subject must equal the fraction of that subject's
CONTROL pixels lying below one fixed DN level -- the same level for every
subject. That is a prediction, and it can fail."""
import numpy as np, tifffile, sys

SUBJ = ["flower-bud-alone-cpl", "dry-erase-marker-head-cpl", "foam",
        "bee-1-cpl", "couch-fibers-cpl"]
D = r"C:\dev\strehl-out\V-BLEND\lin"

def blue(p):
    a = tifffile.imread(p); assert a.dtype == np.uint16
    return a[:, :, 2]

print("="*78)
print("Does one fixed level explain every subject's clamp fraction?")
print("="*78)
print(f"  {'subject':28s} {'clamp %':>9} {'implied T (DN)':>15} {'BEFORE p1':>10} {'BEFORE min':>11}")
rows = []
for s in SUBJ:
    try:
        A = blue(f"{D}\\{s}-after.tiff"); B = blue(f"{D}\\{s}-before.tiff")
    except FileNotFoundError:
        print(f"  {s:28s}  (missing)"); continue
    frac = float((A == 0).mean())
    Bf = B.ravel()
    T = float(np.quantile(Bf, frac)) if frac > 0 else float("nan")
    rows.append((s, frac, T))
    print(f"  {s:28s} {100*frac:9.4f} {T:15.1f} {np.percentile(Bf,1):10.1f} {Bf.min():11d}")

print()
print("  and the converse -- what each subject's clamp fraction WOULD be if the")
print("  level were the one fitted on flower-bud:")
if rows:
    Tfit = rows[0][2]
    print(f"  fitted on {rows[0][0]}: T = {Tfit:.1f} DN")
    print(f"  {'subject':28s} {'predicted %':>12} {'observed %':>12} {'ratio':>8}")
    for s, frac, T in rows:
        B = blue(f"{D}\\{s}-before.tiff")
        pred = float((B < Tfit).mean())
        r = (100*frac)/(100*pred) if pred > 0 else float("nan")
        print(f"  {s:28s} {100*pred:12.4f} {100*frac:12.4f} {r:8.2f}")

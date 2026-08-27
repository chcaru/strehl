"""Provenance audit of BUILD-SHARP §1's blur budget, from ITS OWN stored JSONs.

Read-only. Locates every number in the §1 table and states which ROI
population supplies it.
"""
import json, itertools
from pathlib import Path
import numpy as np

OUT = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\BUILD-SHARP\out")

def load(name):
    return json.loads((OUT / name).read_text())

for fn in ["esf-vs-g0cr.json", "esf-109-vs-shipped.json", "esf-tw-ru-vs-shipped.json"]:
    d = load(fn)
    print(f"\n########## {fn}   ref={d['ref']}  arms={d['arms']}")
    rows = d["rows"]
    arms = sorted({r["arm"] for r in rows})
    for arm in arms:
        sel = [r for r in rows if r["arm"] == arm]
        adm = [r for r in sel if r["admitted"]]
        print(f"  --- arm {arm}  (n={len(sel)}, admitted={len(adm)})")
        for r in sel:
            star = "*" if r["admitted"] else " "
            print(f"   {star} {r['stack']:>10} {r['roi']:>4} floor={r['floor_um']:7.4f} "
                  f"rise_ref={r['rise_ref_um']:8.3f} rise_arm={r['rise_arm_um']:8.3f} "
                  f"delta={r['delta_um']:8.3f} shift=({r['shift_dy']},{r['shift_dx']})")
        if adm:
            rr = np.array([r["rise_ref_um"] for r in adm])
            ra = np.array([r["rise_arm_um"] for r in adm])
            print(f"     pooled ADMITTED: mean rise_ref={rr.mean():.4f} "
                  f"mean rise_arm={ra.mean():.4f}  mean delta={np.mean([r['delta_um'] for r in adm]):.4f}")

print("\n\n########## hunting the published constants")
allrows = []
for fn in ["esf-vs-g0cr.json", "esf-109-vs-shipped.json", "esf-tw-ru-vs-shipped.json"]:
    d = load(fn)
    for r in d["rows"]:
        r["_file"] = fn; r["_ref"] = d["ref"]; allrows.append(r)

targets = {"predicted_total": 34.78, "measured_total": 35.69,
           "optics_RU1": 30.44, "resampling": 14.97, "gated_mean": 7.61}

def report(label, val, how):
    for k, t in targets.items():
        if abs(val - t) < 0.02:
            print(f"  HIT {k}={t}: {val:.4f}  <- {label}  [{how}]")

# every subset of every (file, arm) grouping, on rise_ref and rise_arm
for fn in {r["_file"] for r in allrows}:
    for arm in {r["arm"] for r in allrows if r["_file"] == fn}:
        sel = [r for r in allrows if r["_file"] == fn and r["arm"] == arm]
        for field in ("rise_ref_um", "rise_arm_um"):
            for k in range(1, len(sel) + 1):
                for combo in itertools.combinations(sel, k):
                    m = float(np.mean([c[field] for c in combo]))
                    names = "+".join(f"{c['stack']}/{c['roi']}" for c in combo)
                    report(f"{fn} arm={arm} {field} mean({names})", m, "pooled mean of rises")

print("\n  quadrature checks:")
import math
print(f"   sqrt(30.44^2+14.97^2+7.61^2) = {math.sqrt(30.44**2+14.97**2+7.61**2):.4f}  (published predicted 34.78)")
print(f"   sqrt(30.44^2-14.11^2)        = {math.sqrt(30.44**2-14.11**2):.4f}  (published non-diffraction 26.98)")
for a,b,lab in [(30.44,'optics','o'),(14.97,'resampling','r'),(7.61,'gated','g')]:
    print(f"   variance share {lab}: {100*a*a/(30.44**2+14.97**2+7.61**2):.1f}%")

import json, glob, sys
sys.path.insert(0, '.')
from bandsweep import boundary
R2 = ["112MSDCF","flat-on-ruler-cpl","tweezers-cpl","lavendar-cpl",
      "dry-erase-marker-head-cpl","paper-sweep"]
B = ["0.17-0.20","0.20-0.25","0.25-0.30","0.30-0.40","0.40-0.48"]
def load(far):
    out = {}
    for f in glob.glob(f"bandsweep-far{far}*.json"):
        if "simdecim" in f: continue
        for r in json.load(open(f)):
            if r["key"] in R2: out.setdefault(r["key"], r)
    return out
f20, f8 = load(20), load(8)
TAG = {"PASS":"PASS","MARGINAL":"MARG","FAIL(noise)":"FAIL"}
print("=== VERDICT ROWS (far=20) ===")
for k in R2:
    r = f20[k]
    cells = " | ".join(f"**{r['bands'][b]['R']:.3f}** {TAG.get(r['bands'][b]['verdict'],'FAIL')}" for b in B)
    print(f"| `{k}` | {r['n_real']} | {r['step']} | {r['kept']} | {cells} | **{boundary(r):.2f}** |")
print("\n=== CI ROWS (far=20) ===")
for k in R2:
    r = f20[k]
    cells = " | ".join(f"{r['bands'][b]['R']:.3f} [{r['bands'][b]['lo']:.3f}, {r['bands'][b]['hi']:.3f}]" for b in ("0.17-0.20","0.20-0.25"))
    print(f"| `{k}` | {cells} |")
print("\n=== LADDER ROWS ===")
for k in R2:
    a, b_ = f20[k], f8[k]
    print(f"| `{k}` | {boundary(a):.2f} | {boundary(b_):.2f} | {'same' if boundary(a)==boundary(b_) else 'MOVED'} |")
print("\n=== BAND 0 (0.25-0.50) verdicts, all subjects ===")
allrec = {}
for f in glob.glob("bandsweep-far20*.json"):
    if "simdecim" in f: continue
    for r in json.load(open(f)): allrec.setdefault(r["key"], r)
for k, r in sorted(allrec.items()):
    vs = [r["bands"][b]["verdict"] for b in ("0.25-0.30","0.30-0.40","0.40-0.48")]
    v = "SIGNAL" if all(x=="PASS" for x in vs) else ("NOISE" if all(x.startswith("FAIL") for x in vs) else "MIXED")
    rs = " ".join(f"{r['bands'][b]['R']:7.3f}" for b in ("0.25-0.30","0.30-0.40","0.40-0.48"))
    print(f"  {k:<28} {rs}   {v}")
print("\n=== boundaries, all ===")
for k, r in sorted(allrec.items(), key=lambda kv: boundary(kv[1])):
    print(f"  {k:<28} {boundary(r):.2f}")
bs = sorted({boundary(r) for r in allrec.values()})
print(f"\n  distinct boundaries: {bs}   n_subjects={len(allrec)}")

import json
for far in (20, 8):
    r = {x["key"]: x for x in json.load(open(f"bandsweep-far{far}-112MSDCF.json"))}["112MSDCF"]
    print(f"--- 112MSDCF  far={far}  N={r['n_real']} step={r['step']} kept={r['kept']} ---")
    for k in sorted(r["bands"], key=lambda k: r["bands"][k]["f_lo"]):
        b = r["bands"][k]
        if b["f_lo"] < 0.10: continue
        print(f"  {k:>10}  R={b['R']:8.4f}  CI=[{b['lo']:7.4f},{b['hi']:8.4f}]  {b['verdict']}")
print()
print("ORCH's band 0 is 0.25-0.50 cyc/px (corrected contrast_ms.py, commit 0ff348ec).")
print("FINE bands inside it on 112MSDCF, far=20:")
r = {x["key"]: x for x in json.load(open("bandsweep-far20-112MSDCF.json"))}["112MSDCF"]
for k in ("0.25-0.30", "0.30-0.40", "0.40-0.48"):
    b = r["bands"][k]
    print(f"  {k}  R={b['R']:.4f}  CI low={b['lo']:.4f}  {b['verdict']}   "
          f"(PASS needs R>=2.0 and CI low>=1.5)")

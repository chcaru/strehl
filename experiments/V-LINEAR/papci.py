import json
r = {x["key"]: x for x in json.load(open("bandsweep-far20-paper-sweep.json"))}["paper-sweep"]
print("paper-sweep -- the STRUCTURE side of fact 1826's self-targeting claim")
print(f"  N={r['n_real']} step={r['step']} far={r['far_real']} kept={r['kept']}\n")
for k in sorted(r["bands"], key=lambda k: r["bands"][k]["f_lo"]):
    b = r["bands"][k]
    if b["f_lo"] < 0.10: continue
    band = "band 1 (0.17-0.25)" if b["f_hi"] <= 0.25 else "band 0 (0.25-0.50)"
    flag = "  <-- only 0.1% above the 2.0 bar" if 2.0 <= b["R"] < 2.05 else ""
    print(f"  {k:>10}  R={b['R']:8.4f}  CI=[{b['lo']:7.4f},{b['hi']:8.4f}]  {b['verdict']:<9} {band}{flag}")

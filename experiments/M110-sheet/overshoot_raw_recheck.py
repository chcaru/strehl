import json
d = json.load(open(r"C:\dev\strehl-out\M110-sheet\ca_overshoot_default_vs_ca.json"))
BOUND = 0.788
print("Does item 88 (no kink at r=0.788) survive WITHOUT the null?")
print("Does item 89 (+3.35 pp outermost step) survive WITHOUT the null?")
print()
for subj, v in d.items():
    if not isinstance(v, dict) or "overshoot_real" not in v:
        continue
    real, null = v["overshoot_real"], v["overshoot_inert_null"]
    R = [x["overshoot_pct"] for x in real]
    N = [x["overshoot_pct"] for x in null]
    E = [a - b for a, b in zip(R, N)]
    print("=== " + subj + " ===")
    print(f"{'bin':>11} {'RAW':>7} {'dRAW':>7} {'NULL':>7} {'dNULL':>7} {'EXC':>7} {'dEXC':>7}")
    for i, x in enumerate(real):
        f = lambda a: "" if i == 0 else f"{a[i]-a[i-1]:+7.2f}"
        mark = " <-- boundary" if x["r_lo"] <= BOUND < x["r_hi"] else ""
        print(f"{x['r_lo']:.2f}-{x['r_hi']:.2f} {R[i]:>7.2f} {f(R):>7} "
              f"{N[i]:>7.2f} {f(N):>7} {E[i]:>+7.2f} {f(E):>7}{mark}")
    dR = [R[i]-R[i-1] for i in range(1, len(R))]
    print(f"  item 88, RAW step across boundary bin = {dR[7]:+.2f}; "
          f"neighbours {dR[6]:+.2f}, {dR[8]:+.2f}  -> "
          f"{'NO KINK' if abs(dR[7]) <= max(abs(dR[6]),abs(dR[8]))*1.5 else 'KINK'}")
    dN = [N[i]-N[i-1] for i in range(1, len(N))]
    dE = [E[i]-E[i-1] for i in range(1, len(E))]
    print(f"  item 89, LAST bin: raw {dR[-1]:+.2f}, null {dN[-1]:+.2f}, "
          f"excess {dE[-1]:+.2f}  -> the excess step is "
          f"{'NULL-DRIVEN' if abs(dN[-1]) > abs(dR[-1]) else 'REAL'}")
    print()

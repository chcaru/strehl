import json
a = {r["key"]: r for r in json.load(open("bandsweep-far20-leaf-2-cpl.json"))}["leaf-2-cpl"]
b = {r["key"]: r for r in json.load(open("bandsweep-far20-simdecim2-leaf-2-cpl.json"))}["leaf-2-cpl"]
print("DECIMATION COMMISSIONING -- pre-registered: --simdecim 2 reads the SAME")
print("91 frames as the full 182-develop run, so R and CI must match to every")
print("printed digit and n_real must still report 182.\n")
print(f"  n_real   full={a['n_real']}  decim={b['n_real']}   {'ok' if a['n_real']==b['n_real'] else 'MISMATCH'}")
print(f"  step     full={a['step']}    decim={b['step']}     {'ok' if a['step']==b['step'] else 'MISMATCH'}")
print(f"  far_real full={a['far_real']}   decim={b['far_real']}    {'ok' if a['far_real']==b['far_real'] else 'MISMATCH'}")
print(f"  n_dev    full={a.get('n_dev')}  decim={b.get('n_dev')}")
print(f"  kept     full={a['kept']}    decim={b['kept']}     {'ok' if a['kept']==b['kept'] else 'MISMATCH'}")
print(f"\n  {'band':>10} {'R full':>10} {'R decim':>10} {'CIlo full':>10} {'CIlo decim':>10}  same")
bad = 0
for k in sorted(a["bands"], key=lambda k: a["bands"][k]["f_lo"]):
    x, y = a["bands"][k], b["bands"][k]
    same = (x["R"] == y["R"]) and (x["lo"] == y["lo"]) and (x["verdict"] == y["verdict"])
    bad += not same
    print(f"  {k:>10} {x['R']:10.4f} {y['R']:10.4f} {x['lo']:10.4f} {y['lo']:10.4f}  {'ok' if same else 'MISMATCH'}")
print(f"\n  bands differing: {bad}/{len(a['bands'])}")
print("  DECIMATED DEVELOPS ARE EQUIVALENT TO FULL DEVELOPS:", bad == 0)

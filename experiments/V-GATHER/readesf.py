import json,sys,glob,os
base=r"C:\dev\blog\death-of-software\projects\strehl\experiments\BUILD-SHARP\out"
for f in ["esf-vs-g0cr.json","esf-tw-ru-vs-shipped.json","esf-109-vs-shipped.json"]:
    p=os.path.join(base,f)
    if not os.path.exists(p): continue
    d=json.load(open(p))
    print("="*70); print(f, " ref=",d.get("ref"), " arms=",d.get("arms"))
    for r in d["rows"]:
        print(f"{r['stack']:>10} {r['roi']:>5} adm={str(r['admitted']):>5} "
              f"floor={r['floor_um']:7.4f} arm={r['arm']:>16} "
              f"rise_ref={r['rise_ref_um']:8.3f} rise_arm={r['rise_arm_um']:8.3f} "
              f"d={r['delta_um']:+7.3f}")

import json
p=r"C:\dev\blog\death-of-software\projects\strehl\experiments\M88b-merge-sharpness\out\b03_nulls.json"
d=json.load(open(p))
adm={(r["stack"],r["name"]):r for r in d["N1"]["rows"]}
print(f"{'stack':>12}{'roi':>6}{'admitted':>10}{'floor_um':>10}  {'window (r0,c0,h,w)':<28}{'axis'}")
for r in d["rois"]:
    a=adm.get((r["stack"],r["name"]),{})
    print(f"{r['stack']:>12}{r['name']:>6}{str(bool(a.get('admitted',False))):>10}"
          f"{a.get('p95_abs_um',float('nan')):10.4f}  {str(tuple(r['roi'])):<28}{r['axis']}")

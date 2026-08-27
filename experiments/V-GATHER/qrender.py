import json, sys
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-GATHER")
from ab import render
PLAN = [
    ("wrapped-text-1", 20), ("wrapped-text-2", 20), ("bee-1-cpl", 20),
    ("couch-fibers-cpl", 20), ("tweezers-cpl", 20),
    ("foam", 20), ("lavendar-cpl", 20), ("flower-bud-alone-cpl", 20),
    ("coffee-bubbles", 19), ("highly-angled-ruler-mm-cpl", 20),
]
rows = []
for subj, lim in PLAN:
    for arm in ("1", "0"):
        d = render(subj, arm, lim, "q")
        rows.append(d)
        print(f"{subj:30s} arm={arm} rc={d['rc']} sha={str(d.get('sha'))[:16]} "
              f"wall={d['wall_s']:.1f}s cov={d['coverage']}", flush=True)
    a = [r for r in rows if r["subject"] == subj]
    same = a[0].get("sha") == a[1].get("sha")
    print(f"   -> arms byte-identical: {same}", flush=True)
json.dump(rows, open(r"C:\dev\strehl-out\V-GATHER\quality-renders.json", "w"), indent=1)

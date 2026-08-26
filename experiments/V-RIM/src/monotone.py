import re
from pathlib import Path

for log, tag in ((r"C:\dev\strehl-out\V-RIM\framerings-cb2.log", "coffee-bean"),
                 (r"C:\dev\strehl-out\V-RIM\framerings-fb.log", "flower-bud")):
    lines = Path(log).read_text(encoding="utf-8", errors="replace").splitlines()
    print(f"\n=== {tag}: monotonicity of the median profile over t = 0..280 px ===")
    print("  (STRAIGHTEST-QUARTILE block only; far field is column 5 of the row)")
    seen = set()
    for i, ln in enumerate(lines):
        m = re.match(r"\s+(MERGE|FRAME\d+)\s", ln)
        if not m or m.group(1) in seen or i + 1 >= len(lines):
            continue
        prof = lines[i + 1]
        if "profile:" not in prof:
            continue
        seen.add(m.group(1))
        far = float(ln.split()[4])
        pts = [(int(a), int(b)) for a, b in re.findall(r"(\d+):(\d+)", prof.split("profile:")[1])]
        drops = [(pts[k][0], pts[k + 1][1] - pts[k][1])
                 for k in range(len(pts) - 1) if pts[k + 1][1] < pts[k][1]]
        worst = min((d for _, d in drops), default=0)
        tot = sum(d for _, d in drops)
        verdict = "MONOTONE" if -tot / far < 0.01 else "NON-MONOTONE"
        print(f"  {m.group(1):8s} far={far:6.0f}  reversals={len(drops):2d}  "
              f"worst={worst:+6d} DN ({worst/far*100:+6.2f}%)  "
              f"total fall={tot:+6d} DN ({tot/far*100:+6.2f}%)  {verdict}")
        if drops:
            print(f"           reversals at t = {[t for t, _ in drops]}")

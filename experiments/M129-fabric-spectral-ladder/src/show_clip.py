"""Print the per-ROI, per-aperture 99.9th percentile table behind gate T5."""
import json
import os
import sys

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "out")
path = os.path.join(OUT, sys.argv[1] if len(sys.argv) > 1 else "rois-w2.json")
d = json.load(open(path, encoding="utf-8"))
aps = d["apertures"]
print("99.9th percentile DN per ROI and aperture; gate T5 rejects above "
      f"{d['p999_max']:.0f}\n")
print("ROI     rc     cc  " + "".join(f"{a:>9}" for a in aps) + "   in-band ok")
for i, r in enumerate(d["rois"]):
    p = r.get("p999", {})
    cells = "".join(f"{p.get(a, float('nan')):9.0f}" for a in aps)
    inband = [a for a in ("f11", "f14", "f18") if a in p]
    ok = all(p[a] <= d["p999_max"] for a in inband)
    flags = "".join("*" if p.get(a, 0) > d["p999_max"] else " " for a in aps)
    print(f"{i:3d} {r['rc']:6d} {r['cc']:6d}  {cells}   {'PASS' if ok else 'FAIL'}"
          f"   clipped:{flags}")
print("\n* marks an aperture over the gate.")

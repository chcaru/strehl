import json, os, tri
d = json.load(open(os.path.join(tri.OUT, "compare", "wrapped-text-2.region.json")))
print("wrapped-text-2: is the lower-left BLURRED, or merely DARKER?")
print("edge slope in DN/px scales with local illumination, so a cross-region")
print("comparison in raw DN/px is a comparison across a tone difference.")
print()
print(f"{'site':<13}{'mean DN':>10}{'merge DN/px':>13}{'slope/mean':>12}"
      f"{'vs right':>10}   merge/source")
ref = None
rows = []
for lab, s in d["sites"].items():
    e = s["edge"]
    m = s.get("mean_merge_dn")
    if m is None:
        continue
    rows.append((lab, m, e["merge_dnpx"], e["merge_dnpx"] / m, e["ratio"]))
if not rows:
    print("mean_merge_dn not stored in the JSON; recomputing from saved tiles")
    import numpy as np
    for lab in d["sites"]:
        p = os.path.join(tri.OUT, "tiles", f"wrapped-text-2.{lab}.npz")
        if not os.path.exists(p):
            print("  missing tile:", p); continue
        z = np.load(p)
        a = z["merge"].astype(np.float64)
        e = d["sites"][lab]["edge"]
        rows.append((lab, float(a.mean()), e["merge_dnpx"],
                     e["merge_dnpx"] / float(a.mean()), e["ratio"]))
ref = next((r for r in rows if r[0] == "RIGHT-REF"), None)
for lab, m, sl, norm, rat in rows:
    rel = norm / ref[3] if ref else float("nan")
    print(f"{lab:<13}{m:>10.0f}{sl:>13.1f}{norm:>12.5f}{rel:>10.3f}   {rat:>6.4f}")

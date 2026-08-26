import json, os, numpy as np, tri
SNR = 4.0
def usable(v):
    if any("not clear of" in c for c in v.get("caution", [])):  return False
    if not v.get("reliable", True):                             return False
    e = v.get("edge") or {}
    m, f = e.get("merge_dnpx", 0), e.get("frame_corr_dnpx", 0)
    nm, nf = e.get("noise_merge_dn", 0), e.get("noise_frame_dn", 0)
    if nm > 0 and m < SNR * nm:                                 return False
    if e.get("ratio", 1) < 1.0 and nf > 0 and f < SNR * nf:     return False
    return True
d_abs, d_rel, worst = [], [], None
for s in tri.SUBJECTS:
    d = json.load(open(os.path.join(tri.OUT, "compare", s + ".json")))
    for lab, v in d["sites"].items():
        if lab == "FLAT" or not usable(v):  continue
        p = os.path.join(tri.OUT, "tiles", f"{s}.{lab}.npz")
        if not os.path.exists(p):           continue
        z = np.load(p)
        ma = float(z["merge"].astype(np.float64).mean())
        mb = float(z["frame"].astype(np.float64).mean())
        d_abs.append(ma - mb); r = ma / mb - 1.0; d_rel.append(r)
        if worst is None or abs(r) > abs(worst[2]):
            worst = (s, lab, r, ma, mb)
a = np.array(d_abs); r = np.array(d_rel)
print("ABSOLUTE LEVEL AGREEMENT between the two arms (merge minus frame), DN")
print("  the brief requires absolute DN because an additive bias is invisible")
print("  in a ratio and invisible in an error.")
print()
print(f"  sites            {len(a)}")
print(f"  mean  delta      {a.mean():+.1f} DN")
print(f"  median delta     {np.median(a):+.1f} DN")
print(f"  median |rel|     {np.median(np.abs(r))*100:.2f} %")
print(f"  90th pct |rel|   {np.percentile(np.abs(r),90)*100:.2f} %")
print(f"  worst            {worst[0]} {worst[1]}  {worst[2]*100:+.1f}% "
      f"({worst[3]:.0f} vs {worst[4]:.0f} DN)")

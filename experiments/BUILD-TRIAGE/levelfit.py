"""Is the merge-vs-frame level difference MULTIPLICATIVE (exposure) or
ADDITIVE (black point)?  The answer decides whether edge slope in DN/px may
be normalised by the local mean.

  multiplicative  merge = g * frame            -> slope scales with g,
                                                  slope/mean is invariant
  additive        merge = frame + b            -> slope is UNCHANGED by b,
                                                  normalising INVENTS an error

Fit merge = g*frame + b per site by least squares on the matched tiles and
report both terms in DN.  The brief is explicit that an additive bias is
invisible in a ratio, so it is measured here rather than assumed away.
"""
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

print(f"{'subject':<30}{'site':<12}{'gain g':>9}{'offset b DN':>13}"
      f"{'mean m':>9}{'mean f':>9}{'ratio':>8}{'ratio/g':>9}")
out = []
for s in tri.SUBJECTS:
    d = json.load(open(os.path.join(tri.OUT, "compare", s + ".json")))
    for lab, v in d["sites"].items():
        if lab == "FLAT" or not usable(v):
            continue
        p = os.path.join(tri.OUT, "tiles", f"{s}.{lab}.npz")
        if not os.path.exists(p):
            continue
        z = np.load(p)
        a = z["merge"].astype(np.float64).ravel()
        b_ = z["frame"].astype(np.float64).ravel()
        A = np.vstack([b_, np.ones_like(b_)]).T
        g, off = np.linalg.lstsq(A, a, rcond=None)[0]
        e = v["edge"]
        out.append((s, lab, g, off, a.mean(), b_.mean(), e["ratio"]))
for s, lab, g, off, ma, mb, rat in out:
    print(f"{s:<30}{lab:<12}{g:>9.4f}{off:>+13.1f}{ma:>9.0f}{mb:>9.0f}"
          f"{rat:>8.4f}{rat/max(g,1e-9):>9.4f}")
gs = np.array([o[2] for o in out]); bs = np.array([o[3] for o in out])
print()
print(f"gain   g: median {np.median(gs):.4f}  range {gs.min():.4f}-{gs.max():.4f}")
print(f"offset b: median {np.median(bs):+.1f} DN  range {bs.min():+.1f}..{bs.max():+.1f} DN")

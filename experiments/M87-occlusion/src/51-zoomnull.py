import sys, pathlib, json, numpy as np, tifffile
sys.path.insert(0, str(pathlib.Path("src").resolve()))
import m87lib as L, m87metric2 as M2
C = pathlib.Path("cache")
def lum(p):
    a = tifffile.imread(p); assert a.dtype == np.uint16, a.dtype
    return a[:, :, 1].astype(np.float32)
out = {}
for tag, bp, ap in [("ALIGNED", C/"ship-before-linear.tif", C/"ship-after-linear.tif"),
                    ("ZOOMNULL", C/"zeronull"/"U0-before.tif", C/"zeronull"/"U1-after.tif")]:
    b, a = lum(bp), lum(ap)
    mask, tau = L.foreground_mask(b)
    pts, nrm = M2.boundary_normals(mask, roi=L.ROIS["ROI_LEG"])
    val = M2.valid_profiles(mask, pts, nrm, d_max=M2.D_MAX)
    p, nv = pts[val], nrm[val]
    rb = M2.score_iso(b, p, nv, boot=500); ra = M2.score_iso(a, p, nv, boot=500)
    d = 100*(1-ra["ISO"]/rb["ISO"])
    out[tag] = {"tau":float(tau),"fg":float(mask.mean()),"n":int(val.sum()),
                "before":rb["ISO"],"before_ci":rb["ISO_ci"],
                "after":ra["ISO"],"after_ci":ra["ISO_ci"],"delta_pct":d}
    print(f"{tag:9s} tau={tau:6.0f} fg={100*mask.mean():5.2f}% n={int(val.sum()):5d} "
          f"ISO {rb['ISO']:.5f} -> {ra['ISO']:.5f}   {d:+.1f}%")
A, Z = out["ALIGNED"]["delta_pct"], out["ZOOMNULL"]["delta_pct"]
print(f"\nC-ZOOMNULL: aligned {A:+.1f}%  vs  unregistered {Z:+.1f}%   ratio {Z/A:.3f}")
print("PASS -- the fix does not depend on registration" if 0.75 <= Z/A <= 1.333
      else "FAIL -- benefit depends on alignment; this is a geometry fix")
out["ratio"] = Z/A
json.dump(out, open("data/51-zoomnull.json","w"), indent=1)

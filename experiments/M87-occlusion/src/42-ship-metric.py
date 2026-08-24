import sys, pathlib, json, numpy as np, tifffile
sys.path.insert(0, str(pathlib.Path("src").resolve()))
import m87lib as L, m87metric2 as M2
C = pathlib.Path("cache")
def lum(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"expected uint16, got {a.dtype}"
    return a[:, :, 1].astype(np.float32)
b, a = lum(C/"ship-before-linear.tif"), lum(C/"ship-after-linear.tif")
print("shape", b.shape, "dtype ok, max", b.max())
ROI = L.ROIS["ROI_LEG"]
mask, tau = L.foreground_mask(b)
print(f"mask on shipped BEFORE: tau={tau:.0f} fg={100*mask.mean():.2f}%")
pts, nrm = M2.boundary_normals(mask, roi=ROI)
val = M2.valid_profiles(mask, pts, nrm, d_max=M2.D_MAX)
p, nv = pts[val], nrm[val]
print("valid profiles:", int(val.sum()))
rb = M2.score_iso(b, p, nv, boot=500); ra = M2.score_iso(a, p, nv, boot=500)
print(f"ISO BEFORE = {rb['ISO']:.5f}  CI[{rb['ISO_ci'][0]:.5f},{rb['ISO_ci'][1]:.5f}]")
print(f"ISO AFTER  = {ra['ISO']:.5f}  CI[{ra['ISO_ci'][0]:.5f},{ra['ISO_ci'][1]:.5f}]")
print(f"change     = {100*(1-ra['ISO']/rb['ISO']):+.1f}%")
json.dump({"reader":"tifffile","ISO_before":rb["ISO"],"ci_before":rb["ISO_ci"],
           "ISO_after":ra["ISO"],"ci_after":ra["ISO_ci"],
           "delta_pct":100*(1-ra["ISO"]/rb["ISO"]),"n_prof":int(val.sum()),
           "mask_tau":float(tau),"mask_fg_frac":float(mask.mean())},
          open("data/42-ship-metric.json","w"), indent=1)

"""Invented structure, camera-linear, WITH the resampling control subtracted.

commission_invent.py K4 showed that the merge's own geometric round trip
(crop the field to s, resample back to full size) lowers gradient kurtosis all
by itself. The merge arm gets that round trip; argmax does not. So part of any
merge/argmax kurtosis gap is geometry, not merging.

Three columns per subject, all on the SAME flat mask, all camera-linear green:
  observed  = gk(argmax native)      / gk(merge native)        <- README's claim
  resample  = gk(argmax native)      / gk(argmax round-tripped) <- geometry alone
  corrected = observed / resample                               <- what MERGING buys

corrected is the number that survives. If corrected ~ 1, the subject's apparent
invented structure was the resampler.
"""
import json, pathlib, sys
import numpy as np, tifffile, cv2
from scipy.ndimage import uniform_filter, map_coordinates

sys.path.insert(0, str(pathlib.Path("experiments/V-THESIS").resolve()))
R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
REG = {r["subject"]: r for r in json.loads(
    pathlib.Path(r"C:\dev\strehl-out\V-THESIS\register.json").read_text())}
README = {"bee-3-cpl": 2.79, "flowers-cpl": 1.98, "bee-1-cpl": 1.89,
          "leaf-2-cpl": 1.57, "tweezers-cpl": 1.17, "flat-on-ruler-cpl": 1.01}


def gk(a, m):
    gx = np.diff(a, axis=1)[:-1, :]; gy = np.diff(a, axis=0)[:, :-1]
    g = np.hypot(gx, gy)[m[:-1, :-1]]
    return float((((g - g.mean()) / g.std()) ** 4).mean())


def roundtrip(a, s):
    h, w = a.shape
    sm = cv2.resize(a, (int(round(w*s)), int(round(h*s))), interpolation=cv2.INTER_AREA)
    return cv2.resize(sm, (w, h), interpolation=cv2.INTER_CUBIC)


print(f"{'subject':<19}{'observed':>10}{'resample':>10}{'corrected':>11}"
      f"{'README(png)':>12}")
print("-" * 62)
out = {}
for subj in README:
    reg = REG[subj]; s, tx, ty = reg["fitted_scale"], reg["tx"], reg["ty"]
    gm = tifffile.imread(str(R/subj/"merge.tif"))[:, :, 1].astype(np.float64)
    ga = tifffile.imread(str(R/subj/"argmax.tif"))[:, :, 1].astype(np.float64)
    H, W = gm.shape
    yy, xx = np.mgrid[0:H, 0:W]
    ax = s*xx + tx; ay = s*yy + ty
    inb = (ax >= 1) & (ax < ga.shape[1]-1) & (ay >= 1) & (ay < ga.shape[0]-1)
    a_on_m = map_coordinates(ga, [np.clip(ay, 0, ga.shape[0]-1),
                                  np.clip(ax, 0, ga.shape[1]-1)], order=0)
    energy = uniform_filter(np.hypot(*np.gradient(0.5*(gm+a_on_m))), size=9)
    mask_m = (energy <= np.quantile(energy[inb], 0.35)) & inb
    mask_a = np.zeros(ga.shape, bool)
    mask_a[np.clip(np.round(ay[mask_m]).astype(int), 0, ga.shape[0]-1),
           np.clip(np.round(ax[mask_m]).astype(int), 0, ga.shape[1]-1)] = True
    ka, km = gk(ga, mask_a), gk(gm, mask_m)
    krt = gk(roundtrip(ga, s), mask_a)
    obs, res = ka/km, ka/krt
    out[subj] = {"observed": obs, "resample": res, "corrected": obs/res,
                 "kurt_merge": km, "kurt_argmax": ka, "kurt_argmax_roundtrip": krt,
                 "readme_png": README[subj]}
    print(f"{subj:<19}{obs:>10.2f}{res:>10.2f}{obs/res:>11.2f}{README[subj]:>12.2f}")
print("-" * 62)
c = [v["corrected"] for v in out.values()]
print(f"corrected: median {np.median(c):.2f}  min {min(c):.2f}  max {max(c):.2f}")
pathlib.Path(r"C:\dev\strehl-out\V-THESIS\invent.json").write_text(
    json.dumps(out, indent=1), encoding="utf8")

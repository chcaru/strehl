"""Invented structure, recomputed CAMERA-LINEAR from the 16-bit TIFFs.

The README's 2.79x..1.01x table (ORCH-drift-check/labelcheck.py) is computed on
BUILD-THESIS's 8-bit crop PNGs, which measure.py:231 writes through
    (v ** (1/2.2) * 255).astype(uint8)
after clipping at the 0.5/99.7 percentiles. That is a tone curve and a 256-level
quantiser between the measurement and the scene. This asks whether it survives.

* Green plane, float64, straight off the TIFF. No curve, no channel mix.
  (labelcheck uses PIL convert("L") = 0.299R+0.587G+0.114B, a mix.)
* Flat mask chosen on the MEAN of both arms -- BUILD-THESIS's own symmetric
  convention. The mean is formed by putting argmax on the merge grid with
  NEAREST NEIGHBOUR, and each arm is then measured on ITS OWN native pixels
  under the mask warped back, again nearest neighbour. No interpolator ever
  touches a pixel value; interpolating argmax would smooth the hard edges
  that are the entire object of the measurement.
* Gradient kurtosis of pure Gaussian noise -> 3.245 (Rayleigh). A NOISIER arm
  is pulled TOWARDS 3.245, so the arms' noise gap cannot manufacture an argmax
  excess; it opposes one.
"""
import json, pathlib, sys
import numpy as np, tifffile
from scipy.ndimage import uniform_filter, map_coordinates

sys.path.insert(0, str(pathlib.Path("experiments/V-THESIS").resolve()))
from vstat import sigma_immerkaer  # noqa: E402

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
REG = {r["subject"]: r for r in json.loads(
    pathlib.Path(r"C:\dev\strehl-out\V-THESIS\register.json").read_text())}
README = {"bee-3-cpl": 2.79, "flowers-cpl": 1.98, "bee-1-cpl": 1.89,
          "leaf-2-cpl": 1.57, "tweezers-cpl": 1.17, "flat-on-ruler-cpl": 1.01}


def grad_kurt(a, m):
    gx = np.diff(a, axis=1)[:-1, :]; gy = np.diff(a, axis=0)[:, :-1]
    g = np.hypot(gx, gy)[m[:-1, :-1]]
    if g.size < 5000 or g.std() == 0: return float("nan")
    return float((((g - g.mean()) / g.std()) ** 4).mean())


print(f"{'subject':<19}{'kurt merge':>11}{'kurt argmax':>12}{'ratio':>8}"
      f"{'README':>8}{'n_px':>10}")
print("-" * 68)
out = {}
for subj in README:
    reg = REG[subj]
    s, tx, ty = reg["fitted_scale"], reg["tx"], reg["ty"]
    gm = tifffile.imread(str(R / subj / "merge.tif"))[:, :, 1].astype(np.float64)
    ga = tifffile.imread(str(R / subj / "argmax.tif"))[:, :, 1].astype(np.float64)
    H, W = gm.shape
    yy, xx = np.mgrid[0:H, 0:W]
    ax = s * xx + tx; ay = s * yy + ty
    inb = (ax >= 1) & (ax < ga.shape[1] - 1) & (ay >= 1) & (ay < ga.shape[0] - 1)
    a_on_m = map_coordinates(ga, [np.clip(ay, 0, ga.shape[0] - 1),
                                  np.clip(ax, 0, ga.shape[1] - 1)], order=0)
    mean = 0.5 * (gm + a_on_m)
    energy = uniform_filter(np.hypot(*np.gradient(mean)), size=9)
    thr = np.quantile(energy[inb], 0.35)
    mask_m = (energy <= thr) & inb
    mask_a = np.zeros(ga.shape, bool)
    mask_a[np.clip(np.round(ay[mask_m]).astype(int), 0, ga.shape[0] - 1),
           np.clip(np.round(ax[mask_m]).astype(int), 0, ga.shape[1] - 1)] = True
    km, ka = grad_kurt(gm, mask_m), grad_kurt(ga, mask_a)
    out[subj] = {"kurt_merge": km, "kurt_argmax": ka, "ratio": ka / km,
                 "readme_png_ratio": README[subj], "n_px": int(mask_m.sum())}
    print(f"{subj:<19}{km:>11.2f}{ka:>12.2f}{ka/km:>8.2f}"
          f"{README[subj]:>8.2f}{int(mask_m.sum()):>10}")
print("-" * 68)
print("Rayleigh (pure Gaussian noise) gradient kurtosis = 3.245")
print(f"median linear ratio = {np.median([v['ratio'] for v in out.values()]):.2f}"
      f"   median README(png) ratio = {np.median(list(README.values())):.2f}")
pathlib.Path(r"C:\dev\strehl-out\V-THESIS\invent.json").write_text(
    json.dumps(out, indent=1), encoding="utf8")

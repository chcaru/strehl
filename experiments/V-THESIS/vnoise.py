"""Noise gap between the arms, camera-linear, in genuinely FLAT regions.

Two independent estimators, deliberately different in construction:
  Immerkaer  3x3 Laplacian-like kernel, MEDIAN of |response| (mine)
  Donoho     MAD of the finest diagonal wavelet coefficients (BUILD-THESIS's)
plus a third that assumes nothing about kernels:
  hp7        SD of the residual after a 7x7 box mean, the estimator
             ORCH's labelcheck.py uses.

Control: the merge is produced by cropping the field to s and resampling back,
which lowers noise ALL BY ITSELF. Round-trip the argmax arm the same way and
report how much of the gap that alone accounts for.
"""
import json, pathlib, sys
import numpy as np, tifffile, cv2
from scipy.ndimage import uniform_filter, map_coordinates

sys.path.insert(0, str(pathlib.Path("experiments/V-THESIS").resolve()))
sys.path.insert(0, str(pathlib.Path("experiments/BUILD-THESIS").resolve()))
from vstat import sigma_immerkaer          # noqa: E402  mine
import stats as bt                          # noqa: E402  theirs

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
REG = {r["subject"]: r for r in json.loads(
    pathlib.Path(r"C:\dev\strehl-out\V-THESIS\register.json").read_text())}
SUBJ = ["bee-3-cpl", "flowers-cpl", "bee-1-cpl", "leaf-2-cpl",
        "tweezers-cpl", "flat-on-ruler-cpl"]
don = getattr(bt, "noise_sigma", None) or getattr(bt, "_noise_sigma", None)


def hp7(a, m):
    return float((a - uniform_filter(a, 7))[m].std())


def roundtrip(a, s):
    h, w = a.shape
    sm = cv2.resize(a, (int(round(w*s)), int(round(h*s))), interpolation=cv2.INTER_AREA)
    return cv2.resize(sm, (w, h), interpolation=cv2.INTER_CUBIC)


print(f"{'subject':<19}{'Immerkaer':>10}{'Donoho':>8}{'hp7':>7}"
      f"{'  |':>3}{'resamp-only':>12}{'net(hp7)':>10}")
print("-" * 72)
rows = {}
for subj in SUBJ:
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
    mask_m = (energy <= np.quantile(energy[inb], 0.20)) & inb   # flattest fifth
    mask_a = np.zeros(ga.shape, bool)
    mask_a[np.clip(np.round(ay[mask_m]).astype(int), 0, ga.shape[0]-1),
           np.clip(np.round(ax[mask_m]).astype(int), 0, ga.shape[1]-1)] = True
    ys, xs = np.where(mask_m); ya, xa = np.where(mask_a)
    bm = gm[ys.min():ys.max()+1, xs.min():xs.max()+1]
    ba = ga[ya.min():ya.max()+1, xa.min():xa.max()+1]
    im_r = sigma_immerkaer(ba) / sigma_immerkaer(bm)
    do_r = (don(ba)/don(bm)) if don else float("nan")
    h_r = hp7(ga, mask_a) / hp7(gm, mask_m)
    rt = hp7(roundtrip(ga, s), mask_a) / hp7(gm, mask_m)
    rows[subj] = {"immerkaer": im_r, "donoho": do_r, "hp7": h_r,
                  "hp7_resample_only": h_r/rt if rt else None, "net_hp7": rt}
    print(f"{subj:<19}{im_r:>10.3f}{do_r:>8.3f}{h_r:>7.3f}{'  |':>3}"
          f"{h_r/rt:>12.3f}{rt:>10.3f}")
print("-" * 72)
for k in ("immerkaer", "donoho", "hp7"):
    v = [rows[s][k] for s in SUBJ]
    print(f"{k:<11} median {np.median(v):.3f}   range {min(v):.3f} - {max(v):.3f}")
print()
print("resamp-only = how much of the hp7 gap the merge's crop-and-resample buys")
print("net(hp7)    = argmax AFTER that same round trip, vs merge: the residual")
print("              gap attributable to MERGING rather than to geometry")
pathlib.Path(r"C:\dev\strehl-out\V-THESIS\noise.json").write_text(
    json.dumps(rows, indent=1), encoding="utf8")

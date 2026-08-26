"""CORRECTED commissioning of the invented-structure statistic.

My first attempt (kurt_attack.py) derived the flat mask separately on each arm,
so it compared different sets of pixels. That is NOT the statistic in the
README: labelcheck.py:101 uses ONE mask from the mean of both panels, and
vinvent2.py maps one mask through the geometry. Those numbers are retracted.

This uses ORCH's exact grad_kurtosis / flat_mask definitions, camera-linear,
with the mask held fixed across the pair, and asks the two questions the
statistic has never been asked:

  K5'  BLUR PLANT  -- does it move when the only difference is sharpness?
                      (the test that disqualified P99/P75 at 1.39x)
  K6'  MASK SWEEP  -- is frac=0.35 load-bearing?
"""
import json, pathlib
import numpy as np, tifffile, cv2
from scipy.ndimage import uniform_filter

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
GREEN = 1
SCALES = {"bee-3-cpl": 0.93554, "bee-1-cpl": 0.92379, "leaf-2-cpl": 0.95399,
          "flowers-cpl": 0.98987, "tweezers-cpl": 0.97920, "flat-on-ruler-cpl": 0.97073}
README = {"bee-3-cpl": 2.79, "flowers-cpl": 1.98, "bee-1-cpl": 1.89,
          "leaf-2-cpl": 1.57, "tweezers-cpl": 1.17, "flat-on-ruler-cpl": 1.01}


def grad_kurtosis(a, mask):                      # ORCH's, verbatim
    gx = np.diff(a, axis=1)[:-1, :]
    gy = np.diff(a, axis=0)[:, :-1]
    g = np.hypot(gx, gy)
    v = g[mask[:-1, :-1]]
    if v.std() == 0:
        return float("nan")
    z = (v - v.mean()) / v.std()
    return float((z ** 4).mean())


def flat_mask(mean_img, frac=0.35):              # ORCH's, verbatim
    gx, gy = np.gradient(mean_img, axis=1), np.gradient(mean_img, axis=0)
    energy = uniform_filter(np.hypot(gx, gy), size=9)
    return energy <= np.quantile(energy, frac)


def gaussf(a, s):
    if s <= 0:
        return a
    n = int(6 * s) | 1
    return cv2.GaussianBlur(a, (n, n), s, borderType=cv2.BORDER_REFLECT)


print("=" * 72)
print("K5'  BLUR PLANT, mask fixed on the mean of both panels (ORCH's rule)")
print("=" * 72)
g = tifffile.imread(str(R / "bee-3-cpl" / "merge.tif"))[:, :, GREEN].astype(np.float64)
tile = g[2000:4048, 2000:4048]
print(f"{'planted blur':>13}{'k(sharp)':>11}{'k(blurred)':>12}{'ratio':>9}")
k5 = []
for s in (0.0, 0.5, 1.0, 2.0, 4.0):
    b = gaussf(tile, s)
    mk = flat_mask((tile + b) / 2.0)
    ks, kb = grad_kurtosis(tile, mk), grad_kurtosis(b, mk)
    k5.append((s, ks, kb, kb / ks))
    print(f"{s:>13.1f}{ks:>11.3f}{kb:>12.3f}{kb / ks:>9.3f}x")
rr = [r for _, _, _, r in k5]
print(f"\n-> a pure sharpness difference of up to 4 px moves the statistic "
      f"{min(rr):.3f}x-{max(rr):.3f}x")

print("\n" + "=" * 72)
print("K6'  MASK FRACTION SWEEP, camera-linear, geometry-matched")
print("=" * 72)
FR = (0.10, 0.20, 0.35, 0.50, 0.70)
print(f"{'subject':<20}{'README':>8}" + "".join(f"{f:>9.2f}" for f in FR))
out = []
for s, sc in SCALES.items():
    m = tifffile.imread(str(R / s / "merge.tif"))[:, :, GREEN].astype(np.float64)
    a = tifffile.imread(str(R / s / "argmax.tif"))[:, :, GREEN].astype(np.float64)
    h, w = m.shape
    cy, cx = h / 2.0, w / 2.0
    M = np.array([[sc, 0, cx * (1 - sc)], [0, sc, cy * (1 - sc)]], np.float64)
    aw = cv2.warpAffine(a, M, (w, h), flags=cv2.WARP_INVERSE_MAP | cv2.INTER_LANCZOS4,
                        borderMode=cv2.BORDER_REPLICATE)
    b = 400
    mm, aa = m[b:-b, b:-b], aw[b:-b, b:-b]
    row, rec = f"{s:<20}{README[s]:>8.2f}", {"subject": s}
    for f in FR:
        mk = flat_mask((mm + aa) / 2.0, f)
        r = grad_kurtosis(aa, mk) / grad_kurtosis(mm, mk)
        row += f"{r:>9.2f}"
        rec[str(f)] = float(r)
    out.append(rec)
    print(row)
print("\n(argmax/merge; >1 = selection has the heavier gradient tail)")
pathlib.Path(r"C:\dev\strehl-out\V-THESIS\kurt_attack2.json").write_text(
    json.dumps(dict(blur_plant=k5, mask_sweep=out), indent=1), encoding="utf8")

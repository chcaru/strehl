"""Finishing the invented-structure audit: the noise null on the CORRECTED
implementation, and where the absolute values actually sit.

Gradient magnitude of pure Gaussian noise is Rayleigh, whose kurtosis is 3.245.
If flat regions are noise-dominated both arms sit near 3.245 and the ratio is
driven by genuine departures. If one arm sits far above, that is structure.
"""
import json, pathlib
import numpy as np, tifffile, cv2
from scipy.ndimage import uniform_filter

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
GREEN = 1
SCALES = {"bee-3-cpl": 0.93554, "bee-1-cpl": 0.92379, "leaf-2-cpl": 0.95399,
          "flowers-cpl": 0.98987, "tweezers-cpl": 0.97920, "flat-on-ruler-cpl": 0.97073}


def grad_kurtosis(a, mask):
    gx, gy = np.diff(a, axis=1)[:-1, :], np.diff(a, axis=0)[:, :-1]
    v = np.hypot(gx, gy)[mask[:-1, :-1]]
    if v.std() == 0:
        return float("nan")
    return float((((v - v.mean()) / v.std()) ** 4).mean())


def flat_mask(mean_img, frac=0.35):
    gx, gy = np.gradient(mean_img, axis=1), np.gradient(mean_img, axis=0)
    e = uniform_filter(np.hypot(gx, gy), size=9)
    return e <= np.quantile(e, frac)


print("=" * 78)
print("K2'  NOISE NULL on the corrected implementation")
print("=" * 78)
g = tifffile.imread(str(R / "bee-3-cpl" / "merge.tif"))[:, :, GREEN].astype(np.float64)
tile = g[2000:4048, 2000:4048]
rng = np.random.default_rng(7)
print(f"{'added noise':>13}{'k(clean)':>11}{'k(noisy)':>11}{'ratio':>9}")
for pct in (0.0, 0.05, 0.15, 0.30):
    n = tile + rng.normal(0, pct * tile.std(), tile.shape) if pct else tile
    mk = flat_mask((tile + n) / 2.0)
    kc, kn = grad_kurtosis(tile, mk), grad_kurtosis(n, mk)
    print(f"{pct:>13.2f}{kc:>11.3f}{kn:>11.3f}{kn / kc:>9.3f}x")

print("\n" + "=" * 78)
print("absolute levels at frac=0.35 (Rayleigh/pure-noise reference = 3.245)")
print("=" * 78)
print(f"{'subject':<20}{'k(merge)':>10}{'k(argmax)':>11}{'ratio':>8}   reading")
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
    mk = flat_mask((mm + aa) / 2.0, 0.35)
    km, ka = grad_kurtosis(mm, mk), grad_kurtosis(aa, mk)
    tag = ("both near noise" if max(km, ka) < 4 else
           "argmax has real structure" if ka > km else "merge has more")
    print(f"{s:<20}{km:>10.3f}{ka:>11.3f}{ka / km:>8.2f}   {tag}")
    out.append(dict(subject=s, k_merge=km, k_argmax=ka, ratio=ka / km))
pathlib.Path(r"C:\dev\strehl-out\V-THESIS\kurt_levels.json").write_text(
    json.dumps(out, indent=1), encoding="utf8")

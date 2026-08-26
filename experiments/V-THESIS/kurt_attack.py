"""Attacking the invented-structure statistic with the test that killed two of
BUILD-THESIS's own candidates: DOES IT RISE ON BLUR?

If gradient kurtosis in flat regions moves with sharpness, then "argmax has
2-4x the kurtosis" may be re-reading "argmax is sharper" rather than "argmax
invents structure", and the README table is an artifact.

Also sweeps the flat-mask fraction, which was chosen at 0.35 and never varied.
"""
import json, pathlib, sys
import numpy as np, tifffile

sys.path.insert(0, str(pathlib.Path("experiments/V-THESIS").resolve()))
from vplant import gauss_exact  # noqa: E402

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
GREEN = 1
SUBJECTS = ["bee-3-cpl", "bee-1-cpl", "tweezers-cpl", "flowers-cpl",
            "leaf-2-cpl", "flat-on-ruler-cpl"]


def gkurt(a, frac=0.35):
    """Kurtosis of the gradient magnitude inside the flattest `frac` of tiles."""
    gy, gx = np.gradient(a)
    g = np.hypot(gx, gy)
    B = 64
    h, w = a.shape
    hh, ww = (h // B) * B, (w // B) * B
    blocks = a[:hh, :ww].reshape(hh // B, B, ww // B, B).std(axis=(1, 3))
    thr = np.quantile(blocks, frac)
    mask = np.repeat(np.repeat(blocks <= thr, B, 0), B, 1)
    v = g[:hh, :ww][mask]
    if v.size < 1000:
        return float("nan")
    v = v - v.mean()
    s = v.std()
    return float(np.mean(v ** 4) / (s ** 4 + 1e-30))


print("=" * 74)
print("K5  BLUR PLANT: does the statistic rise on blur? (the disqualifying test)")
print("=" * 74)
a = tifffile.imread(str(R / "bee-3-cpl" / "merge.tif"))[:, :, GREEN].astype(np.float64)
tile = a[2000:4048, 2000:4048]
base = gkurt(tile)
print(f"{'planted blur':<16}{'kurtosis':>12}{'ratio vs sharp':>18}")
k5 = []
for s in (0.0, 0.5, 1.0, 2.0, 4.0):
    v = gkurt(gauss_exact(tile, s) if s > 0 else tile)
    k5.append((s, v, v / base))
    print(f"{s:<16.1f}{v:>12.3f}{v / base:>18.3f}x")
rise = max(r for _, _, r in k5)
print(f"\n-> blurring by up to 4 px moves it {min(r for _,_,r in k5):.3f}x to {rise:.3f}x")
print("   (BUILD-THESIS disqualified its own candidates for rising 1.39x, 5.1x, 12.6x on blur)")

print("\n" + "=" * 74)
print("K6  FLAT-MASK FRACTION SWEEP: is 0.35 load-bearing?")
print("=" * 74)
print(f"{'subject':<20}" + "".join(f"{f:>10.2f}" for f in (0.10, 0.20, 0.35, 0.50, 0.70)))
out = []
for s in SUBJECTS:
    m = tifffile.imread(str(R / s / "merge.tif"))[:, :, GREEN].astype(np.float64)
    g = tifffile.imread(str(R / s / "argmax.tif"))[:, :, GREEN].astype(np.float64)
    row, rec = f"{s:<20}", {"subject": s}
    for f in (0.10, 0.20, 0.35, 0.50, 0.70):
        r = gkurt(g, f) / gkurt(m, f)
        row += f"{r:>10.2f}"
        rec[str(f)] = float(r)
    out.append(rec)
    print(row)
print("\n(argmax kurtosis / merge kurtosis; >1 = selection has the heavier tail)")
pathlib.Path(r"C:\dev\strehl-out\V-THESIS\kurt_attack.json").write_text(
    json.dumps(dict(blur_plant=k5, mask_sweep=out), indent=1), encoding="utf8")

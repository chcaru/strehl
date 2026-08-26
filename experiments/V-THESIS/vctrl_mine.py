"""Their chain reports -0.32/-0.36/-0.35 px on flat-on-ruler's geometry with ZERO
blur planted -- the same signature as their published finding #2.

My own instrument reported -0.329 px on the real flat-on-ruler-cpl (p=0.011, my
only significant subject). So I must run MY instrument on the SAME control. If
it also reads about -0.33, my result is the same artifact and I must say so.

Uses my real site machinery from vmeasure.py, not a simplified grid.
"""
import json, pathlib, sys
import numpy as np, tifffile

sys.path.insert(0, str(pathlib.Path("experiments/V-THESIS").resolve()))
from vstat import va_blur_px  # noqa: E402

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
GREEN, TILE = 1, 512


def green(p):
    return tifffile.imread(str(p))[:, :, GREEN].astype(np.float64)


def run(tag, s, truth):
    m, a = green(R / tag / "merge.tif"), green(R / tag / "argmax.tif")
    h, w = m.shape
    cy, cx = h / 2.0, w / 2.0
    Ta = int(round(TILE * s))
    vals = []
    step = TILE
    for gy in range(TILE, h - 2 * TILE, step):
        for gx in range(TILE, w - 2 * TILE, step):
            tm = m[gy:gy + TILE, gx:gx + TILE]
            if tm.shape != (TILE, TILE) or tm.std() < 40:
                continue
            ax = int(round(s * gx + cx * (1 - s)))
            ay = int(round(s * gy + cy * (1 - s)))
            ta = a[ay:ay + Ta, ax:ax + Ta]
            if ta.shape != (Ta, Ta):
                continue
            v = va_blur_px(tm, ta, denoise=False)
            if v is not None and np.isfinite(v):
                vals.append(float(v))
    med = float(np.median(vals))
    lo, hi = np.percentile(vals, [2.5, 97.5]) if len(vals) > 3 else (np.nan, np.nan)
    print(f"{tag:<20} truth {truth:+.3f} px   V reads {med:+.3f} px  "
          f"[{lo:+.3f},{hi:+.3f}]  n={len(vals)}   error {med - truth:+.3f}")
    return dict(tag=tag, truth=truth, v=med, n=len(vals), lo=float(lo), hi=float(hi))


print("MY instrument on the flat-on-ruler-geometry controls (scale 0.9707):")
out = [run("VCTRL-r-blur0.0", 0.9707, 0.0), run("VCTRL-r-blur0.4", 0.9707, 0.4)]
print("\nMY instrument on the leaf-2-geometry controls (scale 0.9342):")
out += [run("VCTRL-s-blur0.0", 0.9342, 0.0), run("VCTRL-s-blur0.4", 0.9342, 0.4),
        run("VCTRL-s-blur0.8", 0.9342, 0.8)]

print("\n--- for reference, what each chain said about the REAL flat-on-ruler-cpl ---")
print("  BUILD-THESIS  S1 -0.475  S2 -0.438  S3 -0.377   (published as 'selection wins ~0.4 px')")
print("  V-THESIS      -0.329 px  [-0.362,-0.176]  p=0.011  (my only significant subject)")
pathlib.Path(r"C:\dev\strehl-out\V-THESIS\vctrl_mine.json").write_text(json.dumps(out, indent=1), encoding="utf8")

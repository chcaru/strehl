"""Commission contrast_ms.py, then price the fit_to_cover 1/k round trip.

Three arms, all scored with the UNMODIFIED experiments/ORCH-drift-check/contrast_ms.py:

  IDENTITY   image vs a byte-copy of itself      -> every ratio must be 1.0000.
             If it is not, the instrument is not measuring what I think.
  ROUNDTRIP  image vs zoom(zoom(x, k), 1/k)      -> the fit_to_cover cost.
  BLUR       image vs gaussian(x, 0.5)           -> positive control: band-1 EDGE
             must fall clearly while the coarsest band barely moves, proving the
             instrument can SEE a fine-scale loss and that the null is specific
             rather than merely quiet.

A null that is quiet on everything is not a null, it is a broken probe.
"""
import subprocess, sys, os
import numpy as np, tifffile
from scipy.ndimage import zoom, gaussian_filter

SRC = r"C:\dev\strehl-out\V-DILUTE\runs\A_n63_default.tif"
OUT = r"C:\dev\strehl-out\V-REVIEW\resample"
MS  = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check\contrast_ms.py"
K   = 0.9208   # bee-3-cpl N=63, read from A_n63_default.log

os.makedirs(OUT, exist_ok=True)
a = tifffile.imread(SRC)
print(f"source {SRC}\n  shape {a.shape} dtype {a.dtype}")

def fit(x, shape):
    y = np.zeros(shape, dtype=x.dtype)
    h = min(x.shape[0], shape[0]); w = min(x.shape[1], shape[1])
    y[:h, :w] = x[:h, :w]
    return y

def save(tag, arr):
    p = os.path.join(OUT, tag + ".tif")
    tifffile.imwrite(p, arr.astype(np.uint16))
    return p

paths = {}
paths["identity"] = save("identity", a)

f = a.astype(np.float32)
small = zoom(f, (K, K, 1), order=3, prefilter=True)
back  = zoom(small, (a.shape[0] / small.shape[0], a.shape[1] / small.shape[1], 1),
             order=3, prefilter=True)
paths["roundtrip"] = save("roundtrip", fit(np.clip(back, 0, 65535), a.shape))
print(f"  round trip: {a.shape[:2]} -> {small.shape[:2]} -> {back.shape[:2]}  (k={K})")

blur = np.stack([gaussian_filter(f[..., c], 0.5) for c in range(3)], axis=-1)
paths["blur0.5"] = save("blur0p5", np.clip(blur, 0, 65535))

for tag in ("identity", "roundtrip", "blur0.5"):
    print("\n" + "=" * 78)
    print(f"### {tag.upper()}   A = original, B = {tag}")
    print("=" * 78)
    r = subprocess.run([sys.executable, MS, SRC, paths[tag]],
                       capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stdout.write(r.stderr[-800:])

for p in paths.values():
    try: os.remove(p)
    except OSError: pass

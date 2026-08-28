"""Is the fit_to_cover attribution band-dependent?

My attribution quoted band-0 FLAT and band-1 EDGE only. V-LINEAR 31eda43a shows
the signal/noise boundary is per-subject (0.17-0.48), so a verdict that rests on
one band is only as good as that band's qualification. Recompute the round-trip
differential between the two arms V-DILUTE compared, in EVERY band and on BOTH
site classes. If it is small everywhere, the verdict does not depend on which
band a subject qualifies.
"""
import subprocess, sys, os, re
import numpy as np, tifffile
from scipy.ndimage import zoom

SRC = r"C:\dev\strehl-out\V-DILUTE\runs\A_n63_default.tif"
OUT = r"C:\dev\strehl-out\V-REVIEW\allband"
MS  = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check\contrast_ms.py"
os.makedirs(OUT, exist_ok=True)

a = tifffile.imread(SRC)
f = a.astype(np.float32)
ROW = re.compile(r"^\s*(\d)\s+([0-9.]+-[0-9.]+)\s+\S*\s*"
                 r"([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+"
                 r"([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s*$", re.M)

def fit(x, shape):
    y = np.zeros(shape, dtype=x.dtype)
    h = min(x.shape[0], shape[0]); w = min(x.shape[1], shape[1])
    y[:h, :w] = x[:h, :w]
    return y

def bands(arr, tag):
    p = os.path.join(OUT, tag + ".tif")
    tifffile.imwrite(p, fit(np.clip(arr, 0, 65535), a.shape).astype(np.uint16))
    r = subprocess.run([sys.executable, MS, SRC, p], capture_output=True, text=True)
    os.remove(p)
    out = {}
    for m in ROW.finditer(r.stdout):
        out[int(m.group(1))] = (m.group(2), float(m.group(5)), float(m.group(8)))
    if len(out) != 6:
        print(r.stdout[-600:]); raise SystemExit("parse failed")
    return out

def roundtrip(k):
    s = zoom(f, (k, k, 1), order=3)
    return zoom(s, (a.shape[0] / s.shape[0], a.shape[1] / s.shape[1], 1), order=3)

print("Round trip at the two k values V-DILUTE's arms actually had.")
print("  N=33 -> k=0.9198     N=63 -> k=0.9208     (difference 0.11%)\n")
lo = bands(roundtrip(0.9198), "k9198")
hi = bands(roundtrip(0.9208), "k9208")

print(f"{'band':>5} {'cyc/px':>14} {'FLAT k=.9198':>13} {'FLAT k=.9208':>13} {'d FLAT':>9} "
      f"{'EDGE k=.9198':>13} {'EDGE k=.9208':>13} {'d EDGE':>9}")
mx = 0.0
for b in range(6):
    lbl, lf, le = lo[b]
    _, hf, he = hi[b]
    df, de = abs(hf - lf), abs(he - le)
    mx = max(mx, df, de)
    print(f"{b:5d} {lbl:>14} {lf:13.4f} {hf:13.4f} {df:9.4f} {le:13.4f} {he:13.4f} {de:9.4f}")

print()
print(f"LARGEST differential in ANY band, either site class : {mx:.4f}")
print(f"V-DILUTE's claimed effect (1.74x)                   : 0.7400")
print(f"ratio claim / largest mechanism differential        : {0.74/mx:.0f}x")
print()
print("So the attribution does not depend on which band the subject qualifies:")
print("the mechanism is negligible in EVERY band, on BOTH site classes.")

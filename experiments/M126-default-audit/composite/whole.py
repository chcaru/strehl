"""M126: whole-image reconciliation + level-shift check.

Reconciles my crop-scale A-vs-B magnitude against ORCH's stated whole-image
figures for 109MSDCF (97.359% of samples differ, peak 21.1% of full scale,
rms 0.41%). Also reports per-arm mean level, because --photometric changes
normalisation and a level shift would confound a visual comparison.
"""
import sys, os, json
import numpy as np
import tifffile  # hard import -- no PIL fallback

TAG = sys.argv[1] if len(sys.argv) > 1 else "109MSDCF"
ARMS = sys.argv[2].split(",") if len(sys.argv) > 2 else ["A", "B", "E", "D0", "D"]
ROOT = rf"C:\dev\strehl-out\M126-COMPOSITE\{TAG}"
FS = 65535.0


def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p}: dtype {a.dtype}, expected uint16"
    return a


base = load(rf"{ROOT}\lin\A.tif").astype(np.float32)
print(f"{'arm':4s} {'mean DN':>10s} {'vs A: %diff':>12s} {'rms %FS':>9s} {'peak %FS':>9s}")
rows = []
for arm in ARMS:
    p = rf"{ROOT}\lin\{arm}.tif"
    if not os.path.exists(p):
        print(f"{arm:4s}  MISSING")
        continue
    a = load(p).astype(np.float32)
    d = a - base
    r = dict(arm=arm, mean=float(a.mean()),
             pct=float((d != 0).mean() * 100),
             rms=float(np.sqrt((d ** 2).mean()) / FS * 100),
             peak=float(np.abs(d).max() / FS * 100))
    rows.append(r)
    print(f"{arm:4s} {r['mean']:10.1f} {r['pct']:12.3f} {r['rms']:9.4f} {r['peak']:9.3f}")
json.dump(rows, open(rf"{ROOT}\whole.json", "w"), indent=1)

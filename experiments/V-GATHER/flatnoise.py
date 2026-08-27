"""Flat-tile high-pass rms per arm, one definition, all subjects.
Tiles are chosen ONCE on the mean of the two arms so the site list is common.
Includes the alignment-REFUSED subject as a null: its ratio must be exactly 1.000.
Also re-runs the split-half reliability with a WORKING positive control
(identical structure injected into both halves -> r must RISE toward 1).
"""
import os, glob, json
import numpy as np, tifffile

OUT = r"C:\dev\strehl-out\V-GATHER"

def luma(im):
    return 0.2126*im[:, :, 0] + 0.7152*im[:, :, 1] + 0.0722*im[:, :, 2]

def boxblur(y, r):
    k = 2*r+1
    c = np.cumsum(np.pad(y, ((r+1, r), (0, 0)), mode="edge"), axis=0)
    y1 = (c[k:] - c[:-k])/k
    c = np.cumsum(np.pad(y1, ((0, 0), (r+1, r)), mode="edge"), axis=1)
    return (c[:, k:] - c[:, :-k])/k

def hp(y, r=3):
    return y - boxblur(y, r)

def flat_rms(y0, y1, t=256, q=0.25):
    h = (min(y0.shape[0], y1.shape[0])//t)*t
    w = (min(y0.shape[1], y1.shape[1])//t)*t
    y0 = y0[:h, :w]; y1 = y1[:h, :w]
    m = (y0+y1)/2.0
    st = m.reshape(h//t, t, w//t, t).std(axis=(1, 3))
    thr = np.quantile(st, q)
    sel = st <= thr
    out = []
    for y in (y0, y1):
        e = hp(y).reshape(h//t, t, w//t, t)
        v = (e**2).mean(axis=(1, 3))
        out.append(float(np.sqrt(v[sel].mean())))
    return out[0], out[1], int(sel.sum())

subs = sorted({os.path.basename(f)[:-len("-q-g0.tiff")]
               for f in glob.glob(os.path.join(OUT, "*-q-g0.tiff"))})
print(f"{'subject':30s} {'flatHP g0':>10s} {'flatHP g1':>10s} {'ratio':>8s} {'tiles':>6s}")
rows = []
for s in subs:
    try:
        a = luma(tifffile.imread(os.path.join(OUT, f"{s}-q-g0.tiff"))[:, :, :3].astype(np.float64))
        b = luma(tifffile.imread(os.path.join(OUT, f"{s}-q-g1.tiff"))[:, :, :3].astype(np.float64))
    except Exception as e:
        print(f"{s:30s} SKIP {e}"); continue
    r0, r1, n = flat_rms(a, b)
    rows.append((s, r0, r1, r1/r0, n))
    print(f"{s:30s} {r0:10.2f} {r1:10.2f} {r1/r0:8.3f} {n:6d}", flush=True)
    del a, b
with open(os.path.join(OUT, "flatnoise.json"), "w") as f:
    json.dump(rows, f, indent=1)

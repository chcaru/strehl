"""Three-way: SINGLE FRAME (the physical floor) vs BEFORE vs AFTER, same tiles.

Why a single frame is the right reference, and it is two bounds at once:
  * It is ONE real exposure with NO election and NO averaging, so its noise is
    the sensor's actual floor in this exact domain (same demosaic, same scale).
    Nothing built by combining real frames can legitimately be NOISIER.
  * It already contains every bit of scene detail any merge could recover, so
    it also bounds how much real structure is available to be "recovered".
Therefore an arm sitting ABOVE the single-frame floor is adding energy that is
in neither the sensor nor the scene.
"""
import sys
import numpy as np
import tifffile
from noisefloor import tiles, sigma_std, immerkaer

def green(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"expected uint16, got {a.dtype}"
    return a[:, :, 1].astype(np.float32)

def coarse(t, ds=8):
    n = t.shape[0]; b = t.shape[1]//ds
    return sigma_std(t.reshape(n, b, ds, b, ds).mean(axis=(2, 4)).astype(np.float32))

def stats(p):
    g = green(p); t = tiles(g)
    o = dict(mean=t.mean(axis=(1, 2)), std=sigma_std(t), hf=immerkaer(t), coarse=coarse(t))
    del g, t
    return o

if __name__ == "__main__":
    K = 10.0
    names, paths = [], []
    for a in sys.argv[1:]:
        n, p = a.split("=", 1); names.append(n); paths.append(p)
    S = [stats(p) for p in paths]
    for n, p in zip(names, paths): print(f"{n:>8} = {p}")
    sel = np.mean([s["coarse"] for s in S], axis=0)      # selector belongs to no single arm
    msig = np.mean([s["mean"] for s in S], axis=0)
    edges = np.array([200, 500, 1000, 2000, 4000, 8000, 16000, 32000, 65536])
    print(f"\nselector: mean coarse structure across ALL {len(S)} images; flattest {K:.0f}% per bin")
    hdr = "   signal bin      ntile |" + "".join(f"{n:>12}" for n in names) + " |" + \
          "".join(f"{n+'/'+names[0]:>14}" for n in names[1:])
    print(hdr)
    acc = []
    for i in range(len(edges)-1):
        m = (msig >= edges[i]) & (msig < edges[i+1])
        if m.sum() < 20: continue
        idx = np.where(m)[0]
        keep = idx[sel[idx] <= np.percentile(sel[idx], K)]
        if keep.size < 8: continue
        v = [float(np.median(s["std"][keep])) for s in S]
        acc.append((keep.size, v))
        print(f"  {edges[i]:6d}-{edges[i+1]:6d}  {keep.size:6d} |" +
              "".join(f"{x:12.3f}" for x in v) + " |" +
              "".join(f"{x/v[0]:14.3f}" for x in v[1:]))
    if acc:
        w = np.array([a[0] for a in acc], float)
        v = [float(np.sum(w*np.array([a[1][j] for a in acc]))/w.sum()) for j in range(len(S))]
        print(f"  {'WEIGHTED':>13}  {int(w.sum()):6d} |" + "".join(f"{x:12.3f}" for x in v) +
              " |" + "".join(f"{x/v[0]:14.3f}" for x in v[1:]))
        print()
        for j in range(1, len(S)):
            r = v[j]/v[0]
            verdict = ("BELOW the single-frame floor -- consistent with averaging/smoothing"
                       if r < 0.95 else
                       "ABOVE the single-frame floor -- energy not in the sensor or the scene"
                       if r > 1.05 else "AT the single-frame floor")
            print(f"  {names[j]:>8} / {names[0]}: {r:.3f}   {verdict}")

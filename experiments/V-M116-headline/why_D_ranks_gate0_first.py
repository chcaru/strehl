"""V-M116 probe 9: the mechanism. D counts noise as detail."""
from pathlib import Path
import numpy as np, tifffile
M = Path(r"C:\dev\strehl-out\M116\measure")
def lg(p):
    a = tifffile.imread(p); assert a.dtype == np.uint16, f"{p} {a.dtype}"
    return a[:, :, 1].astype(np.float64)
def box(a, k):
    h = k // 2
    pad = np.pad(a, ((h, k-1-h), (h, k-1-h)), mode="edge")
    c = np.pad(pad.cumsum(0).cumsum(1), ((1,0),(1,0)))
    return (c[k:,k:]-c[:-k,k:]-c[k:,:-k]+c[:-k,:-k])/(k*k)
def structure(g):
    hh, ww = g.shape[0]//4, g.shape[1]//4
    s = g[:hh*4,:ww*4].reshape(hh,4,ww,4).mean(axis=(1,3))
    sd = np.sqrt(np.maximum(box(s*s,33)-box(s,33)**2, 0))
    up = np.repeat(np.repeat(sd,4,0),4,1)
    o = np.zeros(g.shape); o[:up.shape[0],:up.shape[1]] = up[:g.shape[0],:g.shape[1]]
    if up.shape[0] < g.shape[0]: o[up.shape[0]:,:] = o[up.shape[0]-1,:]
    if up.shape[1] < g.shape[1]: o[:,up.shape[1]:] = o[:,up.shape[1]-1][:,None]
    return o
for s in ["bee-3-cpl", "foam", "tweezers-cpl"]:
    g = {a: lg(M/f"{s}__{a}.tif") for a in ("B0","B1u","M0u")}
    st = structure(g["B0"])                      # mask from B0: independent of both merges
    mf, md = st <= np.quantile(st,.20), st >= np.quantile(st,.80)
    print(f"\n=== {s} ===  (masks from B0, independent of both merge arms)")
    print(f"  {'arm':5s} {'N (flat band)':>14s} {'D (detail band)':>16s} {'Q = D-N':>10s}")
    for a in ("B0","M0u","B1u"):
        h = g[a] - box(g[a],5)
        N, D = np.log10(h[mf].std()), np.log10(h[md].std())
        print(f"  {a:5s} {N:14.5f} {D:16.5f} {D-N:10.5f}")
    print("  M0u is --gate 0 (pure selection), the arm M116 P10 calls 'gross visible patchwork'.")

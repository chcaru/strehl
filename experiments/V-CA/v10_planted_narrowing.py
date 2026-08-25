"""V-CA v10 -- plant ORCH's narrowing and re-run every V-CA statistic through it.

ORCH's refinement says a ratio of two arms is largely protected by cancellation
(-1.0 pct under a planted narrowing) while absolute quantities are destroyed,
and small-over-large ratios compress toward a null.  That was measured on one
milestone's statistics.  This is a second, independent instrument: the same
plant applied to the CA statistics this audit actually reported.

The plant reproduces what PIL does -- keep the high byte -- without going
through PIL, so the arms stay aligned and only the narrowing changes.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import tifffile

ROOT = Path(r"C:\dev\strehl-out\M110-sheet")


def narrow(a):
    """What PIL hands back for a 16-bit RGB TIFF, in the original units."""
    return ((a.astype(np.uint16) >> 8).astype(np.float32)) * 257.0


def chroma(f):
    return np.abs(f[..., 0] - (0.2126*f[..., 0] + 0.7152*f[..., 1] + 0.0722*f[..., 2]))


def bands(off):
    y = 0.2126*off[..., 0] + 0.7152*off[..., 1] + 0.0722*off[..., 2]
    gy = np.zeros_like(y); gx = np.zeros_like(y)
    gy[1:-1, :] = np.abs(y[2:, :] - y[:-2, :]); gx[:, 1:-1] = np.abs(y[:, 2:] - y[:, :-2])
    g = gy + gx
    seed = g >= float(np.percentile(g[::7, ::7], 98.0))
    band = np.full(seed.shape, 255, np.uint8); cur = seed.copy(); band[cur] = 0
    for k in range(1, 6):
        nxt = cur.copy()
        nxt[1:, :] |= cur[:-1, :]; nxt[:-1, :] |= cur[1:, :]
        nxt[:, 1:] |= cur[:, :-1]; nxt[:, :-1] |= cur[:, 1:]
        band[nxt & ~cur] = k; cur = nxt
    return band


def stats(off, on, band):
    co, cn = chroma(off), chroma(on)
    b0o, b0n = co[band == 0].mean(), cn[band == 0].mean()
    b5o, b5n = co[band == 5].mean(), cn[band == 5].mean()
    d = {}
    d["excess fall % (the headline)"] = 100*(1 - (b0n-b5n)/(b0o-b5o))
    d["band-0 raw change %"] = 100*(b0n/b0o - 1)
    d["whole-frame change % (small/large)"] = 100*(cn.mean()/co.mean() - 1)
    dr = np.abs(on[..., 0]-off[..., 0]); dg = np.abs(on[..., 1]-off[..., 1])
    d["mean |dG| DN  (ABSOLUTE)"] = float(dg.mean())
    d["mean |dR| DN  (ABSOLUTE)"] = float(dr.mean())
    d["|dG|/|dR| (small/large)"] = float(dg.mean()/dr.mean())
    d["% px green changed (ABSOLUTE)"] = 100*float((dg > 0).mean())
    return d


for sub, offn, onn, lab in [("bee-3-cpl", "default.tif", "ca.tif", "sRGB"),
                            ("bee-3-cpl", "lind-default.tif", "lind-ca.tif", "LINEAR")]:
    off = tifffile.imread(str(ROOT / sub / offn))
    on = tifffile.imread(str(ROOT / sub / onn))
    lo, hi = int(min(off.min(), on.min())), int(max(off.max(), on.max()))
    print(f"\n===== {sub} {lab}   occupied range {lo}..{hi} "
          f"=> {max(1,(hi-lo)//257)} levels survive narrowing =====")
    t = stats(off.astype(np.float32), on.astype(np.float32), bands(off.astype(np.float32)))
    nf, nn = narrow(off), narrow(on)
    p = stats(nf, nn, bands(nf))
    print(f"  {'statistic':<38}{'truth':>12}{'narrowed':>12}{'error':>12}")
    for k in t:
        e = p[k]-t[k] if abs(t[k]) < 1e-9 else 100*(p[k]/t[k]-1)
        u = "pp" if abs(t[k]) < 1e-9 else "%"
        print(f"  {k:<38}{t[k]:12.3f}{p[k]:12.3f}{e:11.1f}{u}")

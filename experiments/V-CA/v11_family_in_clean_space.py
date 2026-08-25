"""V-CA v11 -- re-derive the WHOLE family of CA numbers in binned-linear space.

ORCH published -29.4 / -20.5 / -4.9 in the owner's brief.  All five members of
the family were measured in --srgb, whose own --help says "For looking at, NOT
for measuring" and which M113 measured as cross-channel contaminated.  This
re-derives every member from the lin-*.tif renders -- binned, linear, camera
native, NO demosaic (R/G/B co-sited in a Bayer quad), NO colour matrix, NO gamma.

Same stencil and same edge DEFINITION as v1_band_sensitivity.py.  Two scale
caveats, stated rather than hidden:

  * lin-*.tif is 2344x3516, exactly half of 4688x7032: one binned pixel is two
    sensels.  A band index is therefore NOT comparable term-by-term between the
    spaces -- binned band 5 is 10 sensels out, where sRGB band 5 is 5.  The
    excess is reported at matched INDEX (K=5) and at matched PHYSICAL distance
    (K=2, K=3) so the comparison can be read either way.
  * Percentile-defined populations (top 2 % gradient seed, top-decile gradient,
    chroma deciles) are scale-relative and ARE comparable.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import tifffile

ROOT = Path(r"C:\dev\strehl-out\M110-sheet")


def load(p: Path) -> np.ndarray:
    a = tifffile.imread(str(p))
    assert a.dtype == np.uint16, f"{p.name}: expected uint16, got {a.dtype}"
    assert a.ndim == 3 and a.shape[2] == 3, f"{p.name}: expected HxWx3, got {a.shape}"
    return a.astype(np.float32)


def luma(f):
    return 0.2126*f[..., 0] + 0.7152*f[..., 1] + 0.0722*f[..., 2]


def chroma(f):
    return np.abs(f[..., 0] - luma(f))


def grad(f):
    y = luma(f)
    gy = np.zeros_like(y); gx = np.zeros_like(y)
    gy[1:-1, :] = np.abs(y[2:, :] - y[:-2, :])
    gx[:, 1:-1] = np.abs(y[:, 2:] - y[:, :-2])
    return gy + gx


def bandmap(g, pct=98.0, kmax=10):
    seed = g >= float(np.percentile(g[::7, ::7], pct))
    band = np.full(seed.shape, 255, np.uint8)
    cur = seed.copy(); band[cur] = 0
    for k in range(1, kmax+1):
        nxt = cur.copy()
        nxt[1:, :] |= cur[:-1, :]; nxt[:-1, :] |= cur[1:, :]
        nxt[:, 1:] |= cur[:, :-1]; nxt[:, :-1] |= cur[:, 1:]
        band[nxt & ~cur] = k; cur = nxt
    return band


def family(off, on):
    co, cn = chroma(off), chroma(on)
    g = grad(off)                       # selection on the OFF arm only
    band = bandmap(g)
    out = {}
    out["whole-frame mean |R-Y|"] = 100*(cn.mean()/co.mean() - 1)
    dec = g >= float(np.percentile(g[::7, ::7], 90.0))
    out["near-edge (top-decile grad)"] = 100*(cn[dec].mean()/co[dec].mean() - 1)
    b0 = band == 0
    out["raw edge chroma (band 0)"] = 100*(cn[b0].mean()/co[b0].mean() - 1)
    hi = co >= float(np.percentile(co[::7, ::7], 90.0))
    out["decile-10 of |R-Y| (M110)"] = 100*(cn[hi].mean()/co[hi].mean() - 1)
    prof = {k: (co[band == k].mean(), cn[band == k].mean()) for k in range(11)}
    for K in (2, 3, 5):
        eo = prof[0][0]-prof[K][0]; en = prof[0][1]-prof[K][1]
        out[f"edge-localised EXCESS K={K}"] = -100*(1 - en/eo)
    return out, prof


def run(subject):
    have_srgb = (ROOT / subject / "default.tif").exists()
    print(f"\n{'='*78}\n{subject}\n{'='*78}")
    res = {}
    if have_srgb:
        o, n = load(ROOT/subject/"default.tif"), load(ROOT/subject/"ca.tif")
        print(f"  sRGB   {o.shape}")
        res["sRGB"], ps = family(o, n)
        del o, n
    o, n = load(ROOT/subject/"lin-default.tif"), load(ROOT/subject/"lin-ca.tif")
    print(f"  LINEAR {o.shape}  (binned: 1 px = 2 sensels)")
    res["binned-linear"], pl = family(o, n)
    del o, n

    keys = list(res["binned-linear"].keys())
    print(f"\n  {'family member':<32}{'sRGB':>12}{'binned-linear':>16}{'shift':>10}")
    for k in keys:
        a = res.get("sRGB", {}).get(k)
        b = res["binned-linear"][k]
        if a is None:
            print(f"  {k:<32}{'--':>12}{b:15.2f}%{'--':>10}")
        else:
            print(f"  {k:<32}{a:11.2f}%{b:15.2f}%{b-a:9.2f}pp")
    print("\n  band profile (binned-linear), mean |R-Y| off -> on:")
    for k in range(0, 7):
        a, b = pl[k]
        print(f"    band {k:2d} ({2*k:2d} sensels)  {a:9.2f} -> {b:9.2f}   {100*(b/a-1):+7.2f}%")


if __name__ == "__main__":
    for s in ("bee-3-cpl", "wrapped-text-1"):
        run(s)

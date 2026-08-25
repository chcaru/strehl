"""V-M116 probe 8: does the headline statistic have the power to support the
sentence built on it?

The sentence is "the default path is not what's wrong". The number is
D(merge) - D(best single frame). If a merge the report ITSELF calls grossly
defective scores the same number, the number cannot support the sentence.

M0u is `--gate 0`, pure per-pixel selection. M116 P10 calls it "gross visible
patchwork ... the largest quality difference visible anywhere in this campaign".
It is exactly the thing the shipped gate is supposed to fix.

To avoid the circularity M116 correctly refused (scoring M0u against masks
derived from M0u), every mask here comes from an arm OTHER than the one being
scored. Masks from B0 disadvantage every merge; masks from B1u disadvantage M0u
least. Both are reported.
"""
from pathlib import Path
import numpy as np
import tifffile

M = Path(r"C:\dev\strehl-out\M116\measure")
SUBJECTS = ["bee-3-cpl", "foam", "tweezers-cpl"]


def load_green(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p} loaded as {a.dtype}, NOT uint16"
    return a[:, :, 1].astype(np.float64)


def box(a, k):
    h = k // 2
    pad = np.pad(a, ((h, k - 1 - h), (h, k - 1 - h)), mode="edge")
    c = np.pad(pad.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def structure(g):
    hh, ww = g.shape[0] // 4, g.shape[1] // 4
    small = g[:hh * 4, :ww * 4].reshape(hh, 4, ww, 4).mean(axis=(1, 3))
    m1, m2 = box(small, 33), box(small * small, 33)
    sd = np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
    up = np.repeat(np.repeat(sd, 4, 0), 4, 1)
    out = np.zeros(g.shape, np.float64)
    out[:up.shape[0], :up.shape[1]] = up[:g.shape[0], :g.shape[1]]
    if up.shape[0] < g.shape[0]: out[up.shape[0]:, :] = out[up.shape[0] - 1, :]
    if up.shape[1] < g.shape[1]: out[:, up.shape[1]:] = out[:, up.shape[1] - 1][:, None]
    return out


for s in SUBJECTS:
    print(f"\n=== {s} ===")
    g = {a: load_green(M / f"{s}__{a}.tif") for a in ("B0", "B1u", "M0u")}
    hp = {a: v - box(v, 5) for a, v in g.items()}
    for msrc in ("B0", "B1u", "M0u"):
        st = structure(g[msrc])
        mf = st <= np.quantile(st, 0.20)
        md = st >= np.quantile(st, 0.80)
        D = {a: np.log10(hp[a][md].std()) for a in hp}
        N = {a: np.log10(hp[a][mf].std()) for a in hp}
        note = "  <-- CIRCULAR for the arm it came from" if msrc != "B0" else ""
        print(f"  masks from {msrc:4s}: "
              f"dD(B1u-B0) {D['B1u']-D['B0']:+.5f}   "
              f"dD(M0u-B0) {D['M0u']-D['B0']:+.5f}   "
              f"dD(B1u-M0u) {D['B1u']-D['M0u']:+.5f}{note}")
        print(f"  {'':16s}dQ(B1u-B0) {(D['B1u']-N['B1u'])-(D['B0']-N['B0']):+.5f}   "
              f"dQ(M0u-B0) {(D['M0u']-N['M0u'])-(D['B0']-N['B0']):+.5f}")

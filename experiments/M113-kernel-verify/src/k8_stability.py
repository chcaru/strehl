"""M113 K8 - how STABLE is the end-to-end dex number, and where does it live?

K7 turned up something that has to be reported: on the same two files, the same
metric returns +0.0181 dex (256 px tiles, whole frame), +0.0081 (128 px, whole
frame), +0.0299 (64 px, whole frame) and +0.0830 (256 px, central-half lattice).
A quantity published to four decimals as +0.1343 is not stable to four decimals,
so this measures the spread instead of picking a favourite.

Three things:
  G  a GLOBAL, TILE-FREE reading: one FFT over the whole plane-grid image. No
     tiling choice exists, so no tiling choice can be made to flatter.
  L  the tile-size x region ladder, reported in full rather than best-of.
  S  the gain stratified by whether the ELECTION agreed, on the pre-registered
     117-tile central-half lattice, at the tile size that yields a usable n.
"""
import json
import os
import sys

import numpy as np
import tifffile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "experiments", "M95-resample", "src"))
import x2_pairs as X  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
R2 = r"C:\dev\strehl-out\M113\render2"


def luma(p):
    a = tifffile.imread(p).astype(np.float32)
    return 0.25 * a[..., 0] + 0.50 * a[..., 1] + 0.25 * a[..., 2]


def global_band(img):
    """band_ratio's definition, applied ONCE to the whole image. Non-square, so
    the radial frequency is built from each axis's own fftfreq -- identical
    convention, no tiling."""
    t = img.astype(np.float64)
    t = t - t.mean()
    wy = np.hanning(t.shape[0])[:, None]
    wx = np.hanning(t.shape[1])[None, :]
    f = np.fft.fft2(t * wy * wx)
    p = (f.real ** 2 + f.imag ** 2) / t.size
    fr = np.hypot(np.fft.fftfreq(t.shape[0])[:, None], np.fft.fftfreq(t.shape[1])[None, :])
    hi = (fr >= 0.30) & (fr < 0.48)
    lo = (fr >= 0.02) & (fr < 0.10)
    return float(np.log10(p[hi].mean()) - np.log10(p[lo].mean()))


def main():
    cr = luma(os.path.join(R2, "lin-cr.tif"))
    l3 = luma(os.path.join(R2, "lin-l3.tif"))
    res = {}

    print("=" * 78)
    print("G. GLOBAL, TILE-FREE (one FFT over the whole image; no tiling choice exists)")
    h, w = cr.shape
    crb = cr[:h // 2 * 2, :w // 2 * 2].reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))
    l3b = l3[:h // 2 * 2, :w // 2 * 2].reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))
    for lab, a, b in (("plane grid (2x2 binned, the grid the KERNEL acts on)", crb, l3b),):
        ga, gb = global_band(a), global_band(b)
        print(f"   {lab}")
        print(f"     catmull-rom {ga:+.4f}   lanczos3 {gb:+.4f}   GAIN {gb-ga:+.4f} dex")
        res["global_plane"] = dict(cr=ga, l3=gb, gain=gb - ga)

    print("\n" + "=" * 78)
    print("L. TILE-SIZE x REGION LADDER (all of it, not the best of it)")
    print(f"   {'region':16s} {'tile':>6s} {'n':>6s} {'gain dex':>10s} {'sem':>8s}")
    lad = {}
    for rlab, y0, y1, x0, x1 in (("whole frame", 0, h, 0, w),
                                 ("central half", h // 4, 3 * h // 4, w // 4, 3 * w // 4)):
        for T in (64, 128, 256, 512):
            ts = [(y, x) for y in range(y0, y1 - T + 1, T) for x in range(x0, x1 - T + 1, T)]
            if len(ts) < 4:
                continue
            d = np.array([X.band_ratio(l3[y:y + T, x:x + T], 1.0)
                          - X.band_ratio(cr[y:y + T, x:x + T], 1.0) for y, x in ts])
            s = float(d.std(ddof=1) / np.sqrt(d.size))
            lad[f"{rlab}|{T}"] = dict(n=int(d.size), mean=float(d.mean()), sem=s)
            print(f"   {rlab:16s} {T:6d} {d.size:6d} {d.mean():+10.4f} {s:8.4f}")
    v = np.array([r["mean"] for r in lad.values()])
    print(f"\n   SPREAD across 8 defensible tilings of the SAME PAIR OF FILES:")
    print(f"     min {v.min():+.4f}   max {v.max():+.4f}   range {v.max()-v.min():.4f} dex")
    print(f"     the claim under test is +0.1343 dex, quoted to four decimals.")
    res["ladder"] = lad
    res["ladder_spread"] = dict(min=float(v.min()), max=float(v.max()),
                                range=float(v.max() - v.min()))

    print("\n" + "=" * 78)
    print("S. STRATIFIED BY ELECTION AGREEMENT, pre-registered central-half lattice")
    ic = tifffile.imread(os.path.join(R2, "idx-cr.tif")).astype(np.int32)
    il = tifffile.imread(os.path.join(R2, "idx-l3.tif")).astype(np.int32)
    same = ic == il
    for T in (256, 128, 64):
        q = T // 2
        ts = [(y, x) for y in range(h // 4, 3 * h // 4 - T, T)
              for x in range(w // 4, 3 * w // 4 - T, T)]
        fr = np.array([float(same[y // 2:y // 2 + q, x // 2:x // 2 + q].mean()) for y, x in ts])
        d = np.array([X.band_ratio(l3[y:y + T, x:x + T], 1.0)
                      - X.band_ratio(cr[y:y + T, x:x + T], 1.0) for y, x in ts])
        print(f"\n   tile {T}px, n={len(ts)}   election agreement: "
              f"min {fr.min():.3f} median {np.median(fr):.3f} max {fr.max():.3f}")
        print(f"     {'stratum':34s} {'n':>5s} {'gain':>9s} {'sem':>8s}")
        for lab, m in (("agreement == 1.000 (kernel alone)", fr >= 1.0),
                       ("agreement >= 0.99", fr >= 0.99),
                       ("agreement >= 0.95", fr >= 0.95),
                       ("agreement <  0.95", fr < 0.95)):
            vv = d[m]
            if vv.size < 2:
                print(f"     {lab:34s} {vv.size:5d}     -- too few --")
                continue
            print(f"     {lab:34s} {vv.size:5d} {vv.mean():+9.4f} "
                  f"{vv.std(ddof=1)/np.sqrt(vv.size):8.4f}")
        if fr.size > 2:
            print(f"     corr(agreement, gain) = {np.corrcoef(fr, d)[0,1]:+.4f}")
        res[f"strat_T{T}"] = dict(n=len(ts), corr=float(np.corrcoef(fr, d)[0, 1]),
                                  gain_all=float(d.mean()))
    json.dump(res, open(os.path.join(OUT, "k8_stability.json"), "w"), indent=1)
    print(f"\nwrote {os.path.join(OUT, 'k8_stability.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

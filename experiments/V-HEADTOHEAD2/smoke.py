"""Smoke test: does h2.py load a render, parse its tone, invert it, and does
rois.py produce a partition that sums?  Prints numbers that the caller can
check by eye against the render's own log.  Nothing here is a finding."""
import sys

import numpy as np

import h2
import rois

R = r"C:\dev\strehl-out\V-H2H2\renders"
L = r"C:\dev\strehl-out\V-H2H2\logs"


def load(tag, linear=False):
    return h2.Render(rf"{R}\{tag}.tiff", log=rf"{L}\{tag}.log", name=tag,
                     linear=linear)


def main():
    a = load("113-A-g1")
    print(a)
    print(f"  dtype {a.a.dtype}  shape {a.a.shape}")

    # tone inversion must be a monotone bijection on [0,1]: forward(inverse(x))
    # must return x.  This is a numerics check, not a transcription check.
    t = a.tone
    lin = np.geomspace(1e-5, 3.0, 4000)
    lp = lin * t.gain(lin)
    back = t.inv_luma(lp)
    err = np.abs(back - lin) / np.maximum(lin, 1e-12)
    print(f"  inv_luma roundtrip: max rel err {err.max():.3e} over 1e-5..3.0")
    y = h2.s_curve(np.linspace(0, 1, 5000), t.contrast)
    x2 = h2.inv_s_curve(y, t.contrast)
    print(f"  s_curve  roundtrip: max abs err {np.abs(x2 - np.linspace(0,1,5000)).max():.3e}")

    blk = a.raw_crop(2000, 3000, 256)
    linrgb = h2.to_linear(blk, t)
    print(f"  crop u16 mean {blk.mean():.1f}  -> linear mean {linrgb.mean():.5f} "
          f"min {linrgb.min():.5f} max {linrgb.max():.5f}")

    d, f, c = rois.census(a, t=256)
    print(f"  detail[0]={d[0]} flat[0]={f[0]}")

    b = load("113-B-g1")
    ca, na = a.crop(*d[0], 256)
    cb, nb = b.crop(*d[0], 256)
    dy, dx, pk = h2.integer_shift(ca, cb)
    print(f"  A vs B integer shift on detail[0]: dy={dy} dx={dx} peak={pk:.4f}")

    fa = h2.contrast_fft(ca)
    fb = h2.contrast_fft(cb)
    m = h2.band_masks(256)
    PA, PB, C = h2.pair_bands(fa, fb, m, 256)
    print("  band        P_A        P_B        C        gamma")
    for (b0, b1), pa, pb, cc in zip(h2.BANDS, PA, PB, C):
        g = cc / np.sqrt(max(pa * pb, 1e-30))
        print(f"  {b0:.2f}-{b1:.2f}  {pa:.3e}  {pb:.3e}  {cc:+.3e}  {g:+.4f}")


if __name__ == "__main__":
    sys.exit(main())

r"""The split-half DETAIL column is the pre-declared validity control: detail
sites must correlate highly between halves, because detail is real. On
bee-2-cpl it read +0.194 where 119MSDCF read +0.983. Either the control is
broken or the two halves are not in the same geometry.

Test by FFT cross-correlation. If a single global translation restores the
correlation, the halves are merely offset and the offset can be removed. If no
translation restores it, the halves differ by scale/rotation/warp and the
split-half construction is INVALID on that subject -- in which case its
r must not be quoted.

Also reports the correlation restored at the best shift, per band, so a
band-dependent failure (fine bands broken, coarse bands fine = sub-pixel or
scale error) is distinguishable from a global one.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bandmetrics as bm                                           # noqa: E402
import nscale as ns                                                # noqa: E402

OUT = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"


def pear(a, b):
    a = a - a.mean(); b = b - b.mean()
    return float((a * b).sum() / max(np.sqrt((a * a).sum() * (b * b).sum()), 1e-30))


def best_shift(a, b, rad=24):
    """Peak of the normalised cross-correlation, via FFT, within +-rad px."""
    A = a - a.mean(); B = b - b.mean()
    F = np.fft.rfft2(A) * np.conj(np.fft.rfft2(B))
    c = np.fft.irfft2(F, s=A.shape)
    c = np.fft.fftshift(c)
    cy, cx = A.shape[0] // 2, A.shape[1] // 2
    w = c[cy - rad:cy + rad + 1, cx - rad:cx + rad + 1]
    iy, ix = np.unravel_index(np.argmax(w), w.shape)
    return iy - rad, ix - rad


for subj in sys.argv[1:]:
    e, _, _ = ns.load64(os.path.join(OUT, "%s__EVEN__A-unset.tiff" % subj))
    o, _, _ = ns.load64(os.path.join(OUT, "%s__ODD__A-unset.tiff" % subj))
    print("\n%s  shape %s" % (subj, e.shape), flush=True)
    H, W = e.shape
    m = 48
    for lbl, lo, hi in (("band0 (2-4px)", 0, 1), ("band2 (8-16px)", 2, 3),
                        ("band4 (32-64px)", 4, 5)):
        be = bm.smooth(e, bm.RADII[lo]) - bm.smooth(e, bm.RADII[hi])
        bo = bm.smooth(o, bm.RADII[lo]) - bm.smooth(o, bm.RADII[hi])
        dy, dx = best_shift(be, bo)
        r0 = pear(be[m:H - m, m:W - m], bo[m:H - m, m:W - m])
        rb = pear(be[m:H - m, m:W - m], bo[m + dy:H - m + dy, m + dx:W - m + dx])
        print("  %-16s r(0,0) = %+.4f   best r = %+.4f at dy=%+d dx=%+d"
              % (lbl, r0, rb, dy, dx), flush=True)

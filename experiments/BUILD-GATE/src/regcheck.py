"""How long is one registration, and can it be made exact-but-fast?

The ceiling build is dominated by orch_sharp1to1.register(), which evaluates
49x49 integer shifts and computes a normalised correlation over 560x560 at
each. At complete bracket depth on bee-1-cpl that is 299 frames x 3 sites = 897
registrations, and if each costs seconds the deep subjects do not finish.

An FFT cross-correlation computes the same numerator for every shift at once,
and integral images give the per-shift mean and sum-of-squares that the
denominator needs. The result is the SAME QUANTITY by algebra -- but algebra is
not the claim being tested. Floating point reassociation can move a normalised
correlation in the last bits, and if two shifts are nearly tied that can move
the argmax. So this file does not assert equivalence; it MEASURES it, on real
frames, and reports any disagreement rather than averaging it away.

A shift that disagrees is not a rounding curiosity. It would mean the fast path
and ORCH's path crop different pixels, and every downstream number would be
measured on different content.
"""
import os
import sys
import time
import glob

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "ORCH-drift-check"))

from orch_sharp1to1 import (luma, register, CROP, SEARCH, SRC_ROOT)   # noqa: E402

STEP = 2
OFF = list(range(-SEARCH, SEARCH + 1, STEP))


def register_fft(ref, mov):
    """Same argmax as orch_sharp1to1.register, computed for all shifts at once.

    numerator   sum((ref-mean_ref) * mov_window)  -- the ref mean is subtracted
                once; subtracting the window mean as well is unnecessary because
                sum((r-rbar)*(m-mbar)) == sum((r-rbar)*m) when sum(r-rbar)==0.
    denominator sqrt(sum(r'^2) * sum((m-mbar)^2)), and the window sums come from
                integral images so each is O(1) per shift.
    """
    r = ref - ref.mean()
    n = r.size
    rss = float(np.sum(r * r))
    h, w = ref.shape

    s1 = np.zeros((mov.shape[0] + 1, mov.shape[1] + 1))
    s2 = np.zeros_like(s1)
    s1[1:, 1:] = np.cumsum(np.cumsum(mov, axis=0), axis=1)
    s2[1:, 1:] = np.cumsum(np.cumsum(mov * mov, axis=0), axis=1)

    fs = [mov.shape[0] + h - 1, mov.shape[1] + w - 1]
    fa = np.fft.rfft2(mov, fs)
    fb = np.fft.rfft2(r[::-1, ::-1], fs)
    corr = np.fft.irfft2(fa * fb, fs)

    best, at = -2.0, (0, 0)
    for dy in OFF:
        y0 = SEARCH + dy
        for dx in OFF:
            x0 = SEARCH + dx
            if y0 + h > mov.shape[0] or x0 + w > mov.shape[1]:
                continue
            num = corr[y0 + h - 1, x0 + w - 1]
            tot = s1[y0 + h, x0 + w] - s1[y0, x0 + w] - s1[y0 + h, x0] + s1[y0, x0]
            sq = s2[y0 + h, x0 + w] - s2[y0, x0 + w] - s2[y0 + h, x0] + s2[y0, x0]
            mss = sq - tot * tot / n
            if mss <= 0 or rss <= 0:
                continue
            c = num / np.sqrt(rss * mss)
            if c > best:
                best, at = float(c), (dy, dx)
    return at, best


def main():
    import rawpy
    import tifffile
    subject = sys.argv[1]
    master = sys.argv[2]
    nf = int(sys.argv[3]) if len(sys.argv) > 3 else 6

    m = tifffile.imread(master)[..., :3].astype(np.float64)
    my = luma(m)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from ceiling import pick_sites
    sites, _ = pick_sites(m)
    arw = sorted(glob.glob(os.path.join(SRC_ROOT, subject, "*.ARW")))
    idx = np.linspace(0, len(arw) - 1, min(nf, len(arw))).astype(int)

    print("%-10s %-8s %14s %14s %10s %10s   %s"
          % ("frame", "site", "ORCH (dy,dx)", "FFT (dy,dx)", "ORCH corr", "FFT corr", "verdict"))
    tslow = tfast = 0.0
    nsame = ndiff = 0
    for i in idx:
        with rawpy.imread(arw[i]) as r:
            s = r.postprocess(gamma=(2.222, 4.5), no_auto_bright=True,
                              use_camera_wb=True, output_bps=16)
        sy = luma(s.astype(np.float64))
        for (y, x) in sites:
            if y - SEARCH < 0 or x - SEARCH < 0:
                continue
            pad = sy[y - SEARCH:y + CROP + SEARCH, x - SEARCH:x + CROP + SEARCH]
            if pad.shape != (CROP + 2 * SEARCH, CROP + 2 * SEARCH):
                continue
            ref = my[y:y + CROP, x:x + CROP]
            t0 = time.time(); a1, c1 = register(ref, pad);     tslow += time.time() - t0
            t0 = time.time(); a2, c2 = register_fft(ref, pad); tfast += time.time() - t0
            same = a1 == a2
            nsame += same
            ndiff += not same
            print("%-10d %-8s %14s %14s %10.6f %10.6f   %s"
                  % (i, "(%d,%d)" % (y, x), a1, a2, c1, c2,
                     "SAME" if same else "*** DIFFER ***"))
    print("\nORCH register  : %7.2f s total, %6.3f s each" % (tslow, tslow / max(nsame + ndiff, 1)))
    print("FFT  register  : %7.2f s total, %6.3f s each" % (tfast, tfast / max(nsame + ndiff, 1)))
    print("speedup        : %.1fx" % (tslow / tfast if tfast else 0))
    print("shifts identical: %d / %d" % (nsame, nsame + ndiff))
    if ndiff:
        print("NOT VALIDATED: %d shift(s) disagree. The fast path crops different "
              "pixels and must not be used." % ndiff)
        return 1
    print("VALIDATED on this subject: every shift identical, so the fast path "
          "crops the same pixels ORCH's path would.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

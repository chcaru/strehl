r"""Why does an analytically exact scaling relation not come out exact?

band(a) = std(DoG(a)) / mean(a).  DoG is linear and annihilates constants, so
for a' = m + k*(a - m) the relation band(a') = k*band(a) holds identically in
exact arithmetic. lad_commission.py measured a relative error of 2e-3 to 9e-3,
which is four orders of magnitude above float32 rounding. Either the claim is
wrong or the gauge is doing something other than what it says.

This isolates it by re-running the same relation under different precisions and
different pieces of the pipeline, rather than reasoning about which is likelier.
"""
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lad_measure as lm                                           # noqa: E402

BASE = os.path.join(lm.LAD, "probe-default.tiff")
MARGIN, WIN = 32, lm.WIN


def dog(a, lo, hi):
    return ndimage.gaussian_filter(a, lo) - ndimage.gaussian_filter(a, hi)


def band_at(a, lo=lm.SIG_LO, hi=lm.SIG_HI):
    return float(np.std(dog(a, lo, hi)) / np.mean(a))


def main():
    sites, _ = lm.frozen_sites("coffee-bubbles")
    s = sites[len(sites) // 2]
    ml, _ = lm.load_lum(BASE)
    y, x = s["y"], s["x"]
    a32 = np.array(ml[y:y + WIN, x:x + WIN], dtype=np.float32)
    a64 = a32.astype(np.float64)
    print("window dtype float32, shape %s" % (a32.shape,))
    print("  min %.4f  max %.4f  mean %.4f  std %.4f"
          % (a32.min(), a32.max(), a32.mean(), a32.std()))
    neg = int(np.count_nonzero(a32 < 0))
    print("  negative samples: %d  zero samples: %d"
          % (neg, int(np.count_nonzero(a32 == 0))))

    print("\n=== the relation band(m+k(a-m)) == k*band(a), by precision ===")
    print("  %-6s %14s %14s %12s %14s %12s" % ("k", "f32 pred", "f32 got", "rel", "f64 got", "rel"))
    for k in (0.5, 0.8, 1.25, 2.0):
        m32 = np.float32(a32.mean())
        g32 = band_at((m32 + k * (a32 - m32)).astype(np.float32))
        p32 = k * band_at(a32)
        m64 = a64.mean()
        g64 = band_at(m64 + k * (a64 - m64))
        p64 = k * band_at(a64)
        print("  %-6s %14.8f %14.8f %12.2e %14.8f %12.2e"
              % (k, p32, g32, abs(g32 - p32) / p32, g64, abs(g64 - p64) / p64))

    print("\n=== is it the FILTER or the ARITHMETIC? scale directly, no offset ===")
    for k in (0.5, 2.0):
        got = band_at((k * a32).astype(np.float32))
        pred = band_at(a32)          # pure scaling cancels in std/mean
        print("  band(%s*a) = %.8f   band(a) = %.8f   rel %.2e"
              % (k, got, pred, abs(got - pred) / pred))

    print("\n=== does the FILTER commute with an affine map? (f32) ===")
    m32 = np.float32(a32.mean())
    for k in (2.0,):
        lhs = dog((m32 + k * (a32 - m32)).astype(np.float32), lm.SIG_LO, lm.SIG_HI)
        rhs = (k * dog(a32, lm.SIG_LO, lm.SIG_HI)).astype(np.float32)
        d = np.abs(lhs - rhs)
        print("  k=%s  max|DoG(a')-k*DoG(a)| = %.3e   rms = %.3e   scale rms(DoG) = %.3e"
              % (k, d.max(), np.sqrt((d ** 2).mean()), np.sqrt((rhs ** 2).mean())))
        print("  mean(a')  = %.8f   mean(a) = %.8f   (must be equal)"
              % (float(np.mean((m32 + k * (a32 - m32)).astype(np.float32))), float(np.mean(a32))))

    print("\n=== gaussian_filter output dtype and mode ===")
    o = ndimage.gaussian_filter(a32, lm.SIG_LO)
    print("  in %s -> out %s" % (a32.dtype, o.dtype))
    o64 = ndimage.gaussian_filter(a64, lm.SIG_LO)
    print("  f32 vs f64 filter: max abs diff %.3e on data of rms %.3e"
          % (np.abs(o - o64).max(), np.sqrt((a64 ** 2).mean())))


if __name__ == "__main__":
    main()

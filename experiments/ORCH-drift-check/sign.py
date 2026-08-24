"""Does the measured scale actually register frame 298 onto frame 0?

Two questions this settles by rendering rather than by argument:

1. THE SIGN (SYNTHESIS fact 1219).  Magnifying frame 298 should align it to
   frame 0.  If the sign is backwards, magnifying will make the residual WORSE
   than doing nothing, and shrinking will be the one that helps.  Both are
   tried here and the winner is reported.

2. M86 P11 claims first-to-last registration of a deep bracket is impossible
   directly and must route through the edge graph, because the pairwise
   estimator's capture range fails at a 192 px plant.  The drift here is 603 px.
   If an explicit scale ladder registers 0 to 298 in one step, then that
   limitation belongs to that estimator, not to the problem.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drift import STACK, DOWN, green_plane, prep, resample_scale, ncc_peak

S_MEASURED = 0.85715


def residual_after_shift(a, b):
    """Best-aligned RMS residual between two prepped planes, after the FFT
    peak's integer shift is removed.  Lower is better registered."""
    fa = np.fft.rfft2(a)
    fb = np.fft.rfft2(b)
    x = np.fft.irfft2(fa * np.conj(fb), s=a.shape)
    k = int(np.argmax(x))
    dy, dx = np.unravel_index(k, x.shape)
    bb = np.roll(np.roll(b, dy, axis=0), dx, axis=1)
    sa = float(np.sqrt((a * a).mean()))
    sb = float(np.sqrt((bb * bb).mean()))
    if sa <= 0 or sb <= 0:
        return float("nan"), (0, 0)
    return float(np.sqrt(((a / sa - bb / sb) ** 2).mean())), (int(dy), int(dx))


def main():
    names = sorted(f for f in os.listdir(STACK) if f.lower().endswith(".arw"))
    a_raw = green_plane(os.path.join(STACK, names[0]))
    b_raw = green_plane(os.path.join(STACK, names[-1]))
    a = prep(a_raw)
    print("comparing %s  vs  %s" % (names[0], names[-1]))
    print("plane %s (CFA green, %dx block-mean)\n" % (a_raw.shape, DOWN))

    arms = [
        ("do nothing (identity)", 1.0),
        ("MAGNIFY 298 by 1/s = %.5f" % (1.0 / S_MEASURED), 1.0 / S_MEASURED),
        ("SHRINK 298 by s = %.5f  (the wrong sign)" % S_MEASURED, S_MEASURED),
    ]
    print("%-42s %10s %10s   %s" % ("arm", "NCC", "residual", "shift"))
    out = {}
    for label, factor in arms:
        bb = prep(resample_scale(b_raw, factor))
        n = ncc_peak(a, bb)
        r, sh = residual_after_shift(a, bb)
        out[label] = (n, r)
        print("%-42s %10.4f %10.4f   %s" % (label, n, r, sh))

    ident = out["do nothing (identity)"]
    mag = out[arms[1][0]]
    shr = out[arms[2][0]]
    print("")
    print("magnify vs identity : NCC %+.4f   residual %+.4f"
          % (mag[0] - ident[0], mag[1] - ident[1]))
    print("shrink  vs identity : NCC %+.4f   residual %+.4f"
          % (shr[0] - ident[0], shr[1] - ident[1]))
    print("")
    winner = max(out.items(), key=lambda kv: kv[1][0])[0]
    print("BEST BY NCC: %s" % winner)
    print("residual ranking (lower better): %s"
          % " < ".join(k for k, _ in sorted(out.items(), key=lambda kv: kv[1][1])))


if __name__ == "__main__":
    main()

"""signconv.py -- which side of the integer_shift sign convention is wrong?

FOUND WHILE AUDITING.  test_instrument.py TEST 2 reports `MISS ... planted
(2,3) got (2,3)` -- planted and recovered are IDENTICAL, yet scored a failure,
because h2.commission_shift requires `(gy,gx) == (-dy,-dx)`.  Every listed miss
has got == planted exactly, with peaks 0.99+.  That is a sign convention, not a
registration failure.

It matters because it cannot be resolved by reading: EVERY consumer
(coherence.py, h2h2.py, h2h2b.py, toneparity.py, gradetest.py) does

    dy, dx, pk = h2.integer_shift(a, b)
    cb = B.crop(y + dy, x + dx, T)

so if commission_shift's criterion is the correct one, every comparison in this
lane has been re-cropping the moving image AWAY from alignment, doubling the
offset instead of removing it.

This decides it by MEASUREMENT, end to end, on a real render: plant a known
displacement, run the consumers' exact recipe, and see whether the residual
misalignment goes to zero or to twice the plant.  Both candidate conventions
are run as arms; one of them must win, and the arm that wins is not chosen by
argument.

Usage:  python signconv.py
"""
import os
import sys

import numpy as np

import h2
import rois

LIN = r"C:\dev\strehl-out\V-H2H2\lin"
T = 256


def residual(a, b):
    """Correlation of two equal-size crops at zero lag, after mean removal.
    1.0 means perfectly aligned identical content."""
    x = a - a.mean()
    y = b - b.mean()
    d = np.sqrt((x * x).sum() * (y * y).sum()) + 1e-30
    return float((x * y).sum() / d)


def main():
    r = h2.Render(os.path.join(LIN, "113-A-g1.tiff"), linear=True, name="113")
    detail, _flat, _c = rois.census(r, t=T, pad=32, verbose=False)
    rng = np.random.default_rng(7)
    picks = [detail[i] for i in rng.permutation(len(detail))[:6]]
    plants = [(1, 0), (0, -1), (2, 3), (-3, 2), (5, -5)]

    print("For each plant, MOV is the SAME image cropped at (y+dy, x+dx), so")
    print("the true content displacement is known exactly and the perfectly")
    print("aligned answer scores residual 1.000000.\n")
    print("  %-8s %-9s | %-22s | %-22s"
          % ("plant", "returned", "consumer recipe (+g)", "commission (-g)"))

    tot = {"plus": [], "minus": []}
    for (dy, dx) in plants:
        for (y, x) in picks:
            ref = r.crop(y, x, T)[0]
            mov = r.crop(y + dy, x + dx, T)[0]
            gy, gx, pk = h2.integer_shift(ref, mov)
            # consumers: re-crop the moving image at ORIGIN + returned value
            a_plus = r.crop(y + dy + gy, x + dx + gx, T)[0]
            # the OTHER convention: origin MINUS returned value
            a_minus = r.crop(y + dy - gy, x + dx - gx, T)[0]
            tot["plus"].append(residual(ref, a_plus))
            tot["minus"].append(residual(ref, a_minus))
        print("  %-8s %-9s | %-22s | %-22s"
              % ("(%d,%d)" % (dy, dx), "(%d,%d)" % (gy, gx),
                 "%.6f" % np.mean(tot["plus"][-len(picks):]),
                 "%.6f" % np.mean(tot["minus"][-len(picks):])))

    mp, mm = float(np.mean(tot["plus"])), float(np.mean(tot["minus"]))
    print("\n  mean over %d trials:  consumer recipe %.6f   commission %.6f"
          % (len(tot["plus"]), mp, mm))
    winner = "consumers" if mp > mm else "commission_shift"
    print("  -> the correct convention is the one used by %s" % winner)

    # The arm that makes this conclusive rather than merely comparative: the
    # zero plant. If the two conventions differ, only one can return exactly
    # the reference crop when the true displacement is zero -- and BOTH must,
    # since g is then (0,0). A difference here would mean the harness itself
    # is broken and neither column could be trusted.
    z = []
    for (y, x) in picks:
        ref = r.crop(y, x, T)[0]
        gy, gx, pk = h2.integer_shift(ref, ref)
        z.append((gy, gx, pk))
    ok = all(g[:2] == (0, 0) for g in z)
    print("  control: zero displacement -> returned %s, peak %.6f  [%s]"
          % (set((g[0], g[1]) for g in z), z[0][2],
             "OK" if ok else "HARNESS BROKEN"))

    # What does the residual misalignment cost the actual statistic?  A wrong
    # sign is only worth reporting if it moves a number.
    print("\n  cost of the wrong convention, in the statistic that is published:")
    masks = h2.band_masks(T)
    for (dy, dx) in [(0, 0), (1, 0), (2, 3)]:
        for label, sgn in (("correct", -1 if mm > mp else +1),
                           ("wrong", +1 if mm > mp else -1)):
            gam = []
            for (y, x) in picks:
                ref = r.crop(y, x, T)[0]
                mov = r.crop(y + dy, x + dx, T)[0]
                gy, gx, _ = h2.integer_shift(ref, mov)
                c = r.crop(y + dy + sgn * gy, x + dx + sgn * gx, T)[0]
                fa = h2.contrast_fft(ref)
                fb = h2.contrast_fft(c)
                PA, PB, C = h2.pair_bands(fa, fb, masks, T, "signconv")
                gam.append(C / np.sqrt(np.maximum(PA * PB, 1e-300)))
            g = np.mean(gam, axis=0)
            print("    plant (%2d,%2d) %-8s gamma by band: %s"
                  % (dy, dx, label, " ".join("%+.4f" % v for v in g)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

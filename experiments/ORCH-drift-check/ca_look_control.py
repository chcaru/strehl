"""Positive control for ca_look.py's radial displacement measure.

ca_look.py reported |R-G| and |B-G| under 0.08 px in every corner of every
shipped master, against a claimed 0.363 px of uncorrected blue displacement.
Its intended control -- the frame centre -- returns None by construction,
because the radial direction is undefined there. So it never ran, and a zero
from an instrument that has never been shown to respond is not a measurement.

(There is a separate, already-validated CA instrument in ca_radial.py /
ca_control.py that measures R/B correlation on a planted radial shear. This is
not a replacement for it. It validates only the displacement statistic that
ca_look.py actually printed.)

Ground truth is fixed by construction, not measured: roll one channel by an
exact INTEGER number of pixels in x. Integer only -- sub-pixel resampling
would blur the very quantity under test. The radial projection must then read
that roll times the radial unit vector's x-component.
"""
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ca_look import CROP, radial_disp  # noqa: E402

SRC = r"C:\dev\strehl-out\SHIP-V1"


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "tweezers-cpl"
    img = tifffile.imread(os.path.join(SRC, name + ".tiff"))
    H, W, _ = img.shape
    cy, cx = H / 2.0, W / 2.0
    m = 40

    py, px = H - CROP - m, W - CROP - m
    patch = img[py:py + CROP, px:px + CROP, :3].copy()

    my, mx = py + CROP / 2.0, px + CROP / 2.0
    vy, vx = my - cy, mx - cx
    ux = vx / np.hypot(vy, vx)
    print("%s  site BR   radial unit vector x-component = %.4f" % (name, ux))
    print("a roll of n px in x should read as n * %.4f px radially\n" % ux)

    print("%10s %14s %14s %10s" % ("roll (px)", "expected", "measured", "|err|"))
    print("-" * 52)

    errs = []
    zero_reading = None
    for roll in (-3, -2, -1, 0, 1, 2, 3):
        p = patch.copy()
        p[:, :, 0] = np.roll(p[:, :, 0], roll, axis=1)
        r = radial_disp(p, cy, cx, py, px)
        if r is None:
            print("%10d   radial_disp returned None -- INSTRUMENT DEAD" % roll)
            return
        rg = r[0]
        exp = roll * ux
        if roll == 0:
            zero_reading = rg
        err = abs(abs(rg) - abs(exp))
        errs.append((roll, err))
        print("%10d %14.3f %14.3f %10.3f" % (roll, exp, rg, err))

    print()
    # The sign convention of shift_1d is not the point; magnitude tracking is.
    nonzero = [e for roll, e in errs if roll != 0]
    worst = max(nonzero)
    print("=" * 52)
    print("plant's own null: roll=0 reads %+.3f px (bar |x| <= 0.10) : %s"
          % (zero_reading, "PASS" if abs(zero_reading) <= 0.10 else "FAIL"))
    print("worst magnitude error over the non-zero rolls  : %.3f px" % worst)
    if worst <= 0.35 and abs(zero_reading) <= 0.10:
        print()
        print("INSTRUMENT VALIDATED. It tracks a known integer roll and is quiet")
        print("at zero, so its near-zero corner readings on the shipped masters")
        print("are a real measurement rather than a dead statistic.")
    else:
        print()
        print("INSTRUMENT NOT VALIDATED. Do not cite ca_look.py's corner table.")
    print("=" * 52)


if __name__ == "__main__":
    main()

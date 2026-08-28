r"""Potency gate for the hull ladder. Nothing may be interpreted before this.

ORCH: "--unclamped ... is your potency arm: it proves the gauge responds to the
clamp axis at all before you interpret a reduction. Run it first."

And a second potency question ORCH did not ask for, which this lane requires
because prediction P2 is "PerLevel is INERT on the controls": inertness and dead
plumbing are the same reading. `pyramid.rs:3256` records that `hull_lambda`
shipped WIRED AND INERT, moving the output by 0.008% -- plumbed, plausible, and
worthless. So `--per-level` must be shown to move a real render by a real amount
BEFORE any "no change" is reported anywhere.

Reference points from this project: `--pyramid-exponent 4.0` moves 90.98% of
samples; `--pyramid-gate 8.0` moves 16.27%; `hull_lambda` 2->4 moved 0.008% and
was judged inert.

Reads raw 16-bit samples straight from the TIFF. PIL mis-reads this tool's
output; `tifffile` is used everywhere in this lane for that reason.
"""
import os
import sys

import numpy as np
import tifffile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hul_measure as hm                                           # noqa: E402

PAIRS = [("inputrange", "perlevel"), ("inputrange", "unclamped")]


def load(path):
    a = tifffile.imread(path)
    return np.asarray(a)


def main():
    subs = sys.argv[1:] or ["112MSDCF", "coffee-bubbles"]
    print("%-22s %-24s %10s %12s %12s %12s"
          % ("subject", "pair", "differ", "median|d|", "p99|d|", "max|d|"))
    any_row = False
    for sub in subs:
        for a, b in PAIRS:
            pa, pb = hm.arm_path(sub, a), hm.arm_path(sub, b)
            if not (os.path.exists(pa) and os.path.exists(pb)):
                continue
            A, B = load(pa), load(pb)
            if A.shape != B.shape:
                print("  %s: SHAPE MISMATCH %s vs %s" % (sub, A.shape, B.shape))
                continue
            d = np.abs(A.astype(np.int32) - B.astype(np.int32))
            n = d.size
            nz = int(np.count_nonzero(d))
            frac = 100.0 * nz / n
            nzv = d[d > 0]
            print("%-22s %-24s %9.3f%% %12.1f %12.1f %12.1f"
                  % (sub, "%s vs %s" % (a, b), frac,
                     float(np.median(nzv)) if nz else 0.0,
                     float(np.percentile(nzv, 99)) if nz else 0.0,
                     float(d.max())))
            any_row = True
            del A, B, d
    if not any_row:
        raise SystemExit("no arm pairs available yet")
    print("\n  n samples per arm = 7032 x 4688 x 3 = 98,898,048")
    print("  reference: exponent 4.0 moved 90.98%; hull_lambda 2->4 moved 0.008% (INERT)")


if __name__ == "__main__":
    main()

"""Turn the plant from "roughly recovered" into an EXACT count test.

The +5000 DN plant moved ABOVE from 19 to 90,330, not to the 120,000 samples
planted. That is correct behaviour, not a miss: the hull is wide (mean span 4042
DN), so where the merge already sat far below `hi`, adding 5000 DN does not clear
the ceiling. But "correct behaviour" asserted is worth nothing. So predict the
count from the hull independently, BEFORE looking at the detector's answer, and
require exact equality.

    predicted = #{ samples in the plant box : uniform + 5000 > hi + guard }

If predicted == measured exactly, the detector is counting precisely the right
samples, and its zero on the unplanted arm means something.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from bhull2 import BBOX, load16

CACHE = Path("warp/cache")
GUARD = 1.0
PLANT = 5000.0
Y0, Y1, X0, X1 = 1000, 1200, 1000, 1200
MEASURED_ABOVE = 90330      # from the planted run
MEASURED_BELOW = 25         # unplanted below-count, must be unchanged
BASE_ABOVE = 19             # unplanted above-count


def main() -> int:
    lo = np.load(CACHE / "lo.npy").astype(np.float32)
    hi = np.load(CACHE / "hi.npy").astype(np.float32)
    m = load16(Path("warp/merge-W-uniform.tiff")).astype(np.float32)

    print("  PREDICTION, computed from the hull alone (detector not consulted)")
    box = (slice(Y0, Y1), slice(X0, X1), slice(None))
    planted = m.copy()
    planted[box] += PLANT

    above = planted > hi + GUARD
    below = planted < lo - GUARD
    pred_above = int(np.count_nonzero(above))
    pred_below = int(np.count_nonzero(below))

    in_box = np.zeros(m.shape, dtype=bool)
    in_box[box] = True
    pred_above_inbox = int(np.count_nonzero(above & in_box))
    pred_above_outbox = int(np.count_nonzero(above & ~in_box))

    n_planted = (Y1 - Y0) * (X1 - X0) * 3
    headroom = (hi + GUARD - m)[box]
    would_clear = int(np.count_nonzero(headroom < PLANT))

    print(f"    samples planted                  : {n_planted}")
    print(f"    of those, headroom < {PLANT:.0f} DN     : {would_clear}")
    print(f"    predicted ABOVE (whole frame)    : {pred_above}")
    print(f"      of which inside the plant box  : {pred_above_inbox}")
    print(f"      of which OUTSIDE the plant box : {pred_above_outbox}  (must equal "
          f"the unplanted baseline {BASE_ABOVE})")
    print(f"    predicted BELOW (whole frame)    : {pred_below}")

    print("\n  MEASURED by the detector")
    print(f"    ABOVE : {MEASURED_ABOVE}")
    print(f"    BELOW : {MEASURED_BELOW}")

    ok_a = pred_above == MEASURED_ABOVE
    ok_b = pred_below == MEASURED_BELOW
    ok_s = pred_above_outbox == BASE_ABOVE
    ok_h = pred_above_inbox == would_clear

    print("\n  ================ PLANT COMMISSIONING ================")
    print(f"    ABOVE count exact          : {'PASS' if ok_a else f'FAIL {pred_above} vs {MEASURED_ABOVE}'}")
    print(f"    BELOW unchanged (no spill) : {'PASS' if ok_b else f'FAIL {pred_below} vs {MEASURED_BELOW}'}")
    print(f"    no leakage outside the box : {'PASS' if ok_s else f'FAIL {pred_above_outbox} vs {BASE_ABOVE}'}")
    print(f"    headroom accounting exact  : {'PASS' if ok_h else f'FAIL {pred_above_inbox} vs {would_clear}'}")
    print(f"    OVERALL                    : {'GREEN' if all([ok_a, ok_b, ok_s, ok_h]) else 'RED'}")
    return 0 if all([ok_a, ok_b, ok_s, ok_h]) else 1


if __name__ == "__main__":
    raise SystemExit(main())

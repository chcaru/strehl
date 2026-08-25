"""What would M110's headline numbers have read under the PIL narrowing?

ORCH's corrected triage rule: LOCATION statistics are largely immune to 8-bit
narrowing; DISPERSION and VALUE statistics absorb the quantisation directly.

M110's statistics are almost entirely VALUE statistics -- chroma magnitudes,
signed channel ratios, sign-flip counts. Under the corrected rule that puts
them in the VULNERABLE class, not the immune one. M110's clearance therefore
rests entirely on the narrowing never having occurred, and on nothing about
the estimators being robust.

That is a claim worth measuring rather than asserting. This replays the two
headline results on deliberately narrowed copies of the same arrays, the way
PIL would have delivered them, and reports what each would have said.

Not a hypothetical: it is the counterfactual that decides how much work the
one-line dtype assertion in sheet.py::load_raw is actually doing.
"""

from pathlib import Path

import numpy as np
import tifffile

D = Path(r"C:\dev\strehl-out\M110-sheet\bee-3-cpl")
PRED_G = -0.1152 / 1.6361   # -0.0704, derived from color.rs::camera_to_srgb
LEVEL = 257                 # 1 8-bit display level in 16-bit DN


def narrow(a: np.ndarray) -> np.ndarray:
    """What PIL hands you: the high byte, promoted back for arithmetic."""
    return (a >> 8).astype(np.int64)


def ratio_test(off16, on16, label):
    """Section 18 cell A: signed median dG/dR against the matrix prediction."""
    d = on16 - off16
    dR, dG = d[:, :, 0], d[:, :, 1]
    scale = float(np.percentile(np.abs(dR), 99.9))
    m = np.abs(dR) > 0.05 * scale
    if m.sum() < 1000:
        print(f"  {label:<26} UNMEASURABLE -- only {int(m.sum())} px above threshold")
        return None
    med = float(np.median(dG[m] / dR[m]))
    err = abs(med - PRED_G) / abs(PRED_G) * 100.0
    print(f"  {label:<26} signed median dG/dR = {med:+.4f}   "
          f"vs predicted {PRED_G:+.4f}   error {err:6.1f}%   n={int(m.sum()):,}")
    return med


def overshoot_test(off16, on16, label, gate_dn):
    """Section 16: P(chroma sign flip AND magnitude grew), gated."""
    def ry(a):
        luma = 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]
        return a[:, :, 0] - luma

    o, n = ry(off16.astype(np.float64)), ry(on16.astype(np.float64))
    g = np.abs(o) >= gate_dn
    if g.sum() < 1000:
        print(f"  {label:<26} UNMEASURABLE -- only {int(g.sum())} px pass the gate")
        return None
    flip = np.sign(o[g]) != np.sign(n[g])
    grew = np.abs(n[g]) > np.abs(o[g])
    pct = 100.0 * float(np.mean(flip & grew))
    print(f"  {label:<26} overshoot = {pct:6.2f}%   "
          f"gated px = {int(g.sum()):,} ({100.0*g.sum()/g.size:.1f}% of frame)")
    return pct


def main():
    print(__doc__)
    off16 = tifffile.imread(str(D / "default.tif")).astype(np.int64)
    on16 = tifffile.imread(str(D / "ca.tif")).astype(np.int64)
    assert off16.dtype == on16.dtype == np.int64

    off8, on8 = narrow(off16), narrow(on16)
    print(f"levels per channel: 16-bit {len(np.unique(off16[:,:,0])):,}"
          f"   narrowed {len(np.unique(off8[:,:,0])):,}")
    print()

    print("SECTION 18 cell A -- the matrix agreement (a VALUE statistic)")
    t = ratio_test(off16, on16, "as measured (uint16)")
    n = ratio_test(off8, on8, "under PIL narrowing")
    print()

    print("SECTION 16 -- overshoot, gated at 1 display level (a VALUE statistic)")
    overshoot_test(off16, on16, "as measured (uint16)", LEVEL)
    overshoot_test(off8, on8, "under PIL narrowing", 1.0)
    print()

    print("=" * 70)
    if t is not None and n is not None:
        shift = abs(n - t) / abs(t) * 100.0
        print(f"The matrix agreement moves {shift:.1f}% under narrowing.")
        print(f"  reported 2.4% agreement with theory would have become "
              f"{abs(n - PRED_G)/abs(PRED_G)*100.0:.1f}%.")
    print("M110's statistics are VALUE statistics, so ORCH's corrected rule")
    print("places them in the vulnerable class. The clearance rests on the")
    print("narrowing never having occurred -- not on estimator robustness.")


if __name__ == "__main__":
    main()

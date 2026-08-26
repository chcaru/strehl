"""Absolute background LEVEL in DN, before and after. Not error, not ratio.

ORCH's discriminator, and it is the right one. An upward-biased estimator
applied to a downward artifact nulls the veiling metric without removing the
defect, and every ratio-based instrument either of us has pointed at the problem
would report that as success. A ratio hides an additive bias perfectly.

So this reports levels, and it reports them where there is provably no veil to
remove: far from any occluder. A veil is cast by something. If the level rises
out there, the estimator is adding light.

The prediction under test, from BUILD-SHARP: an UNDEBIASED upper envelope over n
frames sits ~sqrt(2 ln n) sigma high by noise alone, which at sigma_frame ~ 200
DN is about +169 DN -- the same order as 109MSDCF's entire -177 DN aura.

The subject mask is taken from the OFF arm and applied to BOTH, so the two arms
are compared over one identical population. Deriving it per-arm would let the
correction redefine the region it is judged on.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import binary_closing, binary_opening, distance_transform_edt

PREDICTED_BIAS_DN = 169.0


def luma(p: Path) -> np.ndarray:
    a = tifffile.imread(str(p)).astype(np.float32)
    if a.ndim == 3:
        return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    return a


def main() -> int:
    out = Path(sys.argv[1])
    stem = sys.argv[2]
    label = sys.argv[3] if len(sys.argv) > 3 else stem

    off = luma(out / f"{stem}-off.tif")
    on = luma(out / f"{stem}-on.tif")
    lift = on - off

    backdrop = float(np.median(off))
    subj = off < 0.5 * backdrop
    subj = binary_opening(binary_closing(subj, np.ones((9, 9))), np.ones((9, 9)))
    dist = distance_transform_edt(~subj)

    print(f"=== {label} ===")
    print(f"subject {100 * subj.mean():.2f}% of frame; "
          f"predicted arithmetic bias if undebiased: +{PREDICTED_BIAS_DN:.0f} DN\n")

    print(f"{'region':>22}  {'off DN':>10}  {'on DN':>10}  {'delta':>8}  "
          f"{'touched':>8}  {'lift|touched':>12}")

    regions = [
        ("all backdrop", ~subj),
        ("backdrop d>=100 px", ~subj & (dist >= 100)),
        ("backdrop d>=300 px", ~subj & (dist >= 300)),
        ("backdrop d>=500 px", ~subj & (dist >= 500)),
        ("subject", subj),
    ]
    far_delta = None
    for name, m in regions:
        if not m.any():
            print(f"{name:>22}  {'--':>10}  (region empty)")
            continue
        a, b = float(np.median(off[m])), float(np.median(on[m]))
        t = np.abs(lift[m]) > 1.0
        lt = float(np.mean(lift[m][t])) if t.any() else 0.0
        print(f"{name:>22}  {a:>10.0f}  {b:>10.0f}  {b - a:>+8.0f}  "
              f"{100 * t.mean():>7.2f}%  {lt:>+12.0f}")
        if name == "backdrop d>=500 px":
            far_delta = b - a

    print()
    if far_delta is None:
        print("  no far field on this subject; the discriminator cannot run here.")
    elif far_delta > 0.5 * PREDICTED_BIAS_DN:
        print(f"  FAIL: level ROSE {far_delta:+.0f} DN where there is no veil to "
              f"remove. That is the order of the predicted arithmetic bias "
              f"(+{PREDICTED_BIAS_DN:.0f} DN). The estimator is adding light.")
    elif far_delta < -0.5 * PREDICTED_BIAS_DN:
        # Not the predicted failure. BUILD-SHARP's bias is UPWARD against a
        # darkening defect; a far field that FALLS cannot be that bias filling
        # the artifact in. Reported separately because the first version of
        # this test took abs() and printed "level rose" on a fall -- a verdict
        # line that contradicted its own rows.
        print(f"  NOT THE BIAS: far-field level FELL {far_delta:+.0f} DN. The "
              f"predicted artifact is an UPWARD bias (+{PREDICTED_BIAS_DN:.0f} "
              f"DN) against a darkening, so a fall is not it. If the rim rows "
              f"above rose while this fell, the two move in OPPOSITE "
              f"directions and an additive bias cannot explain both.")
    else:
        print(f"  PASS: far-field level moved {far_delta:+.0f} DN against a "
              f"+{PREDICTED_BIAS_DN:.0f} DN prediction for an undebiased "
              f"envelope. The estimator is not filling in arithmetically.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

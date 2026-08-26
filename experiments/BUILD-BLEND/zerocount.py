"""ORCH's clamp acceptance test, scored on renders from a single binary.

Metric (ORCH's): percentage of all pixels at exactly 0, per channel,
AFTER (pyramid) minus BEFORE (estimator), in percentage points.

Acceptance, as ORCH stated it:
  * MERGE-verdict subjects must come back within +0.05 pt of BEFORE
  * couch-fibers-cpl (the placebo, currently +0.0000) must not regress

The threshold ramp is included because it is ORCH's own discriminator between a
clamp signature (a spike at exactly zero) and a genuinely dark scene (a smooth
ramp).  Reporting the delta without it would hide which of the two we are
looking at.

Usage:  python zerocount.py <dir-with-{subject}-{estimator,pyramid}.tiff>
"""

import glob
import os
import sys

import numpy as np
import tifffile

THRESHOLDS = (0, 1, 16, 64, 256)
CH = ("R", "G", "B")


def counts(img):
    """Fraction of all samples at or below each threshold, per channel."""
    out = {}
    n = img.shape[0] * img.shape[1]
    for c in range(img.shape[2]):
        p = img[:, :, c]
        out[c] = [100.0 * float((p <= t).sum()) / n for t in THRESHOLDS]
    return out


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\strehl-out\BUILD-BLEND\acceptance"
    subjects = sorted({
        os.path.basename(p).rsplit("-", 1)[0]
        for p in glob.glob(os.path.join(d, "*-estimator.tiff"))
    })
    if not subjects:
        raise SystemExit(f"no *-estimator.tiff under {d}")

    print(f"{'subject':<28} {'ch':<3} {'BEFORE@0':>9} {'AFTER@0':>9} "
          f"{'delta pt':>9}   ramp AFTER 0->256")
    verdicts = []
    for s in subjects:
        pb = os.path.join(d, f"{s}-estimator.tiff")
        pa = os.path.join(d, f"{s}-pyramid.tiff")
        if not os.path.exists(pa):
            print(f"{s:<28} -- missing pyramid arm")
            continue
        B = tifffile.imread(pb)
        A = tifffile.imread(pa)
        if B.shape != A.shape:
            print(f"{s:<28} -- canvases differ {B.shape} vs {A.shape}; skipping")
            continue
        cb, ca = counts(B), counts(A)
        worst = -9e9
        for c in range(A.shape[2]):
            delta = ca[c][0] - cb[c][0]
            worst = max(worst, delta)
            ramp = " ".join(f"{v:6.3f}" for v in ca[c])
            print(f"{s:<28} {CH[c]:<3} {cb[c][0]:9.4f} {ca[c][0]:9.4f} "
                  f"{delta:+9.4f}   {ramp}")
        verdicts.append((s, worst))
        print()

    print("=" * 78)
    print(f"{'subject':<28} {'worst-channel delta':>20}   verdict (ORCH: within +0.05 pt)")
    for s, w in verdicts:
        ok = "PASS" if w <= 0.05 else "FAIL"
        print(f"{s:<28} {w:+20.4f}   {ok}")


if __name__ == "__main__":
    main()

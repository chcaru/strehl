# V-NOISE2 / clipaudit.py -- answer ORCH's exposure-regression broadcast by
# MEASURING the delivered pixels, not by auditing the flags I believe I passed.
#
# ORCH's point is that the IMAGE is wrong, not the recipe.  A flag audit proves
# intent; only a pixel count proves the master.
#
# -------------------------------------------------------------------------
# DEFECT FOUND AND FIXED IN THIS FILE, recorded because it nearly produced a
# false alarm that would have invalidated sec.9 and sec.10 for no reason.
#
# v1 computed `(a == 65535).mean()` over the WHOLE array.  Every enfuse arm
# then read EXACTLY 25.0000% clipped -- 18 files, different subjects, different
# frame counts, four identical decimals.  That is not a measurement, it is 1/4.
# enfuse writes RGBA (4688, 7032, 4); channel 3 is alpha and is 100% opaque, so
# a quarter of all values sit at the ceiling by construction.  strehl writes
# RGB (4688, 7032, 3) and has no alpha, so the two arms were not even being
# measured on the same quantity.  MEASURED per channel on 119/coh-enfuse-A:
#   ch0 0.0%  ch1 0.0%  ch2 0.0%  ch3 100.0%
# The tell was that identical printed values (25.0000) landed on DIFFERENT
# verdicts, because `> 0.25` is a knife edge that a single genuinely clipped
# RGB pixel tips.  A threshold sitting exactly on an artifact of the data
# layout is not a threshold.
#
# So: alpha is excluded (it is not image data), the count is reported per
# channel, and the audit is commissioned below.
# -------------------------------------------------------------------------
#
# COMMISSIONING, because a checker that reads 0.0% on everything is
# indistinguishable from a checker that is broken.  ORCH's whole broadcast is
# about instruments that read CLEAN on a white sheet.  Two arms, answers fixed
# in advance:
#   NEGATIVE  a real arm, untouched             MUST read ok
#   POSITIVE  that same arm x 6.105 and clipped MUST read BLOWN
# 6.105 is ORCH's own measured HEAD --auto-exposure gain, so the positive
# control reproduces the actual regression rather than an arbitrary
# saturation.  Either arm failing is a hard exit and the corpus table is not
# printed.
#
# Usage:  python clipaudit.py

import sys, glob, os
import numpy as np
import tifffile

ROOT = r"C:\dev\strehl-out\V-NOISE2"

KEYS = ["119", "113", "bee-L1", "bee-L1P", "bee-L2", "bee-L2P",
        "bee-L3", "bee-L3P", "bee-L4", "leaf"]

CEIL = 65535
BLOWN = 0.25          # ORCH's corpus threshold: >25% of pixels at the ceiling
ORCH_GAIN = 6.105     # ORCH's measured HEAD --auto-exposure gain


def colour(a):
    """Image channels only.  Alpha is not image data and enfuse always sets it
    fully opaque, which contributes a fixed 1/4 to any whole-array count."""
    return a[..., :3] if a.ndim == 3 and a.shape[-1] == 4 else a


def measure(a):
    c = colour(a)
    return float((c == CEIL).mean()), float(np.median(c))


def first_arm():
    for k in KEYS:
        g = sorted(glob.glob(os.path.join(ROOT, k, "arms", "*.tif*")))
        if g:
            return g[0]
    return None


def commission():
    """Prove the audit can both pass a sane master and convict a blown one."""
    ref = first_arm()
    if ref is None:
        print("COMMISSIONING IMPOSSIBLE: no arm file to build controls from")
        return False

    a = tifffile.imread(ref)
    neg_c, _ = measure(a)

    blown = np.clip(colour(a).astype(np.float64) * ORCH_GAIN,
                    0, CEIL).astype(np.uint16)
    pos_c, pos_m = measure(blown)

    ok_neg = neg_c <= BLOWN
    ok_pos = pos_c > BLOWN
    print(f"COMMISSIONING on {os.path.basename(ref)}")
    print(f"  NEGATIVE untouched       clipped {100*neg_c:7.4f}%  "
          f"expect <= {100*BLOWN:.0f}%   {'PASS' if ok_neg else 'FAIL'}")
    print(f"  POSITIVE x{ORCH_GAIN} clipped   clipped {100*pos_c:7.4f}%  "
          f"median {pos_m:.0f}  expect > {100*BLOWN:.0f}%   "
          f"{'PASS' if ok_pos else 'FAIL'}")
    return ok_neg and ok_pos


def main():
    if not commission():
        print("\nCOMMISSIONING FAILED -- the audit is not trustworthy; "
              "no verdict is reported")
        return 2
    print()

    rows = []
    for k in KEYS:
        arm = os.path.join(ROOT, k, "arms")
        if not os.path.isdir(arm):
            continue
        for p in sorted(glob.glob(os.path.join(arm, "*.tif*"))):
            a = tifffile.imread(p)
            if a.dtype != np.uint16:
                continue
            c, m = measure(a)
            cc = colour(a)
            per = [float((cc[..., i] == CEIL).mean())
                   for i in range(cc.shape[-1])]
            rows.append((k, os.path.basename(p), c, m, per, a.shape[-1]))

    if not rows:
        print("NO ARM FILES FOUND -- cannot answer; do not report a case")
        return 2

    print(f"{'key':10s} {'arm':26s} {'ch':>3s} {'clip%':>8s} "
          f"{'median':>8s}  verdict  per-channel clip%")
    worst, worst_name = 0.0, ""
    for k, name, c, m, per, nch in rows:
        v = "BLOWN" if c > BLOWN else "ok"
        if c > worst:
            worst, worst_name = c, f"{k}/{name}"
        print(f"{k:10s} {name:26s} {nch:3d} {100*c:8.4f} {m:8.0f}  {v:6s}   "
              + " ".join(f"{100*x:.4f}" for x in per))

    print()
    print(f"arms measured : {len(rows)}")
    print(f"worst clipped : {100*worst:.4f}%  ({worst_name})   "
          f"threshold {100*BLOWN:.0f}%")
    if worst > BLOWN:
        print("VERDICT: at least one arm is BLOWN -- numbers from it "
              "must be retaken")
        return 1
    print("VERDICT: no arm is blown; this lane's evidence base has NOT moved")
    return 0


if __name__ == "__main__":
    sys.exit(main())

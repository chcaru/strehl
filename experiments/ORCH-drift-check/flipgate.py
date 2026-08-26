"""The acceptance gate on DEFAULT_MERGE_BACKEND, measured on its own terms.

`merge_cmd.rs` states the blocking condition in prose and ends with:

    "This line moves the day that clip passes the gate."

The recorded blocker, measured through the shipped binary on
`flower-bud-alone-cpl`, camera-linear with --demosaic, CA and photometric
explicitly unset:

    clip%   estimator 0.0001   pyramid 1.4043     (four orders of magnitude)
    p1      estimator 1028     pyramid 334        (shadow collapse)

and the note that neither moves with the band gate, so both belong to the
merge rather than to its parameters.

This script re-measures exactly those two quantities on exactly those arms.  It
is deliberately narrow: it does not re-litigate acuity or micro-contrast, which
the pyramid already won on both subjects, because those were never the blocker.

A gate must be able to FAIL, so the recorded blocking values are asserted as a
regression check against the estimator arm: if the estimator's own numbers have
drifted from what the constant records, the comparison is not the one the
constant authorises and the script says so instead of returning a verdict.

Usage:
    python flipgate.py <dir-with-{subject}--{arm}.tiff> <subject> [<subject> ...]
"""

import sys
import os
import numpy as np
import tifffile

# What merge_cmd.rs records, and what this re-measures.
RECORDED = {
    "flower-bud-alone-cpl": {"estimator": (0.0001, 1028.0), "pyramid": (1.4043, 334.0)},
    "couch-fibers-cpl": {"estimator": (0.0000, None), "pyramid": (0.0000, None)},
}
MAXV = 65535


def measure(path):
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path}: expected uint16, got {a.dtype}"
    clip = 100.0 * float(np.count_nonzero(a >= MAXV)) / a.size
    lum = (0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2])
    p1 = float(np.percentile(lum, 1.0))
    zero = int(np.count_nonzero(np.all(a == 0, axis=2)))
    return clip, p1, zero, a.shape


def main():
    d = sys.argv[1]
    subjects = sys.argv[2:]
    print(f"{'subject':<26} {'arm':<10} {'clip%':>9} {'p1 (DN)':>10} {'exact-0 px':>12}")
    print("-" * 72)
    res = {}
    for s in subjects:
        for arm in ("estimator", "pyramid"):
            p = os.path.join(d, f"{s}--{arm}.tiff")
            if not os.path.exists(p):
                print(f"{s:<26} {arm:<10} {'MISSING':>9}")
                continue
            clip, p1, zero, shape = measure(p)
            res[(s, arm)] = (clip, p1, zero)
            print(f"{s:<26} {arm:<10} {clip:>9.4f} {p1:>10.1f} {zero:>12,}")

    print()
    print("REGRESSION CHECK  the estimator arm must still read what the constant records,")
    print("                  else this is not the comparison the constant authorises.")
    ok_baseline = True
    for s in subjects:
        rec = RECORDED.get(s, {}).get("estimator")
        if not rec or (s, "estimator") not in res:
            continue
        clip, p1, _ = res[(s, "estimator")]
        dc = abs(clip - rec[0])
        print(f"  {s}: estimator clip {clip:.4f} vs recorded {rec[0]:.4f}  "
              f"delta {dc:.4f}", end="")
        if rec[1] is not None:
            print(f" | p1 {p1:.1f} vs recorded {rec[1]:.0f}", end="")
        print()
        if dc > 0.05:
            ok_baseline = False
            print(f"    *** estimator drifted. The recorded blocker was measured on a "
                  f"different pipeline.")
    if not ok_baseline:
        print("\n  VERDICT WITHHELD -- re-establish the baseline first.")
        return 1

    print()
    print("THE GATE")
    verdict_all = True
    for s in subjects:
        if (s, "pyramid") not in res or (s, "estimator") not in res:
            continue
        pc, pp1, pz = res[(s, "pyramid")]
        ec, ep1, ez = res[(s, "estimator")]
        was = RECORDED.get(s, {}).get("pyramid")
        print(f"  {s}")
        if was:
            print(f"    clip%  pyramid was {was[0]:.4f}  ->  now {pc:.4f}   "
                  f"(estimator {ec:.4f})")
            if was[1] is not None:
                print(f"    p1     pyramid was {was[1]:.0f}      ->  now {pp1:.1f}     "
                      f"(estimator {ep1:.1f})")
        # The gate: the pyramid must not clip materially more than the estimator,
        # and must not collapse the shadows relative to it.
        clip_ok = pc <= max(ec * 10.0, ec + 0.05)
        shadow_ok = pp1 >= 0.75 * ep1
        print(f"    clip gate   : {'PASS' if clip_ok else 'FAIL'}  "
              f"(pyramid {pc:.4f} vs estimator {ec:.4f})")
        print(f"    shadow gate : {'PASS' if shadow_ok else 'FAIL'}  "
              f"(pyramid p1 {pp1:.1f} vs estimator p1 {ep1:.1f})")
        verdict_all = verdict_all and clip_ok and shadow_ok

    print()
    print("  " + ("GATE PASSES -- DEFAULT_MERGE_BACKEND may move."
                  if verdict_all else
                  "GATE FAILS -- DEFAULT_MERGE_BACKEND must not move."))
    return 0 if verdict_all else 2


if __name__ == "__main__":
    sys.exit(main())

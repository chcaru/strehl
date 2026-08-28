"""Commissioning for bandsweep.boundary() and its partition guard.

WHY THIS EXISTS.  boundary() originally scanned every key in rec["bands"].
That dict carries BOTH bandsignal.BANDS and bandsignal.FINE, and BANDS contains
the wide band 0.10-0.20 whose verdict is dominated by its 0.11-0.14 content.
On flower-bud-alone-cpl the wide band PASSed at R=4.731 while its own top slice
0.17-0.20 was MARGINAL at 2.015, so the scan certified a 0.20 boundary the
subject does not have.  boundary() now reads the FINE partition only.

A fix that cannot be shown to catch the original defect is not a fix, so arm 2
REPRODUCES that exact record rather than an invented one.  Every arm's expected
answer is fixed here before it runs.

    python commission_boundary.py     # exit 0 = all arms as expected
"""
import sys

import bandsweep


def rec(bands):
    return {"key": "synthetic",
            "bands": {f"{a:.2f}-{b:.2f}": {"R": r, "lo": lo, "hi": 99.0,
                                           "verdict": v, "f_lo": a, "f_hi": b}
                      for (a, b, r, lo, v) in bands}}


def arm_wide_band_cannot_certify_its_top():
    """THE REAL DEFECT, with flower-bud-alone-cpl's own far=20 numbers.

    Wide 0.10-0.20 PASSes; fine 0.14-0.17 PASSes; fine 0.17-0.20 is MARGINAL.
    Correct answer is 0.17 -- the top of the highest FINE band that passed.
    The old scan returned 0.20 by reading the wide band's upper edge.
    """
    r = rec([(0.10, 0.20, 4.731, 2.999, "PASS"),
             (0.11, 0.14, 6.413, 3.965, "PASS"),
             (0.14, 0.17, 3.273, 2.092, "PASS"),
             (0.17, 0.20, 2.015, 1.413, "MARGINAL"),
             (0.20, 0.25, 1.342, 1.146, "MARGINAL")])
    return bandsweep.boundary(r), 0.17


def arm_fine_top_passes():
    """leaf-2-cpl's shape: 0.17-0.20 PASSes, 0.20-0.25 does not -> 0.20.

    Guards the opposite error: the fix must not clamp everything to 0.17.
    """
    r = rec([(0.10, 0.20, 4.140, 3.492, "PASS"),
             (0.14, 0.17, 3.442, 2.893, "PASS"),
             (0.17, 0.20, 2.218, 1.900, "PASS"),
             (0.20, 0.25, 1.512, 1.361, "MARGINAL")])
    return bandsweep.boundary(r), 0.20


def arm_nothing_qualifies():
    """No FINE band above 0.10 passes -> 0.0, the 'no sharpness claim' flag.

    The wide band still PASSes, so this also proves the wide band cannot
    resurrect a subject that the fine partition has ruled dead.
    """
    r = rec([(0.10, 0.20, 4.700, 3.000, "PASS"),
             (0.14, 0.17, 1.900, 1.400, "MARGINAL"),
             (0.17, 0.20, 1.200, 1.100, "FAIL(noise)")])
    return bandsweep.boundary(r), 0.0


def arm_coarse_only_does_not_count():
    """A band STRADDLING the 0.10 gate cannot certify the part above it.

    CORRECTED AFTER FIRST RUN, AND THE CORRECTION IS TO THE ARM, NOT THE CODE.
    I first wrote expected=0.11, reasoning that 0.08-0.11 reaches above 0.10.
    boundary() returned 0.0 and boundary() is right: 0.08-0.11 straddles the
    gate, so under the same principle the fix itself rests on -- a band's
    verdict may only be attributed to frequencies inside that band -- it cannot
    certify the 0.10-0.11 sliver any more than 0.10-0.20 could certify 0.17-0.20.
    That principle was written into boundary()'s docstring BEFORE this ran and
    uniquely determines 0.0; the arm was mis-derived from my own rule.  Logged
    here rather than silently amended, because an expectation edited after
    seeing the output is otherwise indistinguishable from moving the target.
    """
    r = rec([(0.02, 0.05, 80.0, 64.0, "PASS"),
             (0.05, 0.08, 31.0, 26.0, "PASS"),
             (0.08, 0.11, 11.9, 10.1, "PASS"),
             (0.11, 0.14, 1.10, 1.00, "FAIL(noise)")])
    return bandsweep.boundary(r), 0.0


def arm_partition_guard():
    """_fine_partition() must REFUSE a FINE that has a hole in it.

    Anchored on a real mutation of the module attribute, not on a string
    replace, and restored afterwards.  A guard that never fires is decoration.
    """
    keep = bandsweep.FINE
    try:
        bandsweep.FINE = [(0.02, 0.05), (0.08, 0.11)]        # 0.05 -> 0.08 hole
        try:
            bandsweep._fine_partition()
            return "no raise", "AssertionError"
        except AssertionError:
            return "AssertionError", "AssertionError"
    finally:
        bandsweep.FINE = keep


ARMS = [("wide band cannot certify its own top edge (the real defect)",
         arm_wide_band_cannot_certify_its_top),
        ("fine top band passes -> boundary is 0.20, not clamped",
         arm_fine_top_passes),
        ("nothing above 0.10 qualifies -> 0.0 despite wide band PASS",
         arm_nothing_qualifies),
        ("band straddling the 0.10 gate does not count",
         arm_coarse_only_does_not_count),
        ("partition guard refuses a non-contiguous FINE", arm_partition_guard)]


def main():
    bad = 0
    print(f"{'arm':62} {'got':>14} {'expected':>14}  verdict")
    print("-" * 108)
    for name, fn in ARMS:
        got, want = fn()
        ok = got == want
        bad += not ok
        g = f"{got:.2f}" if isinstance(got, float) else str(got)
        w = f"{want:.2f}" if isinstance(want, float) else str(want)
        print(f"{name:62} {g:>14} {w:>14}  {'ok' if ok else 'MISMATCH'}")
    print("-" * 108)
    print(f"{len(ARMS) - bad}/{len(ARMS)} arms as expected")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

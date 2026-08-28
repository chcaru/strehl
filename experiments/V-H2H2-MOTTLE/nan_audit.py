# Does a NaN read as PASS in my own instruments?
#
# V-GATHER found a NaN reaching cert.json, inert only by luck, because
# `NaN > x` is False and a NaN therefore silently satisfies a "must not exceed"
# test. ORCH relayed that as a warning to the build lane. It applies to me: my
# committed instruments return float("nan") on a degenerate input by design.
#
# Asserting "my arms fail closed" would be the exact sin this project keeps
# catching. So this measures it, and it also states the general rule precisely,
# because the warning as relayed is only half right and the half that is missing
# is the half that bites.
#
# THE POLARITY IS THE WHOLE THING. NaN comparisons are False in BOTH directions,
# so what decides the outcome is whether the comparison is the PASS predicate or
# the FAIL predicate:
#
#     pass_if  = value < limit        NaN -> False -> FAILS   (safe)
#     fail_if  = value > limit        NaN -> False -> PASSES  (unsafe)
#
# Those are the same English sentence -- "must not exceed the limit" -- written
# two ways, and only one of them is safe. ORCH's proposed hard gate for the fix
# is phrased "hull violations must not exceed shipping", which is the unsafe
# form if implemented as written.

import math
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from dilution_clamp import share_and_neff, weights  # noqa: E402

NAN = float("nan")


def polarity_demo():
    print("1. THE POLARITY TRAP, demonstrated on the exact gate ORCH proposed")
    print("   gate: 'hull violations must not exceed shipping' (shipping = 72)")
    shipping = 72.0
    for name, val in (("a good result", 40.0), ("a regression", 511.0),
                      ("a NaN", NAN)):
        fail_if = val > shipping          # "fail if it exceeds"
        pass_if = val <= shipping         # "pass if it does not exceed"
        print("     %-16s value %-8s  fail-if-greater -> %-7s  "
              "pass-if-leq -> %s"
              % (name, val, "PASS" if not fail_if else "FAIL",
                 "PASS" if pass_if else "FAIL"))
    print("   => the two phrasings AGREE on every real number and DISAGREE on")
    print("      NaN. Only `pass_if` rejects it. This is the whole finding.\n")


def audit_my_arms():
    """Every comparison my committed instruments use, evaluated at NaN.

    A NaN must make the arm FAIL. If any row reads PASS, that arm is a place
    where a degenerate computation would be reported as a success.
    """
    print("2. MY OWN ARMS AT NaN (a PASS here is a defect)")
    n = NAN
    arms = [
        ("p -> large is winner-take-all",        lambda: n > 0.9999),
        ("exact tie splits evenly",              lambda: abs(n - 0.5) < 1e-4),
        ("tie pair bitwise equal",               lambda: n == n),
        ("clamp does not bind at shipped ladder", lambda: n < 1.0 and n > 0.0),
        ("p = 0 gives 1/participants",           lambda: abs(n - 0.5) < 1e-12),
        ("clamp-removed reproduces their model", lambda: abs(n - 0.891986) < 1e-12),
        ("narrower DoF raises the share",        lambda: n > 0.1067),
        ("pyramid reconstructs",                 lambda: n < 1e-9),
        ("peak moves one level per octave",      lambda: [n] == [0]),
        ("sharper input lands finer",            lambda: n < 2.1938),
    ]
    bad = []
    for name, f in arms:
        ok = bool(f())
        print("     %-42s NaN -> %s" % (name, "PASS  <-- DEFECT" if ok else "FAIL"))
        if ok:
            bad.append(name)
    print("   => %d of %d arms would report a NaN as success\n" % (len(bad), len(arms)))
    return bad


def audit_nan_sources():
    """Can my model actually produce a NaN, and does it survive into a verdict?

    An audit of comparisons is worthless if the value can never be NaN, and
    equally worthless if it can be NaN and I never checked. Both directions are
    tested here.
    """
    print("3. CAN MY MODEL EMIT NaN AT ALL? (if not, section 2 is vacuous)")
    empty = np.array([0.5, 0.4, 0.3])     # every frame under the floor
    s, ne, part = share_and_neff(empty, 1.0, 5.488)
    print("     all frames below the floor -> share %s, n_eff %s, participants %d"
          % (s, ne, part))
    reachable = math.isnan(s)
    print("     NaN is reachable: %s" % reachable)

    w = weights(np.array([NAN, 200.0, 100.0]), 1.0, 5.488)
    print("     a NaN band energy -> weights: %s" % w)
    poisoned = bool(np.isnan(np.sum(w)))
    print("     => a NaN is NOT stopped by the `excess <= 0` guard, because")
    print("        `NaN <= 0` is False, so it passes the guard and enters")
    print("        the sum. Every normalised share is then NaN: %s" % poisoned)
    print("""
     THIS SECTION CAUGHT A DEFECT IN MY OWN MODEL. It first printed
     weights [1.0, 505.58, 10.96] -- the NaN had become weight 1.0, a
     mid-weight participant, because the log-domain placeholder was written
     `np.where(r > 0, r, 1.0)` and `NaN > 0` is False. That is strictly worse
     than a NaN: a NaN is loud and a silent 1.0 is not, and it diverged from
     the pin, whose f32 clamp and exp both propagate NaN. Fixed to
     `np.where(np.isnan(r) | (r > 0), r, 1.0)`.

     The general shape is the same one this whole script is about: a guard
     written as a positive test (`r > 0`) silently routes NaN to the ELSE
     branch. Every `np.where`, every `if x > 0`, every `max(a, b)` in a new
     weight path has this property.""")
    return reachable and poisoned


def main():
    polarity_demo()
    bad = audit_my_arms()
    reachable = audit_nan_sources()

    print("=" * 72)
    print("VERDICT")
    print("=" * 72)
    ok = (not bad) and reachable
    if bad:
        print("  RED: %d arm(s) admit a NaN as success: %s" % (len(bad), bad))
    else:
        print("  My commissioning arms all FAIL CLOSED on NaN, because every one")
        print("  of them is phrased as a PASS predicate (`value < limit`,")
        print("  `value > limit`, `a == b`) rather than as a FAIL predicate.")
        print("  That was luck of style, not design, and it is now measured.")
    if not reachable:
        print("  RED: the audit is vacuous -- no NaN is reachable, so section 2")
        print("       proves nothing about a real failure.")
    print("""
  THE ACTIONABLE PART, for whoever writes the hull-violation gate:

    Write it as   pass = (violations <= shipping)
    NOT as        fail = (violations >  shipping)

  and add a NaN to the test corpus. The two forms are indistinguishable on
  every real number, so no ordinary test separates them; only a NaN does.
  `r_max` introduces a division and a max over a possibly-empty admitted set,
  which are exactly the two NaN sources, and section 3 shows a NaN is not
  stopped by the `excess <= 0` guard -- `NaN <= 0` is False, so it passes the
  guard and poisons the whole normalised sum.
""")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

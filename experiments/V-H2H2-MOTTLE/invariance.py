"""Is the WINNER IDENTITY invariant to the exponent? (It should be, by algebra.)

Commissioning the exponent knob turned up something about my own instrument that
matters more than the commissioning result. Across arms p=0.5, p=2.0 (shipping)
and p=6.0, the winner-coherence table printed IDENTICAL numbers.

That is not a bug. The shipping weight is

    w_i = r_i ** p                      (pyramid.rs:2092, select_weight)

with the SAME p for every frame at a given band. x |-> x**p is strictly
increasing on (0, inf) for p > 0, so

    argmax_i (r_i ** p)  ==  argmax_i r_i     for all p > 0.

The winner is EXACTLY invariant to the exponent. So any acceptance metric built
on the winner's identity -- including my own coherence statistic -- is provably
blind to an exponent-based fix, and would report "no change" no matter how large
the change actually was. That is a metric that cannot fail in the direction that
matters, which is the thing this project forbids.

This script proves the invariance empirically rather than trusting the algebra,
and quantifies the ONE way it can break: select_weight clamps `(p*ln r)` to
[-80, 80] before exp, so frames far enough below the winner all collapse onto the
same clamped weight and become ties, and ties are broken by scan order.

    p * ln r < -80  =>  at p=8, r < exp(-10) = 4.54e-5

Those weights are exp(-80) ~ 1.8e-35 and cannot affect the output sum. The
disagreement they cause is bookkeeping in MY argmax, not a defect in the merge.
"""
import json
import io
import os

import numpy as np

DUMP = r"C:\dev\strehl-out\V-H2H2\wdump"
ARMS = ["null", "soft", "hard"]


def load(prefix, k):
    p = os.path.join(DUMP, "%s-b%d-arg.i32" % (prefix, k))
    return np.fromfile(p, dtype=np.int32) if os.path.exists(p) else None


def main():
    with io.open(os.path.join(DUMP, "null-dims.json"), encoding="utf-8") as fh:
        dims = json.load(fh)

    exps = {}
    for arm in ARMS:
        with io.open(os.path.join(DUMP, "%s-dims.json" % arm), encoding="utf-8") as fh:
            exps[arm] = {b["k"]: b["exponent"] for b in json.load(fh)["bands"]}

    print("winner identity vs exponent   (argmax of r**p is p-invariant by algebra)")
    print("%-3s %-22s %-22s %s" % ("k", "p null->soft", "p null->hard", "coefficients disagreeing"))
    worst = 0.0
    for b in dims["bands"]:
        k = b["k"]
        a0 = load("null", k)
        if a0 is None:
            continue
        row = []
        for arm in ("soft", "hard"):
            a1 = load(arm, k)
            adm = (a0 >= 0) & (a1 >= 0)
            n = int(adm.sum())
            d = int(np.count_nonzero(a0[adm] != a1[adm]))
            frac = d / n if n else float("nan")
            worst = max(worst, frac if frac == frac else 0.0)
            row.append((d, n, frac))
        print("%-3d %-22s %-22s soft %d/%d = %.4f%%   hard %d/%d = %.4f%%"
              % (k,
                 "%.2f -> %.2f" % (exps["null"][k], exps["soft"][k]),
                 "%.2f -> %.2f" % (exps["null"][k], exps["hard"][k]),
                 row[0][0], row[0][1], 100 * row[0][2],
                 row[1][0], row[1][1], 100 * row[1][2]))

    print()
    print("worst disagreement anywhere: %.4f%% of admitted coefficients" % (100 * worst))
    print()
    if worst < 0.02:
        print("VERDICT: the winner map is invariant to the exponent to within %.4f%%."
              % (100 * worst))
        print("  => winner COHERENCE cannot be an acceptance metric for an exponent fix.")
        print("  => winner CONCENTRATION can: it moved 0.2311 -> 0.0827 (soft) and")
        print("     -> 0.4828 (hard) at band 4, both directions, on a real render.")
    else:
        print("VERDICT: NOT invariant -- the algebra above is wrong or the clamp is")
        print("  binding much harder than expected. Investigate before trusting either arm.")


if __name__ == "__main__":
    main()

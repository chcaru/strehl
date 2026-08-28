# `averaged` cannot answer the question ORCH asked it.
#
# ORCH read pyramid.rs's banner --
#
#     averaged : 54.4% 0.0% 0.0% 0.0% 0.0% 0.0% 0.0% 100.0%
#
# -- and concluded "the gate fires on 54.4% of level-0 coefficients and on
# 0.0% at levels 1 through 6 ... at every scale except the finest, strehl is a
# naive pyramid stacker with no noise floor at all."
#
# `averaged_fraction()` is `count(den[k][i] <= 0.0) / len`, where `den` is the
# SUM of weights. It counts coefficients where *every* frame was gated out. Its
# complement is "at least one frame survived", not "no frame was gated". The
# gate can zero 298 of 299 frames at every single coefficient and `averaged`
# still reads 0.0%.
#
# This file demonstrates that by construction, using the same transcription of
# the pin's gate and weight law that dilution_clamp.py uses. It does not claim
# ORCH's CONCLUSION is false -- it may well be true. It claims this statistic
# cannot establish it, and names the two that can, both of which already exist.

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dilution_clamp import weights  # the pin's gate + select_weight, in f32


def gate_stats(e, floor, p):
    """`averaged` and the per-frame gating rate, on the same coefficients.

    `e` is (n_coeff, n_frames) band energy. Returns the fraction of
    coefficients the merge averaged (all frames gated), the fraction of
    (coefficient, frame) pairs the gate zeroed, and mean n_eff over the
    coefficients that were NOT averaged.
    """
    w = np.stack([weights(row, floor, p) for row in e])
    den = w.sum(axis=1)
    averaged = float((den <= 0.0).mean())
    gated = float((w <= 0.0).mean())
    live = den > 0.0
    if live.any():
        wl = w[live]
        neff = float(np.mean(wl.sum(axis=1) ** 2 / np.maximum((wl ** 2).sum(axis=1), 1e-300)))
    else:
        neff = float("nan")
    return averaged, gated, neff


def scenarios(n_frames=299, n_coeff=4000, p=8.0, floor=1.0, seed=7):
    """Three stacks that AGREE on `averaged` and DISAGREE on everything else."""
    rng = np.random.default_rng(seed)
    out = {}

    # (a) gate does no work: every frame far above the floor, near-tied.
    #     This is the actual "naive pyramid stacker" ORCH is worried about.
    out["gate idle (all frames admitted, near-tied)"] = \
        floor * (50.0 + rng.normal(0, 1.0, (n_coeff, n_frames)))

    # (b) gate does moderate work: half the frames pushed under the floor.
    e = floor * (50.0 + rng.normal(0, 1.0, (n_coeff, n_frames)))
    e[:, : n_frames // 2] = floor * 0.10
    out["gate zeroes half the frames"] = e

    # (c) gate does maximal work: exactly one frame clears anywhere.
    e = np.full((n_coeff, n_frames), floor * 0.10)
    e[np.arange(n_coeff), rng.integers(0, n_frames, n_coeff)] = floor * 50.0
    out["gate zeroes all but ONE frame"] = e

    return out, p, floor


def commission():
    """The statistic must be shown BLIND before its silence is interpreted."""
    print("commissioning")
    ok = True

    # 1. Potency: `averaged` must be able to move at all, or a 0.0% reading is
    #    the reading of a dead probe rather than a fact about the gate.
    dead = np.full((200, 8), 0.10)  # nothing clears a floor of 1.0
    a, g, _ = gate_stats(dead, 1.0, 8.0)
    print("    %-58s averaged=%.1f%% gated=%.1f%%"
          % ("POTENCY: nothing clears the floor", 100 * a, 100 * g))
    if a < 0.99:
        print("      FAIL: `averaged` cannot reach 1.0, so it is not measuring this")
        ok = False

    # 2. The complementary potency arm: an idle gate must read 0.0%.
    alive = np.full((200, 8), 50.0)
    a2, g2, _ = gate_stats(alive, 1.0, 8.0)
    print("    %-58s averaged=%.1f%% gated=%.1f%%"
          % ("POTENCY: everything clears the floor", 100 * a2, 100 * g2))
    if a2 > 0.01:
        print("      FAIL: `averaged` does not read 0 on a genuinely idle gate")
        ok = False

    # 3. A PLANTED IMPROVEMENT, not only degradations: n_eff must FALL when
    #    selection genuinely sharpens. A statistic that only ever rises under
    #    damage cannot distinguish a better merge from a blind one.
    near_tied = np.full((200, 16), 50.0) + np.random.default_rng(1).normal(0, 0.5, (200, 16))
    _, _, n_tied = gate_stats(near_tied, 1.0, 8.0)
    sharp = near_tied.copy()
    sharp[:, 0] = 200.0  # one frame genuinely, unambiguously best
    _, _, n_sharp = gate_stats(sharp, 1.0, 8.0)
    print("    %-58s n_eff %.2f -> %.2f" % ("IMPROVEMENT: one frame made clearly best",
                                            n_tied, n_sharp))
    if not n_sharp < n_tied:
        print("      FAIL: n_eff did not fall when selection improved")
        ok = False

    # 4. n_eff must be sane at the endpoints it claims.
    _, _, n_one = gate_stats(np.array([[100.0] + [0.1] * 15]), 1.0, 8.0)
    _, _, n_all = gate_stats(np.array([[100.0] * 16]), 1.0, 8.0)
    print("    %-58s n_eff=%.4f (want 1) / %.4f (want 16)"
          % ("ENDPOINTS: winner-take-all / plain mean", n_one, n_all))
    if abs(n_one - 1.0) > 1e-3 or abs(n_all - 16.0) > 1e-3:
        print("      FAIL: n_eff endpoints are wrong")
        ok = False

    print("    -> %s\n" % ("GREEN" if ok else "RED"))
    return ok


def main():
    if not commission():
        return 1

    scen, p, floor = scenarios()
    print("three stacks, N=299 frames, 4000 coefficients, p=%.0f, same floor" % p)
    print("%-46s %10s %10s %8s" % ("", "averaged", "frames", "n_eff"))
    print("%-46s %10s %10s %8s" % ("", "", "gated", ""))
    rows = []
    for name, e in scen.items():
        a, g, ne = gate_stats(e, floor, p)
        rows.append((name, a, g, ne))
        print("%-46s %9.1f%% %9.1f%% %8.2f" % (name, 100 * a, 100 * g, ne))

    avs = [r[1] for r in rows]
    gts = [r[2] for r in rows]
    nes = [r[3] for r in rows]
    spread_av = max(avs) - min(avs)
    spread_gt = max(gts) - min(gts)

    print("\n  spread across the three stacks:")
    print("    averaged            %.4f  <- BLIND" % spread_av)
    print("    frames gated        %.4f" % spread_gt)
    print("    n_eff               %.2f  (%.2f -> %.2f)" % (max(nes) - min(nes),
                                                            min(nes), max(nes)))
    if spread_av > 0.005:
        print("\nRED: `averaged` moved across the three stacks; the demonstration fails")
        return 1
    if spread_gt < 0.9:
        print("\nRED: the three stacks do not actually differ in gating")
        return 1

    print("""
========================================================================
FINDING
========================================================================

All three stacks report `averaged` = 0.0%. In one the gate does NOTHING; in
another it zeroes {GATED}% of all (coefficient, frame) pairs. `averaged`
cannot tell them apart, because it is `count(den <= 0)` -- the fraction where
the SUM of weights is zero, i.e. where EVERY frame was gated. Its complement
is "at least one frame survived", not "no frame was gated".

So `averaged = 0.0% at levels 1-6` does not license "the gate is not gating
at levels 1-6". It licenses only "at levels 1-6, at least one frame cleared
the floor at essentially every coefficient" -- which is equally the signature
of a gate selecting exactly one strong winner everywhere, i.e. IDEAL
behaviour, the opposite of a naive stacker.

Read the other way round: level 0's 54.4% is where the gate is so aggressive
it wipes out ALL frames and the merge is forced to average. `averaged` is a
wipeout meter, not a gating meter.

TWO FURTHER PROBLEMS WITH THE INFERENCE AS RELAYED

1. The doc's own criterion is "Near 0.0 EVERYWHERE means the gate is not
   gating" (pyramid.rs:1986-1988). It is not near 0 everywhere -- level 0 is
   54.4%. The stated premise is not met, so even the file's own loose test
   does not fire.

2. This finding is NOT NEW. merge_cmd.rs:414-419 already records it, at
   49.1%, with the same inference: "it gates at level 0 and not at all at
   levels 1-6". The quantifier error is in the codebase, and it is
   load-bearing for that comment's reasoning. ORCH's render does add
   something real -- it shows the reading SURVIVES AT HEAD with the measured
   floor active, 54.4% vs the recorded 49.1%. That part is worth having.

WHAT TO MEASURE INSTEAD -- IT ALREADY EXISTS, IN THE SAME FILE

pyramid.rs:2005-2020 documents a per-band weight dump behind WEIGHT_DUMP_ENV:

    -b<k>-neff.f32   sum(w)^2 / sum(w^2), frames effectively contributing.
                     1.0 = winner-take-all, `frames` = plain mean.
    -b<k>-conc.f32   max(w)/sum(w), the winner's share.
    -b<k>-arg.i32    winning frame index, -1 where nothing was admitted.

`neff` is exactly the quantity ORCH's question needs, and the file already
warns which of the two to use: "`conc` has null value 1/frames and therefore
falls with depth whatever the merge does" -- so `conc` must NOT be compared
across frame counts, which is precisely the comparison the dilution argument
wants to make. Dump `neff` per band on one subject and the question is
settled in one render.

CONSEQUENCE FOR MY OWN INSTRUCTIONS

ORCH told me "do not design the weight law around an assumption that the gate
is doing work above level 0. It is not." That instruction rests on this
inference. The gate's work above level 0 is UNMEASURED, not measured to be
zero. I am not going to design around either assumption until `neff` is read.

NOTE ON DIRECTION: ORCH's floor correction (measured floor is 1.07-1.55x the
white constant, so the gate is STRICTER not looser) makes an ungated coarse
band LESS likely, not more -- a higher floor gates more. The correction and
the "not gating above L0" claim pull against each other and were sent in the
same message.
""".replace("{GATED}", "%.1f" % (100 * max(gts))))
    return 0


if __name__ == "__main__":
    sys.exit(main())

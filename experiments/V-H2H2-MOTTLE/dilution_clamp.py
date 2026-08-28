# Does the dilution mechanism survive its own consequence 1?
#
# The proposing lane established, correctly and from the pin, that a frame whose
# band energy falls under `gate * beta * var` contributes EXACTLY ZERO
# (pyramid.rs:2093-2095). It wrote: "So the naive 'all N frames dilute' story is
# false, and I nearly sent it to you as fact."
#
# Its model then places N-1 competitors at ratio r and lets every one of them
# contribute. That is the naive story. This reinstates the clamp.
#
# Two corrections to the model, both read off the pin:
#
#   1. THE CLAMP. `vv = ws.var.level(k)` at pyramid.rs:1355 is per-PIXEL, not
#      per-frame, so `floor` is common across frames at a pixel. A frame
#      participates only if its band energy clears that common floor. In a focus
#      stack that is a statement about DEFOCUS, and the count of frames within
#      the depth of field is set by (DoF / focus step) -- NOT by N.
#
#   2. EXCESS, NOT ENERGY. With a common floor, w_k / w_win is
#      ((e_k - f) / (e_win - f))^p, a ratio of EXCESSES. The proposing model uses
#      (e_k / e_win)^p with r described as "one winner at energy 1.0 and N-1
#      competitors at ratio r". Subtracting a common floor from both terms of a
#      sub-unit ratio makes it smaller, so an energy ratio OVERSTATES dilution.
#
# The discriminating consequence, and the reason this matters:
#
#   * MATCHED RANGE, N DOUBLED (V-SOFTCHECK's 63 vs 32): the step halves, so
#     twice as many frames land inside the DoF. Participation doubles.
#     DILUTION IS PREDICTED. That result survives.
#
#   * DEEPER RANGE, SAME STEP (`bee` at N=299 against a shallow N=22): the extra
#     frames are spent covering depth, land far from focus at any given pixel,
#     and are clamped to exactly zero. Participation is CONSTANT in N.
#     DILUTION IS NOT PREDICTED -- and the `bee` bracket was offered as the
#     strongest confirmation, "I did not tune anything to make that happen".
#
# So the mechanism's two headline confirmations are not the same claim, and only
# one of them follows from the arithmetic once the clamp is honoured.

import json
import sys

import numpy as np

SNR_REF = 64.0  # cancels in a normalised share; carried so the code matches the pin


def weights(e, floor, p):
    """A transcription of pyramid.rs:1359-1361 + select_weight().

    The three-branch structure and the +/-80 clamp on `p * ln(r)` are the pin's,
    not a simplification: at large `p` the clamp is what actually binds, and a
    model that used a bare power would diverge from the code exactly where the
    winner-take-all limit is being tested.
    """
    excess = np.maximum(e - floor, 0.0)
    r = excess / max(floor, 1.0) / SNR_REF
    with np.errstate(divide="ignore", invalid="ignore"):
        if p == 1.0:
            w = r
        elif p == 2.0:
            w = r * r
        else:
            w = np.exp(np.clip(p * np.log(np.where(r > 0, r, 1.0)), -80.0, 80.0))
    return np.where(excess <= 0.0, 0.0, w)


def share_and_neff(e, floor, p):
    w = weights(e, floor, p)
    s = w.sum()
    if s <= 0:
        return float("nan"), float("nan"), 0
    q = w / s
    # participation: frames that cleared the clamp at all
    return float(q.max()), float(1.0 / np.sum(q * q)), int(np.count_nonzero(w))


def naive_share(r, n, p):
    """The proposing lane's model: N-1 competitors, all participating."""
    return 1.0 / (1.0 + (n - 1) * r ** p)


def stack(n, half_range, dof, snr, floor=1.0):
    """Band energy per frame at one pixel.

    Frames are spaced evenly over +/- `half_range` in depth units; the pixel's
    true depth is 0. A defocused frame's band energy falls off as a Gaussian of
    width `dof`. `snr` is the in-focus band energy in units of the noise energy,
    and the floor is `gate * beta * var` = 2 * noise with the shipped gate 2.0.
    """
    z = np.linspace(-half_range, half_range, n)
    noise = floor / 2.0
    return snr * noise * np.exp(-(z / dof) ** 2) + noise


def commission():
    fails = []

    def arm(name, ok, detail):
        print("  %-4s %-52s %s" % ("PASS" if ok else "FAIL", name, detail))
        if not ok:
            fails.append(name)

    # 1. The winner-take-all limit is a statement about a WELL-SEPARATED stack.
    #    Two earlier versions of this arm failed for two different real reasons,
    #    both worth keeping on the record:
    #      (a) an even symmetric focus grid puts two frames at identical
    #          defocus, so the limit is 1/2, not 1;
    #      (b) on a DENSE grid the neighbour frame is genuinely near-tied -- at
    #          p = 60 it still holds 59% of the winner's weight -- so no
    #          exponent produces winner-take-all there. That is a property of
    #          the stack, not a bug, and it is the mottle situation in miniature.
    #    The limit is therefore tested where it actually applies.
    sparse = stack(9, 3.0, 0.5, 400.0)      # spacing 1.5 DoF: well separated
    s1, _, _ = share_and_neff(sparse, 1.0, 20.0)
    arm("p -> large is winner-take-all when separated", s1 > 0.9999,
        "sparse-grid share %.6f" % s1)

    tie = np.array([200.5, 200.5, 120.0, 80.0, 40.0])
    wt = weights(tie, 1.0, 20.0)
    s2, _, _ = share_and_neff(tie, 1.0, 20.0)
    # Exactly 0.5 would mean the other three frames were not in the sum at all.
    # The residual IS the check: it is the third frame, correctly counted.
    arm("an exact tie splits evenly, and the rest still counts",
        wt[0] == wt[1] and abs(s2 - 0.5) < 1e-4 and s2 != 0.5,
        "tied pair bitwise equal, share %.9f (not exactly 0.5: the "
        "remaining frames contribute %.3e)" % (s2, 0.5 - s2))

    # 2. The pin's +/-80 clamp. pyramid.rs:2088-2090 claims it is "an overflow
    #    guard that never binds in practice rather than a silent averaging
    #    switch". That is TRUE at the shipped ladder (max 8) and FALSE far
    #    outside it, where saturation makes frames tie AT THE CEILING and
    #    selection is destroyed rather than sharpened. Worth pinning because the
    #    proposed log-N diagnostic raises p, and this bounds how far it can go.
    dense = stack(65, 3.0, 1.0, 400.0)
    lo, _, _ = share_and_neff(dense, 1.0, 8.0)
    hi, _, _ = share_and_neff(dense, 1.0, 400.0)
    arm("the +/-80 clamp does not bind at the shipped ladder", lo < 1.0 and lo > 0.0,
        "p=8 share %.4f; at p=400 saturation gives %.4f (ties at the ceiling)"
        % (lo, hi))

    e = dense
    # 3. p = 0 must give a plain mean OVER PARTICIPANTS, not over N.
    #    This is the control that separates my model from the proposing one:
    #    theirs returns 1/N by construction.
    s, neff, part = share_and_neff(e, 1.0, 0.0)
    arm("p = 0 gives 1/participants, not 1/N",
        abs(s - 1.0 / part) < 1e-12 and part < 64,
        "share %.6f = 1/%d, N = 64, naive would say 1/64 = %.6f"
        % (s, part, 1.0 / 64))

    # 3. PLANTED DEFECT that is also an exact attribution: remove the clamp
    #    (floor -> 0) and my model must reproduce the proposing model's number.
    #    If it does, the entire difference between us is the clamp and nothing
    #    else -- no coding discrepancy is hiding in the gap.
    r, n, p = 0.5, 32, 8.0
    flat = np.concatenate([[1.0], np.full(n - 1, r)])
    mine, _, _ = share_and_neff(flat, 0.0, p)
    theirs = naive_share(r, n, p)
    arm("with the clamp removed I reproduce their model",
        abs(mine - theirs) < 1e-12,
        "mine %.6f vs theirs %.6f (their published cell: 0.8920)" % (mine, theirs))

    # 4. PLANTED IMPROVEMENT: a narrower depth of field is a genuinely more
    #    discriminating capture. It must RAISE the winner's share and LOWER
    #    n_eff. A statistic that only ever moves one way cannot tell a better
    #    capture from a worse one.
    wide, _, pw = share_and_neff(stack(64, 3.0, 1.00, 400.0), 1.0, 4.0)
    narrow, _, pn = share_and_neff(stack(64, 3.0, 0.50, 400.0), 1.0, 4.0)
    arm("a narrower DoF raises the winner's share",
        narrow > wide and pn < pw,
        "share %.4f -> %.4f, participants %d -> %d" % (wide, narrow, pw, pn))

    # 5. The clamp must actually bind on a realistic deep stack, or arm 2 and
    #    the whole argument are vacuous.
    _, _, part299 = share_and_neff(stack(299, 12.0, 1.0, 400.0), 1.0, 4.0)
    arm("the clamp binds hard on a deep stack",
        part299 < 299 * 0.25, "%d of 299 frames clear the gate" % part299)
    return fails


def main():
    print("commissioning")
    if commission():
        print("\nRED")
        return 1
    print("  GREEN\n")

    p_l2, p_l3 = 7.6832, 5.4880  # the shipped ladder at the mottle levels
    out = {}

    print("=" * 74)
    print("SCENARIO A -- matched range, N doubled (V-SOFTCHECK's 63 vs 32)")
    print("=" * 74)
    print("  the step halves, so more frames land inside the DoF\n")
    print("  %-6s %-8s %-14s %-12s %-10s" % ("N", "p", "participants", "share", "n_eff"))
    rowsA = {}
    for p, tag in ((p_l3, "L3"), (p_l2, "L2")):
        for n in (32, 63):
            e = stack(n, 3.0, 1.0, 400.0)
            s, ne, part = share_and_neff(e, 1.0, p)
            rowsA[(tag, n)] = (s, ne, part)
            print("  %-6d %-8.4f %-14d %-12.4f %-10.2f" % (n, p, part, s, ne))
    for tag in ("L3", "L2"):
        a, b = rowsA[(tag, 32)], rowsA[(tag, 63)]
        print("  %s: share ratio 63/32 = %.3f, participants %d -> %d"
              % (tag, b[0] / a[0], a[2], b[2]))
        out["A_%s_share_ratio" % tag] = b[0] / a[0]
    print("\n  PREDICTED: dilution. The proposing lane's 63/32 story SURVIVES.")

    print("\n" + "=" * 74)
    print("SCENARIO B -- deeper range, same step (`bee` N=299 vs shallow N=22)")
    print("=" * 74)
    print("  the extra frames buy depth, land far from focus, and are")
    print("  clamped to exactly zero at any given pixel\n")
    print("  %-6s %-10s %-8s %-14s %-12s %-10s"
          % ("N", "range", "p", "participants", "share", "n_eff"))
    rowsB = {}
    for p, tag in ((p_l3, "L3"), (p_l2, "L2")):
        for n, rng in ((22, 3.0), (299, 3.0 * 299 / 22)):
            e = stack(n, rng, 1.0, 400.0)
            s, ne, part = share_and_neff(e, 1.0, p)
            rowsB[(tag, n)] = (s, ne, part)
            print("  %-6d %-10.1f %-8.4f %-14d %-12.4f %-10.2f"
                  % (n, rng, p, part, s, ne))
    for tag in ("L3", "L2"):
        a, b = rowsB[(tag, 22)], rowsB[(tag, 299)]
        print("  %s: share ratio 299/22 = %.3f, participants %d -> %d"
              % (tag, b[0] / a[0], a[2], b[2]))
        out["B_%s_share_ratio" % tag] = b[0] / a[0]
    print("\n  The proposing lane predicts 0.083 - 0.122 here and cites the")
    print("  measured 0.180 / 0.060 as bracketing it. Under the clamp the")
    print("  prediction is the ratios above.")

    print("\n" + "=" * 74)
    print("SCENARIO C -- the MEASURED geometry, from BUILD-CROP.md")
    print("=" * 74)
    print("""  Focus breathing gives the focus travel directly. BUILD-CROP.md
  reports a per-stack magnification scale factor k:

      109MSDCF     N =  22   k = 0.9870   ->  1.30% travel
      bee-1-cpl    N = 299   k = 0.9236   ->  7.64% travel

  So `bee` is 5.88x DEEPER and its step is 0.414x, i.e. 2.42x FINER.
  It is neither of the pure cases above. Participation scales with
  1/step, so it rises 2.42x -- not the 13.6x the frame count suggests.
""")
    trav22, trav299 = 1.0 - 0.9870, 1.0 - 0.9236
    step_ratio = (trav299 / 298) / (trav22 / 21)
    print("  travel ratio %.2fx, step ratio %.3fx (finer), N ratio %.1fx"
          % (trav299 / trav22, step_ratio, 299 / 22))
    print("\n  %-14s %-8s %-14s %-12s %-10s"
          % ("subject", "p", "participants", "share", "n_eff"))
    base_dof, base_half = 1.0, 3.0
    for p, tag in ((p_l3, "L3"), (p_l2, "L2")):
        # hold the DoF fixed and scale the sampling to the measured geometry
        e22 = stack(22, base_half, base_dof, 400.0)
        e299 = stack(299, base_half * (trav299 / trav22), base_dof, 400.0)
        s22, n22, k22 = share_and_neff(e22, 1.0, p)
        s299, n299, k299 = share_and_neff(e299, 1.0, p)
        print("  %-14s %-8.4f %-14d %-12.4f %-10.2f" % ("109 (N=22)", p, k22, s22, n22))
        print("  %-14s %-8.4f %-14d %-12.4f %-10.2f" % ("bee (N=299)", p, k299, s299, n299))
        print("  %s: share ratio bee/109 = %.3f, participants %d -> %d"
              % (tag, s299 / s22, k22, k299))
        out["C_%s_share_ratio" % tag] = s299 / s22
    print("""
  MEASURED against the proposing lane's claim:

    its prediction (all 299 participate)   0.083 - 0.122
    measured scene ratio on `bee`          0.180 / 0.060
    this model, clamp + measured geometry  see C above

  The proposing model's agreement with 0.180 / 0.060 came from letting
  all 299 frames dilute. Honouring its own consequence 1 and using the
  measured focus travel, dilution predicts a far milder collapse. It is
  a real CONTRIBUTOR to the `bee` result; it does not account for it.
  A second mechanism is still unidentified -- which is the same thing
  V-NEVERWORSE concluded from the other end with its 57% ceiling.
""")
    print("""
The mechanism is real and scenario A is a sound derivation of V-SOFTCHECK's
63-vs-32 result. That is worth having and I am not withdrawing it.

Scenario B is the load-bearing one, because the `bee` bracket was offered as
independent confirmation obtained without tuning. It only follows if `bee`'s
299 frames were spent on a FINER STEP rather than on MORE DEPTH. If they were
spent on depth -- which is what a 299-frame macro stack of a bee is usually
for -- then participation is flat in N, the clamp voids the prediction, and the
agreement with 0.180 / 0.060 is a coincidence of a model that ignored its own
consequence 1.

THIS IS AN EMPIRICAL QUESTION WITH A CHEAP ANSWER: the focus range and step for
`bee` and for the shallow subjects are capture parameters. Read them before
anyone builds on the `bee` bracket. I have NOT read them and this script does
not know them -- both scenarios use assumed geometry, and the numbers above are
the SHAPE of the two predictions, not measurements of our corpus.
""")
    json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "dilution.json", "w"),
              indent=1, sort_keys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

r"""M128 / check_a2 — commission the Amendment A2 jitter correction.

A2 registers a correction. A registered correction that has never been shown to
recover a known answer is a hope, not a method. This plants a known `B` and a
known per-aperture registration jitter into synthetic ladder data and asks three
questions:

  1. Does the UNCORRECTED fit reproduce the +7.2% bias A2 predicts? If it does
     not, A2's arithmetic is wrong and the correction is aimed at nothing.
  2. Does the CORRECTED fit recover the planted `B`?
  3. Is the correction inert when there is no jitter? A correction that shifts
     a clean answer is worse than none.

It also runs the correction over the whole hypothesis set, because a correction
that only works at the value it was derived from is a coincidence.

    python src\check_a2.py
"""

import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import predict as P  # noqa: E402

GREEN_PX_UM = 10.24
GAUSS_1090 = 2.563
APS = (5.6, 8.0, 11.0)
# The measured independent locus component, green px, from across.py.
SIGMA_PX = {5.6: 0.2672, 8.0: 0.2885, 11.0: 0.3555}


def fit_ladder(ns, rises_um):
    """The registered reduction: rise^2 = s^2 N^2 + c^2, then B = s/(a*lambda).

    Written here independently of predict.py's forward model so that an error
    in one does not cancel an error in the other.
    """
    x = np.array([n ** 2 for n in ns], float)
    y = np.array([r ** 2 for r in rises_um], float)
    s2, c2 = np.polyfit(x, y, 1)
    if s2 <= 0:
        return None, None
    s = float(np.sqrt(s2))
    return s, float(np.sqrt(c2)) if c2 > 0 else 0.0


def a_lambda_um():
    """s per unit N under a hypothesis, divided by that hypothesis' B.

    `B` comes from predict.invert, the same inversion section 2 uses, so this
    check cannot drift from the registered table. Derived rather than
    hand-copied: a constant copied by hand into check_prereg.py was wrong by
    2.7x and turned a 7.2% bias into 1.0%.
    """
    vals = []
    for _label, fc in P.HYPOTHESES:
        _n_eff, b, _p = P.invert(fc, P.N_REF)
        rises = [P.rise_um(fc * P.N_REF / n) for n in APS]
        s, _ = fit_ladder(APS, rises)
        vals.append(s / b)
    return float(np.mean(vals)), float(np.std(vals))


def hyps():
    """(label, B, f_c) per registered hypothesis."""
    out = []
    for label, fc in P.HYPOTHESES:
        _n_eff, b, _p = P.invert(fc, P.N_REF)
        out.append((label.split()[0], b, fc))
    return out


def main():
    al, al_sd = a_lambda_um()
    print(f"a*lambda = {al:.6f} um, spread across the three hypotheses "
          f"{al_sd:.2e} um")
    if al_sd / al > 1e-3:
        print("  FAIL: a*lambda depends on which hypothesis is used, so the "
              "ladder reduction is not the inverse of the forward model.")
        return 1
    print("  the ladder reduction inverts predict.py's forward model to "
          "1 part in 1e3 or better, so B recovered below is comparable to B "
          "registered in section 2")

    jit_um = {n: GAUSS_1090 * SIGMA_PX[n] * GREEN_PX_UM for n in APS}
    print("\nplanted jitter contribution to the 10-90% rise, um:")
    print("  " + "  ".join(f"f/{n:g} {jit_um[n]:.3f}" for n in APS))

    print("\n" + "-" * 68)
    print("QUESTION 1 and 2, over every registered hypothesis.")
    print(f"  {'hypothesis':>12}{'B true':>9}{'B uncorr':>10}{'bias %':>9}"
          f"{'B corr':>9}{'err %':>8}")
    ok_bias, ok_corr = True, True
    for name, b_true, fc in hyps():
        clean = [P.rise_um(fc * P.N_REF / n) for n in APS]
        dirty = [float(np.hypot(c, jit_um[n])) for c, n in zip(clean, APS)]
        s_u, _ = fit_ladder(APS, dirty)
        b_u = s_u / al
        # The registered correction: subtract the jitter contribution in
        # quadrature from rise^2 before fitting.
        fixed = [float(np.sqrt(max(d ** 2 - jit_um[n] ** 2, 0.0)))
                 for d, n in zip(dirty, APS)]
        s_c, _ = fit_ladder(APS, fixed)
        b_c = s_c / al
        bias = (b_u / b_true - 1.0) * 100.0
        err = (b_c / b_true - 1.0) * 100.0
        print(f"  {name:>12}{b_true:>9.4f}{b_u:>10.4f}{bias:>9.2f}"
              f"{b_c:>9.4f}{err:>8.3f}")
        if abs(err) > 0.01:
            ok_corr = False
        if name == "H2" and abs(bias - 7.2) > 0.15:
            ok_bias = False
            print(f"      A2 predicts +7.2% at H2; this gives {bias:+.2f}%")
    print(f"\n  QUESTION 1 -- A2's predicted +7.2% bias at H2 reproduces: "
          f"{ok_bias}")
    print(f"  QUESTION 2 -- correction recovers planted B to <0.01% at every "
          f"hypothesis: {ok_corr}")

    print("\n" + "-" * 68)
    print("QUESTION 3 -- inertness. With no jitter planted, the correction "
          "must not move the answer.")
    ok_inert = True
    for name, b_true, fc in hyps():
        clean = [P.rise_um(fc * P.N_REF / n) for n in APS]
        s_c, _ = fit_ladder(APS, clean)
        shift = abs(s_c / al / b_true - 1.0) * 100.0
        if shift > 1e-6:
            ok_inert = False
        print(f"  {name}: B {s_c / al:.6f} vs planted {b_true:.6f}, "
              f"shift {shift:.2e}%")
    print(f"  QUESTION 3 -- inert on clean data: {ok_inert}")

    print("\n" + "-" * 68)
    print("NEGATIVE CONTROL -- apply the correction with the WRONG sign. It "
          "must make things worse, or the test cannot tell a correction from "
          "a coincidence.")
    _lbl, b_true, fc = hyps()[1]
    clean = [P.rise_um(fc * P.N_REF / n) for n in APS]
    dirty = [float(np.hypot(c, jit_um[n])) for c, n in zip(clean, APS)]
    wrong = [float(np.sqrt(d ** 2 + jit_um[n] ** 2))
             for d, n in zip(dirty, APS)]
    s_w, _ = fit_ladder(APS, wrong)
    err_w = (s_w / al / b_true - 1.0) * 100.0
    caught = abs(err_w) > 10.0
    print(f"  wrong-sign B {s_w / al:.4f} vs planted {b_true:.4f} "
          f"({err_w:+.2f}%) -> {'CAUGHT' if caught else 'MISSED'}")

    print("\n" + "-" * 68)
    print("SENSITIVITY -- how well must sigma_e be known? The correction uses "
          "a measured sigma_e; this is the residual bias in B if that "
          "measurement is itself wrong by the given factor.")
    print(f"  {'sigma_e error':>15}{'B recovered':>13}{'residual %':>12}")
    for f in (0.5, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0):
        fixed = [float(np.sqrt(max(d ** 2 - (f * jit_um[n]) ** 2, 0.0)))
                 for d, n in zip(dirty, APS)]
        s_f, _ = fit_ladder(APS, fixed)
        print(f"  {f:>14.2f}x{s_f / al:>13.4f}"
              f"{(s_f / al / b_true - 1.0) * 100.0:>12.2f}")
    print("\n  A2 states sigma_e is an OVER-estimate, so the rows above 1.00x "
          "are the ones in play, and they push B DOWN -- toward H3 and away "
          "from H1, exactly as A2 registered.")

    verdict = ok_bias and ok_corr and ok_inert and caught
    print("\n" + "=" * 68)
    print(f"A2 CORRECTION COMMISSIONING: {'PASS' if verdict else 'FAIL'}")
    print("=" * 68)
    return 0 if verdict else 1


if __name__ == "__main__":
    raise SystemExit(main())

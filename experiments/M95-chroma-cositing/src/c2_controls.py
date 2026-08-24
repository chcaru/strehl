"""C7/C8/C9 — controls for the ROBUST estimator and the coherence gate.

The instrument changed after C1-C3 passed, so those results do not transfer.
This re-runs them on `phase_ramp_shift_robust` and adds two new ones.

C7  the naive estimator's failure, demonstrated rather than asserted.
    A large planted shift wraps the phase inside the fit band. The naive fit
    returns a confident wrong number. The robust one recovers it. If C7 does
    not show the naive estimator failing, the extra machinery is unjustified
    and should be removed.
C8  robust estimator: null, and planted shifts small AND large.
C9  the coherence gate can tell structure from noise.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m95c as C  # noqa: E402

BIN = os.path.join(C.OUT, "armF-f183.tif")
S = 256


def main():
    img = C.load_tif(BIN)
    g = img[:, :, 1].astype(np.float64)
    # Fixed, spread-out crops so this control does not depend on a selector.
    crops = [(400, 700), (900, 1500), (1400, 2200), (1700, 900)]
    res = {"crops": crops}
    ok = True

    # ------------------------------------------------ C7
    print("== C7: does the naive estimator actually fail on a large shift? ==")
    rows = []
    for plant in (0.5, 1.5, 2.5, 4.0):
        for y, x in crops[:2]:
            a = C.crop(g, y, x, S)
            b = C.shift_by(a, plant, 0.0)
            n = C.phase_ramp_shift(a, b)
            r = C.phase_ramp_shift_robust(a, b)
            rows.append(
                {"plant": plant, "y": y, "x": x, "naive_dy": n[0], "robust_dy": r[0]}
            )
            print(
                "  plant %+.2f px  naive %+8.4f (err %+7.4f)   robust %+8.4f (err %+7.4f)"
                % (plant, n[0], n[0] - plant, r[0], r[0] - plant)
            )
    naive_big = [abs(r_["naive_dy"] - r_["plant"]) for r_ in rows if r_["plant"] >= 2.5]
    robust_big = [abs(r_["robust_dy"] - r_["plant"]) for r_ in rows if r_["plant"] >= 2.5]
    c7 = max(naive_big) > 0.5 and max(robust_big) < 0.03
    print(
        "  naive worst error at >=2.5 px: %.4f   robust worst: %.4f"
        % (max(naive_big), max(robust_big))
    )
    print("  C7: %s (naive must fail >0.5 px, robust must hold <0.03 px)" % ("PASS" if c7 else "FAIL"))
    res["C7"] = {"rows": rows, "naive_worst": max(naive_big), "robust_worst": max(robust_big),
                 "pass": bool(c7)}
    ok &= c7

    # ------------------------------------------------ C8
    print("\n== C8: robust estimator, null and planted ==")
    worst_null = 0.0
    for y, x in crops:
        a = C.crop(g, y, x, S)
        d = C.phase_ramp_shift_robust(a, a)
        worst_null = max(worst_null, abs(d[0]), abs(d[1]))
    print("  null worst |component| = %.6f px (bar 0.01)" % worst_null)

    plants = [(0.0, 0.0), (-0.5, -0.5), (0.25, -0.25), (-0.25, -0.25), (3.2, -1.7)]
    worst_p = 0.0
    prows = []
    for py, px in plants:
        errs = []
        for y, x in crops:
            a = C.crop(g, y, x, S)
            b = C.shift_by(a, py, px)
            d = C.phase_ramp_shift_robust(a, b)
            errs.append(max(abs(d[0] - py), abs(d[1] - px)))
        e = max(errs)
        worst_p = max(worst_p, e)
        prows.append({"plant": [py, px], "worst_err": e})
        print("  planted (%+.2f, %+.2f)  worst err %.5f px" % (py, px, e))
    print("  planted worst = %.5f px (bar 0.03)" % worst_p)
    c8 = worst_null < 0.01 and worst_p < 0.03
    print("  C8: %s" % ("PASS" if c8 else "FAIL"))
    res["C8"] = {"null_worst": worst_null, "planted_worst": worst_p, "rows": prows,
                 "pass": bool(c8)}
    ok &= c8

    # ------------------------------------------------ C9
    print("\n== C9: does the coherence gate separate structure from noise? ==")
    rng = np.random.default_rng(7)
    coh_real, coh_noise, coh_half = [], [], []
    for y, x in crops:
        a = C.crop(g, y, x, S)
        b = C.shift_by(a, -0.5, -0.5)
        coh_real.append(C.coherence(a, b))
        na = rng.standard_normal((S, S)) * float(np.std(a))
        nb = rng.standard_normal((S, S)) * float(np.std(a))
        coh_noise.append(C.coherence(na, nb))
        # A pair that is half signal, half independent noise: the gate should
        # land between the two extremes rather than being a step function.
        coh_half.append(C.coherence(a + rng.standard_normal((S, S)) * float(np.std(a)),
                                    b + rng.standard_normal((S, S)) * float(np.std(a))))
    print("  coherence, real shifted pair : %s" % ["%.3f" % v for v in coh_real])
    print("  coherence, independent noise : %s" % ["%.3f" % v for v in coh_noise])
    print("  coherence, signal+noise      : %s" % ["%.3f" % v for v in coh_half])
    c9 = min(coh_real) > 0.8 and max(coh_noise) < 0.3
    print("  C9: %s (real >0.8, noise <0.3)" % ("PASS" if c9 else "FAIL"))
    res["C9"] = {"real": coh_real, "noise": coh_noise, "half": coh_half, "pass": bool(c9)}
    ok &= c9

    res["admissible"] = bool(ok)
    C.jdump("c2_controls.json", res)
    print("\nROBUST INSTRUMENT ADMISSIBLE: %s" % ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

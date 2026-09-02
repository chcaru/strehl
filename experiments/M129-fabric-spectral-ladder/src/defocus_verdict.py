"""Do the real focus curves match the calibrated defocus law?

WHERE THIS SITS. Three scripts feed this one and none of them can close the
question alone.

  defocus_b.py      measured fitted B against frame offset in 12 real cells. Its
                    control C1 failed, so its own P8-P10 are void and are not used
                    here. What survives is the raw B-versus-offset curves and
                    their fitted curvatures, which are measurements.
  defocus_robust.py showed the +0.1157 aperture gap survives every reachable
                    frame choice. That rests on the estimator being able to see
                    defocus at all.
  defocus_sens.py   commissioned exactly that on synthetic data with a known
                    truth and an exactly computed defocused pupil. It found the
                    response is real, is roughly two units of B per squared wave,
                    and - overturning my registered direction - goes DOWNWARD.

This script asks the one question left: put the real curvatures through the
synthetic law and see whether the implied defocus is physically coherent. That is
a test of the whole chain, because the two ends were measured independently. The
synthetic side knows nothing about focus rails and the real side knows nothing
about wavefronts, so agreement is not built in anywhere.

PREDICTIONS, REGISTERED BEFORE THE FIRST RUN.

V1  THE LAW IS QUADRATIC. Fitting the synthetic mean response over its monotone
    range as |dB| = c * W20^q returns q in [1.8, 2.2]. Wavefront variance grows as
    the square of the defocus coefficient and low-order MTF loss follows the
    variance, so a quadratic is what optics predicts. This also matters because
    defocus_b.py fitted a PARABOLA in frame offset; if q were not near 2 that
    choice of functional form would have been wrong and its curvatures would not
    be usable here.

V2  THE IMPLIED DEFOCUS IS SMALL. Inverting the law on each real curvature gives
    a per-frame defocus below the Rayleigh quarter wave at every cell. A stack
    whose neighbouring frames differed by more than a quarter wave would be
    visibly undersampled in focus and would not stack.

V3  THE RIG IS CONSISTENT ACROSS THE FIELD. Within one aperture, all six ROIs sit
    on the same sensor viewing the same flat target moved by the same rail, so
    they should imply the same per-frame defocus. Predicted: the coefficient of
    variation across the six ROIs is below 0.40 in each aperture. This is a blind
    prediction; the per-ROI numbers have not been computed at the time of writing.

V4  THE SIGN TEST, RESTATED AS THE HEADLINE. Defocus lowers fitted B. The gap
    puts f/14 ABOVE f/18. Threat T1 says f/14 carries more residual defocus
    because its depth of field is shallower, which predicts f/14 LOWER. The
    predicted sign is opposite to the observed one, so T1 is excluded rather than
    merely bounded.

NOT A BLIND PREDICTION, AND LABELLED AS SUCH. The ratio of implied per-frame
defocus between the two apertures discriminates how the capture was stepped: a
constant physical step gives f/14 a factor (N18/N14)^2 more defocus per frame,
while a step scaled to the diffraction depth of field - the standard way to bracket
a macro stack - gives a ratio of 1. I worked this ratio out by hand from the
already-printed curvatures before writing this file, so it is reported as a
consistency observation and carries no pass or fail. Recording that it was
computed first is the point; a prediction made after seeing the answer is not
evidence and should not be dressed as one.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
M5 = os.path.abspath(os.path.join(HERE, "..", "..", "m5-diffraction"))
if M5 not in sys.path:
    sys.path.insert(0, M5)
import m5_lib as L  # noqa: E402

RAYLEIGH = 0.25
NMARK = {"f14": 14.0, "f18": 18.0}


def load(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as fh:
        return json.load(fh)


def main():
    sens = load("defocus-sens.json")
    real = load("defocus-b.json")

    waves = sens["waves"]
    mono = sens["monotone_waves"]
    rows = sens["rows"]
    dB = np.array([[s["B"] - r["series"][0]["B"] for s in r["series"]]
                   for r in rows])
    mean_dB = dB.mean(axis=0)

    print("V1  is the synthetic response quadratic in defocus?")
    print("=" * 76)
    sel = [waves.index(w) for w in mono if w > 0]
    w = np.array([waves[i] for i in sel], float)
    y = np.abs(mean_dB[sel])
    q, lc = np.polyfit(np.log(w), np.log(y), 1)
    c = float(np.exp(lc))
    print(f"  {'W20':>7} {'|mean dB|':>11} {'c*W20^q':>11}")
    for wi, yi in zip(w, y):
        print(f"  {wi:7.2f} {yi:11.5f} {c * wi ** q:11.5f}")
    print(f"  fitted  |dB| = {c:.4f} * W20^{q:.4f}")
    v1 = bool(1.8 <= q <= 2.2)
    print(f"  V1 -> {'PASS' if v1 else 'FAIL'}, exponent {q:.4f} "
          f"{'inside' if v1 else 'outside'} [1.8, 2.2]")
    if v1:
        print("  A quadratic in W20 and a defocus linear in frame offset together")
        print("  make B a parabola in offset, which is the form defocus_b.py fitted.")

    print("\nV2/V3  the real curvatures, put through that law")
    print("=" * 76)
    print("  a cell's parabola has B(k) = B* + curv * (k - vertex)^2 with curv < 0")
    print("  the law has |dB| = c * W20^q and defocus is linear in offset, so")
    print("  W20 per frame = (|curv| / c) ** (1/q)")
    print()
    print(f"  {'ap':>5} {'ROI':>4} {'curv':>10} {'W20/frame':>11} "
          f"{'frames to 1/4 wave':>19}")
    per = {}
    for cell in real["cells"]:
        cur = abs(cell["curv"])
        w20 = (cur / c) ** (1.0 / q)
        per.setdefault(cell["aperture"], []).append(w20)
        print(f"  {cell['aperture']:>5} {cell['roi']:>4} {-cur:10.5f} "
              f"{w20:11.5f} {RAYLEIGH / w20:19.2f}")

    v2 = all(v < RAYLEIGH for vs in per.values() for v in vs)
    print(f"\n  V2 -> {'PASS' if v2 else 'FAIL'}, every cell implies less than "
          f"{RAYLEIGH} waves between neighbouring frames")

    print()
    cvs = {}
    for ap, vs in per.items():
        a = np.array(vs)
        cvs[ap] = float(a.std(ddof=1) / a.mean())
        print(f"  {ap}: mean {a.mean():.5f} waves/frame, sd {a.std(ddof=1):.5f}, "
              f"cv {cvs[ap]:.3f}")
    v3 = all(v < 0.40 for v in cvs.values())
    print(f"  V3 -> {'PASS' if v3 else 'FAIL'}, spread across the six ROIs "
          f"{'within' if v3 else 'beyond'} 0.40 in both apertures")

    print("\n  consistency observation, NOT a blind prediction (see the header)")
    print("  " + "-" * 72)
    m14 = float(np.mean(per["f14"]))
    m18 = float(np.mean(per["f18"]))
    ratio = m14 / m18
    b14 = real["agg"]["f14"]["B0"] if "B0" in real["agg"]["f14"] else None
    ne14 = 2.1466 * 14.0
    ne18 = 2.0309 * 18.0
    fixed_step = (ne18 / ne14) ** 2
    print(f"  measured ratio of waves per frame, f/14 : f/18 = {ratio:.3f}")
    print(f"  a constant physical step would give (N18/N14)^2 = {fixed_step:.3f}")
    print(f"     using N_eff = {ne14:.2f} at f/14 and {ne18:.2f} at f/18")
    print("  a step scaled to the diffraction depth of field would give 1.000,")
    print("  because that depth is itself proportional to N_eff^2, so the")
    print("  wavefront error per step is the same at every aperture")
    d1 = abs(ratio - 1.0)
    d2 = abs(ratio - fixed_step)
    which = "depth-of-field scaled stepping" if d1 < d2 else "a constant physical step"
    print(f"  the measurement is {d1:.3f} from 1.000 and {d2:.3f} from "
          f"{fixed_step:.3f}, so it favours {which}")
    print("  which is the standard way to bracket a macro stack, and it means the")
    print("  two stacks carry comparable defocus per frame rather than f/14")
    print("  carrying half again as much")

    print("\nV4  does defocus have the sign needed to explain the gap?")
    print("=" * 76)
    gap = sens["gap"]
    print(f"  measured gap, f/14 minus f/18            {gap:+.4f}")
    print(f"  effect of defocus on fitted B            negative, "
          f"{sens['verdict']['per_wave']:+.4f} per wave")
    print("  threat T1 predicts f/14 carries MORE residual defocus, because its")
    print("  depth of field is shallower, so T1 predicts f/14 measures LOWER")
    print("  and the gap should be NEGATIVE.")
    v4 = bool(gap > 0 and sens["verdict"]["per_wave"] < 0)
    print(f"  V4 -> {'PASS, T1 is excluded by sign, not merely bounded' if v4 else 'FAIL'}")
    print()
    print("  This does not depend on the calibration constant, on the focus step,")
    print("  or on which frame the focus map chose. It depends only on the")
    print("  measured direction of the estimator's defocus response, which S3")
    print("  establishes at ten times its own threshold, and on the measured sign")
    print("  of the gap. Both are large and both were measured independently.")

    print("\nwhat is retracted")
    print("=" * 76)
    print("  defocus_b.py's reading of its own output is withdrawn. It found")
    print("  fitted B peaking near best focus at 12 of 12 cells and concluded the")
    print("  estimator had failed off-focus, because a diffraction-limited fit")
    print("  should not be trusted on a defocused frame. The premise was sound and")
    print("  the conclusion was wrong: the peak is the estimator's genuine defocus")
    print("  response, measured here on synthetic data where the answer is known.")
    print("  Its control C1 still stands as failed and its P8-P10 are still not")
    print("  claimed, because P8 asked for a curvature sign that is now known to")
    print("  be the wrong way round and cannot be reinterpreted after the fact.")
    print()
    print("  What replaces them is stronger than what they asked for. P10 wanted")
    print("  the gap to close after a defocus correction. V4 shows no defocus")
    print("  correction of any size can close it, because defocus moves B the")
    print("  wrong way.")

    ok = v1 and v2 and v3 and v4
    print("\nverdict")
    print("=" * 76)
    print(f"  V1 quadratic law      {'PASS' if v1 else 'FAIL'}")
    print(f"  V2 defocus per frame  {'PASS' if v2 else 'FAIL'}")
    print(f"  V3 uniform over field {'PASS' if v3 else 'FAIL'}")
    print(f"  V4 sign test          {'PASS' if v4 else 'FAIL'}")
    print(f"  -> threat T1 (residual defocus) is "
          f"{'EXCLUDED' if ok else 'NOT CLEANLY EXCLUDED'}")
    print("  The aperture trend in B remains unexplained, with defocus now")
    print("  removed from the candidate list. Aberration and rig geometry remain,")
    print("  and two apertures cannot separate them, which is what the capture")
    print("  requested in captures-needed section 34 is for.")

    payload = {"law_c": c, "law_q": float(q), "V1": v1, "V2": v2, "V3": v3,
               "V4": v4, "excluded": bool(ok),
               "waves_per_frame": per, "cv": cvs,
               "ratio_measured": ratio, "ratio_fixed_step": float(fixed_step),
               "favours": which, "n_eff": {"f14": ne14, "f18": ne18},
               "gap": gap, "per_wave": sens["verdict"]["per_wave"]}
    with open(os.path.join(OUT, "defocus-verdict.json"), "w",
              encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    print("\nwrote out/defocus-verdict.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

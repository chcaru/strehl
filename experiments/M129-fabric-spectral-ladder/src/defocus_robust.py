"""What the voided defocus test still says about Amendment 9's aperture gap.

defocus_b.py's control C1 failed and its P8-P10 are not claimed. The reason is a
design flaw, and naming it is the useful part: `knee_model_fit` fits a
DIFFRACTION-LIMITED model, so it assumes the absence of exactly the extra blur the
test was trying to measure. Off best focus the roll-off is steeper than any
diffraction MTF can produce, the fit absorbs the mismatch into its slope and floor
instead of its cutoff, and the returned `f_c` stops meaning what it means at focus.
The negative curvature at 12 of 12 cells is that failure, not a physical result.

But the per-offset `B` values are measurements, not fits to a theory of focus, and
they bear on Amendment 9 whether or not the defocus question is answered. They say
how much the headline moves when the frame choice moves. Two things are checked
here, and the second is a threat that was not previously registered.

Q1  DOES THE HEADLINE SURVIVE? Amendment 9 concluded `B` <= 2.0309 and excluded
    H3's 2.4020 by 18 standard errors, using each cell's best-focus frame. If any
    reachable frame choice at f/18 pushed `B` near 2.4020 the exclusion would rest
    on the focus map rather than on the optics. Checked against the maximum over
    every cell and every offset, which is far more adversarial than any real
    frame-selection error.

Q2  DOES THE APERTURE GAP SURVIVE? This is the new threat. The gap under
    investigation is +0.1157. If `B` swings by more than that as the frame moves
    within a single stack, then a frame-selection bias that differed between the
    two apertures could manufacture the whole gap, and the trend would be an
    artefact of the focus map rather than of the optics. Reported as the worst gap
    reachable by choosing offsets adversarially - one offset for f/14 and another
    for f/18, the same offset applied to every ROI - which bounds what any
    systematic frame-selection bias could do.
"""

import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
INBAND = ["f14", "f18"]
H3_B = 2.4020


def main():
    d = json.load(open(os.path.join(OUT, "defocus-b.json"), encoding="utf-8"))
    a9 = json.load(open(os.path.join(OUT, "pixel-check.json"), encoding="utf-8"))
    cells = d["cells"]
    offs = d["offsets"]

    print("how far B moves when the frame moves")
    print("=" * 76)
    print(f"  {'ap':>6} {'n cells':>8} {'min B':>8} {'max B':>8} "
          f"{'range':>8} {'mean within-cell range':>24}")
    stats = {}
    for t in INBAND:
        r = [c for c in cells if c["aperture"] == t]
        allb = np.array([b for c in r for b in c["B"]])
        rng = np.array([max(c["B"]) - min(c["B"]) for c in r])
        stats[t] = {"min": float(allb.min()), "max": float(allb.max()),
                    "range": float(allb.max() - allb.min()),
                    "within": float(rng.mean())}
        print(f"  {t:>6} {len(r):8d} {allb.min():8.4f} {allb.max():8.4f} "
              f"{allb.max() - allb.min():8.4f} {rng.mean():24.4f}")

    print()
    print("Q1: does the exclusion of H3 survive an adversarial frame choice?")
    print("=" * 76)
    worst = stats["f18"]["max"]
    sem = a9["bound"]["sem"]
    print(f"  Amendment 9's bound came from the mean at best focus: "
          f"{a9['bound']['B']:.4f} +- {sem:.4f}")
    print(f"  the largest B any single f/18 cell reaches at ANY offset: {worst:.4f}")
    print(f"  H3 sits at {H3_B:.4f}, which is "
          f"{(H3_B - worst) / sem:.1f} s.e. above even that")
    q1 = worst < H3_B
    print(f"  Q1 -> {'PASS, the exclusion is not a property of the frame choice'if q1 else 'FAIL'}")
    print("  Every candidate contaminant, defocus included, inflates B, so a")
    print("  worse frame choice can only raise the measured value. The bound is")
    print("  one-sided in the safe direction.")

    print()
    print("Q2: could a frame-selection bias have manufactured the aperture gap?")
    print("=" * 76)
    common = [o for o in offs
              if all(o in c["offsets"] for c in cells)]
    print(f"  offsets present in every cell: {common}")
    print(f"  {'offset':>7} {'f14 mean B':>11} {'f18 mean B':>11} {'gap':>9}")
    per = {}
    for o in common:
        m = {}
        for t in INBAND:
            v = [c["B"][c["offsets"].index(o)]
                 for c in cells if c["aperture"] == t]
            m[t] = float(np.mean(v))
        per[o] = m["f14"] - m["f18"]
        print(f"  {o:>+7} {m['f14']:11.4f} {m['f18']:11.4f} {per[o]:+9.4f}")

    gaps = list(per.values())
    print()
    print(f"  gap held at a COMMON offset ranges {min(gaps):+.4f} to {max(gaps):+.4f}")
    print(f"  Amendment 9 measured {d['gap0']:+.4f} at each cell's own best frame")
    same_sign = all(g > 0 for g in gaps)
    print(f"  the gap keeps its sign at every common offset -> "
          f"{'YES' if same_sign else 'NO'}")

    adv = {}
    for t in INBAND:
        adv[t] = {o: float(np.mean([c["B"][c["offsets"].index(o)]
                                    for c in cells if c["aperture"] == t]))
                  for o in common}
    lo = min(adv["f14"][a] - adv["f18"][b] for a in common for b in common)
    hi = max(adv["f14"][a] - adv["f18"][b] for a in common for b in common)
    print()
    print("  Now the adversarial version: allow the two apertures DIFFERENT")
    print("  offsets, which is what a frame-selection bias that acted unequally")
    print("  on the two stacks would do.")
    print(f"  reachable gap spans {lo:+.4f} to {hi:+.4f}")
    q2 = lo > 0.0
    print(f"  Q2 -> {'PASS, no frame choice makes the gap vanish or reverse' if q2 else 'FAIL, a frame-selection bias could account for the gap'}")
    if not q2:
        print("  The aperture trend is NOT safe against frame selection. It must")
        print("  be reported as conditional on the focus map until section 34's")
        print("  capture, which is the same conclusion by a different route.")

    payload = {"stats": stats, "gap_by_common_offset": per,
               "gap_span_common": [min(gaps), max(gaps)],
               "gap_span_adversarial": [lo, hi],
               "f18_max_any_offset": worst, "H3_B": H3_B,
               "H3_se_above_worst": (H3_B - worst) / sem,
               "Q1": bool(q1), "Q2": bool(q2), "same_sign": bool(same_sign)}
    with open(os.path.join(OUT, "defocus-robust.json"), "w",
              encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    print("\nwrote out/defocus-robust.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

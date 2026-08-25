"""Price the Gaussian against the exponential on M111's own ladder.

ORCH handed this decision over rather than making it. The merge now contains
THREE kernels over one focus axis at one calibrated temperature:

    top-hat      1 if gap <= T else 0        merge.rs, shipping
    exponential  exp(-gap/T)                 through_focus.rs:371, diagnostic
    gaussian     exp(-0.5 (gap/T)^2)         softgate.rs, M111's new one

The scales were made identical by explicit design; the SHAPES diverged silently
because neither author had read the other's file.

WHY THIS SCRIPT IMPORTS M111'S RATHER THAN REIMPLEMENTING IT
------------------------------------------------------------
M111 says its section 15.3 machinery evaluates any monotone kernel with a
one-line change. Taking it at its word is the whole point: a comparison is only
a comparison if the two arms differ in ONE thing. Re-deriving the Stieltjes
summation here would put my arithmetic on one side of the scale and M111's on
the other, and any difference I found could be either the kernel or me. So the
masks, the bins, the Kish estimator, the population definitions and the verdict
logic are M111's, untouched and unedited on disk, and the ONLY substitution is
`KERNEL`. This is discipline 751's shape applied to a comparison instead of to
a control.

THE TRAP THIS SCRIPT IS ANCHORED AWAY FROM
------------------------------------------
-0.5 z^2 = -z has roots z = 0 and z = 2. The two kernels are EXACTLY EQUAL at
zero and at two tolerances, so any comparison anchored at z = 2 measures
nothing at all and would report a null that is a property of the anchor. The
ladder integrates over z = 0.25 .. 1e5, which spans the crossing rather than
sitting on it, and the arm below prints the kernels at the crossing so the
reader can see the coincidence rather than trip over it.

Inside z < 2 the GAUSSIAN is the heavier of the two. Only beyond z = 2 is the
exponential heavier. That ordering is the opposite of the intuition "the
exponential has the fat tail, so it is heavier", and it already falsified one
of my own directional assertions in merge.rs's tests.

CUTOFFS MATCH IN WEIGHT, NOT IN DISTANCE
----------------------------------------
Both kernels are truncated at the same WEIGHT, `WEIGHT_FLOOR = 2^-16`:

    gaussian     z_cut = sqrt(32 ln 2) = 4.7096 tolerances
    exponential  z_cut = 16 ln 2       = 11.0904 tolerances

Truncating both at one DISTANCE would silently turn a comparison of shapes into
a comparison of supports, which is a different experiment wearing this one's
name. The exponential's cutoff sits inside the ladder's span (rungs at 10, 12,
14, 16), so the ladder can resolve its tail rather than guessing at it.

WHAT WOULD MAKE THE EXPONENTIAL THE WRONG CHOICE
------------------------------------------------
Raising n_eff at SEAMS is the fix working: flat regions where the merge draws a
hard election boundary get averaged instead. Raising n_eff in TEXTURE is the
fix misfiring: a sharp pixel is sharp in few frames, and admitting far-off
frames there averages in-focus detail with out-of-focus detail. That is blur,
and it is the same direction that made `--gate 1e5` destroy the photograph.

So the number that decides this is not "which kernel admits more" but the
SEPARATION between the two populations. Pre-registered before running:

    the exponential's heavier tail beyond z = 2 will raise its TEXTURE ratio
    by more than it raises its SEAM ratio, narrowing or destroying the
    separation that made the Gaussian's prediction hold.

If that is wrong -- if the exponential separates as well or better -- I will
report it, because a pre-registration that only ever confirms is decoration.
"""

import json
import os
import sys
from pathlib import Path

import numpy as np

M111 = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M111-waxy-blobs")
OUT = Path(r"C:\dev\strehl-out\M97")
MY_RENDER = Path(r"C:\dev\strehl-out\M97\render")
sys.path.insert(0, str(M111))

import softgate_prediction as sp  # noqa: E402  (path must be set first)

WEIGHT_FLOOR = 1.0 / 65536.0
GAUSS_CUTOFF = np.sqrt(-2.0 * np.log(WEIGHT_FLOOR))  # sqrt(32 ln 2) = 4.7096
EXPO_CUTOFF = -np.log(WEIGHT_FLOOR)                  # 16 ln 2       = 11.0904

# Rungs added by `refine_for_exponential.py`. The first eight (tail) were placed
# in the span M111's ladder leaves as a single bin, gate 16 -> 64, because the
# Gaussian is already zero there and the exponential is not. `width_decomp.py`
# then MEASURED that those eight carry 0.0% of the bound width, and that 100% of
# it sits in the FIRST bin, where exp(-z)'s cusp at the origin makes it 31x
# looser than the flat-topped Gaussian. The last three (low) split that first
# bin. Both sets are kept: the tail refinement is the measurement that proved
# the tail was not the problem.
MY_GATES = [0.03, 0.06, 0.12, 18, 20, 24, 28, 32, 36, 40, 44]


def rung_path(g):
    tag = f"{g:g}".replace(".", "p")
    return MY_RENDER / f"state-g{tag}" / f"n_eff_gate{g:.2f}.npy"


def refined_ladder():
    """M111's rungs plus mine, sorted by gate.

    Order matters and is not cosmetic: the Stieltjes bins are formed as
    `maps[j] - maps[j-1]`, so an out-of-order rung produces negative counts and
    silently corrupts every bound. Sorting here and letting the monotonicity
    guard check the result is the safe form.
    """
    rungs = list(sp.LADDER)
    for g in MY_GATES:
        p = rung_path(g)
        if not p.exists():
            raise SystemExit(f"refined ladder wants {p}, which is not there. "
                             "Run refine_for_exponential.py first.")
        rungs.append((float(g), str(p)))
    return sorted(rungs, key=lambda r: r[0])


def expo(z):
    """through_focus.rs's kernel, truncated exactly as softgate.rs truncates.

    Deliberately written in the same shape as M111's `gauss` so the two differ
    in the exponent and nothing else.
    """
    z = np.asarray(z, dtype=np.float64)
    w = np.exp(-z)
    return np.where((z >= EXPO_CUTOFF) | (w < WEIGHT_FLOOR), 0.0, w)


def show_the_crossing():
    """Print the coincidence rather than let the next reader discover it."""
    print("=" * 74)
    print("THE CROSSING -- where a comparison would measure nothing")
    print("=" * 74)
    print("  -0.5 z^2 = -z  has roots  z = 0  and  z = 2")
    print()
    print("  %8s %14s %14s %12s" % ("z (tol)", "gaussian", "exponential", "g - e"))
    for z in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 4.7096, 6.0, 8.0, 11.0904):
        g = float(sp.gauss(z))
        e = float(expo(z))
        print("  %8.4f %14.8f %14.8f %12.2e" % (z, g, e, g - e))
    g2, e2 = float(sp.gauss(2.0)), float(expo(2.0))
    if abs(g2 - e2) > 1e-15:
        raise SystemExit(f"THE CROSSING IS NOT AT z=2: {g2} vs {e2} -- the "
                         "kernels are not what this script says they are")
    print()
    print(f"  at z = 2 both read {g2:.12f} -- identical to machine precision.")
    print("  INSIDE z < 2 the GAUSSIAN is heavier; only BEYOND z = 2 is the")
    print("  exponential heavier. Anchoring a comparison at z = 2 measures the")
    print("  anchor, not the kernels.")
    print()


def arm(name, kernel, cutoff, ladder, ladder_name):
    """One kernel through M111's machinery, with only `KERNEL` substituted."""
    print("=" * 74)
    print(f"ARM {name} on the {ladder_name} ladder   "
          f"cutoff {cutoff:.4f} tol   {len(ladder)} rungs")
    print("=" * 74)
    sp.KERNEL = kernel
    sp.CUTOFF = cutoff
    sp.SWAP_MASKS = False
    sp.OUT = str(OUT)
    sp.LADDER = ladder
    verdict = sp.main()
    # M111's `tag` is computed as "tophat if KERNEL is tophat else gauss", so
    # an exponential run writes a file labelled `gauss`. Relabelling it is not
    # cosmetic: a mislabelled artefact is how a number ends up cited as the
    # other kernel's, and this project has already lost twenty minutes to a
    # phantom agent for exactly that reason.
    wrong = OUT / "softgate_prediction-gauss.json"
    right = OUT / f"m97-kernel-{name}-{ladder_name}.json"
    with open(wrong) as fh:
        blob = json.load(fh)
    blob["kernel"] = name
    blob["ladder"] = ladder_name
    blob["rungs"] = [g for g, _ in ladder]
    blob["cutoff_tolerances"] = float(cutoff)
    with open(right, "w") as fh:
        json.dump(blob, fh, indent=1)
    os.remove(wrong)
    print(f"\nrelabelled -> {right.name}")
    return verdict, blob


def pull(blob):
    return (blob["populations"]["of which elected <=8"],
            blob["populations"]["textured (control-defined)"])


def sep(blob):
    s, t = pull(blob)
    return s["ratio_lo"] - t["ratio_hi"]


def check_nesting(name, coarse, fine):
    """Refining a ladder must TIGHTEN the bounds, never move the estimand.

    Both are rigorous bounds on the same quantity, so the refined interval must
    lie inside the coarse one. If it does not, the two ladders are not sampling
    one distribution -- which is exactly what would happen if my rungs came
    from a different binary than M111's -- and every number here is void.
    M111 ran this same check when it refined its own ladder.
    """
    ok = True
    for pop, c, f in zip(("seam", "texture"), pull(coarse), pull(fine)):
        inside = (f["ratio_lo"] >= c["ratio_lo"] - 1e-9
                  and f["ratio_hi"] <= c["ratio_hi"] + 1e-9)
        width_c = c["ratio_hi"] - c["ratio_lo"]
        width_f = f["ratio_hi"] - f["ratio_lo"]
        print("  %-12s %-8s coarse %5.2f-%-5.2f  refined %5.2f-%-5.2f   "
              "width %5.3f -> %-5.3f  %s"
              % (name, pop, c["ratio_lo"], c["ratio_hi"],
                 f["ratio_lo"], f["ratio_hi"], width_c, width_f,
                 "NESTED" if inside else "*** NOT NESTED ***"))
        ok &= inside
    return ok


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    show_the_crossing()

    coarse = list(sp.LADDER)
    fine = refined_ladder()
    added = sorted(set(g for g, _ in fine) - set(g for g, _ in coarse))
    print(f"coarse ladder: {[g for g, _ in coarse]}")
    print(f"refined adds : {added}   (z = {[g / 4 for g in added]})")
    print()

    vgc, bgc = arm("gaussian", sp.gauss, GAUSS_CUTOFF, coarse, "coarse")
    print()
    vec, bec = arm("exponential", expo, EXPO_CUTOFF, coarse, "coarse")
    print()
    vgf, bgf = arm("gaussian", sp.gauss, GAUSS_CUTOFF, fine, "refined")
    print()
    vef, bef = arm("exponential", expo, EXPO_CUTOFF, fine, "refined")

    print()
    print("=" * 74)
    print("DID REFINING MOVE THE ESTIMAND, OR ONLY TIGHTEN IT?")
    print("=" * 74)
    n1 = check_nesting("gaussian", bgc, bgf)
    n2 = check_nesting("exponential", bec, bef)
    if not (n1 and n2):
        raise SystemExit(
            "REFINED BOUNDS ARE NOT INSIDE THE COARSE ONES. The two ladders are "
            "not sampling one gap distribution and every number above is void. "
            "The most likely cause is rungs rendered by a different binary.")
    print("\n  Both refined intervals nest inside their coarse ones, so the extra")
    print("  rungs tightened the bounds without changing what is being bounded.")

    print()
    print("=" * 74)
    print("THE COMPARISON, on the ladder that resolves BOTH kernels")
    print("=" * 74)
    print("  %-14s %-9s %-22s %-22s %-11s %s"
          % ("kernel", "ladder", "seam ratio", "texture ratio", "separation", "verdict"))
    for nm, lad, b, v in (("gaussian", "coarse", bgc, vgc),
                          ("exponential", "coarse", bec, vec),
                          ("gaussian", "refined", bgf, vgf),
                          ("exponential", "refined", bef, vef)):
        s, t = pull(b)
        print("  %-14s %-9s %6.2f - %-13.2f %6.2f - %-13.2f %+10.3f  %s"
              % (nm, lad, s["ratio_lo"], s["ratio_hi"],
                 t["ratio_lo"], t["ratio_hi"], sep(b), v))

    gap_g, gap_e = sep(bgf), sep(bef)
    print()
    print("  Separation is seam_lo - texture_hi: positive means the ladder can")
    print("  tell the two populations apart, and larger is a cleaner separation.")
    print("  Raising n_eff at SEAMS is the fix working. Raising it in TEXTURE is")
    print("  the fix averaging in-focus detail with out-of-focus detail, which is")
    print("  blur -- the direction that made `--gate 1e5` destroy the photograph.")
    print()
    print("  The pre-registered claim was that the exponential's heavier tail")
    print("  beyond z = 2 raises TEXTURE more than SEAM and narrows the")
    print("  separation.")
    print()
    if gap_g > gap_e:
        print("  MEASURED, on the refined ladder: the GAUSSIAN separates better")
        print(f"  ({gap_g:+.3f} against {gap_e:+.3f}). The pre-registration HELD.")
        winner = "gaussian"
    elif gap_e > gap_g:
        print("  MEASURED, on the refined ladder: the EXPONENTIAL separates better")
        print(f"  ({gap_e:+.3f} against {gap_g:+.3f}). The pre-registration was")
        print("  REFUTED, and is reported as a refutation rather than buried,")
        print("  because a pre-registration that only ever confirms is decoration.")
        winner = "exponential"
    else:
        print("  MEASURED: the two separate identically. Check the anchor -- this")
        print("  is what a comparison pinned at z = 2 would say.")
        winner = "tie"

    with open(OUT / "m97-kernel-comparison.json", "w") as fh:
        json.dump({"winner_on_refined_ladder": winner,
                   "crossing_z": 2.0,
                   "coarse_rungs": [g for g, _ in coarse],
                   "refined_rungs": [g for g, _ in fine],
                   "arms": {
                       "gaussian-coarse": {"verdict": vgc, "separation": sep(bgc),
                                           "populations": bgc["populations"]},
                       "exponential-coarse": {"verdict": vec, "separation": sep(bec),
                                              "populations": bec["populations"]},
                       "gaussian-refined": {"verdict": vgf, "separation": gap_g,
                                            "populations": bgf["populations"]},
                       "exponential-refined": {"verdict": vef, "separation": gap_e,
                                               "populations": bef["populations"]}}},
                  fh, indent=1)
    print("\nwrote m97-kernel-comparison.json")


if __name__ == "__main__":
    main()

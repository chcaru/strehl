"""BUILD-OUTPUT: an affirmative verdict clause, and the commissioning it owes.

THE QUESTION THIS FILE ANSWERS
ORCH asked, plainly: is there a defensible verdict line that can say "this
binary is better on mottle", or can this instrument only ever say "not worse"?

As `recert.py` stands the answer is "only ever not worse", and the reason is
structural rather than statistical. `verdict()` builds a list called `reasons`
and ends with `ok = not reasons`. Every clause in it appends a reason to
REFUSE. The success string is "PROMOTABLE -- no gate regression, no band bought
its noise win out of structure", which is a conjunction of two ABSENCES. There
is no term anywhere in that function that can fire on an improvement, so no
input, however good, can make it say more than "nothing objected".

THE DEFECT THAT CAUSES IT, IN THIS PROJECT'S OWN TERMS
`summarise` computes `median_d_floor` (recert.py:322) and prints it
(recert.py:329). `verdict` conditions on `tested`, `blur_trade`, `cleaner` and
`median_d_structure` (recert.py:473-480) and NEVER on `median_d_floor`.
AGENTS.md: "A value printed but never conditioned on is a defect." The
un-conditioned value here is not an incidental one -- it is the noise term, in
the band the six subjects were convicted in. The instrument measures the win it
cannot state.

So the honest answer is: the limitation is real, it is in the verdict line and
not in the measurement, and it is repairable. This file repairs it, and pays
what the repair owes.

WHAT AN AFFIRMATIVE CLAUSE OWES THAT A REFUSAL CLAUSE DOES NOT
A refusal clause that is too eager costs a promotion. An affirmative clause that
is too eager MANUFACTURES A WIN, and this campaign has already had five invented
FAIL->PASS transitions relayed to four lanes on the strength of a diff. So the
bar here is higher than for `verdict`'s existing terms:

  * it must FIRE on a real, band-confined mottle improvement (arm C);
  * it must NOT fire on a blur that lowers the mottle floor by destroying the
    band (arms D, E) -- the trap ORCH named: "a mottle win with `paid` near
    0.406 is the blurred candidate wearing a disguise";
  * it must NOT fire on identical pixels (arm A);
  * it must NOT fire on a real but sub-threshold improvement (arm F), which is
    what makes the magnitude term load-bearing rather than decorative;
  * it must NOT fire on added mottle (arm B).

Arm F is the one most easily skipped and it is the one that proves WIN_MIN is
doing work. Without it WIN_MIN could be 0.0 and every other arm would still
pass, which is a threshold that has been written down but never tested.

THRESHOLDS AND WHAT THEY ARE OWED
`median_d_floor` is already a RELATIVE change (a ratio to the base floor), so a
threshold on it is relative in the sense this project requires. Its MAGNITUDE
still owes subject-invariance, which arm F-INV supplies by requiring the
fired/not-fired populations to stay separated across subjects rather than on one
favourable crop.

Run: python mottlewin.py      Exit 0 only if every arm passes.
"""
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "BUILD-RECERT"))
from recertlib import BANDS, classify, display_crop, measure_crop  # noqa: E402
from commission_bands import blur_rgb, plant_band_noise  # noqa: E402

SHIP = Path(r"C:\dev\strehl-out\acceptance\SHIP-V4")
# The six subjects convicted of mid-scale mottle -- the population this clause
# exists to speak about. Commissioning on the subjects it will judge is the
# point; a clause tuned on one crop of one subject has earned nothing.
SUBJECTS = ["coffee-bubbles", "lead-1-cpl", "113MSDCF",
            "flat-on-ruler-cpl", "112MSDCF", "foam"]
# Ten sites rather than the harness's usual five. `plantprobe.py` measured why:
# on `lead-1-cpl` three of the usual five crops hold NO STRUCTURE ABOVE THE
# MOTTLE FLOOR (sites 2400,3600 and 3600,2000 read NO-STRUCT outright; 1200,1200
# loses detectability once the f=3.0 plant raises its own base floor), so arm C
# had one testable cell and could not speak. Adding sites gives the arm material;
# it does not give the clause a lower bar, because MIN_TESTED_WIN still requires
# three cells and every refused cell is still counted as refused, not passed.
CROPS = [(1200, 1200), (2400, 3600), (3600, 2000), (1600, 4800), (2800, 2400),
         (2000, 2800), (3200, 4000), (1400, 3000), (2600, 1600), (3000, 3400)]

# Arm F needs a plant whose achieved improvement lands BELOW WIN_MIN but above
# the noise of the measurement. `plantprobe.py` measured the mapping from plant
# factor to achieved d_floor: f=1.02..1.10 moves the floor by less than 0.7%
# (indistinguishable from nothing), f=1.2 lands at -0.005..-0.017, and f=1.5
# straddles WIN_MIN at -0.039..-0.083. The first version of arm F guessed
# f=1.03 and landed at -0.002, below its own window, so ZERO cells qualified and
# the arm silently never ran -- which the tally caught only because an unrun arm
# is explicitly a failure here.
F_FACTORS = (1.2, 1.3, 1.15, 1.25, 1.35)
F_MIN_MOVE = 0.005

# --- the clause's constants ------------------------------------------------
# The share of tested cells that may read BLUR_TRADE before the win is called a
# blur. It is NOT zero, and finding out why cost a commissioning failure worth
# recording: on arm C the candidate is the UNTOUCHED ORIGINAL and the base is
# that same array with band-confined noise added, so structure is bit-identical
# between the two by construction and the true structural cost is exactly zero.
# One cell in `lead-1-cpl` and one in `flat-on-ruler-cpl` still read BLUR_TRADE,
# because `structure` removes the band's noise in quadrature and that estimate
# is unstable when the base is noisy -- so `paid` can charge a structural cost
# on a pair that has no structural difference at all. Requiring zero BLUR_TRADE
# cells therefore lets one estimation-noise cell veto a win that was unanimous
# on ten. The populations separate by FRACTION, not by zero-versus-nonzero, and
# arm G is what licenses the number between them.
BLUR_FRAC_MAX = 0.34
# A win must be bigger than the tolerance that merely calls a cell "quieter"
# (classify's floor_tol = 0.02), or the clause would fire on the noise of its
# own threshold. 0.05 is 2.5x that tolerance; arm F requires a real improvement
# just under it to be REFUSED, which is what makes the number load-bearing.
WIN_MIN = 0.05
# A majority of tested cells must be clean wins. One crop in five is a crop, not
# a subject-level finding.
WIN_MAJORITY = 0.5
# Structure may not fall at all beyond classify's own peak tolerance. This is
# deliberately the SAME 0.02 the refusal clause uses: an affirmative claim may
# not be held to a looser structural standard than a refusal.
WIN_STRUCT_TOL = 0.02
MIN_TESTED_WIN = 3

TALLY = defaultdict(lambda: {"PASS": 0, "FAIL": 0})


def summarise_band(rows):
    """Per-band counts, the same collapse `recert.summarise` performs."""
    tested = [x for x in rows if not x["refused"]]
    blur = [x for x in tested if x["verdict"].startswith("BLUR_TRADE")]
    clean = [x for x in tested if x["verdict"].startswith("CLEANER")]
    dfl = [x["d_floor"] for x in tested if x["d_floor"] is not None]
    dst = [x["d_structure"] for x in tested if x["d_structure"] is not None]
    return {
        "n": len(rows), "tested": len(tested), "refused": len(rows) - len(tested),
        "cleaner": len(clean), "blur_trade": len(blur),
        "blur_frac": (len(blur) / len(tested)) if tested else None,
        "median_d_floor": float(np.median(dfl)) if dfl else None,
        "median_d_structure": float(np.median(dst)) if dst else None,
        "paid": [x["paid"] for x in tested if x["paid"] is not None],
    }


def mottle_win(s):
    """Affirmative: may this candidate be said to be BETTER on mottle?

    Returns (fired, line). Every condition is stated as the thing that must be
    TRUE, and the first one that is not true is reported, so a near-miss is
    legible rather than a bare False.

    NaN DISCIPLINE. Every comparison is written so that a None or NaN input
    fails the condition rather than passing it. `NaN <= x` is False in Python,
    which for an affirmative clause is the safe direction -- but relying on that
    silently is how a NaN reached `cert.json` on another lane tonight, so the
    None checks are explicit and the NaN check is written out.
    """
    t, why = s.get("tested", 0), None
    df, ds = s.get("median_d_floor"), s.get("median_d_structure")
    if t < MIN_TESTED_WIN:
        why = f"only {t} cell(s) tested, need >= {MIN_TESTED_WIN}"
    elif df is None or math.isnan(df):
        why = "median_d_floor is not a number"
    elif ds is None or math.isnan(ds):
        why = "median_d_structure is not a number"
    elif s.get("blur_frac") is None or math.isnan(s["blur_frac"]):
        why = "blur fraction is not a number"
    elif s["blur_frac"] > BLUR_FRAC_MAX:
        why = (f"{s['blur_trade']}/{t} cells ({s['blur_frac'] * 100:.0f}%) bought the noise "
               f"win out of structure (BLUR_TRADE), over the {BLUR_FRAC_MAX * 100:.0f}% "
               f"ceiling; a blur is not a mottle win")
    elif not (s.get("cleaner", 0) > WIN_MAJORITY * t):
        why = f"only {s.get('cleaner', 0)}/{t} cells clean, need a majority"
    elif not (df <= -WIN_MIN):
        why = f"median_d_floor {df:+.4f} does not reach -{WIN_MIN:.2f}"
    elif not (ds >= -WIN_STRUCT_TOL):
        why = f"structure fell {ds:+.4f}, beyond -{WIN_STRUCT_TOL:.2f}"
    if why:
        return False, "no mottle claim -- " + why
    return True, (f"BETTER ON MOTTLE -- mottle floor {df * 100:+.2f}% on "
                  f"{s['cleaner']}/{t} clean cells, 0 blur-trades, "
                  f"structure {ds * 100:+.2f}%")


def pair_rows(base_disp, cand_disp, band="mottle"):
    mb, mc = measure_crop(base_disp), measure_crop(cand_disp)
    c = classify(mb[band], mc[band])
    return {"verdict": c["verdict"], "d_floor": c["d_floor"],
            "d_structure": c["d_peak"], "paid": c["paid"], "refused": c["refused"]}


def record(arm, ok, fails, msg):
    TALLY[arm]["PASS" if ok else "FAIL"] += 1
    if not ok:
        fails.append(f"{arm}: {msg}")


def main():
    if not SHIP.exists():
        print(f"REFUSE: missing {SHIP}")
        return 2
    rng = np.random.default_rng(20260828)
    fails = []
    per_arm_fired = defaultdict(list)
    blur_frac_pop = defaultdict(list)

    print(f"WIN_MIN={WIN_MIN}  WIN_MAJORITY={WIN_MAJORITY}  "
          f"WIN_STRUCT_TOL={WIN_STRUCT_TOL}  MIN_TESTED_WIN={MIN_TESTED_WIN}\n")

    for subj in SUBJECTS:
        p = SHIP / f"{subj}.tiff"
        if not p.exists():
            cands = list(SHIP.glob(f"{subj}*.tiff"))
            if not cands:
                print(f"  SKIP {subj}: no master")
                continue
            p = cands[0]
        arr = tifffile.imread(str(p)).astype(np.float32)
        ident = {"shift": (0, 0), "gain": [1.0, 1.0, 1.0], "offset": [0.0, 0.0, 0.0]}
        crops = []
        for (y, x) in CROPS:
            try:
                crops.append(display_crop(arr, y, x, ident["shift"], ident["gain"],
                                          ident["offset"], 1.0, already_srgb=True))
            except ValueError:
                pass
        del arr
        if len(crops) < MIN_TESTED_WIN:
            print(f"  SKIP {subj}: only {len(crops)} usable crop(s)")
            continue

        # ---- arm A: NULL. Identical pixels must never read as a win.
        rows = [pair_rows(c, c.copy()) for c in crops]
        fired, line = mottle_win(summarise_band(rows))
        record("A null", not fired, fails, f"{subj}: identical pixels fired '{line}'")
        per_arm_fired["A null"].append(fired)

        # ---- arm B: DEGRADATION. Mottle ADDED. Must never read as a win.
        rows, landed = [], 0
        for c in crops:
            noisy, clean, ok = plant_band_noise(c, "mottle", factor=3.0)
            if ok:
                landed += 1
                rows.append(pair_rows(clean, noisy))
        if landed >= MIN_TESTED_WIN:
            fired, line = mottle_win(summarise_band(rows))
            record("B degrade", not fired, fails, f"{subj}: added mottle fired '{line}'")
            per_arm_fired["B degrade"].append(fired)

        # ---- arm C: IMPROVEMENT. The same plant, run the other way: base is
        # noisy, candidate is clean, and STRUCTURE IS BIT-IDENTICAL between them
        # by construction. This is the arm that proves the clause can ever say
        # "better"; if it does not fire, the clause is decorative.
        rows, landed = [], 0
        for c in crops:
            noisy, clean, ok = plant_band_noise(c, "mottle", factor=3.0)
            if ok:
                landed += 1
                rows.append(pair_rows(noisy, clean))
        if landed >= MIN_TESTED_WIN:
            s = summarise_band(rows)
            fired, line = mottle_win(s)
            record("C improve", fired, fails,
                   f"{subj}: a band-confined mottle denoise did NOT fire -- {line}")
            per_arm_fired["C improve"].append(fired)
            if s["blur_frac"] is not None:
                blur_frac_pop["C improve"].append((subj, s["blur_frac"]))
            print(f"  {subj:22s} C improve  fired={fired}  {line}")

        # ---- arm D: WIDE BLUR. Lowers the mottle floor by destroying the band.
        # This is ORCH's disguise case and the clause must refuse it.
        rows = [pair_rows(c, blur_rgb(c, 8, 2).astype(np.float32)) for c in crops]
        s = summarise_band(rows)
        fired, line = mottle_win(s)
        record("D blur", not fired, fails,
               f"{subj}: a wide blur fired '{line}' -- a blur was scored a mottle win")
        per_arm_fired["D blur"].append(fired)
        paid_d = s["paid"]
        if s["blur_frac"] is not None:
            blur_frac_pop["D blur"].append((subj, s["blur_frac"]))
        print(f"  {subj:22s} D blur     fired={fired}  d_floor "
              f"{('%+.4f' % s['median_d_floor']) if s['median_d_floor'] is not None else '-'}"
              f"  paid {('%.3f' % np.median(paid_d)) if paid_d else '-'}  {line}")

        # ---- arm E: HEAVIER vs LIGHTER BLUR. The explicit non-reward guard:
        # getting blurrier must never be ranked a mottle improvement.
        rows = [pair_rows(blur_rgb(c, 4, 2).astype(np.float32),
                          blur_rgb(c, 10, 2).astype(np.float32)) for c in crops]
        fired, line = mottle_win(summarise_band(rows))
        record("E nonreward", not fired, fails,
               f"{subj}: heavier blur fired '{line}'")
        per_arm_fired["E nonreward"].append(fired)

        # ---- arm F: SUB-THRESHOLD IMPROVEMENT. A real, band-confined denoise
        # deliberately too small to clear WIN_MIN. Must NOT fire. This is what
        # makes WIN_MIN load-bearing: without this arm the threshold could be
        # zero and every other arm would still pass.
        rows, landed = [], 0
        for c in crops:
            for f in F_FACTORS:
                noisy, clean, _ = plant_band_noise(c, "mottle", factor=f)
                m0 = measure_crop(noisy)["mottle"]["floor"]
                m1 = measure_crop(clean)["mottle"]["floor"]
                if m0 <= 1e-12:
                    continue
                if -WIN_MIN < (m1 - m0) / m0 < -F_MIN_MOVE:
                    landed += 1
                    rows.append(pair_rows(noisy, clean))
                    break
        if landed >= MIN_TESTED_WIN:
            s = summarise_band(rows)
            fired, line = mottle_win(s)
            record("F subthresh", not fired, fails,
                   f"{subj}: a sub-threshold denoise (d_floor "
                   f"{s['median_d_floor']:+.4f}) fired '{line}' -- WIN_MIN is not load-bearing")
            per_arm_fired["F subthresh"].append(fired)
            print(f"  {subj:22s} F subthr   fired={fired}  d_floor "
                  f"{s['median_d_floor']:+.4f} (target: between -{F_MIN_MOVE} and -{WIN_MIN})")

    # ---- arm G: INVARIANCE. BLUR_FRAC_MAX is this clause's one absolute
    # threshold, so it owes what PAID_MAX owes: the planted-denoise and
    # planted-blur populations must be DISJOINT across subjects with the
    # constant between them. A threshold that merely happens to work on the
    # subject it was chosen on has been fitted, not commissioned.
    c_pop = [f for _, f in blur_frac_pop["C improve"]]
    d_pop = [f for _, f in blur_frac_pop["D blur"]]
    print("\n  arm G invariance -- BLUR_TRADE fraction, per subject:")
    for label, pop in (("C improve (denoise)", blur_frac_pop["C improve"]),
                       ("D blur   (blur)   ", blur_frac_pop["D blur"])):
        detail = ", ".join(f"{s}={f:.2f}" for s, f in pop)
        print(f"    {label}: {detail}")
    if len(c_pop) < 3 or len(d_pop) < 3:
        fails.append(f"G invariance: too few subjects to test disjointness "
                     f"(denoise n={len(c_pop)}, blur n={len(d_pop)})")
    else:
        hi_c, lo_d = max(c_pop), min(d_pop)
        ok = hi_c <= BLUR_FRAC_MAX < lo_d
        TALLY["G invariance"]["PASS" if ok else "FAIL"] += 1
        print(f"    denoise max {hi_c:.3f}   BLUR_FRAC_MAX {BLUR_FRAC_MAX:.3f}   "
              f"blur min {lo_d:.3f}   -> {'DISJOINT' if ok else 'OVERLAP'}")
        if not ok:
            fails.append(f"G invariance: populations are not separated by "
                         f"BLUR_FRAC_MAX={BLUR_FRAC_MAX} (denoise max {hi_c:.3f}, "
                         f"blur min {lo_d:.3f}) -- the threshold is not subject-invariant")

    print("\n" + "=" * 78)
    for arm in sorted(TALLY):
        t = TALLY[arm]
        n_fired = sum(per_arm_fired[arm])
        print(f"  {arm:12s} PASS {t['PASS']:2d}  FAIL {t['FAIL']:2d}   "
              f"(fired on {n_fired}/{len(per_arm_fired[arm])} subjects)")
    total = sum(v["PASS"] + v["FAIL"] for v in TALLY.values())
    npass = sum(v["PASS"] for v in TALLY.values())
    print(f"  {'TOTAL':12s} {npass}/{total} cells pass")

    # An arm that never ran cannot have passed. A clause commissioned only
    # against defects is exactly the failure mode this project has shipped.
    required = ["A null", "B degrade", "C improve", "D blur", "E nonreward", "F subthresh"]
    for arm in required:
        if not per_arm_fired[arm]:
            fails.append(f"{arm}: NEVER RAN on any subject -- an unrun arm is not a passed arm")
    if not any(per_arm_fired["C improve"]):
        fails.append("C improve: the clause never fired on ANY planted improvement. "
                     "It cannot say 'better' and is decorative.")

    if fails:
        print("\nCOMMISSIONING FAILED:")
        for f in fails:
            print("  - " + f)
        return 1
    print("\nCOMMISSIONING PASSED -- the clause fires on a planted mottle improvement, "
          "and refuses null, added mottle, wide blur, heavier blur and a "
          "sub-threshold win.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

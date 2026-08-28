"""Bank facts 1896-1902 from lane V-RIM's adjudication of the 13 tight-scale rim failures."""
import io
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
ANCHOR_PREFIX = "| 1895 | MEASURED | BUILD-OUTPUT |"

ROWS = [
    ("1896", "CORRECTED", "V-RIM",
     "**THE RIM GATE CONVICTS A RAW, NEVER-STACKED CAMERA FRAME, SO IT IS NOT MEASURING A "
     "STACKER DEFECT.** The 13 tight-scale FAILs adjudicate as 11 instrument artifact, 2 "
     "real-but-below-visibility, 0 real defect. The controls that settle it are the ones that "
     "are not ours: Zerene Stacker PMax reads +7.455 percent FAIL, and single captures of "
     "`coffee-bean` that were never stacked at all - no merge, no strehl anywhere in their "
     "history - read +6.741 percent FAIL and +7.579 percent FAIL. A statistic that convicts an "
     "unprocessed frame cannot be evidence about the processing. The mechanism is in the "
     "estimator: `rimv6.measure` returns `max(q[t=+2..+7]) - 1` where `q` is normalised so that "
     "`E[q]` is 1 on the bright shoulder, so it is a MAX OVER SIX SAMPLES OF A QUANTITY WHOSE "
     "EXPECTATION IS ONE, and any zero-mean shoulder fluctuation pushes the expected max above "
     "1. A rim-free image that is monotone by construction FAILs at 2 percent shoulder "
     "roughness per step, reading +2.304 percent against `RIM_MAX` of 0.02, and +28.35 percent "
     "at 30 percent roughness. Verdict: **rim-unconvicted at tight scale** - stronger than "
     "rim-unexamined, weaker than rim-clean. It does not block print readiness and it cannot "
     "support a claim either."),

    ("1897", "MEASURED", "V-RIM",
     "**A BIAS-SUBTRACTION FLOOR MEASURED ON A SMOOTHED IMAGE CANNOT REMOVE A BIAS THAT ONLY "
     "EXISTS IN THE UNSMOOTHED ONE.** The rim axis subtracts a floor to cancel its pedestal, and "
     "the floor is measured on the sigma equals 3 smoothed image - precisely the image in which "
     "the shoulder fluctuation driving the pedestal has been destroyed by construction. So the "
     "correction is computed where the defect is absent and applied where it is present, and it "
     "cancels nothing. The read-across arm prices the damage: on a rim-free image evaluated at "
     "each master's OWN measured shoulder sd, the rim-free pedestal is greater than or equal to "
     "the master's own reading for 11 of 13 subjects, and `lead-1-cpl` reads +3.36 percent where "
     "rim-free reads +18.64 percent, 5.5 times larger. Generalises past this axis: **a "
     "correction term must be estimated on the same signal it is subtracted from**, and a floor "
     "fitted on a filtered copy is a different quantity wearing the same name."),

    ("1898", "CORRECTED", "V-RIM",
     "**THE THIRTEEN RIM FAILURES WERE MEASURED ON A RENDER THAT IS NOT THE DELIVERABLE.** "
     "`experiments/V-RIM/rimaxis.py:52` sets `SEAL_DIR` to `acceptance\\SHIP-V4` rather than the "
     "delivered masters, and the two are genuinely different renders, not copies: about 99.7 "
     "percent of samples differ, mean absolute 398.9 DN on `112MSDCF` and 931.2 DN on "
     "`leaf-2-cpl`, max 22764 DN. Re-pointing at `ORCH-FAITHFUL\\faithful` moves the tally from "
     "9 PASS 13 FAIL 4 REFUSED to **9 PASS 12 FAIL 5 REFUSED**, flips `112MSDCF` from FAIL to "
     "REFUSED, and swings `leaf-2-cpl` from +37.07 percent to +12.92 percent - a factor of 2.9 "
     "on the second-worst subject in the set. Every number in fact 1881 therefore describes "
     "output that does not ship. The wider lesson is cheap and was paid for twice tonight: **an "
     "instrument's input path is part of its calibration**, and a hard-coded directory constant "
     "is exactly the kind of thing that survives a rename and silently redirects a whole axis."),

    ("1899", "MEASURED", "V-RIM",
     "**TWO SUBJECTS WERE CONVICTED IN VIOLATION OF THE AXIS'S OWN WRITTEN REFUSAL RULE, BECAUSE "
     "THE RULE WAS NEVER WIRED UP.** `rimaxis.py:57` defines `MIN_ISOLATED = 0.20` and the "
     "docstring states that subjects below it are REFUSED as unmeasurable. The name appears "
     "**exactly once in the entire repository, at its own definition** - it is read by nothing. "
     "`wrapped-text-1` at 16.2 percent and `wrapped-text-2` at 12.1 percent are both below the "
     "declared threshold and both were scored and failed. A companion defect in the same gate: "
     "`printcert4.rim_verdict` convicts on `corrected_bright` alone, so `flower-bud-alone-cpl` "
     "PASSES while reading `corrected_dark` +4.51 percent, and under a planted unsharp mask the "
     "dark-over-bright ratio reaches 1.04 - **a one-sided gate cannot be measuring ringing**, "
     "which is symmetric by definition. A declared guard that nothing reads is worse than an "
     "absent one, because the docstring is what the next reader trusts."),

    ("1900", "MEASURED", "V-RIM",
     "**AN AMPLITUDE SANITY CHECK CONVERTS AN ABSTRACT PERCENTAGE INTO SOMETHING A HUMAN CAN "
     "REFUTE BY LOOKING.** An unsharp-mask ladder on `109MSDCF` - the only subject whose zero "
     "sits near zero - reads +10.22 percent at amount 4.0, radius 2.0. `wrapped-text-2` reads "
     "+10.93 percent, so the gate is asserting a rim STRONGER THAN A FOUR-TIMES UNSHARP MASK, "
     "and nothing remotely like that is present in the pixels. Corroborated at 1:1 at the "
     "instrument's own worst sites: `leaf-2-cpl` at +37.07 percent has its **worst four sites in "
     "flat out-of-focus background with no edge in frame at all**, and `coffee-bean` at +33.25 "
     "percent is bean-surface crystal with no occluding edge, reading +8.36 percent on a 2048 px "
     "crop of itself, so the number is crop-dependent. **Price every threshold in a unit the eye "
     "can adjudicate before trusting it**; a percentage with no physical referent cannot be "
     "argued with."),

    ("1901", "MEASURED", "V-RIM",
     "**THREE RIM-LIKE AXES EXIST AT THREE DISJOINT SCALES AND NONE OF THEM RETIRES ANOTHER.** "
     "`rimv6` walks plus or minus 12 px; `halo_profile` walks 2 to 120 px with its far reference "
     "at 400 to 900 px; and a separate earlier axis in `docs/research/V-RIM-verification.md` "
     "uses a 0 to 140 px ring window with a 170 to 300 px null and reports **RING on 5 of 14 "
     "measurable subjects** - `coffee-bean`, `lavendar-cpl`, `flower-bud-alone-cpl`, "
     "`bee-3-cpl`, `flower-bud-with-background-fern-cpl`. Three of those five are also among the "
     "thirteen, which is exactly the coincidence that invites conflation. **The tight-scale "
     "acquittal says nothing about the mid-scale ring axis, which remains live and "
     "unadjudicated.** Two bands are additionally unwalked by anyone: 9 to 120 px and 120 to 400 "
     "px - and the second is the geometry where a halo's decay separates from ordinary scene "
     "lighting falloff, which is what produced `halo_profile`'s four false HALO positives in the "
     "first place."),

    ("1902", "MEASURED", "V-RIM",
     "**A COMMISSION SUITE PASSING 11 OF 11 ESTABLISHED ONLY SENSITIVITY, BECAUSE EVERY ARM WAS "
     "A VARIANT OF THE SAME IMAGE.** `rimcommission.py` passes 11/11 and contains no specificity "
     "arm: its `FLOOR` arm tests the sigma equals 3 smoothed base and its `NOTALWAYS` arm tests "
     "the unmodified master, and **neither is a sharp image known to be rim-free**. The planted "
     "rim arm shows a clean monotone response, so the instrument genuinely is not inert - "
     "sensitivity was real and was the only thing ever measured. Adding the missing arm reversed "
     "the axis's verdict on 11 of 13 subjects. This is the fourth entry in the instrument "
     "failure catalogue to reduce to the same sentence: **sensitivity and specificity are "
     "different measurements, an instrument can have all of one and none of the other, and only "
     "the arm you did not run can tell you which you have.**"),
]


def build_row(num, kind, lane, body):
    if "|" in body:
        raise SystemExit(f"fact {num}: raw pipe in body")
    if body.count("*") % 2 != 0:
        raise SystemExit(f"fact {num}: odd asterisk count")
    return f"| {num} | {kind} | {lane} | {body} |\n"


def main():
    with io.open(PATH, "r", encoding="utf-8", newline="") as fh:
        lines = fh.readlines()

    hits = [i for i, ln in enumerate(lines) if ln.startswith(ANCHOR_PREFIX)]
    if len(hits) != 1:
        raise SystemExit(f"anchor matched {len(hits)} lines, expected exactly 1")
    at = hits[0]

    for num, _, _, _ in ROWS:
        if any(ln.startswith(f"| {num} |") for ln in lines):
            raise SystemExit(f"fact {num} already present")

    new = [build_row(*r) for r in ROWS]
    lines[at + 1:at + 1] = new

    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.writelines(lines)

    print(f"inserted {len(new)} rows after fact 1895 (line {at + 1})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

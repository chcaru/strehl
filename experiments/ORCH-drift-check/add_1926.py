"""Bank facts 1926-1932 from lane V-RIM's second pass: clamp closed, mid-scale axis adjudicated."""
import io
import re
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
EXPECTED_TAIL = 1925

ROWS = [
    ("MEASURED", "V-RIM",
     "**THE INTERPOLATION CLAMP IS CLOSED: THE RIM-FREE LADDER NOW EXTENDS BY DIRECT MEASUREMENT "
     "TO ACHIEVED SHOULDER SD 0.3930, COVERING ALL THIRTEEN TIGHT-SCALE FAILURES WITH NO "
     "`np.interp` ANYWHERE.** The earlier acquittals rested on a ladder that ran out and was "
     "extrapolated; it no longer is. `leaf-2-cpl` is **acquitted** at a pedestal of **+45.39 "
     "percent** against a reading of **+37.07 percent**. `coffee-bean` is **NOT acquitted on this "
     "route**, reading **+33.25 percent against a measured pedestal of +28.84 percent**, i.e. 4.4 "
     "points above its own floor. Recorded as a partial result rather than smoothed into the "
     "earlier verdict, because **the value of closing a clamp is lost if the closure is only "
     "reported where it confirms.**"),

    ("MEASURED", "V-RIM",
     "**A SECOND, INDEPENDENT PEDESTAL ROUTE PUTS TWELVE OF THE THIRTEEN BELOW THE RIM-FREE "
     "FLOOR, AND ITS CONSTRUCTION IS THE POINT.** An isotonic PAV pedestal was computed **in "
     "place on `rimv6`'s own profile array**, preserving every per-edge residual bit-exact so "
     "that shoulder roughness - the quantity actually under test - is provably untouched by the "
     "correction being applied to it. This is the direct repair of the earlier defect in which a "
     "correction term was estimated on a smoothed image where the bias had been destroyed by "
     "construction. Both PASS controls read **exactly 0.000 percent** coherent excursion. The "
     "sole exception, `pencil-steep-angle-cpl`, implies a rim of **1.2 percent of the local edge "
     "step**, below the planted ladder's resolution and therefore below what the instrument can "
     "honestly call a defect."),

    ("MEASURED", "V-RIM",
     "**THE TWO PEDESTAL ROUTES LEAVE DIFFERENT SINGLE EXCEPTIONS AND NO SUBJECT FAILS BOTH, "
     "WHICH IS THE SIGNATURE OF A NULL AT THE MARGIN RATHER THAN OF A DEFECT.** A real rim would "
     "be convicted by both constructions; noise at threshold is convicted by whichever one "
     "happens to sit closer to it on a given subject. **This is a reusable adjudication rule for "
     "borderline findings: build two estimators that differ in construction rather than in "
     "tuning, and ask whether the exception set is stable.** A finding that survives only one "
     "route has told you about the route."),

    ("MEASURED", "V-RIM",
     "**THE ONE UNEXPLAINED EXCESS WAS PROBED FOR ITS MOST LIKELY BENIGN CAUSE AND THAT CAUSE WAS "
     "REFUTED, SO IT REMAINS OPEN RATHER THAN RESOLVED.** `coffee-bean`'s 4.4-point excess over "
     "its rim-free pedestal is **not** explained by heavy-tailed shoulder statistics: excess "
     "kurtosis **-1.60 against a synthetic -1.58** at matched sd, and p99.9 of **1.98 against "
     "1.93** - both essentially identical, so the tail shape is ordinary. Its acquittal therefore "
     "rests on the pixels and on the never-stacked control captures alone, **one leg rather than "
     "three**, and is recorded that way."),

    ("CORRECTED", "V-RIM",
     "**THE MID-SCALE RING RESULT IS NOT REPRODUCIBLE BY ANYONE, INCLUDING ITS AUTHOR, BECAUSE "
     "EVERY ARTIFACT IT DEPENDS ON HAS BEEN DELETED.** It rendered its own inputs with a binary "
     "pinned at `1cacb61` into a scratch tree; **that tree, its `json2` outputs, and the binary "
     "are all gone**, and `summarise.py` hardcodes the vanished path so it cannot run at all. Its "
     "published **5-of-14 RING** result reads like current evidence and is not. **The general "
     "hazard is specific and worth stating: scratch-tree hygiene and reproducibility are in "
     "direct tension, and a result whose inputs live only in a directory scheduled for deletion "
     "has a shelf life nobody wrote down.** The honest consequence here is that the one "
     "hypothesis which would make the published result correct as written - that strehl simply "
     "improved between `1cacb61` and now - is **permanently untestable**."),

    ("MEASURED", "V-RIM",
     "**RE-RUN UNCHANGED ON EVERYTHING THAT STILL EXISTS, THE MID-SCALE RING INSTRUMENT FINDS "
     "NOTHING: FIFTEEN MEASUREMENTS, ZERO RING.** Run on the deliverable, on SHIP-V4, and on the "
     "deliverable with the sRGB curve undone, the readings sit **25 to 80 times below the "
     "published amplitudes**, and **eight of nine subjects read at or below their own rim-free "
     "floor**. The instrument itself is not the problem - its ratio rule is sound at **zero false "
     "positives in 432 trials**. Verdict: **the mid-scale ring axis does not block print.** "
     "Corroborated by eye at the orchestrator's own inspection of the unstretched panels, where "
     "no band is visible."),

    ("MEASURED", "V-RIM",
     "**A THIRD DISTINCT DEFECT IN THE TIGHT-SCALE INSTRUMENT: IT MEASURES NUMBERS OFF FILES "
     "WHOSE OWN PROVENANCE FORBIDS EXACTLY THAT.** `rimaxis.py:52` points `SEAL_DIR` at "
     "`acceptance/SHIP-V4`, whose provenance files state that the colour space is sRGB **with the "
     "tone curve applied** and carry the instruction **DO NOT MEASURE NUMERICALLY**, and whose "
     "subjects were each rendered with per-subject auto-exposure. Three independent defects have "
     "now been found in one instrument by reading its source rather than its output. **The "
     "pattern across all three is identical and is the finding: every one is an input-path or "
     "reference-selection error, not an error in the statistic.** Instrument review that reads "
     "only the estimator will keep missing this entire class."),
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

    ids = [int(m.group(1)) for m in
           (re.match(r"^\|\s*(\d+)\s*\|", ln) for ln in lines) if m]
    tail = max(ids)
    if tail != EXPECTED_TAIL:
        raise SystemExit(f"tail is {tail}, expected {EXPECTED_TAIL} — re-read before banking")

    hits = [i for i, ln in enumerate(lines) if ln.startswith(f"| {tail} |")]
    if len(hits) != 1:
        raise SystemExit(f"anchor matched {len(hits)} lines, expected exactly 1")
    at = hits[0]

    new = []
    for offset, (kind, lane, body) in enumerate(ROWS, start=1):
        num = tail + offset
        if any(ln.startswith(f"| {num} |") for ln in lines):
            raise SystemExit(f"fact {num} already present")
        new.append(build_row(num, kind, lane, body))

    lines[at + 1:at + 1] = new
    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.writelines(lines)
    print(f"inserted {len(new)} rows ({tail + 1}-{tail + len(new)}) after fact {tail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

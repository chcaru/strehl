"""Bank facts 1851-1864 into SYNTHESIS.md.

Anchors on the full text of the row it inserts after and hard-errors if that
anchor is not unique, because an anchor that matches twice inserts in the wrong
place silently and an anchor that matches zero times is a no-op that still
exits 0. Also refuses raw pipes (they truncate a table row) and odd asterisk
counts (they leave italics open and swallow the rest of the table).
"""
import io
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

ANCHOR_PREFIX = "| 1850 | ARGUED | ORCH |"

ROWS = [
    ("1851", "MEASURED", "V-REVIEW",
     "**THE HALO INSTRUMENT NEVER MEASURED THE ONE REGION WHERE A HALO AND A LIGHTING FALLOFF DIFFER.** "
     "`halo_profile.py` walks the near profile from 2 to 120 px and takes its far-field reference at 400-900 px. "
     "Nothing between 120 and 400 px is examined. A genuine halo decays within roughly 100 px; a scene lighting "
     "falloff does not, so the decay signature that separates them lives entirely inside the unmeasured gap. "
     "The hole is structural, not a tuning choice. Filling it with the same Voronoi walk and the same far field "
     "(`vh_hole.py`, four clean controls) is what overturned all four HALO verdicts."),

    ("1852", "MEASURED", "V-REVIEW",
     "**ALL FOUR HALO VERDICTS ARE FALSE POSITIVES, AND THREE FIRE ON A SCENE GRADIENT.** "
     "`flat-on-ruler-cpl` flagged +5680 DN reads +6098 DN at 120-170 px, i.e. it PEAKS OUTSIDE the measured "
     "region at 107% of the flagged value and then decays over 400 px, which is a falloff and not a halo. "
     "`119MSDCF` flagged +820 DN reads +944 / +914 / +1065 DN out to 900 px and NEVER decays. "
     "`lavendar-cpl` flagged +351 DN sits on a background spanning 2879 DN. "
     "`tweezers-cpl` bump 1567 DN is one step in a ramp spanning 22461 DN with overshoot -15519 DN. "
     "Most studio subjects have a graduated backdrop, so this is a mechanism and not a coincidence."),

    ("1853", "MEASURED", "V-REVIEW",
     "**A SECOND COVERAGE DEFECT RAN THE OPPOSITE WAY AND LET FOUR SUBJECTS PASS ON A PARTIAL WALK.** "
     "`vals` breaks at the first pinched band while `bands` keeps all seven, so how much of the profile was "
     "actually examined is invisible in the output. Four subjects report clean from a 4-of-7 or 5-of-7 walk. "
     "`leaf-2-cpl` reports clean on its 20-32 px value while carrying a +5721 DN excursion at 50-80 px that "
     "was never examined. The same instrument therefore produced false verdicts in BOTH directions."),

    ("1854", "MEASURED", "V-REVIEW",
     "**NO HALO IS DEMONSTRATED ON ANY DELIVERED SUBJECT, AND THE RESIDUAL RISK IS ELEVEN SUBJECTS RATHER THAN FOUR.** "
     "Partition over the 26 delivered masters, summing to 26: 0 visible / 4 measured-but-not-visible / "
     "11 clean on a full walk / 4 clean-but-blind / 7 unmeasurable. This retires the corpus-wide halo verdict "
     "of '7 clean, 4 HALO, 15 unmeasurable' that ORCH had been broadcasting to the owner and to fifteen lanes. "
     "Demonstrating no halo is NOT the same as demonstrating the absence of halos; the 4 blind and the 7 "
     "unmeasurable are UNSCORED and must never be counted as clean."),

    ("1855", "MEASURED", "V-REVIEW",
     "**THE HALO INSTRUMENT IS LEAST SENSITIVE TO EXACTLY THE SHAPE IT FLAGGED.** "
     "Against a planted calibration ladder its detection floor is about 4500 DN for a NARROW rim, and only via "
     "the `bump` statistic. A BROAD rim stayed at `bump 0.0` and read clean at 9000 DN, which is twice the "
     "amplitude of anything it flagged. `flat-on-ruler-cpl` was flagged on a broad excursion. An amplitude "
     "threshold cannot fix this; the recommended replacement is a DECAY test keyed to the mechanism in 1851, "
     "which tightens the instrument rather than loosening it."),

    ("1856", "MEASURED", "BUILD-DEFECT",
     "**THE FLATS-DERIVED DUST MAP IS MIS-REGISTERED AND MUST NOT SHIP; THE PHOTOGRAPHS FIND THE REAL MOTES.** "
     "Of the four motes the flat fields nominate, scored on 12 real subject stacks, three read +0.2001% / "
     "+0.1571% / +0.5398% at p = 0.9900 / 0.9501 / 1.0000, i.e. not there at all. Re-locating on the "
     "photographs finds TWO real motes, (3202,121) at -3.6303% and (3434,2305) at -8.2359%, both p = 0.0025, "
     "displaced 16 and 25 quads from the flats coordinates; three flats components are fragments of one mote. "
     "Correcting at the flats coordinates would brighten clean pixels beside an uncorrected mote."),

    ("1857", "MEASURED", "BUILD-DEFECT",
     "**M71'S DUST MASK IS A BORDER ARTEFACT.** 99.93% of it lies within 40 quads of a frame edge, an "
     "enrichment of 17.8x, with a ring profile falling from -0.9340% at d=0 to -0.0030% at d=40. "
     "M71's own roll control was structurally incapable of catching this, because rolling a border-concentrated "
     "mask still lands on a border. A blind search for further dust cannot be commissioned on this corpus at all: "
     "every plant-sensitive setting has a roll null of 22-434 false components and every null-clean setting is "
     "blind, so scripts 12 and 14 REFUSE rather than report least-bad candidates."),

    ("1858", "MEASURED", "BUILD-DEFECT",
     "**THE HOT-PIXEL ARM IS A NULL AND SHIPS OFF, AND THE 'TRAILS' PREMISE IT WAS COMMISSIONED ON IS REFUTED.** "
     "14,626 candidate sites reproduce M101 to +0.2% with row asymmetry 60.97x against M101's 61.1x, but only "
     "111 survive an 8 electron reproducible floor. Three ORCH brief premises were wrong and are corrected here: "
     "there are 242 dark frames in 11 ISO groups rather than 22; 20 of the 26 stacks are f/5.6 so M71's "
     "lower-bound caveat does not apply; and warp-smeared hot-pixel trails are not present."),

    ("1859", "MEASURED", "BUILD-DEFECT",
     "**SEVEN OF TEN CONCLUSION REVERSALS PASSED A SHIPPED VERIFIER WITH EVERY NUMBER LEFT CORRECT.** "
     "Auditing all four section verifiers through their real entry points, on the real document, by exit code: "
     "reversing which side of the optical path two motes are on, and turning 'a flag did nothing' into 'two "
     "different images' with all four table numbers intact, were both invisible. Now 10 of 10 caught. "
     "This is the FOURTH independent lane to find its own verifier blind to a reversed conclusion, after "
     "V-NEVERWORSE at 712 green, V-LINEAR at 88/88 green, and V-KILLB0 whose verdict lived only in prose. "
     "Presence-testing is the natural thing to write and it cannot detect polarity."),

    ("1860", "MEASURED", "BUILD-DEFECT",
     "**COMMISSION DELETION AS WELL AS REVERSAL, AND COMMISSION THE PASS/FAIL CHANNEL ITSELF PER VERIFIER.** "
     "Deleting a finding is cheaper than stating it wrongly, so a harness that catches reversals can still be "
     "blind to removal; tested explicitly at 9 of 9. Separately, a first positive control read exit 0 and looked "
     "exactly like a dead exit code but was not: the corrupted line was prose the checker never re-derives. "
     "AN INERT PLANT AND A DEAD INSTRUMENT GIVE THE IDENTICAL GREEN, so the 2x2 (clean to 0, planted digit to "
     "non-zero, innocuous prose to 0) must be run per verifier and not per suite."),

    ("1861", "MEASURED", "BUILD-CROP",
     "**THE VISIBLE MAGENTA DEFECT IS STREHL'S OWN LATERAL-CA CORRECTION OVER-CORRECTING RED, NOT THE MERGE.** "
     "The correction moves red from -2.009 px inward PAST ZERO to +0.672 px outward while blue stays outward, "
     "so R and B land on the SAME side of every edge and pile up as magenta. Real lateral CA moves R and B in "
     "OPPOSITE directions, so magenta is the signature of the correction rather than of the optics. "
     "With `STREHL_FIX_CA=off` all three channels are bit-exact at 0 DN. The merge is exonerated twice over: "
     "a single frame carries LARGER CA than the 299-frame master, -3.212 px against -2.009 px at the corner."),

    ("1862", "MEASURED", "BUILD-CROP",
     "**THE SHIPPING DEFAULT IS 1.82x WORSE THAN SWITCHING THE CORRECTION OFF, AND THE FINGERPRINT IS CORPUS-WIDE.** "
     "Edge magenta 1.4447% with the correction on against 0.7939% with it off; 806 against 408 magenta pixels "
     "in the interrogated rect; edge-to-flat ratio 157x confirms displacement rather than a colour cast. "
     "13 of 14 coherent subjects carry red displaced outward and 12 of 14 have R and B the same sign, which is "
     "the over-correction fingerprint. Only `highly-angled-ruler-mm-cpl` still shows the lens's natural "
     "opposite-sign pattern, which makes it the built-in control for the under-corrected end."),

    ("1863", "MEASURED", "BUILD-CROP",
     "**`eps_r` IS ABOUT 40% TOO LARGE, AND THE FILE'S OWN COMMENT ALREADY SAID SO.** "
     "The applied 704.5 ppm sits ABOVE the entire 500.9-651.9 ppm range of the six per-stack measurements "
     "quoted three lines away at `optics.rs:365`. Red was fitted on 20 ROIs over two subjects; blue on 1071 "
     "tiles over six stacks, so the weaker-evidenced arm is the wrong one. The radial-extrapolation explanation "
     "was PRE-DECLARED as the falsification and is REFUTED: no kink at `support_r_max = 0.788`, residual "
     "proportional to raw everywhere, and the innermost bin, inside both the estimator's exact range and the "
     "fit's own support, is still 42% over-corrected."),

    ("1864", "MEASURED", "BUILD-CROP",
     "**COMMISSIONING PROVED SENSITIVITY AND NEVER PROVED SPECIFICITY, AND A 3x NEAREST-NEIGHBOUR VIEWER "
     "MANUFACTURED THE BLOCKS ORCH DIAGNOSED FROM.** Two instrument failures in one finding. "
     "The magenta counter passed a planted-1px control and then ranked `109MSDCF` 7x above the subject a human "
     "actually saw, on a subject with r-squared -0.013 and no radial organisation: a displacement was planted "
     "and detection confirmed, but noise was never planted and rejection never confirmed. "
     "Separately, modal magenta run length is 1 px with run-start phase near-uniform mod 2/4/8/16/32, so there "
     "is NO block structure; `orch_zoom.py` renders at 3x nearest-neighbour, which turns any 1-3 px fringe into "
     "hard 3x3 blocks. ORCH read its own tool's rendering as a property of the data and built a Bayer-cell "
     "hypothesis on it. Blockiness under an integer-zoom viewer is not evidence of a block-structured stage."),
]


def build_row(num, status, source, body):
    if "|" in body:
        raise SystemExit("REFUSED: raw pipe in fact %s truncates the table row" % num)
    if body.count("*") % 2 != 0:
        raise SystemExit("REFUSED: odd asterisk count in fact %s leaves italics open" % num)
    return "| %s | %s | %s | %s |" % (num, status, source, body)


def main():
    with io.open(PATH, "r", encoding="utf-8", newline="") as fh:
        text = fh.read()

    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(newline)

    hits = [i for i, ln in enumerate(lines) if ln.startswith(ANCHOR_PREFIX)]
    if len(hits) != 1:
        raise SystemExit(
            "REFUSED: anchor %r matched %d rows, expected exactly 1"
            % (ANCHOR_PREFIX, len(hits))
        )
    at = hits[0]

    for num, _s, _src, _b in ROWS:
        if any(ln.startswith("| %s |" % num) for ln in lines):
            raise SystemExit("REFUSED: fact %s already present" % num)

    new_rows = [build_row(*r) for r in ROWS]
    lines[at + 1: at + 1] = new_rows

    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.write(newline.join(lines))

    print("inserted %d rows after line %d (fact 1850)" % (len(new_rows), at + 1))
    print("new tail: %s" % lines[at + len(new_rows)][:90])


if __name__ == "__main__":
    sys.exit(main())

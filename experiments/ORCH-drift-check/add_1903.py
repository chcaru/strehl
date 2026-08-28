"""Bank facts 1903-1907 from lane BUILD-CROP's corpus verification of the eps_r re-fit."""
import io
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
ANCHOR_PREFIX = "| 1902 | MEASURED | V-RIM |"

ROWS = [
    ("1903", "MEASURED", "BUILD-CROP",
     "**THE DESIGNATED CONTROL FOR THE UNDER-CORRECTED END OF THE CA FIT DOES NOT EXERCISE THE "
     "CODE UNDER TEST, AND THE BANNER ASSERTS THAT IT DOES.** `highly-angled-ruler-mm-cpl` read "
     "0.02414 on all three arms - re-fit, shipped and correction-off. That is not a tie: all "
     "three TIFFs share one SHA256, and a fresh CA-on probe is bit-identical to CA-off at "
     "**differs 0 px, max 0 DN**. Mechanism: the CA correction rides the warp, and "
     "`guard_subject` matches the **directory name** against `TILTED_SUBJECTS` and refuses to "
     "solve an alignment, so no warp exists and `compose` is never reached. Because the guard "
     "keys on the NAME it fires identically at 1 frame or 299, so this is how the subject ships "
     "rather than an artifact of a cheap proxy. Meanwhile the banner prints `lateral CA : "
     "CORRECTING, profile a7c2-fe100gm-2xtc-x4cpl -- gear matched, default on` directly above "
     "`alignment : REFUSED`. **This is a fourth inert knob, and unlike the other three it ships "
     "with a banner asserting the opposite** - the banner is printed from profile resolution, "
     "not from the warp actually running, so it tells the truth about the gear and a falsehood "
     "about the pixels. Consequence the orchestrator asked for and did not get: the fear that a "
     "re-fit might wreck the one never-over-corrected subject is **structurally impossible on "
     "that subject**, which is a stronger answer than a number and is emphatically not "
     "reassurance - **the under-corrected end of the fit has no control at all.**"),

    ("1904", "MEASURED", "BUILD-CROP",
     "**THE eps_r RE-FIT IS CORPUS-VERIFIED AS AN ORDERING, WHICH IS THE ONLY FORM THAT "
     "SURVIVES.** Across 22 scored subjects, all arms from two pinned binaries whose SHA256 were "
     "re-hashed after the run and had not moved despite a concurrent lane rebuilding: **re-fit "
     "beats shipped on 18 of 22, loses on 4; re-fit beats CA-off on 19 of 22**; median delta "
     "-0.25 percent, range -11.38 to +0.54 percent. The four losses are `flower-bud-alone-cpl` "
     "+0.54, `lavendar-cpl` +0.17, `flower-inner-edge-cpl` +0.01 and `lead-1-cpl` +0.01, and the "
     "lane refused to count the bottom two as passes because they are fifth-decimal, **below the "
     "proxy's resolution**. Not unanimous, and the exception is worth keeping visible: "
     "**correction OFF beats both correction arms on `flowers-cpl`, `pencil-flatter-angle-cpl` "
     "and `pencil-steep-angle-cpl`.** Three subjects remain unscored - `113MSDCF`, `119MSDCF` "
     "and `coffee-bean` - and are unaccounted rather than clean. The proxy itself is validated "
     "for ordering on one subject only, where it compresses the effect about 5.6 times, so **its "
     "numbers are not master numbers**."),

    ("1905", "MEASURED", "BUILD-CROP",
     "**A LIVENESS FIX FAILED ITS OWN COMMISSIONING, AND BOTH REASONS ARE REUSABLE.** The first "
     "attempt to make `carefit.py` distinguish MEASURED ZERO from COULD NOT MEASURE still "
     "reported MEASURED ZERO on a flat field, because the discriminator was **tile count** and "
     "`field()` gates on a **percentile** of gradient - a percentile always selects tiles, so on "
     "any input whatsoever the count is non-zero and can never discriminate. **A threshold "
     "defined as a quantile of the data cannot detect the absence of the data.** Separately the "
     "commissioning harness `livecomm.py` compared **whole output lines**, which always differ "
     "because they carry the subject name, so it would have passed on any two runs at all; it "
     "had to be re-pointed at the verdict token. The working discriminator is the condition "
     "number `cond = det/tr^2`, exactly 0.0 when `det <= 0`. Direction matters here: the "
     "original defect biased a re-fit **away from well-corrected subjects**, which is precisely "
     "the direction that keeps an over-correction alive."),

    ("1906", "MEASURED", "BUILD-CROP",
     "**ALL SEVEN NEW STACKS ARE 2x TELECONVERTER AT 200 mm, SO THE BASE-LENS-VERSUS-TC SPLIT "
     "REMAINS UNSETTLEABLE, AND SIX OF THE SEVEN ARE SHOT BELOW THE NOISE PROFILE'S CALIBRATION "
     "ISO.** Read from EXIF in one pass: none is TC-free, so no capture in the corpus can "
     "separate the base lens's aberration from the teleconverter's, and the optical profile's "
     "`optical_path` field continues to describe the only configuration ever measured. "
     "Incidental and more actionable: **six of seven are ISO 50, while the shipped noise profile "
     "is calibrated at ISO 100.** A noise model consulted below its calibration floor is an "
     "extrapolation, and every gate that divides by sigma inherits it - which makes these seven "
     "the most informative captures in the corpus for the noise-model provenance question, and "
     "the least covered by its evidence."),

    ("1907", "MEASURED", "ORCH",
     "**PATH-SCOPED COMMITS CORRECTLY EXCLUDE ANOTHER LANE'S WORK, WHICH LEAVES THAT WORK "
     "ORPHANED IN A THIRD LANE'S FILE AND SWEEPABLE BY ANY BARE COMMIT.** About 36 lines of "
     "BUILD-SOFTGATE's uncommitted `preflight_soft_kernel()` are sitting in "
     "`crates/strehl-cli/src/merge_cmd.rs`, which BUILD-CROP owns, because the shared merge "
     "dispatch lives there. BUILD-CROP's path-scoped commit did the right thing and excluded it, "
     "and the author may not know its work is parked in someone else's file. Both halves of the "
     "existing rule are therefore incomplete: `git add -- <paths>` protects the committer from "
     "sweeping others, but **nothing protects the code that gets left behind**, and a single "
     "`git add -A` anywhere in the tree captures it under the wrong lane's message. The missing "
     "step is explicit: **when a lane's work lands in a file it does not own, the owner must "
     "hand it back by name rather than simply not committing it**, and the author must be told "
     "where its own code is living."),
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

    print(f"inserted {len(new)} rows after fact 1902 (line {at + 1})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

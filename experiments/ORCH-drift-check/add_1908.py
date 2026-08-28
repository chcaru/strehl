"""Bank facts 1908-1912 from lane V-REVIEW's independent scoring of the CA re-fit."""
import io
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
ANCHOR_PREFIX = "| 1910 | MEASURED | V-H2H2 |"

ROWS = [
    ("1911", "MEASURED", "V-REVIEW",
     "**THE MAGENTA FIX IS INDEPENDENTLY CONFIRMED: RED-VERSUS-GREEN MISREGISTRATION IS CUT BY "
     "ROUGHLY HALF TO TWO THIRDS ON EVERY SCOREABLE SUBJECT.** Scored from the IMAGES, by a lane "
     "that deliberately read none of the rendering lane's conclusions: `d_ppmR` median **-186.6 "
     "ppm** over a range of -237.3 to -131.6, at **7.2 to 59.8 sigma**, negative on **11 of "
     "11**, magnitude ratio median **0.459** spanning 0.340 to 0.615, and **zero subjects "
     "worse**. The instrument was commissioned through its shipped entry point rather than an "
     "internal one: identity returns 0.000000000, a planted -508.4 ppm is recovered as **-508.6 "
     "at 41.5 sigma**, untouched blue returns +0.0, and a pure-resample width null returns "
     "1.0000. Scope stated honestly and not inflated: **11 of 26 subjects, so zero-worse is a "
     "claim about 11, not about the corpus**, and the pre-named opposite-sign control "
     "`highly-angled-ruler-mm-cpl` never rendered, so the one subject the fix was predicted to "
     "make WORSE is neither confirmed nor refuted."),

    ("1912", "MEASURED", "V-REVIEW",
     "**WHEN A GATE CAN CHANGE WHICH SAMPLES VOTE, AN UNPAIRED COMPARISON MANUFACTURES SIGNAL "
     "OUT OF NOTHING, AND FIXING THE SITE LIST IS NOT ENOUGH.** `vc_ca.measure` refuses "
     "low-correlation sites, so the two arms of a before-and-after comparison do not merely "
     "differ in value - **they are computed over different populations**. Measured cost of that "
     "alone, with no change to the estimator: **+16.8 ppm of phantom signal on "
     "`dry-erase-marker-head-cpl` and -97.7 ppm on `highly-angled-ruler-mm-cpl`**, the latter "
     "large enough to fail a null arm that the estimator itself actually passes. The repair is "
     "to pair explicitly by site identity before differencing. This is the same failure shape as "
     "a quantile threshold that cannot detect absent data - **a selection rule applied "
     "independently to each arm is part of the estimator, not part of the preprocessing.**"),

    ("1913", "MEASURED", "V-REVIEW",
     "**A COMMISSIONED INSTRUMENT CARRIED AN ORIENTATION-DEPENDENT DEFECT THAT WAS INVISIBLE AT "
     "BOTH 0 AND 90 DEGREES.** Binning profile samples with `digitize` into unit bins measured a "
     "gain of **1.000 at 0 degrees, 0.936 at 20 and 70 degrees, and 0.170 at 45 degrees** - the "
     "instrument lost 83 percent of its response on diagonal structure while reading perfectly "
     "on the two orientations anyone would think to test. It additionally manufactured a "
     "spurious **1.114** real-edge sign asymmetry, which fell to 0.988 once lattice sampling "
     "replaced the binning. Both axis-aligned checks passed throughout. **Orientation must be "
     "swept, not sampled at the cardinal angles**, and the corollary is general: a commissioning "
     "grid that tests only the symmetric cases cannot see a defect that lives between them."),

    ("1914", "MEASURED", "V-REVIEW",
     "**A PATH-SCOPED COMMIT DOES NOT WARN THAT IT IS SHIPPING SCRIPTS WITHOUT THE MODULE THEY "
     "IMPORT, SO THE COMMIT CANNOT RUN FROM A FRESH CHECKOUT.** Commit `82b1c411` landed "
     "`vc_score.py`, `vc_positive.py` and `vc_commission.py` while their shared dependency "
     "`vc_ca.py` remained **untracked**, and every one of them worked perfectly in the working "
     "tree, which is exactly why nobody noticed. It was caught only by reading `git status` at "
     "wind-down and repaired in `90ccaaba`. This is the direct cost of the path-scoping rule "
     "that protects concurrent lanes from each other: **naming your paths explicitly means "
     "nothing checks whether the set you named is closed under import.** The cheap guard is to "
     "read `git status` for untracked files in your own experiment directory before every "
     "commit, not after the last one."),

    ("1915", "CORRECTED", "V-REVIEW",
     "**A PRE-REGISTERED PREDICTION FAILED AND WAS RECORDED AS FAILED RATHER THAN REINTERPRETED, "
     "AND THE INSTRUMENT SHIPPED WITH A KNOWN FAILING ARM.** Prediction P3, that blue would be "
     "unchanged by a red-only re-fit, is **REFUTED as stated**: blue moved at 3.1 to 32.8 sigma. "
     "It moves about 12 times less than red, median ratio of magnitudes 0.082, so it cannot "
     "explain red's change and the headline result survives - but the prediction as written "
     "failed and is not recorded as a pass. Alongside it, `vc_ca.py` **fails its BLUR-ONLY arm "
     "on the ruler** at 4 of 5, a paired -77.2 ppm at sigma 1.2 and 7.3 sigma, while passing 5 "
     "of 5 on `dry-erase`, and **the tolerance was not loosened to make it green**. A companion "
     "script `vc_sharp.py` is in the tree having FAILED its commission on all three width "
     "statistics, and its sigma-equivalent numbers are therefore load-bearing nowhere; only the "
     "raw paired width ratio, whose null is exactly 1.000, is used."),
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

    print(f"inserted {len(new)} rows after fact 1910 (line {at + 1})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

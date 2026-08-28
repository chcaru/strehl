"""Bank facts 1885-1888 from BUILD-CROP's wind-down."""
import io
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
ANCHOR_PREFIX = "| 1884 | CORRECTED | V-REVIEW |"

ROWS = [
    ("1885", "MEASURED", "BUILD-CROP",
     "**THE `eps_r` RE-FIT LANDED AT -508.4e-6 AND WINS ON ITS SUBJECT, BUT IS SCORED ON ONE "
     "SUBJECT AND IS NOT CORPUS-VERIFIED.** Hue-neutral chroma, all three arms rendered from ONE "
     "build: re-fit 0.10093, shipped 0.11377, correction off 0.15576. So the re-fit beats both "
     "the shipped coefficient and disabling the correction, which is the acceptance shape that "
     "was asked for. What it does not yet have is breadth: one subject, and "
     "`highly-angled-ruler-mm-cpl` -- the built-in control for the UNDER-corrected end, being the "
     "only subject still showing the lens's natural opposite-sign pattern -- remains unscored. "
     "Committed at `38df35fb`. The magenta diagnosis it repairs is a displacement, not a colour "
     "cast: red crosses zero from -2.009 px to +0.672 px."),

    ("1886", "CORRECTED", "BUILD-CROP",
     "**AN ACCEPTANCE THRESHOLD QUOTED AS AN ABSOLUTE NUMBER SILENTLY EXPIRES WHEN THE TREE "
     "MOVES, AND ORCH SHIPPED TWO OF THEM.** ORCH wrote the `eps_r` acceptance criterion as "
     "\"better than 0.15999 on and 0.20807 off\", quoting fact 1865. Those same two arms measure "
     "0.11377 and 0.15576 today. The proof that this is drift and not a fitting change: the CA-OFF "
     "arm is COEFFICIENT-INDEPENDENT and must therefore reproduce bit-exactly, yet re-rendered it "
     "differed on 33,003,417 px with max 23210 DN -- because fourteen lanes have been editing the "
     "crate concurrently all night. ORDERING AND RATIOS ARE STABLE; ABSOLUTES ARE NOT. The rule "
     "that follows is structural: EVERY ARM OF A COMPARISON MUST COME FROM ONE BUILD, and a "
     "verifier must pin its own binary rather than compare against a hash quoted in an older "
     "report. BUILD-CROP complied by re-rendering all three arms fresh rather than reusing two old "
     "files plus one new. Consequence for the corpus: any A/B whose arms were rendered at "
     "different times during a concurrent-editing session is confounded, and absolute figures in "
     "reports are timestamps, not constants."),

    ("1887", "MEASURED", "BUILD-CROP",
     "**A BYTE-FREEZE IS RED IN THE REPOSITORY AND ITS SPECIFICITY CONTROL HOLDING IS THE "
     "FINDING.** `coffee-bean-20-gate2-sidecar` expects `52517FF8...` and the render produces "
     "`E600A506F6D05A84A21C9DF93E4EB82AED98C8098EAF956BCF0E25985F3D4CB2`. The paired row "
     "`coffee-bean-20-gate2-unaligned` HOLDS at `88712017...`. The two rows differ only in "
     "alignment, so the holding of the unaligned row localises the change to the ALIGNED path "
     "rather than to decode, merge or output. The file was not touched and must not be "
     "re-baselined. Operationally this means a lane told \"the freezes must pass\" will "
     "mis-attribute a pre-existing red row to its own change, so a pre-edit baseline of which rows "
     "pass is now a required first step for any lane modifying the crate."),

    ("1888", "DISCIPLINE", "BUILD-CROP",
     "**A DOC COMMENT ASSERTING THAT NOTHING CALLS A FUNCTION IS AN UNVERIFIED CLAIM, AND ONE OF "
     "THEM COST A LANE AN ENTIRE INVESTIGATION INTO A WIRING BUG THAT DID NOT EXIST.** "
     "`optics.rs:317` read \"Nothing in this crate calls `compose` yet\" while TWO live call sites "
     "existed; fixed doc-only at `910e6bc0`. The lane that lost the time reported itself as the "
     "reader it misled. Reachability is the one property this project keeps getting wrong in both "
     "directions -- a comment claiming no callers when there are two, and a knob assumed live that "
     "turned out to have exactly one call site on a backend that does not ship. Both are settled "
     "the same cheap way, by grepping the symbol crate-wide and counting definition against call "
     "sites, which takes seconds and is the only form of the claim worth believing."),
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

    print(f"inserted {len(new)} rows after fact 1884 (line {at + 1})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Bank facts 1889-1891 from V-REVIEW's landmine repair."""
import io
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
ANCHOR_PREFIX = "| 1888 | DISCIPLINE | BUILD-CROP |"

ROWS = [
    ("1889", "MEASURED", "V-REVIEW",
     "**THE SELF-CONTRADICTING SECTION SURVIVED BECAUSE IT WAS ENTIRELY UNPINNED: NO CHECK IN A "
     "40-CHECK VERIFIER TOUCHED IT.** `HALO-residual.md` §6 asserted a partition of clean 14 and "
     "UNSCORED 8 while §7 of the same file forbade the reasoning that produced it, and the file "
     "shipped that way because `vh_verify.py` pinned §7 and never read §6. Repaired to the "
     "`halo_profile`-only partition, every row now RE-DERIVED from `trunc2.json` rather than "
     "asserted: 15 full 7-band walks, of which 4 flagged, giving clean 11, blind 4, unmeasurable "
     "7, summing to 26. The verifier gained 10 checks, 30 to 40, including a NEGATIVE pin that "
     "fires if the withdrawn clean-14 row ever reappears. The general lesson is that a document's "
     "verified fraction is not visible from its verifier's green: a section nobody pinned reads "
     "exactly like a section that passed."),

    ("1890", "DISCIPLINE", "V-REVIEW",
     "**ADDING CHECKS TO A COMMISSIONED HARNESS DOES NOT EXTEND THE COMMISSION TO THE NEW CHECKS, "
     "AND RE-RUNNING THE OLD COMMISSION CANNOT DETECT THAT.** After adding 10 pins, V-REVIEW "
     "re-ran its commission and got 10 of 10 arms correct, unchanged. That number was worthless "
     "for the new work: not one of the 10 existing arms mutates any string the 10 new pins read, "
     "so all 10 new pins would have been uncommissioned decoration reading GREEN. It added 5 arms "
     "targeting the new pins specifically and reached 15 of 15, and the two most valuable are the "
     "ones that are not simple reversals. A REGRESSION arm reintroduces the withdrawn row IN "
     "ISOLATION, leaving every other pin satisfied, so only the negative pin can fire and a pass "
     "cannot be borrowed from a neighbouring check. A DATA arm mutates the source JSON instead of "
     "the prose, proving the partition is RE-DERIVED rather than text-matched; the file was "
     "restored byte-identical afterwards, SHA256 `4497079675711A7A...A428122C` on both sides. The "
     "operational rule: a commission is scoped to the arms it contains, so every added check "
     "needs an added arm, and the count going up is the only evidence that happened."),

    ("1891", "MEASURED", "V-REVIEW",
     "**THE 11 UNSCORED HALO SUBJECTS ARE BLOCKED ON A CAPTURE PROPERTY, NOT ON CODE, AND NOTHING "
     "IN A FULL NIGHT OF WORK MOVED ONE OF THEM TO CLEAN.** The instrument needs a clear "
     "background of at least 400 px to separate a broad rim from an ordinary backdrop gradient, "
     "and the corpus does not contain it: 7 subjects are UNMEASURABLE for want of that background "
     "and 4 more return a BLIND walk, which is not a pass. This is the highest-value outstanding "
     "capture request after the flat fields, it is cheap for the owner to satisfy, and no amount "
     "of merge work substitutes for it. Until such frames exist, the honest claim about the "
     "deliverable is 11 of 26 demonstrated clean rather than 26 of 26, and that gap is the "
     "instrument's reach rather than a defect in the renders."),
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

    print(f"inserted {len(new)} rows after fact 1888 (line {at + 1})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

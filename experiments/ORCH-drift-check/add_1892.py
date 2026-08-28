"""Bank facts 1892-1895 from BUILD-OUTPUT plus ORCH's byte-freeze adjudication."""
import io
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
ANCHOR_PREFIX = "| 1891 | MEASURED | V-REVIEW |"

ROWS = [
    ("1892", "MEASURED", "ORCH",
     "**THE RED BYTE-FREEZE IS NOT A REGRESSION: IT IS THE CA RE-FIT ARRIVING EXACTLY WHERE IT "
     "SHOULD, AND THE PAIRED CONTROL HOLDING IS THE PROOF.** Two lanes contradicted each other. "
     "BUILD-OUTPUT ran the suite at commit `c7bb6282` on 2026-08-27 01:04 and reported BOTH rows "
     "HOLD, reproduced twice. BUILD-CROP later reported `coffee-bean-20-gate2-sidecar` RED. Both "
     "are honest and they measured different trees: the `eps_r` re-fit `393d7ca3` landed between "
     "them. The mechanism was then traced rather than assumed - `eps_r` is consumed by "
     "`OpticalProfile::compose`, and `compose` has exactly TWO live call sites crate-wide, both "
     "in `align_cmd.rs` at 1929 and 2095, so the lateral-CA correction exists ONLY on the "
     "alignment path. `-sidecar` runs with `env_align=unset` and must move; `-unaligned` runs "
     "with `env_align=0`, never reaches `compose`, and must hold. It held. The registry detected "
     "a real change and its control localised the cause to one code path, which is the whole "
     "point of pairing the rows. Consequence: the row needs re-baselining WITH ITS `why` COLUMN "
     "REWRITTEN, because a permanently-red row trains every future lane to ignore it and would "
     "mask the next genuine break."),

    ("1893", "MEASURED", "BUILD-OUTPUT",
     "**THE DELIVERED MASTERS ARE NOT PRINT FILES: NO EMBEDDED ICC PROFILE AND NO PRINT "
     "RESOLUTION, READ FROM THE ACTUAL BYTES.** `tiff_tags.py` on the shipped gallery reports "
     "XResolution and YResolution `1/1`, ResolutionUnit `none`, and tag 34675 ICCProfile ABSENT. "
     "A lab or printer driver receiving that has to guess both the colour space and the physical "
     "size. The finding the brief did not anticipate is that THE CODE AT HEAD IS ALREADY CORRECT "
     "on all three modes - `--srgb` writes a 2716-byte sRGB-TRC profile with 300/1 and unit inch, "
     "`--linear-srgb` writes a 696-byte identity-TRC profile, and camera-native correctly writes "
     "none - so these are STALE ARTIFACTS, NOT BROKEN CODE, and re-rendering is the entire fix. "
     "The new test that pins this walks the ICC tag table as raw bytes and asserts TRC direction, "
     "gTRC and bTRC aliasing, desc-versus-curve agreement and colorants; commissioned on 4 arms, "
     "and on all three sabotage arms every one of the 5 pre-existing ICC tests still passed, so "
     "the new test is the only thing in the crate with power over any of them."),

    ("1894", "CORRECTED", "BUILD-OUTPUT",
     "**THE PRINT GATE'S CLIP CHECK IS MEASURING THE sRGB GAMUT WALL RATHER THAN THE TONE SCALE, "
     "AND IT FAILED THE ONE MASTER WITH ZERO BLOWN HIGHLIGHTS.** `orch_printready.py` failed "
     "`dry-erase-marker-head-cpl`, whose `clipALL3` is 0.0000 percent, while passing 16 subjects "
     "carrying MORE genuine clipping than one it failed - `112MSDCF` at 0.0693 percent against "
     "`flowers-cpl` at 0.0131 percent. `clipALL3` is the statistic the gate's name refers to. Its "
     "companion CRUSH statistic is worse: it is ANTI-CORRELATED with the property it names and "
     "must stay ungated, since 25 of 26 subjects read `crushALL3` 0.0000 percent and the pixels "
     "it flags have median luma 0.24 to 0.33 with 33k to 53k distinct surviving levels, against "
     "`flowers-cpl`'s genuine black at 0.0011 with 122 levels. A gate whose verdict is "
     "anti-correlated with its own name is worse than no gate, because it spends reviewer "
     "attention in exactly the wrong places."),

    ("1895", "MEASURED", "BUILD-OUTPUT",
     "**AN INDEPENDENT SECOND INSTRUMENT HAD ALREADY RECORDED THE SOFT-GATE ZERO BEFORE ANYONE "
     "WENT LOOKING FOR IT.** `BUILD-HULL.md:383` carries the row `soft-gate-gaussian` with "
     "24,724,512 samples and 0 differing at 0.0000 percent - the same `112MSDCF` zero measured "
     "independently and written to disk before the inertness investigation began. Two instruments "
     "built for different purposes, same zero, so the finding does not rest on one lane's "
     "comparator. Worth recording as method rather than trivia: the corroboration was already in "
     "the corpus and nobody had read it, which is the cheapest evidence available and the kind a "
     "grep finds in seconds."),
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

    print(f"inserted {len(new)} rows after fact 1891 (line {at + 1})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

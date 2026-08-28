"""Bank fact 1916: ORCH read the print-metadata tags out of a delivered master's own bytes."""
import io
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
ANCHOR_PREFIX = "| 1915 | CORRECTED | V-REVIEW |"

ROWS = [
    ("1916", "CORRECTED", "ORCH",
     "**BLOCKER 7 IS REFUTED FOR THE ACTUAL DELIVERABLE: THE DELIVER-V6 MASTERS DO CARRY A VALID "
     "ICC PROFILE AND 300 DPI, AND THE BLOCKER WAS RAISED FROM THE WRONG TREE.** Read out of "
     "`C:\\dev\\strehl-out\\DELIVER-V6\\masters\\bee-2-cpl.tiff` by "
     "`experiments/BUILD-OUTPUT/tiff_tags.py`, which parses the IFD directly rather than asking "
     "a library: tag **34675 ICCProfile present, 2716 bytes, and the profile's own internal size "
     "field reads 2716**, so the profile is self-consistent and not a truncated stub. It is a "
     "valid v2.1.0 `mntr`/`RGB `/`XYZ ` profile with signature `acsp`, ten tags, white point "
     "0.964203/1.000000/0.824905 which is D65, and red primary 0.436096/0.222504/0.013931 which "
     "is the published IEC 61966-2-1 matrix column. Its three TRC curves are 1024-point and "
     "return f(0)=0.00000, f(0.5)=**0.21450**, f(1)=1.00000, and the sRGB curve at 0.5 is "
     "0.2140, so the transfer curve is the real one and not a gamma 2.2 approximation. Tags "
     "**282 and 283 both read 300/1 with tag 296 ResolutionUnit = 2 (inch)**, which is 300 DPI. "
     "The file is 16 bits on 3 channels, uncompressed, and tag 305 stamps `strehl 0.0.0 "
     "(6af834dac08d)` so the render is traceable to a commit. **The lesson is the one already "
     "banked as fact 1901 about SEAL_DIR, recurring at the level of a status document rather "
     "than a script: the blocker was true of the stale ORCH-FAITHFUL masters and was written up "
     "as a property of the project.** A defect must be attributed to the artifact it was "
     "measured on, and re-checked against the current deliverable before it is allowed to block "
     "shipping."),
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

    print(f"inserted {len(new)} rows after fact 1915 (line {at + 1})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

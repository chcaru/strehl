"""Re-baseline the two coffee-bean freeze rows for the acuity restoration.

Field-precise: splits on TAB, rewrites only sha256 / baselined_at /
baselined_on / why, and hard-errors if a row is not found or if the sha
standing in the file is not the one this script expects to supersede. A blind
string replace would silently do nothing if another agent had already touched
the row.
"""

from __future__ import annotations

import sys
from pathlib import Path

TSV = Path(r"C:\dev\blog\death-of-software\projects\strehl\crates\strehl-cli\tests\byte-freezes.tsv")
AT = "6430fb2"
ON = "2026-08-25"

COMMON = (
    "RE-BASELINED at {at}, and the move is INTENDED. WHAT MOVED THEM: the "
    "noise-driven window shrink is restored -- SelectionScale::tighten_by_acuity "
    "lowers each pixel's election radius to the smallest one whose calibrated "
    "noise floor still resolves that pixel's own through-focus peak, min-ed with "
    "the geometric cap. 57e4554 had DELETED that term on my argument that the "
    "cap subsumes it; BUILD-RENDER's dated gallery delta then charged the "
    "deletion -6.6% gradient RMS across 26 subjects, seventeen of them softer, "
    "and bisected it to that commit with separate git-archive pins. The cap does "
    "not subsume the term because ce2c793's veto refuses the geometric collapse "
    "wherever no second layer is resolvable, which on a subject without "
    "silhouettes is almost everywhere: couch-fibers-cpl elects r13 on 99.93% of "
    "the plane with the term off and on 3.42% with it on. "
    "ATTRIBUTION PROVEN BY ISOLATING THE VARIABLE, NOT BY BLAMING A COMMIT "
    "RANGE, following the standard this row set at 2525e08 and 96571ee: "
    "re-rendering this row's OWN recorded invocation with the CURRENT binary and "
    "STREHL_ACUITY=0 reproduces the superseded baseline BIT-EXACTLY, and with it "
    "unset reproduces the value in this row bit-exactly "
    "(experiments/BUILD-HALO/attribute_acuity_freeze.py, 4/4 arms). Both arms "
    "are required: 'off reproduces the old bytes' alone would also be satisfied "
    "by a build that ignored the flag and moved nothing. That incidentally "
    "clears every other agent's commits since {prev} of touching these bytes. "
    "NOT A REGRESSION: a deliberate change to the election is exactly what these "
    "rows exist to catch, and they caught it -- the unaligned row's new value was "
    "reported by the test as `actual` before the attribution script measured the "
    "same value independently. bytes are unchanged at 49450019: the geometry did "
    "not move, only the pixel VALUES. "
    "FIXED WITH THIS BASELINE: STREHL_ACUITY is now in RENDER_ENV and cleared "
    "before the render. It is a real render input -- it sets the election radius "
    "on 96.58% of couch-fibers-cpl -- and it exists ONLY so both arms of the "
    "restoration A/B can come from one binary, because this tree is shared and "
    "two pins built hours apart have already been mistaken for an A/B here twice. "
    "A WARNING THIS ROW EARNED TODAY: the attribution script initially omitted "
    "--merge estimator and --photometric off, which byte-freeze.rs passes "
    "explicitly, and the tool REFUSED the flag combination outright. Both "
    "defaults have moved since these rows were frozen. That refusal is the only "
    "reason the omission did not silently produce a confident wrong attribution "
    "-- this file's header defect, arriving in the tool built to diagnose it. "
    "Superseded value {old} was the pre-restoration baseline at {prev}."
)

ROWS = {
    "coffee-bean-20-gate2-unaligned": (
        "3162EB0B1C8D5F3A1D646CCE50900492DABB9606B6BA58B36156E19171D0781A",
        "88712017FE31362F35FF2FF5D4B98727CDEFCBAC489D9A7827F21EE0154A8620",
        "2525e08",
        " THIS ROW: registration is OFF, because align_enabled() short-circuits "
        "before any cache path is computed, so no shared state can reach it.",
    ),
    "coffee-bean-20-gate2-sidecar": (
        "88154E2D59A7288304A6B6967960183F6EB1D538FF5D4649F059206AEECA461E",
        "63BB88C90908C4CF1EDA32D2C764FECC33F31A4D64A5273BBF677E582394C7F0",
        "96571ee",
        " BOTH ROWS MOVED THIS TIME, and that is the correct localisation "
        "signature: the election runs before warp application and is shared by "
        "both rows, so a merge-core change must move both. A change that moved "
        "only the sidecar row would have been in warp application and would not "
        "have been this one.",
    ),
}


def main() -> int:
    lines = TSV.read_text(encoding="utf-8").splitlines(keepends=False)
    hits = 0
    for i, line in enumerate(lines):
        if not line or line.startswith("#"):
            continue
        f = line.split("\t")
        if f[0] not in ROWS:
            continue
        old, new, prev, extra = ROWS[f[0]]
        if f[11] != old:
            print(f"REFUSING {f[0]}: sha in file is {f[11][:16]}, expected {old[:16]}")
            return 2
        if len(f) != 17:
            print(f"REFUSING {f[0]}: {len(f)} fields, expected 17")
            return 2
        f[11] = new
        f[14] = AT
        f[15] = ON
        f[16] = COMMON.format(at=AT, old=old, prev=prev) + extra
        lines[i] = "\t".join(f)
        hits += 1
        print(f"re-baselined {f[0]}\n   {old[:16]} -> {new[:16]}")
    if hits != len(ROWS):
        print(f"REFUSING: matched {hits} rows, expected {len(ROWS)}")
        return 2
    TSV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote {TSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

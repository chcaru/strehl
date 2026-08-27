"""Re-baseline the two coffee-bean freeze rows for the full-resolution gather flip.

Writes fields [11] (sha), [14] (baselined_at), [15] (baselined_on) and [16]
(why). Field-indexed rather than string-replaced, because the notes contain the
hashes themselves and a `str.replace` would rewrite the wrong one.

Refuses if a row is missing or already carries the new value, so a second run
cannot silently no-op and look like a success.
"""

from __future__ import annotations

import sys
from pathlib import Path

TSV = Path(r"C:\dev\blog\death-of-software\projects\strehl\crates\strehl-cli\tests\byte-freezes.tsv")
AT = "4c99cc40"
ON = "2026-08-26"

SIDECAR_NEW = "52517FF8AE245F238C29F64A29E601C2D5C064CB4D86E93006512993837EC206"
SIDECAR_OLD = "63BB88C90908C4CF1EDA32D2C764FECC33F31A4D64A5273BBF677E582394C7F0"
UNALIGNED = "88712017FE31362F35FF2FF5D4B98727CDEFCBAC489D9A7827F21EE0154A8620"

SHARED = (
    "RE-BASELINED at 4c99cc40 (measurement), and the move is INTENDED. WHAT MOVED THEM: "
    "the FULL-RESOLUTION GATHER default flipped from off to on. warp_frame_in_place now "
    "dispatches to warp_frame_in_place_fullres, so every output pixel is gathered from a "
    "full-resolution demosaic of the frame instead of from its own half-resolution CFA "
    "phase plane, which had band-limited every phase to 0.25 cyc/output px BEFORE the "
    "election, where no later stage could recover it. "
    "WHY THE DEFAULT MOVED, all measured on real captures by instruments whose author did "
    "not write the path: band correlation at 0.25 cyc/out px 0.1514 -> 0.9329, and at 0.35 "
    "from NEGATIVE (-0.4965, inverted structure) to +0.4478; time 27.7->20.1 s (79 frames), "
    "45.9->40.6 s (130), 110.3->97.1 s (299), i.e. 40-97 ms/frame FASTER against a prior "
    "analysis predicting +549 ms/frame slower; edge energy +6.3-15.7% on wrapped-text-1 and "
    "+6.8/+9.0% on bee-1-cpl with the local-envelope ring fraction flat or lower "
    "(1.086->1.053% strongest edge, 1.744->1.744% median). "
    "A DISAGREEMENT RECORDED AS OPEN, NOT RESOLVED: a step-normalised overshoot statistic "
    "reads the full-res arm as ringing MORE (0.179 vs 0.128/0.140), beyond its own "
    "0.0122 byte-identical bound. The tie was broken by rendering both arms at 1:1 and "
    "LOOKING -- paper fibre inside flat white resolves on this path and is mush on the "
    "other, which sharpening cannot manufacture, and no bright rim appears on the dark side "
    "of any letterform, which sharpening would. The two statistics still disagree. "
    "ATTRIBUTION PROVEN BY ISOLATING THE VARIABLE, not by blaming a commit range, following "
    "the standard set at 2525e08, 96571ee and 6430fb2 -- necessary here because five files "
    "in crates/ were left modified by agents that died before committing, so a pin of any "
    "parent could not have separated this change from theirs. Re-rendering each row's OWN "
    "recorded invocation with the CURRENT binary and STREHL_FULLRES_GATHER=0 reproduces its "
    "standing baseline BIT-EXACTLY, and with it unset reproduces the value in this row "
    "bit-exactly (experiments/ORCH-drift-check/attribute_gather_freeze.py). That clears the "
    "five uncommitted files, and every commit since 6430fb2, of touching these bytes. "
    "ONLY THE SIDECAR ROW MOVED, AND THAT IS THE PREDICTED SIGNATURE, written from the call "
    "site BEFORE the render: fullres_gather_enabled() is read in exactly one place, "
    "warp_frame_in_place, which is warp application -- so the STREHL_ALIGN=0 row, where no "
    "warp runs and the flag is unreachable, MUST NOT move, and is a SPECIFICITY CONTROL "
    "rather than an inert arm. The registry itself predicted this in the 6430fb2 note, in "
    "advance and against itself: 'a change that moved only the sidecar row would have been "
    "in warp application and would not have been this one.' This is that change. The script "
    "fails on a violation in EITHER direction, so 'did not move' could not have been "
    "excused after the fact. "
    "CROSS-CHECKED: byte-freeze.rs measured the new sidecar hash independently and printed "
    "it as `actual` before the attribution script ran; the two instruments, which share no "
    "code, agree to the byte. "
    "FIXED WITH THIS BASELINE: STREHL_FULLRES_GATHER is now in RENDER_ENV and cleared before "
    "every render -- it selects what every output pixel is interpolated FROM, so an ambient "
    "value would render a different image than every row here claims. That omission is the "
    "STREHL_ALIGN=0 defect this file's header documents; it is registered in the same commit "
    "that gives it something to hide. A unit test now pins the polarity and makes an "
    "unrecognised value panic rather than fall back, so a silent flip back cannot happen "
    "without re-measuring."
)

ROWS = {
    "coffee-bean-20-gate2-unaligned": (
        UNALIGNED,
        SHARED + " THIS ROW'S HASH IS UNCHANGED, and that is the result, not the absence of "
        "one: it is the specificity control described above, verified this run to reproduce "
        "bit-exactly under both arms.",
    ),
    "coffee-bean-20-gate2-sidecar": (
        SIDECAR_NEW,
        SHARED + f" Superseded value {SIDECAR_OLD} was the pre-flip baseline at 6430fb2. "
        "bytes are unchanged at 49450019: the geometry did not move, only the pixel VALUES.",
    ),
}


def main() -> int:
    lines = TSV.read_text(encoding="utf-8").split("\n")
    seen = set()
    for i, line in enumerate(lines):
        if not line or line.startswith("#"):
            continue
        f = line.split("\t")
        if f[0] not in ROWS:
            continue
        sha, why = ROWS[f[0]]
        if f[11] == sha and f[14] == AT:
            sys.exit(f"{f[0]} already carries the new baseline -- refusing to no-op")
        f[11], f[14], f[15], f[16] = sha, AT, ON, why
        lines[i] = "\t".join(f)
        seen.add(f[0])
    missing = set(ROWS) - seen
    if missing:
        sys.exit(f"rows not found in the registry: {sorted(missing)}")
    TSV.write_text("\n".join(lines), encoding="utf-8", newline="")
    print(f"re-baselined {len(seen)} rows: {sorted(seen)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

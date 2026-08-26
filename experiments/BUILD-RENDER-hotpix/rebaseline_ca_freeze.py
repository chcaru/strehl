"""Re-baseline coffee-bean-20-gate2-sidecar as a field edit, not a text substitution.

The row is a TSV line whose `why` field is a paragraph containing commit hashes,
percentages and the previous sha256. A regex or a whole-line rewrite over that is
how a neighbouring row or a quoted hash gets clobbered silently, so this splits on
tabs, asserts the field count and the OLD values, and writes back exactly four
fields. Anything unexpected is a hard error rather than a best effort.
"""

import pathlib
import sys

TSV = pathlib.Path(r"crates\strehl-cli\tests\byte-freezes.tsv")
ROW = "coffee-bean-20-gate2-sidecar"

I_SHA, I_BYTES, I_AT, I_ON, I_WHY = 11, 12, 14, 15, 16

OLD_SHA = "6325922C11DE23A1B73FFEF69C6E2FEE6BD628FF4275C87DA5797669C4227D8F"
NEW_SHA = "88154E2D59A7288304A6B6967960183F6EB1D538FF5D4649F059206AEECA461E"
BYTES = "49450019"
AT = "96571ee"
ON = "2026-08-25"

WHY = (
    "RE-BASELINED at 96571ee, and the move is INTENDED. WHAT MOVED THEM: lateral-CA "
    "correction now defaults ON. align_cmd.rs called active_profile(), which reads "
    "STREHL_FIX_CA and returns None when unset; unset was the default, so every render "
    "the owner has ever seen ran with a measured, tested correction switched off because "
    "nothing called it (fact 1449's defect class). It now calls profile_for_capture_env, "
    "which applies the profile iff the body model and composed lens id in the FILE match "
    "the ones it was measured on, and declines on Unknown. "
    "ATTRIBUTION PROVEN BY ISOLATING THE VARIABLE, NOT BY BLAMING A COMMIT RANGE, "
    "following the standard BUILD-HALO set on this row at 2525e08: re-rendering this "
    "row's OWN recorded invocation from a clean git-archive pin of 96571ee with "
    "STREHL_FIX_CA=off reproduces the superseded baseline 6325922C..27D8F BIT-EXACTLY, "
    "and with it unset reproduces the value below bit-exactly "
    "(experiments/BUILD-RENDER-hotpix/attribute_ca_freeze.py, 4/4). Both arms are "
    "required: 'off reproduces the old bytes' alone would also be satisfied by a build "
    "that ignored the flag and moved nothing. That incidentally clears every other "
    "commit since 2525e08 of touching these bytes, and clears the four uncommitted "
    "files other agents had in the shared tree when this was measured. "
    "ONLY THE SIDECAR ROW MOVED, AND THAT IS THE LOCALISATION SIGNATURE THIS FILE'S "
    "HEADER PREDICTS: the correction is applied during warp application, so the "
    "unaligned row -- which applies no warp -- is unchanged at 3162EB0B..781A, exactly the "
    "'if only the sidecar row moves, warp application changed' case. A change that moved "
    "both rows would have been a merge-core change and would not have been mine. "
    "FIXED WITH THIS BASELINE: STREHL_FIX_CA is now in RENDER_ENV and cleared before the "
    "render. It was not, and this is the same unrecorded-input defect the header "
    "describes and the EDGE_AWARE comment admits committing a second time -- with a new "
    "twist worth recording, because it generalises: the variable is OLD and the omission "
    "never bit while unset meant off, since the only reachable ambient state matched the "
    "recorded pipeline. Defaulting it ON turned a dormant unrecorded input into a live "
    "one WITHOUT ANYTHING IN THIS FILE CHANGING. scripts\\gallery.ps1 sets this variable, "
    "so 'ran the gallery, then ran the tests, in one shell' is a real path to a "
    "mismatched hash, not a hypothetical one. A clear-list is not made safe by being "
    "complete on the day it was written. "
    "Superseded value 6325922C..27D8F was the pre-default-on baseline at 2525e08 and is "
    "the value the STREHL_FIX_CA=off control reproduces. bytes are unchanged at 49450019: "
    "the geometry did not move, only the pixel VALUES."
)


def main():
    assert TSV.is_file(), f"missing {TSV}"
    text = TSV.read_text(encoding="utf-8")
    lines = text.split("\n")

    hits = [i for i, l in enumerate(lines) if l.startswith(ROW + "\t")]
    assert len(hits) == 1, f"expected exactly 1 row named {ROW}, found {len(hits)}"
    i = hits[0]

    f = lines[i].split("\t")
    assert len(f) == 17, f"expected 17 fields, got {len(f)}"
    assert f[I_SHA] == OLD_SHA, f"row sha256 is {f[I_SHA]!r}, not the value measured against"
    assert f[I_BYTES] == BYTES, f"row bytes is {f[I_BYTES]!r}"
    assert f[I_AT] == "2525e08", f"row baselined_at is {f[I_AT]!r}"
    assert "\t" not in WHY and "\n" not in WHY, "why field must not contain a tab or newline"

    f[I_SHA], f[I_BYTES], f[I_AT], f[I_ON], f[I_WHY] = NEW_SHA, BYTES, AT, ON, WHY
    lines[i] = "\t".join(f)

    out = "\n".join(lines)
    TSV.write_text(out, encoding="utf-8", newline="")

    check = TSV.read_text(encoding="utf-8").split("\n")
    assert len(check) == len(lines), "line count changed"
    g = check[i].split("\t")
    assert len(g) == 17 and g[I_SHA] == NEW_SHA and g[I_AT] == AT, "write-back did not land"
    others = sum(1 for a, b in zip(check, text.split("\n")) if a != b)
    assert others == 1, f"{others} lines changed; exactly 1 expected"
    print(f"re-baselined {ROW}")
    print(f"  sha256 {OLD_SHA[:16]}.. -> {NEW_SHA[:16]}..")
    print(f"  at     2525e08 -> {AT}")
    print("  exactly 1 line changed; 17 fields intact")
    return 0


if __name__ == "__main__":
    sys.exit(main())

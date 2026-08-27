"""Insert facts 1818-1819 into SYNTHESIS.md after row 1817.

Guarded: exits non-zero if any number already exists or the anchor is not
found exactly once.
"""
import io
import re
import sys

PATH = r"docs\research\SYNTHESIS.md"

ANCHOR = 1817

ROWS = [
    (
        1818,
        "MEASURED",
        "ORCH",
        "**THE EXPOSURE GUARD HOLDS AT CORPUS SCALE: 0 OF 10 BLOWN AGAINST 15 OF 23 BEFORE IT, AND THE "
        "FAITHFUL RENDER LANDS ON THE PIN'S OWN EXPOSURE.** Instrument `clipcheck.py`, binary built "
        "from `5f367a94` at `target-orch\\release\\strehl.exe`, recipe `stack <dir> -o <out> --srgb`. "
        "The same-binary predecessor arm rendered with `--auto-exposure` reads **15/23 BLOWN, 4 high, "
        "4 ok** including `lead-1-cpl` 98.80% and `leaf-2-cpl` 96.23% at a pure-white median; the "
        "guarded arm reads **0/10 BLOWN, 0 high, 10 ok** over the subjects rendered so far. **THE "
        "CONTROL THAT MAKES IT A FIX RATHER THAN A DARKENING: the guarded medians reproduce the "
        "acceptance pin's** -- `109MSDCF` 61063 against the pin's 60918, `bee-2-cpl` 48095 against "
        "48077, i.e. within 0.25% -- so the guard restores the pin's rendering rather than inventing a "
        "third one. Speed is unaffected and re-confirmed in passing: `bee-1-cpl` at **N=299 folded in "
        "233 s**, `couch-fibers-cpl` N=299 in 206 s.",
    ),
    (
        1819,
        "MEASURED",
        "ORCH",
        "**THE OWNER'S \"HORRIBLE\" VERDICT WAS PRONOUNCED ON CORRECTLY EXPOSED MASTERS, SO THE "
        "EXPOSURE REGRESSION DOES NOT EXPLAIN IT AND MUST NOT BE OFFERED AS THE ANSWER.** "
        "`DELIVER-V5/print-masters` -- the set actually reviewed -- measures **0 of 26 BLOWN, 0 high, "
        "26 ok** under `clipcheck.py`, as does `acceptance/SHIP-V4` (0.00-0.09% clipped). The "
        "regression was introduced after pin `9b05d0b7` and would have shipped tonight, but it never "
        "reached the reviewer. **THIS IS RECORDED SPECIFICALLY TO STOP A TEMPTING AND FALSE STORY: "
        "\"we found the bug that made them look bad\" is unavailable, and any claim of restored quality "
        "must be measured against the defects that survive a clean exposure.** Those defects, observed "
        "at 1:1 by direct inspection (`peek.py`, `PEEK_MODE=edge/flat`), are subject-dependent and "
        "split cleanly: **isolated subjects on a plain ground render well** -- `bee-2-cpl` shows "
        "individual hairs resolved against a clean white field with no rim, no aura and no visible "
        "mottle -- while **continuous textured surfaces do not**: `leaf-2-cpl` carries a bright bloom "
        "along every vein, low-frequency dark blotches across cell interiors, and general softness. "
        "**ARGUED, NOT MEASURED: that these are one defect.** The pyramid's own help states the "
        "mechanism for the first -- \"a wrong pick in a coarse band IS the rim\" -- which is the same "
        "band range the concentration inversion and the `p_eff` work address, so they are plausibly "
        "the same coarse-band selection failure seen three ways; that identification is a hypothesis "
        "and is not established.",
    ),
]


def main() -> int:
    text = io.open(PATH, encoding="utf-8").read()

    for num, _, _, _ in ROWS:
        if re.search(r"^\| %d \|" % num, text, re.M):
            print("REFUSED: fact %d already exists" % num)
            return 2

    anchor_hits = re.findall(r"^\| %d \|.*$" % ANCHOR, text, re.M)
    if len(anchor_hits) != 1:
        print("REFUSED: anchor row %d found %d times, expected 1" % (ANCHOR, len(anchor_hits)))
        return 3
    anchor = anchor_hits[0]

    block = anchor
    for num, kind, lane, body in ROWS:
        block += "\n| %d | %s | %s | %s |" % (num, kind, lane, body)

    out = text.replace(anchor, block, 1)
    if out == text:
        print("REFUSED: replacement did not land")
        return 4

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(out)

    after = io.open(PATH, encoding="utf-8").read()
    for num, _, _, _ in ROWS:
        if not re.search(r"^\| %d \|" % num, after, re.M):
            print("FAILED: fact %d not present after write" % num)
            return 5
    print("OK: inserted facts %s" % ", ".join(str(n) for n, _, _, _ in ROWS))
    return 0


if __name__ == "__main__":
    sys.exit(main())

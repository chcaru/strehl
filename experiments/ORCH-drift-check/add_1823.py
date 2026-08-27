"""Insert facts 1823-1825 into SYNTHESIS.md after row 1822.

Guarded: exits non-zero if any number already exists or the anchor is not
found exactly once.
"""
import io
import re
import sys

PATH = r"docs\research\SYNTHESIS.md"

ANCHOR = 1822

ROWS = [
    (
        1823,
        "MEASURED",
        "ORCH",
        "**THE FULL 26-SUBJECT CORPUS NOW RENDERS 0/26 BLOWN, AGAINST 15/23 BLOWN ON THE SAME BINARY "
        "BEFORE THE GUARD.** Every subject in `D:\\personal\\macro` rendered end to end with the fixed "
        "binary at `5f367a94` (`--srgb`, no `--auto-exposure`), 26/26 `ok=True`, scored by "
        "`clipcheck.py`: **0 blown (>25% clipped), 0 high, 26 ok**, worst clip fraction **0.39%** "
        "(`flowers-cpl`), medians 2084-61063 DN spanning the genuinely dark subjects "
        "(`coffee-bubbles` 2084, `foam` 6755) through the genuinely bright ones (`109MSDCF` 61063) "
        "**without either end being forced**. The pre-fix arm on the same binary read `lead-1-cpl` at "
        "98.80% and `leaf-2-cpl` at 96.23% clipped. Full-resolution JPEGs and a 26-up contact sheet "
        "at `C:\\dev\\strehl-out\\ORCH-FAITHFUL\\faithful\\preview\\`. **THE CONTROL THAT BLOCKS A "
        "FALSE STORY STANDS:** the delivered set the owner actually reviewed (`DELIVER-V5"
        "\\print-masters`) reads **0/26 blown**, so the exposure regression never reached him and "
        "**cannot be offered as the explanation for his rejection of the output** -- the quality "
        "complaint survives the exposure fix intact and is a separate, still-open defect.",
    ),
    (
        1824,
        "MEASURED",
        "ORCH",
        "**RAISING THE BAND-0 NOISE-GATE FLOOR 4x CUTS FLAT-REGION GRAIN 73% FOR A 9% COST IN EDGE "
        "MICRO-CONTRAST, AND MOVES THE FLAT LEVEL DOWN -- THE DIRECTION FACT 1820's MECHANISM "
        "PREDICTS.** `112MSDCF` (79 frames, large genuinely-featureless dark ground), HEAD at "
        "`5f367a94`, both arms `--srgb` with no `--auto-exposure`, `STREHL_GATE_FLOOR_SCALE="
        "4,1,1,1,1,1,1` against default. Band-0 averaged duty cycle **32.1% -> 80.9%**, so the knob "
        "has authority at exactly the band where fact 1820 measured `n_eff`=1.008. Scored by "
        "`contrast_ab.py` at the 12 lowest-gradient and 12 highest-gradient tiles **separately**, "
        "sites chosen on the default arm only: **FLAT high-pass std x0.2717**, **EDGE high-pass std "
        "x0.9108**. **THE CORROBORATION IS IN THE LEVELS, NOT THE GRAIN:** fact 1820's mechanism says "
        "flat output is the max of N noise samples, and `E[max] > E[mean]` therefore requires "
        "averaging to move flat regions DOWN. Measured: flat sites **-206.7 DN**, edge sites **+13.7 "
        "DN** (i.e. nothing). Different subject, different lane, different instrument, and a "
        "direction that was not chosen in advance -- **independent corroboration of the winner-take-"
        "all-on-noise mechanism.** The 9% edge cost is real and is the price a *global* knob pays for "
        "being unable to tell flat from detailed, which is the standing argument for a "
        "confidence-scaled exponent over an env var.",
    ),
    (
        1825,
        "DISCIPLINE",
        "ORCH",
        "**A 1:1 CROP IS ILLUSTRATION, NEVER EVIDENCE: THE ORCHESTRATOR READ ONE BACKWARDS IN BOTH "
        "LEVEL AND CONTRAST, AND WAS ABOUT TO REPORT THE OPPOSITE OF THE MEASUREMENT.** Shown a "
        "matched A/B of the fact-1824 arms, the read was *\"cleaner but hazier -- lifted blacks, lost "
        "micro-contrast, 4x is too aggressive\"*. Measurement: blacks went **DOWN** 206.7 DN and edge "
        "micro-contrast fell **9%, not the ~40% the impression implied**. **Grain reads to the eye as "
        "deeper blacks and smoothness reads as veiling**, so the two defects this project most needs "
        "to separate are exactly the two the eye conflates. **A SECOND, MECHANICAL TRAP IN THE SAME "
        "COMPARISON:** both arms place tone on their OWN 99.9th percentile, so an arm that averages "
        "more has lower peaks, a lower white point, and therefore receives MORE gain -- **it comes out "
        "globally brighter for reasons that have nothing to do with the merge**, and that brightness "
        "reads as lost contrast. Any A/B of two merge settings must normalise the arms to a common "
        "level before measuring anything; `contrast_ab.py` does this and prints the rescale factor so "
        "the confound is visible rather than assumed away (here it was small, 0.79%, but it was "
        "measured and not presumed). **GENERALISES: report no quality verdict from pixels without the "
        "paired numbers, the instrument, and the commit.**",
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

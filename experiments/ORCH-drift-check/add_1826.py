"""Insert facts 1826-1827 into SYNTHESIS.md after row 1825.

Guarded: exits non-zero if any number already exists or the anchor is not
found exactly once.
"""
import io
import re
import sys

PATH = r"docs\research\SYNTHESIS.md"

ANCHOR = 1825

ROWS = [
    (
        1826,
        "MEASURED",
        "ORCH",
        "**THE BAND-0 GATE-FLOOR KNOB IS SELF-TARGETING: AT 4x IT IS NEARLY INERT WHERE REAL "
        "STRUCTURE DOMINATES AND STRONGLY ACTIVE WHERE NOISE DOES, WITHOUT ANY ADAPTIVITY BEING "
        "CODED.** Two subjects, same binary (HEAD `5f367a94`), same recipe (`--srgb`, no "
        "`--auto-exposure`), same knob: on `112MSDCF`, whose lowest-gradient tiles are "
        "noise-dominated, band-0 `averaged` runs **32.1% -> 80.9%**; on the backlit-paper focus sweep "
        "(`flat-fields\\subject-focus-sweep-with-cpl`, 62 frames), whose lowest-gradient tiles carry "
        "real fibre structure, the same setting moves it **0.0% -> 1.1%**. **THE MECHANISM:** where "
        "structure is present the coefficients sit far above the floor and a modest floor raise cannot "
        "change the decision; where only noise is present they sit just above it and the same raise "
        "flips them to averaging -- **the gate is already signal-adaptive, and the knob only moves the "
        "threshold at which that adaptivity engages**. This materially weakens the standing objection "
        "that a global constant cannot distinguish flat from detailed, an objection the orchestrator "
        "had itself raised against this knob. **THE RANGE IS BOUNDED ABOVE AND THE BOUND IS "
        "MEASURED:** at 64x the paper sweep loses **25% of its band-1 structural energy** (EDGE ratio "
        "0.7505) with fibres visibly smeared in a 1:1 crop, so the usable region lies below that and "
        "the ladder's remaining work is between 8x and 32x.",
    ),
    (
        1827,
        "DISCIPLINE",
        "ORCH",
        "**A 'FLAT FIELD' IS NOT A NULL SUBJECT, AND THE ORCHESTRATOR PUBLISHED A CONCLUSION FROM ONE "
        "BEFORE CHECKING -- WITHDRAWN HERE.** The claim was that stacking the backlit-paper focus "
        "sweep gave band-0 `averaged = 0.0%`, i.e. winner-take-all at every pixel on a subject with "
        "nothing to select on, and that therefore *the gate never fires on flat content*. **Backlit "
        "printer paper at this magnification is dense with real fibre structure at every measurable "
        "scale**, so 0% averaging there is plausibly correct behaviour rather than a defect, and the "
        "claim is withdrawn. **THE DISCRIMINATOR THAT SETTLED IT, WHICH IS THE REUSABLE PART:** in an "
        "octave decomposition, read the ABSOLUTE band energy against scale at the sites being scored "
        "-- on `112MSDCF` the lowest-gradient tiles run **706 -> 338 -> 288 -> 255 -> 233 (FALLING, "
        "the signature of noise)** while on the paper sweep they run **503 -> 763 -> 1263 -> 1523 -> "
        "1537 (RISING, the signature of structure)**. A site whose energy rises with scale **cannot "
        "contribute evidence about grain**, and a ratio taken there means something different from "
        "the same ratio taken on noise. `contrast_ms.py` separated the two subjects without being told "
        "which was which, which is the instrument passing a test it could have failed. **GENERALISES: "
        "before scoring any site as 'flat', measure whether it is noise-dominated; 'low gradient' and "
        "'no signal' are not the same property**, and the whole grain argument depends on the "
        "difference.",
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

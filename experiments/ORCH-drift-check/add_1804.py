"""Insert fact 1804 into SYNTHESIS.md after row 1803.

Guarded: exits non-zero if the number already exists or the anchor is not
found exactly once.
"""
import io
import re
import sys

PATH = r"docs\research\SYNTHESIS.md"

NUM = 1804
KIND = "MEASURED"
LANE = "ORCH"
BODY = (
    "**RIM IS THE DEFECT THAT DISQUALIFIES THE PRINTS -- 13 FAIL AGAINST 9 PASS, THE ONLY AXIS WHERE "
    "FAILURES OUTNUMBER PASSES -- AND SHARPNESS, THE AXIS THE WHOLE CAMPAIGN HAS BEEN OPTIMISING, IS "
    "UNMEASURED ON 23 OF 26 SUBJECTS.** Run directly by the orchestrator "
    "(`python -u experiments\\V-GATHER\\printcert4.py`) against the corrected gauge, over the 26-master "
    "seal census: **BLOTCH** 17 PASS / 8 FAIL / 1 SUBJECT; **RIM** 9 PASS / 13 FAIL / 4 REFUSED; "
    "**SHARP** 2 PASS / 1 FAIL / **16 REFUSED / 7 NOT EXAMINED**; **DUST** 26 PASS. Each column "
    "partitions and sums to 26. **Eight of the nine subjects that moved clean -> failing under the "
    "corrected gauge did so on rim alone.** Rim overshoot, as a fraction of the edge step against a "
    "2.0% bar (3.5% on one subject), every one with its 95% lower bound also above the bar: "
    "`leaf-2-cpl` **+37.07%** (112 edges), `wrapped-text-2` +10.93% (1432), `lavendar-cpl` +8.01% "
    "(1159), `wrapped-text-1` +7.48% (1861), `pencil-steep-angle-cpl` +6.77% (2034), `lead-1-cpl` "
    "+3.36% (1284). **CONSEQUENCE FOR THE MERGE REBUILD, and it inverts the acceptance criteria the "
    "orchestrator had issued twice: the sharpness figure 0.755 was being quoted as a corpus property "
    "and is a fact about three subjects, since 23 of 26 are REFUSED or NOT EXAMINED and the axis is "
    "silent below blur sigma 0.6 with every deficit a LOWER bound. A measured rim improvement must "
    "not be traded for an unmeasured sharpness one.** `--pyramid-exponent`, `Hull::PerLevel` and the "
    "`r_max` weight law are three levers on ONE defect and must be evaluated one axis at a time or "
    "the attribution is lost. **\"Overshoot of the edge step, then a plateau\" is the literal shape "
    "fact 1803 predicts from a level-0 clamp**, which makes rim the axis where that hypothesis lives "
    "or dies. **METHOD WORTH COPYING, and the reason this table can be trusted where the earlier "
    "17-PASS one could not: every column counts REFUSED and NOT EXAMINED separately from PASS and "
    "sums to the census, so a subject the gauge could not speak about cannot be read as one it "
    "cleared** -- discipline 29 enforced structurally rather than remembered. Standing caveats the "
    "table prints about itself: rim sees only edges isolated enough to plateau within 7 px, a fraction "
    "running **12% to 72%** per subject; dust detected planted 2000 DN defects and missed 500 DN while "
    "the darks put this sensor's worst site at **331 DN**; and no axis measures colour, tone or "
    "composition."
)


def main() -> int:
    text = io.open(PATH, encoding="utf-8").read()

    if re.search(r"^\| %d \|" % NUM, text, re.M):
        print("REFUSED: fact %d already exists" % NUM)
        return 2

    anchor_hits = re.findall(r"^\| 1803 \|.*$", text, re.M)
    if len(anchor_hits) != 1:
        print("REFUSED: anchor row 1803 found %d times, expected 1" % len(anchor_hits))
        return 3
    anchor = anchor_hits[0]

    row = "| %d | %s | %s | %s |" % (NUM, KIND, LANE, BODY)
    out = text.replace(anchor, anchor + "\n" + row, 1)
    if out == text:
        print("REFUSED: replacement did not land")
        return 4

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(out)

    if not re.search(r"^\| %d \|" % NUM, io.open(PATH, encoding="utf-8").read(), re.M):
        print("FAILED: fact %d not present after write" % NUM)
        return 5
    print("OK: inserted fact %d" % NUM)
    return 0


if __name__ == "__main__":
    sys.exit(main())

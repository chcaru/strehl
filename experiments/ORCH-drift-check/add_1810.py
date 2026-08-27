"""Insert fact 1810 into SYNTHESIS.md after row 1809.

Guarded: exits non-zero if the number already exists or the anchor is not
found exactly once.
"""
import io
import re
import sys

PATH = r"docs\research\SYNTHESIS.md"

NUM = 1810
KIND = "MEASURED"
LANE = "ORCH"
BODY = (
    "**THE PRINT GATE CANNOT EXPRESS THE WIN THE FIX IS AIMED AT: ON THE SIX MOTTLE SUBJECTS IT READS "
    "0 PASS / 6 ACQUITTED, AND THE ACQUITTALS EXPIRE AT 5% RENDER MOVEMENT.** BUILD-OUTPUT, "
    "`orch_printready.py` driven by the new `recert.py` harness, 26 subjects / 4,825 frames. **FIRST, "
    "A BASELINE THE ORCHESTRATOR HAD BEEN RELAYING IS WITHDRAWN:** the standing figure quoted to "
    "multiple lanes was `17 PASS / 5 FAIL / 4 REVIEW`; re-measured it is **17 PASS / 0 FAIL / 9 "
    "ACQUITTED**. Diffing a candidate against the quoted split **would have invented five FAIL -> PASS "
    "wins** out of nothing. The lane caught this by re-measuring rather than differencing, which is "
    "the only reason it surfaced. **SECOND, AND THE REAL FINDING:** all six mottle subjects sit behind "
    "**acquittals**, not passes, and an acquittal expires once the render moves 5%. **A fix therefore "
    "expires its own evidence, while the `17 PASS` it does not target never moves** -- so the gate's "
    "headline number is simultaneously insensitive to success and sensitive to nothing else. "
    "PASS -> FAIL and ACQUIT -> EXPIRED are now separated and both block promotion. **THE HARNESS IS "
    "THE DELIVERABLE:** a full re-certification is **54.7 min measured** (render 2682.6 s, gate 472.2 "
    "s, pair 110.9 s, h2h 15.0 s), but `--only` on the six mottle subjects -- 463 of 4,825 frames -- is "
    "**11.8 min**, giving **~5 triage attempts per hour**; `finalpass.ps1`'s own `-WhatIfTiming` "
    "estimate of 119 min is **2.7x pessimistic** against an actual 44.7 min at 105.5 frames/min. "
    "Commissioned on both arms the corpus requires: metric **59 PASS / 0 FAIL / 7 REFUSED** with "
    "planted-denoise `paid` max **0.000** disjoint from planted-blur min **0.406**; harness 4/4, whose "
    "load-bearing arm is a blurred candidate **quieter in all three bands** (`d_floor` -0.7301 / "
    "-0.1701 / -0.0108) -- every noise statistic improves on it, a noise-only harness promotes it, and "
    "this one refuses and names structure. The null is exact under two independent instruments: no "
    "subject changed state, 390 cells at `d_floor +0.0000 / d_structure +0.0000`, and a separate "
    "SHA-256 sweep at **26 byte-identical / 0 differing** including all 26 `--auto-exposure` choices. "
    "**THREE DEFECTS IN ITS OWN INSTRUMENTS, EACH CAUGHT BY A CONTROL, ONE OF WHICH IS A GENERAL "
    "LESSON:** the verdict line certified a run that measured nothing; the `PSModulePath` fix was "
    "inert **and its control shared the bug** (`dict(os.environ)` upper-cases keys) so the control "
    "*refused* rather than passed, which is the only reason the shared defect surfaced; and the h2h "
    "digest check sat inside `if not out.exists()` and scraped `stack`, which never prints it, so **a "
    "cached render skipped verification entirely**. **NOT ESTABLISHED:** no genuinely different binary "
    "has yet been scored -- every arm to date is the pin or a synthetic perturbation -- `h2h` covers "
    "`119MSDCF` only, `PAID_MAX=0.25` is untested in the gap between 0.25 and 0.406, and 54.7 min was "
    "measured against 2-5 concurrent lanes so it is an upper bound."
)


def main() -> int:
    text = io.open(PATH, encoding="utf-8").read()

    if re.search(r"^\| %d \|" % NUM, text, re.M):
        print("REFUSED: fact %d already exists" % NUM)
        return 2

    anchor_hits = re.findall(r"^\| 1809 \|.*$", text, re.M)
    if len(anchor_hits) != 1:
        print("REFUSED: anchor row 1809 found %d times, expected 1" % len(anchor_hits))
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

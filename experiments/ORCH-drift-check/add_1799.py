"""Insert facts 1799-1802 into SYNTHESIS.md after row 1798.

Guarded: exits non-zero if any target number already exists, or if the
anchor row is not found exactly once. Never edits in place on a miss.
"""
import io
import re
import sys

PATH = r"docs\research\SYNTHESIS.md"

ROWS = [
    (
        1799,
        "MEASURED",
        "V-GATHER",
        "**THE MERGE EMITS DETAIL THAT IS PRESENT IN NO INPUT FRAME, ON 13 OF 19 SUBJECTS, AND THE "
        "ATTRACTIVE EXPLANATION IS REFUTED.** On a linear gauge, after 44 extra renders, the shipped "
        "master **exceeds its own focus ceiling** -- the sharpest value any contributing frame supplies "
        "at that site -- on **13 of 19 subjects, by up to -96.4%**. `stack.rs:11` names the mechanism. "
        "The competing explanation, that the warp kernel rings, is **REFUTED by the one control that "
        "could kill it**: `nearest` has no negative lobes and cannot ring, yet reads *more* overshoot "
        "than the interpolating kernels (`wrapped-text-2`: nearest **+9.85%**, catmull-rom +8.89%, "
        "lanczos3 +10.64%). Resampling ringing cannot order those three that way. The rim finding "
        "survived reconstruction on an instrument **sharing no code** with the original, after the same "
        "lane ruled its own two earlier versions inadmissible -- once for n=0 under a NaN control, once "
        "for a null reading *higher* than the master through population mismatch. **CONVERGENCE, from a "
        "lane not looking for it:** V-NEVERWORSE priced hull violations at **0 / 72 / 511** for merge "
        "exponents **1 / 8 / 16**, and the shipping ladder runs exponent 8 at the three finest bands. "
        "Two instruments, two questions, one parameter. **STILL OPEN and stated as the lane's own gap: "
        "the attribution is mechanistic, not experimentally isolated** -- naming a line of code is an "
        "argument about source, and 13 of 19 is an argument about pixels; neither varies the merge.",
    ),
    (
        1800,
        "MEASURED",
        "V-GATHER",
        "**THE PRINT GATE WAS MEASURING THROUGH A SIGN INVERSION, AND THE CORRECTED STANDING IS 1 OF 26 "
        "CLEAN, NOT 17 PASS.** `certmeasure.py`'s `window_shift` carried the registration correction with "
        "the wrong sign, **displacing every measurement window by twice the drift** rather than removing "
        "it. All four prior REFUSALs were artifacts of it and **all four now FAIL**; `cert-wrongsign.json` "
        "is retracted and preserved. With the gauge corrected, **9 subjects move clean -> failing and "
        "exactly one subject (`119MSDCF`) is clean on all four axes.** The retraction was produced by the "
        "lane that had committed the defect, against its own published result. **The orchestrator had been "
        "relaying 17 PASS / 5 FAIL / 4 REFUSED to four other lanes for hours; the number was wrong in the "
        "flattering direction.** Uncorrected gaps carried forward and not counted as passes: 7 deep stacks "
        "unexamined on sharpness, the rim gauge seeing only 12-72% of edges, and the dust gauge blind "
        "below ~500 DN while the sensor's worst measured site is **331 DN**.",
    ),
    (
        1801,
        "MEASURED",
        "V-GATHER",
        "**A NaN REACHED THE ACCEPTANCE FILE AND WOULD HAVE READ AS PASS, BECAUSE `NaN > x` IS `False`.** An "
        "unbounded chroma window emitted NaN into `cert.json`; every acceptance test of the form \"must not "
        "exceed\" is a **one-sided comparison**, and a one-sided comparison is *satisfied* by a missing "
        "measurement. It was inert only by luck of which axis it landed on. **DISCIPLINE 33 -- an "
        "acceptance comparison must be two-sided or explicitly NaN-guarded, and the guard must be "
        "commissioned by firing a NaN through it.** This is the same failure shape as discipline 29 (a "
        "count that does not move reads identically whether nothing was wrong or nothing was examined) and "
        "of fact 1797's corollary (a contract satisfied by a corpse): **in each, absence of a measurement "
        "wears the costume of a passing one.** Companion trap from the same audit, in the opposite "
        "direction: a threshold carried unchanged across a gauge change printed a conclusion **from n=0**.",
    ),
    (
        1802,
        "ARGUED",
        "ORCH",
        "**NO FIXED EXPONENT CAN SATISFY THE THREE CONSTRAINTS NOW ON THE MERGE, WHICH IS AN ARGUMENT "
        "AGAINST THE PARAMETERISATION AND NOT AGAINST THE TUNING.** Three symptoms, three lanes, three "
        "instruments, one knob: **mottle** in near-tied flat regions demands the exponent fall (over-"
        "selection on noise-ordered competitors; measured ceiling 57% on one subject at 9.3% sharpness "
        "cost); **manufactured detail** on 13 of 19 subjects demands it fall (hull violations priced 0 / "
        "72 / 511 at exponents 1 / 8 / 16, fact 1799); **depth softening** on `bee` at 0.180 / 0.060 "
        "retention demands it **rise** (winner's share 0.4524 -> 0.0550 from N=22 to N=299, fact 1794). "
        "Two directions down, one up, same parameter, all three on real subjects. A tuning exercise "
        "searches for a value; there is no value. **The `r_max`-relative form `w_k = max(0, r_k - "
        "theta*r_max)^p` is the only proposal on the table that is permitted to succeed**, because it "
        "moves the depth axis by changing *what the ratio is measured against* rather than how hard the "
        "ratio is pressed -- leaving the exponent, and therefore the ringing budget, alone. **This does "
        "not make it correct and it is not yet measured.** Its falsification is pre-registered and cheap: "
        "the fix must reduce blotch and raise sharpness **while hull violations do not exceed the "
        "shipping arm** -- a fix that trades manufactured detail for either of the other two has made the "
        "images worse in the way that disqualifies a print, since manufactured detail is the tool "
        "reporting a subject that was never there.",
    ),
]


def main() -> int:
    text = io.open(PATH, encoding="utf-8").read()

    for num, _, _, _ in ROWS:
        if re.search(r"^\| %d \|" % num, text, re.M):
            print("REFUSED: fact %d already exists" % num)
            return 2

    anchor_hits = re.findall(r"^\| 1798 \|.*$", text, re.M)
    if len(anchor_hits) != 1:
        print("REFUSED: anchor row 1798 found %d times, expected 1" % len(anchor_hits))
        return 3
    anchor = anchor_hits[0]

    block = anchor + "\n" + "\n".join(
        "| %d | %s | %s | %s |" % (num, kind, lane, body) for num, kind, lane, body in ROWS
    )
    out = text.replace(anchor, block, 1)
    if out == text:
        print("REFUSED: replacement did not land")
        return 4

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(out)

    check = io.open(PATH, encoding="utf-8").read()
    for num, _, _, _ in ROWS:
        if not re.search(r"^\| %d \|" % num, check, re.M):
            print("FAILED: fact %d not present after write" % num)
            return 5
    print("OK: inserted facts %s" % ", ".join(str(n) for n, _, _, _ in ROWS))
    return 0


if __name__ == "__main__":
    sys.exit(main())

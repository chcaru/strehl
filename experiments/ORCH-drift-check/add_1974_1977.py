"""Append facts 1974-1977 to the SYNTHESIS fact table (lane V-H2H2 close-out)."""
import io
import re
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
EXPECTED_TAIL = 1973

ROWS = [
    (1974, "V-H2H2", "MEASURED", (
        "THE CONFIDENCE EXPONENT IS A NULL: its cost is measured and its benefit is not "
        "quotable. On bee-1-cpl at N=299 with the srgb path, over the acuity band 0.17-0.25 "
        "cyc/px where this subject qualifies SIGNAL, arm S100 reads flat 0.8015 and acuity "
        "0.9939; arm S1000 reads flat 0.8052 and acuity 0.8854; arm K (gate floor 4x) reads "
        "flat 0.0937 and acuity 1.0028. All three nulls land inside the 0.005 tolerance at "
        "1.0016, 1.0040 and 1.0013, so all three comparisons are valid rather than merely "
        "reported. Both strengths remove the same flat amplitude while S1000 costs roughly 19x "
        "the acuity, so the benefit saturates by z=100 and the cost does not. The reason the "
        "benefit cannot be claimed is a qualification fact, not a measurement failure: "
        "bee-1-cpl's signal/noise boundary sits at 0.48, so the flat 0.25-0.50 band qualifies "
        "as SIGNAL too, and a reduction there cannot be called a grain win. Two earlier commits "
        "point the same way, 0b73c830 recording that p_eff loses to a one-line env var and "
        "91373702 recording that nothing passes. Do not ship the exponent on this evidence."
    )),
    (1975, "V-H2H2", "MEASURED", (
        "A LANE FALSIFIED ITS OWN PRE-REGISTERED PREDICTION AND WITHDREW THE SCOPE CLAIM, which "
        "is the pre-registration mechanism working as designed rather than a defect. The "
        "prediction was that the flat effect would be at or above 0.95 at every strength; the "
        "measurement was 1.0019 at N=79 but 0.805 at N=299. The withdrawn claim was that "
        "`select_weight` returns zero before consulting the exponent, which holds only where "
        "the gate has already collapsed the candidate set to a single frame -- a condition that "
        "stops being true at depth. The generalisable content is that A SCOPE CLAIM VERIFIED AT "
        "SHALLOW N IS NOT VERIFIED AT DEEP N when the mechanism that makes it true is itself "
        "N-dependent, so any claim resting on set collapse must be re-measured at the deepest "
        "stack in scope rather than transferred."
    )),
    (1976, "V-H2H2", "MEASURED", (
        "`contrast_ms.py` FAILS A PLANTED DC-OFFSET NULL, and the instrument is shared by "
        "roughly 38 committed files across at least eight lanes. The true answer for a "
        "DC-offset arm is exactly 1.000 at every band, because a constant added to an image is "
        "annihilated by every high-pass filter; the instrument returned 0.9696 at all six "
        "bands. The mechanism was confirmed by reading the source rather than inferred: lines "
        "64-67 compute the medians of both sides and rescale B by their ratio, announcing "
        "\"tone confound removed\", so a DC offset added to B moves B's median, moves the "
        "scale, and multiplies B's AC amplitude by a factor other than one. The error is "
        "invertible, which means the truth is BRACKETED between the raw and the corrected "
        "reading and neither end may be quoted alone. Note the cross-lane exposure explicitly: "
        "this instrument is not the producer of the merge-vs-best-frame softness numbers, which "
        "came from V-SOFTCHECK's own `bandqual.py` using a different per-frame gain "
        "normalisation, but that is a different mechanism in the same vulnerability class and "
        "was referred for independent DC-null testing rather than assumed safe."
    )),
    (1977, "V-H2H2", "MEASURED", (
        "THE BYTE-FREEZE REGRESSION GUARD DOES NOT COVER THE DEFAULT MERGE BACKEND. Coverage is "
        "2 data rows with 0 naming pyramid, while `DEFAULT_MERGE_BACKEND` is pyramid, and the "
        "harness says so about itself at `byte-freeze.rs:522`, `547-548` and `574`. This was "
        "verified by a party other than the lane that wrote it. The consequence is that the "
        "guard most relied on to catch silent output drift is blind to the path that every "
        "default render actually takes, so a regression in the shipping backend would not trip "
        "it -- a green byte-freeze currently certifies only the non-default backends. This is a "
        "product risk rather than a research finding and it is cheap to close, since it needs a "
        "freeze row naming the pyramid backend rather than any new measurement."
    )),
]


def main() -> int:
    src = io.open(PATH, encoding="utf-8").read()
    ids = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", src, re.M)]
    if not ids:
        raise SystemExit("FATAL: no fact rows matched")
    if max(ids) != EXPECTED_TAIL:
        raise SystemExit("FATAL: tail is %d, expected %d" % (max(ids), EXPECTED_TAIL))

    n_before = len(ids)
    cur_tail = EXPECTED_TAIL
    for new_id, lane, kind, body in ROWS:
        if new_id in ids:
            raise SystemExit("FATAL: fact %d already present" % new_id)
        if body.count("*") % 2 != 0:
            raise SystemExit("FATAL: odd '*' count in fact %d" % new_id)
        if "|" in body:
            raise SystemExit("FATAL: '|' in body of fact %d" % new_id)
        anchor = None
        for m in re.finditer(r"^\| %d \|.*$" % cur_tail, src, re.M):
            anchor = m
        if anchor is None:
            raise SystemExit("FATAL: could not locate row %d" % cur_tail)
        src = src[: anchor.end()] + "\n" + ("| %d | %s | %s | %s |" % (new_id, lane, kind, body)) + src[anchor.end():]
        cur_tail = new_id

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(src)

    back = io.open(PATH, encoding="utf-8").read()
    ids2 = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", back, re.M)]
    if max(ids2) != ROWS[-1][0]:
        raise SystemExit("FATAL: post-write tail is %d" % max(ids2))
    if len(ids2) != n_before + len(ROWS):
        raise SystemExit("FATAL: row count went %d -> %d" % (n_before, len(ids2)))
    for new_id, _l, _k, _b in ROWS:
        if new_id not in ids2:
            raise SystemExit("FATAL: fact %d missing after write" % new_id)
    print("OK facts %s appended  rows %d -> %d"
          % (", ".join(str(r[0]) for r in ROWS), n_before, len(ids2)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

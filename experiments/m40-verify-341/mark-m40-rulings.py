"""Mark the five facts M40 re-ruled, in place, without deleting anything.

Rule: a superseded fact is annotated, never rewritten and never removed. The
original wording stays legible so the record shows what was believed and when.
All five of these are mine.
"""

import pathlib
import re

SRC = pathlib.Path("docs/research/SYNTHESIS.md")

MARK = {
    341: " **RE-OPENED by M40 (fact 455): the premise is false.** The ROI called \"a flat ROI, where no detail can exist\" spans **3.5x** in per-frame corrected detail across the sweep, and the modal winner frame carries **1.2670x** the reference frame's detail *unmerged*. The +35.47% is therefore mostly the reference frame's own defocus, not a merge defect. The defect may still exist; this measurement of it does not establish it.",
    428: " **REFUTED AS A REPAIR by M40 (facts 443, 446, 457).** The 0.8854x reproduces exactly, but the same estimator reads **1.0347x and 1.3147x** on 119MSDCF's flat ROIs — the credit is removed on one ROI of one stack and survives at +31.5% on another. The constant also **exceeds its own ceiling**: a pure-noise plant caps the operator at 1.045x. It was a fit to the ROI it was measured on.",
    429: " **CONFIRMED and STRENGTHENED by M40 (fact 459).** M40 shows it was a *double* tautology: with `black_dn = 0.0` both sides reduce to the same expression divided by `sqrt(n) >= 1`, and the second assertion was the algebraic identity. Understated here, not overstated.",
    430: " **REFUTED AS FRAMED by M40 (fact 454).** On a genuinely detail-free plant the corrected metric reads **-11.63 DN** where truth is 0, so the correction **crosses zero and lands further from truth than the defect it replaced** — and the shipped `max(0,.)` hides it. The -11.5% was not an overshoot to be tuned away; it was the sign of a wrong correction.",
    431: " **REFUTED by M40 (fact 448).** The plant's inflation by acceptance-set size at gate 1.0 is **1.0770, 1.0591, 1.0454, 1.0383, 1.0319, 1.0293, 1.0286, 1.0220** for n = 1..8 — a **smooth decay, not a step**. `selection_inflation(n>=2) = 1.0` is wrong at every n tested, and the two-branch step drives a 7.4-point discontinuity through the 41.66% of the plane sitting at n = 1.",
}


def main():
    text = SRC.read_text(encoding="utf-8")
    lines = text.split("\n")
    hits = 0
    for i, line in enumerate(lines):
        m = re.match(r"^\| (\d+) \| ", line)
        if not m:
            continue
        n = int(m.group(1))
        if n not in MARK:
            continue
        cells = re.split(r"(?<!\\)\|", line)
        if len(cells) != 6:
            raise SystemExit(f"row {n}: expected 4 cells, got {len(cells) - 2}")
        if "RE-OPENED by M40" in cells[3] or "by M40" in cells[3]:
            raise SystemExit(f"row {n} already marked - refusing to double-mark")
        cells[3] = cells[3].rstrip() + MARK[n] + " "
        lines[i] = "|".join(cells)
        hits += 1
    if hits != len(MARK):
        raise SystemExit(f"marked {hits}, expected {len(MARK)}")
    SRC.write_text("\n".join(lines), encoding="utf-8")
    print(f"marked {sorted(MARK)}")


if __name__ == "__main__":
    main()

"""Amend fact 1258: replace my hand-computed "~2.5x" with the measured
per-channel numbers, and state the mechanism more precisely.

This is a precision refinement of my own fact from the same session, not a
retraction -- the direction and the conclusion are unchanged. checkmid.py
recomputed the normalised mid-band change from the reported quantities and
got 0.297x (R), 0.564x (G), 0.439x (B), a median factor of 2.28 rather than
the 2.5 I wrote. The amendment is marked inline so the change is visible
rather than silent.
"""
import io

SYN = "docs/research/SYNTHESIS.md"

OLD = ("In absolute "
       "terms the mid-band SD fell ~2.5x; it dominates because everything "
       "around it fell 10x.")
NEW = ("Normalised by mean level the mid-band fell only "
       "**0.297x (R), 0.564x (G), 0.439x (B)** -- a median factor of **2.28** "
       "-- while the fine noise fell **10.3x, 7.4x and 8.4x**. **The mottle "
       "dominates the residual because of the gap between those two numbers, "
       "not because it grew.** (Amended: as first folded this read '~2.5x', "
       "computed by hand from ratios of ratios; `checkmid.py` recomputed it "
       "and the correct median factor is 2.28. Direction and conclusion "
       "unchanged.)")

s = io.open(SYN, encoding="utf-8").read()
assert s.count(OLD) == 1, "expected exactly one occurrence, found %d" % s.count(OLD)
s = s.replace(OLD, NEW)
assert "0.297x (R)" in s
io.open(SYN, "w", encoding="utf-8", newline="\n").write(s)
print("SYNTHESIS: fact 1258 amended with the measured mid-band factors")

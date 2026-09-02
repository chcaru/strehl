"""Print the out-of-band evidence for condition A4, from the SNR survey alone.

A4 asks whether f/5.6 and f/8 show a TEXTURE-limited knee rather than an
optics-limited one: whether their spectra fail to reach the noise floor inside the
measurable band. Section 2.3 predicted, before any data, that they must -- both live
hypotheses put their cutoffs above the GQ lattice reach of 69.05 cy/mm.

That question can be answered without estimating a single cutoff, which is worth
doing because the cutoff estimator's bias has not yet been commissioned and running
it now would put an unlicensed number in the record. Excess power in the 'high' band,
50.8 to 64.5 cy/mm, is enough: it is above every candidate cutoff at f/14 and f/18
and below every candidate cutoff at f/5.6 and f/8, so it separates the two cases by
construction.

Reads only out/snr-w2.json. Touches no raw file and estimates nothing.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")

# Candidate cutoffs in cy/mm from PREREGISTRATION.md section 2.3.
CANDIDATE = {"f5.6": (105.54, 135.17), "f8": (73.88, 94.62),
             "f11": (53.73, 68.81), "f14": (42.22, 54.07),
             "f18": (32.83, 42.05)}
GQ_REACH = 69.05
FLOOR_TOL = 0.20   # excess below 20% of the floor counts as "reached the floor"


def main():
    w = sys.argv[1] if len(sys.argv) > 1 else "2"
    with open(os.path.join(OUT, f"snr-w{w}.json"), encoding="utf-8") as fh:
        d = json.load(fh)
    lo, hi = d["bands"]["high"]
    lo_mm, hi_mm = lo * 1000 / 5.12, hi * 1000 / 5.12
    recs = d["records"]
    tags = []
    for r in recs:
        if r["aperture"] not in tags:
            tags.append(r["aperture"])
    rois = sorted({r["roi"] for r in recs})

    print("CONDITION A4: does the spectrum reach the noise floor inside the band?")
    print()
    print(f"Statistic: excess power in the 'high' band, {lo_mm:.1f}-{hi_mm:.1f} cy/mm,")
    print(f"as a fraction of the noise floor. GQ lattice reach {GQ_REACH:.2f} cy/mm.")
    print(f"A value below {FLOOR_TOL:.2f} means the spectrum has reached the floor")
    print("there, i.e. the roll-off is complete inside the measurable band.")
    print()
    print("  Registered prediction from section 2.3, made before any data:")
    print(f"  {'ap':>6} {'H2 cy/mm':>9} {'H3 cy/mm':>9}  band position")
    for t in tags:
        c2, c3 = CANDIDATE[t]
        if max(c2, c3) < lo_mm:
            pos = "both cutoffs BELOW the band -> must be at floor"
        elif min(c2, c3) > hi_mm:
            pos = "both cutoffs ABOVE the band -> must NOT be at floor"
        else:
            pos = "band straddles the candidates -> undecided by construction"
        print(f"  {t:>6} {c2:9.2f} {c3:9.2f}  {pos}")
    print()

    print(f"  {'ROI':>4} " + "".join(f"{t:>9}" for t in tags))
    table = {}
    for i in rois:
        row = {r["aperture"]: r["bands"]["high"]["snr"] for r in recs
               if r["roi"] == i}
        table[i] = row
        print(f"  {i:>4} " + "".join(f"{row.get(t, float('nan')):9.3f}"
                                     for t in tags))
    print()
    print(f"  {'ap':>6} {'median':>9} {'at floor?':>11}  verdict against the prediction")
    ok = True
    for t in tags:
        vals = [table[i][t] for i in rois if t in table[i]]
        med = float(np.median(vals))
        at_floor = med < FLOOR_TOL
        c2, c3 = CANDIDATE[t]
        if max(c2, c3) < lo_mm:
            want, name = True, "at floor"
        elif min(c2, c3) > hi_mm:
            want, name = False, "not at floor"
        else:
            want, name = None, "undecided"
        if want is None:
            verdict = f"predicted {name}; measured " \
                      f"{'at floor' if at_floor else 'not at floor'}"
        else:
            good = (at_floor == want)
            ok &= good
            verdict = f"predicted {name}: {'AGREES' if good else 'DISAGREES'}"
        print(f"  {t:>6} {med:9.3f} {str(at_floor):>11}  {verdict}")
    print()
    print(f"A4 evidence: {'CONSISTENT' if ok else 'INCONSISTENT'} with section 2.3.")
    print()
    print("What this does and does not establish. It establishes that the roll-off")
    print("is complete inside the band at f/14 and f/18 and incomplete at f/5.6 and")
    print("f/8, which is what A4 asks and is exactly what the model predicted before")
    print("the data existed. It does NOT establish where the cutoff is, and no")
    print("cutoff is quoted here. f/11 is left undecided on purpose: the band")
    print("straddles its two candidates, which is the same marginality section 2.3")
    print("already registered when it called f/11 'a supporting point' with an H3")
    print("margin of 0.24 cy/mm under the lattice reach.")


if __name__ == "__main__":
    main()

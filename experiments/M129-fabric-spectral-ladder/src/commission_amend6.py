"""Commission check_amend6.py by planting defects it must catch.

It has already caught two errors I did not plant -- two cells of the SNR table read
off a single ROI's row instead of the median -- which is the strongest evidence a
checker can offer. This adds the deliberate half: every class of figure it claims to
guard is corrupted in turn, on a COPY, and the checker must go red and must name the
right line.

Two rules from the house, both learned the hard way and both enforced here:

  Anchor every mutation on a unique full-line string and hard-error if it does not
  land. A bare replace(old, new, 1) that silently misses produces a green run that
  looks like a passing control and is actually a test of nothing.

  Never mutate the real file. The copy lives in TEMP and the original is never
  written, so there is no path by which a failed control can damage the record.

Exit code 0 only if every plant is caught.
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(HERE, "PREREGISTRATION.md")
CHECKER = os.path.join(HERE, "src", "check_amend6.py")

# (name, unique full line to find, replacement, substring the failure must name)
PLANTS = [
    ("SNR table, knee row",
     "| knee, 29.3-44.9 cy/mm | 18.6 | 23.1 | 39.7 | 23.2 | 7.7 |",
     "| knee, 29.3-44.9 cy/mm | 18.6 | 23.1 | 39.7 | 23.2 | 9.9 |",
     "knee band, f18"),
    ("SNR table, low row",
     "| low, 7.8-17.6 cy/mm | 2011 | 1707 | 2802 | 2591 | 1730 |",
     "| low, 7.8-17.6 cy/mm | 2011 | 1707 | 2802 | 2591 | 1930 |",
     "low band, f18"),
    ("equalisation cost, a floor multiplier",
     "| 4 | 2.23 | 1.55 | 6.10 | 2.73 |",
     "| 4 | 1.23 | 1.55 | 6.10 | 2.73 |",
     "ROI 4 f11 floor multiplier"),
    ("equalisation cost, a residual ratio",
     "| 2 | 1.65 | 1.48 | 5.59 | 3.39 |",
     "| 2 | 1.65 | 1.48 | 5.59 | 4.39 |",
     "ROI 2 knee ratio after"),
    ("units table, the ratio",
     "| low band, the artefact alone | 1.72x | **3.1 points** |",
     "| low band, the artefact alone | 2.72x | **3.1 points** |",
     "low primary-arm ratio"),
    ("units table, the derived points",
     "| knee band, contaminated by the signal | 5.69x | 9.9 points |",
     "| knee band, contaminated by the signal | 5.69x | 19.9 points |",
     "knee differential points"),
    ("A4 table",
     "| 0.557 | 0.708 | 0.823 | 0.083 | **-0.021** |",
     "| 0.557 | 0.708 | 0.823 | 0.483 | **-0.021** |",
     "high band, f14"),
    ("prose range, floor multiplier",
     "The floor rises by 1.47x to 2.23x, which is a real but modest cost. **The residual",
     "The floor rises by 1.47x to 3.23x, which is a real but modest cost. **The residual",
     "max floor multiplier"),
    ("prose range, residual knee ratio",
     "knee-band ratio of 2.7x to 3.6x is not a failure to equalise: it is the roll-off",
     "knee-band ratio of 1.7x to 3.6x is not a failure to equalise: it is the roll-off",
     "min residual knee ratio"),
    ("6b linearity table",
     "| 8000 | 7936.1 | 0.992 |",
     "| 8000 | 7936.1 | 0.892 |",
     "added v 8000, rise/v"),
    ("6b arms table, a bias",
     "| loud, as captured | 19 | -17.53% | 2.51 |",
     "| loud, as captured | 19 | -19.53% | 2.51 |",
     "loud_raw bias"),
    ("6b arms table, an sd",
     "| quiet, equalised | 19 | -18.62% | 1.88 |",
     "| quiet, equalised | 19 | -18.62% | 2.88 |",
     "quiet_eq sd"),
    ("6b gap sentence",
     "**Differential bias falls from 9.77 points to 1.09 points**, a factor of 9.",
     "**Differential bias falls from 9.77 points to 2.09 points**, a factor of 9.",
     "gap after"),
    ("6b slope sentence",
     "directly: 9.77 points across a 9.0x power ratio is **4.4 points per e-fold**. Applied",
     "directly: 9.77 points across a 9.0x power ratio is **5.4 points per e-fold**. Applied",
     "slope, points/e-fold"),
    # --- Amendment 7 ------------------------------------------------------
    # Anchors here end in "\n" on purpose. "| f/5.6 | 3.402 |" is a SUBSTRING of
    # Amendment 7a's wider rows for the same aperture, so without the newline the
    # anchor matches three times and the control voids itself.
    ("7 slope table",
     "| f/5.6 | 3.402 |\n",
     "| f/5.6 | 3.502 |\n",
     "slope, f5.6"),
    ("7 slope headline, the sd",
     "**The fabric's MEASURED low-band slope is alpha = 3.126, ROI-to-ROI sd 0.294.**",
     "**The fabric's MEASURED low-band slope is alpha = 3.126, ROI-to-ROI sd 0.394.**",
     "slope, overall sd"),
    ("7 aperture spread",
     "spread of the mean slope is **0.1553**; within-aperture, ROI to ROI, it is **0.2467**;",
     "spread of the mean slope is **0.1653**; within-aperture, ROI to ROI, it is **0.2467**;",
     "between-aperture spread"),
    ("7 bias-vs-slope table",
     "| 3.126 | -4.24% | 1.05 |",
     "| 3.126 | -5.24% | 1.05 |",
     "alpha 3.126, bias"),
    ("7 points per alpha",
     "**-2.35 points per unit of alpha.** At 2.2, what every earlier test planted: -1.53%.",
     "**-3.35 points per unit of alpha.** At 2.2, what every earlier test planted: -1.53%.",
     "points per unit alpha"),
    ("7 quantisation, bin size",
     "index, and one radial bin is **4.340%** of `f_c`. The smallest gap between any two",
     "index, and one radial bin is **5.340%** of `f_c`. The smallest gap between any two",
     "one bin, % of f_c"),
    ("7 T6 table",
     "| re-emergent bins observed | 1 |",
     "| re-emergent bins observed | 3 |",
     "T6, bins observed"),
    # --- Amendment 7a -----------------------------------------------------
    ("7a blocked effect table",
     "| f/5.6 | 3.402 | +0.2761 | +3.91 |",
     "| f/5.6 | 3.402 | +0.3761 | +3.91 |",
     "7a effect, f5.6"),
    ("7a sign test",
     "assumes nothing at all: **f/18 minus f/11 is positive in 6 of 6 ROIs**, mean",
     "assumes nothing at all: **f/18 minus f/11 is positive in 5 of 6 ROIs**, mean",
     "7a sign positives"),
    ("7a steepening table",
     "| f/18 | 0.1681 | +1.6190 | 0.2153 | +1.0942 |",
     "| f/18 | 0.1781 | +1.6190 | 0.2153 | +1.0942 |",
     "7a f_c H2, f18"),
    ("7a object table",
     "| f/18 | 3.168 | 1.5493 | 2.0741 |",
     "| f/18 | 3.168 | 1.6493 | 2.0741 |",
     "7a object H2, f18"),
    ("7a mean object slope",
     "Mean object slope **2.260** under H2, **2.515** under H3 - within **0.060** of the",
     "Mean object slope **2.360** under H2, **2.515** under H3 - within **0.060** of the",
     "7a object mean H2"),
    ("7a predicted steepening",
     "f/18 is +0.2198 where diffraction alone predicts +0.5335 (H3) to +0.8450 (H2). A",
     "f/18 is +0.2198 where diffraction alone predicts +0.5335 (H3) to +0.9450 (H2). A",
     "7a predicted arm H2"),
    ("7a band tilt",
     "band spanning 2.25x in frequency tilts one end relative to the other by **1.195x**,",
     "band spanning 2.25x in frequency tilts one end relative to the other by **1.295x**,",
     "7a band tilt"),
    # --- Amendment 8 ------------------------------------------------------
    ("8 harness table",
     "| 0.3000 | 0.2845 | 0.9483 | 10505 |",
     "| 0.3000 | 0.2845 | 0.9283 | 10505 |",
     "harness planted 0.30, ratio"),
    ("8 margin table, B_hat",
     "| H3 | equalised | 2.7147 | 0.0106 | 0.0245 | 2.3 |",
     "| H3 | equalised | 2.8147 | 0.0106 | 0.0245 | 2.3 |",
     "B_hat H3 equalised"),
    # The distance column must equal |B_hat - boundary|. Moving ONLY the distance
    # leaves every external figure intact, so nothing outside the document can
    # catch it. The internal-consistency check is the only thing that can.
    ("8 margin table, distance alone",
     "| H2 | equalised | 3.3172 | 0.0061 | 0.5780 | 94.4 |",
     "| H2 | equalised | 3.3172 | 0.0061 | 0.5280 | 94.4 |",
     "distance H2 equalised"),
    ("8 forward table",
     "| native | f18 | 0.1595 | 0.1982 | 19.5% | 40.9 |",
     "| native | f18 | 0.1595 | 0.1982 | 19.5% | 44.9 |",
     "forward native f18, sigma"),
    ("8 reach table",
     "| f11 | 0.2751 | 0.7781 | 0.3523 | 0.9965 | both |",
     "| f11 | 0.2751 | 0.7781 | 0.3523 | 0.9765 | both |",
     "reach f11, H3/Nyq"),
    ("8 combined separation",
     "Combined separation **60.6 sigma** native, **55.5 sigma** equalised, against **2.3**",
     "Combined separation **66.6 sigma** native, **55.5 sigma** equalised, against **2.3**",
     "forward combined, native"),
    ("8 Nyquist in prose",
     "so the largest cutoff the GQ lattice can represent is `0.5 / sqrt(2)` = **0.35355**",
     "so the largest cutoff the GQ lattice can represent is `0.5 / sqrt(2)` = **0.36355**",
     "GQ Nyquist in prose"),
]


def run(doc):
    r = subprocess.run([sys.executable, CHECKER, doc], capture_output=True,
                       text=True)
    return r.returncode, r.stdout + r.stderr


def main():
    rc, out = run(DOC)
    print(f"baseline on the real document: exit {rc}")
    if rc != 0:
        print("BASELINE IS NOT GREEN. Commissioning a checker against a document")
        print("that already fails proves nothing; fix the document first.")
        print(out)
        return 1
    print()

    tmpdir = tempfile.mkdtemp(prefix="amend6-")
    with open(DOC, encoding="utf-8") as fh:
        original = fh.read()
    caught = 0
    for name, old, new, must_name in PLANTS:
        n = original.count(old)
        if n != 1:
            print(f"  ANCHOR MISS  {name}: the anchor line occurs {n} times, "
                  f"not once. The plant cannot be placed unambiguously, so this")
            print(f"               control is void rather than passing.")
            return 1
        path = os.path.join(tmpdir, "PREREGISTRATION.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(original.replace(old, new, 1))
        rc, out = run(path)
        named = any(l.startswith("  FAIL") and must_name in l
                    for l in out.splitlines())
        ok = rc != 0 and named
        caught += ok
        if ok:
            verdict = "caught, and named the right line"
        elif rc != 0:
            verdict = f"went red but did NOT name '{must_name}' -- wrong line"
        else:
            verdict = "MISSED, the checker stayed green"
        print(f"  {'ok  ' if ok else 'FAIL'} {name:40s} {verdict}")

    shutil.rmtree(tmpdir, ignore_errors=True)
    print()
    print(f"{caught}/{len(PLANTS)} plants caught")
    if caught == len(PLANTS):
        print("check_amend6.py is commissioned.")
        return 0
    print("check_amend6.py is NOT commissioned; do not rely on its green.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

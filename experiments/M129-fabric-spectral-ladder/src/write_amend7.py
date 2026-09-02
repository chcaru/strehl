import io
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(HERE, "PREREGISTRATION.md")

AMEND = """
---

### Amendment 7 - the texture slope was an assumption, and a new threat T6

Three things are recorded here. The subject's spectral slope is now measured rather
than assumed; the bias depends on it, in the direction predicted before the run; and
a threat specific to a *woven* subject, absent from T1-T5, is registered, tested and
retired for the two apertures that carry the measurement.

**The fabric's texture slope is alpha = 3.126, ROI-to-ROI sd 0.294.** `src/slope_survey.py`,
`out/slope-survey.txt`. Fitted as `log P = a - alpha log f` over the low band
0.040-0.090 sensor cyc/px with the noise floor subtracted, at each cell's own best
focus, over 30 (ROI, aperture) pairs.

| aperture | mean alpha |
| --- | --- |
| f/5.6 | 3.402 |
| f/8 | 3.080 |
| f/11 | 2.949 |
| f/14 | 3.031 |
| f/18 | 3.168 |

**Every synthetic test in this lane planted 2.2.** That number was an inherited guess
and it was never the subject's. T3 registered that the subject spectrum is not flat
and argued the ratio cancels it; that argument is untouched. What was never checked is
whether the *estimator's bias* depends on the slope. It does.

**The slope is aperture-independent, which is the load-bearing part.** Amendment 6's
equalisation assumes that below the cutoff the spectrum differs between apertures only
in scale, so that matching the low-band SNR matches the noise and not the optics.
Between-aperture spread of the mean slope is **0.1553**; within-aperture, ROI to ROI,
it is **0.2467**; ratio **0.63**. The apertures differ less from each other than the
ROIs do from each other, so there is no aperture-dependent shape to confound the
equalisation.

**A potency control, and two failures before it worked.** A verdict of "the spreads
are comparable" is worth nothing from a test that cannot tell them apart.

1. *Floor subtraction as the disturbance.* Moved the fitted slopes by 0.003. This is
   not a failed control but a measurement: in the low band the signal sits 1000-5000x
   above the floor, so floor subtraction cannot matter there. It retires the worry
   that the low band might be floor-contaminated - the worry that motivated choosing
   that band in Amendment 6.
2. *A planted aperture ramp, specified by span.* The fit recovered the plant with
   **0.0000** error and the verdict still did not flip. A linear ramp across five
   points has a standard deviation of only **0.354** times its span, so a ramp of span
   0.5 is a spread of 0.177 - smaller than the within-aperture spread it had to beat.
   The lesson is general: **specify a plant by the statistic the test compares.** Here
   the test compares standard deviations, so the plant must be sized in standard
   deviations.
3. *The same ramp, specified by standard deviation.* Recovered exactly, verdict
   flipped. The control passes.

**The bias is worse on a steeper texture, as predicted in writing beforehand.**
`src/slope_bias.py`, `out/slope-bias.txt`. Low-band SNR held at 2000 by adding noise
so the slope is the only variable, planted `f_c` = 0.1273 sensor cyc/px, 16 replicates
per point. The prediction registered in the script's docstring before it was ever run
was that the bias becomes **more negative** as alpha grows, because a steeper spectrum
reaches the floor at a lower frequency.

| alpha | bias | sd |
| --- | --- | --- |
| 2.000 | -0.44% | 1.05 |
| 2.200 | -1.53% | 2.01 |
| 2.600 | -3.97% | 1.44 |
| 3.000 | -3.43% | 1.88 |
| 3.126 | -4.24% | 1.05 |
| 3.400 | -4.24% | 1.05 |
| 3.800 | -5.06% | 1.44 |

**-2.35 points per unit of alpha.** At 2.2, what every earlier test planted: -1.53%.
At 3.126, what the fabric is: -4.24%. **Every bias figure this lane quoted before
today is optimistic by about 2.7 points.**

**The individual estimates are quantised, and the sweep says how much that matters.**
`src/slope_quant.py`, `out/slope-quantisation.txt`. Two rows above are identical to
four decimals in both mean and sd, which does not happen by chance across 16
independent replicates. The cause is quantisation: the estimator returns a radial bin
index, and one radial bin is **4.340%** of `f_c`. The smallest gap between any two
distinct bias values is **0.2713** points, which is exactly one bin divided by 16
replicates - the signature of a quantised estimator averaged over replicates.

The means are still usable, because replicate standard deviations are 0.24-0.46 bins,
so replicates scatter across adjacent bins and the mean interpolates. Standard error
per row is 0.263-0.503 points, so the endpoint difference of 4.61 points is **10.4
sigma**. But a single row-to-row step of about 0.8 points is only 1.8 sigma.
**Registered rule for quoting this result: quote the fitted slope and the endpoints;
do not quote row-to-row differences.** The tie at alpha 3.126 and 3.400 is the grid,
and the non-monotone step from 2.6 to 3.0 is replicate scatter.

**An unplanned second result, and it is about the ladder rather than the sweep.** One
radial bin being 4.340% of `f_c` is the estimator's intrinsic resolution on a single
(ROI, aperture) cell, and that applies to the real ladder, not only to this synthetic.
Section 2.2 separates H2 from H3 by 28.07% in `f_c*N`, so **the hypotheses lie 6.5
bins apart**, and averaging over the six ROIs would give a per-aperture standard error
near 0.58 points if the real data scatter like the synthetic. Resolution is not what
threatens this lane. The bias is.

### T6 - the subject is a weave, and a weave is periodic

**Registered here rather than in section 4 because it was not thought of then.** T1-T5
all treat the subject spectrum as smooth: a power law rolled off by a diffraction MTF.
A weave is periodic, and a periodic structure puts discrete peaks in the spectrum. If
a harmonic lands near the cutoff, the spectrum can fall to the floor at the end of the
roll-off and then be lifted back out of it, so the last detectable bin is the harmonic
and not the cutoff. That biases `f_c` **high**, toward H3. It is the only mechanism
found in this lane that pushes opposite to T1 and to the SNR bias, so it cannot be set
aside as conservative.

**Test and result.** `src/weave_peaks.py`, `out/weave-peaks.txt`. Reads the saved
radial PSDs; estimates no cutoff. A bin counts as a re-emergence if it stands 3 sigma
above the floor - the same rule `m5_lib.knee` uses - at a frequency **above** the one
where that spectrum first reaches the floor. Danger zone 30-55 cy/mm, bracketing the
H2 and H3 candidates at f/14 and f/18.

| | measured |
| --- | --- |
| bins examined, 6 ROIs x 5 apertures | 1350 |
| false positives expected at 3 sigma | 1.8 |
| re-emergent bins observed | 1 |
| most cells sharing one frequency | 1 of 30 |

The single detection is ROI 4 at f/5.6, 54.5 cy/mm, standing 0.166 of the floor. **The
count is below chance and nothing repeats at a fixed frequency**, which is the
discriminating test: a genuine weave harmonic is a property of the fabric, so it must
sit at one frequency and recur across ROIs and apertures. An isolated bin is what
chance looks like. f/5.6 is in any case an out-of-band control under section 2.3, not
part of the measurement.

**Sensitivity, stated rather than implied.** The smallest re-emergence this null
covers is 0.234 of the floor at 29.7 cy/mm, 0.208 at 36.1, 0.195 at 43.7 and 0.170 at
52.3, set by the number of samples in each radial bin. A harmonic smaller than that is
invisible here - **and equally invisible to the crossing estimator, which uses the same
rule**, so it cannot move the measurement either.

**Three control failures, all of them mine, all caught by the control.** Recorded
because the third is the one that would have produced a false all-clear.

1. *Wrong reference.* Peaks were first measured against the power law extrapolated from
   the low band. Above the cutoff that extrapolation carries no roll-off and so sits
   far above the data; planted harmonics of 3x, 4x and 8x were **all missed**. The
   reference has to be the floor, because the floor is what the estimator compares
   against.
2. *Wrong demand.* The control then required the detector to see a re-emergence of 30%
   of the floor at a frequency where its own threshold was 50%. But the detector shares
   the estimator's rule, so a harmonic it cannot see is one the estimator cannot see;
   demanding more sensitivity than the estimator has tests the wrong thing. Replaced by
   a threshold calibration: plant at 1.5x the local threshold and require a hit, at
   0.5x and require a miss.
3. *Wrong position.* The calibration planted at fixed frequencies of 36 and 44 cy/mm,
   which on that spectrum lie **below** where it first reaches the floor, so the
   re-emergence rule excluded them by construction and the control read FAIL against a
   detector that was behaving correctly. Plant positions must be derived from the
   spectrum being planted into. With that fixed the control passes at all three
   positions, hit and miss.

**Verdict: T6 is retired for f/14 and f/18**, the two apertures section 2.3 calls the
measurement, at the stated sensitivity. It is not retired in general and the test is
kept in the reduction, because passing on this capture is not passing on every capture.
"""


def main():
    with io.open(DOC, encoding="utf-8") as fh:
        text = fh.read()
    if "### Amendment 7" in text:
        raise SystemExit("Amendment 7 already present")
    text = text.rstrip("\n") + "\n" + AMEND.replace("\r\n", "\n")
    if not text.endswith("\n"):
        text += "\n"
    with io.open(DOC, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    # A blank line inside a Markdown table silently splits it in two.
    lines = text.split("\n")
    bad = []
    for i in range(1, len(lines) - 1):
        if not lines[i].strip() and lines[i - 1].lstrip().startswith("|") \
                and lines[i + 1].lstrip().startswith("|"):
            bad.append(i + 1)
    print("wrote Amendment 7")
    print("blank lines splitting a table:", bad if bad else "none")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

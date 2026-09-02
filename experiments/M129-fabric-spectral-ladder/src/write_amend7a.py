import io
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(HERE, "PREREGISTRATION.md")

AMEND = """
---

### Amendment 7a - the low band is not free of the optics, and Amendment 7 mis-stated its own headline

Amendment 7 was written and machine-checked before this was noticed. Two of its claims
are wrong and are corrected here rather than edited away. The error was found by its
own checker: a tolerance disagreement on an unrelated figure forced a reading of the
per-ROI table, and f/18 turned out to be steeper than f/11 in every single ROI.

**The measured slope IS aperture-dependent.** `src/slope_paired.py`,
`out/slope-paired.txt`. Amendment 7 compared the spread of the five aperture means
(0.1553) against the mean ROI-to-ROI spread within one aperture (0.2467) and read
independence from 0.1553 <= 0.2467. **That test throws away the pairing.** The same
six ROIs are measured at every aperture, so ROI-to-ROI variation is a shared block
effect and contributes nothing to the difference between apertures. Removing the ROI
main effect first:

| aperture | mean alpha | effect | t |
| --- | --- | --- | --- |
| f/5.6 | 3.402 | +0.2761 | +3.91 |
| f/8 | 3.080 | -0.0462 | -0.65 |
| f/11 | 2.949 | -0.1773 | -2.51 |
| f/14 | 3.031 | -0.0951 | -1.35 |
| f/18 | 3.168 | +0.0425 | +0.60 |

Residual sd 0.1730 on 20 df, standard error of each effect 0.0706. And the test that
assumes nothing at all: **f/18 minus f/11 is positive in 6 of 6 ROIs**, mean
difference +0.2198, sign-test **p = 0.031**.

**There is no aperture in this ladder at which the low band is free of the optics.**
This is the substantive finding and it corrects Amendment 6, not only Amendment 7. The
incoherent diffraction MTF falls monotonically from zero frequency; it has no flat
region. Amendment 6 chose the low band because it sits *below every candidate cutoff at
every aperture* and treated it as optics-free. **Being below the cutoff and being
unaffected by it are different things.** Planting an object slope of exactly 3.000 and
fitting the same low band returns:

| aperture | f_c H2 | steepening H2 | f_c H3 | steepening H3 |
| --- | --- | --- | --- | --- |
| f/5.6 | 0.5404 | +0.3349 | 0.6921 | +0.2525 |
| f/8 | 0.3783 | +0.5131 | 0.4844 | +0.3805 |
| f/11 | 0.2751 | +0.7740 | 0.3523 | +0.5608 |
| f/14 | 0.2161 | +1.0879 | 0.2768 | +0.7675 |
| f/18 | 0.1681 | +1.6190 | 0.2153 | +1.0942 |

Pure model arithmetic; no measurement enters. The fitting harness was verified first:
with the MTF removed it recovers a planted index to **1.7e-11**.

**A NaN walked through that harness gate on the first attempt.** The check passed
`n_eff = 1e9` intending "no MTF", but a large effective f-number is a *tiny* cutoff,
so the MTF was zero everywhere, the fit returned `nan`, and the gate `nan > 1e-6`
evaluated False and printed "harness OK". No MTF means an *infinite* cutoff, `n_eff`
approaching zero. Recorded because the failure mode is general: **a numerical gate
must test for finiteness explicitly, or NaN satisfies it silently.**

**The object slope is 2.26 to 2.52, and 2.2 was approximately right all along.**
`src/slope_object.py`, `out/slope-object.txt`. `equalise._scene` builds amplitude as
`r**(-slope/2)` and *then* multiplies by the MTF, so its `slope` argument is an
**object** slope. Amendment 7 put the measured value into it. Inverting each measured
per-aperture slope through that aperture's own MTF:

| aperture | measured | object H2 | object H3 |
| --- | --- | --- | --- |
| f/5.6 | 3.402 | 3.0671 | 3.1494 |
| f/8 | 3.080 | 2.5665 | 2.6991 |
| f/11 | 2.949 | 2.1745 | 2.3877 |
| f/14 | 3.031 | 1.9428 | 2.2633 |
| f/18 | 3.168 | 1.5493 | 2.0741 |

Mean object slope **2.260** under H2, **2.515** under H3 - within **0.060** of the
long-assumed 2.2 under H2. **Amendment 7's claim that every earlier synthetic planted
the wrong slope is withdrawn.** Synthetic work in this lane must plant an object slope
near **2.3**, swept over 1.9 to 2.7.

**Amendment 7's bias-versus-slope result survives, with its axis relabelled.** The
measurement that bias moves **-2.35 points per unit of slope** is unaffected, because
`slope_bias.py` swept `_scene`'s argument, which is the object slope. What changes is
where the subject sits on that axis: near 2.3, not 3.126. So the applicable bias is
about **-1.8%**, not -4.24%, and **Amendment 7's figure is pessimistic rather than
optimistic.** The lane is not endangered by the error; the number was simply wrong.

**A residual confound remains, and its sign identifies it.** The inferred object
slopes above are not constant - they fall monotonically from 3.07 at f/5.6 to 1.55 at
f/18 under H2. The subject cannot change with aperture, so something is left over.
Removing the full MTF steepening **overshoots**: observed steepening across f/11 to
f/18 is +0.2198 where diffraction alone predicts +0.5335 (H3) to +0.8450 (H2). A
second aperture-dependent effect is therefore present **with the opposite sign to
diffraction**. The registered candidate is **T1, the primary threat**: wider apertures
have shallower depth of field, so more of the ROI is defocused, and defocus steepens
the spectrum - largest at f/5.6, smallest at f/18, exactly the sign required. This is
the first *quantitative* handle this lane has on T1's size, and it was obtained
without a defocus sweep.

**f/5.6 is the odd one out and diffraction predicts the opposite.** Diffraction makes
f/5.6 the *shallowest* measured slope, its cutoff being furthest above the band. It is
instead the steepest, at 3.402, with the largest effect in the blocked table
(+0.2761, t = +3.91). That is T1 again, and it is consistent with section 2.3 already
treating f/5.6 as an out-of-band control rather than a measurement.

**What this costs the equalised arm, stated rather than absorbed.** Equalising the low
band assumes the band's *shape* is common and only its *level* differs. That
assumption is now measurably false. A residual slope difference of 0.2198 across a
band spanning 2.25x in frequency tilts one end relative to the other by **1.195x**,
against a level ratio of **1.72x** being corrected - so the shape error is about
**27%** of the level difference. Not negligible, not dominant. It is carried as an
uncertainty on the equalised arm, and it is a further reason Amendment 5 required both
arms to be reported rather than averaged.
"""


def main():
    with io.open(DOC, encoding="utf-8") as fh:
        text = fh.read()
    if "### Amendment 7a" in text:
        raise SystemExit("Amendment 7a already present")
    text = text.rstrip("\n") + "\n" + AMEND.replace("\r\n", "\n")
    if not text.endswith("\n"):
        text += "\n"
    with io.open(DOC, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    lines = text.split("\n")
    bad = []
    for i in range(1, len(lines) - 1):
        if not lines[i].strip() and lines[i - 1].lstrip().startswith("|") \
                and lines[i + 1].lstrip().startswith("|"):
            bad.append(i + 1)
    print("wrote Amendment 7a")
    print("blank lines splitting a table:", bad if bad else "none")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

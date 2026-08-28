# V-DCNULL

Lane report. Does the DC-offset defect V-H2H2 found in
`experiments/ORCH-drift-check/contrast_ms.py` also contaminate the published
merge-versus-best-single-frame band ratios on `113MSDCF`?

**Verdict: NO for the DC mechanism, MEASURED. The published sign survives and the
published magnitude survives. A DIFFERENT and unguarded sensitivity was found in the
same instrument -- it is `gain`-covariant, not DC-covariant -- and it is large enough
to matter, but nothing in this lane shows it fired.**

Harness `experiments/V-DCNULL/dcnull.py`. Every number below was printed by one run of
it. No stack was rendered, no binary was run: all arms are synthetic plants pushed
through the committed scoring code, extracted from its own file on unique anchors that
hard-error if they do not land.

## 1. Which instrument produced the seven numbers. MEASURED by elimination.

The published figures `1.0997 / 1.1936 / 1.1345 / 0.9426 / 0.7314 / 0.6063 / 0.5942`
are **not** `bandqual.py`'s, and the `gnorm` per-frame gain normalisation named in the
brief is not on their path.

`V-SOFTCHECK-bandqual.md:406` sources them to `V-SOFTCHECK-nyquist.md`, whose "N
hypothesis" table carries a diagnostic column `max63/max32` that the report says "read
exactly 1.0000 at all seven bands". Exactly one file in the tree prints a column with
that name:

    git grep -n "max63" -- experiments
    experiments/V-SOFTCHECK/ncommon.py:49
    experiments/V-SOFTCHECK/ncommon.py:58

The producer is `experiments/V-SOFTCHECK/ncommon.py`. Its statistic is

    median over tiles of  rings(master)_b / max over k of rings(frame_k)_b

with `rings()` the scoring function. Three files carry `rings()`; the harness checks
they are **byte-identical** and reports `True`, so this result covers `ncommon.py`,
`ntest.py` and `ncurve.py` alike. `bandsweep.py` also measures a merge deficit but on
`119MSDCF`, `coffee-bubbles`, `109MSDCF` and `flower-bud-alone-cpl`, not `113MSDCF`,
and is ruled out. `ncurve.py` is master-to-master with no reference frames and cannot
produce a merge/ceiling ratio at all.

`bandqual.py` did not produce the seven numbers. It produced the qualification, `R =
3.3235` at 0.20-0.25, which decides which of them is quotable. It is audited separately
in section 5 because that job is load-bearing for the headline.

## 2. Commissioning the harness. MEASURED.

Two potency controls, because a null that reads 1.0000 on a dead probe is worthless.

Synthetic scene 1024x1024, 49 tiles of 256, 9 frames on a four-zone focus ladder,
median level 1222.7 DN. Baseline `merge / max-over-frames`, band 0.20-0.25: **0.5824**.

**P0, the probe must see a real blur.** Gaussian blur planted on the master:

| plant | 0.20-0.25 reading | max deviation from baseline |
| --- | ---: | ---: |
| none | 0.5824 | - |
| sigma 0.5 | 0.3911 | 6.198e-01 |
| sigma 1.0 | 0.0844 | 9.955e-01 |

**P1, the probe must see a DC-driven bias of the class under test.** `rings_meannorm`
is a deliberately sabotaged scorer that divides band power by the tile mean squared --
the vulnerability the brief asked about, built on purpose so the null in section 3 can
be shown to be a null and not a corpse. Same DC plant, same tiles:

| plant | 0.20-0.25 reading | max deviation from its own baseline |
| --- | ---: | ---: |
| none | 0.5824 | - |
| DC +250 DN on master | 0.4086 | 3.019e-01 |
| DC +1000 DN on master | 0.1852 | 6.910e-01 |

A pure DC offset moves the sabotaged scorer by up to 69%. The probe registers this
defect class. What follows is therefore a measurement and not an absence.

## 3. Q1, the DC-offset null on the real producer. PASSES. MEASURED.

True answer 1.0000 at every band: a constant added to an image is annihilated by every
band-pass in the bank. `rings()` subtracts the per-tile mean before windowing and its
annuli start at 0.05 cyc/px, so DC is removed twice over.

| arm | max deviation from baseline, all seven bands |
| --- | ---: |
| DC +250 DN on master only | 1.741e-07 |
| DC +1000 DN on master only | 2.320e-07 |
| DC -250 DN on master only | 0.000e+00 |
| DC +250 DN on all frames only | 1.976e-07 |
| DC +250 DN on both sides | 1.976e-07 |
| DC +250 DN on even frames only | 0.000e+00 |

Worst reading anywhere: **2.320e-07**, which is the float32 rounding floor of the
instrument's own `astype(np.float32)`, not a bias. Quadrupling the offset from 250 to
1000 DN raises it by 33%, not by 4x, which is the signature of rounding rather than of
a mechanism. Every published band read `0.9429 / 0.8447 / 0.7176 / 0.5824 / 0.4524 /
0.3424 / 0.2569` under every DC plant, unchanged to seven digits.

**The 0.9696 defect does not exist in this instrument.** It has no median-ratio
rescale, no tone rescale, and no division by any level statistic anywhere between the
TIFF and the ratio.

## 4. Q2, the pure-gain null on the real producer. FAILS, exactly and predictably. MEASURED.

A gain-normalising instrument would return 1.0000. `ncommon.py` does not normalise
gain and does not claim to. Multiplying one side by a constant `g`:

| arm | observed ratio to baseline | predicted `g^2` | relative error |
| --- | ---: | ---: | ---: |
| gain x1.1500 on master only | 1.322500 | 1.322500 | 7.72e-08 |
| gain x1.0327 on master only | 1.066469 | 1.066469 | 1.50e-07 |
| gain x1.1500 on both sides | 1.0000 (maxdev 5.453e-06) | 1.0000 | - |

The law is exact: `r_observed = r_true * (g_master / g_frame)^2`. It is a **relative**
gain law -- a gain common to both sides cancels completely.

What that costs the headline, printed by the harness:

- A true 1.0000 reads **0.9426** if `g_master/g_frame = 0.970876`, a **2.91%** level
  mismatch between the master and the single-frame references.
- A 1% master under-gain alone moves the reading by **0.0199**.

`ncommon.py` has **no exposure audit**. `grep` for `exposure`, `.log` or
`check_exposure` in that file returns nothing, while its sibling instruments
`dmeasure.py` and `d113measure.py` both hard-error on a gain mismatch before forming a
ratio, and `V-SOFTCHECK-nyquist.md` records this lane already falling into exactly this
trap once ("+2.33 against +0.85 ... that comparison was worthless"). The guard that
caught it there is absent here.

**This is a defect in the instrument. It is not evidence that the number is wrong.**
Nothing in this lane shows a gain mismatch was present, and section 7 says why it
cannot now be checked.

## 5. Q3, the qualifier. FAILS a DC null, but not by enough to move the verdict. MEASURED.

`bandqual.py` chose 0.20-0.25 as the highest band carrying real detail. Its `gnorm`
divides band power by the square of the per-frame median tile level, which a DC offset
moves. Truth for every arm below is 1.0000, because a DC offset changes no band power.

| arm | max deviation from baseline |
| --- | ---: |
| uniform DC +250 DN, frames sharing one mean | 8.260e-06 |
| DC +250 DN on even frames only | **4.421e-01** |
| gain x1.15 on all frames | 4.339e-07 |
| per-frame gain jitter 5% | 8.161e-07 |

The uniform arm passes only because my synthetic frames share a mean, so the two
`g` values entering the ratio cancel. Real probes do not share a mean; `bandqual.py`
prints their spread itself. Repeating with a real 4.01% level spread (1057.7 to 1219.2
DN, 1.153x):

| arm | max deviation from baseline |
| --- | ---: |
| spread + uniform DC +250 DN | 1.648e-02 |
| spread + uniform DC +1000 DN | 3.660e-02 |

So `bandqual.py` **does** carry the defect class: a DC offset biases `R` by up to 44%
when the offset is differential across frames, and by 1.6 to 3.7% under a uniform
offset on a realistically uneven stack. Its gain normalisation, by contrast, is exact
to 4.3e-07 -- `gnorm` does the job it was written for.

Whether that matters to the headline is a bounded question, and the bound was printed:

| quantity | published | deflated by the worst bias measured (0.4421) | bar |
| --- | ---: | ---: | ---: |
| `R` at 0.20-0.25 | 3.3235 | 2.3047 | 2.00 |
| CI low | 2.9495 | 2.0453 | 1.50 |

**PASS survives deflation.** The band that licenses the headline still qualifies even
if the qualifier were carrying the largest DC bias this lane could plant in it.

## 6. Q3, does the published conclusion change? MEASURED, in two parts.

**(a) The SIGN survives.** "Merge is softer than the best single frame above ~0.20
cyc/px" rests on `ncommon.py`, which returned its baseline unchanged to 2.320e-07 under
every DC plant tried, including one-sided, two-sided, negative and differential
offsets. There is no DC mechanism available to flip it.

**(b) The MAGNITUDE survives, against this mechanism.** "~5.7% short in the 0.20-0.25
band" would need a bias of order 3% to be meaningfully wrong. The DC bias measured on
the producing instrument is 2.3e-07, five orders of magnitude too small. The
qualification that makes 0.9426 the quotable number also survives, by section 5.

**The remaining exposure is not DC.** It is the `g^2` law of section 4, and 2.91% of
relative gain mismatch is exactly the size that would erase the whole 5.7%. That is a
real, unguarded, one-sided threat to the magnitude and it is named here rather than
dismissed.

**It is not a threat to the sign.** The gain mismatch that would explain each published
band as a true 1.0000, printed by the harness:

| band | 0.05-0.10 | 0.10-0.15 | 0.15-0.20 | 0.20-0.25 | 0.25-0.30 | 0.30-0.35 | 0.35-0.40 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| required mismatch | -4.87% | -9.25% | -6.51% | 2.91% | 14.48% | 22.13% | 22.92% |

One scalar cannot take seven values, and it cannot take opposite signs in the low bands
and the high bands. A gain mismatch multiplies all seven readings by one factor; it
cannot manufacture the frequency-dependent shape, which is the sign claim.

## 7. EVIDENCE GONE

`C:\dev\strehl-out\V-SOFTCHECK` does not exist. `Test-Path` returns `False`. With it
went `cache/113MSDCF--lin--T128.npz`, `srgb/113MSDCF/master.tiff`,
`srgb/113MSDCF/f000..f062.tiff` and `srgb-stride/113MSDCF-s2/`, which are every input
`ncommon.py` reads. The seven published numbers cannot be recomputed from their own
pixels by anyone, and this lane did not try. That is why every arm here is synthetic.

Specifically missing, and the reason section 4 stops where it does: the `.log` files
that would record the `--exposure` used for `srgb/113MSDCF/master.tiff` against the one
used for `f000..f062.tiff`. Without them the actual value of `g_master/g_frame` is
unrecoverable. `softcheck.py`'s design note asserts "no exposure gain, no tone curve"
for that path; that is an assertion in a docstring, not a measurement, and this lane
did not upgrade it.

## Kept artifacts

`experiments/V-DCNULL/dcnull.py`, self-contained, roughly 40 seconds, no image tree, no
binary, no render. It regenerates every number in this report.

## NOT MEASURED

- Whether `srgb/113MSDCF/master.tiff` and its 63 single-frame references were in fact
  developed at the same gain. Inputs deleted; see section 7. This is the one live
  threat to the published magnitude and it is now unfalsifiable without a re-render.
- The magnitude of the DC bias in `bandqual.py` on the real `113MSDCF` probes. It needs
  their actual per-frame level spread, which is gone. Section 5 substitutes a planted
  4.01% spread and a worst-case bound; it is not the real number.
- `bandqual.py`'s third PASS condition, `R_flat < 1.3`, under DC plant. Section 5 bounds
  only the `R` and CI-low conditions.
- The other six published bands' qualification status under DC bias. Only 0.20-0.25,
  the band the headline rests on, was bounded.
- Any of this on `119MSDCF`, `bee-1-cpl`, `109MSDCF`, `coffee-bubbles` or
  `flower-bud-alone-cpl`. One synthetic subject only.
- Whether the wall-pricing table in `V-SOFTCHECK-nyquist.md` (0.8795 to 0.7368) shares
  the producer audited here. Its band edges run to 0.50 and `ncommon.py`'s stop at
  0.40, so it does not, and its producer was not identified.

## Unverified

The scene generator, the plants and the two potency controls were written and checked by
one author. The harness has had no polarity audit: no arm of it has been deliberately
reversed to confirm it would report a failure it was told to report.

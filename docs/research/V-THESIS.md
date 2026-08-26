# V-THESIS: independent verification of the detail null

Adversarial re-test of `a533e831` (BUILD-THESIS, `experiments/BUILD-THESIS/REPORT.md`),
commissioned to break the result in **both** directions. The measuring instrument
here shares no code with BUILD-THESIS. Where their numbers are quoted they are
marked *reproduced*; where mine are quoted they are marked *independent*.

Harness: `experiments/V-THESIS/`. Outputs: `C:\dev\strehl-out\V-THESIS\`.

## Verdict on each finding

| # | finding | verdict |
| --- | --- | --- |
| 1 | no 1.2-1.8x detail gain; arms within 0.5 px; 0.5 px is also the noise gap | **direction CONFIRMED, number REFUTED** |
| 2 | selection wins on `flat-on-ruler-cpl` by ~0.4 px | **CONFIRMED** |
| 3 | the merge's advantage is noise and absence of invented structure | **CONFIRMED** |
| 4 | two candidate statistics killed for rising on blur | **UNVERIFIABLE** (code deleted) |
| 5 | S1 fails a noise null | **CONFIRMED, and worse than stated** |
| 6 | identity returns 1.000; inversion exact from 0.20 px up | **half CONFIRMED, half REFUTED** |

## The arms are comparable; the confounds the brief flagged are absent

Verified *independently*, not accepted:

* **One binary.** `Get-FileHash` on the scratch `strehl.exe` returns
  `4C0C6022ADF0A5E325275E7FFEA010D54B6B17925FE947B03A0A816E72FF7840`. All 77
  files of `git archive b9b6921e` hash-match the scratch tree with **0
  mismatches and 0 extra .rs files**. All 12 provenance sidecars carry that
  sha256 and `exit: 0`. No cross-build comparison is involved.
* **Camera-linear.** The merge TIFF's ImageDescription reads *"Linear
  camera-native RGB ... no transfer curve"*. The argmax arm carries no such tag,
  but its histogram median sits beside the merge's (leaf-2: 2481 against 2553 DN)
  where an sRGB-curved copy would sit near 14400. `--srgb` appears in no argv.
* **Registration is not the false negative.** My instrument compares *power
  spectra indexed by cycles-across-tile*, which is exactly translation-invariant
  and makes the scale correction structural rather than post-hoc. Commissioned:
  a 7.6% pure scale difference with zero blur reads **-0.002 px**, and a 10%
  error in the assumed scale moves a planted 0.40 px blur by **0.001 px**. So
  registration error cannot wash out a real difference here.

## My instrument, and the plants it had to survive first

`vstat.py` fits `ln P_argmax(k) - ln P_merge(k) = c - 4 pi^2 sigma^2 k^2`. The free
intercept absorbs every gain, exposure and contrast difference, so nothing is
divided by a contrast estimate. Each arm's white-noise floor is subtracted
exactly before the log using its own Immerkaer sigma. Positive means merge finer.

| plant | required | measured |
| --- | --- | --- |
| identity | 0.000 | **+0.0000** |
| pure scale, zero blur | 0.000 | **-0.002** |
| exact Gaussian 0.20 / 0.50 / 1.20 px | recover | 0.231 / 0.615 / 1.259 |
| same, across a scale mismatch | recover | 0.200 / 0.600 / 1.000, error -0.000 |
| noise at the arms' real sigma ratio | 0.000 | +0.038 to +0.090 |
| detection floor | - | **0.02-0.05 px** |

It also has a disclosed weakness: 0.05% salt-and-pepper reads -0.243 px unless
despeckled, and despeckling inflates every reading 15-30%. The no-despeckle
variant is primary here and the despeckled one is a sensitivity column.

## Independent headline

Own 512 px non-overlapping grid, symmetric band-SNR gate, 109 kept tiles.
Equivalent Gaussian blur in merge pixels, positive means merge finer.

| subject | n | median | bootstrap 95% CI | sign p | noise null |
| --- | ---: | ---: | --- | ---: | ---: |
| `bee-3-cpl` | 21 | +0.203 | -0.158 to +0.287 | 0.383 | +0.043 |
| `bee-1-cpl` | 17 | -0.196 | -0.318 to +0.380 | 1.000 | +0.045 |
| `leaf-2-cpl` | 20 | -0.258 | -0.406 to +0.219 | 0.503 | +0.084 |
| `flowers-cpl` | 10 | -0.079 | -0.349 to +0.664 | 1.000 | +0.274 |
| `tweezers-cpl` | 18 | -0.165 | -0.275 to +0.076 | 0.238 | +0.078 |
| `flat-on-ruler-cpl` | 23 | **-0.329** | **-0.362 to -0.176** | **0.011** | -0.022 |
| pooled | 109 | -0.183 | -0.249 to +0.076 | - | - |

**No subject shows a merge detail gain.** The pooled interval excludes a merge
advantage above +0.076 px. For a 1.2x gain to hide under that bound the argmax
arm's own PSF sigma would have to be below 0.14 px, narrower than the pixel
aperture itself (sigma 0.289 px for a one-pixel box). That is impossible, so the
README's 1.2-1.8x is **excluded, not merely unobserved**.

Model-free confirmation, since the Gaussian model turns out not to fit: the
scene-referred power ratio `P_argmax / P_merge`, normalised at period 32 merge px,
stays inside **+/-1.72 dB** at every scale from 32 px down to 4 px on all six
subjects, and is *positive* at the finest scales on five of six. A 1.2x gain
would put a **-1.84 dB** deficit at the half-power frequency and 1.8x a
**-4.2 dB** one. Nothing of that size and sign exists anywhere in the corpus.

## Defects found in BUILD-THESIS's method

**D1. The blur ladder is not a blur ladder below 0.4 px.**
`blureq.py` inverts against `scipy.ndimage.gaussian_filter`, whose kernel radius
is `int(truncate*sigma + 0.5)`. Measured in `plant_audit.py`: at sigma <= 0.12 it
is **bit-for-bit the identity** (max delta 0 DN on a real tile); at sigma 0.20 its
MTF-squared at Nyquist is **0.99997** against a true Gaussian's 0.674. The first
eight rungs of `LADDER` do essentially nothing.

**D2. The reported precision is that defect, not a resolution.**
Driving their own unmodified `invert()` with an infinitesimal target
(`floor_exact.py`): a relative deficit of **1e-6** inverts to **0.155 / 0.184 /
0.166 px** on S1 / S2 / S3. Against an exact Fourier Gaussian the same deficit
returns **0.000 / 0.000 / 0.000**. So "the instrument resolves 0.2 px" is a
floor, every published magnitude is lifted off it, and the subject values
correspond to statistic differences of roughly 1-3%, not half a pixel.

**D3. Therefore the load-bearing equivalence is not a physical coincidence.**
"0.5 px is also the noise gap" is two similarly small relative differences
pushed through the same compressive floor. Re-inverted against an exact
Gaussian the headline shrinks by 25-40% (S1 becomes -0.31 / -0.31 / -0.27 /
+0.37 / -0.36 / -0.37). Signs and orderings survive; magnitudes do not. My own
properly noise-corrected instrument puts the arms' pure noise difference at
**+0.04 to +0.09 px** on five of six subjects, not 0.5 px.

**D4. The scale confound is expressible in their instrument and uncorrected in
the headline.** On a synthetic pure-scale pair with zero blur, their statistics
report argmax/merge ratios of **S1 1.1218, S2 1.0328, S3 1.0507** at s=0.9236 --
a systematic bias favouring argmax. Their `geom_handicap` is the correction, and
`blureq.py` never applies it.

**D5. Their commissioning script, re-run unmodified on their own six subjects,
exits 1 and contradicts their commissioning table.** The REPORT records S2 as
*"passes: <= +0.2% at every level"* and S3 as *"<= +0.1%"*. The script reports:

| trial | S1_norm | S2_f50 | S3_acf |
| --- | --- | --- | --- |
| NULL-GAUSS-1pct | FAIL 6/13 | PASS | PASS |
| NULL-GAUSS-5pct | FAIL 12/13 | FAIL 2/13, worst 1.20x | FAIL 2/13 |
| NULL-GAUSS-15pct | FAIL 12/13, worst 3.95x | FAIL 2/13, worst 4.65x | FAIL 1/13 |
| PLANT-BLUR-0.8 | PASS | **FAIL 2/13, worst 1.6864x** | **FAIL 2/13, worst 1.3032x** |

The last row is the defect that matters. **S2 rises 1.69x on a planted 0.8 px
blur** -- and rising on blur, at 1.39x on the same plant, is precisely what
disqualified `P99/P75`. The killed candidates and the retained ones were not
held to the same criterion over the same tiles.

**D6. Labelling.** The REPORT's per-subject FOV column prints the *logged* scale
(flowers 0.9367) while the measurement used the ECC-fitted one (0.9893). The
measurement is right; the column is not.

## A defect in the README's replacement claim

The gradient-kurtosis "invented structure" table added by `0a29f724` is computed
by `ORCH-drift-check/labelcheck.py` on BUILD-THESIS's crop PNGs, which
`measure.py:231` writes as `(v ** (1/2.2) * 255).astype(uint8)` after clipping at
the 0.5 and 99.7 percentiles, and which `labelcheck.py` then reads through PIL
`convert("L")`, a 0.299/0.587/0.114 channel mix. That is a tone curve, a 256-level
quantiser and a channel mix between the measurement and the scene -- against the
project's own standing rule.

Recomputed camera-linear on the 16-bit TIFFs, green plane, same symmetric
mask-on-the-mean convention, with no interpolator ever touching a pixel value,
and with a control for the fact that the merge arm alone gets a crop-and-resample
round trip that lowers kurtosis by itself:

| subject | README (PNG) | linear | resample-only | **corrected** |
| --- | ---: | ---: | ---: | ---: |
| `bee-3-cpl` | 2.79 | 4.13 | 1.15 | **3.58** |
| `bee-1-cpl` | 1.89 | 4.07 | 1.19 | **3.43** |
| `tweezers-cpl` | 1.17 | 3.79 | 0.90 | **4.20** |
| `flowers-cpl` | 1.98 | 2.16 | 0.91 | **2.36** |
| `leaf-2-cpl` | 1.57 | 1.67 | 0.96 | **1.74** |
| `flat-on-ruler-cpl` | 1.01 | 1.15 | 1.02 | **1.13** |

The finding **survives and strengthens** -- the tone curve was shrinking it. But
the README's *geometry narrative* does not: `tweezers-cpl` is quoted at 1.17x as
a near-planar subject where selection is well posed, and camera-linear it is
**4.20x**, the largest in the set. Only `flat-on-ruler-cpl` remains the exception.
That row needs correcting before the narrative is repeated.

This statistic was commissioned before use (`commission_invent.py`): identity
1.000; adding noise at the arms' own sigma gap moves it by at most 3%, and
planting piecewise-constant plateaus moves it **8.2x to 15.0x**, so it can
express the failure it is meant to catch and is not re-reading the noise gap.

## Noise, measured camera-linear in the flattest fifth of the frame

| estimator | median | range | direction |
| --- | ---: | --- | --- |
| Immerkaer (mine) | 1.455 | 1.346-1.816 | argmax noisier, 6 of 6 |
| Donoho (theirs) | 1.234 | 1.000-1.525 | argmax noisier, 5 of 6 |
| 7x7 residual (ORCH's) | 1.015 | 0.955-1.415 | **no gap** |

The two high-frequency estimators agree; the broad-band one does not, because in
a flat region a 7x7 residual is dominated by residual scene structure rather than
by photon noise. The honest statement is that the gap is at the fine end.

## What I could not test

* **Finding 4 is unverifiable.** `P99/P75` and the LoG zero-crossing density are
  not in `stats.py` -- only described in a docstring. The 5.13x and 12.6x cannot
  be reproduced from the shipped code, and the REPORT does not record which
  inputs `commission.py` was given.
* **A direct PSF measurement failed.** `vpsf.py` returns sigma 3.4-3.8 px on both
  arms, which is physically impossible for a system PSF; the patches are catching
  broad tonal ramps. Its sanity plant produced no rows at all. No number from it
  is used here. The dB exclusion argument above does not depend on it.
* **A realistic speckle plant could not be built.** The arms' outlier
  populations (0.2% to 14.6% beyond 6 sigma) are dominated by real structure.
* **`flat-on-ruler-cpl`'s merge arm carries 14.6% outliers against argmax's 5.3%,
  plus faint vertical seam lines at 1:1.** Unexplained, and possibly the real
  cause of that subject's result.

## The claim that is defensible

> Across six subjects rendered twice from one pinned binary, measured green-plane
> and camera-linear, `--merge pyramid` and `argmax-baseline` resolve the same
> detail: the two arms' power spectra agree to within **+/-1.7 dB** at every scale
> from 32 down to 4 pixels, and the pooled equivalent-blur difference is
> **-0.18 px (95% CI -0.25 to +0.08)** -- if anything favouring selection. A
> 1.2x gain would require a **-1.8 dB** deficit and is excluded. What the merge
> delivers instead is **1.2-1.5x lower noise** at the fine end and **1.7-4.2x
> less invented structure** in out-of-focus ground, against selection's
> **0.33 px** win on the one flat, planar subject where selection is well posed.

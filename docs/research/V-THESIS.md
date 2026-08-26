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

## Which backend actually ran: the banners, verbatim

The flag-inference trap (naming an estimator-only flag without `--merge` selects
the estimator) did **not** catch BUILD-THESIS. Line 1 of every headline subject's
`merge.err`:

| subject | banner line 1 | banner line 2 |
| --- | --- | --- |
| `bee-3-cpl` | `merge backend   : pyramid (default)` | `LAPLACIAN MULTI-BAND MERGE (--merge pyramid; THE DEFAULT PATH)` |
| `bee-1-cpl` | `merge backend   : pyramid (default)` | same |
| `leaf-2-cpl` | `merge backend   : pyramid (default)` | same |
| `flowers-cpl` | `merge backend   : pyramid (default)` | same |
| `tweezers-cpl` | `merge backend   : pyramid (default)` | same |
| `flat-on-ruler-cpl` | `merge backend   : pyramid (default)` | same |

Corroborated three ways. The argv of all six merge arms is bare -- `stack <dir>
--out <file>` -- carrying **none** of the eight trap flags, so there was nothing
to infer from. `bee-3-cpl/merge.err:37` says outright *"Those are the --merge
estimator path's stages; this arm is the merge only."* And `n_eff` appears **0
times** in a pyramid run log against 2 in an estimator one.

**The headline is about the shipping backend.** The README's negative stands as
a statement about `strehl stack`'s default.

### Where the 86.07% came from, and why it does not belong where it sits

It is real and correctly sourced: `EST-flat-on-ruler-cpl/merge.err:71`, a gate
calibration table under the banner `merge backend   : estimator (--merge)` --
`gate 4.00, mean n_eff 1.142, n_eff=1 86.07%`. BUILD-THESIS rendered three
subjects with the estimator on purpose and the REPORT calls it "the estimator
arm".

But it is offered under the heading *"Why the merge does not win where it was
expected to"*, as reason 2, explaining the tie of arms that were the **pyramid**.
The pyramid has no `n_eff` and does not degenerate to selection that way. **The
mechanism is inapplicable to the arms it is used to explain** -- a true fact
about one backend used to explain another backend's result.

**A provenance defect worth fixing:** the `EST-*` directories' sidecars are stale
copies of the pyramid run's (`EST-flat-on-ruler-cpl/merge.provenance.json`
mtime 9:16:25, its `merge.tif` 10:09:38), and their argv shows neither `--merge
estimator` nor the EST output path. Only the banner is truthful. The banner's
`wrote` line confirms each EST run wrote to its own directory, so no pyramid
render was ever clobbered.

## Is the null backend-invariant? Measured, not argued

The estimator renders survive for three subjects, from the same pinned binary,
with identical frame count, reference frame and field-of-view scale to their
pyramid twins -- so P and E sit on one grid and need no registration. Same
sites, same gates, same statistic as the headline above.

Commissioned first in this same-grid configuration: planted 0.00 / 0.20 / 0.50 /
1.00 px read back **+0.000 / +0.198 / +0.497 / +0.998**, and a pure-noise plant
reads **+0.053**.

| subject | pyramid vs argmax | estimator vs argmax | pyramid vs estimator |
| --- | ---: | ---: | ---: |
| `bee-3-cpl` | +0.203 (p 0.38) | +0.180 (p 0.38) | **+0.131** (p 0.007) |
| `leaf-2-cpl` | -0.258 (p 0.50) | -0.189 (p 0.82) | **-0.169** (p 0.012) |
| `flat-on-ruler-cpl` | -0.329 (p 0.011) | -0.158 (p 0.011) | **-0.247** (23/23, p < 0.0001) |
| pooled, n = 64 | -0.180 [-0.315, +0.146] | -0.147 [-0.201, +0.153] | -0.124 [-0.197, -0.089] |

**The tie is backend-invariant.** Neither backend resolves finer than the
selector on any of the three subjects, and the two backends' margins against
argmax agree closely. Relabelling the arms would not have changed the
conclusion, and there is no hidden pyramid win.

The backends do differ from each other, significantly but small and
subject-dependent: the pyramid is finer on `bee-3-cpl` by 0.131 px and softer on
the other two. **On `flat-on-ruler-cpl` the shipping pyramid is the softest of
all three arms**, losing to the estimator on 23 of 23 sites -- which is also the
one subject where selection wins outright, and is worth a look on its own.

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

## The same result with no ladder, no inversion and no Gaussian model

Every defect above lives in `blureq.py`'s ladder and its inversion. So here is
the headline restated in units that need neither. `S2_f50` is a half-energy
frequency in cyc/px -- it *is* "how fine this arm resolves". The README's claim,
put in these units, is that `f50_merge / f50_argmax` should be 1.20 to 1.80.
Computed from BUILD-THESIS's own per-tile numbers (*reproduced*, not mine):

| subject | f50 merge | f50 argmax | raw ratio | geometry-corrected |
| --- | ---: | ---: | ---: | ---: |
| `bee-3-cpl` | 0.0735 | 0.0728 | 1.010 | 1.034 |
| `bee-1-cpl` | 0.0768 | 0.0766 | 1.003 | 0.995 |
| `leaf-2-cpl` | 0.0493 | 0.0496 | 0.993 | 0.970 |
| `flowers-cpl` | 0.0654 | 0.0687 | 0.952 | 0.830 |
| `tweezers-cpl` | 0.0830 | 0.0837 | 0.992 | 0.924 |
| `flat-on-ruler-cpl` | 0.1057 | 0.1174 | 0.900 | 0.918 |

**The merge's half-energy frequency never exceeds the selector's by more than
1.0% raw or 3.4% geometry-corrected. The claim requires 20% to 80%.** Median
0.993 raw, 0.947 corrected. This is the number to publish, because no ladder,
no inversion and no blur model stands between it and the pixels.

It also closes the one gap in the dB argument above: those f50 values, 0.049 to
0.106 cyc/px, all sit inside the 0.031-0.25 cyc/px band my spectral fit covers,
so the -1.84 dB a 1.2x gain would produce would have landed where I was looking.

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

## Addendum 3 -- the alignment confound, measured with the control nobody ran

The orchestrator made the alignment confound the top priority: `argmax-baseline`
does not align, both merge paths do, and if the matched sites are not genuinely
matched across that rescale the comparison measures registration error rather
than detail -- which would *wash out* a real merge advantage and manufacture the
reported null.

### The gap: their whole-chain control switched the confound off

All three of BUILD-THESIS's chain controls carry, in their own run log:

```
field of view scaled to 1.0000 (control: both arms share one grid)
```

`experiments/BUILD-THESIS/build_controls.py` writes that line, and it is true.
The control that proves the chain can recover a planted blur was run with the
arms on ONE grid. The confound that threatens the headline is a 2-7% rescale,
and no control ever exercised it. The plant was never shown able to express the
failure it was meant to catch.

### Building the missing control

`experiments/V-THESIS/build_scaled_ctrl.py` and `build_ruler_ctrl.py` construct
synthetic subjects where the scale AND the blur are both known:

    argmax_syn = warp(gauss_exact(merge, sigma), scale s about the centre)

Blur before the resample, so `sigma` is a scene blur in merge pixels. Two
geometries: leaf-2's 0.9342 (6.6% -- the size of the miss the orchestrator
flagged on `EST-leaf-2-cpl`) and flat-on-ruler's 0.9707 (2.9%).

`python experiments/BUILD-THESIS/measure.py VCTRL-...` then
`python experiments/BUILD-THESIS/blureq.py ...` -- their code, unmodified.
Their `measure-mean.json` was copied to `$env:TEMP` first and restored after.

### What their chain does when the truth is exactly zero

| control | truth | S1_norm | S2_f50 | S3_acf | signs |
|---|---:|---:|---:|---:|---|
| their CTRL-identity (one grid) | 0.000 | +0.000 | +0.000 | +0.000 | agree |
| their CTRL-blur0.8 (one grid) | 0.800 | +0.800 | +0.800 | +0.800 | agree |
| their CTRL-blur1.5 (one grid) | 1.500 | +1.498 | +1.500 | +1.500 | agree |
| V VCTRL-s-blur0.0 (6.6% rescale) | 0.000 | **+0.310** | **-0.460** | **-0.434** | DISAGREE |
| V VCTRL-s-blur0.4 (6.6% rescale) | 0.400 | +0.483 | **-0.325** | +0.322 | DISAGREE |
| V VCTRL-s-blur0.8 (6.6% rescale) | 0.800 | +0.745 | +0.599 | +0.622 | agree |

On one grid the chain is flawless. Across a realistic rescale, with **no blur
planted at all**, it reports 0.31-0.46 px of equivalent blur and its three
statistics disagree in sign -- the same size and the same signature as the
entire published headline. And a genuine **+0.4 px merge advantage** is reported
by `S2_f50` as a **0.325 px argmax advantage**: the sign is inverted, on 4 of 6
tiles.

Their published six subjects also disagree in sign on 5 of 6. That disagreement
was visible in their own output and is the tell.

The decisive comparison: their real-subject readings span S1 [-0.475,+0.491],
S2 [-0.438,+0.257], S3 [-2.062,+0.470]. The **0.0 px** control lands inside that
range on 2 of 3 statistics; the **+0.4 px** control lands inside on **all
three**. Their data cannot discriminate "no difference" from "a real 0.4 px
merge advantage".

### My instrument, held to the same test

| control | truth | V reads | error |
|---|---:|---:|---:|
| VCTRL-r-blur0.0 (2.9% rescale) | +0.000 | **-0.007** | -0.007 |
| VCTRL-r-blur0.4 (2.9% rescale) | +0.400 | **+0.400** | -0.000 |
| VCTRL-s-blur0.0 (6.6% rescale) | +0.000 | **+0.054** | +0.054 |
| VCTRL-s-blur0.4 (6.6% rescale) | +0.400 | **+0.404** | +0.004 |
| VCTRL-s-blur0.8 (6.6% rescale) | +0.800 | **+0.802** | +0.002 |

A real merge advantage planted across the exact rescale in question is
recovered to within 0.004 px. **The null I report is not a washout.**

Deliberately corrupting the scale (`floor_budget.py`) confirms it: a full 6.6%
miss -- twice the largest plausible error, since my anchor fit and warp-correlate
sweep agree with their ECC to within 0.5-2% on all six -- moves my reading by at
most 0.15 px and never flips a sign.

| subject | fitted | -6.6% | -3.3% | correct | +3.3% | +6.6% |
|---|---:|---:|---:|---:|---:|---:|
| bee-3-cpl | 0.93554 | +0.331 | +0.294 | +0.255 | +0.203 | +0.102 |
| leaf-2-cpl | 0.95399 | -0.248 | -0.230 | -0.218 | -0.174 | -0.079 |
| flat-on-ruler-cpl | 0.97073 | -0.300 | -0.370 | -0.385 | -0.397 | -0.441 |

Their ECC also recovered the planted scale exactly on all five controls
(0.9342 and 0.9707, matching truth). It did not latch wrong on the headline arms.

## Addendum 4 -- the "0.5 px is also the noise gap" equivalence is incomplete

Their own `limits.json` noise-null table, n=12 rows:

| statistic | median abs px | max abs px |
|---|---:|---:|
| S1_norm | 0.367 | 0.492 |
| S2_f50 | 0.255 | 1.503 |
| S3_acf | 0.241 | 1.320 |
| all | **0.261** | **1.503** |

"0.5 px" is roughly the *maximum* of S1, not the typical value (0.261). But the
substantive point is that the floor has at least three terms and their yardstick
counted one:

| term | size | counted? |
|---|---|---|
| noise gap | 0.261 px median | yes |
| scipy kernel truncation | 0.155-0.184 px | no -- V `floor_exact.py` |
| **arm rescale** | **0.310-0.460 px** | **no -- V `VCTRL-*-blur0.0`** |

The largest single measured term is the one their commissioning switched off.
The sentence "0.5 px is also what the instrument reports for the noise gap
alone" is therefore not a coincidence and not a noise floor; it is a floor built
mostly of registration and truncation, with noise second.

## Addendum 5 -- `flat-on-ruler-cpl` (finding #2) is right for the wrong reason

Their published row: **-0.475 / -0.438 / -0.377**, offered as "selection wins
outright, ~0.4 px, all three statistics agreeing".

Their chain on that subject's OWN geometry with **zero blur planted**
(`VCTRL-r-blur0.0`): **-0.320 / -0.361 / -0.354**, all six tiles each, all three
agreeing.

The tri-statistic agreement that was offered as corroboration is what the chain
does when the answer is zero. It is a shared systematic, not independent
confirmation. Bias-subtracting leaves -0.155 / -0.077 / -0.023: their own data,
corrected, says the subject is a tie.

The direction nevertheless survives on independent evidence. My instrument reads
**-0.007 px** on that same zero-truth geometry and **-0.329 px [-0.362,-0.176],
sign p=0.011** on the real subject. Selection *is* finer there. Their number,
their magnitude and their stated grounds are not evidence for it.

## Addendum 6 -- the invented-structure statistic fails both commissioning tests

First, a retraction of my own: `experiments/V-THESIS/kurt_attack.py` derived the
flat mask separately on each arm, so it compared different sets of pixels. Its
numbers are withdrawn. `labelcheck.py:101` uses one mask from the mean of both
panels; `kurt_attack2.py` and `kurt_levels.py` follow that rule.

**K5' blur plant, mask fixed on the mean of both panels:**

| planted blur | k(sharp) | k(blurred) | ratio |
|---:|---:|---:|---:|
| 0.0 | 3.180 | 3.180 | 1.000x |
| 0.5 | 3.180 | 4.109 | **1.292x** |
| 1.0 | 3.001 | 5.084 | **1.694x** |
| 4.0 | 3.184 | 7.365 | **2.313x** |

**Gradient kurtosis in flat regions RISES on blur.** BUILD-THESIS disqualified
two of its own candidates for rising 1.39x, 5.1x and 12.6x on a blur plant. By
the project's own standard this statistic fails the same test.

**K2' noise null:** 1.302x at 5% added noise, 1.198x at 15%, 0.862x at 30% --
non-monotone, and up to 1.30x on noise alone.

The confounds are the same size as the effect (1.09-2.26x observed).

**K6' mask-fraction sweep, camera-linear, geometry-matched:**

| subject | README | 0.10 | 0.20 | 0.35 | 0.50 | 0.70 |
|---|---:|---:|---:|---:|---:|---:|
| bee-3-cpl | 2.79 | **0.90** | 1.73 | 2.26 | 1.93 | 1.71 |
| bee-1-cpl | 1.89 | 1.65 | 2.34 | 1.82 | 1.34 | 1.04 |
| leaf-2-cpl | 1.57 | 1.30 | 1.43 | 1.58 | 1.65 | 0.74 |
| flowers-cpl | 1.98 | 0.97 | 1.24 | 1.65 | 1.93 | 2.44 |
| tweezers-cpl | 1.17 | 0.67 | 1.03 | **1.86** | 0.99 | 1.06 |
| flat-on-ruler-cpl | 1.01 | 1.11 | 1.12 | 1.09 | 1.07 | 0.98 |

The per-subject **ordering is not robust**. `frac` was never varied and is
load-bearing: at 0.10 the README's top subject reads 0.90, below unity. Three
implementations of "the same" statistic give bee-3 = 2.79 (README, via 8-bit
gamma PNGs), 3.58 (my `vinvent2.py`) and 2.26 (here). The magnitude is not
stable enough to quote per subject.

What IS robust: absolute levels against the pure-noise (Rayleigh) reference of
3.245.

| subject | k(merge) | k(argmax) | ratio |
|---|---:|---:|---:|
| bee-3-cpl | 5.947 | 13.420 | 2.26 |
| bee-1-cpl | 9.325 | 16.926 | 1.82 |
| leaf-2-cpl | 3.601 | 5.683 | 1.58 |
| flowers-cpl | 4.605 | 7.582 | 1.65 |
| tweezers-cpl | 15.627 | 29.136 | 1.86 |
| flat-on-ruler-cpl | 5.338 | 5.811 | 1.09 |

Both arms sit far above pure noise, so this is structure and not the noise gap;
argmax carries the heavier tail on 6 of 6 at frac 0.35 and on 5-6 of 6 across
frac 0.20-0.50. `flat-on-ruler-cpl` is the exception at every fraction tested
and in every implementation.

Two caveats on that exception. `tweezers-cpl` moves 1.17 -> 1.86 camera-linear,
which breaks the README's "near-planar target, so selection is well-posed"
narrative -- tweezers has the *highest* absolute gradient kurtosis of any
subject. And on `flat-on-ruler-cpl` the merge is 0.33 px softer (measured
above); K5' says 0.5 px of blur inflates kurtosis about 1.29x, which is enough
to suppress a ratio of ~1.3 to the observed 1.09. The exception may be the
softness confound rather than an absence of invented structure.

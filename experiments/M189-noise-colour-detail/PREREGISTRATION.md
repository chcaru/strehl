# M189 PTC-referenced noise-colour detail — positive-control preregistration

Status: **FROZEN BEFORE FIRST EXECUTION**

Date: 2026-09-05

## 1. Question

The decisive question is whether

\[
Q(f)=\frac{C(f)}{\max(1,G(f))}
\]

responds to a genuine pre-noise PSF narrowing while retaining the already
derived directions for post-noise blur and unsharp masking.

This is a synthetic commissioning only. It opens no capture and does not claim
transfer to a real optical pair.

## 2. Candidate-visible observation

The candidate receives:

- 16 independent repeat pairs of one completed monochrome observation;
- the calibrated PTC slope `g = 0.221113 DN/e-`;
- independently supplied read noise `RN = 1.2392 e-`; and
- no arm name, optical sigma, noiseless scene, filter identity, or expected
  direction.

The candidate implementation is `metric.py`. It accepts only the repeat arrays
and the two noise constants.

## 3. Frozen fixture

- output side: `256` pixels;
- oversampling: `4`, hence a `1024 x 1024` latent field;
- latent seed: `189001`;
- latent construction: NumPy `default_rng().standard_normal`, Gaussian-filtered
  at sigma `1.0` high-resolution pixel with periodic boundary, normalized to
  zero mean/unit population standard deviation, then mapped to
  `8000 + 1200*x` DN;
- optical render: periodic Gaussian filter at
  `4 * sigma_optical` high-resolution pixels, `truncate=6`, then area-average
  each non-overlapping `4 x 4` block;
- base optical sigma: `1.00` output pixel;
- genuine improvement sigma: `0.55` output pixel;
- genuine degradation sigma: `1.65` output pixels;
- temporal noise:
  `variance_DN2 = g * mean_DN + (g * RN_e)^2`;
- repeat streams: seeds `189003` and `189004`, 16 independent standard-normal
  fields each, reused across the three optical arms but independent between the
  two members of every pair;
- post-render blur: periodic Gaussian sigma `1.00` output pixel;
- post-render USM:
  `x + 0.75 * (x - Gaussian(x, 1.00))`, unclipped;
- adaptive re-noise attack: apply the same USM to the noiseless base mean, then
  add fresh PTC noise from seeds `189005` and `189006`;
- flat null: constant `8000 DN` plus PTC noise from the base repeat streams;
- no clipping, tone curve, demosaic, resampling, PRNU, or fixed-pattern term.

The optical constants deliberately reuse the independently frozen M167
base/improvement/degradation sigmas. The noise law changes from M167's constant
Gaussian noise to the signal-dependent PTC law under test.

## 4. Frozen metric

All FFTs are unitary 2D FFTs. Frequencies are radial output cycles/pixel. The
licensed band is

```text
0.12 <= radius < 0.30 cyc/output-pixel
```

split into 36 equal radial bins.

For each Fourier cell, averaged over 16 repeat pairs,

\[
C=\operatorname{Re}E[X_A X_B^*],
\qquad
N=\tfrac12E|X_A-X_B|^2.
\]

The external white-noise reference is

\[
N_{\rm ref}
=g\,\operatorname{mean}((A+B)/2)+(gRN_e)^2.
\]

For each radial bin,

\[
G=N/N_{\rm ref},\qquad
Q_{\rm bin}=\frac{\sum C}{\max(1,G)}.
\]

The reported score is the sum of `Q_bin` divided by the number of licensed
Fourier cells. Cross-power is signed and is not clipped at zero.

## 5. Frozen arms and predicates

All ratios use the base score as denominator.

| ID | arm | frozen predicate |
|---|---|---|
| P0 | identity | absolute ratio error from `1` <= `1e-12` |
| P1 | genuine optical improvement | ratio `> 1.05` |
| P2 | genuine optical degradation | ratio `< 0.95` |
| P3 | completed-image Gaussian blur | ratio `< 0.95` |
| P4 | completed-image USM | `0.98 <= ratio <= 1.01` |
| P5 | USM intervention power | uncorrected coherent-power ratio `> 1.05` and weighted noise gain `> 1.05` |
| P6 | optical-noise null | weighted noise gain for base, improvement, and optical degradation is in `[0.97, 1.03]` |
| P7 | adaptive re-noise attack | score ratio `> 1.05` while weighted noise gain is in `[0.97, 1.03]` |
| P8 | flat specificity | flat score is strictly below base score |

P7 is expected to pass as an **attack demonstration**, not as candidate
acceptance. If it does not, the prior M189 no-go mechanism is not established
by this fixture.

The positive-control candidate is commissioned for the ordinary three
directions only if P0-P6 and P8 pass. P7 decides whether the declared
denoise-sharpen-re-noise limitation remains live.

## 6. Interpretation frozen before results

- If P1 fails, the lane verdict is `NO-GO — BLIND TO REAL IMPROVEMENT`.
- If P1-P6 and P8 pass, `Q` is a viable common-linear-filter-safe candidate on
  this synthetic raw-plane fixture.
- P7 passing does not erase that result. It proves the candidate requires a
  declared renderer threat model or an additional authenticated ancestry
  witness.
- No result from this fixture admits M1 by itself. PRNU/fixed-pattern
  specificity, tone, real-pair transfer, and the complete M167 battery remain
  separate admission work.


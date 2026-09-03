# M-PHASE0-SPLIT preregistration

Date: 2026-08-25

## Question and prior evidence

This lane asks whether an off-by-default, same-invocation odd/even split of the
default pyramid merge can produce trustworthy diagnostic half renders, a
half-difference image, and a Fourier ring correlation (FRC) curve without
changing the ordinary render.

D8 in `docs/proposals/2026-08-sota-path.md` proposes three uses: self-tuning,
per-tile FRC acuity, and a null image, with
`P_sig = Re(A conj(B))` and `P_noise = P(A-B)/2`.  The corpus does **not**
license all three.  M115 established the algebra and useful product shapes, but
its replacement flat null failed (0.2984/0.4034 against 0.25), its identical
sharpening result is algebraic for a common linear transfer function, and its
reported 0.4961 FRC crossing was later withdrawn in `SYNTHESIS.md`: 9/12
crossings were last-bin fallbacks and 32 ring/threshold settings repaired none.
`V-SOFTCHECK-coherence.md` also shows that `(A+B)/2` can score perfect
coherence and zero null while losing 29.6% of delivered band power.
`V-SOFTCHECK-selection-vs-alignment.md` attributes 87.3% of one observed
incoherence to planted residual half-warp.  A same-invocation split removes
that separate-alignment confound, but not common sensor structure, odd/even
focus-step mismatch, or gameability.

The mandatory `prior_art.py --commission` check passed before this document was
written.  Its SPLIT search surfaced M92, M97, M103, M127, V-THESIS, V-DCNULL,
V-SOFTCHECK-coherence, and V-SOFTCHECK-selection-vs-alignment.

## Frozen implementation and statistic

The explicit flag will be `--split-out DIR`; absence is off.  Only the pyramid
backend will accept it.  In the existing decode/register fold, global even and
odd input indices will feed two additional one-plane `BandMerge` accumulators.
Each half therefore derives its own band weights from the same registered green
luma frames.  The ordinary four-plane accumulator, its worker count, reduction
order, and output path will not change.

Products use the unquantised `f32` half renders.  Analysis divides the native
quad-pixel grid into centred, non-overlapping 256 by 256 tiles.  Each tile has
its mean removed and a separable Hann window applied before a 2-D FFT.  For
integer-radius ring `r`,

`FRC(r) = sum Re(A_k conj(B_k)) / sqrt(sum |A_k|^2 sum |B_k|^2)`.

DC and rings with fewer than 16 coefficients are excluded.  A measured acuity
is the linearly interpolated first downward crossing of `1/7` that is followed
by three consecutive below-threshold rings.  A curve with no such crossing is
reported as `CENSORED_ABOVE`; one already below at the first eligible ring is
`CENSORED_BELOW`.  A censored endpoint is never converted to the final bin.
Frequency is cycles per native quad pixel.  The null TIFF encodes signed
`A-B` in camera-linear DN with zero at 32768.

The real-stack headline is the aggregate-tile crossing on `109MSDCF` (22
frames), with a deterministic 1,000-resample tile bootstrap.  A numeric 95%
percentile interval is allowed only if at least 90% of resamples have a measured
crossing.  Otherwise the result is a bound plus measured/above/below censor
fractions.  A second frame-parity assignment (indices shifted by one) is the
parity ladder; a changed censor class or non-overlapping measured 95% intervals
is `NOT ROBUST`.

## Commissioning and planted failures

All acceptance decisions are fixed before controls run.

1. **External fixed-spectrum predicate.**  A literal impulse, constant field,
   and checkerboard have hand-derived non-zero DFT bins.  The Rust FFT must
   match those bins to `1e-4` relative error.  Input and answers are not made by
   the estimator.
2. **Null.**  Sixteen pairs of independently seeded white-noise tiles must have
   aggregate ring-weighted mean absolute FRC below 0.05 and no band
   (`0.02-0.15`, `0.15-0.30`, `0.30-0.48`) with `|mean FRC| >= 0.08`.
   Plant `N1` reuses one noise half as the other; the control must go RED.
3. **Positive.**  A fixed multiscale signal plus independent noise must read
   mean FRC at least 0.90 in `0.02-0.10` cycles/px, at most 0.60 in
   `0.35-0.48`, and fall by at least 0.25.  With noise removed, every powered
   ring must read `1.0000 +/- 1e-4`.  Plant `P1` conjugates with the wrong sign;
   the fixed low-frequency predicate must go RED.
4. **Sharpening.**  Identical 3 by 3 unsharp masking (amount 1.5) must increase
   a naive gradient-acuity score by at least 25% while moving the FRC crossing
   by no more than one ring and any powered-ring FRC by at most `5e-4`.
   Plant `S1` reports the naive acuity as resolution; it must go RED.
5. **Censoring.**  A fully correlated pair with power through the last ring
   must return `CENSORED_ABOVE`.  Plant `C1` substitutes the last-bin frequency;
   it must go RED.
6. **Common-mode adversary.**  Adding the same fixed pattern to independent
   noise is expected to violate the null bar.  This is a required demonstration
   of the metric's specificity limit, not evidence of scene detail.

The commissioning harness passes only if every clean control is GREEN and all
four named plants are observed RED.  A Rust/Python comparison uses an
independent direct DFT on fixed small arrays; agreement is required before real
pixels are interpreted.

## Decision bar and declared bias

**Bias direction declared first:** pressure to end a 63-commit no-Rust streak
biases this lane toward shipping and toward calling correlated sensor structure
resolved scene detail.  The historical last-bin fallback biases toward a clean
numeric resolution.  The counter-bias is to overreact to that history and
discard useful diagnostic products.  The rules above therefore force explicit
censoring and separate product utility from acuity validity.

* **SHIP DIAGNOSTIC ONLY:** controls pass and ordinary output is byte-identical,
  but real acuity is censored/parity-sensitive or common-mode specificity is
  unresolved.  Ship halves/null/FRC labelled experimental; no auto-tuning.
* **SHIP ACUITY:** controls pass, at least 90% of bootstrap crossings are
  measured, the parity ladder is robust, and an independent flat/common-mode
  capture stays inside the null bar.
* **STOP/REMOVE:** any clean control fails, any plant remains GREEN, or ordinary
  output bytes change when diagnostics are enabled.

Confounds reported regardless of outcome: shared sensor/FPN structure,
quantisation (products must precede it), half-density focus sampling, unequal
half counts/refusals, registration residuals shared by both halves, window and
ring choices, tile content, and threshold censoring.  This lane will not wire
automatic tuning: the corpus's prior split objective ran to a boundary and rose
4.14 times on a flat ROI.

## Commissioning amendment, before real pixels

The first clean sharpening control exposed a bad **control specification**, not
a favourable result: identical spatial unsharp masking changed the largest
individual finite-window ring by 0.010859, while the registered resolution
crossing moved from 0.222192 to 0.220543 cycles/pixel (a **decrease** of
0.001650, versus one ring = 0.015625) and naive gradient acuity rose 1.838176x.
The original `5e-4` all-ring clause incorrectly demanded the infinite/periodic
algebra after mean removal, finite tiling and Hann windowing, which do not
commute with a spatial filter.  It would reject the metric when sharpening made
its headline estimate slightly worse.

Before any real capture was opened, that non-load-bearing clause is therefore
retired.  The frozen sharpening gate is now the question the user actually
posed: the reported crossing must **not increase**, must stay within one ring,
and the naive acuity positive control must rise at least 25%.  `S1` still
substitutes naive acuity for resolution and must go RED.  The maximum ring move
remains reported as a sensitivity, not scored as a pass/fail gate.  This
amendment is additive so the failed original specification remains auditable.

## Post-measurement commissioning correction

Audit after the first real run found that the registered null gates pooled broad
bands and therefore did not literally test the user's phrase “at all
frequencies.”  The real number is treated as provisional until a stricter
synthetic check passes.  Before running that new check, its bar is fixed here:
at every individually usable ring, treat the 16 independent tiles as
replicates, compute the mean tile FRC divided by its sample SE, and require the
maximum absolute Student statistic to be below **4.0**.  With roughly 30 rings
and 15 degrees of freedom this is an approximately 5%-familywise two-sided
screen; it tests consistency with zero rather than demanding an impossible
literal zero from finite noise.  `N1` remains the positive failure.  If this
new gate fails, the real result is discarded rather than the bar being moved.

## Independent-verification correction, after the initial report

Independent verification found two unregistered classifier edge defects.  The
implementation had discarded physical ring indices before looking for three
“consecutive” below-threshold rings, so unusable rings could be silently
compressed out.  It also labelled a curve whose final one or two rings dropped
below threshold `CENSORED_ABOVE`, even though neither a stable crossing nor a
valid lower bound had been established.  The affected result was treated as
provisional while both Rust and the CSV re-checker were corrected.

The correction preserves ring indices and requires physical adjacency across
the bracketing ring and all three confirming rings.  If a curve ends below the
threshold without three such rings, or if the transition is interrupted by an
unusable ring, it returns `INSUFFICIENT`.  Post-hoc regression plants `C2`
(compress the missing ring away) and `C3` (restore the false terminal
`CENSORED_ABOVE`) must each go RED; they are regression evidence, not falsely
presented as preregistered controls.  The aggregate real result is retained
only if its decisive rings are physically contiguous and usable and independent
reclassification leaves its outcome and value unchanged.

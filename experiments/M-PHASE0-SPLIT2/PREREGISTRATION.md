# M-PHASE0-SPLIT2 preregistration

**Written before this lane decoded or measured any real pixel.** A planning pass
had already reported a preliminary 576-file/two-pass structure, so file count
and ISO grouping are not blinded outcomes. No FRC, null, stability, or tuner
reading from this capture had been seen.

## Question and bias

This is not a reopening of D8. It asks whether *separate repeated exposures* of
one fixed subject provide sufficiently independent observations for a
fake-resistant repeat-pair resolution metric.

My desired result is **SALVAGE / BUILD**: it would give the project an honest
competitive-resolution instrument and, unusually for this programme, a direct
Rust payoff. That biases me to mistake shared fixed-pattern/quantisation
structure for scene signal and to excuse illumination changes. The opposing
bias is that the second light pass can depress correlation even when optical
detail is real.

The most likely reason this preregistration is wrong is structural: separate
exposures have independent shot/read noise, but a fixed scene on the same
sensor pixels still shares PRNU, DSNU, dust, optics, and deterministic RAW
quantisation. A difference null cancels those terms and therefore cannot prove
they do not inflate the scene-pair FRC.

## Eligibility gate: establish what the capture is

`validate_capture.py` must be commissioned before reading real metadata. Its
fixed predicates are:

* exactly the contiguous external filename sequence
  `DSC00296.ARW` through `DSC00871.ARW` (576 files);
* 18 contiguous ISO runs of 32 frames, two runs at each of
  `{50,64,80,100,200,320,400,500,640}`, with all nine ISOs in each pass;
* one camera; 14 bits; 200 mm; f/5.6; 1.6 s; fixed manual-focus mode;
* strictly increasing timestamps and no within-run gap >=5 s;
* within-run EXIF brightness range <0.5 EV and file-size CV <5%;
* the two passes differ by >0.5 EV at every ISO;
* any numeric focus-position tag, if present, is invariant.

Plants alter file count, exposure, focus mode, and light grouping; all four
must go RED. Metadata cannot prove the focus ring or subject did not move. A
pixel gate therefore uses the first pass at ISO 50: every unregistered
evaluation crop must have integer phase-correlation shift zero relative to
frame 0, and every frame's log high/mid spectral-power ratio must lie within
0.10 of the group median. A one-quad-pixel roll and an exact sigma=1 Fourier
blur are the RED plants for those two checks. Failure means **NOT GENUINE /
STOP**, with no FRC measurement.

## Pixels, partitions, and fixed statistics

Decode Sony RAWs read-only with `rawpy`, verify the Bayer pattern, subtract the
two green black levels, and average the two green CFA sites into one quad-green
sample. Use a fixed centred 1536x1536-quad-pixel evaluation crop, divided into
36 non-overlapping 256x256 tiles. The disjoint centred-left 256x1536 strip is
used only to estimate photometric scale; it never contributes Fourier samples.
No registration or resampling is allowed in the primary analysis.

For image pair `A,B`, each tile is mean-subtracted and multiplied by a separable
Hann window. Aggregate integer Fourier rings:

```
FRC = sum Re(A conj(B)) / sqrt(sum |A|^2 sum |B|^2)
P_sig = mean Re(A conj(B))
P_noise = 0.5 mean |A-B|^2
SNR = P_sig / P_noise
```

The resolution statistic is the first interpolated 1/7 FRC crossing followed
by three physically adjacent below-threshold rings (minimum 16 coefficients).
Terminal, gapped, and incomplete transitions are not measurements. Frequency
is cycles/quad-pixel.

Within each 32-frame run, the scene pair is the mean of even frames versus the
mean of odd frames. The primary noise null uses disjoint ABBA contrasts: for
each consecutive four-frame block weights are `(+1,-1,-1,+1)`, which cancel a
constant and linear light drift; alternating blocks form `D1` and `D2`.
This uses every exposure once and keeps the two residuals disjoint.

The historic M115 bar is kept in its original units and band:
**maximum ring `P_sig/P_noise <0.25` over 0.10 <= f <0.2762**. It is not an FRC
bar. The separate commissioned FRC-null bars are mean absolute ring FRC <0.05,
each pooled band magnitude <0.08 for `[.02,.15)`, `[.15,.30)`, `[.30,.48)`,
and maximum per-ring absolute tile t <4.

The deciding null number is the pooled 18-run ABBA maximum mid-band SNR, with a
fixed-seed 1,000-resample 95% tile-bootstrap interval. It passes only if the
point estimate **and upper interval endpoint** are <0.25. Also report every
ISO/light run; a ladder reversal makes the result NOT ROBUST.

## Commissioning before real FRC

The copied algorithm is not trusted merely because D8 was commissioned. The
new Python implementation must pass:

1. fixed 8x8 arrays against a separately written direct DFT;
2. independent-noise null, including all three null bars;
3. same smooth signal plus independent noise: low-band FRC >=0.90,
   high-band <=0.60, low-high >=0.25;
4. identity/full-effect ceiling: every usable ring is 1 within `1e-12`;
5. identical unsharp mask: naive gradient acuity rises >=1.25x, while the
   crossing cannot improve and moves by at most one 256-tile ring;
6. common-mode adversary: low-band FRC must violate 0.08 (the closed D8
   implementation read 0.972099);
7. classifier gap, short-tail, and endpoint controls.

Every targeted plant must make the harness exit nonzero.

The missing data-dependent-tuner control is held out. A clean nonlinear
spectral-shrinkage tuner chooses its parameter on synthetic training repeats
`A,B`, then applies that fixed parameter independently to evaluation repeats
`C,D`. The plant instead tunes a shared-data leakage strength on `C,D` and can
select their common mean, whose estimator ceiling is FRC=1. A fixed external
lineage predicate perturbs only `D` and requires the emitted `C` product to be
bit-identical. The planted evaluator must go RED, while recording how close its
fake resolution gets to 1. The tuner never sees the clean latent or the
one-sided perturbation, preventing generator/checker cancellation.

## Illumination and uncertainty

Primary comparisons are only within a 32-frame fixed-light run. ABBA removes
linear within-run drift without estimating a scale from measured pixels. As a
sensitivity analysis, per-frame scalar normalization is estimated from the
disjoint normalization strip and applied to the evaluation crop. If raw and
normalized null verdicts differ, file **NOT ROBUST / NO BUILD**.

For each ISO, compare the two pass means only after a scalar fit on the
normalization strip. This cross-light result is not a null and cannot overturn
the primary result: changed shadows/illumination are real latent changes that
bias FRC and its crossing downward. Report the crossing shift and any
unmeasured/censored cases explicitly.

Scene-pair crossing uncertainty is a 1,000-resample spatial-tile bootstrap.
It describes variation across the fixed crop, not repeatability over subjects.

## Committed verdict

Recommend a Rust build only if eligibility passes, every commissioning plant
goes RED, every null bar passes with the bootstrap rule, the real scene has a
measured (not fallback) crossing in both light passes, identical sharpening
does not improve it, the held-out tuner plant is rejected, and the ISO/light
ladders do not reverse the decision. Even then, the recommendation must say
that ordinary user stacks lack 32 true repeats and that this capture cannot
separate stable sensor structure from a stable scene. Any failed condition is
**NO BUILD**; no Rust will be written in this lane.

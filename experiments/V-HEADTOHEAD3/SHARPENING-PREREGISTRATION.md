# V-HEADTOHEAD3 sharpening-discriminator preregistration

Frozen 2026-09-02 after the tone-neutral baseline was committed, but before
reading any new source-transfer, input-fixed flat, rank-envelope, or
self-sharpening outcome.  The already known facts are:

* the 113 sharpening-0 and sharpening-40 PMax files use the same 63
  `OriginalDocumentID` values;
* their Lightroom source settings are respectively
  `Sharpness/ColorNoiseReduction/Contrast2012 = 0/0/+100` and
  `40/25/+100`;
* the old six-band-normalised ordinal statistic reads strehl/PMax
  `0.8721 [0.7817,0.9745]` versus `0.3992 [0.3381,0.4720]` at
  0.20--0.25 cyc/px;
* the prior corpus reports a separate marker experiment in which an
  Lightroom-fed stack had 2.4x the top-gradient statistic on flat foam.

Those are priors, not controls for this experiment.  No number below may be
tuned to make them recur.

The read-only scorecard is
`docs/proposals/2026-09-sota-scorecard.md`, SHA-256
`11A754A61837EBE70CD1D59B9AD224D9240CFD105747B1CC28FCE78BEFC03BAA`.
Its common-linear-input, independent-repeat M1, exact M4, and exact M8
contracts were not used to create these retrospective outputs.  This
experiment can convict a spatial-development artifact, but cannot award a
scorecard resolution win.

## Question, bias, and licensed scope

Does the Sharpness-40/colour-NR-25 development rung's advantage over the
Sharpness-0 rung at **0.20--0.25 cyc/native px** behave like a spatial
sharpening transfer that also raises no-signal structure, or like additional
scene-supported resolution that such a transfer cannot reproduce?

My favoured direction is **ARTIFACT**.  That direction would remove the most
serious apparent competitive deficit, and the prior flat-foam result makes it
expected.  Therefore every ARTIFACT predicate must be satisfied jointly; a
clean or failed proxy cannot be interpreted as proof of real resolution.

The previous `A_k` value at 0.20--0.25 was normalised by six bands, three of
which extend above 0.25.  It is historical, not licensed under scorecard v1.1.
This follow-up uses a new statistic whose numerator and normalisation consume
no measured band above 0.25.  Any inspection above 0.25 is represented only by
the literal label `UNLICENSED_GT_0.25`; no number, ordering, or verdict may be
printed there.

## Frozen data and source-only split

The two source directories are:

* `D:\edited\macro\test2\20260507-DSC00001.tif` through `00063.tif`
  (Sharpness 0);
* `D:\edited\macro\test\20260507-DSC00001.tif` through `00063.tif`
  (Sharpness 40).

All source work uses the green plane.  Source files must match one-to-one,
have shape 4672x7008x3, and have less than 1% of a candidate crop on exact
container rails.

Four Sharpness-0 frames, identities 4/20/36/52, select sites and are used for
nothing else.  Candidate 512x512 crops use the existing 512-pixel grid.  For
each crop and selection frame, replace values by average ranks, Gaussian-blur
with sigma 1, and compute the p95 Euclidean finite-difference magnitude.
The site score is the maximum of those four p95 values.  Within each
checkerboard parity `(y/512 + x/512) mod 2`, freeze the twelve lowest-score
sites as `flat` and twelve highest-score sites as `detail`.  This gives
24 flat and 24 detail sites, spatially balanced and selected without opening
Sharpness-40 sources, either PMax output, or strehl.

The transfer-model training identities are 1/9/17/25/33/41/49/57 on parity-0
sites.  Holdout identities are 6/14/22/30/38/46/54/62 on parity-1 sites.
The fit may not read a PMax or strehl pixel.  A checker recomputes the
source-only site set and model independently before outcomes.

## Strictly licensed band statistic

For an `H x W` crop with `N=HW`, let `q` be its centred average-rank field,
`w` the separable Hann window, and `F` the unnormalised 2-D FFT of `w*q`.
Define

```text
Q25 = sum( |F_k|^2 : 0.20 <= |f_k| < 0.25 )
      / ( N * sum(w^2) * mean(q^2) ).
```

Thus `Q25` is band energy per fixed rank variance, not a share whose
denominator imports an unlicensed band.  It is exactly invariant to any
strictly increasing point map.  Measurement crops remain native; interpolation
is permitted only for geometry.  Comparator band edges are scaled into their
native grids as in the baseline.

Every interval below is a 10,000-draw paired site bootstrap, PCG64 seed
`20260904`.  Frame effects are first reduced to one median per site so frames
are not treated as independent physical sites.

## Flat-power discriminator

On the frozen flat sites define:

```text
F_source = exp(mean_site median_holdout_frame log(Q40 / Q0))
F_output = exp(mean_site log(Q_PMax40 / Q_PMax0)).
```

These are `INPUT_FIXED_FLAT_PLACEBO_NOT_M4`: the sites lack the scorecard's
independent temporal-noise qualification and 1,000 convex-blend reference.
A lower 95% bound above **1.25** is nevertheless strong evidence that the
development rung raises licensed-band structure where no output was consulted
to select the site.  A complete interval inside `[0.95,1.05]` is a null but
only weak evidence.

## Outcome-independent sharpening transfer

Fit a two-parameter, zero-phase Gaussian unsharp mask using only training
source pairs:

```text
USM(x; sigma,a) = x + a * (x - Gaussian_sigma(x))
H(f) = 1 + a * (1 - exp(-2*pi^2*sigma^2*f^2)).
```

Search `sigma=0.30..2.50` and `a=0.00..3.00`, both in steps of 0.05.
The loss is median absolute log-amplitude error between `H` and the aggregate
Sharpness-40/Sharpness-0 Hann-spectrum transfer in 0.02--0.20 cyc/px.
The 0.20--0.25 target band is excluded from fitting.  The optimum must be
interior and improve both training and holdout below-0.20 loss by at least 25%
over identity.

On heldout source pairs, applying the frozen USM to Sharpness-0 must predict
the actual 0.20--0.25 `Q25` gain: the complete 95% interval for
`Q40/Q_USM(0)` must lie in `[0.85,1.15]`.  Failure freezes the result as
`INDETERMINATE`; no richer filter or wider grid may be fitted after outcomes.

The same frozen USM is then applied without clipping to PMax0 and strehl.
Sites remain the source-frozen detail sites.  Define:

```text
D_out  = mean log(Q_PMax40 / Q_PMax0)
D_pred = mean log(Q_USM(PMax0) / Q_PMax0)
closure = D_pred / D_out
E_forward = exp(mean log(Q_USM(PMax0) / Q_PMax40))
R_original = exp(mean log(Q_strehl / Q_PMax40))
R_USM      = exp(mean log(Q_USM(strehl) / Q_PMax40)).
```

`REPRODUCES` requires the closure CI to lie in `[0.75,1.25]`, the
`E_forward` CI to lie in `[0.85,1.15]`, `R_original` to satisfy the 5% TRAILS
bar, and `R_USM` no longer to satisfy that bar.  This is not a claim that
sharpening improves truth; it asks whether the observed advantage is
transferable presentation.

## Corroborative hull distance

Exact scorecard M8 cannot be run: there is no common linear input, independent
per-frame output warp, or external temporal-noise `tau`.  The available
tone-invariant proxy is labelled `LOCAL_RANK_ENVELOPE_PROXY_NOT_M8`.

After correct integer registration, for paired rank fields `q0,q40`, construct
the 3x3 local `[min(q0),max(q0)]` envelope.  Count Sharpness-40 samples beyond
it by more than `tau_q=0.01`; repeat in the reciprocal direction.  Per-site
rank-hull distance is

```text
H = rate(q40 outside local hull(q0)) - rate(q0 outside local hull(q40)).
```

Compute `H_source` on heldout source pairs and `H_output` on the two PMax
outputs.  A lower 95% bound above **0.005** is corroborative evidence of new
local extrema.  An interval wholly inside `[-0.005,0.005]` is a weak null;
a clean hull can result from mild or clamped sharpening.

## Frozen verdict

`ARTIFACT` requires all of:

1. PMax40 has a licensed-band advantage over PMax0:
   `LCB95(exp(D_out)) > 1.05`;
2. the source-only model passes every fit and holdout gate;
3. `REPRODUCES` is true;
4. `LCB95(F_output) > 1.25`;
5. either `LCB95(F_source) > 1.25`, `LCB95(H_source) > 0.005`, or
   `LCB95(H_output) > 0.005`;
6. no leave-one-site reversal and no two spatial quadrants oppose the
   direction.

`REAL DEFICIT -- RETROSPECTIVE MODEL-CONDITIONAL` requires the PMax40
advantage and original strehl trail, a valid source model, `UCB95(closure)<0.25`,
both flat intervals wholly inside `[0.95,1.05]`, both hull intervals wholly
inside `[-0.005,0.005]`, and `R_USM` still satisfying the TRAILS bar.

Every other combination is `INDETERMINATE`.  No result here may be called
physical resolution, MTF, M1, M4, or M8.

## Commissioning required before outcomes

1. A fixed Fourier-bin oracle must admit 0.21875 cyc/px, reject 0.28125, and
   catch a reversed or above-cap mask.
2. Affine, gamma-3, and logistic point maps must move `Q25` and the rank hull
   by at most `1e-10`; a raw-power mutant must move.
3. An untouched constant-plus-noise flat pair must read ratio 1 and hull
   distance 0.  A spatial USM plant generated by a direct convolution path
   independent of the analytic fitter must make flat power exceed 1.25 and
   hull distance exceed 0.005.
4. The independent USM plant at sigma 1.0, amount 1.0 must be recovered within
   one grid step, predict its heldout target within 10%, and satisfy the
   synthetic `REPRODUCES` predicate.  A no-op model must go RED.
5. Planted displacements `(2,-3)` and `(-4,1)` must return their exact negative
   corrections.  Wrong-sign and no-op registration must go RED.
6. An above-cap sinusoid may alter only the
   `UNLICENSED_GT_0.25` sentinel, never a licensed decision.
7. Literal predicate fixtures must reach ARTIFACT, REAL DEFICIT, and
   INDETERMINATE.  Mutants that omit the flat requirement, fit the heldout
   band, or import an outcome into the source model must go RED.

Every positive control must pass and every planted defect must go RED before
either PMax output or strehl is opened by the new outcome instrument.

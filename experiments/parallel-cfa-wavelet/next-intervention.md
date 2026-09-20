# Next intervention: held-out RAW relative-blur discriminator

2026-09-19. **ARGUED proposal; no implementation or execution.** The complete
parallel wavelet is closed after the independent full-image rejection. Do not
change its weights, probes, transform or support.

Recommend one small **model-adequacy screen before an ownership algorithm**:
ask whether one actual source patch predicts another by a constrained forward
blur on structure excluded from fitting. Do not reconstruct latent detail.
The useful potential result is a directed relation between observed sources;
a small fitted residual is not itself a donor label.

## Prior evidence that constrains this test

- `docs/research/M115-deconv-headroom.md` §5 rejects through-focus width as a
  PSF calibration: its inferred scale was 1.87–2.15 times the per-frequency
  fit, and measured attenuation was much flatter across frequency than its
  optical model predicted. Near-scaled copies do not identify blur direction.
  Its matched-contrast Wiener null closes inverse reconstruction as the reason
  for this proposal; it does not test this held-out source relation. Section2.2
  also invalidates fixed-winner noise propagation as selection uncertainty.
- `docs/research/M87-occlusion.md` §5 reports lower fit R² on a successful
  known-truth plant than on a failed real reconstruction. SYNTHESIS discipline627
  explicitly forbids interpreting R² as correctness. A single-depth patch
  model must refuse mixed-depth support, rather than propagate an owner into it.
- `experiments/donor-consistency/next-support-review.md` already explains the
  delta-source trap: an unconstrained positive kernel can absorb a real feature
  at another depth, and reverse-fit failure does not resolve the ambiguity.
- `experiments/source-concentration/results-review.md` rejects thresholded
  component-radius ordering on real extended radial detail; its failure-scan
  review records no nominations on the retained real windows. Do not revive
  peak, thresholded mass, centroid or radius as evidence for this proposal.
- M78's cross-blur changed an alignment conservation statistic without improving
  held-out placement. This proposal holds the actual consumer geometry fixed;
  it neither refits placement nor uses a better fit residual as placement truth.

These checks followed separate-term `prior_art.py` searches for relative blur,
consistency, transfer, prediction, PSF and kernel, plus focused source/report
searches. SYNTHESIS §§3.1–3.4.2 retain the streaming, injected-noise and runtime
geometry constraints. No directly matching held-out RAW ownership test was
found in this bounded search; that is not a claim that none exists anywhere.

## One fixed model, with an explicit refusal outcome

Use actual gathered known4 CFA in black-subtracted DN, before WB, colour
development or tone. Fit `target = K(Sigma) * source` with a zero-centred,
nonnegative, unit-sum elliptical Gaussian. Sigma is one symmetric2×2 covariance
shared by all four CFA planes: three parameters, identity included. Bound each
standard deviation at8 quads and use a fixed24-quad support radius. These are
proposed finite screen bounds, not measured optical constants. A boundary fit
refuses; do not enlarge the family after seeing results.

No gain, offset, translation, per-colour kernel, latent image, frame-index depth
or metadata-derived defocus. Fit only a fixed spatial training block. A separate
protected block supplies the prediction test; its support is excluded from the
training target and every source convolution stencil. Use genuine scene apron,
not crop extension. Fit both directions. Return fitted covariances, held-out
residuals per plane and explicit compatible/ambiguous/refused status. No source
assignment follows merely from winning this pairwise fit.

The injected model must account for uncertainty in **both** original sources.
Small noise controls perturb original u16 samples independently, then rerun
actual rounded MHC/Catmull/CA gather and the whole fit/refusal decision. Do not
pretend gathered samples are independent, introduce a residual noise estimate,
or turn a fixed-fit probe into a calibrated ownership probability. Independent
controls must freeze the numerical fit/refusal tolerances before execution.

## First falsifier and stopping condition

The independent first scene must contain multiple training features at one
depth, and held-out compact coloured detail crossed by a genuine thin feature
at another depth. A Gaussian-blurred positive must recover its known directional
relation; this validates the operator only. The different-depth feature must
retain its own evidence or remain unknown. A compact source explaining its
neighbour through blur must not swallow that neighbour's distinct ownership.

Also require a centred, normalized multicomponent **coloured fan** with different
channel spreads, rank-1 gain-only copies, flat/noise, identical sources, clipped
cores and missing apron. These must expose model mismatch or ambiguity instead
of inventing a sharp owner. Reverse source order and use actual fractional
gather. Refusal everywhere fails the positive requirement; less fan energy or
a low residual cannot pass a truth/detail control.

**Likely failure:** the real fans are asymmetric/chromatic, while this family
is symmetric and shared; Gaussian relative blur is not a universal relation
between two defocus PSFs. Occlusion and changing specular appearance can break
the single-source model even with correct geometry. If these prevent a useful
directed prediction, close this family without another PSF/threshold sweep.

## Small implementation seam and conditional route to an image

Reuse `shared-source-field/implementation.rs::gather_direct` for the actual
consumer inputs and the original-source perturbation logic in
`boundary-cfa-wavelet/probe.rs`. Add a standalone patch-pair fitter/discriminator,
not a new merge or covariance framework. Retain only original u16 patches,
two current gathered patches and scalar pair receipts. No stack-sized aligned
collection is needed. The first screen is small enough to avoid a full RAW
render; fitting and real-data costs remain unmeasured.

If independently admitted, the next evidence is one fixed read-only panel from
the existing facet/dark windows using the held RAW map, with disputed structure
kept out of fitting. Existing compact/late source witnesses are evaluation
references, not hardcoded owners. This panel must demonstrate useful prediction
before building a complete-image field. A whole-image path would additionally
need a streaming candidate-and-witness scheme, rejection of cycles/ambiguous
relations, and an all-source confirmation pass; an all-pairs image method is
not a fast route. Do not assume transitivity to save work.

Only after those source decisions survive independent truth and real-source
review should their shared four-plane memberships feed the already implemented
full-AC replay seam with exact baseline fallback, held mean base and original
hull. That avoids another reconstruction invention, but the current proposal
does **not** yet specify or authorize that ownership field or a full render.

# Prospective independent contract for cross-scale band guidance

Preparation, 2026-09-26. ARGUED development and observation contract; no model,
new fixture, training, validation or photographic result has been run by this
reviewer. The reviewer owns this file only. `source_trace` owns the model and
`trace_review` owns new fixture choices. Root owns execution and budget decisions.

## What this changes, and what it does not

The fixed737-parameter learner remains rejected under its original contract.
The free-weight oracle remains unqualified under its original two-reference
conjunction. Preserve both reports and all their bars; do not rewrite either
decision using the prospective contract below. All12 former training cases and
all7 former held cases are now developer-visible. They are19 known regression
cases, not independent validation, even when their truth is not used in a fit.

The oracle supplies a constructive near/far improvement within the original
coefficient/Mean/hull/MHC consumer. It does not establish learnability, a global
optimum, seven-band transfer, or a photographic ceiling. Its curved positive
chroma is1.09137 times current, whereas its glint chroma is0.971927 times current.
Both fail the historical uniform-reference chroma guard. These are different
tradeoffs, not one lost-highlight result. Its freely fitted weights can absorb
particular noise draws and are not denoising targets to imitate.

Prior records read: `../learned-band-guide/plan.md`,
`../learned-band-guide/independent-choice-review.md`,
`../learned-band-guide/independent-results.md`,
`../band-weight-oracle/plan.md`, and
`../band-weight-oracle/independent-results.md`. The earlier whole-patch
marigold source-pure trial and direct StackMFF source-copy output remain rejected.
Native source inspection supplied preservation windows but no defensible cleanup
ownership; this development must not invent an edited photographic truth target.

Mechanical prior query run for this direction:
`python -B experiments/ORCH-drift-check/prior_art.py learned cross-scale "signed coefficient"`.
It surfaced B-algorithms-sota, G-edof-deconvolution, M193c-output-grid and other
records; this is a search receipt, not a claim those reports verify this design.
The already documented shared-source-field/cross-scale-source-prior failures
forbid silently replacing independent band ownership with one shared source map.

## One development lane, with a real budget

Freeze one architecture before training. Signed four-CFA coefficients and
parent/child-band evidence may inform scores, but each band retains its own
nonnegative source weights shared across the four CFA planes. Original source
coefficients, terminal Mean, input bounds, native gather and MHC stay fixed.
There is no learned RGB, learned geometry, source-subset rescue, hard-coded depth
ownership or production default change. The noise model is injected unchanged.
The author's plan must declare parameter count, feature scaling, border handling
and an inference route that does not retain aligned full-frame source volumes.

Root's cumulative training cap is20 GPU minutes, with at most3 documented
training attempts/revisions. Keep the architecture and training/development
split fixed. A revision may address a diagnosed loss-balance or optimizer
conditioning problem; it must name the observed problem and predicted remedy
before its run. No arbitrary seed search, architecture sweep or photo-driven
checkpoint selection. Save the unsuccessful attempts as well as the selected
checkpoint. These are proposed cost limits, not measured runtime claims.

Spend at most3 of those GPU minutes on the old19 alone. Their role is a cheap
live-fit diagnosis, not an end product or the whole development campaign. Before
spending the remaining budget, add the expanded physical training set and
independently drawn noise described below. GPU training time excludes native
export and builds; root must bound those separately rather than hide them in a
short optimizer timing. No automatic extension follows a timeout or failed fit.

Use actual reconstructed image losses, with separately visible flat, structured,
true-bright and chromatic terms. Balance nominated small detail regions against
large smooth areas so full-image averaging cannot silently erase them. Train
against generated radiance truth, not oracle logits: many weights can reconstruct
the same output, and oracle noise-fitting is not a supervised target. A projection
or gradient score may supplement image error but cannot replace it.

Before trusting a training curve, show the trainable path is live: finite
nonzero gradients, a directional/finite-difference check on the new scorer path,
and an actual decrease of the declared objective on a structured known case.
Report flat and structured losses separately; a falling total from flats alone
does not establish useful fitting. Record objective/gradient behavior over the
fit and near its end. Hitting a step/time limit is not convergence, and a finite
fit cannot establish a representation ceiling. Freeze the development checkpoint
selection rule before training; best-development selection is allowed, while
fresh-validation selection is not. Do not add repeated whole-workspace tests.

Stage1 uses the author's fixed27,201-parameter architecture and declared loss,
including the extra fixed-region RGB/chroma term. Its first loss excludes only
the previously unqualified clipped-glint core: original coordinates
[77,73,100,96], output coordinates [61,57,84,80]. Exclude RGB/chroma samples and
gradient stencils touching this rectangle; normalize over retained samples/edges.
The genuine unclipped glint remains supervised. External adjacent/spread scores
and all historical windows are unchanged, including any overlap with that core.
This is declared censoring of an unreachable sharp-radiance target, not a mask
chosen after a failed fit.

Before the first fit, `independent-check.py check-commission` binds the author's
successful commission and checks every exact loss mask plus the normalized fixed
ROI windows. Independent mutations at the excluded rectangle's corner and one
pixel outside test both gradient-stencil refusal and retained supervision. It
also chooses a deterministic nonzero head on the known near/far case and compares
autograd with a central difference of the COMPLETE declared loss, ROI included.
Use epsilon0.01 on the largest-magnitude head-gradient component, a conditioning
choice, with5% derivative agreement and actual descent/ascent required. No result
from this commissioning is an image-quality or held-out claim.

The subsequent `check` reuses the pinned previous analytic/native score checker,
replays the saved model and weights exactly over all19 cases, and preserves both
the original seven-case judgment and the prospective development judgment.
Those first-fit judgments are known regressions only and cannot admit a photo.

## New evidence without another large framework

Reuse the existing actual-consumer exporter, reconstruction and replay. The
independent fixture author's frozen scope is24 new training cases:4 compact
flats,10 natural-texture two-layer compositions,8 analytic nonstationary
pattern/bright/colour cases, and2 full-support seven-band analytic cases. Natural
textures use existing marigold112/152/320 image patches as texture only, never as
ground truth for that photograph. Each generated case/combination receives an
independent original-sensor noise draw before its actual native processing.
On-the-fly per-optimizer-step noise resampling is not implemented or required;
do not claim it happened. The independently drawn cases add noise diversity but
do not themselves establish robustness to arbitrary realizations.

There are10 fresh independent challenge cases: dark flat N17/ISO1600; bright
flat N65/ISO400; forked/tapered geometry over CHIP149 texture N33/ISO100;
serrated-polygon geometry over CHIP149 N17/ISO400; unclipped glint plus weak
adjacent structure N17/ISO1600; clipped counterpart N17/ISO400; nonseparable
chirp with colour N9/ISO100; near-fine/far-coarse N65/ISO100; and two full-support
seven-band cases (flat and fresh multiscale structure, N5). The held pupil is a
clipped disc with x<=0.45. New subject texture, geometry/composition and pupil
form are held from training; changed noise seeds alone are not the physical
holdout. None of these generated optics calibrates the actual lens.

The fixture author freezes exact manifests, geometry, pupil and noise choices,
windows and baseline eligibility before the learned checkpoint is exposed to
those challenges. Do not move their windows after seeing the candidate. The old7
cannot be rebranded as this challenge. New challenge truth and results must not
choose any of the allowed training revisions. If challenged cases later enter
development, they lose held-out status and a new independent screen is required;
this is not authorized within the present budget.

Native seven-AC support is a distinct requirement. The fixture author identifies
at least897 CFA quads as necessary and proposes1024 or odd1031 quad dimensions.
Use two bounded full-support probes: flat and a multiscale two-depth/contact
scene constructed through original u16 inputs and the native consumer. Do not
claim that enlarging an80x72 crop makes its physics representative. Cheap analytic
seven-band probes test support, scale behavior and retention; they are not a
replacement for the compact physical renderer's occlusion/PSF tests. Conversely,
compact high-N cases do not establish seven-band behavior. Record these scopes
separately: neither their conjunction nor a small replay proves488-frame
photographic performance. The fixture author's separate specification resolves
the exact manageable counts before export; no cases may be dropped silently.

Reuse exact native reconstruction commissioning, including exercised bounds and
odd sizes, and replay the selected scorer through the actual consumer. Show live
source-weight influence and preserve existing numerical identity/permutation
checks within their stated scope. Existing ordinal-seeded probe behavior means
fixed-tensor permutation is not an end-to-end RAW order-invariance claim.

## Prospective image judgments and their failure directions

The fresh checker first scores exact truth and deliberate detail erasure, added
noise, wrong-source weights and bright-core suppression. Require the relevant
mutation to occur and the appropriate judgment to reject it. Flat control comes
first. A truth image passing does not prove it is representable by this consumer.
Synthetic noise drawn from the injected calibration tests the operator, not the
camera calibration. No new private stage noise estimate is permitted.

Report every fixed window's absolute RGB/green/chroma error and ratios to BOTH
current and uniform, including failures. Report signed near/far/colour/glint
component recovery separately. Preserve the historical eligibility convention:
reference recovery below0.5 is unqualified retention, not candidate-caused loss;
cap recovery credit at1.0, so overshoot gains no detail credit. Where ratios are
undefined because a reference error is zero, show the absolute errors and use
only precommissioned arithmetic tolerances, never a fitted denominator floor.

The conservative automatic-observation bars are prospectively:

- Flat RGB/green/chroma errors remain within1.10 of both current and uniform.
- Two independently nominated structured positives improve RGB RMSE by at least
  5% against current, with a live difference from uniform and protectable detail.
- Other qualified structured RGB/green/chroma windows remain within1.05 of
  current. Genuine glint cores and weak-colour regions are protected separately
  from their surrounding spill; a smaller surrounding error cannot excuse core
  destruction.
- Each eligible near/far, true-bright and chromatic component retains at least
  90% of the capped current-reference recovery. Absolute image-error bars remain
  binding alongside this test, since projections can retain amplitude while
  introducing false structure. No gain is claimed for an unqualified component.

The1.05 structured tolerance is a prospective conservative tradeoff allowance,
not a measured perceptual threshold. The original1.10-both-comparators rule
continues to describe the old experiment only. Uniform remains a hard flat-noise
reference and a reported structured comparator; structured chroma relative to
uniform alone is no longer an automatic veto. Uniform can suppress colour error
by destroying chromatic structure, so that comparison must be read together with
the component and absolute-current tests. This does not waive actual colour harm:
the old curved oracle would fail1.05-current chroma, while its glint would not
fail solely for being less smooth than uniform.

Lower RGB or chroma error can reward blur or desaturation; detail/component
checks oppose that direction. Component projections can reward ringing or
coincident structure; absolute errors oppose that direction. Gradient magnitude
can reward noise/sharpening and is inadmissible as a quality acceptance score.
A small aggregate can hide localized damage; use the fixed region results rather
than average a failed core into a passing background. No single metric certifies
photographic quality.

## A bounded photograph is an observation, not retrospective qualification

Numerical corruption, inactive training, unexplained domain errors or substantial
unreviewed flat/detail/core/colour damage block a photographic run. Passing the
conservative bars permits consideration of one complete488-source marigold
observation; it does not imply success. A narrowly failed synthetic conjunction
may instead support that observation only after an independent review states the
exact failed case, magnitude, credible failure mechanism, remaining protection
evidence and the photographic question it can still answer. Root records this
separate decision before execution. Retain the failure and never relabel the
synthetic screen as passed. A generic wish to see an image is not that rationale.

Freeze the selected checkpoint/configuration before the photograph. Use the exact
current complete baseline, same input set, existing geometry, full488 source
contributions and pinned development/tone. No local mask, threshold, source-count
or photo-driven checkpoint rescue. Follow the repository's bounded streaming
resource rules; incomplete rendering is not a quality result.

Independent review uses complete before/after images for context and existing
unresampled native tiles no larger than400px, including the fan's near/far hairs
and rim/inner-bud controls. Look explicitly for erased/interrupted hairs, colour
fringes, new switching seams and damaged true bright detail. Smoothness or darker
yellow alone does not establish cleanup. The baseline itself is not truth.
Deliver the complete matched outputs if any improvement is shown or claimed;
crop-only results do not satisfy the owner's delivery requirement. No production
promotion, mineral transfer or SOTA claim follows without its own evidence.

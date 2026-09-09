# Common-TIFF count and dimension continuation

2026-09-08. Root-owned next engineering task after the completed sampler
executions; sampler independent saved review is finishing. Source preparation
may proceed now, but no live product source changes until that review's
current-source check finishes. User authorized autonomous continuation.

## Question and prior answers

Extend the completed identity-grid common-TIFF consumer beyond its fixed
three128x96-frame intake while preserving the original behavior and declared
simulation noise. This is software input/output generalization, not a new
merger, physical calibration, resampling or SOTA claim.

The mandatory prior_art searches actually ran before this commission, exit0:

    python -I -S -B experiments/ORCH-drift-check/prior_art.py "common TIFF" "frame count" dimensions "known map" gather "resampling noise"
    python -I -S -B experiments/ORCH-drift-check/prior_art.py common-TIFF "common RGB" frame-count "odd dimensions"

The implementation auditor ran both and root also ran the second. Exact
findings and context reads are in ../sampler-boundary/next-consumer-audit.md.
Headline reports: V-GATHER.md, V-HEADTOHEAD2.md, BUILD-DEMOSAIC.md,
BUILD-GATE.md, common-tiff-stack-integration.md. Secondary reports:
BUILD-SHARP.md, ORCH-veiling.md, M107b-lateral-correction.md, M95-resample.md,
BUILD-TRIAGE.md, BUILD-CROP.md, M20-VERIFICATION.md, M126-composite.md,
M181-m4-feasibility.md, M-COVER-NATIVE.md, M152-site-census.md and
M12-shrinkage-measured.md, all under docs/research. The audit also reads
M165-common-input.md and experiments/review-output-adapter/audit.md.

The common stack-to-image route is already commissioned; do not rerun its
completed twelve-case study. The RGB variance/covariance cautions in V-GATHER,
BUILD-GATE and BUILD-DEMOSAIC govern later maps. M165's external profile
qualification remains unresolved. Frame count does not measure physical focus
spacing, eligible sites or deep-stack gate potency. An already-answered finding
is a successful outcome, with no justified change required merely to show work.

## Fixed implementation scope

Add common-tiff-stack-v2 at the existing CLI entry with2..8 ordered inputs,
each axis64..512, checked pixels<=262144 and exactly four pyramid levels
(three Laplacian bands plus base). Preserve v1's exact3/128x96 admission,
original256KiB input and128KiB writer caps, description/software/profile and
legacy output bytes. Keep the same seven manifest fields.

Use runtime geometry/count and bounded vectors in the existing own CLI
modules. Core BandMerge, parser, coefficients, InputRange, HardFloor, profile,
RGB order and the two existing simulation-only noise laws stay unchanged.
No new noise estimator, color conversion, exposure fit, map, crop, kernel,
band-count option, RAW/capture/model or comparator intake.

Retain only the current encoded input, decoded u16 frame and f32 preparation
beside reusable merge/workspace state; do not accumulate aligned frames.
The proposed v2 per-input/output cap is6*pixels+64KiB, at most1,638,400B,
with total eight-input extents checked before visits. Manifest remains64KiB.
Detailed final/staging receipts may grow with the bounded count; enumerate
simultaneous writer/result/log artifacts before releasing execution. The
implementation contract must make each claimed cap an actual pre-read,
pre-allocation or checked-publication guard.

Early bad count/dimension/overflow input must refuse before decoding/folding.
A later frame's wrong geometry or payload hash must retain its exact completed
prefix and produce no admitted final image. Preserve duplicate/profile/noise
refusals and all v1 admission restrictions.

## Independent evidence to freeze before execution

Separate author fixes the exact finite fixture list and oracles; no product
implementation logic copied into its expected image path. Include:

- Distinct constant contributors atN2,5,8 on small, odd non-square and
  upper-bound geometry. Every omitted/duplicated contributor must change the
  independently rounded expected mean; also authenticate every actual fold.
- Odd129x97 asymmetric RGB addresses, last row/column/corners and multiple
  strip arrangements. Independently require level geometry129x97,65x49,
  33x25,17x13. Wrong dimension, dropped edge and channel-order destroyers
  must actually differ.
- One fixed new odd-size noisy population with observer off/on/placebo,
  identical whole TIFF/pixels, injected variance/proxy identities and
  appropriate level gain. Require both actual accumulated-denominator
  populations in Laplacian levels; this is no physical-noise certification.
- Early invalid bounds/counts and late final-frame geometry/hash failures.
  Refusal reason, fold prefix and absent admitted output are part of the test.
- One held v1 output compatibility case, not the prior full image campaign.

Before each predicate, identify an input that makes it fail and an actual
positive/negative control. Runtime counter and image agreement are distinct:
a mean-valued missing contributor can hide from image equality alone.

## Ownership and release boundary

factor_eight_implementation owns an external unapplied patch and source
contract in this directory first; no live crates edit during the sampler's
pending source audit. coordinate_verification owns independent fixture/checker
design in this directory. Root owns integration, exact commits and releases.
Use another independent reviewer for actual output interpretation.

This charter authorizes source preparation only. Before builds, fixture
generation or images, root must freeze the exact finite case population,
source/command/environment/input identities, per-stage resource ceilings,
old-output provenance and complete actual artifact reader. There is no
numeric execution or retry authority in this source-only charter.

After scope completion, integer translation plus input-only crop is the
next separately considered geometry step. Fractional gather awaits a
resampling-aware covariance and band-noise contract; identity variance24
cannot silently stand in for it. No maps are bundled into this change.

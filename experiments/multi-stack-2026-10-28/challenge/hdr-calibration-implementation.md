# Conservative HDR radiometric calibration implementation

Source: crates/strehl-cli/src/session-photometry.rs. Additive opt-in HDR module;
no existing merge, sampling, alignment or ordinary-stack arithmetic changed here.
Initial frozen source SHA256:
84137e9a3d0e59a70b2d75e0a493607b3aadf7bbca48cbbea38a031f6a23f3ef.
Root owns exports/integration, schedules tests and independent review, and binds
this source into the rendering provenance. No Cargo or RAW job ran in this
implementation allocation. The preceding nine-source preflight is separately
recorded in hdr-preflight-results.md.

## Consumer API and lifecycle

    workspace_bytes(geometry, config) -> anyhow::Result<usize>
    report_bytes(pass_count, config) -> anyhow::Result<usize>
    calibrate(session, identities, alignment, cache, anchor_pass,
              &[PassPhotometryInput { nominal_gain, noise, profile }], config)
        -> anyhow::Result<PhotometryReport>
    report.require_gains() -> anyhow::Result<&[f32]>

Run calibration before allocating merge buffers. Reuse one full-domain
NativeSampler source-by-source, keeping only two compact spatial patch sets.
Originals stay u16 in the existing source cache; gather/output arithmetic is f32.
No full aligned frame volume or private noise fit is introduced. NativeSampler
preserves the complete image center, existing applied optical profile, pinned
resampler and original clipping/coverage masks. The calibration-phase workspace
is checked against1GiB by default; source cache and decoder are separately
budgeted by the caller. Retained report records, bounded reason/identity strings and Vec capacity growth
are separately checked by report_bytes(pass_count, config). calibrate enforces
the sum of numerical and report buffers against its phase limit; the caller
adds both to its preflight alongside the source cache/decoder allowance.

Each supplied noise model must be trustworthy and its levels must match the
original source exactly. Source identities must be unique. Calibration uses
nominal exposure gains only to put source values in common units; a fitted
correction divides the target nominal gain by its measured normalized ratio.
The caller must pass that TOTAL corrected gain into the existing variance
propagation, which multiplies absolute variance by gain squared. The helper
never creates a noise curve or treats spatial standard deviation as temporal
noise. Its generous variance allowance is only a compatibility eligibility
heuristic, not a delivered covariance or precision estimate.

## Admission contract

Fixed8x6 patches of32x32plane pixels are arranged before values are inspected;
checkerboard cells alternate scalar fitting and held-out validation. Any patch
with missing original coverage or any censored contributing CFA tap is excluded
as a whole. All four colors need positive signal above the injected noise margin.
The same procedure works when the explicit primary/anchor is the long clipped
exposure: clipped anchor patches never calibrate the other passes.

Mutual-nearest geometric scale candidates only nominate source pairs. At most
nine deterministic candidates per target pass are sampled across the track.
Each pair fits one log-median ratio from fit patches, then must satisfy the
held-out median1%,95th-percentile3%, and maximum5% residual bars. The maximum
prevents a single adverse patch from hiding beneath a large sample's percentile.
Correction is bounded to+/-0.25EV. Flat-only agreement cannot certify compatible
focus/placement: several textured patches must agree after correction, with
centered detail mismatch checked against the supplied noise allowance. These
checks concern sampled overlap; no global same-focus certificate is written.

At least three accepted original pairs must span at least50% of both focus
tracks. Their correction variation must be<=2%. One final pass-wide log-median
scalar is then fitted from accepted pair scalars. All retained validation values
are rechecked against THAT scalar, rather than each pair's separate fit. This
last check prevents locally plausible corrections from hiding a global failure.

A supported correction-bound or held-out spatial/color failure is a measured
contradiction, and vetoes the entire pass even if three other pairs pass. Missing
coverage/signal, flat-only data or textured correspondence failure are unavailable
evidence rather than a measured scalar contradiction. This distinction and all
refused pair details persist in the report.

All targets must pass before calibrated_gains becomes Some. Otherwise the full
serializable report retains exact identities/ranks, patch exclusions, fit and
validation results, bounds, stability and refusal reasons. require_gains returns
an actionable aligned-layers/capture remedy. There is no silent nominal HDR
fallback. Reported thresholds are engineering hypotheses requiring adversarial
controls and real validation, not fitted sensor constants.

## Prepared controls and verification status

Eleven inline tests are now prepared, with a00 flat-noise first: flat-only refusal;
known bounded gain recovery and exact identity; excessive gain, color and
spatial drift; one local flare that defeats percentile-only screening; blur and
misregistered detail despite equal means; clipped anchor and NaN-poisoned true
coverage gaps; original-unit gain-squared variance; pair count/rank-span/stability;
revalidation under one final scalar; nine-pair survivor-selection adversity; and
checked numerical/report workspace and geometry bounds.

Source-only formatting completed with:

    rustfmt --edition 2024 crates/strehl-cli/src/session-photometry.rs

UNVERIFIED at initial freeze: compilation, these new tests, runtime acceptance
on the full HDR corpus, photographic recovery and calibration performance.
Independent review is assigned to root/independent_review. The prior native
repeat output and sampler controls do not validate this new calibrator.

## Independent review and correction record

Root compiled the initial source: flat control passed, then9/10 controls passed.
The positive clipped-anchor control had only180DN texture; its simulated short
exposure was six times darker, so gain amplifies read variance36times and it
correctly failed the conservative texture guard. The control now compacts an
actual360DN checkerboard, retains the real good compact patches and explicitly
requires textured acceptance. No production gate was relaxed.

Independent reviewer root/independent_review found a survivor-selection blocker:
three accepted pairs could certify a pass despite six supported contradictory
pairs being discarded. PairRefusalKind now distinguishes unavailable evidence
from affirmative radiometric contradiction, and finalize_pass vetoes any such
contradiction before considering accepted survivors. The new nine-pair control
uses the actual pair and pass code paths, includes three good pairs spanning
both tracks, and tests six contradictory versus six unavailable pairs separately.

The fresh source freeze after both fixes is SHA256
585fe0d44a048e4714fdba574fc6cf2ff2ca56e5df04f17b3a60faff8a6c8539.
VERIFIED by retained root logs: initial flat control passed; after corrections,
all11controls passed in outputs/multi-stack/checks/photometry-suite-2.log. The
log shows Compiling strehl-cli, not a stale cached-test assumption. Root ran:

    cargo test --locked -p strehl-cli --lib session_photometry::tests::a00 -- --nocapture
    cargo test --locked -p strehl-cli --lib session_photometry::tests:: -- --nocapture

Working directory and GIT_WORK_TREE were
C:/Users/chris/.codex/worktrees/multi-stack/strehl; CARGO_BUILD_JOBS=8. The final
suite used STREHL_BUILD_ID=c149e52834fc-multi-stack-candidate5 and exited0.
Compilation/controls establish mechanics only. Runtime HDR acceptance and
photographic recovery remain unverified. Two syntax-only clippy findings await
root's current build freeze release; no numerical change is proposed.

Root subsequently froze candidate5, then released two clippy-only syntax edits:
a combined if-let candidate guard and is_multiple_of(2) in the test stimulus.
Current module SHA256 is
66763ae97e9870f54fb4d305c87473f7d820ed5d8cdc0b9df19a742642aad1f3.
A direct comparison against candidate5/owned-source.zip confirms only those two
edits. Admission/arithmetic remains the tested585fe0 source. Root's next check
must confirm the lint cleanup; no additional RAW run occurred in this lane.

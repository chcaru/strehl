# M194d independent comparison design

2026-09-07. Owner: `roadmap_audit`. **PREREGISTERED DESIGN ONLY:** no build,
measurement, render, source mutation, RAW access or new acceptance bar was
performed for this document. The exact operator below is the author's proposal,
subject to root approval before implementation. This document does not activate
the broader Phase-1 gate or authorize an additional candidate search.

## Scope and prior findings

The current [program](../../docs/proposals/2026-09-sota-program.md) permits a
bounded development experiment while retaining Phase-1 and capture requirements.
[M138's audit](../M138-w1-gate-audit/REPORT.md) established that the old
`NO_COMMON_K` outcome rejected legacy-width matching before rendering any Pareto
output. It did not refute admission merging. Its other findings remain: a
selected maximum is not an unselected pair statistic; pooled calibration can
hide per-frame failure; a Gaussian image reducer is not exact heteroscedastic
variance propagation; and the noncentral/warp/coarse-band distribution was not
fully commissioned.

[M138's repaired draft](../M138-w1-gate-audit/corrected-gate-preregistration.md)
is still not a frozen campaign. It separates statistical calibration from
output quality and rejects assertions in place of raw evidence. The surviving
M143 review account in [STATUS §2.9.44](../../docs/STATUS.md) explains why the
0.90 spatial-power threshold could not simply become a temporal-variance bar;
it also refutes the accusation that this number was fitted to width survivors.
No separate M143 report was found in the bounded path/content search. This
design cites that available account and the incorporated repairs, not an
unread independent report.

Consequently, M194d cannot return `PHASE1_GO`, a universal admission probability,
a camera-calibration result, a scorecard pass or a refutation of every admission
operator. It can expose this one heuristic's delivered-pixel tradeoff on a known
development plant. Width, singleton fraction and weights may diagnose behavior;
they must not filter which fixed images get rendered or imitate legacy widths.

## Fixed operator and comparison population

The author's proposed operator is:

```text
F = existing gate * beta_band * V_band                 [DN²]
q = max(E - F, 0)                                     [DN²]
a = q / max(F, 1 DN²)
w = (hypot(a, 1) / 64)^p, including frames with q = 0
```

The constant 1 in `hypot(a,1)` is dimensionless and fixed prospectively. It is
an uncalibrated weighting choice on the existing floor scale, not a statistical
confidence level. The existing exponent/ramp, numerical exponent clamp,
injected noise, measured floor, geometry, Gaussian base, hull and writer remain.
The intended implementation uses the current one-pass `BandMerge` accumulator;
it may not retain an aligned-frame stack or silently introduce a winner pass.
The agreed proposed API is `AdmissionMode::{HardFloor, FloorPedestalV1}` with
`MergeConfig.admission` defaulting to `HardFloor`. The new test-local entry
requires `STREHL_M194D_ADMISSION` to be exactly `hard-floor` or
`floor-pedestal-v1`; missing/malformed values refuse. New
`m194d-consumer-plan-v1` and `m194d-consumer-receipt-v1` schemas bind
`config.admission` plus the explicit formula/version. A new child entry under
`known_scene_benchmark::band_admission_benchmark` uses the shared consumer;
the original M194b entry and schemas remain. No Cargo feature or dependency is
needed. The proposer owns the final exact entry name and root-approved paths.
A changed formula or setting requires a dated pre-output amendment here;
outcomes cannot choose a revised constant.

**Pre-output design refinement:** an earlier author proposal used a compile
feature and this document initially proposed four unfeatured output controls.
Before any implementation or output, root/author chose the explicit runtime
enum and required the complete forty off-mode outputs plus forty on-mode
outputs. The remainder of this design reflects that stronger concrete binding.

Compare against **committed M194c**, not the more favorable pre-repair M194b
flat-noise result: commit `04128e041dabc0bdb86c64526cd8155dd0a0fd07`, baseline
`experiments/m194c-probe-layout/candidate-2/`, with run-index SHA-256
`71b2ba05ddc23fc78640aa1f9b53ea3b12ddac0f1fa955d1ee8cdf8428fda6ab` and score
SHA-256 `5963b7b5804e9b726bd0cb4ee561dd857c45b26c996625794d53b81d3aa83428`.
Its copied executable, source record, inputs and all forty TIFFs remain intact.

Use the same twenty input cases and forty outputs per mode: flat and scalar plane, each
noise-off plus repeats 701/709/719/727/733/739/743/751; analytic color and color-null
noise-off; full9 and original-frame4/single4 for every case. Reuse the actual
twenty manifests/180 CFA inputs. Do not regenerate noise, modify optics, search
seeds, change a mask, fit a normalization or add a favorable scene after output.
The sole experimental setting difference is the named candidate operator.
Render all forty `hard-floor` outputs and all forty `floor-pedestal-v1` outputs
on the same new pinned executable. The former must match the archived M194c
forty complete TIFFs. Pair each candidate with its exact off-mode counterpart;
do not replace one of the forty off-mode checks with a synthetic shortcut.

Retain three bands, gate 2, the existing exponent ramp, measured floor,
Catmull-Rom, two workers, full-resolution MHC, CameraLinear, WB consumed as f32,
mean base and the existing input-range hull. The physical frame-4 gauge, curved
placements, quad crop (9,7,142,106), native offset (18,14), RGB16 284x212 output
and native ROI [64,256)x[64,176) remain fixed. Single4 retains local probe index 0;
original frame 4 uses local index 4 in full9. It is an actual single-input
comparator, not a common intermediate-noise seed control or an attainable oracle.

## Delivered quantities and their failure directions

Reuse byte-unchanged `m194b-known-scene/score.py` for target construction, TIFF
interpretation, error, repeated error, paired differences and registered-wave
readout. Use the existing separate pupil/cell integration and Welford/direct
complex readout for a bounded independent arithmetic check of the final result.
Do not reproduce the whole old proof suite as purported new corroboration.

- **Truth and detail:** retain per-RGB bias/MSE/RMSE against both the continuous
  cell-integrated ideal and the in-focus optical-observation target for scalar
  scenes. For noise-off plane, report both waves' amplitude and phase versus
  each target and baseline. Higher amplitude alone is not better: overshoot,
  ringing or incorrect phase can increase it. Lower noisy MSE can reward blur;
  ideal error, noise-off waves and the paired flat scene expose that direction.
- **Noise:** for each scene and arm, use same-seed candidate-minus-baseline
  per-repeat MSE differences and whole-repeat SEM. Report temporal variance
  ratios/differences and the existing delete-one-repeat jackknife SE. There are
  eight repetitions, not millions of independent pixels. Keep repeat-mean bias
  and variance distinct; do not clip a negative finite-repeat bias estimate
  into a fabricated zero. Include within-version full9-minus-single4 results
  as context, without allowing that contrast to replace the version comparison.
- **Color:** score the analytic color and color-null cases against their actual
  RGB cell-integrated truth, per channel. They have no optical-observation target
  or repeated-noise uncertainty. Channel averaging can hide opposing errors;
  color-null shows whether weighting manufactures channel differences. These
  analytic inputs do not establish color accuracy of the optical scalar plant.
- **Sparse error:** alongside unchanged whole-image/ROI pixel-movement counts
  and maxima, add only the following declared diagnostics on the fixed ROI:
  per-channel 99.9th percentile and maximum absolute truth error; counts of
  `|candidate-truth|-|baseline-truth| > 10 DN` and its symmetric improvement
  `< -10 DN`; and the inherited count of absolute movement >10 DN. Use every
  fixed case/target and report counts over the full fixed population. Define
  the percentile by nearest rank `ceil(.999*n)` of sorted absolute errors, so
  a library's interpolation default cannot choose it. These are descriptive
  tails, not new pass thresholds. Movement alone is not harm, and a lower mean
  cannot hide a worse tail. Record the actual worst locations and signed
  before/after/truth values, including each new worst site.

Also retain the already identified red sample at native (142,170), flat/repeat
709/full9, as a named regression trace; report its values in all eight flat
repetitions. Improving that one selected site cannot establish general benefit.
All-output sparse diagnostics prevent that historical coordinate from becoming
a new optimization target. Full-image movement can be described separately;
do not expand the quality ROI to manufacture independent boundary evidence.
Delivered clipping counts may flag saturation, but a post-hull TIFF cannot
establish a pre-clamp overshoot bound. No pre-clamp observer is added here.

Retain M194c's existing engineering review triggers unchanged: >1 DN increase
in a registered channel/ROI RMSE, >2% temporal-variance rise, or >1 DN loss of
a noise-off plane-wave amplitude requires an explicit disposition. These
triggers do not create a quality GO when absent. Report smaller and opposing
movements too. Numerical integration agreement tolerances are not physical
uncertainty or practically significant effect sizes; M194b's approximation
restrictions remain. No pooled ranking may hide an adverse channel, scene,
target, repetition or sparse-error result.

## Economical controls, before trusting the comparison

The operator verifier owns independently chosen coefficient/actual-consumer
controls. For this proposal they must show that q=0 produces a positive weight
**and reaches normalization**, rather than being zeroed by the caller; equal
below-floor inputs reach the mean; unequal-floor/noise cases remain finite;
high-SNR preference is live; the fixed exponent ramp/clamp is respected; and
single-frame, chunk combination and frame-workspace lifecycle behave as declared.
An algebraically positive formula unused by the real branch is not a live
operator. A passing same-formula test does not commission its noise calibration.

Require all forty new off-mode complete TIFFs to match archived M194c. Also
assert the actual `MergeConfig` default and original M194b options resolve to
`HardFloor` before any test-local override. Explicitly selected off-mode
identity alone is not an observation of an unselected-default call. Together,
the source/default check and full output comparison constrain accidental
default-path changes. The on-mode must change a separately labelled
actual-output power fixture supplied by the independent operator verifier.
If it is live there but inactive on all forty fixed candidate outputs, report
no measured benchmark effect; do not grow the scored population until it wins.
Single4 identity is checked according to the exact operator's declared
arithmetic, not assumed from its name.

Reuse commissioned M194b/M194c offset, flat-blur, true-wave blur, color-swap,
known-repeat-noise and same-output controls. New sparse arithmetic needs only a
cheap, separately chosen two-pixel truth-error plant: one pixel improves and
one worsens by equal amounts while the mean hides the exchange; include a
same-output null and a changed site away from (142,170). Fixed nearest-rank
values on a small list must be manually predictable. These diagnostic arrays
never replace candidate images. No broad frequency/threshold search is required.

## Minimal binding changes that really need commissioning

The original M194b reader strictly pins `CONFIG.select == SoftPower`, complete
environment, plan key set, exact child command, and build argv. M194c's wrapper
also permits only a gatefloor source delta. Those contracts cannot silently
describe a new admission mode. Do not weaken them or rewrite
their frozen artifacts to make this candidate pass.

Use one explicit M194d control-plane revision, importing the unchanged
pixel/scoring components and reusing existing binding checks where their
contracts still apply. Narrow versioned copies of `consumer-run.py`,
`run-baseline.py` and `score-benchmark.py` are reasonable: record their original
source digests and enumerate the necessary entrypoint/schema/config/environment/
driver/source-set differences. Import `score.py` from its original bound path.
Do not silently monkeypatch or project candidate fields away to satisfy the
old validator. Freeze before output:

1. The root-approved product source allowlist (core operator/configuration and
   required CLI/fixture integration), exact Cargo argv and test entrypoint,
   compiler artifact and isolated executable shared by both modes. Bind actual
   bytes before/after and visible compilation. No feature/dependency change is
   permitted by the current proposal.
   Include new untracked files explicitly; `git ls-files` alone omits them.
2. A schema-versioned plan/receipt field naming the exact candidate operator,
   formula version and constant. It must originate in compiled consumer state,
   and match the externally trusted prerecord, command/build and final receipt.
   Merely setting a JSON label or reporting the old SoftPower config is
   insufficient. Keep unrelated configuration and the full environment exact.
3. A complete fixed index tying every output to input, plan, receipt, executed
   child, build and actual TIFF. A combined index is keyed by mode as well as
   scene/repetition/arm; two separately sealed mode indices are also valid.
   Shared input hashes across modes are intentional, whereas duplicated output
   identities are not. Reuse original producer hashes; freeze both exact modes
   before the first render. Keep schema/source revisions
   explicit rather than projecting away an operator field to fool the old
   baseline-only validator.
4. The union of the existing compiler-input map and a small supplementary map
   for actually included external Rust tests plus new controller/reader sources.
   Discover includes from current declarations, bind their exact byte snapshots
   through the full run, and allow independent review files to be written
   outside the frozen set. Reuse M194c's commissioned closure/check helpers
   where applicable; do not copy a second general evidence engine. Its current
   include resolver assumes the CLI crate's `CARGO_MANIFEST_DIR`; any new core
   include must use the actual including crate's root. The fixed known include
   set is sufficient; a general Rust parser is unnecessary.

The new-boundary refusal set is deliberately small: missing/malformed required
mode or wrong binary with a candidate label; on-mode with a legacy label; mismatched
plan/receipt operator; coherently rehashed unrelated config/crop change; omitted
new core/include source; and missing or duplicated paired output. Each has
recomputed outer hashes. The unchanged same-candidate package is the inert
control. Reuse existing chronology, path, TIFF metadata and actual-CFA binding
commissioning unless a revision changes those contracts. Final independent
verification reads the forty candidate, forty off-mode and forty pinned
baseline TIFFs once, pairs by scene/repetition/arm and mode, and rechecks actual
source/input byte invariance. Off-mode-versus-archive is exact byte identity;
on-versus-off is the paired quality comparison.

## Decision limits

This proposal can dilute detail by giving blurry/below-floor frames positive
weight; it may reduce sparse selector excursions while doing so. Its constant
and current beta/variance approximations are not calibrated probabilities.
The scalar plane has one depth and cannot exercise an occluding two-layer edge;
the analytic color plant has a separate, narrower forward model. Neither can
settle deep-stack alignment, general occlusion halos, physical noise calibration,
RAW decoding, real-scene material detail, or the frozen Phase-1 population.

The useful outcome is one attributed development result with its gains, harms
and inactive cases retained. A mixed result is a tradeoff, a failed instrument
is not a refuted merge, and an unpowered fixture is not affirmative evidence.
The root chooses the next bounded experiment from that result. No extra
operator, parameter tuning, capture release, default promotion or scorecard
change follows automatically from this design.

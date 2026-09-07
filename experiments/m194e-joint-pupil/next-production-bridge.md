# M194e next production bridge: source and size audit

2026-09-07, `roadmap_audit`. **VERIFIED by source inspection / DERIVED support
arithmetic; proposed execution is UNRUN.** Only this document is changed by
this audit. No Rust edit, build, renderer, metric, RAW read or new quality
population. Actual M194e CFA admission still requires successful independent
float commissioning followed by independent conversion checks; no successful
float authority is assumed here.

## Decision: reuse the path, give the input new semantics

The production seam already exists. The historical
[production audit](../review-production-truth/audit.md) predates M194; its
missing-seam finding must not be repeated as current absence. M194 added
`PyramidFrameSource`, `PreparedPyramid` and `run_pyramid_prepared` in
`crates/strehl-cli/src/merge_cmd.rs`. M194b's
`merge_cmd/known-scene-benchmark.rs::FileSource` actually loads checked CFA,
constructs `Frame`, and runs that body through gather, four-plane fold,
canonical reduction, collapse, optional confidence rereads and the real TIFF
writer. M194d adds an explicit admission mode to that same path.

The smallest new integration is a test-local strict reader for admitted
M194e inputs, feeding a streaming `PyramidFrameSource` and the existing prepared
body. It must not copy `BandMerge` or writer arithmetic, encode fake RAWs, or
route through M165's one-frame common-TIFF exercise. The
[output adapter audit](../review-output-adapter/audit.md) already identified
pre-render domain planning and actual post-write checks; M194b/d implement
those pieces for their own fixed synthetic contract. Reuse that narrow pattern.

The existing M194b `Inputs::load` is correctly incompatible: it requires
320×240, nine indexed frames, reference4, four named scenes, fixed noise/WB
fields and the M194b schema. M194d's nested entry still consumes that input
schema. M194e instead has five64×48 frames, signed geometric defocus, ordered
layers, electron/quantization evidence and separate float/CFA commissions.
Do not relabel these inputs as `m194b-known-scene-v1`, invent missing repeat
fields, or weaken that old parser. A small versioned bridge adapter may reuse
strict JSON/hash/file-loading helpers and the shared product body; it needs
its own exact input-to-prepared-state mapping. No new general certificate
engine or80-output controller is needed for the initial bridge commission.

## What the bridge must actually bind

The caller supplies the genuine emitted-manifest and independent CFA-commission
digests externally. Verify their exact association with the float authority,
source/model/settings and five actual `.cfa` payloads. Read each complete
6144-byte little-endian u16 frame at consumption, recheck its hash and fill
only declared active storage. Frame metadata is explicit: active64×48,
origin0, stride64, buffer height48, RGGB, black512 and white15360. Keep only
metadata plus current decoded frames under the existing bounded worker scheme.

Preserve the source adapter's path/count checks, storage validation and
confidence source delegation. Existing sentinel paths distinguish this path
from real RAW decoding; an injected source is not a claim that every metadata
helper performs zero filesystem probes. Keep CA/defect/restoration disabled and
exclude real capture/profile lookup from the synthetic claim.

Before pixels, bind the effective output settings, actual `PyramidDomain`,
resolved `CoverFit`, all selected source indices, actual level sizes and
reference/gauge. After pixels, read the actual TIFF dimensions, samples,
orientation, color description, ICC disposition and whole-file/pixel hashes.
The test executable, its including Rust source set and inherited numerical
sources need the existing build/source binding. A full build identifier is
not necessarily the CameraLinear writer's Software tag; M194 established that
the measurement writer can emit the package-only stamp.

Initially consume all five frames with explicit known identity placements.
The geometric reference index is a gauge choice, not a best-focus oracle:
neither a midpoint nor either in-focus layer supplies universal two-layer
truth. The existing consumer's `best` meaning original frame4 does not transfer
to this scene. Any later single-input comparator must name its original index
and disclose the local-zero probe seed, as M194b/d do.

## Coordinates and delivered-value convention

M194e's forward map is canonical-to-native. The production `WarpMap` is a
reference-to-source pull, so this is the compatible direction after converting
native coordinates to quad units. Do not invert it merely because the renderer
used its inverse to evaluate radiance. Identity in all five initial frames
avoids a fitted alignment claim; it does not commission arbitrary similarities.

For quad crop origin `(dx,dy)`, full-resolution output pixel `(u,v)` has native
canonical centre `(u+2dx,v+2dy)`. The crop is applied before pyramid analysis in
`extract_planes`; the writer receives compact planes and does not crop twice.
Use the actual pre-render domain, not a rectangle inferred from output width.
`CoverMode::Crop` may shrink even an identity map because the resampler's
coverage margin remains part of `cover_or_explain`. Record that actual result;
do not assume a64×48 TIFF or silently scale it back to that size.

The future bridge must separately declare WB and the merge's noise model;
M194e's noiseless emitter supplies neither a measured temporal noise law nor
camera WB calibration. An economical path commission can retain M194b/d's
explicit synthetic algorithm coefficients and f32 WB `[4/3,1,5/3]`, while
clearly recording that the input has no shot/read draw. That would exercise a
noise-gated algorithm on noiseless data, not prove its model matches measured
noise. Alternatively chosen coefficients require a prospective explicit plan;
do not obtain them implicitly through M194's generic profile-based fixture
helper. Use `NoiseModel::new` once, as M194b's `Inputs::noise` already does.

For CameraLinear, full-resolution MHC, exposure0, no auto-exposure, matrix,
tone curve or restoration, the existing writer normalizes black-subtracted
merged DN by `14848`, applies its declared f32 WB and encodes RGB16. Reading
`TIFF_u16 * 14848 / 65535` recovers quantized **post-WB DN**; subtracting512
again would be wrong. This scale is not electrons or linear-sRGB. The final
TIFF quantizer is `(x*65535+0.5) as u16` after clipping, distinct from M194e's
ties-to-even **input-CFA** quantization. Neither rule should be substituted
for the other. Compare actual writer values with independently transformed
references, including CFA/site factors, f32 WB and both quantization stages.

## Why64×48 does not reproduce the three-band experiment

`PlaneGeometry::from_active` gives32×24 quad pixels. The actual
`pyramid::level_sizes` stops before any reduced dimension falls below
`MIN_LEVEL_EXTENT=8`. With requested bands3 it therefore returns:

```text
32×24 -> 16×12; next8×6 is rejected
```

That is **one Laplacian band plus a base**, not three Laplacian bands plus a
base. Cropping can only reduce the available dimensions. Effective band count
also enters `MergeConfig::exponent_at`; this is not merely missing coarse
output rows with the same remaining weight configuration.

`gatefloor::Probe::run` measures at most
`min(4, sizes.len().saturating_sub(2))` bands. Here it is zero. The ordinary
fold's finite-prefix slice is empty, so `BandMerge::beta_for` uses its white
fallback. This is source-derived behavior, not a new measured floor result.
The known debug path separately indexes `self.beta[0]`; it must stay out of
this small-input bridge unless repaired and independently tested. An unused
observer flag or a fallback result must not be called a measured-floor check.

**DERIVED minimum for three realized Laplacian bands:** after three ceiling
halvings, `ceil(Q/8)>=8`, requiring each compact quad dimension `Q>=57`.
Thus114×114 even native dimensions, before coverage/crop loss, merely realize
the count:57→29→15→8.56→28→14→7 fails. This is a band-count minimum, not an
adequate quality field of view or an approved replacement for the fixed64×48
numerical fixture.

## Spatial support is a separate size requirement

The source uses five-tap binomial reduction, two-phase expansion and five-tap
smoothing of squared Laplacian coefficients; borders replicate. MHC's final
five-by-five stencil adds radius2 native pixels and uses mirror extension.
Coverage of resampler taps alone does not remove these analysis boundaries.

For a conservative per-axis bound in quad coordinates, conditional on fixed
per-frame beta and identity gather:

| Dependency | Radius in level0 quad coordinates |
| --- | --- |
| Gaussian level k from repeated reduction | `2*(2^k-1)` |
| Laplacian coefficient at level k | at most `6*2^k-2` |
| Its smoothed energy/weight | at most `8*2^k-2` |
| Expansion of that weighted band to level0 | adds at most `2*(2^k-1)` |

At the coarsest selected band k2, the combined bound is36 quad pixels per
side; the three-level mean-base route is28. The final MHC may read one adjacent
quad beyond the requested output site, giving a conservative37-quad/74-native
guard for this **identity-gather, fixed-beta local path**. No claim that every
tap has nonzero influence at every phase, or that a single-frame reconstruction
cannot cancel these dependencies. Different per-frame weights need not cancel
them. Nonidentity full-resolution gather requires its own additional mapped
resampler/MHC support; do not reuse this identity bound as a universal guard.

The actual measured beta also pools a crop-wide synthetic probe after mean
removal. That global scalar is domain dependent; a local filter guard alone
does not establish invariance to changing the whole analysis domain. The guard
calculation describes local convolution dependence, not a global proof that a
larger image leaves all estimates unchanged.

The old M194b/d320×240 input with actual compact142×106 quad crop realizes
`[142×106,71×53,36×27,18×14]`. It is therefore a useful prospective size to
reuse, subject to compatible new geometry. Under the conservative identity
bound, such an output has a136×64 native interior before any additional
nonidentity-gather allowance. Its old192×112 scoring ROI is **not** wholly
inside that stricter guard. Do not import the old mask as an independently
validated border-free depth-boundary ROI. The old finite-image comparison
remains its own result.

A later quality fixture must prospectively put its depth boundary, fixed
boundary band and flat controls in an adequately supported region, retaining
the whole-image and sparse-error readouts as well. Extending the64×48 scene
without moving its edge at x≈32 need not place the edge in that region. The
larger scene, edge placement, valid mask, independent numerical budget and
work ceilings are a new reviewed fixture, not a silent upscale, favorable ROI
selection or passing subset of the current numerical commission.114×114 alone
has no interior under the conservative three-band guard.

## Minimal future commission and the later quality experiment

The bridge commission needs only a bounded set of real delivered files:
all-five admitted inputs; actual domain/dimensions and normalization; an
unchanged-input byte companion; changed-output-setting/source controls; a
nonzero quad-crop address control; source refusal; and confidence reread/output
identity if confidence is supported. Existing M194/M194b controls are useful
starting points, but the new reader must reject stale and coherently rehashed
source/commission/map substitutions against its external authority. Keep
private API fixtures visibly separate from admitted M194e model data.

Record actual effective levels and floor fallback in that result. A64×48
successful path commission cannot adjudicate the M194d candidate, certify
three-band occlusion-boundary fidelity, measure temporal noise from five
different-focus frames, or license a physical/SOTA claim. No M194d mode switch
or new comparative population is needed just to show that admitted CFA reaches
the existing writer.

Only afterward should a separately registered larger fixture/noise population
compare fixed HardFloor and FloorPedestalV1 settings. It needs independently
commissioned model values, multiple independent noise realizations, the same
declared output grid, explicit ideal-pinhole versus attainable-control scope,
flat temporal noise, boundary fidelity and sparse adverse tails. These are
future requirements, not tests or measurements performed by this audit.

## Inspection record

Read both prior audits, M194b/d input/plan/render sources, production prepared
source/fold/writer, gatefloor, `pyramid::level_sizes/build/collapse/smooth5`,
full-resolution gather and MHC border handling. Commands were `rg` inventories,
bounded `Get-Content` source reads, `Get-FileHash` and `git rev-parse HEAD`.
One initial Windows `rg` glob-path request failed with error123 and was replaced
by explicit paths; no execution result was inferred from that search failure.
Inspection HEAD was `7d08462aa7b6ae5992976cf129baa8f16889aae5`; the workspace
is shared. Source hashes below identify the inspected bytes, not a new build.

| Source | SHA-256 |
| --- | --- |
| `crates/strehl-cli/src/merge_cmd.rs` | `ca829e45c7021c5c5df7b51da85859e3763a9a95d01d302a91ab7cd0687b2dcf` |
| `merge_cmd/known-scene-benchmark.rs` | `92febefaaae87849d689ac59390e8c0170a409f5ecf31f3f4102b5288537b5f7` |
| `merge_cmd/band-admission-benchmark.rs` | `d275b189d374117de2f6d5d9aa163417d675adba1820d96f42e9dfe0d322c2c3` |
| `crates/strehl-core/src/pyramid.rs` | `848b485271abc48ee496ee69d70a1e01f45074bfbccde7a7ca076ded90f77d9e` |
| `merge_cmd/gatefloor.rs` | `bcea35986c73011c20d872bddc9c0ef3ea9354101259bd3952c16976bb1c9496` |
| `crates/strehl-cli/src/image_out.rs` | `c1362363740cb0176985283455cd6ddef80479854b1bbc9f0396851c490f82b6` |
| `crates/strehl-core/src/demosaic.rs` | `425d6889485011cf6f2aaf57b0b873f15fd6ee3250853f3ba5f6540b496b3810` |

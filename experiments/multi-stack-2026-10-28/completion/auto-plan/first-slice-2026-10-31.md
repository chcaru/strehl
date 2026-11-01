# Automatic session planner: first slice (October 31, 2026)

Scope: the first engineering step toward the user's "hand it all to Strehl"
direction in [the handoff](../../../../docs/multi-stack-handoff.md). This adds an
automatic planning layer over the existing consumer. It is not the complete
automatic best-result workflow, and no photographic-quality claim is made.

## What the bug-3 regression case actually contains

MEASURED (`strehl session inspect`, metadata only, packaged CLI
`desktop-129ddfd67a3f75a5`) on
`C:/Users/chris/Pictures/Strehl/strehl-1793474770086-32624-1/session-manifest.json`:
all seven passes (1,650 frames) share ILCE-7CM2, FE 100mm F2.8 Macro GM OSS + 2X
Teleconverter, ISO 100, f/5.6, 200 mm, levels 512/16383, RGGB and one WB record.
Shutter is 1.6 s for 103--107 and 2 s for 100/102 (ratio 1.25, 0.32 EV). Body
serial is unavailable. Capture order: 100 (19:47), 102, 103, 104, 105, 106, 107 (21:38).

ARGUED from downscaled orientation previews (`rawpy` half-size, camera WB, no auto
brightness; mid-sweep frame per pass; local only under
`outputs/multi-stack/auto-plan-01/preview/`): 103--107 frame the whole weevil
with modest translation/magnification differences (105 visibly larger); 100/102
are close-ups of the elytra at roughly 2.5--3x the magnification. Equal focal
length metadata does not reveal this: macro magnification follows focus distance.
**The shutter refusal the user saw masked a multi-scale/framing relationship;
this case is not primarily HDR.**

## Implementation

- `SessionMode::Auto` (`"auto"`): desktop default for new sessions ("Best
  result"). The serde default for a manifest without `mode` remains Combine; saved
  manifests keep their recorded mode. One-pass Auto uses the unchanged ordinary path.
- `crates/strehl-cli/src/session-plan.rs`: after joint alignment, per-pass facts
  are planned against the anchor (explicit primary, else the geometry reference).
  Equal settings: combine at gain 1. Different shutter: held-out calibrated
  photometry (`calibrate_selected`, existing `hdr-spatial-cross-validation-v1`
  criteria), then the corrected gain, never a nominal fallback. Different
  ISO/aperture/decoded calibration, unknown shutter, refused calibration or no
  placed frame: the pass is **excluded with a stated reason** rather than failing
  the session. `plan.json` and a log summary record every decision;
  `render-report.json` records `excluded_passes`.
- Auto uses the existing noise-gated repeat grouping (as Repeat/HDR and any
  primary-target Combine already do). ARGUED from product17 grouping evidence;
  not separately measured here.
- Unchanged: within-pass setting changes and cross-pass camera/lens identity
  still refuse (`validate_capture_headers`). `session-align.rs` is untouched, so
  archived map bindings are unaffected.

## Verification

All runs used `target/release/strehl.exe` built from this working tree
(SHA256 `f490d275f58624887c8f97b6cc6977daa5959d4fda7382c11019b718701deead`,
fresh `Compiling` of all crates, `cargo build --locked --release -p strehl-cli`),
16 threads, 16 GiB budget, idle host (~45 GiB available). Inputs were SHA256-checked
copies outside the capture tree; receipts and full logs are local under
`outputs/multi-stack/auto-plan-01/`.

| Check | Result |
| --- | --- |
| `cargo test --locked -p strehl-cli -p strehl-ui session -- --test-threads=4` | VERIFIED: freshly compiled; 164 CLI + 66 UI passed, 0 failed (4 new planner tests; 2 UI guard tests updated for Auto). |
| Negative control: 107 + 100 subsets (30+30, stride 10), mode Combine | VERIFIED: exit 1 in 1.3 s, `combined passes have different shutter times; use HDR or aligned layers` (old behavior retained). |
| Same inputs, mode Auto | VERIFIED: exit 0, 76.8 s, peak private 5.50 GB. 100-2s placed 0/30: all 49 cross probes `CoarseStageFailed`. Plan excluded it with a reason; anchor rendered. Exposure calibration was therefore **not exercised on real data**. |
| Five 1.6 s passes (107/106/105/104 stride 10, 103 stride 2; 120 frames), Auto | VERIFIED: exit 0, 152.4 s, peak 6.10 GB. 107+106 joined (265 accepted cross edges); 105/104/103 placed 0, every cross probe from 107 `CoarseStageFailed` (level 0 or 1). Plan: 2 of 5 contribute; three exclusions stated. Before this change the session would fail. |
| No-regression: 107+106 subsets, Auto vs fresh Combine (primary 107) | VERIFIED: 735 identical edge transforms; photograph (uint16) and linear master (f32) 4592x6892x3 **bit-identical**, all finite. |

A saved alignment cannot be shared across Auto/Combine manifests: the binding
includes the spec mode (`alignment envelope does not match ... session layout`);
the equality control therefore ran Combine fresh and compared alignment too.

Not done: complete-image photographic comparison against single passes; the full
1,650-frame session; HDR-vs-Auto equality on a pair whose shutter-differing pass
actually aligns; desktop exercise of the new default; strict clippy.

## What this establishes and the next decision

The planner converts whole-session refusals into explained per-pass fallback
without changing equal-setting output. For the user's actual seven passes,
though, the dominant blocker is **cross-pass registration across magnification
and framing changes**, not exposure: the coarse cross-probe stage fails for every
pass but 106. The next substantive work is a scale/translation-robust coarse
cross-pass initializer (then direct pairwise fits in the global solve as now),
followed by a multi-scale consumer able to insert close-up detail (100/102) into
the whole-body canvas. Changing `session-align.rs` invalidates archived map
bindings (handoff: archived17 hash) and needs fresh controlled maps.

## Second slice: wide-baseline registration and the pose-change gate

Source: commit `fc7eb5a74`; release `strehl.exe` SHA256
`fa78fa817a6d019f435a5d53e75735524eafdf9004bceb0cd988beb6e5dae954` (fresh
`Compiling`, built from that tree). The later rustfmt commit `1d1966f29` changes
no file hashed into a binding and no behavior.

**Implementation.** `strehl-core/src/align-global.rs` proposes reference->moving
similarities by masked FFT NCC (Padfield form, gain/offset invariant) over
magnification up to 4x either way, +-12 deg and all translations, coarse (128 px)
then local refinement (256 px). Proposals never become placements:
`session-align.rs` searches only passes with no accepted cross probe, keeps the
first candidate a direct seeded guide refinement confirms, re-measures that
pass's refused probes and candidates from it, and tiles the more magnified frame
for such pairs (`guide-wide`/`native-wide` receipts). Ordinary passes keep the
old path. Passes joined this way carry `cross_support_ratio` (median native
cross-edge tiles / the pass's median intra-edge tiles) and `relative_scale`;
below 0.5 they are `geometry_consistent: false`. Auto excludes those and passes
beyond x1.5 magnification; fused manual modes refuse them.

**Unit evidence.** VERIFIED: 5 new core tests on analytic value-noise scenes
(rotated 2.6x close-up and its inverse within 8/4 moving px, partial overlap with
gain/offset change within 4 px, unrelated scene NCC < 0.6 vs true > 0.9, flat and
invalid-bound refusal, FFT vs direct circular correlation). Breaking the swapped
inversion fails the close-up test (mutation check). After the slice: 55 core
alignment, 165 CLI and 66 UI session tests pass; clippy reports nothing in the
changed files.

**Five-pass subset (107/106/105/104/103, 120 frames).** MEASURED: before the
gate, 120/120 placed in one component; seeds x1.217/x1.229/x1.242, about -1.9 deg;
the true candidate scored NCC 0.93 vs 0.61--0.66 for alternatives; about 7 s per
search. Orienting wide pairs on the magnified frame lowered cross-edge median RMS
from 3.3--4.5 to 2.9--3.1 plane px (intra 2.8). **But the fused photograph
ghosted**: frozen-gain (6.081, sRGB) overview and native 400 px crops showed
patchwork bands and displaced hairs absent from the 107+106 result. Residual
fields after placement (frame 15 vs mid frames; phase correlation on 192 px tiles;
commissioned on a known (+7,-3) shift, recovered exactly): 106 control median
2.0 px, similarity residual 1.5 px; 104 median 26.6 px, similarity and affine
residuals about 23 px; 105 no usable tiles. A red/cyan overlay showed legs aligned
but wing-cover bands offset non-uniformly. ARGUED: the specimen's pose changed
between sessions, so one 2-D placement per frame cannot register it. Support
ratios: 106 1.17; 105/104/103 0.16/0.28/0.15. With the gate: 2 of 5 contribute,
three excluded with the ghosting reason.

**Close-up subset (107 + 100).** MEASURED: no confirmed seed; all candidates near
x0.27 (the wrong direction) at NCC about 0.70, comparable to false candidates.
The true roughly 2.7x relation is not found at 128/256 px search sizes. Even if
found, the earlier sessions likely share the pose change, and Auto excludes
magnifications beyond x1.5.

**Complete regression manifest (7 passes, 1,650 frames), Auto.** MEASURED: exit 0,
43.6 min, sampled peak private 10.79 GiB, 16 threads, cache on D:. 1104/1650
placed; 105/104/103 joined by wide seeds and excluded (support 0.18/0.16/0.15);
102/100 not joined. Fused 598 sources (107+106) in 475 groups, 6892x4596 canvas,
finite master. Author review (not independent) of the frozen-gain overview and two
native crops: coherent subject, no ghosting or seams.

**Still not established.** Any gain from the fused 107+106 result over 107 alone
(no single-pass comparison yet); use of pose-changed passes (needs locally
deformable registration with its own validation); close-up insertion; cross-ISO
or aperture pooling; independent review.

## Third slice: bug-4, per-frame photometry and lighting layers

Input: `D:/personal/macro/insects/bug-4` (read-only), five passes 100/102/103/104/105
(279/299/299/299/55 frames; ISO 100, f/5.6; 0.625/0.5/0.4/0.33/0.33 s), manifest
`outputs/multi-stack/bug4-01/manifest-auto.json`, cache `D:/codex-work/bug4-01/cache`,
32 threads, 32 GiB limit. Builds are dirty trees on `7baad0c99`; final release
`strehl.exe` SHA256 `cc7a7aaf20197ecc63e0223c197e600dfd122f53976a92911091394407c28950`.

**Registration.** MEASURED: before this slice 102/103 intra-pass edges failed
(trace: coarse level 1 correlated 7 tiles where 8 were required). An identity-seed
retry for intra-pass pairs refused by the coarse ladder, and a contrast floor
scaled to the pass's signal level, placed 1,231/1,231 frames in one component.

**Photometry.** `session-frame-photometry.rs` solves log brightness per frame from
block-mean ratios over native-confirmed overlaps (Huber, then redescending
rejection; conjugate gradient). MEASURED: residual 0.0004 ln over 11,042 overlaps;
anchor 102 itself drifts x0.80--1.26 within the pass. Cross-pass brightness ratio
varies 27--35% across the overlap (intra about 1%): the lighting changed shape.

**Pose gate.** `session-geometry-check.rs` measures remaining local displacement
(48 px tiles, NCC, +-10 px) of each pass's focus-nearest frame against the
reference frame after placement. Synthetic: consistent geometry under a shading
ramp < 0.5 px; a bend up to 8 px reports median > 2. MEASURED on bug-4: 100/103
0.0, 104 1.0, 105 1.4 guide px (bar 1.5); the support proxy had flagged 104/105
(0.38/0.37). MEASURED on the bug-3 five-pass subset (`manifest5-auto.json`,
release SHA256 `4c3fb4e64eedc7201b2c8453e0661fa31caed8cb8ab4603d2ecd0937c434613f`,
32 threads, 183 s, `out5-residual-01`): 106 median 0.0 (86 tiles), combined;
pose-changed 104 median 4.0, p90 6.1 guide px (18 tiles), excluded by the residual;
105/103 had too few usable tiles and fell back to support (0.16/0.15), excluded.
Plan reasons now name the residual when it was measured.

**Lighting fusion.** Each lighting group is merged separately (merged CFA planes
before development) and blended through Laplacian pyramids. MEASURED against the
anchor-only developed photograph (identical frozen display transform, native
400 px crops; author review, not independent):

| Arm | Weights | Result |
| --- | --- | --- |
| v1 | Mertens detail x exposure x saturation | Hazier (-9% subject high-pass), glow beside the silhouette, hard seam at a layer coverage edge |
| v2 | Anchor-first pooled detail, feathered coverage, uncovered pixels filled from the anchor | No seams; flat-region noise halved but background lifted (ring mean 0.037 -> 0.070) |
| v3b | + detail-band consistency gate; coarse tone from the anchor except where clipped | Ring unchanged, DoG energy +2--5%; developed photograph shows dark holes at speculars, softer grain |
| v4 | Detail-only; coarse tone always the anchor's | Same holes and softness as v3b |

The band-energy gains are not evidence of quality (mixing inconsistent content
also raises energy). ARGUED cause of the remaining defects: a layer's fine
Laplacian bands are relative to its own local brightness, so they do not sit on the
anchor's base where lighting differs. Decision: `lighting_layer` passes are
reported and not consumed unless `--lighting-fusion` is given. VERIFIED: default
Auto on bug-4 (`out-auto-06`, 352 s) is bit-identical to the anchor-only render
(`out-auto-03`).

**Tooling.** `STREHL_LIGHTING_DUMP` writes captured group planes;
`STREHL_LIGHTING_FROM_DUMP` (optionally `STREHL_LIGHTING_DUMP_GROUPS`) develops
from them without re-merging; the ignored test `lighting_fusion_from_dump` fuses
a dump offline in about 3 s. Alignment and render cache bindings now hash
`align-global.rs`, `session-frame-photometry.rs`, `session-geometry-check.rs`,
`session-plan.rs` and `session-lighting-fusion.rs` (previously edits to them could
reuse stale caches).

**Checks.** 177 CLI session tests and 1,036 UI tests pass. The four fusion tests
include a seam test that fails when the anchor fill is removed (mutation check).
`cargo test -p strehl-cli --lib`: 390 passed, 8 failed, all in `merge_cmd`
experiment controls needing private corpus or output-root setup; this slice does
not touch them. Clippy with toolchain 1.98.0 reports nothing in changed files and
existing findings in `image_out.rs`, `merge_cmd.rs` and frozen experiment sources.

## Fourth slice: light superposition and pose layers (2026-11-01)

Commit `f967526ab`; release `strehl.exe` SHA256
`e124d4b97484088bfd8016c70097708aec4758693dd195b28d4deae9f39ef41a` (the commit
adds only a clippy type alias after this build). 32 threads, 32 GiB limit.

**Diagnosis.** MEASURED on the bug-4 dump: group 4 (pass 105) is out of focus;
the other lightings differ mainly in where speculars fall. Tile NCC on
band-passed log brightness found residual misregistration between merged groups
after the joint solve: median 0.78/0.80/2.62 plane px (p90 1.1/1.4/4.9) for
100/103/104. Averaging without registration measurably softened hairs
(Python prototype, `nowarp` arm).

**Method.** Light adds linearly, so equal-weight averaging of brightness
normalised lighting groups is the "every lamp on" image. Per layer: defocus
gate (fine band sigma 0.7 / coarse band sigma 2.8 contrast ratio against the
anchor; lighting scales both, defocus only the fine; drop below 0.75 or fine
ratio below 0.3); coarse-to-fine dense residual field (quarter-resolution seed
search, full-resolution refinement, neighbourhood-median outlier rejection,
smooth fill) and bicubic warp; uncovered canvas predicted as anchor x smooth
per-channel ratio, with a 24 px coverage feather; anchor near-clipped
highlights kept. Pose layers additionally yield to the relit anchor where the
smoothed log difference exceeds 0.1--0.25, with the ratio refitted on agreeing
pixels.

**Tests.** Six fusion tests; mutation checks: removing registration fails the
misregistration test, removing both fill and feather fails the seam test,
removing the highlight keep fails the highlight test, removing the pose gate
fails the ghost test (ghost error 1.81). The seam test first asserted equality
with full coverage far from the edge; a smooth ratio cannot extrapolate a
lighting ramp, so it now asserts continuity across the edge. 180 CLI session
tests pass.

**bug-4** (`out-auto-08`, 2,994 s including a one-off re-alignment after the
cache-key change; peak RSS 26.9 GB). Plan 5 of 5. MEASURED: residual
0.78/0.81/2.60 -> 0.13/0.09/0.30 plane px after warping (same estimator:
convergence, not independent accuracy); 105 dropped (fine/coarse 0.38).
Against the anchor-only photograph on one frozen display transform: background
high-pass SD 135.5 -> 104.6; mean -7% (darker speculars averaged with other
lights). Native 400 px crops (spec, c0, glow, head, hairs; author review, not
independent): hairs and edges as crisp as the anchor's, specular texture
intact, no holes, haze or seams, more even light at the head. The offline v5
development (`out-dev-v5`, single-level registration) differs from
`out-auto-08` by mean 7/65535.

**bug-3 seven passes** (`out7-auto-02`, 2,858 s). Plan 5 of 7: 107 anchor, 106
combined, 103/104/105 pose layers, 100/102 unplaced. MEASURED: 105 and 103
dropped as defocused (0.43, 0.22; their separate merges are visibly blurry),
104 superposed with residual 11.16 -> 0.87 plane px and agreement 0.30 (6.9%
of the canvas). No ghosting in native crops at the largest changes; the canvas
is 4 px smaller than `out7-auto-01`, so pixel differences against it are not
meaningful.

**Cache identity.** Restoring sources with `git checkout` converted them to
CRLF and changed every include_bytes hash, forcing a full re-alignment. The
alignment binding and the consumer's alignment and renderer keys now normalise
CRLF to LF (other hashed sites, such as mosaic and transfer caches, do not yet).

**Open.** Why some separately merged passes come out blurry (bug-3 103/105,
bug-4 105) is not diagnosed; close-up passes are still unplaced.

## Fifth slice: local sharpness gate and desktop integration (2026-11-01)

Commits `385e28956` (local gate) and `a8706839a` (desktop, report fix). Release
`strehl.exe` SHA256 prefix `23adf74311a8edef`.

**Blurry layers diagnosed.** bug-3 103 has 22 frames and 105 sits at x1.21
magnification; bug-4 105 has 55 frames. Their separate merges are blurred
because the passes do not span the subject's focus, not because of a merge
defect. Such a pass is still sharp over the depth it covers.

**Local gate.** Per pixel, the layer's fine (sigma 0.7) over coarse (sigma 2.8)
band contrast, relative to the anchor's and pooled over 24 px; low-structure
areas stay eligible; canvas borders (clamped filters read as sharp; found by a
failing test, all 2,166 false pixels within 40 px of the edge) are not judged.
Test: a layer sharp left and blurred right keeps the anchor's fine detail on the
right (0.61 without the gate: mutation check) and halves noise on the left.
MEASURED on dumps: bug-4 layers 99--100% locally sharp, 105 still dropped
(no usable fine contrast); bug-3 103/105 blurred throughout. Gate cost under 4 s.

**Desktop.** The saved-session view lists each pass's role and outcome from
`plan.json` and `render-report.json` (alignment, sharpness, coverage,
agreement, or the reason it was not used). Best result has a "Combine other
lighting and moved poses" control (`--anchor-lighting-only`), saved in the
recipe and available to agents; the agent `create_session` schema lacked the
`auto` mode and now has it. VERIFIED: `out-auto-09` (937 s, cached alignment)
imported into a headless desktop through `scripts/strehl-control.py`, and an
offscreen GPU screenshot shows the contributions. Exercising the app found that
layered reports lacked the recipe fields an import requires; fixed. Evidence
outputs now set layers aside with a recorded reason instead of failing.
1,037 UI and 181 CLI session tests pass; UI clippy clean.

**Extra detail: assessment.** ARGUED from the decision record and these runs:
(1) deconvolution is bounded at the apertures used (MTF at Nyquist is zero at
f/8--f/11; unguarded Wiener loses to selection), so restoration is not the
lever; (2) group-level shift-and-add would work on already resampled merges and
promises little; (3) the real sources are magnification (bug-3 100/102 close-ups,
unplaced: no confirmed wide-baseline seed despite a 4x scale range) and
multi-observation original-CFA reconstruction in the core gather, which the
architecture names as required and which an earlier single-frame sampler failed
for neutral-detail loss. Neither is started.

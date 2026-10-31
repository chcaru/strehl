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

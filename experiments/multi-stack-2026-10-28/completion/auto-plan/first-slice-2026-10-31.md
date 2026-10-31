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

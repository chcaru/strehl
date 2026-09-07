# M194g bridge command and private-control proposal

2026-09-07. Source/control design only. Root freezes exact executable, source
set, original commands and all external pins before any compilation/test/render
is accepted as evidence. The new Rust child is
`crates/strehl-cli/src/merge_cmd/noise-pupil-bridge.rs`, included under the
existing test-only `known_scene_benchmark` module. The old M194f child is
unchanged. This source author does not independently verify the bridge.

## Entry and fixed environment

Use a new root-owned test build/copy record with actual `Compiling strehl-cli`,
the compiler-reported test executable and actual original/copied bytes, hashes
and complete source include closure. No M194f build receipt is relabeled.
Normal binary filter prefix:
`merge_cmd::production_truth::known_scene_benchmark::noise_pupil_bridge`.
The exact nesting is checked against the compiled test listing before commands
are frozen. A missing filter that executes zero tests cannot pass.

All invocations require `RAYON_NUM_THREADS=2`, `STREHL_PYRAMID_WORKERS=2`,
`STREHL_DEFECT=off`, `STREHL_FIX_CA=off`, `STREHL_FULLRES_GATHER=1`.
Other STREHL overrides are cleared. In particular, measured-floor white/debug
and floor-scale overrides are absent. `STREHL_M194G_BRIDGE_` is the sole new
namespace; options below are its exact suffixes. No exposure or confidence
switch exists, so those foreign options refuse rather than silently change
the fixed CameraLinear/exposure0/RGB-only path.

The intended `m194g_noise_production_bridge` ignored test supports:

- `MODE=plan|render`, `NOISE_ADMISSION=absolute-path`,
  `NOISE_ADMISSION_SHA256=external-independent-pin`;
- `SCENE=textured|flat`, `SEED=noise-off|701|709|719|727|733|739|743|751`,
  `SUBSET=all|first|last`, `ADMISSION=hard-floor|floor-pedestal-v1`,
  `OBSERVER=off|count|placebo`;
- `PLAN=absolute-new-plan-path`; render additionally requires
  `PLAN_SHA256=external-pin`, `OUTPUT=absolute-new-tiff`,
  `RECEIPT=absolute-new-receipt`.

Endpoints require textured/noise-off/HardFloor. Planning derives the selected
files from the actual admitted tuple and streams all90 declared hashes; it
does not decode a stack. Both phases reopen the actual authority and children.
Rendering compares the full trusted saved plan to the newly derived plan.
Successful pixel receipts say `COMPLETE_RGB_UNVERIFIED`, because independent
TIFF and command-log checks still have work to do. No noise-file or quality
authority is emitted by this adapter.

## Private schedule and witnesses

One nonignored private-module invocation executes exactly six tests, with
`--test-threads=1 --nocapture` and a new namespaced `PRIVATE_OUTPUT` directory:

1. `m194g_private_source_rails_and_fault`: exact decoded0/511/512/15360 at
   independently named sites; actual same-length changed payload fails its
   old hash, a rehashed15361 then fails the rail boundary. Index3 succeeds
   before a named second fault-hook attempt refuses; successful observer counts
   do not include refusal. This test distinguishes fault-hook attempts from
   the earlier ordinary decode.
2. `m194g_private_bounded_json_paths_aliases`: inclusive limit and limit+1,
   duplicate JSON keys, traversal/absolute/Windows drive paths, two distinct
   equal-byte files, and a real hard link that is rejected as the same file.
3. `m194g_private_settings_geometry`: actual Crop/level-size constructor,
   both endpoint crops, original4/local0/probe0, invalid seeds and endpoint
   combinations, actual selected admission mode and retained unsupported
   CameraLinear exposure refusal.
4. `m194g_private_manifest_schema_tuple_controls`: complete private18×5
   descriptor companion;24 changed schema/type/geometry/noise/WB/seed/shape
   cases, missing bundle and persisted/reopened restored companion. These
   descriptors have nonexistent private authority paths and cannot authorize
   intended input. Add the accepted intended-reader90-row contract: ten
   status/type/association/tuple/control/closure faults and restored companion;
   actual row-to-file association and extrema faults use bounded real private
   CFA bytes.
5. `m194g_private_ledger_changed_input`: actual first read and final check,
   same-length file mutation, coherently rehashed second-read refusal and fresh
   restored read. No old authority ledger is reused after its failed check.
   Absolute/new output and casefolded alias controls follow; a real same-length
   output mutation after receipt persistence reaches the actual publication
   failure path. A preexisting rejected-path sentinel forces a secondary
   retention error, while the original output-change error and revoked receipt
   must remain visible. The restored output gets a separate successful private
   publication companion.
6. `m194g_private_actual_plan_controls`: actual `plan` constructor, disk reopen,
   wrong crop/original/probe/admission/exposure/WB/frame-WB/noise/normalization
   mutations, exact full-plan comparison and original4 endpoint companion.

A separate ignored `m194g_private_production_outputs` invocation emits exactly
six private320×240-source RGB TIFFs: constant off/count/placebo, affine,
affine with64 DN added to both greens, and the same constant under
FloorPedestalV1. All five input frames are identical for each private field.
The constant channel signals are1800/2000/2400 DN above black; affine fields
are R=`1500+2x+y`, G=`1800+x+3y`, B=`2300+3x+2y`. These are defined at native
photosite coordinates before WB. The actual source/probe/WB/writer are used.
The first three complete TIFF bytes must match, actual hooks must be0/5/5 and
collected per-frame counts0/1/0. The changed-green output must differ by actual
pixel hash; an independent TIFF oracle, not that movement alone, determines
the correct change. Actual per-render stderr remains the measured-floor
witness. A final attempted render fails decode at local3 on its first attempt,
requires counts `[1,1,1,0,0]` and produces no TIFF or successful receipt.

The independent reviewer rechooses coordinate/colour sites and checks all six
actual TIFFs, four levels, measured-prefix/count logs and whole plan/config.
No sharpness or quality metric is introduced here. Record every actual first
compile/control failure and its source revision; do not replace failed records.

## Intended commission after noise-file admission

Proposed eight distinct population settings: both scenes × noise-off/seed701
× HardFloor/FloorPedestalV1, all five inputs and observer off. Add count and
placebo repetitions of the textured/seed701/HardFloor setting, and two
noise-off textured HardFloor endpoints. This is12 intended RGB outputs,
separate from six private outputs and the later38-output quality matrix.
Root may choose this finite set before its release; it is not executed or
admitted by this proposal. Every render needs its own externally pinned plan.
Independent read must reject altered/missing/duplicate/nonfinite floor log
records, wrong contributing counts, rehashed false plan/TIFF associations,
failed/partial command records, false output dimensions and config overrides.

Root accepted the intended90-file reader's concrete closed child contract in
`next-noise-files-verifier-design.md`. The bridge now checks its complete
ordered90 rows, all passing controls and matching four upstream refs; it
reopens the child's source/input bindings and associates each CFA/audit by
resolved path/hash/length, with actual extrema checked while bytes are live.
The genuine float gate alone, or the1186-private-noise PASS, cannot bypass that
boundary. No actual90-file admission yet exists for this bridge to consume.
All bridge build/test/run commands remain withheld pending root source/command
release; no source-level PASS is reported as executed evidence.

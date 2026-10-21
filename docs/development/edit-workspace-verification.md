# Edit workspace verification — October 20, 2026

This revision separates immediate photograph development from capture-range
repairs, makes region geometry editable, and adds an experimental image-guided
Magic lasso. It also corrects Windows display queries during monitor changes.

## Interaction controls

The tests exercise pointer/key events through the actual egui controls. Inputs
that would fail the old implementation include double-clicking a slider track,
blurring its numeric editor after reset, reopening an empty resized Regions
shelf, and pressing Escape while a freehand boundary is unfinished. Geometry
controls additionally require a real move/resize/vertex operation, one Undo,
and restoration on cancellation. Text-field Escape must not also cancel canvas
state. Regions must remain visible when the window loses focus.

Paint-time controls preserve evidence: opening Source repair with a missing or
shorter bracket must preserve its stored range; opening Display & export must
preserve valid imported values below 203 or above 4000 nits. Numeric field state
belongs to a photograph and selected region. The continued-typing control changes
the scope while a number owns focus, then types another digit: without isolation
the old text edits the new scope; with isolation its value remains unchanged.
The earlier blur-only hypothesis did not reproduce and was not claimed as a bug.

Worker publication checks the photograph, recipe, selection scope and operation
generation. A cancelled or superseded Magic selection cannot appear later.
Starting Magic supersedes an older Adaptive operation; Adaptive cannot start
while Magic is working. This is distinct from editing or autosaving the recipe.

## Photo and selection review

The [Adaptive development record](adaptive-development.md) contains the complete
photographic comparisons, exact zero-amount controls, local-support check and
bounded analysis measurements. These are editable starting points, not learned
AI, restoration of clipped texture or a universal quality claim.

Magic selection tests pair contrasting objects with flat, gradient, noise,
concave-enclosure, hole and HDR controls. The initial real garnet selection was
rejected: it retained two peripheral patches while omitting the main reflection.
That rejected result is retained locally as evidence of the failure. A successful
synthetic fixture alone was not treated as proof that the tool was useful on a
photograph. The revised result contains the main reflection and two separate
small bright patches, accepted independently after whole-scene and detail
review. The final receipt reproduces those reviewed contours exactly. A tested
insect enclosure remains an explicit no-selection case. Selection is bounded and
contrast based; it does not identify object semantics, and the current recipe
cannot encode holes. A supported high-contrast core may replace a hole-bearing
candidate; the status discloses this and small-gap closure.

The final garnet receipt sampled a 289 × 384 grid (348,704 source-pixel samples)
and the insect receipt a 384 × 384 grid (463,264 samples), rather than traversing
the entire 7032 × 4688 photograph. Both original TIFF hashes remained unchanged.
The receipts are local at `outputs/magic-selection-review`; debug worker timings
there are not optimized interaction-latency measurements.

## Automated checks

**VERIFIED:** The fresh desktop suite passed 789 tests, with 13 hardware/manual
tests left for explicit invocation. The editing crate passed 40 tests. After
the final lint-only refactor, the 31 editor/geometry controls were rebuilt and
passed again. Four real-GPU tests were run explicitly and passed: float photo/UI
white with an SDR negative control; independent crop/peak/alpha/transfer checks;
registered SDR texture lifetime; and actual rejection of a delayed response
from a monitor the window has already left.

Strict all-target Clippy passed for the changed UI/editing crates using the same
`--no-deps` scope as CI. An initial broader invocation encountered existing
engine lint errors; it is not reported as a clean workspace-wide lint result.

```powershell
$env:CARGO_TARGET_DIR = 'target/progressive-photo'
$env:CARGO_BUILD_JOBS = '4'
cargo test --locked -p strehl-ui -- --test-threads=2
cargo test --locked -p strehl-edit --all-targets
cargo test --locked -p strehl-ui edit_workspace:: -- --test-threads=2
cargo clippy --locked -p strehl-ui -p strehl-edit --all-targets --no-deps -- -D warnings
cargo test --locked -p strehl-ui native_float_pixels_ui_white_and_sdr_negative_control -- --ignored --nocapture
cargo test --locked -p strehl-ui independent_crop_peak_alpha_and_sdr_encodings -- --ignored --nocapture
cargo test --locked -p strehl-ui registered_sdr_images_preserve_color_crop_alpha_and_deferred_lifetime -- --ignored --nocapture
cargo test --locked -p strehl-ui actual_poll_discards_stale_monitor_reply_before_publishing_display_state -- --ignored --nocapture
```

## Native isolation

Native checks launch owned windows using copied saved photographs and isolated
catalogs. They do not change Windows HDR settings or operate the user's open
Strehl window. Source-photo, saved-log, recipe and user-catalog hashes are checked
afterward. The photographed HDR display report is separate from input origin:
an old SDR TIFF does not acquire retained scene-linear highlights merely because
the monitor supports HDR.

Native layout screenshots are SDR proxies. They can establish layout and
control placement; they cannot establish HDR luminance. GPU readback controls
and actual window/monitor transitions cover those separate implementation paths.

**VERIFIED on Windows:** The final optimized executable
`f74c37e2501877b4c96dec3df201141becab87881695f9517603c2572641f6a8`
(29,083,648 bytes) completed repeated primary-HDR → secondary-SDR → primary-HDR
moves with both an old SDR TIFF and a scene-linear master. The SDR photograph
remained SDR on both monitors. The master changed presentation generations and
published an error-free patch covering the actual painted 3× crop after each
move. No stale monitor response reappeared during the additional heartbeat check.

The primary display reported 240-nit SDR white and 499.3-nit peak; the secondary
reported SDR. Observed cross-monitor state changes took 63–79 ms; the master's
replacement patch was settled within 219–235 ms. These are MCP-inclusive observed
upper bounds from one machine, not input-to-photon latency or physical luminance
calibration. The published 1024 × 672 patch used stride 4 for this 1440 × 940
window's demand; this run does not claim source-pixel stride-1 inspection.

Both isolated app windows closed cleanly, logs were empty, protected file hashes
matched, and the user's existing Strehl window rectangles were unchanged.
Receipts are at `outputs/hdr-monitor-review/native-{sdr,hdr}-final/receipt.json`.
The commands used the owned-window harness and copied fixtures:

```powershell
python outputs/hdr-monitor-review/check-native-transitions.py --binary outputs/strehl-editor-preview/Strehl.exe --run outputs/feature-validation/insect-run --catalog outputs/feature-validation/state/Strehl/projects.json --output outputs/hdr-monitor-review/native-sdr-final
python outputs/hdr-monitor-review/check-native-transitions.py --binary outputs/strehl-editor-preview/Strehl.exe --run outputs/feature-validation/insect-run --catalog outputs/hdr-monitor-review/linear-master-catalog.json --master outputs/quality-october20-slide/repair/linear-master.tiff --output outputs/hdr-monitor-review/native-hdr-final
```

**VERIFIED native regional editing:** The MCP path selected an insect reflection,
applied Highlights −25.7324 to that region, preserved global/HDR controls, an
unrelated local adjustment and the source-range instruction, and changed the
actual bounded preview. A disjoint crop remained byte-identical. One Undo and
Amount zero restored the baseline PNG exactly; Amount 0.4 → 1 reused the frozen
treatment. The diagnosis reported 18.7% of sampled SDR pixels with a channel near
stored white, without claiming recovered texture. The first broader pale-wing
enclosure legitimately received no treatment and remains a negative example.

The isolated native check also rejects stale revisions and unsupported intents.
The setup comparison was corrected for omitted optional fields and f32 JSON
round trips; these were harness mismatches, not application mutations. Original
files and catalog hashes remained unchanged. This bounded preview check is
separate from the complete-image regional support control in the Adaptive record.
Receipt: `outputs/adaptive-native-review/final-2026-10-20-d/receipt.json`.

```powershell
python outputs/adaptive-native-review/check-native-highlights.py --binary outputs/strehl-editor-preview/Strehl.exe --run outputs/feature-validation/insect-run --catalog outputs/feature-validation/state/Strehl/projects.json --output outputs/adaptive-native-review/final-2026-10-20-d
python outputs/edit-workspace-review/capture-layout.py outputs/strehl-editor-preview/Strehl.exe --size 1200x800
```

The final native layout capture was reviewed after the optimized build: tool
labels have separate cells, controls use aligned numbers and thin rails, Select
is active on entry, the Regions shelf remains anchored, stored region outlines
remain visible, and the completed-stage blocks no longer consume the editing
photo's vertical space. The photograph's aspect ratio is preserved. The capture
and its original-data hash receipt are in `outputs/edit-workspace-review`.

## Matched pan CPU check

**MEASURED:** Four isolated native runs used the previous optimized app (A,
SHA-256 `570726353f6c97cc920e89c6e14d8733d2c9775b2ca171587643e44c4875ab4c`)
and this revision (B, hash above), in A/B/B/A order. Each opened the same copied
33 MP insect run and recipe at 2600 × 1300, then performed the
same 100 paced pan commands at 8×. No compilation or other QA process ran during
these measurements. Each command had to change the actually painted aperture.

Independent review caught that `--agent` overrides `--edit` in both executables.
These first receipts therefore measure the Agent pane, despite the requested
launch flag. The crop and CPU evidence remains valid for that pane; it cannot
establish performance with Edit visible. Direct pane visibility must be witnessed
before claiming an Edit-workspace comparison.

The audit now requires direct before/after pane witnesses tied to the owned
process, binary, launch nonce and phase. Ten harness controls passed, including
wrong-pane, stale-launch and external-file rejection. A genuine baseline Edit
pane was observed, but the first follow-up stopped before timing because the
desktop capture was JPEG and the initial witness validator accepted only PNG.
Both native formats are now accepted. A later owned-window activation failed
in the desktop helper (`foreground window did not report a process id`) after
its prescribed fresh-selection recovery. Input attempts stopped; no corrected
Edit-pane ABBA result is claimed. The new app's separate native Edit layout
capture above remains valid. This limitation concerns the measurement setup,
not an observed application crash or measured editing slowdown.

| Arm | Frames | Framework CPU p95 (ms) | Summed framework CPU (ms) | UI update sum (ms) |
| --- | ---: | ---: | ---: | ---: |
| A1 | 672 | 4.648 | 2644.24 | 1473.01 |
| B1 | 669 | 4.590 | 2631.70 | 1463.61 |
| B2 | 672 | 4.662 | 2652.75 | 1459.08 |
| A2 | 668 | 4.672 | 2654.05 | 1472.65 |

The observed ranges overlap. The minimum summed framework work differs by less
than 0.5%, so this is treated as essentially flat CPU cost, not a speedup. Both
per-frame and total work are reported to expose extra redraws. Every trace has
complete frame coverage, unchanged development recipes and protected-input
hashes, and a final published stride-1 detail patch. The comparison is relative
to the preceding progressive-display build; it does not erase that feature's
earlier measured cost against the older coarse-preview baseline.

This measures main-thread work and renderer submission through a paced MCP
trace. It does not measure physical pointer latency, GPU time, FPS, Magic worker
latency, or performance under every photograph/recipe. A universal zero-regression
claim is not established. Receipts, raw samples and painted apertures are at
`outputs/edit-workspace-review/performance-{a1,b1,b2,a2}/receipt.json`.

```powershell
python scripts/test-display-performance.py -v
# Original commands used the initial harness that merely passed --edit.
# The current harness pauses for direct pane witnesses before/after timing.
# Use fresh output directories; never reuse the original evidence directories.
python scripts/check-display-performance.py --binary outputs/strehl-hdr-preview/Strehl.exe --run outputs/feature-validation/insect-run --catalog outputs/feature-validation/state/Strehl/projects.json --output outputs/edit-workspace-review/performance-a1 --edit --motions 100 --size 2600x1300
python scripts/check-display-performance.py --binary outputs/strehl-editor-preview/Strehl.exe --run outputs/feature-validation/insect-run --catalog outputs/feature-validation/state/Strehl/projects.json --output outputs/edit-workspace-review/performance-b1 --edit --motions 100 --size 2600x1300
python scripts/check-display-performance.py --binary outputs/strehl-editor-preview/Strehl.exe --run outputs/feature-validation/insect-run --catalog outputs/feature-validation/state/Strehl/projects.json --output outputs/edit-workspace-review/performance-b2 --edit --motions 100 --size 2600x1300
python scripts/check-display-performance.py --binary outputs/strehl-hdr-preview/Strehl.exe --run outputs/feature-validation/insect-run --catalog outputs/feature-validation/state/Strehl/projects.json --output outputs/edit-workspace-review/performance-a2 --edit --motions 100 --size 2600x1300
```

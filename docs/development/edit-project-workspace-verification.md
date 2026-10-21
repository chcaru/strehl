# Edit and project workspace verification

October 21, 2026. Development preview on `codex/hdr-editing-agent`; no new public
release. This extends the [spatial/export checks](spatial-export-verification.md).

## Executed controls

**VERIFIED:** 868 desktop tests and 57 editing tests pass. Thirteen desktop tests
remain explicitly ignored by the ordinary suite; this pass does not claim to
have rerun the earlier hardware-specific HDR controls. Fresh `Compiling` and
`Checking` lines accompany the tests and strict UI/editing Clippy run. Scoped
formatting and whitespace checks pass. The Windows sandbox's incremental-cache
hard-link warning falls back to copying; it is not a source lint error.

```powershell
$env:CARGO_BUILD_JOBS = '4'
$env:CARGO_TARGET_DIR = 'target/progressive-photo'
cargo test --locked -p strehl-ui -p strehl-edit -- --test-threads=2
cargo clippy --locked -p strehl-ui -p strehl-edit --all-targets --no-deps -- -D warnings
cargo fmt -p strehl-ui -p strehl-edit -- --check
$env:CARGO_TARGET_DIR = 'outputs/quality-october20-target'
cargo build --release --locked -p strehl-ui --bin strehl-ui
```

Filesystem tests ran under the normal Windows account with `TEMP`, `TMP`,
`LOCALAPPDATA` and `XDG_STATE_HOME` redirected to an isolated directory below
`outputs/edit-polish-review`. The restricted sandbox cannot exercise the actual
hard-link publication/locking path reliably. The original photographs and user
catalog are not fixtures.

The controls exercise choices that could fail:

- Real pointer events distinguish Select-mode blank-image panning from region
  moves, including a fresh drag after wheel zoom. Edit-specific timeline exit
  clears held inspection while retaining crop and pinned ranges. Escape and
  double-click fit do not steal the polygon edge's add-point action.
- Empty Regions geometry is constant across tools and gives space back to the
  controls; returning to a populated shelf restores its previously resized
  height. Tests use two pane widths and check visible guidance.
- Real tree drags move virtual stacks without opening photographs or changing
  capture evidence. Cycle rejection, F2 rename, Enter/Escape and organization
  Undo are covered.
- Saved versions reject a different TIFF, decoded master, loaded pixels or
  owner. A stale worker cannot replace newer edits. Restore preserves the
  previous recipe and is one Undo; an identical restore adds no duplicate.
- Export ownership and recipe are captured before encoding and retained across
  navigation. Failed publication, competing library writes and deferred close
  preserve recovery. A failed file-browser action reports its error without
  claiming that unsaved history needs recovery.
- Independent preview controls use reused IDs with different provenance,
  weak-reference lifetime checks, a visible set exceeding the cache capacity,
  changed visible-row sets, and a same-path image replacement with different pixels.
  These reject stale textures and repeated idle decoding; they are not FPS
  measurements.

## Native review

The optimized app was exercised through its real local MCP interface on a copy
of the complete 7032 × 4688 insect TIFF. The checks require settled progressive
display geometry, changed Adaptive pixels, retained measured fields after manual
editing, exact Amount-zero and Undo RGB restoration in a bounded 512 × 341 crop,
named-version restore and
Undo, and a full-resolution PNG beside the TIFF. The durable export record must
match the file hash and saved recipe. An existing export must not be overwritten.
Original source, copied TIFF and actual user catalog hashes stay unchanged.

The recipe assertion compares exact native f32 bits: snapshot JSON can expand
an f32 through an f64 value, while typed recipe JSON uses its shortest f32
round-trip representation. The initial raw-JSON assertion caught those two
representations; no coefficient tolerance was introduced.

Native Edit, compact Edit, Export and Projects captures were inspected. An
independent review prompted the smaller empty shelf and corrected Select hint.
Projects shows actual saved-edit thumbnails and the export under its owning
version. Right-clicking the exported fixture and choosing Reveal in Explorer
opened its containing folder. Desktop window access timed out before visual
confirmation of the selected file; the structured-argument tests are not a
substitute for that remaining native selection check.

Local harnesses, complete photographs, screenshots and receipts remain in ignored
`outputs/edit-polish-review`; they are not shipped or uploaded. A screenshot is
an SDR rendering and does not establish physical HDR luminance. Standalone
captures do not visually validate a populated stack timeline; the actual
timeline interaction tests cover that path.

Final delivery commands and identity:

```powershell
python outputs/edit-polish-review/check-native.py --run-name native-workflow-final
python outputs/edit-polish-review/capture-workspace.py --run-name native-final
```

The resulting `Strehl.exe` is 30,388,736 bytes, SHA-256
`ddead8da35d98086e9e69c96f221b1743213f966228bbcdb5ce33882fb8ba3cd`.
The native workflow receipt and the pane-capture receipt name that same binary.

## Limits and photographic review

Explorer previews are bounded navigation aids. They are not native-resolution
color proofs. Known wide-gamut/HDR exports use explicitly labeled saved-edit or
base-photo previews when direct decoding would misrepresent their encoding.
Standalone photographs remain in the Photographs group; virtual folder moves
apply to project/folder/stack objects and never move files on disk.

The new Adaptive options retain exact old Natural output on all three complete
review photographs and exact original output at Amount zero. Independent review
of whole photographs and separately chosen native crops accepted restrained
optional treatments, not glare removal, clipped-detail recovery, Adobe parity
or universal improvement. Analysis cost is measured separately from rendering
and UI latency in the [spatial-treatment record](adaptive-spatial-treatment.md).

## October 21 follow-up

Edit timeline inspection again animates into the linked source/final comparison
and paints the admission footprints on both photographs. Opening Edit no longer
blanket-suppresses these diagnostics. Leaving the timeline still clears the
comparison in the same paint, retaining the crop and pinned source spans. The
regression uses real pointer motion and actual rendered overlay marks, requires
an intermediate animation position, then checks immediate exit and re-entry.

Pane commands share a 26-point height; the version actions share a row, and the
profile selector and Apply/Recalculate action have bounded, aligned geometry.
Numeric controls reserve their own height above the slider instead of inheriting
a taller button size and colliding with the track. Tests render the actual pane
at 230, 270 and 440 points, compare painted controls and text baselines, and drive
the real profile menu. Selecting Signature applies it directly; advanced changes
remain a draft until Recalculate. Disabled regions cannot start treatment.
Native screenshot review also prompted a shared scrollbar gutter for the fixed
header and Regions tools. The controls reserve it even when sections collapse,
so both content edges remain aligned without a horizontal jump.
The Regions list also no longer forces its default minimum scroll height into
the small empty shelf; the actual painted shelf must fit the viewport in the
regression, including where the outer native pane would otherwise clip overflow.

**VERIFIED:** a fresh build passed 877 UI tests and 67 editor tests; 14 local
timing/photographic checks remain explicitly ignored by the ordinary suite.
Strict Clippy passed for both crates and all targets. The first layout checks
caught two test-oracle issues: comparing a text glyph center to a button-box
center, and targeting a popup before egui's sizing pass. The corrected tests
retain the separate rectangle bounds and now exercise a settled menu.

```powershell
$env:CARGO_BUILD_JOBS = '4'
$env:CARGO_TARGET_DIR = 'target/progressive-photo'
cargo test --locked -p strehl-ui -p strehl-edit --all-targets
cargo clippy --locked -p strehl-ui -p strehl-edit --all-targets --no-deps -- -D warnings
```

Tests use a separate TEMP/LOCALAPPDATA under `outputs/polish-october21/test-state`
and the normal Windows account to avoid the sandbox's filesystem-link/ACL test
artifacts. Final logs are retained in `outputs/polish-october21/workspace-tests-delivery.log`
and `clippy-delivery.log`. Thumbnail behavior, limits and measurements have their own
[record](explorer-thumbnail-performance.md); Signature's complete-photograph
and independent crop review is in the [Adaptive record](adaptive-spatial-treatment.md).

The final optimized executable passed the owned native workflow with Signature:
changed preview pixels, exact Amount-zero and Undo restoration, preserved manual
settings, named version restore/Undo, full-resolution PNG beside the TIFF, and
durable recipe/export lineage. The copied TIFF and the protected source/catalog
hashes stayed unchanged. The native run exercises the stored Signature parameters;
the actual profile-menu activation is covered separately by the pointer test.

```powershell
$env:CARGO_BUILD_JOBS = '4'
$env:CARGO_TARGET_DIR = 'outputs/quality-october20-target'
cargo build --release --locked -p strehl-ui
$env:RAYON_NUM_THREADS = '4'
python outputs/edit-polish-review/check-native.py --run-name october21-signature-final --signature
python outputs/edit-polish-review/capture-workspace.py --run-name october21-signature-delivery --signature
```

Independent final screenshot review accepted Edit at 1280 x 900 and 980 x 720,
plus Export at 1280 x 900: aligned content edges, consistent controls and a
contained Regions shelf. This is layout inspection, not an interaction-latency
measurement or physical HDR-display validation.

Delivery: `outputs/strehl-polish-october21/Strehl.exe`, 30,458,368 bytes, SHA-256
`b033fbc4c27b72c49cef20b62813b928fea9937b60fa3ab2db01dc06acc953e8`.
The native workflow, screenshot capture and copied delivery all identify this
same binary. Receipts are retained under
`outputs/edit-polish-review/october21-signature-final/receipt.json` and
`outputs/edit-polish-review/october21-signature-delivery/`.

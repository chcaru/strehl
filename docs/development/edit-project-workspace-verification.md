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

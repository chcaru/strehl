# Spatial development and Export delivery checks

October 21, 2026. This records the Windows development preview, not a new public
release or a claim of Lightroom equivalence. The source changes include spatial
treatment, named presets, the separate Export pane, portable agent operations,
and standalone TIFF canvas handling.

## Executed checks

**VERIFIED:** fresh compilation passed 832 desktop tests and 52 editing tests.
Thirteen desktop tests were ignored by the ordinary suite; four GPU controls
were then explicitly run on the freshly compiled test executable and passed.
Scoped formatting and strict UI/editing Clippy passed. An incremental-cache
hard-link warning in the vendored GPU dependency fell back to copying files;
it was not a source lint failure.

```powershell
$env:CARGO_BUILD_JOBS = '4'
$env:CARGO_TARGET_DIR = 'target/progressive-photo'
cargo fmt -p strehl-ui -p strehl-edit
cargo test --locked -p strehl-edit
cargo test --locked -p strehl-ui -- --test-threads=2
cargo clippy --locked -p strehl-ui -p strehl-edit --all-targets --no-deps -- -D warnings
& 'target/progressive-photo/debug/deps/strehl_ui-70916e2a3d351f08.exe' hdr_display:: --ignored --test-threads=1
$env:CARGO_TARGET_DIR = 'outputs/quality-october20-target'
cargo build --release --locked -p strehl-ui -p strehl-edit --example adaptive-benchmark --bin strehl-ui
python outputs/export-review/capture-panes.py
python outputs/export-review/native-mcp/check-native.py --run-name final-v3-verified
$env:RAYON_NUM_THREADS = '4'
& 'outputs/quality-october20-target/release/examples/adaptive-benchmark.exe' 'outputs/adaptive-spatial-review/insect/before.tiff' 'outputs/export-review/adaptive-worker-final.json'
```

The local screenshot/MCP harnesses, private photo copies, logs and receipts live
under ignored `outputs/export-review`. They are investigation artifacts, not
bundled user data. The generated native preview is 29,718,016 bytes, SHA-256
`fdd73309e16c7fe81d6199ddd4f7823cd9b4201a7293a196769d06197db84a31`.

## Native photo and agent checks

The final native Edit, SDR Export and HDR Export captures were independently
viewed. The photo fills the available workspace; control/value columns align,
and source origin is distinct from the display's HDR capability. No visible
overlap or clipped active controls was found. Collapsed advanced sections are
not validated by those screenshots, and an SDR screenshot is not physical HDR
luminance evidence.

Earlier captures exposed two real opening defects: the welcome screen remained
after opening a standalone TIFF, then unused process instruments consumed half
the canvas. Both were fixed. Explicit standalone editing/export now uses the
existing photograph navigator, progressive renderer, annotation coordinates and
Undo. It creates no capture history or diagnostic geometry certificate. Tests
check actual painted size, a requested off-center 3× view, Undo, and the real
right-click menu; invalid dimensions and recorded-capture inputs do not enter
this path. An independent reviewer caught and verified removal of misleading
regional-repair/contribution actions from the standalone menu.

The live MCP test used a copied 7032×4688 insect TIFF and isolated application
settings. It required an actual painted view and settled progressive detail,
then decoded the same 512×341 crop through the protocol. Adaptive changed the
pixels. Setting ordinary adjustments retained every measured spatial
coefficient. Keeping a nonempty treatment with Amount zero restored the exact
baseline; Undo restored the exact treated crop. Export without an explicitly
chosen folder was rejected before any job or output file was created.

| Decoded RGB crop | SHA-256 |
| --- | --- |
| Baseline and Amount zero | `a915d4677061be45a57ea78d86c1a870d8d813ea303f9f95fe8d5f652c5b57a9` |
| Adaptive and Undo | `2cbb06ab9c66edcc80db6fc47b07b30d8ec6d1cf6a69661ecaee5ab157082b9f` |

PNG bytes also matched for each restoration pair. The original source, copied
TIFF, actual user catalog and binary hashes were unchanged. Only the harness's
own app and MCP child processes were closed. Initial harness attempts assumed
an explicitly serialized empty list and exact decimal `0.3` equality after an
f32 round trip; corrected assertions used the documented omitted-empty state
and an exactly representable adjustment. Failed receipts were retained.

## Bounded timing and quality limits

**MEASURED:** four alternating, warmed analysis runs on the complete insect
master took 12.582–12.724 ms, sampling 16,328 pixels. The minimum was 12.582 ms.
Reusing the cached treatment for 5,000 Amount evaluations averaged 4.58 µs per
evaluation. These timings exclude import, preview creation, publication,
rendering, GPU execution and interaction latency; they do not establish a
frame-rate improvement or absence of regression. The smaller-preview arm uses
different samples and is not an equal-output performance comparison.

The separate [spatial photographic review](adaptive-spatial-treatment.md)
includes whole-image comparisons and independently chosen native crops. The
[export record](../export-formats.md#verification-and-limits) distinguishes the
passing independent color checks from the failed author RGB-error bound.
Earlier [display performance evidence](progressive-display-verification.md)
and its CPU-cost limitations remain applicable; they are not replaced by this
worker-only timing.

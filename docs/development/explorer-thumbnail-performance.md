# Explorer photograph previews

Explorer rows and their larger hover previews share a bounded texture cache.
No decode, file metadata read, image hash or cache-directory scan runs in the
paint callback. The completed photograph already loaded by Edit supplies its
small in-memory linear preview; opening Projects does not reopen that TIFF.

Two background lanes publish independently and wake the interface when their
result is ready. There is no 80 ms polling delay. Cancellation retains its lane
until the worker has actually returned. Invisible queued rows are discarded,
and the current visible working set is pinned to avoid eviction/reload flicker.
GPU previews are bounded to 40 entries and 24 MiB.

## First use and reuse

- Uncompressed RGB8/RGB16 TIFFs and Strehl RGB32-float masters use a bounded
  sparse row reader, retaining the existing transfer, embedded primaries,
  display baseline and baked-source metadata rules. The navigation derivative
  is at most 384 pixels on its longest edge. The reader averages four linear
  samples per thumbnail cell and reads at most two original rows per thumbnail
  row. It never materializes a full RGB image.
- Camera thumbnails use the embedded JPEG and reduced-resolution IDCT. RAW
  arithmetic and the final photograph are unaffected.
- File derivatives are retained under the app-state `explorer-previews` folder,
  bounded to 128 MiB and 512 entries. A reopened project reads small derivatives
  instead of decoding each original photograph again. Keys include source path,
  size, modified/created timestamps and small first/last file blocks; a changing
  source is rejected before publication. These are navigation-cache freshness
  checks, not cryptographic authentication of the full original file.
- New saved edit versions include their own small SDR preview alongside the
  immutable recipe. They remain inspectable without reopening or hashing the
  original photograph. Their preview identity includes the saved photograph,
  loaded-pixel identity and recipe. Renaming a version does not invalidate it.
  Older versions without derivatives may be populated from an open photograph
  only after matching its loaded-pixel identity.

Compressed or tiled TIFFs use the existing full, color-managed decoder as a
compatibility fallback, and PNG still requires inflation before its first
derivative. These paths can take longer on first use. Their codecs cannot be
interrupted midway through a decode; the second lane can continue independently.
Saved-version derivatives are part of the saved history, not the disposable
file-cache budget.

Sparse thumbnails are navigation aids, not detail-analysis inputs or full
low-pass reconstructions. Fine repeating patterns can alias: a checkerboard
control explicitly preserves that known limitation. Full photo display, edits,
exports and diagnostic processing continue to use their existing pixel paths.

## Verification and measurement

Fail-capable controls cover native/downsized linear samples and metadata;
big-endian multistrip channel/row placement; wide-gamut color conversion;
compressed fallback; truncated and oversized layouts; cache replacement with
a restored timestamp; corrupt-cache recovery; immutable version provenance;
closed-source version inspection; in-memory current-photo reuse; and retained
cancellation lanes. Saved-version texture tests must inspect the requested
texture ID, since independent completions intentionally have no fixed order.

The ignored UI test
`measure_explorer_cold_and_warm_navigation_derivatives` accepts a read-only TIFF
path in `STREHL_EXPLORER_BENCH`. It prints four alternating old-full-decode/new-
uncached comparisons and retained-derivative reads. Run in release mode with
`--ignored --nocapture`, without competing builds or image workloads. Its scope
is worker time; the OS file cache is uncontrolled and UI/GPU presentation is
excluded. It must not be reported as an end-to-end frame-rate measurement or a
guarantee of instantaneous reads from arbitrary storage.

### Local measurement, 2026-10-21

**MEASURED:** a 7032 × 4688 RGB16 insect TIFF (197,800,975 bytes), reduced to a
384-pixel navigation preview. Four alternating old/new passes completed in one
release test. The source was opened read-only and cache writes used a temporary
fixture directory.

| Worker path | Four measured times (ms) | Minimum (ms) |
| --- | --- | --- |
| Previous full decode and resize | 138.9210, 136.0308, 135.5258, 138.7001 | 135.5258 |
| Sparse reader, no retained derivative | 12.6691, 12.0395, 12.2686, 11.3205 | 11.3205 |
| Retained derivative | 4.1964, 0.1336, 0.1599, 0.1230 | 0.1230 |

The uncached navigation derivative took 11.32–12.67 ms against 135.53–138.92 ms
for the previous path on this photograph; comparing per-setting minima gives
11.97×. The first retained-derivative reading is included, not discarded.
“Uncached” here means no Strehl derivative: the OS file cache was uncontrolled.
This measures worker completion, not first paint, whole-pane loading or frame
rate. Different storage and compressed formats can behave differently.

The executed receipt is `outputs/polish-october21/explorer-timing.log` (local,
ignored). It contains the fresh release `Compiling strehl-ui` line, fixture path,
all samples and one passing timing test. The integrated verification reported
877 UI tests and 67 edit-engine tests passing, including legacy-preview
reconstruction followed by leaving its photograph. Strict Clippy passed; its
only reported warnings were the environment's incremental-cache hard-link
fallback to file copying.

Executed from the public-release checkout in PowerShell:

```powershell
$env:CARGO_BUILD_JOBS = '4'
$env:CARGO_TARGET_DIR = 'outputs/quality-october20-target'
$env:RAYON_NUM_THREADS = '4'
$env:STREHL_EXPLORER_BENCH = (Resolve-Path 'outputs/adaptive-spatial-review/insect/before.tiff').Path
cargo test --release --locked -p strehl-ui measure_explorer_cold_and_warm_navigation_derivatives -- --ignored --nocapture
```

`TEMP`, `TMP` and `LOCALAPPDATA` were redirected into the isolated
`outputs/polish-october21/test-state` fixture. No other build or native image
workload ran during the measured loop.

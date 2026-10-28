# Complete weevil TIFF workflow export

2026-10-26. Source prepared for root execution under the extended raw-quality-2026-10-26-comparator allocation. No Cargo build, RAW decode, TIFF export or Helicon invocation was executed by this preparation lane. The preceding two-frame Helicon witness establishes current application/export access only; it does not establish quality or the active width of these weevil originals.

## Frozen preparation

New source: crates/strehl-cli/examples/weevil-batch-develop.rs. The completed quality-batch-develop.rs is preserved unchanged; its product decoder/MHC/developer and exact vitamin fixture are reused in the new example. export-preparation.json records source, configuration, original source, manifest, historical fixture configuration and baseline-log hashes. Configuration is weevil-export-config.json in this directory.

All299 inputs are taken in their exact existing order from outputs/raw-quality-2026-10-26/weevil-107-baseline/input-order.json: DSC00001.ARW through DSC00299.ARW in D:/personal/macro/insects/bug-3/107MSDCF. The manifest itself is pinned. The example checks every original's size/SHA256 before the first decode and rechecks every original's content, size and modification time after all outputs are written. No capture, sidecar or runtime map is written. Golden inputs also have before/after content checks.

One original u16 frame is decoded at a time. Arithmetic is f32 with four Rayon workers, one temporary normalized CFA image and the product writer's one RGB16 output image; there is no aligned-frame volume or source RGB volume. Each frame's camera, ISO100, levels512/15360, RGGB-compatible active origin, dimensions, D65 camera matrix and exact manual WB must match. Full product-decoder active dimensions are retained and recorded. The independent RawPy witness was7028×4688; the prior vitamin Helicon witness was7032×4688. Neither is substituted for the product decoder's actual weevil extent.

Development is fixed to WB[1637/1024,1,2774/1024], exposure gain1, D65 XYZ-to-camera rows[0.746,-0.2365,-0.0588],[-0.5687,1.3442,0.2474],[-0.0624,0.1156,0.6584], and tone[-0.00026,0.27030,0.55]. Tone values are rounded numbers printed in the complete native baseline log, not recovered exact internal tone bits. The prepared source records the actual f32 bits. Source-specific automatic tone or WB would alter inter-frame evidence and is not used.

The actual-consumer vitamin control first requires exact original-u16 normalization against the frozen336-square CFA and exact RGB16 pixels against its retained TIFF. It exercises the same normalize_row and write_demosaiced route used for export. The control is consistency evidence for this developer path, not a new independent photographic benchmark or Sony calibration. All output headers must be full-size RGB16 with identical nonempty ICC profiles.

## Root command and resource envelope

Prepared commands, **NOT RUN by this lane**:

```powershell
cargo build --locked --release -p strehl-cli --example weevil-batch-develop
& '.\target\release\examples\weevil-batch-develop.exe' 'C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\experiments\raw-quality-2026-10-26\comparator\weevil-export-config.json'
```

Root schedules the executable through the established bounded wrapper with four threads,6GiB job commitment,900s wall and3600s CPU limits, and records current host load. The example fixes four Rayon workers itself. Watch for the actual Compiling line on the new example build. Successful completion requires receipt.json status299_UNALIGNED_NATIVE_RGB16_DEVELOPED and299 frame records; a partial directory is not a complete export. Capture the actual native exit code before display filtering. No timing or memory-performance claim follows from the source alone.

The fresh configured destination is outputs/raw-quality-2026-10-26/weevil-107-tiff-export. Only its frames/ directory contains comparator inputs. Its ordered inputs.txt lists exactly299 TIFFs; golden.tiff is outside that directory/list. Per-frame receipts include original identity, active rectangle, WB bits, output SHA256/bytes/type and elapsed time. Final receipt records executable SHA256, configuration/manifest identity,4-worker count and whole-corpus postflight. There is no subset/export-resume flag. About59GB of uncompressed RGB16 pixels is expected for this full source set, before small metadata; this is a derived storage estimate, not measured output size.

## Comparison meaning and next consumer

This is a complete external workflow comparison: Strehl native RAW merging followed by development versus product-developed RGB16 inputs followed by Helicon alignment/merging. The TIFF workflow applies tone before merge and has no lateral-CA warp; the native baseline applies its lens-profile CA correction in gather and develops after merge. Helicon also selects its own alignment and output crop. These are inherent recorded workflow differences, so this cannot isolate the merger algorithm or claim byte-matched processing. The rounded premerge tone is another disclosed difference.

The exporter creates no stack and makes no improvement claim. Root must retain the eventual complete Helicon stack master and full image, compare complete outputs with the previous native result, and inspect the fixed native weevil witnesses under a commissioned common view. Whole-scene size/brightness or gradient energy is not detail fidelity. Glints, hairs/scales, edge duplication and genuinely separate depths must remain part of the assessment.

Optional runtime-map focus-neighbourhood crops were omitted to keep this exporter a simple complete-source producer. Root's separate photo-review lane already owns those witnesses. No proposed mechanism is tuned from the export.

## Preparation checks

Verified299 baseline indices and exact filenames; inspected relevant historical fixture configuration keys, current decoder/developer interfaces and baseline render-log metadata. rustfmt with skip_children=true passed for the new example. An initial rustfmt invocation followed its image_out.rs module and changed formatting; this was repaired after proving exact equality to rustfmt(HEAD), with a concurrent-content guard. image_out.rs has no remaining diff. No global Git setting was changed. Source/config remain frozen for root execution.

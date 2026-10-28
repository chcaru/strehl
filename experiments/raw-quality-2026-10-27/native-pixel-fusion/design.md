# Fixed native whole-tuple fusion

Status: SOURCE PREPARED, not built or executed by the author. Root owns execution and photographic decisions. The complete flat observation is a mechanism test, not a general-quality promotion.

## One changed consumer

Each actual `BandWorker::fold` prepares the ordinary gathered R/G1/G2/B planes, guide, injected variance/probe and canonical seven-band Pyramid contribution. `canonical_fields` exposes the identical per-source finest AC weight. The candidate accumulates `sum(w0 * (value / 65536))` in each channel, one shared `sum(w0)`, and an unweighted sum of every tuple. The65536 factor is the production SoftPower power-of-two numerator scale; it prevents finite large weights from overflowing at camera DN levels. Final supported values are `(numerator/denominator)*65536`; unsupported pixels use the all-source mean. No other field, gate, exponent, beta, placement or resampler changes.

Both accumulations use original-order f32 arithmetic. The canonical Pyramid retains its existing four arithmetic chunks and left absorption; the candidate is a separate sequential reduction. At a pixel where **every original gathered four-channel tuple is bit-identical**, including the one-source case, the candidate copies that tuple exactly. This explicit shortcut avoids assuming multiplication/division is bit-associative. It cannot select a frame: it applies only to equal inputs. Every numerator and mean is checked finite, including before this shortcut; the denominator is checked at finish.

This removes frequency-dependent coefficient mixtures and terminal-mean synthesis from the candidate. It retains the current finest field's weaknesses: noise selection, poor color-only support and wrong ownership when fine and coarse structures belong to different depths. No source-selection or noise-calibration claim follows from using an existing noise gate. There is no amount knob: the independently reproduced canonical arm is the causal baseline; zero-evidence fallback is a separate test.

## Generated API and review

`compare_generated(frames, transforms, crop, noise, cfg)` returns `Comparison` with `baseline`, `native`, `uniform`, `forced`, and `gathered_source0` arms. Each arm contains `planes4` and the existing MHC `camera_rgb` result. `forced` uses explicitly fixed source0, never an elected truth. The source0 witness is the only retained gathered-source image. All arms consume the same one preparation per source. `Accumulator::new(pixels)`, `add(planes, weights)` and `finish()` expose zero-support/equal-input/extreme-weight commissioning without a second sampler implementation.

Generated extent is bounded to1152 native pixels; root separately authorized one1088-native pure-flat case. The receipt states actual level sizes and `exponent_at(k, sizes.len()-1)`: small default-seven-band fixtures truncate and do not reproduce the full-resolution ladder. Independent controls own flat-first, unequal high-DN/extreme finite weights, colored/thin/glint and far-coarse/near-fine cases. A supplied plant does not calibrate the camera. A generated loss remains visible even if root separately admits the complete flat diagnostic.

## Complete flat adapter

`full-adapter.rs` binds all60 original DSC00016..DSC00075 files to the baseline input-order SHA, metadata and content hashes before/after. It binds the held map, RGB16 master, linear master and the native-export receipt that establishes first-source WB. It preserves current CA profile `a7c2-fe100gm-2xtc-x4cpl`, reference30, quad crop `[25,17,3466,2310]`,6932x4620 output, four threads, canonical chunks15/15/15/15, MHC and exact recorded DisplayBaseline bits. Reported per-frame AWB variation never changes development.

The source30 checkpoint decodes only original index30 while retaining source-count60 in the actual preparation/probe gauge. It requires candidate **and canonical single-source hull** to equal the actual CA-corrected gathered tuple bit-for-bit. The ordinary `write_merged_observed` is called on gathered/candidate tuples and its RGB pixels must match. Separately, fixed-tone sensor/RGB16/linear outputs of canonical/candidate must all match exactly. The ordinary writer parity pair uses its automatic tone; it is not silently equated with the delivered fixed-tone pair. The ordinary source30 writer's pre-tone linear RGB32 payload must also exactly equal the fixed-tone helper's candidate linear payload, independently commissioning that normalization seam.

The complete60 adapter produces the canonical and candidate from one actual preparation per source. Before accepting the complete receipt, decoded baseline RGB16 and linear RGB32 payloads must reproduce the held baseline exactly. The fixed display path uses the ordinary `write_demosaiced_with_master` seam and identical pre-MHC normalization, camera matrix and saturation handling. The receipt records source/guide/variance/weight hashes, actual settings, input preservation and elapsed times; runtime/resource claims require root's completed bounded run.

Outputs are `baseline-master.tiff`, `candidate-master.tiff`, their `*-linear.tiff` siblings, and complete `*-sensor.f32le` plus geometry/units JSON. Whole images and these full-resolution masters precede frozen native witnesses. No aligned-frame or RGB-source volume is retained. The full299 weevil adapter is deliberately not enabled in this allocation before the flat photograph decision.

Root registration: module `merge_cmd::native_pixel_fusion` includes `implementation.rs`; its child `full` includes `full-adapter.rs`. Tests:

```text
merge_cmd::native_pixel_fusion::independent_controls::fixed_native_pixel_screen
merge_cmd::native_pixel_fusion::full::flat_source30_checkpoint
merge_cmd::native_pixel_fusion::full::flat60_complete_observation
```

Screen output: `STREHL_NATIVE_PIXEL_OUT`. Full/checkpoint config: `STREHL_NATIVE_PIXEL_CONFIG`, strict JSON `{ "schema": 1, "out_dir": "<fresh absolute workspace outputs directory>", "expected_test_executable_sha256": "<frozen binary hash>" }`. Root supplies four workers and the existing native GPU/direct/probe flags, with ordinary CA enabled. No default or production source is edited by this author. Source-format parsing only was run with `rustfmt --edition 2024 --config skip_children=true`; builds, RAW decoding and all numerical tests remain root-owned.

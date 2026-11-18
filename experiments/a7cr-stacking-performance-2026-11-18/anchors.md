# Code anchors for the round-2 performance plan

Condensed from five read-only surveys of the working tree on 2026-11-18. Line numbers
are approximate and will drift; function names are the anchors. Paths are under
`crates/`. `M` = `strehl-cli/src/merge_cmd.rs`, `G` = `strehl-gpu/src/lib.rs`,
`DA` = `strehl-cli/src/merge_cmd/decode-ahead.rs`, `PS` = `strehl-cli/src/pixel-shift-cmd.rs`,
`CFA` = `strehl-raw-codec/src/cfa.rs`.

## Q1 start-up and tear-down
- `sony_focus_cmd::print_preflight(&paths)`: called at M ~3383 and ~8640
  (`run_pyramid_attempt`); loop at `strehl-cli/src/sony-focus-cmd.rs` ~544; reader
  `archive::open_sparse` at `strehl-raw-codec/src/archive.rs` ~179 (8 KiB `BufReader`,
  `seek_relative` per chunk, hashes prefix and suffix chunks ~225-248); the model test at
  `strehl-raw/src/sony-focus.rs` ~202; switch `STREHL_SONY_FOCUS_AUDIT`.
- Repeated per pass: `StackGroups::from_env` (M ~8624, also `run_refined` ~8917),
  `recorded_groups` (PS ~85), `GroupJournal::open` (PS ~592), `alignment_for_observed`
  (M ~8695, ~8926), first-frame `strehl_raw::decode` (M ~8655), `identity` (M ~8477,
  ~8836, ~9711).
- `BandWorker::new` M ~6169-6202 (two `BandMerge::new`, `FrameWorkspace::new`); freed in
  `try_gpu` M ~6230-6289 (`release_external_totals`, `fws = None`).
- `GpuFold::build` G ~937-1243: `strict::compile` ~950, instance/adapter/device ~953-985,
  pipelines ~1192-1204 (`cache: None`), `add_second_accumulator` ~1284.
- Tear-down: `drop(worker)` M ~9725; no `process::exit`; `main.rs` returns `run_from`.
- Write path: `write_merged_observed_with_reconstruction` M ~11335; serial `norm` loops
  ~11631 and ~11735, mosaic ~11695-11706 dropped at ~11753; `colour_carry::interleave`,
  `optical_restore::restore` ~11760, `smooth_chroma` ~11804, `image_out::write_rgb_full`.

## Q2 reference tiles
- `gather_restoration_references` M ~7116-7253 (`RowSource`, slots `workers.clamp(1, 4)`,
  `slot.prepare`, `optical_restore::observe`); `prepare_frame_into` M ~7043 (luma,
  `depth_guide::record`, `luma_variance`); `load_frame_impl_observed` M ~7521
  (`extract_planes_bands`, `colour_carry::copy_carried`).
- Tile plan: `optical_restore::plan_tiles` (`merge_cmd/optical-restore.rs` ~345-393):
  `TP = 128`, `MARGIN = 4`, `SIDE = 136`, `MAX_TILES = 200`; 770 candidates on a 128 px
  grid; frames = the two folded indices nearest the tile's median depth;
  `reference_rows()` ~401; crop use in `restore` ~589-656.
- Gather: `align_cmd.rs` `warp_fullres_banded`, `BAND_ROWS`, `fullres_source_rows`,
  `gather_rows_catmull_rom_checked`, `CARRIED_SITES`.

## Q3 group check
- `StackGroups::prepare_with` PS ~1160-1204 (members via `decode_serial`, `measure`
  ~1175, `MeasuredGroup` fields 1199-1204); `measure` / `measure_with_witness` / `judge`
  PS ~849-921; pinned tests PS ~1460, ~1482.
- `strehl-core/src/pixel-shift.rs`: `balance` ~96, `Integral::new` ~142-186 (row pass,
  `COLUMNS = 256` strips, copy back), `block` ~191, `normal` ~221-251, `fit_member`
  ~320-364, `witness` ~429-576 (per-site loop ~459-511, `edges` with `ln` ~446, tile-row
  combine ~523-545).

## Q4-Q6 supply and fold thread
- Decode-ahead: `DecodeAhead::run_decoder` DA ~236, `run_prefetcher` ~286, `decoders()`
  ~59, `pin_decoder` ~85; spawned at M ~9501-9515; window `(2 * lookahead).max(8)
  .max(decoders + 2)` M ~9493; `GPU_PREP_FOLD_THREADS` M ~5190; pools M ~9438-9467.
- Prefetch: `RawPyramidSource::prefetch` M ~5521-5538 (4 MiB discard reads), `prefetchers`
  ~5540; `decode_with` M ~5433 (`identity_cached` ~5450).
- Codec: `decode_archive_impl` CFA ~303-582 (serial path ~466-522 with `RESIDENT`),
  `unpredict_into` CFA ~162-211, `decode_archive_rows` ~295; `strehl-raw/src/lib.rs`
  `decode_with` ~380-510 (`metadata_image` ~423, ISO ~483).
- Fold thread: `fold_chunk_gpu` M ~6585, `gpu_start` ~6321 (`gpu.stage` ~6434,
  `probe_submit` ~6459), `gpu_finish` ~6476 (`probe_collect` ~6499,
  `add_staged_keeping_luma` ~6544, `luma_tap.collect` ~6568); `LumaTap` M ~5140-5187.
- Device: `GpuFold::stage` G ~1716-1850 (parallel fill ~1809-1830, two upload slots),
  `probe_submit` ~2020 (new read-back buffer ~2148), `probe_collect` ~2170,
  `add_staged_keeping_luma` ~2391, `luma_collect` ~2480, `record_gather` ~1906,
  `record_fold` ~1540, `MAX_CALLS` ~672.
- Depth tap: `merge_cmd/depth-guide.rs` `record` ~992, `cell_energy_of_difference` ~965,
  `finish_tap` ~1026; blur `merge_cmd/axial-colour.rs` `blur_into` ~206.

## Q7-Q8 tail
- `finish_chunk` M ~6632, `finish_device_chunk` ~5199, `read_chunk` G ~2548-2652
  (64 MB pieces), `absorb_chunk` ~2536.
- Halves: M ~9746-9761 (`merge.finish`, `odd.finish`, `merge.absorb`, `route_halves`).
- `strehl-core/src/pyramid.rs`: `BandMerge` ~1694-1820, `absorb` ~3525-3753, resolve
  ~3945-3958 (`resolve_soft_numerator` ~1883), hull clamp ~4007, collapse ~655-677,
  `expand` ~368-410, `reduce` ~288-333, blend maps `ensemble_blend_level` ~2290-2331,
  `box_smooth` ~4723 (f64 prefix sums), `log_ramp` ~4445 (std `ln`).
- Restoration: `strehl-core/src/optical-restore.rs` `convolve` ~832-912, `pair_terms`
  ~229-258, `kernel` ~732-820; `merge_cmd/optical-restore.rs` `restore` ~565-942.

## Q9 alignment
- `strehl-core/src/align.rs`: `ncc_tile_impl` ~982 (tile terms ~1002-1017, offset loop
  ~1028-1068), `fit_stage_impl` ~1658, `align_pair_impl` ~2045, `AlignPyramid::build`
  ~567, `downsample` ~484, `AlignConfig::deep` ~701, `solve_global_selected_with_triples`
  ~2973. `strehl-core/src/plane.rs` `green_luma` ~77.
- `strehl-cli/src/align_cmd.rs`: `measure_ladder_streaming` ~638-804 (batch ~681,
  `rayon::join` loop ~774-787), `load` closure ~620, `finish_measured_map` ~2045, cache
  key ~1923, sidecar path ~1806; oracle test ~4510.

## Q10 preview
- `ca_refine::run_refined` M ~8906-8941, `stride_for` ~8890, `begin_preview_of` ~8953,
  `end_preview` ~8969, `ca_refine::capture` M ~11712; `strehl-core/src/ca-refine.rs`
  `measure_mosaic` ~209, correlation ~455-547, fit ~552; green unchanged:
  `strehl-core/src/optics.rs` ~754 (`Channel::Green => return t`).

## Archive format
- Envelope `STRHARC1` 48 bytes (`archive.rs` 1-59); stream `STRHRAW1`; 13-byte chunk
  header (decoded length, payload length, method, CFA width); methods 0 (Zstd), 8 (CFA
  predictor + Zstd), 255 (stored); 128-row CFA chunks; `zstd::bulk::compress(input, 1)`
  per chunk (`strehl-raw-codec/src/lib.rs` ~244); whole-file SHA-256 of the original ARW
  bytes only. Encoder on the Pi (`strehl-capture/src/transfer.rs`), receiver tees the wire
  stream (`receiver.rs` ~483, `archive::retain`).

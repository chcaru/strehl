# P7d: region-only depth repair (E4)

**Status:** results note for E4 / phase P7d of
[the implementation plan](../../docs/proposals/2026-11-desktop-studio-2-implementation.md)
(section 8, "E4 in detail"). Branch `studio2/p7d-region-repair` from the integration branch
`91ebd7e70`; code commit `e89e585b9`. **Date:** 2026-11-21. **Evidence labels** as in
`AGENTS.md`.

## What a repair did, and what it does now

A depth repair is a source-range repair: the region's permitted frames are folded in a
separate accumulator and blended into the merged CFA before colour development
(`merge_cmd/region-repair.rs`). Until now the desktop ran it inside a complete new render:
CA preview pass, decode and fold of every frame, then the repair pass.

The region-only rebuild (`merge_cmd/region-only.rs`) runs only the repair pass, against the
linear master an earlier render of the same stack wrote:

| Step | How | Exactness |
| --- | --- | --- |
| Original CFA | The master inverted per site through the colour matrix, then the writer's normalisation undone | Read only in the blend ring (below) |
| Repair pass | `Repairs::apply` unchanged: same frames, canonical chunks, full analysis domain, noise model, warps and merge configuration | Same arithmetic as the full render |
| Alignment | The run's warp map: copied into the new run and named by `STREHL_WARPMAP` (old runs), or the shared engine cache (new runs) | Same map |
| Lateral CA | `--reuse-ca-from <render.log>`: the earlier render's refinement, no preview pass. Renders now log it exactly (`exact red … blue …`); older logs give the printed rounding | Exact for new runs |
| Tone | Pinned from the master's baseline | The original's |
| Write | The unchanged writer; every pixel whose 5 x 5 Malvar stencil meets no repaired site keeps the original master's and photograph's samples (`image_out::RegionComposite`, inert in every other render) | Bit-identical outside |

Frames outside the regions' ranges are not decoded. Region-only refuses (and the desktop
falls back to the whole stack) when any whole-image stage is active: colour carry, optical
restoration, calibrated fusion, depth guide, axial colour, frame refinement, self flat,
temporal energy, sensor master, a restoration gain cap, the directional demosaic, or no
recorded tone.

**Why not a cropped domain** (ARGUED, from `strehl-core/src/pyramid.rs`, `NullWindow`): the
ensemble gate measures its null on a window centred in the domain
(`x0 = (width - w) / 2`), so a domain cropped to the region measures other thresholds and
selects differently. It could not be bit-identical to the full repair. The full-domain repair
pass is the cost floor of this design (below).

## Gate on the 299-plane weevil (MEASURED)

Input: `D:\personal\macro\insects\bug-3\107MSDCF`, 299 ARW (read-only). Region: an ellipse at
(0.30, 0.60), radius (0.03, 0.045), feather 0.5, frames 116 to 132 (17 frames). Engine:
`target\release\strehl-ui.exe --engine-worker stack <source> --merge pyramid --srgb --out …
--linear-master … --auto-exposure`, as the desktop runs it, built from this branch. Environment:
`STREHL_CACHE_DIR` and a copy of the owner's run's warp map (`STREHL_WARPMAP`) in scratch,
`RAYON_NUM_THREADS=32`, `STREHL_PYRAMID_WORKERS=32`. Host: Ryzen 9 9950X3D (32 threads),
RTX 5090 (GPU fold on). Scripts `gate.py` and `compare.py` (scratch, deleted after).

| Run | Arguments added | Wall time | Peak working set | CPU load before |
| --- | --- | --- | --- | --- |
| A, original | none | 7.8 s | 6.81 GB | 27 % |
| C, region-only | `--region-recipe`, `--region-only-master/-photo` (A), `--reuse-ca-from` (A) | 7.03, 7.14, 7.12 s | 4.00, 3.82, 3.83 GB | 25, 27, 23 % |
| B, full repair, same CA | `--region-recipe`, `--reuse-ca-from` (A) | 11.88, 11.85 s | 6.84, 6.82 GB | 30, 28 % |
| B2, full repair as before | `--region-recipe` | 15.18, 14.43 s | 7.17, 7.09 GB | 37, 34 % |

A repetition under 50 to 100 % load from other lanes gave 15.5 to 30.7 s for every arm; it is
excluded. The repair pass itself (CPU, 17 frames, full domain) took 5.8 to 6.4 s in every arm:
it is most of a region-only rebuild, because the GPU folds all 299 frames in about 2.6 s.

Pixels were classified from the ellipse alone (not from the engine): *outside* means every
site of the stencil lies outside the support, *inside* means every site lies past the feather,
each with a margin of 1e-4 in the shape's distance; the rest is the blend ring.

| Comparison | Pixels | Bit-identical | Largest difference |
| --- | --- | --- | --- |
| C vs A (master), outside | 32,822,785 | 32,822,785 | 0 |
| C vs A (photograph), outside | 32,822,785 | 32,822,785 | 0 |
| C vs B (master), inside | 33,272 | 33,272 | 0 |
| C vs B (master), blend ring | 109,959 | 58,056 | 7.5e-8 absolute; 8.8e-7 of the pixel's largest channel |
| B vs A (master), outside | 32,822,785 | 32,822,785 | 0 |
| B2 vs A (master), outside | 32,822,785 | 4,400,995 | 0.21 of the pixel (p99 1.7e-3) |
| C vs B2 (master), inside | 33,272 | 6 | 0.068 of the pixel (p99 1.6e-3) |

- **Gate, stated tolerance:** bit-identical outside the region's reach and on fully covered
  stencils; in the blend ring the difference is the inverse's rounding, at most 1e-6 of the
  pixel. The gate holds.
- **Controls:** the repair took effect (C differs from A in 142,768 pixels). B reproduces A
  bit for bit outside, so the full render is deterministic and the comparison is fair. B2 is
  the failing control: the full repair as the desktop ran it re-measures the lateral CA with
  the repaired area in the preview and moves every pixel of the photograph slightly; the
  region-only rebuild does not.
- **An older run:** region-only against the owner's original render of this stack (built
  2026-11-04, log without the exact line, so the printed CA) changed 142,770 pixels, all
  within x 1897 to 2322, y 2600 to 3025, and kept the rest of that master's bytes. Inside, the
  rounded CA differs from the exact one by at most 1.3e-4 absolute (p99 2e-3 of the pixel).

## Desktop

`start_depth_repair` takes the region-only route when the open render is in the library and
saved, kept a linear master, photograph and log, and is not a session or temporal render. The
request uses that run's own settings (confidence map off). Otherwise, or if the region-only
rebuild stops, it re-stacks the whole stack, and says why. The Develop status reads
"Rebuilding the painted area only" or "Re-stacking the whole stack", and the activity tray
shows a Heavy-lane "Depth repair · painted area only / whole stack" with Cancel (new
`ActivityKind::Repair`). VERIFIED by
`a_depth_repair_rebuilds_the_painted_area_only_and_falls_back_to_the_whole_stack` and
`a_region_only_repair_names_its_original_and_reads_a_copy_of_its_warp_map`.

## Tests and checks (VERIFIED)

- `region_only_keeps_the_original_outside_and_matches_the_full_repair_inside` (production
  writer, generated stack, a soft depth-brush stroke): outside bit-identical to the original;
  inside bit-identical to the full repair; ring under 1e-5 of the pixel; tone and baked recipe
  as the original and the full repair.
- `region_only_refuses_an_original_of_another_size_or_without_a_tone`,
  `the_ca_refinement_is_read_back_from_a_render_log` (the weevil log's lines, the exact line,
  refused and absent refinements, an unstated applied refinement).
- `cargo test -p strehl-ui`: 1,354 passed, 0 failed. `cargo clippy -p strehl-ui --all-targets
  -D warnings`: clean. `cargo fmt --check` clean for strehl-ui and the new files.
- `cargo test -p strehl-core`: all suites pass (800 unit tests).
- `cargo test -p strehl-cli --no-fail-fast`: the byte-freeze suite (`tests/byte-freeze.rs`)
  5 of 5 passed (664.8 s); the lib target 266 passed, 13 failed. The same 13 (the m194f/m194g
  experiment harnesses and two native-green-probe controls, which need private inputs) fail on
  the integration commit `91ebd7e70`. One doctest fails, `Command::Stack (line 234)`, on
  existing indented help text this branch does not change. strehl-cli was not clippy- or
  fmt-clean before this branch; none of its 118 clippy diagnostics falls on a changed line,
  and no unrelated code was reformatted (the writer's byte-frozen text is untouched).

## Open

- **The repair pass runs on the CPU** (5.8 s for 17 frames). It is shared by the full repair, so
  folding it on the GPU (claimed bit-identical to the CPU fold) would speed both and keep the
  comparison exact. That is the next speedup; not done here.
- Region-only needs the original's master, photograph and log; older runs supply the printed
  CA rounding (measured above). Session renders still re-stack whole.

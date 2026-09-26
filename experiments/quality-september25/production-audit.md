# Bounded production implementation audit

2026-09-25. **ARGUED from source inspection: no new actionable implementation defect found in the paths below.** This is a limited audit, not a correctness certification or evidence that the remaining photographic defects are absent. No source changes, new tests, RAW reads, builds or renders were performed for this audit.

## Scope and prior closures

Mechanical searches used `experiments/ORCH-drift-check/prior_art.py` with `coordinate crop support boundary gather` and `coefficient base units saturation overflow`. The current proposal checkpoint and recent mineral, marigold and chip conclusions constrained the search.

- `docs/research/BUILD-CROP.md` refuted fit-to-cover as the proposed softness cause. `M-COVER-BORDER.md` identified late-crop black-fill contamination; `M130-crop-early.md` records the early-domain repair. Do not rediscover either as a new defect.
- `experiments/sampler-boundary/repair-rationale.md` and its independent reviews cover the repaired upper-edge fractional-coordinate plateau. This audit does not extend those scalar controls into a new native-gather guarantee.
- `docs/research/V-GATHER.md` and `M194c-probe-layout.md` distinguish the old noise-floor/layout failures from a supposed double-demosaic cause.
- The September 25 weighted-numerator overflow repair is already measured separately. The base-band-transfer and real-source-contribution refusals do not establish a replacement source-selection treatment.
- `experiments/opal-headroom/stage-results.md` records no actual pin/clip/knee changes on the completed opal output. That result cannot be generalized to every stack, and it does not support reopening the opal pin path.

## Checked consumers

| Area | Symbols / source locations | Bounded finding |
| --- | --- | --- |
| Gather coordinates and crop | `align_cmd.rs::warp_frame_fullres_with_sink_impl` (2210); `native-direct-planes/implementation.rs::warp_frame_fullres_into_planes`; `native-gpu-gather/integration.rs::gpu_rounded_planes` (153) | Crop uses original quad coordinates. The packed GPU row expression at line 183 is consistent with two native u16 samples per word; it is not a missing factor of two. |
| Source preparation | `merge_cmd.rs::load_frame_impl` (5244), `validate_pyramid_frame` (5438), `run_pyramid_prepared` (6176) | Geometry/storage and per-frame levels are checked; refused warps are excluded; source count must match the prepared manifest. No demonstrated source-inclusion or crop-origin error found. |
| Soft accumulation and reconstruction | `pyramid.rs::SOFT_NUMERATOR_SCALE` (1512), `resolve_soft_numerator` (1515), `BandMerge::accumulate_level` (2082), `absorb` (2241), `finish` (2525) | The inspected soft path accumulates scaled numerators, absorbs matching quantities and restores the scale once at resolution. No newly demonstrated sign, base-unit or scaling defect found. |
| Final CFA/development boundary | `merge_cmd.rs` interleave at 8116–8125; `image_out.rs::develop_pixel` (1246), `tone_from_mosaic` (1325), `write_demosaiced` (1388) | The four planes return to RGGB at their expected sites. Normalization, final demosaic and development ordering supplied no new counterexample within this pass. |

Line numbers describe the source inspected on this date and may move. Existing optional paths were not exhaustively audited, and no claim is made about complete output quality, cross-stack calibration or all valid input geometries. No new diagnostic campaign is recommended from this audit: it did not identify a fresh suspicious path with a cheap, realistic failing input.

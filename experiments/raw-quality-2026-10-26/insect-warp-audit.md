# Insect field-warp audit

2026-10-26. Root-allocated bounded source/prior review. **VERIFIED** means inspected source or retained reports here, not independently replayed numerical results. No RAW reads, fits, builds, source implementation edits or photographic comparisons were run. Root supplied the unified and mechanical prior searches; this pass read their relevant conclusions and current consumers.

**Decision: no field-distortion intervention is justified by the currently saved insect evidence.** The failed fixed-gap nomination does not answer this separate question, but aggregate alignment residuals do not answer it either. Keep the current color work primary. Do not enable a richer warp or rerun a stack from these residuals.

## What survives from prior work

- `docs/research/M6-residual-halo-measured.md`, verdict and section 1.1: the tested old three-stack residual was explained by defocus-related matching degradation; depth-organized radial change and asymmetric field signature were not detected by commissioned controls. Its useful identifiability step was **sliding pair baselines**, so the same tile was observed at several defocus levels. Fixed-anchor depth and defocus regressors had been algebraically confounded. This is evidence about those populations, not proof that the current rig has no distortion.
- `M86-alignment.md`: pairwise measurement imposes a cycle floor; a global solve cannot turn biased edge measurements into physical truth. Its early interpretation of softness and end-to-end drift must be read with the later amendments.
- `M97b-align-visible.md`, sections 12.2–12.4: a uniform-blur control reproduced the supposed radial sharpness trend. The two merged photographs were also not related by one similarity because their location-dependent contributing frames differed. That composite-to-composite non-similarity **does not establish non-similarity between original captures**, much less radial lens distortion.
- `M103-halfdrift.md`, section 16: the example 150.3→2.9 plane-pixel end-to-end residual gain accompanied 36.4→37.5 plane-pixel mean per-frame placement in the merge gauge. Its curved focus-breathing track and gauge amendment block promoting an endpoint correction or straight-track plant as a practical placement fix. These historical values describe that experiment, not the current 107MSDCF solve.
- `metadata-continuation-2026-10-25.md`: optical-table and ordinary guide-phase continuations produced no admitted photographic benefit. Actual optical records were also inspected in `C:/Users/chris/AppData/Local/Temp/strehl-core-main-0d466788/experiments/rea-a7c2-2026-10-24-l/`: `consumer-results.md`, `resume-2026-10-25/completion.json`, and `independent-photo-review.md`. Generated geometry passed its declared family; actual per-frame optical tables had zero accepted all-control wins in either bee3 or slide2. This rejects that calibrated-law recipe's photographic gate, not all runtime spatial geometry. The ordinary phase result is taken from the current published continuation summary; the inspected t5 guard review verifies builds/refusals only and is not its photo verdict.

## Current source and saved insect evidence

**VERIFIED:** ordinary alignment extracts a half-native green guide, measures direct pairs, and reduces each accepted result to one `AlignEdge` containing similarity, RMS, tile count and lever. `StageFit` adds summary peak/refusal counts but no retained coordinates or displacement vectors. `TileMeasurement` and `Observation` exist inside `crates/strehl-core/src/align.rs`; `align_cmd::measure_edges_observed` does not save them. The current `ui-progress.rs::alignment_pair_finished` emits pair IDs, progress and acceptance counts, not tile correspondences.

The current `WarpMap` stores per-frame similarities and provenance, not a spatial displacement field. The inspected baseline directories contain `alignment.txt`, `align.log` and process receipts; no saved tile-correspondence artifact was found. Both current maps have 299 frames, reference 149, 3516×2344 **quad/guide** coordinates, Catmull–Rom sampling and strategy `S3-ba-unit-measured-component-v1`:

| Saved baseline | Held-out corner residual | Cycle floor |
| --- | ---: | ---: |
| `weevil-107-baseline` | 3.3588 quad px | 1.5540 quad px |
| `bug2-100-baseline` | 4.0764 quad px | 1.0182 quad px |

These summaries cannot locate a field error, separate its sign from defocus bias, or establish physical per-frame placement. The old 4-quad-pixel threshold is not a quality certificate. No aggregate residual was interpreted as displacement of an insect hair or scale.

`crates/strehl-cli/src/lens-research-geometry.rs` already contains an explicitly disabled `ResearchPull` with source/anchor radial curves, native similarity and checked domains. Its centers, knot values and scale conventions are supplied by a manifest; it does not estimate distortion from the current tile residuals. Enabling it would assume the missing optical law, not discover one. The generated consumer results explicitly contain no defocus/occlusion model.

## One conditional low-cost next step

**ARGUED, not dispatched:** if root already needs a new alignment for another reason, retain the existing fine-stage tile observations before reduction: source-pair IDs, tile centers, measured dx/dy, status, contrast, peak, survivor mask, seed and guide gauge. This costs a compact receipt and need not add a pair fit, RAW decode or warp. Include refusals, because retaining only well-fitting survivors can hide precisely the field where a richer model is proposed.

Use that receipt only for a bounded M6-style identifiability screen across already-measured sliding pairs: same physical tile at several focus offsets, and spatially separated tiles at comparable defocus. A field term must persist across those offsets and predict held spatial sites; a term changing with focus mismatch or fit population remains matching bias. If focus/support does not provide this crossed comparison, stop as unidentifiable. Do not select a radial model merely from radial residual appearance, or treat a smaller residual against the same NCC measurements as independent placement truth. Controls must include symmetric defocus with fixed geometry and a known non-similarity displacement before any interpretation.

The currently retained tiny 104–106 caches cannot supply whole-field support, and the failed fixed-gap sites must not be relabeled as geometric evidence. Thus this review recommends **no extra execution now**. Receipt retention during an independently needed run is the sole suggested addition; any later warp still needs demonstrated original-sensel structure placement and complete-photograph verification.

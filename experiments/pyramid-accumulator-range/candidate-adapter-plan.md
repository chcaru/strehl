# Minimal corrected full-stack observation without weakening the old baseline

Proposal only; no source edits or executions. Keep the existing `complete_pair` historical baseline assertion unchanged. A corrected merge necessarily changes its output, so running it through that old assertion under the name baseline is the wrong contract.

Add one separate ignored current-only test entry point, such as `merge_cmd::full_stack_source_prior::corrected_current`, and a distinct runner phase. Reuse the current recipe, input decoder/gather/BandWorker path, canonical chunk plan, metadata checks and final writer. No source-prior pass is involved. The new entry point may share an internal implementation after extraction, but the existing test's behavior and historical-equality requirement must remain unchanged.

Its extra config field is one immutable historical bundle: paths plus hashes for the original completed full-current receipt, its baseline-cache metadata and binary, and the original build/executable bindings. All refer to already retained files, never rewritten candidate outputs. For garnet, use `full-stack-source-prior/garnet104-full-1/output` or the just-completed verified observer-off equivalent; choose one before the corrected run and bind it in the new config. Preserve the unchanged original recipe master/hash/pixel-hash fields.

Before decoding any originals, require:

- Original master file hash, native dimensions and RGB16 pixel hash equal the unchanged recipe; ICC remains present.
- Retained historical receipt is full/current, covers all ordered183 inputs, and records the recipe's original expected pixel hash.
- Historical cache metadata, binary and plane hashes validate with the existing cache reader. Source-order digest, map hash, camera levels/WB/matrix, crop, full geometry, reference and requested exposure match the original recipe/receipt.
- Re-render that saved historical cache through the candidate binary's unchanged writer and require complete RGB16+ICC equality with the original master. This cheap cache replay tests the retained baseline rendering independently of the changed merge and avoids another full RAW baseline job.

Only then run the complete corrected RAW merge with all existing input-content hashes, active-area/calibration checks, gathered-input/source-order evidence and canonical chunk ordering. Write `corrected.tiff` and `corrected-cache.*`, not `baseline.*`. Do not require the corrected image to equal the original; require dimensions/ICC, finite accumulator/reconstruction checks, identical held acquisition/development policy, exact original/map bindings, and a complete run receipt. Record both expected historical hash and measured corrected hash, with an explicit `historical_cache_replay_exact:true` and `corrected_output_changed` observation. Quality admission remains false until full-image/native photographic review.

The runner should independently compare current versus retained per-source active/gathered/guide/variance/beta evidence to show that the correction changed the intended accumulator rather than input geometry or noise. Its checks must distinguish bit-identical held fields from intentionally changed normalized weighting or accumulator representation; do not promise canonical-weight identity if the chosen numerically safe representation rescales weights. In all cases the intended mathematical relative weights must be independently checked by the f64 regression reference and the fix-specific nulls.

This needs one new purpose-specific entry point and a small validation branch, not a permissive `skip_baseline_check` flag. Any missing/mismatched historical provenance must refuse before a corrected full stack starts. The original historical recipe and old validation route continue to reject mismatching baselines exactly as before.

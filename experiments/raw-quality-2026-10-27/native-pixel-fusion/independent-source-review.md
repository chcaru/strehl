# Independent native-pixel source review

**VERIFIED by source inspection; execution UNVERIFIED at this review.** No remaining source-level blocker was found after the corrections below. This is readiness for the root-scheduled generated screen and source-30 checkpoint, not permission to infer photographic improvement or promote a default. Root separately decides whether to release the complete 60-frame observation after the bounded checks. This reviewer ran no build, RAW decode, numerical test or image export for this allocation.

## Actual consumer and arithmetic

[implementation.rs](implementation.rs) calls the existing `BandWorker::fold` once per source. The canonical Pyramid therefore runs through the actual gather, injected noise/probe, variance and coefficient accumulation. `canonical_fields` reconstructs the current weight using that retained workspace and beta, the same production energy and `select_weight` functions, and the effective pyramid depth. The candidate immediately consumes those same four prepared planes and finest-band weights. There is no proxy sampler, separately developed RGB source, new noise fit or aligned-source volume.

All four phases share the denominator. A zero denominator averages every source; a positive denominator uses the unchanged canonical weights. Exact tuple equality checks all four gathered channel bits across every source, then copies the common tuple. This explicit shortcut preserves signed values and singleton identity without pretending f32 multiplication/division is exact. It does not elect a winner. The candidate uses original-order f32 sums; the canonical arm retains its own four 15-frame chunks and left-absorption order. The two reductions must not be described as numerically identical algorithms.

The first draft omitted the production numerator scale: a finite `exp(80)` weight times a high-DN value can overflow f32. The corrected accumulator uses `sum(w*(v/65536))`, then rescales the quotient. Every numerator and unweighted sum is checked finite before the equal-tuple shortcut; denominator finiteness is checked at finish. Independent controls include unequal 60000/64000-DN tuples with finite extreme weights and a double-precision arithmetic reference, plus a denominator overflow case. These controls are prepared, not reported as passed.

Noise gating is not a noise guarantee. Above its floor this remains a selective mixture, and the full-photo finest exponent is capped at 8. The candidate also imposes that finest mixture on coarse structures and radiometric levels. Far/coarse loss, noise selection, weak color-only support and glint/edge changes remain plausible failures. The separate-depth and flat controls are essential; gradient gain cannot discharge them.

The initial generated receipt incorrectly used requested band count when reporting exponents. It now uses `sizes.len()-1`. The small structured fixtures have four AC bands and finest exponent 5.488, not the full photograph's seven bands/exponent 8. The independently prepared larger flat case reaches the exponent-8 cap without tuning the structured fixtures. It tests that noise regime only; it does not close the structured full-resolution transfer gap.

## Source-30 and complete-flat bindings

[full-adapter.rs](full-adapter.rs) pins all 60 DSC00016–DSC00075 identities, order, byte counts, mtimes and content hashes; the saved map; both retained full masters; and the export receipt establishing first-source WB. It checks reference 30, Catmull–Rom, all sources placed, current CA profile and complete-source support, quad crop `[25,17,3466,2310]`, and output 6932x4620. It does not replace the map's tiny reference roundoff with exact identity. Four execution threads, one reusable frame worker, unchanged seven-band configuration and one injected ISO-100 model are explicit. Per-frame WB is reported; the pinned first-source WB controls development. Exact tone bits come from the retained linear master's metadata.

The checkpoint decodes original index 30 while preserving original stack index/count for the actual preparation and probe. Both the candidate and canonical single-source input hull must equal the **CA-corrected gathered planes**, not the unwarped original CFA. The checkpoint checks identical delivered sensor, RGB16 and linear payloads. The originally redundant ordinary-writer comparison was strengthened: ordinary `write_merged_observed` also writes a linear master, whose decoded pre-tone payload must match the adapter's fixed-tone linear output. Thus the check covers the custom normalization seam; the automatic and held display tones are not silently equated.

For the complete run, canonical decoded RGB16 **and** float RGB payloads must reproduce the held full baseline before a successful receipt can be emitted. The baseline and candidate sensor masters retain signed black-subtracted values before WB/MHC/development. Original files, map, order, held masters and executable are rechecked at the end. A failed/partial run cannot borrow the completion receipt's unchanged-input assertions. No prior flat sensor master exists here to establish a separate held CFA-payload identity.

## Wrapper and display review

[run.py](run.py) binds build sources and the frozen executable, requires a fresh affected compilation, and runs exactly one ignored test with clean environment and explicit 120s/4GiB screen, 120s/8GiB checkpoint or 600s/12GiB full bounds. The flat route leaves ordinary CA enabled. Whole-host CPU/GPU samples are appropriately not presented as process-exclusive performance. The wrapper does not make a quality-based automatic release decision.

[prepare-views.py](prepare-views.py) now parses the successful full receipt, binds the actual arm master paths/hashes/byte counts, requires equal ICC bytes, and permits a byte-identical null candidate. It preserves the delivered tone, exports complete photographs, and reads back all eight frozen 384-pixel native subarrays without resampling. This verifies export correspondence, not perceptual quality. Complete-image inspection must still precede those witnesses and retain the full Helicon comparisons.

Frozen source SHA256 values reviewed:

| File | SHA256 |
| --- | --- |
| implementation.rs | `b945db40b901d3a9306d434388aff6a5afa6a2795e327c2f8f54f305c00d3b65` |
| full-adapter.rs | `b5ef9e8518f7ab3cd355c3a5e37e56ef67a9ad3b5f48bb8b449a2c0a04262150` |
| run.py | `54e44e56a2586b5056742bbe700e44fdb3b05bc5582d5478bceca1e79efb1dd6` |
| prepare-views.py | `067d7cdbd694b933eb97a35702a60a6f43a656275db32c1e3325c8d2da006cf2` |

The [independent control plan](independent-plan.md) owns the separate photographic-risk guards. Passing either operator or writer checks establishes correctness of the tested path, not genuine detail recovery, SOTA quality, or completion of the user's corpus goal.

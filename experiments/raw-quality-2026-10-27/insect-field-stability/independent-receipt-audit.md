# Independent receipt audit: fixed per-step field refused

2026-10-27. **VERIFIED saved evidence.** The declared hypothesis failed with complete training and primary held populations. The runs and artifacts completed successfully; that is separate from `stability_pass=false` and `REFUSED_FIXED_PER_STEP_HYPOTHESIS`. No new numerical evaluation, RAW read, source edit, or follow-on investigation was performed for this audit. The frozen [source review](source-review.md) remains unchanged.

## Authority and preservation

Root's exact commands and bounds are retained in the [control process receipt](../../../outputs/raw-quality-2026-10-27/insect-field-controls-1/process.json) and [actual process receipt](../../../outputs/raw-quality-2026-10-27/insect-field-actual-1/process.json). They run the frozen `controls.py` and `analyze.py` through Python with `-B -X faulthandler`, one worker and the declared fresh outputs. Both exit 0 with terminal job accounting, no process error or cleanup error. Controls took 0.718s with 24,784,896 bytes peak job commitment; saved-data analysis took 2.328s with 23,658,496 bytes. These are diagnostic-job timings, not full stacking performance.

Read-only SHA256/length verification checked **65 unique bound files, 252,831,074 bytes; every binding matched**. This covers current source bindings, both completions' artifacts, generated fixtures/results, and the actual analysis's saved observer/summary/support inputs. No `.ARW` was opened. Original preservation remains the preceding bound observer's before/after evidence, not a new original-file census.

The actual [receipt](../../../outputs/raw-quality-2026-10-27/insect-field-actual-1/output/receipt.json) has SHA256 `8ea62a78e4547d2d540fb2e9d6846aa2e8f20c5a54322a8f113d6459d1810a97`; root completion is `36ea2981dbac00649281d550b1415bf2a67beafb0822b1cf821667f0c4796b93`. The operator remains the reviewed `b0205a3e…`; input preservation, mechanical completion and source-disjoint flags are true. Attribution, physical claim, quality claim and admission are false.

## Completed controls and actual refusal

All [generated control checks](../../../outputs/raw-quality-2026-10-27/insect-field-controls-1/output/controls.json) pass: zero/noise refusal, stable positive recovery, all-correlated training mean, reversed held signal, wrong site/span, missing/omitted rows and acquisition-overlap rejection. The identical-data persistent-bias lookalike also passes while attribution stays false, demonstrating the intended limit.

The actual inventory contains all 7,020 pair/site rows. Each site has all 88 training vectors; site 15 includes its 15 MAD outliers as predeclared. Every primary cell has all 95/88 or 74/67 expected vectors and zero missing residuals. **Only the two site-41 cells in the primary held interval pass; all six replication cells fail.** Saved relative MSE reductions versus the zero predictor are:

| Site | Primary span 1 / span 8 | Replication span 1 / span 8 |
| --- | --- | --- |
| 15 | −1100.0% / −589.4% | −1599.8% / −62.6% |
| 41 | +33.1% / +34.0% | −113.1% / −156.9% |
| 56 | −312.0% / −121.1% | −465.1% / −122.4% |

Positive requires at least +20% in every cell. Negative values mean worse prediction than zero. The adverse span-32 counts remain explicit: primary site 56 has no valid vector; replication sites 15 and 56 have none. They were neither substituted into the primary gate nor hidden as successful observations.

**Decision:** close this exact constant per-step measured-residual hypothesis. Its failure does not identify the cause of softness or reject all focus-dependent geometry. These residuals share the producing similarity estimator, acquisitions and possible defocus bias; map overlap remains conditional support. No field correction, richer fit, replacement site, optical attribution, or photographic improvement follows from this result.

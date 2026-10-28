# Independent source review: fixed measured-field stability

2026-10-27. **VERIFIED source; no numerical execution.** No blocker found for the single bounded generated commissioning and saved-data test in [brief.md](brief.md). This is a six-scalar matcher-residual hypothesis, not an alignment correction or photographic admission.

Reviewed frozen sources:

| File | SHA256 |
| --- | --- |
| [analyze.py](analyze.py) | `b0205a3ec0f258011be4068de04a60fe5af90ec64cf8ee36100cf886d496cec1` |
| [controls.py](controls.py) | `8d14f8cc7fee64ebdbf2790c65078db141039a90627eef9e939b511c0cd4b54b` |
| [run.py](run.py) | `4092daaf6cae4b0f51cc2c099c2c28f0cfe35bc2c337b3eca5b75571470f4949` |

## Quantity, inventory and split

The loader joins the bound summary's descriptive f64 measured-minus-final-similarity vectors to the actual trace status and MAD mask. It does not recompute NCC, fit a second similarity, substitute a scalar RMS, or treat a missing final fit as zero. All 2,340 pairs at all three fixed sites yield exactly 7,020 rows, including uncorrelated and never-attempted records. The support table must join the same statuses and observation; neither overlap, historical-map scale nor peak magnitude selects or rescales the fitted data.

Training averages every available span 8 vector divided by 8 with both source indices in 0..95. Later MAD outliers remain included. The affirmative gate additionally requires complete training. Both held endpoints must lie within 112..207 or 224..298; `validate_disjoint` rejects any shared acquisition. Every primary site/span must retain 95/88 or 74/67 actual vectors respectively. A refusal or absent final residual makes that cell incomplete even when the remaining vectors predict well. Zero-null energy is nonaffirmative. All nine spans and unused/cross-boundary populations remain in the census; span 32 never becomes a substitute primary arm.

The per-step vector is expressed in each pair's source-i guide coordinates. No global-map normalization or physical-depth conversion is introduced. Therefore rejection concerns this particular coordinate-stationarity hypothesis, not every possible geometric defect.

## Producing controls and execution boundary

Controls call the actual fit/scorer with fixed complete inventories. Zero and known shared-acquisition noise precede a structured positive. An independently written literal 88-row mean checks that deterministic MAD flags cannot remove training rows. Held reversal, wrong-site and wrong-span coefficients traverse the same scorer. Missing-primary, omitted-row and acquisition-overlap controls challenge population admission. The unchanged positive relabeled as a persistent matching bias must also pass numerically while all attribution/physical/quality flags stay false; this explicitly demonstrates non-identifiability of cause.

The runner binds source/dependency files and exact operator identity, requires completed passing generated controls before actual evaluation, and checks terminal child status and false admission flags. The saved-data job preserves a failed scientific stability decision as a complete diagnostic rather than converting process exit 0 into scientific success. One worker, 120s wall/CPU and 4GiB bounds remain root-owned. No author job, RAW read or new source photograph was executed for this review.

## Limits that survive a pass

Residuals share each pair's estimated similarity as well as source acquisitions; their dependence is stronger than an independent-row model. Consecutive 16-source blocks are descriptive and cannot support IID confidence or a camera-noise claim. The generated controls commission this arithmetic and gate, not independence or physical accuracy of real NCC. Conditional reference-i footprint overlap does not establish the matched moving-j structure, focus support, visibility or unchanged texture. Persistent defocus-sensitive matching bias can pass. Only a bounded original-structure check could follow a stable result; no field warp, optical attribution, wider basis, or photographic gain follows from this test alone.

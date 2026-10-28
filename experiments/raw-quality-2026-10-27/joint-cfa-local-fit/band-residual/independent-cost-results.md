# Flat checkpoint: numerical pass, visibly failed reconstruction

2026-10-27. **VERIFIED from saved output:** the complete neutral-flat result has dense colored striping and broad green/yellow modulation against uniform gray truth. This is already a serious image defect. The actual product baseline was unavailable at this checkpoint, so its relative quality guard correctly remains unavailable/false; this does not prevent observing the absolute failure. No full photograph or broader fourteen-fit campaign is justified by the cost pass alone. Root has held that campaign.

Complete128x128 independent truth:

![Flat truth](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/outputs/raw-quality-2026-10-27/joint-cfa-band-prepare-1/output/flat-neutral/truth-complete.png)

Complete128x128 candidate, with the identical fixed display and ICC:

![Flat candidate](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/outputs/raw-quality-2026-10-27/joint-cfa-band-cost-1/output/flat-neutral--candidate/complete-output.png)

The complete [delivered float field](../../../../outputs/raw-quality-2026-10-27/joint-cfa-band-cost-1/output/flat-neutral--candidate/output.npy) and [144x144 latent coefficients](../../../../outputs/raw-quality-2026-10-27/joint-cfa-band-cost-1/output/flat-neutral--candidate/latent.npy) are retained. I viewed both complete displays at native size. On the prospectively fixed central96x96, RGB RMSE is303.055DN, green36.516DN and chroma374.289DN. Mean errors are R−155.787, G+4.200, B−184.268DN. These are not merely an unviewed score or a slight noise tradeoff.

The solver nevertheless reaches the unchanged normal-residual criterion at45iterations:9.54052e−6, with objective nonincreasing and finite output. That establishes a numerical property of this weighted surrogate, not faithful radiance. The flat result does not identify which combination of admission, nullspace, minimum-norm choice and model approximation causes the image failure. Do not recast it as a tolerance failure or start an iteration/threshold campaign.

## Mechanical observations

The actual A/transpose dot error is1.90e−10 versus2e−5; the wrong-phase adjoint foil is rejected at.0842. Constant A error is max.001465DN/RMS.000322DN. Independent continuous Fourier/footprint predictions have per-phase RMS3.086,.020,.020,3.768DN, within the frozen noise-scaled model bars. This limited model check is not a calibration or complete signal-band guarantee.

Complete Haar transforms on128x128 and odd127x125 originals both have max roundtrip.015625DN and RMS about.00434DN, within.05/.01DN. Parseval/adjoint checks pass, and one-sided adjoint foils fail. Actual q=1 objective and gradient agree with the raw residual formulation to1.56e−7/2.98e−7 relative. Literal duplication changes normalized objective/gradient by2.65e−8/1.12e−7; no duplicated-data fit or information-gain claim was made.

The wrong reference-footprint construction fails the physical-coordinate check by.004656native pixel; its prediction effect is only.243DN RMS. Keeping that separate from the larger noise-scaled model tolerance was necessary. High/tiny norm representations, common metric scaling, zero initial residual, clipped-input refusal, missing-phase domain refusal and unsupported footprint refusal pass. All five actual guard destroyers reject added flat noise, far/weak-green erasure, false green and overcontrast. Sharp red alias cancellation survives u16 quantization. The visibility128/256pupil comparison is descriptive: RMS.665DN, max19.374DN; no visibility fit ran, and its finite target cell areas are exact.

## Executed scope and cost

Root ran Python3.12 with`-B -X faulthandler`, `controls.py --stage cost`, the prepared fixture manifest, and operator SHA`536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac`. The full [invocation](../../../../outputs/raw-quality-2026-10-27/joint-cfa-band-cost-1/invocation.json) records exact paths and environment. A preceding prepare attempt stopped before imports/output creation because `operator.py` shadowed the standard library; root renamed it `sensor-operator.py` without changing its content, then prepared all ten fixed fixtures successfully. No numerical result is attributed to that failed attempt.

Cost job exit0,16.344s,3,216,637,952bytes peak commitment, four CPU workers and no cleanup error. It includes primitives, guard commissioning and only the neutral-flat candidate. The image fit used3.769s preparation and3.708s solver/reference-cell integration; saves/displays/scoring are separately timed. Root's conservative projection167.063s is below the300s budget but is not a measured full-screen time or scientific qualification. The controller's separate135.062s estimate is also explicitly a projection; neither converts the visible flat failure into a pass.

The other nine candidate fits and four solved foils have not run. Neither depth coexistence, weak-green preservation, alias-diverse recovery nor practical full-image integration has passed. A posthoc actual-product comparison may score this exact saved field; no repeat candidate fit is needed. No RAW read, reconstruction rerun, new crop search or source edit occurred during this review.

## Actual product comparison of the same saved field

**MEASURED / VERIFIED, later on 2026-10-27:** root completed the separately built actual-product baseline and the [saved-field review](../../../../outputs/raw-quality-2026-10-27/joint-cfa-band-saved-review-1/output/review.json). The candidate was not fitted again; its score reproduces exactly. I inspected the complete truth, complete 128-square candidate and complete supported 96-square baseline at native display size. The product baseline remains nearly uniform gray with fine noise. The candidate retains obvious regular colored striping and broad color modulation.

![Complete actual product baseline](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/outputs/raw-quality-2026-10-27/joint-cfa-band-saved-review-1/output/baseline-complete.png)

| Same central 96-square reference cells, DN | Actual product | Saved candidate | Unchanged candidate limit |
| --- | ---: | ---: | ---: |
| RGB RMSE | 10.5381 | 303.0554 | 12.0919 |
| Green RMSE | 12.4924 | 36.5161 | 14.2416 |
| Chroma RMSE | 8.8173 | 374.2888 | 10.1990 |

All three existing error guards now have an available actual reference and fail. The [actual camera-RGB DN master](../../../../outputs/raw-quality-2026-10-27/joint-cfa-band-baseline-1/output/flat-neutral/camera-rgb-dn.f32le) is 96×96×3 f32, with origin (16,16); its receipt binds the original source order, bytes and exact consumed phase-noise bits. The product final MHC reflects at this crop edge, while the candidate's scored region is interior to its complete 128-square field. This boundary/context difference is retained, not treated as a basis-isolated comparison. It does not invalidate the independently visible whole-field flat defect.

The review command is recorded verbatim in the linked receipt; it invoked `review-cost.py --cost-dir .../joint-cfa-band-cost-1 --baseline .../joint-cfa-band-baseline-1/output/receipt.json --out .../joint-cfa-band-saved-review-1/output`. The owned job exited 0 in 2.468 seconds with 1,004,085,248 bytes peak commitment. It imported no sensor operator, performed no reconstruction, verified retained bindings and unchanged originals, and kept photographic admission false. The unchanged recipe remains rejected; constant deflation is a separately allocated, prospective solver question, not an amendment to these failed results.

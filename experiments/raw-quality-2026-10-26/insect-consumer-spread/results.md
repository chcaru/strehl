# Fixed consumer-spread observation refused

**MEASURED, negative discriminator result.** All four fixed source143/source149 by G1/G2 comparisons against the complete CA-off stack returned `REFUSED_HELD_TRANSFER`. This does not identify blur, placement error, a capture ceiling, or a reconstruction defect. The fitted zero-spread values are parameters of a rejected family, not measurements that blur is absent. Close this recipe without changing its thresholds, support, direction, or source references.

Root executed the frozen [discriminator](discriminate.py), SHA256 `487b2987b2cf291661346c32736b63891d8def9ace912a40030441863b8f40de`:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B -X faulthandler 'C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\experiments\raw-quality-2026-10-26\insect-consumer-spread\discriminate.py' --out 'C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\outputs\raw-quality-2026-10-26\insect-consumer-spread-1'
```

[Invocation](../../../outputs/raw-quality-2026-10-26/insect-consumer-spread-job-1/invocation.json) pins one thread for OMP/OpenBLAS/MKL/NumExpr. [Process receipt](../../../outputs/raw-quality-2026-10-26/insect-consumer-spread-job-1/process.json) records exit0, 0.640 s wall, 63,688,704 bytes peak job committed memory, no termination, and complete pipe drain. The script's internal timer was 0.218 s. No host-load comparison was recorded; these are execution receipts, not a competitive performance claim. Only retained CFA artifacts were read; no original RAW was decoded by this observation.

## Actual results

The [immutable nomination](feature-nomination.json) fixed one bristle at master `(1920,748,28,24)`, with separate along-shaft training and held sections, 22 sites each per phase. The source contrast below is the inverse-variance-weighted **training** SD, not a temporal noise estimate or held-section SD. All four comparisons passed the source-support and rank guards before failing transfer. Units are black-subtracted DN.

| Fixed source | Phase | Training source SD | Training RMSE | Held RMSE | Held RMSE / training SD | Gain | Offset DN |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 143 | G1 | 47.532 | 45.096 | 64.525 | 1.357 | 1.1665 | -17.803 |
| 143 | G2 | 46.864 | 44.604 | 64.480 | 1.376 | 1.1726 | -17.499 |
| 149 | G1 | 45.888 | 10.821 | 29.154 | 0.635 | 0.9317 | -6.130 |
| 149 | G2 | 44.873 | 11.956 | 24.808 | 0.553 | 0.9437 | -6.731 |

All selected normalized taps were `[0,1,0]`. Neither the substantial source143 training failure nor the source149 held failure supports interpreting their kernel moments. [Full results](../../../outputs/raw-quality-2026-10-26/insect-consumer-spread-1/result.json) retain every reference, phase, gain, offset, refusal and input hash. Bound inputs were unchanged. Original149-to-actual-gather149 green was exactly identity, including zero residual, in both phases. Original143 and gathered143 have different coordinate gauges and were not compared at matching array indices.

## Controls and limits

[Generated controls](../../../outputs/raw-quality-2026-10-26/insect-consumer-spread-1/controls.json) ran flat first and passed the prospective checks. Noisy-flat inputs refused support. Identity was exact. Added Gaussian sigma1 produced fitted spread 1.154/1.146 pixels. Crucially, a **pure 0.5-pixel displacement with no added physical blur** produced centroid 0.515 and apparent spread 1.091 pixels. This coarse sampled family cannot separate displacement from blur variance. The sharpening placebo was admitted as a local transfer with gain about1.235 and zero spread; it was not refused, and admission does not imply photographic quality.

The fixed [low-signal background candidate](../../../outputs/raw-quality-2026-10-26/insect-consumer-spread-1/actual-flat-first.json) refused support in both phases for all retained references before the bristle was read. This is not certified flat ground truth or a noise-calibration check. The actual target shifted eight columns refused every comparison, so that destroyer remained live.

G1/G2 are separate sampling phases, not independent noise replicates. The injected ISO100 model is the exact observer model, with gain0.22893773 DN/e, read noise4.2 e and levels512/15360. Its sigma was neither propagated through source143's gather nor fitted to merged noise; source/merge covariance is unknown. The held section belongs to the same short bristle, not another feature or field location. Its lower-right continuation joins the body boundary. No physical PSF, unique causal attribution, preserved-detail claim or image-quality improvement follows.

## Read-only check of saved patch geometry

**VERIFIED literal-array inspection after the run; no new fit or score.** [Saved arrays](../../../outputs/raw-quality-2026-10-26/insect-consumer-spread-1/complete-support-arrays.npz) contain the complete32x36 support including four-pixel halo. At fixed G1 local row `y=14`, columns `x=9,11,13,15,17` inside the nominated28x24 support are:

| Actual quantity | Five consecutive G1 samples, DN |
| --- | --- |
| Gathered143 | 143, 190, 218, 175, 92 |
| Gathered149 | 157, 291, 390, 197, 27 |
| Final signed sensor CFA | 114.35, 403.51, 417.05, 171.64, 12.00 |

The final peak is taller and more concentrated in this section than source143's, and differs along the shaft from source149. This is not a width estimate or proof of true detail: sharpening, selection, visibility and local radiance variation remain possible. It does show why source143's better-looking surrounding hair context cannot establish that it is the sharp truth for this particular bristle. A positive broadening model in the source-to-stack direction is not an adequate general description of these samples. The fixed training section also samples a different part of the varying shaft than the held section; its weighted SD must not be presented as their common signal scale. The independent visual reviewer confirms that the held section approaches the thickening/root and adjacent outline, while the training section lies nearer the isolated upper shaft. Changing support occupancy is plausible, but direct body intersection and its causal role in the residual are not established.

**Decision:** do not extend this metric or derive a sharpening/deconvolution setting from it. The smallest useful next action is to close the blur-attribution branch and evaluate a separately justified reconstruction intervention on complete photographs, preserving these arrays as a counterexample to assuming a neighboring source is the local sharp ceiling. This observation supplies no positive evidence selecting such an intervention.

The underlying complete299-source observer replay is unchanged photographic output: [complete view](../../../outputs/raw-quality-2026-10-26/weevil-107-sensor-ca-off/stack-full.jpg), [RGB16 master](../../../outputs/raw-quality-2026-10-26/weevil-107-sensor-ca-off/stack-master.tiff), [linear master](../../../outputs/raw-quality-2026-10-26/weevil-107-sensor-ca-off/linear-master.tiff), [signed CFA master](../../../outputs/raw-quality-2026-10-26/weevil-107-sensor-ca-off/sensor-master.tiff). Its [completion receipt](../../../outputs/raw-quality-2026-10-26/weevil-107-sensor-ca-off/completion.json) binds all299 inputs, fixed executable/map and exact byte identity of RGB16 and linear outputs to the prior CA-off result. No new photographic improvement is claimed.

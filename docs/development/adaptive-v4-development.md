# Adaptive V4: larger corpus and native execution

2026-10-22. **Development candidate, not production approved.** A larger original
model now predicts image-specific fields substantially better than a constant
profile. That does not make the resulting treatment good: the first independent
blind review preferred unchanged insect and mineral photographs over the current
experimental rendering. No learned profile is enabled in the editor.

This follows the [earlier prototype](adaptive-distillation.md). The original
[V4 tools](../../experiments/adaptive-distillation/README.md) accept an external
cache and contain no teacher, private images, recovered code or learned weights.
The [native runtime](learned-profile-runtime.md) is separate from both inference
and photographic policy.

## Data and color contract

**VERIFIED locally:** 4,105 candidate sources were audited read-only; 4,104 decoded.
Exact source/decoded identities and perceptual similarities were joined with
capture-group metadata. The refined allocation contains 3,504 training entries,
501 validation entries and 99 reserved entries, across 54 connected groups.
Those contain 3,498, 499 and 92 distinct source-file hashes respectively.
Absence of a perceptual-hash match does not prove scene independence. All earlier
prototype test subjects are now development data, not fresh acceptance evidence.

Only training/validation inputs received new teacher labels: 4,822 training and
692 validation examples after controlled variants. Repeated views, stack frames
and augmentations are not extra independent scenes. Reserved sources were used
for identity auditing, not model selection or teacher-output evaluation.

The predictor input is explicit: encoded sRGB storage, FP32 inverse transfer,
Bradford BT.709/D65 to linear ProPhoto/D50, and two unchanged scalar mask channels.
The contract digest is
`63a26739adaa9ecf8be76c7ea91a1f85eeb97f75619c4ae0279060c7c666287a`.
This corrects the previous prototype's declared display-RGB research domain.
It does **not** turn camera JPEGs or developed TIFFs back into a RAW pipeline.
Most source images are embedded camera previews; masks are controlled geometric
variants, not production semantic segmentation. Encoded-first resizing differs
from resizing a linear RAW tapout. Native HDR input behavior is not established.
All five validation groups contain embedded previews, with no complete stack
renders or verified scene-linear masters. An inventory label containing `master`
does not establish a linear color domain: the existing cache processes those
training files through the same RGB8/sRGB path. The validation table therefore
does not establish fidelity on the editor's actual scene-linear source.

## Model and executed run

The student uses a depthwise image encoder, spatial context, global image
statistics, FP32 gain fields, training-only mean/PCA color tables and a learned
coarse residual. A bounded memory-mapped loader streams batches rather than
putting the entire cache on the GPU. Training/PCA identities and content hashes
bind fitted statistics to the data; checkpoints use restricted weights-only
loading.

**MEASURED:** 339,682 parameters and 1,400,932 buffer elements occupy 6,962,456
FP32 bytes. The ONNX model is 7,072,834 bytes. This candidate is larger than the
5,895,891-byte local teacher; quality was prioritized over the earlier compression
target. No claim calls V4 the smaller model.

The run completed 6,000 steps, batch 12, on an RTX 5090; validation selected the
last checkpoint. The private research trainer and packaged public trainer have
identical numerical code. Both exporters produced the same trained model bytes:
`7f92ef40abb45341b067a8a8b7c03e5c9a2da9138f8a1734d4c73e8afd4fa3c1`.

An independent curve audit found that the exposure-family validation ratio was
best at step 3,000 and was 1.87% worse at step 6,000. The joint score improved
only 0.093% from step 4,500 to 6,000. These development observations do not support
extending the run merely because the joint best checkpoint was the last one.

## Validation fidelity, not photographic quality

**MEASURED by the packaged evaluator:** 692 validation rows, five validation groups.
Error is averaged within sources, then groups equally. The constant comparator
is fitted from training outputs only. Gains are log2-ratio error; color is raw
table-value error. Exposure is in the model's EV-like output units; a scalar
prediction error is not a measured final-image brightness error.

| Output | Student RMSE | Training-mean RMSE |
| --- | ---: | ---: |
| SDR gain | 0.08483 | 0.25135 |
| SDR background color | 0.02590 | 0.04017 |
| SDR subject color | 0.02597 | 0.04017 |
| SDR sky color | 0.02706 | 0.04389 |
| SDR exposure | 0.40739 | 1.03845 |
| HDR gain | 0.05051 | 0.18784 |
| HDR background color | 0.01487 | 0.02164 |
| HDR subject color | 0.01459 | 0.02130 |
| HDR sky color | 0.01538 | 0.02177 |
| HDR exposure | 0.47851 | 1.06607 |

All ten aggregate comparisons also beat wrong-image assignments. Mean error can
hide a conspicuous local failure or little image-specific variation. The largest
SDR gain-table error is still 15.81 stops, and the largest exposure errors are
1.68 SDR and 1.53 HDR units. These tails are retained, not excused by the mean.

A separate occupied-coordinate probe used 501 unperturbed validation images and
an explicit simplified exposure policy. SDR gain-only RMSE was 0.04964 stops,
versus 0.31415 with another image's map. Including each model's own exposure
raised total-correction RMSE to 0.36038; HDR was 0.56149. These measurements omit
color tables and use cached resolution. They cannot prove full-resolution
photographic fidelity or safety at coordinates reached by later edits.

## Native operation and packaging checks

**VERIFIED:** public PyTorch-to-ONNX comparisons passed all ten outputs. A separate
Rust/Tract 0.23.9 [native probe](../../experiments/adaptive-distillation/native-probe/README.md)
executed the trained model on a complete-photo predictor
input and agreed with ONNX Runtime within `rtol=2e-4, atol=2e-5`; maximum gain
difference was 7.28e-6. Its translated NNEF version produced identical output
bytes without compiling the ONNX file parser.

**MEASURED, isolated development process:** 24 warm NNEF calls had median
59.07 ms on the local CPU. This is not an app-latency or universal performance
claim. It excludes decoding, input preparation, full-image composition and
display. The native compositor's separate full-photo checks are documented in
the runtime report. No comparison of differently threaded runtimes is presented
as a speedup.

The public runner completed a synthetic ten-step train/export/evaluate sequence
with deliberately nonfinite test labels left unread. Independent controls reject
cross-split aliases, wrong color domains, invalid fields and changed cache files.
The public trained export's hash matches the research export, and the packaged
validation evaluator reproduces the table above. No reserved V4 test rows were evaluated.

```text
python experiments/adaptive-distillation/input-contract.py
python experiments/adaptive-distillation/runner-guard-smoke.py
python experiments/adaptive-distillation/student-v4.py
python outputs/ai-adaptive-production/smoke-v4-public.py
python experiments/adaptive-distillation/export-v4.py --cache outputs/ai-adaptive-production/cache-v4-linear --checkpoint outputs/ai-adaptive-production/v4-linear-development/best.pt --output outputs/ai-adaptive-production/public-v4-linear-export
python experiments/adaptive-distillation/evaluate-v4.py --cache outputs/ai-adaptive-production/cache-v4-linear --checkpoint outputs/ai-adaptive-production/v4-linear-development/best.pt --training-means outputs/ai-adaptive-production/v4-linear-development/training-means.pt --output outputs/ai-adaptive-production/public-v4-linear-evaluation.json --device cuda
```

The `outputs` paths are ignored local receipts, not downloadable fixtures.

## Open production boundary

The current simplified renderer applies exposure, gain, identity tone and color
tables. Static investigation established that the native reference pipeline also
has camera-dependent exposure compensation and nonlinear highlight handling
before color tables. A model-output match through the simplified renderer cannot
establish equivalence to the complete reference pipeline.

### Independent photographic decisions

**VERIFIED by independent visual review:** three development panels used whole
photographs followed by fixed native regions, anonymous candidates and duplicate
baselines. These are subjective photographic judgments, not universal quality
measurements. The reviewer recorded observations before receiving the identities.

- The first panel covered six photographs. Unchanged versions were preferred on
  all four developed macro subjects. Lifting the two dark interiors was useful,
  but a bright sign lost separation between its white arrow and cyan background.
- Fixed clamp and highlight-shoulder alternatives did not visibly repair those
  failures. No threshold was selected from this result.
- A gain-only treatment subtracting median log gain within a preregistered
  luminance region was more restrained, but
  did not establish useful spatial adaptation beyond simpler controls. The
  unchanged opal and neutral slide remained preferred. Several deliberately
  shifted fields introduced their own discontinuities; beating those damaged
  controls cannot establish meaningful scene correspondence.

One fine teacher/student preference reversed between panels even though all 36
corresponding whole/crop RGB arrays were byte-identical. That ranking was
withdrawn as reviewer uncertainty. A suspected new mark on the slide was also
withdrawn after native-resolution inspection found the mark in the baseline.
The robust macro rejection remains; neither correction is hidden to strengthen it.

A fourth, separately frozen panel used the actual 7032 by 4688 scene-linear insect
master. Eight arms included the saved current result and duplicate, direct-linear
display, both predictors at two fixed exposure-allocation endpoints, and a
scalar-only tone control. All eight whole photographs and 48 fixed native crops
were reviewed before identities were revealed. The current result and duplicate
were preferred. The teacher versions remained too bright/vivid; the student
versions were too subdued. Neither pair had a dependable improvement from
moving positive exposure into the nonlinear stage. The scalar-only control was a
viable flatter alternative, but did not beat the preferred current photograph.

This last experiment preserved the gain-query brightness scale while changing
only the declared linear/nonlinear exposure split. Both endpoints used the same
extrema cap, negative-input policy and color tables. Independent synthetic review
caught and fixed a near-black extrema error before rendering. The final synthetic
checks covered 210 channel-permuted cases; original source and frozen fields were
unchanged after complete-photo rendering. The experiment establishes sensitivity
under its explicit policy, not the unknown native exposure allocation or a
general quality result. The independent photographic review found no rescue on
this development image, so it does not justify enabling an AI profile.

### Paired input-domain check

**MEASURED:** a fixed selection of three distinct RAW source hashes from each of
the five existing validation groups compared the exact cached preview, the same
preview decoded before linear resampling, and a neutral clipped LibRaw RGB16
proxy. All 15 source hashes were unchanged. The proxy changes color, tone, WB,
scaling, decoder and possibly crop as well as transfer behavior; it is neither
an Adobe input nor the application's unclipped master.

The broad prediction that linear RAW inputs would make every head worse was
not supported. Relative to the linearly resampled preview, median per-source
error improved for both gain heads and all six color heads. Exposure errors
worsened on 9 of 15 SDR and 10 of 15 HDR sources, with three groups worse and
two better in each branch. A separate actual scene-master insect retained a
1.49416 SDR and 1.08991 HDR scalar discrepancy. It was not pooled into the RAW
pairs. These are predictor-output units, not measured final-image EV errors.

An independent review used per-source medians, group signs and absolute errors
against fixed means and same-group donors. It also checked RMSE where one-sided
residuals made a cyclic permutation's MAE equal by arithmetic. Some mean and donor
comparisons still fail. These results support neither a uniform domain-failure
explanation nor a claim that additional training will fix the photograph.

The commissioning controls passed; swapping red/blue and decoding after resize
both failed as intended. A nonconstant black/white fixture distinguishes the
correct linear result 0.5 from the incorrectly ordered result about 0.214.

Executed local investigations (private images and model remain ignored):

```text
python outputs/ai-adaptive-production/render-six-photo-native.py
python outputs/ai-adaptive-production/probe-shoulder.py
python outputs/ai-adaptive-production/anchored-gain-probe.py --commission
python outputs/ai-adaptive-production/anchored-gain-probe.py
python outputs/ai-adaptive-production/paired-domain-probe.py --commission
python outputs/ai-adaptive-production/paired-domain-probe.py --commission --sabotage-channel-swap
python outputs/ai-adaptive-production/paired-domain-probe.py --commission --sabotage-decode-after-resize
python outputs/ai-adaptive-production/audit-paired-domain.py
python outputs/ai-adaptive-production/scene-rolloff-probe.py --commission
python outputs/ai-adaptive-production/scene-rolloff-probe.py --commission --sabotage-identity
python outputs/ai-adaptive-production/scene-rolloff-probe.py --rois outputs/ai-adaptive-production/scene-rolloff-rois.json --output outputs/ai-adaptive-production/photographic-probes/scene-rolloff-v1
```

The paired probe's frozen plan and results are retained with its local receipt.
The three sabotage commands intentionally return failure.

Scene-linear and already-developed inputs require separate acceptance. Remaining
work includes an accepted photographic policy and reference rendering contract,
real semantic masks, fresh-scene review, UI/recipe integration, and end-to-end
interaction tests. More training photos alone do not close those gaps. No learned
profile is promoted, no release is created, and the reserved final test remains
unevaluated.

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
capture-group metadata. The refined allocation contains 3,504 training sources,
501 validation sources and 99 reserved sources, across 54 connected groups.
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

The six-photo development panel uses whole-frame views followed by fixed native
regions, anonymized candidates, duplicate baselines and deliberate clipping/color
failures. The macro rejection already prevents promotion. An original Strehl
highlight policy can be tested, but cannot be labeled a recovered native curve.
Scene-linear and already-developed inputs require separate acceptance. Remaining
work includes a useful photographic policy, real semantic masks, broader fresh
scene review, UI/recipe integration, and end-to-end interaction tests. More
training photos alone do not close those gaps.

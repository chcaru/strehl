# Adaptive model distillation prototype

Historical V1–V3 results. See [V4 development](adaptive-v4-development.md) for the
subsequent larger corpus, explicit linear input contract and native runtime checks.

2026-10-22. **VERIFIED:** an original student was trained, exported, and executed
independently of its local teacher. **Not approved as an editing profile:** the
held-out insect loses to a constant baseline on color and exposure, one mineral
has a large local gain-table discrepancy, and the complete photographic color
pipeline remains unverified. No Strehl UI option or default changed.

This extends the [static model investigation](rea-adaptive-investigation.md).
The [original experiment code](../../experiments/adaptive-distillation/README.md)
accepts an externally supplied cache. The repository includes no teacher asset,
recovery code, private photographs, cached predictions, or pretrained student.
The trained prototype and detailed evaluation remain local research artifacts.

## What was trained

The student starts with fresh parameters and learns ten outputs: SDR/HDR
spatial gain tables, three color tables for each mode, and two exposure scalars.
A small depthwise CNN feeds a multiscale spatial decoder and low-rank color
tables. The final candidate uses a 13-cubed coarse color grid with rank four,
interpolated to 32 cubed. Two shared fine-grid residuals are calculated from
**training-output means**, preserving static color-table curvature. They are
not teacher initializer tensors or spatial photograph detail.

**MEASURED:** 265,900 learned parameters occupy 1,063,600 FP32 bytes. Shared
buffers add 786,432 bytes. The exported ONNX file is 1,931,154 bytes, including
graph overhead, versus the 5,895,891-byte teacher: 3.05 times smaller.
The exported student SHA-256 is
`9d6856dc6f82494a44921ebc7f024111264fbf2398d014bb2e8ed294aa5eaea7`.

Three bounded development candidates were tried using validation only:

- A 9-cubed color grid was too restrictive. Its color error exceeded the
  full training-mean baseline even after learning.
- A 13-cubed grid improved color fidelity but retained a substantial static
  approximation error.
- The shared fine-grid residual improved that representation. This candidate
  completed 8,000 FP32 training steps, batch 12, on an RTX 5090. Checkpoint 2,600
  was selected by validation before test outputs were evaluated.

The first two candidates' interpolation probes do not establish a lower bound
for the final residual-plus-clipping model. No architecture or weights were
changed after inspecting the final candidate's test results.

## Data and scope

**VERIFIED:** a filename inventory found 25,737 image paths. The experiment used
476 selected photographs: 364 training, 40 validation, 71 test, and one
calibration control. Most inputs were embedded camera JPEGs from RAW files;
eight were existing complete stack renders or overviews. All source files were
opened read-only. Selected source size and modification time were checked before
and after decoding.

There are four deterministic input variants per photograph: unmodified RGB with
zero masks, a soft subject mask, and two controlled mask/exposure/color variants.
This yields 1,456 training, 160 validation, 284 test, and four control examples.
Only the original RGB/zero-mask variant is the primary test; perturbed variants
are reported separately. They are not extra independent photographs.

Entire trips and macro subjects stay in one allocation. The test has seven
groups: one travel group and six macro subject groups, including the insect,
minerals, and a flower. Exact cached-RGB hashes and a perceptual-hash distance
check found no cross-split matches among selected images. This does **not**
establish semantic scene independence: the unnamed training pool and broad trip
groups remain limitations. No claim treats hundreds of adjacent captures as
hundreds of independent subjects.

**UNVERIFIED:** correspondence to the teacher's native input color pipeline.
Cached RGB is normalized to 0..1 and stretched to 512 by 384; its camera look,
primaries, transfer, and preprocessing are not established as Adobe's. Subject
and sky inputs are controlled geometric/color proxies, not semantic segmentation.
All label calls and student reads use the same cached uint8 input divided by
255. Targets, parameters, buffers, and arithmetic are FP32; TF32/autocast are off.

## Held-out numerical results

The comparator was written independently of the student. It rejects missing
heads, malformed shapes, nonfinite values, and nonpositive gains. Controls detect
a doubled gain, a spatial reversal with an unchanged histogram, and added
texture on a flat input. These establish metric behavior, not photographic taste.

The strong constant baseline is the full per-output training mean, with gains
averaged in log space. MSE is averaged within each test group, then equally
across groups, before taking its square root. Gains are scored in log2 ratio
units; the exposure scalars' physical conversion is unknown and they are **not**
reported as exposure stops. Color errors are raw model-table units.

**MEASURED, original RGB variant only:**

| Output | Student RMSE | Constant baseline RMSE | Error reduction |
| --- | ---: | ---: | ---: |
| SDR spatial gain | 0.26161 | 0.32473 | 19.4% |
| SDR global color | 0.04075 | 0.05823 | 30.0% |
| SDR subject color | 0.04096 | 0.05793 | 29.3% |
| SDR sky color | 0.04419 | 0.06436 | 31.3% |
| SDR exposure scalar | 0.36343 | 1.23693 | 70.6% |
| HDR spatial gain | 0.12234 | 0.21896 | 44.1% |
| HDR global color | 0.02709 | 0.03005 | 9.8% |
| HDR subject color | 0.02628 | 0.02923 | 10.1% |
| HDR sky color | 0.02761 | 0.03077 | 10.3% |
| HDR exposure scalar | 0.50684 | 1.37567 | 63.2% |

All ten aggregate errors beat the baseline and mismatched-photo assignments.
That aggregate does not establish reliable image-specific fidelity:

- On the insect, **all six color heads and both exposure heads regress** versus
  the training mean. SDR color error is 13.1–17.8% higher; HDR color is 4.7–6.1%
  higher. SDR exposure error is 0.08328 versus 0.04513; HDR is 0.44068 versus
  0.32509. These are prediction errors, not measured image brightness changes.
- Fourteen of 70 original-variant group/head comparisons fail the local
  correct-photo-versus-wrong-photo assignment control. The ten aggregate passes
  must not hide these failures.
- A mineral's SDR gain discrepancy reaches **15.51 log2 stops** at table
  coordinate knot 3, row 78, column 0: teacher gain 0.0000394831 versus student
  1.83889. In that table, 2.33% of cells differ by more than one stop and 0.063%
  by more than four. Its actual photographic effect is unresolved; no claim
  that these coordinates are unused or safe is made.
- The exploratory 20% reduction target is not met by every head. HDR color is
  particularly weak. Averaging SDR and HDR must not erase that limitation.

Metrics can be fooled by nearly constant outputs, unoccupied color/brightness
coordinates, or large errors concentrated in small regions. Full output means,
per-group results, wrong assignments, maximum errors, and spatial plots expose
some of those failures. They do not replace a validated renderer or independent
complete-photograph review. The local contact sheets show input photographs and
model fields at brightness knot eight, **not rendered Adaptive photographs**.

## Export and performance

**VERIFIED:** ONNX structural checks and all ten output comparisons passed
against PyTorch on eight validation fixtures spanning all four mask variants.
Exact shapes and finite FP32 values are required; NaNs cannot pass equality.
Tolerance is `rtol=2e-4`, `atol=2e-5`. Maximum absolute differences were about
`1.25e-5` for gains, `5.37e-6` for color tables, and `1.06e-4` for exposure
scalars. Fixed-batch export emits a shape-tracing warning; it supports exactly
`[1,5,384,512]`, not arbitrary dimensions.

**MEASURED:** Windows, Ryzen 9 9950X3D, ONNX Runtime 1.28.0 CPU provider, four
intra-op threads, one inter-op thread, spinning disabled. Eight fixtures,
12 alternating-order rounds, 96 warm calls per model:

| Model | Minimum | Median | p95 |
| --- | ---: | ---: | ---: |
| Teacher | 26.94 ms | 27.58 ms | 28.42 ms |
| Student | 6.70 ms | 6.87 ms | 7.30 ms |

The median forward-pass ratio is 4.01 times. This excludes source decode,
semantic masks, full-resolution table application, color management, and UI
presentation. It is not an app interaction benchmark. The RTX 5090 was used for
training, not for this CPU timing comparison.

## Executed checks and local receipts

The full research run used the ignored local scripts:

```text
python -u outputs/ai-adaptive-distillation/train-student.py --steps 8000 --batch 12 --grid 13 --shared-residual --name student-v3
python -u outputs/ai-adaptive-distillation/evaluate-student.py --name student-v3
python outputs/ai-adaptive-distillation/ceiling.py --means outputs/ai-adaptive-distillation/student-v1/training-means.pt --grids 9 13 17
```

Public code was then separately exercised, including a small training cache
whose unused test labels deliberately contain NaNs:

```text
python experiments/adaptive-distillation/student.py
python experiments/adaptive-distillation/evaluation.py --commission --output outputs/ai-adaptive-distillation/public-evaluation-commission.json
python experiments/adaptive-distillation/train-student.py --cache outputs/ai-adaptive-distillation/public-smoke-cache --output outputs/ai-adaptive-distillation/public-trainer-smoke --device cuda --steps 10 --batch 2 --evaluate-every 5 --grid 13 --shared-residual
python experiments/adaptive-distillation/export-benchmark.py --cache outputs/ai-adaptive-distillation/cache --checkpoint outputs/ai-adaptive-distillation/student-v3/best.pt --output outputs/ai-adaptive-distillation/public-v3-export-validated --teacher outputs/ai-adaptive-investigation/private-model/adobe-look-local-research.onnx
```

The last command produced the timing table above. Exported student bytes were
identical across the research and public exporters. Additional guards rejected
a scene spanning training/validation and a nonfinite training label, while
leaving poisoned holdout labels unread. The public 10-step smoke verifies the
packaged path; it is not a repeat of the full 8,000-step training experiment.

Local receipts include the cache manifest, each candidate's configuration and
training history, `student-v3/independent-evaluation.json`,
`student-v3/worst-gain-diagnostic.json`, and
`public-v3-export-validated/export-benchmark.json`. They contain private source
identities and are intentionally excluded from Git. No research facts were
folded into `SYNTHESIS.md` from this prototype.

## Next acceptance boundary

Compression and standalone execution are demonstrated. Before adding an AI
profile to Strehl, establish the input/output color contract and full-resolution
application order, use representative semantic masks, address the local and
insect failures, and independently review complete rendered photographs with
highlight, flat-region, and color controls. If these test scenes influence the
next model, treat them as development data and reserve fresh scene groups.
More photographs alone do not resolve an incorrect rendering contract.

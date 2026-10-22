# Adaptive-profile distillation experiment

An original compact FP32 student that learns spatial gain maps, color tables, and
exposure scalars from externally supplied teacher outputs. This is research code,
not an enabled Strehl editing profile. It contains no teacher model, proprietary
weights, image corpus, decoder, or model-recovery tools. See the
[experiment report](../../docs/development/adaptive-distillation.md) for results
and limitations.

The student combines a small depthwise CNN, a multiscale spatial decoder, and six
low-rank coarse color tables interpolated to the required output grid. It starts
with fresh parameters and an analytical identity grid. Training-label means can
initialize its output heads. Optional `--shared-residual` retains fine **color
table** curvature from two shared training-output means; it does not recover
spatial image detail. Both learned parameters and these extra buffers count
toward model size.

## Dependencies

Python 3.10 or later, NumPy, and PyTorch are required. ONNX export and benchmarking
also use `onnx` and `onnxruntime`. Install PyTorch appropriate for your CPU/GPU.
Training and storage use FP32; mixed precision and TF32 are disabled. The trainer
keeps the selected training/validation cache resident on the chosen device, so
use a small corpus or `--device cpu` when GPU memory is limited.

## Supply a local cache

Create a directory containing `manifest.json`, `inputs.npy`, and one `.npy` file
for each named output below. No program here discovers images or obtains a
teacher for you. Produce the labels with a teacher you can use and record its
input conventions. Every teacher call must use exactly the tensor that the
student later reads, including color conversion, resize, masks, and quantization.

`inputs.npy` has shape `[N,5,384,512]`, either `uint8` or `float32`:

- `uint8` inputs are converted to FP32 and divided by 255 for both teacher and student.
- FP32 inputs are passed through without a scale change.
- The five channels are three image channels and two auxiliary mask channels.
  Declare their actual color encoding and mask semantics. The code neither
  infers these nor creates semantic masks.

All output arrays are FP32 and use the same record order:

| Output files, without `.npy` | Shape |
| --- | --- |
| `pgtm`, `pgtm_hdr` | `[N,16,96,128]` |
| `rgbt_0`, `rgbt_1`, `rgbt_2`, `rgbt_0_hdr`, `rgbt_1_hdr`, `rgbt_2_hdr` | `[N,3,32,32,32]` |
| `exposure`, `exposure_hdr` | `[N,1]` |

Gain maps must be positive. Color-table values must be in `[0,1]`, with `2e-6`
validation tolerance for floating-point rounding; loss targets are not clamped.
Every input and output must be finite. Exposure units and table-axis semantics
belong to the supplied teacher contract; a matching shape does not establish a
matching renderer.

A minimal manifest looks like this; provide enough scenes for meaningful evaluation:

```json
{
  "schema": 1,
  "domain": "Describe the teacher's image color encoding and preprocessing here",
  "masks": "Describe the two auxiliary mask channels here",
  "records": [
    {"group_id": "scene-a", "split": "train"},
    {"group_id": "scene-b", "split": "validation"},
    {"group_id": "scene-c", "split": "test"}
  ]
}
```

All frames, crops, and augmentations of a scene or complete focus stack must stay
in one group and split. The trainer rejects a `group_id` spanning splits. You
must also check duplicates and related captures before caching: different group
names do not make correlated photographs independent. Only training and
validation rows are loaded; test/control rows are left for frozen evaluation.
The ten outputs alone contain about 3.75 MiB per sample, before inputs and
training working memory.

## Train and export

Paths are explicit. Output directories must be new or empty.

```text
python experiments/adaptive-distillation/student.py
python experiments/adaptive-distillation/evaluation.py --commission
python experiments/adaptive-distillation/train-student.py --cache path/to/cache --output runs/student --device cuda --steps 2400 --grid 9 --rank 4
python experiments/adaptive-distillation/export-benchmark.py --cache path/to/cache --checkpoint runs/student/best.pt --output runs/student-export
```

Add `--shared-residual` to training to preserve the shared fine-grid training-mean
residual. Add `--teacher path/to/compatible-teacher.onnx` to export/benchmark only
when you want a local teacher timing comparison. That ONNX model must expose one
FP32 input named `input` and the ten output names above. No teacher path is
hard-coded. Export uses fixed batch one and fixed spatial dimensions.

The trainer saves the initial warm start, then selects checkpoints using
validation errors against the full training-mean output baseline. Gains use
natural-log error; the standalone evaluator reports log2 gain-ratio error.
Per-head normalizers come only from training labels. Families receive balanced
weights instead of being weighted by tensor element count. The validation score
floors near-zero denominators; inspect absolute errors and the unfloored baseline
ratios as well. Fixed seeds do not guarantee bitwise repeatability across devices
or cuDNN versions.

The export script checks ONNX structure and compares every exported head against
PyTorch on validation fixtures before timing. It uses one CPU provider for both
models, warm-up calls, and alternating model order, and records raw timings plus
minimum, median, and p95. These are forward-inference measurements: no image
decode, mask generation, color rendering, or UI display is included.

## Evaluate the frozen model

For one photograph, save teacher and student outputs as two `.npz` mappings with
the ten exact keys and batch dimension one, then run:

```text
python experiments/adaptive-distillation/evaluation.py --teacher teacher-output.npz --student student-output.npz --output comparison.json
```

The evaluator rejects missing heads, wrong shapes, nonfinite values, and
nonpositive gains. Its commissioning controls include a spatial rearrangement
that preserves a histogram and added texture on a flat image. Compare frozen
predictions against a training-mean baseline on unseen **scenes**, including
mask counterfactuals and full-photo review with a validated common renderer.

Low tensor error can still hide lost image-specific variation, a wrong input
color space, or bad rendering. These tools measure imitation under a declared
contract, not photographic taste, clipping recovery, HDR display correctness,
or equivalence to another application's complete processing pipeline. No
renderer or pretrained student checkpoint is included.

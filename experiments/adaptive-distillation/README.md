# Adaptive-profile distillation experiment

Original FP32 students that learn spatial gain maps, color tables, and exposure
scalars from externally supplied teacher outputs. This is research code,
not an enabled Strehl editing profile. It contains no teacher model, proprietary
weights, image corpus, decoder, or model-recovery tools. See the
[experiment report](../../docs/development/adaptive-distillation.md) for results
and limitations.

The later [V4 development report](../../docs/development/adaptive-v4-development.md)
records the larger-data run and its unresolved photographic acceptance boundary.

Two generations are retained:

| Tools | Purpose |
| --- | --- |
| `student.py`, `train-student.py`, `export-benchmark.py` | Earlier V1–V3 compact coarse-table experiments; device-resident cache |
| `student-v4.py`, `train-v4.py`, `export-v4.py`, `evaluate-v4.py`, `input-contract.py` | V4 fidelity experiment; full-grid training-output PCA and streamed cache with an explicit color contract |

Neither generation is an accepted UI profile or evidence of production image
quality. The scripts use compatible tensor shapes, but **different input color
contracts are not interchangeable**. The V4 instructions are below the earlier
experiment instructions; they do not migrate old labels or checkpoints.

The V1–V3 student combines a small depthwise CNN, a multiscale spatial decoder, and six
low-rank coarse color tables interpolated to the required output grid. It starts
with fresh parameters and an analytical identity grid. Training-label means can
initialize its output heads. Optional `--shared-residual` retains fine **color
table** curvature from two shared training-output means; it does not recover
spatial image detail. Both learned parameters and these extra buffers count
toward model size.

## Dependencies

Python 3.10 or later, NumPy, and a recent PyTorch supporting
`torch.load(..., weights_only=True)` are required. ONNX export, benchmarking,
and V4 evaluation also use `onnx` and `onnxruntime`. Install PyTorch appropriate
for your CPU/GPU. Training arithmetic and output fields use FP32; mixed precision
and TF32 are disabled. RGB/mask input storage may be uint8. The V1–V3 trainer
keeps the selected training/validation cache resident on the chosen device, so
use a small corpus or `--device cpu` when GPU memory is limited.

## V1–V3: supply a local cache

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

## V1–V3: train and export

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

## Evaluate one frozen output pair

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

## V4: explicit input contract

V4 adds a stronger spatial decoder and predicts coefficients of full-resolution
color-table bases fitted from **training output labels only**. Each role retains
its training-mean table; a learned coarse residual supplements the shared PCA
basis. Neither teacher parameters nor teacher implementation are loaded into
the student. PCA bases and fitted means are buffers and count toward model size.
The model exposes optional rendered-loss hooks; the supplied trainer does not
activate a renderer or invent an interpretation of the exposure outputs.

The ten output files and tensor shapes remain those listed above. For the new
`linear-prophoto-d50-bradford-from-srgb-v1` contract, `inputs.npy` still stores
**encoded sRGB pixels**, followed by subject and sky weights. Use uint8 in
`[0,255]`, or FP32 in `[0,1]`, consistently across all five channels. The helper
scales to FP32, decodes the sRGB transfer, and converts BT.709/D65 to linear
ProPhoto/D50 with the declared Bradford matrix. Mask values are only scaled.
Do not put already-linear ProPhoto pixels in this storage format: that would
apply the conversion twice. Linear uint8 storage is not supported.

Every teacher label must have been produced from
`input-contract.py`'s `prepare_numpy(stored_batch, descriptor)`, or an independently
verified equivalent operation. The trainer uses `prepare_torch` lazily on each
batch. Both implementations have analytic color and cross-implementation
commissioning controls. Resizing happens **before** these helpers; record its
filter, coordinate convention, aspect policy, and whether it operates on encoded
or linear pixels. The descriptor does not establish those choices for you.

This contract describes normalized SDR source pixels. The presence of HDR output
heads does not validate HDR inputs. Inverse-sRGB conversion cannot undo camera
profiles, baked tone curves, clipping, or prior local adjustments. Applying the
same shape-compatible model to a RAW-development tapout or a developed TIFF can
therefore be a substantial domain shift. No Adobe pipeline equivalence follows
from the color-space conversion alone.

The explicit `display-rgb-research-v1` contract preserves the older scaled-RGB
experiment for compatible external labels. It must be declared, never inferred
from an image filename or private cache identifier. Comparing an old checkpoint
with V4 requires matching input contracts; changing metadata alone cannot make
an old model or its labels compatible with a new domain.

## V4: manifest and split requirements

The manifest must include the full supported `model_input_contract`, its canonical
`model_input_contract_sha256`, and `records` in array order. Generate the contract
fields with the helper instead of transcribing its floating-point coefficients:

```python
import importlib.util
import json
from pathlib import Path

helper = Path("experiments/adaptive-distillation/input-contract.py")
spec = importlib.util.spec_from_file_location("input_contract", helper)
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)
descriptor = contract.contract_descriptor(storage_dtype="uint8")
manifest = {
    "schema": 1,
    "model_input_contract": descriptor,
    "model_input_contract_sha256": contract.contract_sha256(descriptor),
    "preprocessing": "Record the actual resize, orientation and source-development policy",
    "records": [
        {"group_id": "scene-a", "source_id": "photo-a", "variant": 0, "split": "train"},
        {"group_id": "scene-b", "source_id": "photo-b", "variant": 0, "split": "validation"},
        {"group_id": "scene-c", "source_id": "photo-c", "variant": 0, "split": "validation"},
        {"group_id": "scene-d", "source_id": "photo-d", "variant": 0, "split": "test"},
    ],
}
Path("path/to/cache/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
```

This tiny manifest illustrates the schema, not adequate training diversity.
Provide a stable `source_id` for every original photograph, sharing it across
augmentations, and a `group_id` joining related captures, retakes, crops and stack
revisions. Optional `path`, `paired_display_render`, `source_sha256` and
`decoded_sha256` strengthen cross-split checks; paths are identity metadata and
are never opened by these tools. Audit physical-scene relationships and duplicates
independently: absent or renamed metadata cannot prove independence.

Training and validation splits must both be nonempty. Evaluation needs at least
two distinct validation sources for each selected `variant` so its wrong-image
control can exist; cross-group donors are preferred. Training rejects known
group/source aliases crossing any split. Training reads only train/validation
row values; export and evaluation read only validation row values. Array headers,
file metadata and manifest identities may describe the entire cache, but no test
or control row values are indexed. There is no public override to reopen test
data during model selection.

All labels must be finite. V4's default gain support requires
`abs(ln(gain)) <= 12` and strictly positive gains; out-of-support labels fail
preflight. Color tables allow only the existing `2e-6` numerical tolerance around
`[0,1]`; targets remain unchanged. Those are model-domain limits, not photographic
quality thresholds. Exposure remains in the supplied teacher's output units.

Optional `category: "macro"` identifies macro groups; `group_id` beginning with
`macro-` is also recognized. `kind` beginning with `complete_stack` identifies
complete renders within such groups. The default sampler gives macro groups
half the training mass when both macro and general photos exist, balances macro
physical groups, and gives complete renders 70% of their group's mass when both
complete renders and other captures exist. Repeated variants do not create extra
training weight. Adjust `--macro-share` and `--complete-share` for your corpus;
these sampling choices are not universal defaults for photographic taste.

## V4: stream, export and evaluate

V4 memory-maps the arrays and transfers batches to the selected device. Unlike
the V1–V3 trainer, it does not place the whole cache on the GPU. Training means,
normalizers and PCA are fitted only from training rows. PCA reuse is bound to the
manifest, selected rows, input contract, weights, rank and training-array content
hashes. File receipts detect ordinary cache replacement during a run. Keep the
cache immutable while any training or evaluation process is using it.

```text
python experiments/adaptive-distillation/student-v4.py
python experiments/adaptive-distillation/input-contract.py
python experiments/adaptive-distillation/runner-guard-smoke.py
python experiments/adaptive-distillation/train-v4.py --cache path/to/cache --output runs/v4 --device cuda --steps 6000 --batch 8 --rank 8
python experiments/adaptive-distillation/export-v4.py --cache path/to/cache --checkpoint runs/v4/best.pt --output runs/v4-export
python experiments/adaptive-distillation/evaluate-v4.py --cache path/to/cache --checkpoint runs/v4/best.pt --training-means runs/v4/training-means.pt --output runs/v4-evaluation.json --device cuda
```

Use `--device cpu --workers 0` for a CPU training run. Output directories must be
new or empty; the evaluation output file must not exist. The first three commands
exercise small synthetic controls and do not open photographs or teacher labels.
They are necessary checks, not evidence that the model improves photographs.

The trainer saves `best.pt`, `training-means.pt`, `pca-fit.pt`, cache receipts,
configuration and validation history. Checkpoints use restricted
`weights_only=True` loading. Evaluation verifies the exact training-mean file
digest stored in the checkpoint; substituting another run's mean is rejected.
Training scores natural-log gain error and averages rows within each validation
group, then groups equally. The standalone evaluator reports log2 gain error,
first averaging variants within a source, then sources and groups. Unequal
variant counts can therefore change their aggregation; inspect per-group and
per-head values alongside the headline score.

The exporter checks every head's exact FP32 shape and finiteness and PyTorch/ONNX
agreement across each validation group/variant plus synthetic mask cases. It
exports fixed batch one, then measures CPU forward calls. Timing excludes image
decoding, preprocessing, rendering, upload and UI interaction. The evaluator adds
training-mean and wrong-image controls, per-group errors and tail statistics.
`--v3-checkpoint` optionally compares a compatible earlier model; its default
source is the sibling `student.py`. It never silently changes the model's input
color domain.

Low uniform tensor error can hide rare, conspicuous defects or errors at lookup
coordinates the image does not visit. Low occupied error can hide damage that a
later edit will expose. Neither establishes useful exposure, preserved highlights,
plausible color or a good interactive experience. Independent full-photograph
review, fixed controls, a validated rendering contract and untouched final scenes
are still required. These tools do not select a UI profile, enable learned editing,
or establish production quality.

## Public V4 packaging differences

The optional [native inference probe](native-probe/README.md) runs the exported
model in a separate Rust process, translates it to NNEF, and permits a build
without the ONNX file parser. It records exact field hashes and timings, without
adding an inference runtime to the application or claiming photographic quality.

The V4 architecture, losses, training loop, PCA fitting and exporter retain the
research implementation. Public packaging changes only nonnumerical access paths:
the optional V3 source defaults to the sibling file; all caches require an explicit
input descriptor; and the evaluator accepts validation rows only. Private-cache
identifier exceptions and historical test-reclassification switches are omitted.
Synthetic Windows path strings in guard tests exercise alias normalization; they
are fictional and are never opened. No teacher model, decoder/recovery code,
training weights, private paths or dataset is included.

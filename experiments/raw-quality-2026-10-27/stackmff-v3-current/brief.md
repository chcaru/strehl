# Current learned selector: source review and practical comparison

Root allocation, 2026-10-27. The exact fixed insect residual hypothesis failed.
Do not prolong that narrow analysis. Investigate the newly released October2026
StackMFF V3 as a deterministic comparison on the complete weevil stack, to
test whether a different spatial focus decision produces a useful photograph.
This is an external developed-image comparator, not a replacement for Strehl's
original-CFA reconstruction contract. No generated restoration, diffusion,
training, private-image upload, product integration or default change.

## Prior work and changed question

Root ran both unified and mechanical searches for StackMFF / learned focus /
regression. Read `experiments/stackmff-v4-evaluation/{decision,results}.md` and
`experiments/quality-september25/stackmff-readiness.md`. The old three-source
384px marigold V4 hard-selection pilot showed patch seams and was rejected.
It neither tested this redesigned model nor its default soft fusion nor a
complete insect stack. The new official V3 release is materially different:
source-probability fusion with spatial smoothing and two inference scales.
This is not permission to repeat the old frozen pilot or tune it.

Verified upstream commit `6e1d7211f7634f60245706ebe3b839b320df9d00`, 2026-10-24,
in [the official repository](https://github.com/Xinzhe99/StackMFF-V3).
The actual LICENSE is MIT, Copyright2026 Xinzhe Xie; third-party notices
separate code from training data/benchmark rights. Download only inference
code, its own checkpoint, licence/notices and necessary metadata into ignored
outputs; retain all provenance. No benchmark images are needed. Use safe
weights-only loading and audit imports before execution. Public release claims
are not evidence of quality or practical cost on this macro corpus.

## Bounded source tasks

- cfa-residual: inspect the pinned MIT inference/model sources and give an exact
  source list, checkpoint identity, input quantity/defaults, spatial context,
  and practical all299 tiled/streaming route. Write `model-audit.md`. No imports,
  inference, package install or parameter changes. Identify whether faithful
  memory-bounded execution is possible before writing a new engine.
- integration-review: inspect retained weevil source-development manifests,
  held map and existing gather/export helpers. Write `input-bridge.md` with one
  concrete complete-stack input route, coordinate/crop/development contract,
  and cost/memory implications. No RAW/large-image numerical work or export.
- photo-review: independently challenge current model readout and whole-stack
  comparison; write `comparison-protocol.md` with compact live-model fidelity,
  noisy-flat and structured controls plus fixed whole-image/native witnesses.
  Preserve source detail at multiple depths and independent color. No jobs.
- root: pin/download sources and weights, choose a single executable method
  after source review, commission it, run bounded cost and complete photograph,
  present whole outputs/masters and independent assessment. Numerical execution
  remains root-owned. No photograph is claimed under this source-only stage.

Candidate defaults are upstream weighted fusion, scales(1,0.75), sigma0.5.
Do not substitute hard argmax. If a memory adaptation changes semantics,
report it and qualify it explicitly rather than calling it the official result.
Do not store an aligned full-frame volume. The eventual runtime must gather
only the consumer's bounded input region and retain image-sized outputs.

## Root implementation release

Root extends these same owners to `model-adapter.py`, `input-bridge.py` and
`controls.py`, respectively. No numerical jobs by authors. The source route is
the already retained 299 unaligned7032x4688 RGB16 TIFFs used for Helicon, gathered
into the held native6896x4596 crop. OpenCV's cubic RGB interpolation is explicit;
it is not native CFA/Catmull pixel parity. Keep legacy map gauge and original
RGB channel order, and commission both using actual producing-path controls.

Model execution uses original f32 weights with TF32 disabled, all299 sources
jointly in each bounded spatial context. Proposed256px cores and128px plugin
halo need nonvacuous whole-versus-tile control at both inference scales, plus
a wrong-halo foil, before use. No mixed precision or learned parameter change.

Root runs one controls job (300s), then one fixed all299 tile at core origin
(1792,512), twice unchanged for startup/repeat accounting (600s). Both have
24GiB host job commitment and24GiB maximum Torch allocation/reservation,
four CPU threads. Record complete-source hash checks outside the timed tile.
Only mechanically passing controls and a practical cost observation can release
one complete stack, bounded3600s/24GiB host/24GiB Torch. Exact full-job command
and source identities are saved by `run.py`. The fixed quality controls remain
visible even if failed; a complete observational comparator does not promote
those failures into a pass. No source-subsetting, lower-resolution substitute
or image-quality assertion follows from a fast cost tile.

The initial public-download command to `stackmff-v3-upstream-1` failed DNS at
the sandbox network boundary before any artifact download. The approved retry
to `stackmff-v3-upstream-2` completed: all seven Git blobs matched exact sizes
and Git SHA1; the658587byte checkpoint matched release SHA256
`39b2ea3738e8fea1676c379238d6be81a87988fc9952dbd6ac3825d5d7249f46`.
No package installation or model execution occurred during download.

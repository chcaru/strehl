# Four-step level-balanced original-CFA pilot

2026-10-27. SOURCE PREPARATION ONLY. Root owns execution and scheduling. Old
executed files remain unchanged. No source author numerical, RAW, CUDA, import
or build job was run. This is one deliberately changed objective with two
evidence-supported components; it is not a quality improvement or production
release. Independent controls and all complete photographs are still required.

## Producing changes

`bands-gpu.py` preserves physical R,G1,G2,B phase packing, seven-level limit,
support masks, replicated3x3 admission neighborhood, supplied marginal noise,
and original admission formula. It changes unequal lowpass support pairs to
the count-aware orthonormal rotation in the brief. Support counts are exact
f32 integers through these seven levels. Equal pairs retain the old arithmetic
expressions/order, including variance half-sums. Unpaired entries carry with
their true count; the inverse uses the transpose rotation. Variance uses the
squared rotation coefficients. Boolean support remains conjunction of every
nonzero participating original support; no reflected/padded data is invented.

`normal-operator.py` performs one raw source census before factors: per-level
Q/R and maxima are f32 CUDA scalars, accumulated in original source and packed
band order. The same admitted support defines Q and R. Seven shared AC
multipliers are R/Q; terminal LL remains unchanged. An empty Q=R=0 level has
multiplier0 and remains omitted. Nonfinite, negative, inconsistent-zero or
underflowed active mass/multiplier refuses. A scalar `metric_override` bypasses
level normalization solely for the existing total-metric mechanics null.
No-focus has a=1 and Q=R. Ordinary CLI always uses candidate/no override.

The actual helper seams used by production and independent controls are:

```text
HaarPlan(torch, observed_hw, origin_xy=(0,0))
  .forward / .inverse / .variance / .support
  .bands / .sizes / ._phase preserve the original packing
  .support_counts[physical_phase][level] = (y_counts, x_counts)
prepare_source(...) -> SourceBands with RAW, unbalanced metric
level_statistics(current) -> (Q[7], R[7], raw_max[7], raw_LL_max)
resolve_level_balance(torch,Q,R,metric_override=None) -> multipliers[7]
apply_level_balance(current,multipliers) -> same current with updated metric
StreamedProblem(...) -> existing Source/Noise/normal/rhs/restore/evaluate API
```

The constructor retains `level_Q_f32`, `level_R_f32`,
`level_multipliers_f32`; metadata `level_balance` records those plus raw maxima,
scope, formula and override status. Its initial `sources` records describe the
raw census, before global normalization. The common normalized qmax is the
maximum of each raw level maximum times its shared multiplier and untouched
LL maximum. Subsequent preparations recompute unchanged source statistics and
apply these frozen multipliers. No factor/source/coefficient volume is cached.

The frozen integrated original-sensor operator, actual A(ones), supplied noise,
clipping treatment, source order, N normalization, nuisance Gram/G, coefficient
projection and final true-normal/objective checks remain. This is not an exact
likelihood or a corrected full covariance model. Band correlations and
data-dependent admission remain. Relative source/spatial/color/orientation
weights within each level are preserved, not normalized per source. A flat at
the admission floor returns to1/V; no denoising guarantee is asserted.

## Solver and observational checkpoints

`solver.py` clones the executed normal-CG recurrence and true-final audit, with
maximum iterations4 instead of64. No preconditioner, restart, prior or change
to the1e-5 numerical bar. `fit(problem,checkpoint=None)` calls the optional
callback after complete finite iterations1,2,4. It supplies a private clone of
correction z and copied recursive-history metadata. Delivery errors propagate
as `CheckpointFailure`, never as a successful numerical stop. No checkpoint
pixels enter recurrence arithmetic. Each intermediate explicitly says that
true objective/convergence has not been assessed.

The final initial-constant and restored-X true checks remain exactly the old
two-pass evaluations. A finite iteration-cap result is saved with refusal. If
the solver stops early, existing photographs and final fields survive and the
receipt says the checkpoint schedule is incomplete; it neither forces extra
iterations nor copies one photograph to a later iteration. There is no automatic
extension beyond4.

## Complete source and development path

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-27/direct-cfa-level-balanced/photograph.py --out <fresh workspace output> --renderer-binding <delivery-build-4/executable.json> --development-receipt <delivery-controls-2/output/held-development.json>
```

The worker imports only hash-bound source-validation/telemetry helpers from the
executed full worker, frozen paired measurement and commissioned delivery.
All299 original caches are hashed/header-checked before and after; actual ARWs
are only stat-checked against their verified export. No RAW decode/write.
Source/renderer/development bindings are checked before/after, including
`views.source_dependencies()`. The original field4743x7109, origin(-34,-22),
reference149, all299 maps/noise and output(68,46,6896,4596) are unchanged.

Each `checkpoints/iteration-01`, `iteration-02`, `iteration-04` contains:

- Restored signed latent, quantity metadata and recursive-only checkpoint receipt.
- `delivery/camera-rgb-dn.f32le` plus exact final-cell integration receipt.
- `native/rgb16-master.tiff` and actual native developer receipt/logs/config.
- `views/complete-stack.jpg`, overview, all ten fixed native384 witnesses and
  their receipt/index, produced by photo-review's fixed presentation helper.

The same frozen native executable and held development are used at every
checkpoint. There is no retone, denoise, sharpening, remosaic or MHC. Signed
camera values are preserved through integration into the delivered f32 master.
After final true checks, `fit/` saves complete final X and correction z. The
last matching checkpoint latent hash must equal the final restored latent hash.
Previous native, HeliconB4/B8 and rejected64-step complete output references
are presentation-only; none enter the reconstruction.

Success status is `COMPLETE_LEVEL_BALANCED_FULL299_PILOT`, complete true,
source_count299, three checkpoint records and actual numerical status. Quality
claim and photographic admission stay false regardless of recognizability or
residual change. The pilot stops for independent complete-image review.

Root budget:1500s wall,6000CPU-seconds,16GiB host commitment,8GiB Torch
allocated/reserved, four CPU workers/one interop, f32, noTF32/autocast. Each
source pass and checkpoint is telemetered by pass-through wrappers. Intermediate
delivery runs while recurrence tensors remain live, so its peak memory is
explicitly part of the same cap. No new speed claim is made.

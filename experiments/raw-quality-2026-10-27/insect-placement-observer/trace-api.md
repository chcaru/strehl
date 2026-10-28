# Fine alignment observer API

Source preparation, 2026-10-27. Implementation: `strehl_core::align`, in
`crates/strehl-core/src/align.rs`. Root owns compilation and execution. No
numerical equivalence or physical-placement claim is made by this source edit.

```rust
pub fn align_pair_observed(
    reference: AlignFrame<'_>, moving: AlignFrame<'_>,
    spots: &[(usize, usize)], cfg: &AlignConfig,
    observer: Option<&mut dyn FnMut(&PairTrace)>,
) -> Result<StageFit, AlignFailure>;

pub fn fit_stage_observed(
    reference: PlaneRef<'_>, moving: PlaneRef<'_>, tile: usize,
    spots: &[(usize, usize)], radius: i32,
    seed: Option<SimilarityParams>, cfg: &AlignConfig,
    observer: Option<&mut dyn FnMut(&StageTrace)>,
) -> Result<StageFit, AlignFailure>;
```

Each enabled observer receives **one immutable completed record** per call,
including a refusal. It may clone that record into its pair-local collector.
The callback cannot change stage inputs or results. Existing `align_pair` and
`fit_stage` signatures remain; they enter the same internal implementations
with no trace. `None` allocates no trace vectors or config clones. The core
performs no trace serialization or file I/O.

All public trace structs derive `Clone, Debug`; `PairTermination` additionally
derives `Copy, PartialEq, Eq`. Fields are public:

```text
PairTrace
  fine_passes: Vec<FinePassTrace>
  selected_fine_pass: Option<usize>
  termination: PairTermination
  result: Result<StageFit, AlignFailure>

FinePassTrace
  index: usize                         # zero-based attempted pass
  stage: StageTrace
  corner_moved: Option<f64>             # existing convergence calculation only

StageTrace
  measurements: StageMeasurements
  result: Result<StageFit, AlignFailure>

StageMeasurements
  reference_dimensions, moving_dimensions: (usize, usize)
  plane_center: (f64, f64)
  tile: usize
  radius: i32
  seed: Option<SimilarityParams>
  config: AlignConfig
  warped_tiles_used: bool
  tiles: Vec<TileTrace>                 # original spots order, including failures
  initial_fit: Option<SimilarityParams>
  initial_residuals: Option<Vec<f32>>
  median, mad, cutoff: Option<f32>
  keep: Option<Vec<bool>>
  final_fit: Option<SimilarityParams>
  final_residuals: Option<Vec<f32>>
  census: TileCensus

TileTrace
  ordinal: usize                       # index in spots, not accepted observation
  probe: TileProbe                      # actual NCC call argument
  fit_center: (f64, f64)                 # literal tx+tile/2, ty+tile/2
  centered_offset: (f64, f64)            # fit_center minus plane_center
  measurement: TileMeasurement          # actual status/contrast/dx/dy/peak
  observation_index: Option<usize>
  observation: Option<Observation>      # copy from the producing obs vector
```

`initial_residuals` and `keep` index only correlated observations, as linked by
each tile's `observation_index`. `final_residuals` retain the original survivor
order (true entries of `keep`). `mad` is the actual floored MAD used by the
existing cutoff, not an independently recomputed statistic. `None` means that
the producing calculation did not execute; it is never a false rejection mask.
A singular initial fit retains tile/census data but no initial fit/residuals;
a singular final fit also retains the initial residuals and outlier decision.

Terminal variants and their exact meanings:

```text
CoarseGridTooSmall { level }
CoarseStageFailed { level, cause: AlignFailure }
FineStageFailed { pass, cause: AlignFailure }
FinePassFailedRetained { pass, cause: AlignFailure }
FineConverged { pass }
FinePassLimit
```

Coarse refusals have no fine passes or selected index. The outer result retains
the existing public error (including `CoarseStageFailed { level }`), while
`cause` retains the error previously discarded by its mapper. Fine failure on
pass zero has no selected pass. A later failed pass remains in `fine_passes`,
while `selected_fine_pass` points to the preceding successful pass and the
pair result remains successful. The first pass and failed passes have
`corner_moved=None`; only the existing successful later-pass calculation
supplies that value. One-pass configurations finish as `FinePassLimit`.

All numeric fields retain native `f32` / `f64` values, including genuine NaNs
in failed `TileMeasurement`s. The CLI serializer must store `to_bits()` beside
every float and use readable JSON null for nonfinite values. No NaN-to-zero
normalization belongs in the core. Pair IDs/ordinals, unavailable pyramids or
planes, serialization size limits, original guide/source hashes and global
map equality belong to the CLI adapter; core traces do not invent them.

The existing arithmetic is shared: one original NCC call per tile; unchanged
observation, fitting, MAD, residual and convergence expressions/order. Trace
copies occur after their producing calculations. Fine-stage iteration uses
the same helper with optional capture; coarse calls remain unobserved.
Recorded coordinate subtraction is descriptive only and never enters fitting.
Root must execute ordinary-vs-observed bitwise controls before using this
instrument, including failed/retained passes and complete global-map parity.

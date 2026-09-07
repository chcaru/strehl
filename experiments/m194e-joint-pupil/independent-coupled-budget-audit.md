# Independent full3 refusal and nested indicator-budget audit

2026-09-07. Diagnostic/source arithmetic and prospective design only. No
reference rerender, numerical source change, candidate trial or float/CFA
authority. Full3 remains a failed complete campaign; twelve completed frames
cannot substitute for the fifteen required arrays.

## Exact retained failure

The externally bound full-run3 result is
`38e691f130e830f9bfb2b21176049cbd98b15a2134b638a03ee8f6363566c89f`.
It is `UNCOMMISSIONED_NUMERICS` at cell-refined frame2, native cell(4,0).
Source and design bindings match before/after. The frozen author diagnostic
`cell-diagnosis-3/result.json` has SHA
`49902496359b6976776bb765e2228b36409d1df2e20bd405a11d8ece1732093f`.
It records both initial roots and every terminal leaf, not a selected subset.

`independent-coupled-budget-read.py` imports no renderer and evaluates no new
optical samples. It independently reconstructs the unit cell's two initial
triangles and every longest-edge bisection from each immutable binary path.
The two initial paths and all128 distinct depth6 terminal paths form complete
partitions. Every saved triangle, area, depth and numerical leaf term agrees.
Canonical `math.fsum` reproduces all recorded totals exactly:

| Quantity, electrons | Initial two leaves | Terminal128 leaves |
| --- | ---: | ---: |
| Area | 1 | 1 |
| Sum absolute cell low/high delta | 9.094947017729282e-13 | 2.1316282072803006e-12 |
| Weighted low pupil indicators, PL | .0001492910489976939 | .00014699950807447616 |
| Weighted high pupil indicators, PH | .00014604429568497733 | .0001469206070715453 |
| E = delta + PL + PH | .0002953353455921659 | .00029392011727764965 |
| High quadrature value | 11383.252407088126 | 11383.252407088126 |

Both frontiers fail the cell-refined E limit.0001875 while passing the separate
PH limit.00025. PL+PH alone exceeds the cell limit, whereas the cell delta is
negligible. All terminal leaves are at depth6; none is eligible for further
spatial subdivision. The frozen refined whole-cell reference is
11383.252407088143e, a signed difference-1.6370904631912708e-11e. That close
value does not override the registered indicator refusal or create a complete
float pass.

The independent first reader attempt is retained as `DIAGNOSTIC_INVALID`:
after three checks it looked up bare `model.py` in the full campaign's
repository-relative FileRef map. The diagnostic's own source map uses bare
filenames, but the campaign does not. The second attempt changes only that
schema lookup; all16 checks pass, status `DIAGNOSTIC_VERIFIED_NO_ADMISSION`,
result SHA `f313e51d0d1af94314b09a405bd74b55ddab82d80322e2a9d3582bc46e2fd071`.

Exact commands were run using Python3.12.10 at
`C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe`:

```powershell
python -X utf8 -X pycache_prefix=experiments/m194e-joint-pupil/work/cache-independent-coupled-read-1 experiments/m194e-joint-pupil/independent-coupled-budget-read.py --output experiments/m194e-joint-pupil/independent-coupled-budget-read-1.json
python -X utf8 -X pycache_prefix=experiments/m194e-joint-pupil/work/cache-independent-coupled-read-2 experiments/m194e-joint-pupil/independent-coupled-budget-read.py --output experiments/m194e-joint-pupil/independent-coupled-budget-read-2.json
```

The results preserve `sys.orig_argv`, interpreter path, actual xoptions and
runtime versions. The reader loads an existing24KiB reference array only;
there is no numerical model integration, worker pool or parameter sweep.

## Derivation before proposing a remedy

For native triangle i with area Ai, each positive quadrature rule has weight
mass Ai. If every supplied point error indicator is at most t, then its
weighted low and high sums each satisfy PL_i<=t*Ai and PH_i<=t*Ai. Summing a
complete unit-cell partition gives PL<=t and PH<=t. Therefore the unchanged
consumer E=D+PL+PH can receive as much as2t from the inner stage even if
spatial quadrature delta D is zero. With t=.00025 and the cell-refined
C=.0001875, separate stage acceptance does not imply a feasible outer budget.
Spatial refinement need not reduce that floor, as the retained case shows.

This reasoning concerns numerical indicators, not rigorous physical or
integration-error bounds. Low/high differences are still heuristic; all
independent full-array precision/refinement comparisons remain necessary.

One compatible per-arm allocation is t=min(P,C/4), reserving half of C for
the two inner terms. However, it would change the consumed pupil target when
the cell arm changes, so it would no longer isolate cell refinement. Root and
Curie's family-wide choice is preferable for the originally intended test:

```text
Cmin = .0001875                         # strongest registered cell target
t0 = Cmin/4 = .000046875
primary inner point target = t0
cell-refined inner point target = t0
angle-refined inner point target = t0/4 = .00001171875
```

Primary and cell-refined share the same actual point target; only the
registered cell rule/order/outer target changes between them. The angular
refinement still tightens its consumed point target by four and changes its
registered angular orders. All standalone point/global pupil caps and outer
cell limits remain their published values. The consumed inner target must be
separately named in source/receipts/contracts, not silently reported as the
larger standalone cap. Each value is derived from the fixed three-arm family;
no observation-dependent choice or parameter sweep is involved.

For each primary/cell-refined whole cell, the intended inner contribution is
at most2t0=Cmin/2=.00009375. Its separate PH contribution is also below every
relevant published pupil cap. This reservation makes the budgets compatible;
it does not guarantee convergence, speed or the full image's true accuracy.
It also does not introduce a new requirement D<=C/2: the actual global
allocator should continue using the unchanged combined E and separate PH,
allowing spare budget from smaller observed inner terms to serve D.

## Required finite arithmetic and independent falsifiers

The weighted bound assumes finite nonnegative low/high weights and their
actual sums matching native triangle area. Explicitly check these on the
consumed rules, with a prospectively fixed floating-mass tolerance. A bound
on just the geometric triangle areas cannot detect incorrect quadrature
normalization. Keep original coordinates, positive areas, complete frontier
coverage, all resource/depth limits and actual global E/PH refusal barriers.
Small tolerated floating mass/point-indicator excess must be included in the
reservation derivation; the roughly half-budget headroom must not be described
as exact real arithmetic. Do not omit PL, PH, or the existing repeated PH term
in the final reported E+PH indicator to make this case pass.

Before implementation release, freeze component controls that exercise the
actual consumed path, including:

- Point-call interception witnesses t0 for primary/cell-refined and t0/4 for
  angle-refined on real cell integration. It must not merely compare metadata.
  The interceptor has scalar/indicator byte-null and placebo companions.
- Separate standalone point calls preserve their declared cap and old behavior;
  the new inner policy must not silently replace that API's meaning.
- Negative, nonfinite, half-mass and over-mass quadrature weights refuse at the
  real leaf-evaluation boundary. Unmodified constant/affine companions pass.
- The archived full3 source still refuses this exact cell. A new internal
  old-cap ablation may restore it if the same path is reached; its actual
  disposition is recorded, not rescued by choosing another failing point.
- Re-run all original API/map/allocator/observer controls on any new source,
  explicitly rebinding the new standalone-versus-inner target distinction.
  Preserve all earlier failures and the unchanged independent references.

After a reviewed numerical amendment, any fresh campaign must regenerate all
fifteen arrays. No full-layer analytic shortcut is being proposed here, and no
passing partial array or close diagnostic scalar supplies missing authority.

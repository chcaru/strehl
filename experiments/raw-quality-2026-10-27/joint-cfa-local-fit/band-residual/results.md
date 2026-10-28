# Original-CFA band residual: first flat rejected

**MEASURED / VERIFIED, 2026-10-27.** The first complete128-square generated flat
fails visibly: colored stripes and broad channel bias. Root and independent
review agree. The original-CFA operator checks and45-step numerical stopping
condition pass; neither establishes image quality. Stop the remaining fixed
fourteen-fit campaign and any full-photo adapter for this unchanged recipe.

| Same central96-square cells, camera DN | Actual current product | Candidate |
| --- | ---: | ---: |
| RGB RMSE | 10.5381 | 303.0554 |
| Green RMSE | 12.4924 | 36.5161 |
| Chroma RMSE | 8.8173 | 374.2888 |

The actual comparator uses the same seven original-u16 observations, geometry
and exact injected noise coefficients through BandWorker/MHC-Catmull-remosaic.
Its complete supported96-square output begins at native(16,16); candidate128
is scored on those identical cells. The product's final MHC reflects at its96
edge, while the candidate region is interior. This disclosed boundary difference
does not explain away the obvious whole-field candidate defect. No photograph
or commercial-workflow performance comparison follows from these generated data.

Complete candidate:

![Rejected complete candidate](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/outputs/raw-quality-2026-10-27/joint-cfa-band-saved-review-1/output/candidate-complete.png)

Complete actual supported product output:

![Actual product baseline](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/outputs/raw-quality-2026-10-27/joint-cfa-band-saved-review-1/output/baseline-complete.png)

Full float [candidate master](../../../../outputs/raw-quality-2026-10-27/joint-cfa-band-cost-1/output/flat-neutral--candidate/output.npy),
[actual camera-DN master](../../../../outputs/raw-quality-2026-10-27/joint-cfa-band-baseline-1/output/flat-neutral/camera-rgb-dn.f32le),
and [independent review](independent-cost-results.md) are retained. The exact
baseline master path/shape/hash is authoritative in its case receipt.

## Executed commands and bounds

Commands run from the repository root with Python3.12, `-B -X faulthandler`:

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-27/joint-cfa-local-fit/band-residual/run.py prepare
python -B -X faulthandler experiments/raw-quality-2026-10-27/joint-cfa-local-fit/band-residual/run.py cost
python -B -X faulthandler experiments/raw-quality-2026-10-27/joint-cfa-local-fit/band-residual/run.py build
python -B -X faulthandler experiments/raw-quality-2026-10-27/joint-cfa-local-fit/band-residual/run.py build --iteration 2
python -B -X faulthandler experiments/raw-quality-2026-10-27/joint-cfa-local-fit/band-residual/run.py baseline --build-iteration 2
python -B -X faulthandler experiments/raw-quality-2026-10-27/joint-cfa-local-fit/band-residual/run-observation.py saved-review -- --cost-dir outputs/raw-quality-2026-10-27/joint-cfa-band-cost-1 --baseline outputs/raw-quality-2026-10-27/joint-cfa-band-baseline-1/output/receipt.json
python -B -X faulthandler experiments/raw-quality-2026-10-27/joint-cfa-local-fit/band-residual/run-observation.py residual-budget
```

Before successful preparation, the same prepare command failed at Python imports:
`operator.py` shadowed the standard library. Renaming it `sensor-operator.py`
preserved implementation bytes/hash. No numerical work/output directory resulted
from that first import failure. The first Rust build failed on one large JSON
macro's recursion limit. Splitting only receipt assembly preserved schema and
numerical expressions; the failed source is retained as`baseline-bridge-build1.rs.txt`.
Build2 freshly compiled strehl-cli in245.813s, with105 pre-existing research-test
warnings; no whole-repository clean-check claim. Its exact executable SHA is
`993f8a0547f2be04c96e273e55c0d51f406f79ec819085af16b064ad4963727a`.

| Completed owned job | Wall seconds | Peak committed bytes |
| --- | ---: | ---: |
| Fixture preparation | 3.468 | 1042067456 |
| Mechanics plus neutral fit | 16.344 | 3216637952 |
| Ten actual product baselines | 2.125 | 6369280 |
| Saved-field comparison, no refit | 2.468 | 1004085248 |
| Saved-error budget, no refit | 8.453 | 3120463872 |

All numerical jobs retained120s/480CPU-second/4GiB limits, four workers,
whole-host observations, terminal accounting and exit0. These are implementation
cost observations, not competitive full-workflow timings. Manifests under
`outputs/raw-quality-2026-10-27/joint-cfa-band-*` bind exact commands, environment,
original files, source and result hashes. The cost's167.063s full-screen estimate
was below300s, but the visible flat failure overrode that scheduling gate.

## What the no-fit error budget establishes

The diagnostic reuses the exact frozen A/H/q and saved latent field. Its delivered
image reproduces bitwise. Against the known2048-DN continuous flat, original
photosite signal error is R89–214DN and B112–249DN across sources, about5–12
times the injected temporal sigma; green is18–77DN, about1–4sigma. Thus the large
delivered error is not simply invisible to the original sensor measurements.
All arrays and per-phase/band raw and weighted contributions are retained in
[the residual budget](../../../../outputs/raw-quality-2026-10-27/joint-cfa-band-residual-budget-1/output/residual-budget.json).

The unchanged objective is0.00036842 at known truth and0.00453734 at the saved
numerically accepted field. The accepted field remains about12.3times worse
even in its own objective. LL receives admission1 while flat AC can receive
0.0001. These measured facts motivate testing exact elimination of the three
constant-color nuisance modes and a projected stopping reference. They do not
prove a spectral nullspace, optimal replacement, optical limit or photographic
improvement. A separately allocated continuation must keep the64-step bound,
full reconstructed objective, independent detail/color guards and actual baseline.

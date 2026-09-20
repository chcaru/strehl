# Saved colour error is predominantly fine spatial variation

MEASURED / independently checked, without a new fit or image correction. The
rejected Cauchy result's additional colour error is mainly variation inside
two-pixel blocks, rather than a broad colour offset. This observation does not
identify a CFA nullspace, an optical cause, or the right replacement prior.

Command run:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B -X faulthandler experiments/layered-raw-inverse/run-colour-error.py --out experiments/layered-raw-inverse/colour-error-1
```

Commission/decomposition/independent-check wall times are2.110/.234/2.281s,
operational metadata rather than benchmarks. Scored SHA256:
`33cb5f37fd617c805b0c4d1c5889414cb8ad4f471fc6b20ba8e290bc213b52f3`.
All saved images/truth and frozen results remain unchanged by hash.

The complete existing64x64 supported domain is used for every arm. Signed
R-G/B-G truth errors are formed in f64 exactly as the retained scalar metric;
the stored reconstructions remain f32. Nested block projections split squared
error into within2, between2/4 and common4 components. DC is separately split
from common4, never added twice. An independently enumerated coordinate oracle
checks every component, exact scalar-score agreement and fixed roundoff bounds.

| Layered retained arm | Chroma RMSE, DN | Fraction within2, four tested bases | Signed R-G / B-G mean error, DN |
|---|---:|---:|---:|
| Original Huber, known alpha | 67.309896 | 48.19-52.66% | -2.0911 / -2.5274 |
| Shot-scaled Huber, known alpha | 66.305886 | 51.99-58.67% | -1.5465 / -2.1776 |
| Cauchy, known alpha | 131.312300 | 82.80-83.53% | -1.4058 / -0.3506 |

Fractions pool both coordinate energies before division. They describe this
particular basis. Four circular shifts keep all4096 pixels but join opposite
domain boundaries artificially. They are dependent sensitivity checks, not
replicates, and do not exhaust all16 possible4x4-grid origins.

The independent comparison of **added** Cauchy error, rather than just its
within-arm fraction, attributes94.07-96.04% of the increase over original Huber
to within2 variation. Against shot-scaled Huber the range is91.69-93.54%.
Signed DC error decreases, so a uniform colour cast cannot explain the failure.
Individual component changes may exceed100% of the net increase because another
component decreases; these are differences of error energies, not probabilities.

The flat control behaves differently: pooled within2 fractions stay near
13.04-15.98% for Cauchy versus12.90-15.84% for original Huber. Its small total
increase does not show the layered scene's dramatic redistribution. The shot
flat failure also spans coarser components. These comparisons limit a story
based solely on one output or one partition phase.

Constant signed error, native checker, aligned4-pixel blocks and weak smooth
sines commission distinct scale allocations. Shifted block partitions must
change components while preserving total. Deliberately overlapping residuals
double-count a live middle component and fail the same conservation criterion.
This validates the accounting; it is not evidence that real detail should be
smoothed. No image-quality acceptance requirement changes.

Independent interpretation and per-coordinate details:
independent-colour-error-results.md. The next implementation must protect real
coloured edges while suppressing false inter-channel variation; this diagnostic
alone does not select its mechanism.

# Four fixed residual updates

MEASURED by `python experiments/quality-september14/joint-backprojection-controls.py > experiments/quality-september14/joint-backprojection-controls-1.log`, frozen solver SHA256 `18de9215052d96eb959db3208ed81cace73a82050f5f96b3825a2b86b7b96f8e`. Execution used .8125 CPU seconds. No RAW reads, parameter changes, iteration sweep or production edits.

The signal tests pass, but preserving the initializer's low noise does not. All twelve fixed noiseless signals improve RGB truth error versus both the initializer and anchor MHC. There are zero regressions under the frozen RGB-or-chroma bar (>5% and >.0005 absolute). All six independent-colour cases improve RGB error by more than 10% and .0005, satisfying the prospective meaningful-gain requirement.

| Continuous scene | Four updates RGB RMSE | Initializer | Anchor MHC |
|---|---:|---:|---:|
| Neutral, x, .20 cycles/native pixel | .002165 | .005741 | .006687 |
| Neutral, oblique (.24,.18) | .004963 | .015588 | .015631 |
| Independent colour, x, .08 | .001683 | .006431 | .009004 |
| Independent colour, oblique (.24,.18) | .012288 | .050694 | .071286 |

The initializer is the unchanged diagnostic nine-MHC/bilinear-gather mean. Its signal and noise metrics, the anchor metrics, all continuous truths, and all noise draws match the preceding valid fixture exactly. It is not the actual product Catmull-Rom mean. Four updates are fixed before execution, not selected using these results.

Flat controls ran first. For the two fractional-phase noise draws, RGB RMSE rises from .001403/.001427 in the initializer to .002895/.002901 after four updates. Chroma RMSE rises from .001293/.001342 to .003480/.003494. This is about twice the RGB error and 2.6–2.7 times the chroma error. Both remain below the single-frame MHC and below full Lanczos inversion, but the explicit >5% flat-noise cost bar fails. Coincident observations retain essentially the initializer's noise; noiseless flats remain exact. These are synthetic operator-noise measurements, not camera calibration.

Controls retain power: wrong maps increase the fixed chromatic oblique .30 case's RGB error from .012288 to .069320, while the wrong-map flat placebo changes by zero. Identical coincident alias observations produce identical output against distinct native truths. Exact data replication changes output only within the fixed 2e-6 f32 tolerance. A channel without observations preserves its explicit initializer exactly and reports `NO_USABLE_DATA_INITIAL_PRESERVED`. Input initializers are checked unchanged after every call.

This therefore does not establish the requested combination of meaningful detail gain and low colour noise. Actual corrected-geometry photographs could still show a useful local tradeoff, but no photographic gain or absence of periodic stipple follows from these synthetic results. No further solver variant or iteration adjustment is implied by this result.

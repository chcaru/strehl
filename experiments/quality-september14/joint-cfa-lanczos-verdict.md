# Fixed Lanczos forward-basis correction

MEASURED by `python experiments/quality-september14/joint-cfa-lanczos-controls.py > experiments/quality-september14/joint-cfa-lanczos-controls-1.log`, solver SHA256 `3e5b208df4f3f43d97ef2669c95a8252b6eb9526c86216c685bb555f674e15d4`. Same twelve continuous signals, six flat conditions, injected noise draws, controls, regularization and CG limits as the bilinear experiment. Only the forward basis and its required support bounds change. All comparator metrics match the preceding valid run exactly. No RAW reads.

The correction clears the fixed noiseless-signal falsifiers and warrants a bounded real-image check. All twelve RGB truth errors improve versus anchor MHC. There are zero prospective RGB-or-chroma regressions versus the diagnostic same-data nine-MHC/bilinear-gather mean. That mean is not the actual product's Catmull-Rom/merge comparator. All nominal channels converge. Execution used .859375 CPU seconds.

| Continuous scene | Lanczos joint RGB RMSE | Bilinear joint | Anchor MHC | Diagnostic mean |
|---|---:|---:|---:|---:|
| Neutral, x, .20 cycles/native pixel | .001537 | .011771 | .006687 | .005741 |
| Neutral, oblique (.24,.18) | .002934 | .025546 | .015631 | .015588 |
| Independent colour, x, .08 | .000208 | .001632 | .009004 | .006431 |
| Independent colour, oblique (.24,.18) | .002110 | .018139 | .071286 | .050694 |

It does not clear an unconditional noise-quality claim. On the two fractional-phase flat-noise draws, RGB RMSE is .004285/.004248 versus anchor .005158/.005060 and diagnostic mean .001403/.001427. Chroma RMSE is .005342/.005311 versus anchor .004578/.004354 and mean .001293/.001342. RGB noise improves relative to one frame, while chromatic noise rises; the nine-frame mean suppresses noise much more. Noiseless flat bias remains below 1e-6. Synthetic injected noise validates the operator, not the camera calibration.

The controls retain their power. Wrong maps increase the fixed chromatic oblique .30 case's RGB error from .002110 to .078673; mixing eight blurred frames with the sharp anchor gives .040987. The wrong-map flat placebo remains below 1e-6. Identical coincident alias observations still give identical output against distinct truths. Missing all blue observations remains explicit NaN. Exact data duplication is not extra information and can change the data/prior balance.

This is a native 1x reconstruction result. The test's continuous scene formula is independent of the Lanczos reconstruction basis. There is no claim that all frequencies, real focus mismatch, uncertain alignment, or arbitrary camera noise pass. The fixed weak first-difference prior is relative to each channel's median supplied variance; it is not purely numerical normalization. Actual-image detail, colour and flat-noise inspection are still required before a production decision.

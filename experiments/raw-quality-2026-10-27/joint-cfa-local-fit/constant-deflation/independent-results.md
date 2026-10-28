# Constant deflation: flat improved, fixed recipe still refused

2026-10-27. **VERIFIED:** I viewed the complete independent truth, actual product baseline, old finite candidate and deflated finite candidate at native size with the identical fixed display/ICC. Deflation removes the earlier conspicuous regular colored stripes and broad rainbow modulation. The new flat looks nearly neutral at this display size; remaining small color/noise errors are less visually obvious. That generated improvement is real, but the unchanged RGB and chroma guards still fail and the solver reaches its fixed iteration cap. Reject this fixed recipe's progression to the larger screen or a photograph. No additional fit, metric, display adjustment or crop was run for this review.

Complete new 128-square output:

![Deflated complete flat](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/outputs/raw-quality-2026-10-27/joint-cfa-deflation-cost-1/output/flat-neutral--candidate/complete-output.png)

Complete old 128-square output and actual supported 96-square product baseline:

![Old complete flat](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/outputs/raw-quality-2026-10-27/joint-cfa-band-cost-1/output/flat-neutral--candidate/complete-output.png)

![Actual product baseline](C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/outputs/raw-quality-2026-10-27/joint-cfa-band-saved-review-1/output/baseline-complete.png)

The full [new float master](../../../../outputs/raw-quality-2026-10-27/joint-cfa-deflation-cost-1/output/flat-neutral--candidate/output.npy), [physical latent field](../../../../outputs/raw-quality-2026-10-27/joint-cfa-deflation-cost-1/output/flat-neutral--candidate/latent.npy), [old float master](../../../../outputs/raw-quality-2026-10-27/joint-cfa-band-cost-1/output/flat-neutral--candidate/output.npy) and [actual camera-DN master](../../../../outputs/raw-quality-2026-10-27/joint-cfa-band-baseline-1/output/flat-neutral/camera-rgb-dn.f32le) remain available. I also inspected the complete new 144-square latent display.

| Same reference cells (16,16), 96×96, DN | Actual product | Old fit | Deflated fit | Frozen upper limit |
| --- | ---: | ---: | ---: | ---: |
| RGB RMSE | 10.5381 | 303.0554 | 13.4045 | 12.0919 |
| Green RMSE | 12.4924 | 36.5161 | 12.3484 | 14.2416 |
| Chroma RMSE | 8.8173 | 374.2888 | 18.6714 | 10.1990 |

Only green passes. The actual baseline uses the same original observations, geometry and exact noise bits. Its final MHC reflects at the supported 96-square crop edge; the candidate scores those cells inside its complete 128-square field. This remains a disclosed context difference, not an isolated basis comparison.

## Numerical and mechanical interpretation

All inherited and new mechanics pass. Actual B(C) columns reproduce exactly; their color supports are disjoint. Literal P error is 1.29e−9, symmetry 2.82e−12 and producing projected-adjoint error 4.90e−10. The deliberately one-sided transpose fails at 0.738 against 2e−5. Restored objective identity error is 4.85e−9. The frozen-q DC-offset test changes restored values by the specified offset within max 0.000122 DN/RMS 0.0000127 DN, without changing weights or fitting again. The new zero-RHS path returns exact zero in zero iterations.

The actual flat stops at 64 iterations, unconverged. Restored full/projected normal ratios are 0.01168/0.01113 against 1e−5. The old brightness-dominated reference would give 2.20e−7; reporting it separately exposes why references cannot be interchanged. Physical original objective falls from the measured constant-only initialization's 0.000335733 to 0.0000676262, with nonincreasing projected history. Lower objective does not establish faithful color. The measurements do not justify more iterations, a relaxed image bar, or a claim that the original-A nullspace caused the old stripes. Deflation also changes the implicit minimum-correction completion, not merely a label on the same finite image.

The [process receipt](../../../../outputs/raw-quality-2026-10-27/joint-cfa-deflation-cost-1/process.json) records the exact Python `-B -X faulthandler` command, original fixture/baseline arguments and operator SHA `8fad7b79…`; controls are `d3ef782c…`. Root's owned run exited 0 in 21.093 seconds, four workers, peak commitment 3,224,412,160 bytes, no cleanup errors, unchanged source/input bindings. Root's unmeasured full-screen cost projection is 163.819 seconds, but `full_screen_released` is false. Only the neutral image fit ran; other color, depth, alias and visibility image tests remain unexecuted. This closes the fixed solver variant as a negative result, without rejecting original-CFA reconstruction as an entire family or claiming photographic progress.

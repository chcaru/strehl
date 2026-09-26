# Sampler confound corrected; photographic blur model still refused

**MEASURED by root execution:** source-only bilinear sampling created a false
blur coefficient in the original no-blur control. One compact Catmull-Rom
sampler repairs that control and passes every original generated control with
the old thresholds unchanged. The separately executed nine-patch photographic
test nevertheless remains **STOP_LOCAL_BLUR_NOT_IDENTIFIED**. No alignment map,
RAW decode, render, physical blur estimate, or photographic improvement follows.

Commands run from the repository root:

```
python -I -B -X faulthandler experiments/alignment-sampling-control/run.py --out experiments/alignment-sampling-control/run-1
python -I -B -X faulthandler experiments/alignment-sampling-control/run.py --qualified-from experiments/alignment-sampling-control/run-1 --out experiments/alignment-sampling-control/saved-photo-1
```

Both bounded jobs exited0 with terminal resource accounting: generated job
3.859seconds and saved-photo job8.953seconds. These are operational receipts,
not speed benchmarks. The latter read exactly nine retained CFA arrays and
decoded zero RAW files.

## Direct numerical result

The unchanged original controls first reproduce their original refusal,
`translation: beta differs from independent Gaussian truth`. Both complete
ordinary/joint readings are now saved before the assertion. The newly measured
joint beta is -0.09111197854 source-native pixel squared at fitted displacement
(0.42917781,-0.56853154); planted motion is(0.43,-0.57) with zero physical blur.
This is a new repeat of the exact old stimulus, not a recovered measurement
from the historical run, which never saved its coefficient.

At known motion, identity geometry, without the phase guide:

| Source phase | Exact five-point arm beta | Bilinear raster arm beta |
| --- | ---: | ---: |
| (0,0) | 1.43e-15 | 1.08e-15 |
| (0.5,0.5) | 1.43e-15 | -0.1283167165 |
| (0.5,0) | 1.43e-15 | -0.0804757965 |

Both arms use the same discrete five-point derivative; only sampling differs.
The unequal-axis case remains outside a scalar isotropic interpretation. These
coefficients are not an offset correction to apply to other scenes.

The one compact4x4 Catmull-Rom candidate gives beta-0.00150200007 on the unchanged
original guided zero-blur stimulus. All original generated controls then pass,
including blur-only, mixed, reciprocal phase/support, wrong motion, flat and
straight-edge refusal, and explicit asymmetric/anisotropic limitations. The
original first0.03beta bar and remaining thresholds are unchanged. Both initial
fit inputs match the bilinear run by complete array hashes. Independent judge
commission rejects13 adverse record classes; five actual sampler checks cover
known taps, integer/constant identity, compact support and mixed quadratic axes.

This establishes that the tested interpolation change resolves the operational
generated refusal. It does not isolate every contribution of the phase guide
or make the resulting coefficient a calibrated physical PSF estimate.

## Photographic result and decision

The original saved-photo measure, with only the sampler/support overlay, fails
its frozen phase/support and predictive criteria. Frame146's beta is positive
on left/right choices(0.19078,0.21703) and negative on top/bottom choices
(-0.17819,-0.10066). Its held-out joint/ordinary RMSE ratios are0.99671,0.99106,
1.01295,1.00738, failing the original0.95 requirement and worsening both
top/bottom choices. None of the seven eligible frames146–148/150–153 satisfies
the improvement requirement in all four choices. Historical boundary-limited
frame145 and identity frame149 remain reported and excluded exactly as before.

Lower residual can reward a wrong nuisance explanation; it is not photographic
quality. This negative result therefore closes this one-Laplacian local blur
route under the tested model after repairing its sampler instrument. Do not
relax the sign or predictive gates, reinterpret beta as camera motion, choose
a favourable support, or render a changed map from it. The corrected compact
sampler is a reusable implementation finding, not independently established
full-stack alignment improvement. The earlier September19 local-chip gain and
failed star-sand transfer are unchanged.

No historical refusal or frozen source file was edited. All numerical values
above are read from the saved run receipts; independent source/choice review
lives in `independent-plan.md` and `independent-source-review.md`. The original
historical failure remains at `../chip-differential-blur/run-1/result.json`.

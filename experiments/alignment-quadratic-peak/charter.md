# Coupled quadratic NCC peak: fixed consumer comparison

2026-09-14. Root authorized one small opt-in candidate and the independent tests here. Author owns production changes; quality_evidence owns this source adaptation and controls; root builds and executes. No default promotion follows this test. No RAW is read by these tests.

Candidate: a guarded closed-form coupled x/y quadratic over the existing 3x3 NCC neighbourhood, through AlignConfig::peak_refinement. Separable is unchanged default. Quadratic preserves integer election, score, contrast, source sampling, pair fits and global solve; rejected fits retain the original separable displacement. Negative-definite, scale-relative conditioned curvature and a strictly interior maximum are required. Author fixes normalized determinant >1e-4 before execution. No parameter sweep.

## Fixed inputs and controls

consumer-tests.rs retains the prior alignment-sinc-peak constants, RNG, Field, render, seed_warp, probe and independent error functions verbatim. That prior 48-row population never executed because the sinc literal controls failed. It is reused without changing seeds, 256x256 grid,64 frequencies,128x128 tile,6 signed offsets,3500/250DN levels,16DN noise,0.35/1.4px blur,1.008 scale or0.004rad rotation. Four content blocks (same focus, unequal blur, additive mixed depths, noisy same focus), each through both actual public NCC consumers. No raster warp generates truth. Gaussian noise is software stimulus, not calibration evidence.

Literal controls: nine known quadratic vertices, zero cross-term agreement, four live separable-bias witnesses, reflection/transpose/positive score gain and offset invariance, wrong-sign destroyers. Ten refusals cover flat,NaN,infinity,tie,indefinite fitted curvature despite a central integer winner,ill-conditioned curvature,out-of-cell continuous vertex despite a central integer winner,short buffer,boundary andzero side. Known vertices must agree within1e-4px. The sampler test establishes model adequacy; an exactly quadratic control alone does not.

## Decision fixed before execution

In EACH same-focus path, require >=20% RMS error reduction, maximum <=0.075 reference-plane px and maximum <=old maximum+0.005. If old RMS<0.005, the gap is inconclusive. In EACH unequal-blur/mixed-depth/noisy path, require RMS<=old RMS+0.005, maximum<=old maximum+0.02 and maximum<=0.25. These are unchanged engineering bars from the prior independent design. No population pooling can hide a block failure.

All48 rows retain successful status, bit-identical input arrays, NCC peak and contrast. Require >=4 changed offsets per six-row block, or mark inconclusive. This changed-output witness replaces the former accepted-count observer; it does not claim to count accepted-but-identical offsets or expose integer coordinates. Actual flat,periodic andLowPeak controls compare exact original outputs. Default cfg must match explicit Separable. Independent wrong-sign,axis-swap and omitted-warp-matrix controls must fail the scoring truth.

RMS can conceal one bad phase, so report maxima and every signed row. NCC residual, fractional-phase smoothing, gradient increases and same-focus success alone cannot establish real defocus alignment or photographic quality. A photographed line/thread's centroid can move with focus even with correct geometry.

Same fixed local timing: old/new/new/old,16 calls per block,one warmup per mode; minimum candidate/old<=1.10 in each path. This does not establish complete alignment speed.

## Execution

Root only: python -I -B experiments/alignment-quadratic-peak/build.py, then run.py. Reuse existing bounded helpers and cached target/native-pyramid-profile. Build cap600wall/1800CPU seconds,4GiB; fresh Compiling strehl-core required. Numerical cap120 aggregate childCPU seconds,2GiB,256MiB retained. Preserve first failure; no automatic retry,precision/window/threshold rescue or new source population. Generated success permits a separately chosen actual RAW comparison only. Full-image source-landmark/crop preservation and matched smooth controls remain required for photographic claims.


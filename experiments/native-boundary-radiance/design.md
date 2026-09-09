# Fixed geometry and saved-input handoff

2026-09-09. Source/metadata review and analytic derivation only. No numerical run, RAW decode, renderer or reader implementation. The charter and `../native-green-probe/new-quality-directions.md` retain the primary sources and mandatory prior-art searches. M87 already has a successful oracle-alpha fit and a failed native correction that destroyed hairs; this experiment tests spatial radiance under shared-pupil visibility, not that old scalar fit. Geometry remains an explicit oracle input, never evidence of native visibility estimation.

## Moment interface

Identity geometry only, native reference-2 coordinates, integer-centred unit sensor cells. Width320, height240, RGGB active origin(0,0). Mask `n=(1,-0.15)`, `c=142`, foreground when `n dot qF >= c`; depths `(1,2)`, inverse foci `(.5,.625,.75,.875,1)`, `K=12`. Thus `dF=12*(f-1)`, `dB=12*(f-.5)`. These are **signed native-pixel displacements per unit pupil coordinate**, not blur diameters. A pupil coordinate `u` is uniform over the unit disc; the shared ray intersects `qF=z+dF*u`, `qB=z+dB*u`.

Proposed implemented API, agreed with author:

```text
point_moments(n,c,dF,dB,z,target) -> [AF,XF,YF,AB,XB,YB]
cell_moments(n,c,dF,dB,source_cell_centre,target) -> same six columns
```

The unknowns are `[F(target), Fx, Fy, B(target), Bx, By]`, in raw black-subtracted DN and DN/native-pixel. No truth amplitude, phase, gradient, latent array or per-channel radiance coupling enters the fit; both green phases use their actual coordinates in one green field.

For `dF != 0`, put `e=sign(dF)*n/|n|`, `t=(c-n dot z)/(|dF|*|n|)`. For `-1<t<1`:

```text
A = (acos(t) - t*sqrt(1-t*t))/pi
M = e * 2*(1-t*t)^(3/2)/(3*pi)
F first moment = (z-target)*A + dF*M
B first moment = (z-target)*(1-A) - dB*M
row = [A, F.x, F.y, 1-A, B.x, B.y]
```

For `t<=-1`, use `A=1,M=0`; for `t>=1`, `A=0,M=0`. At `dF=0`, foreground visibility depends only on `z`; integrate the two clipped parts of the unit square exactly for area and first moments. Their areas sum to1, their relative first moments sum to `source-target`. These complement identities are arithmetic checks, not independent corroboration.

`cell_moments` integrates the point row over `z in source+[-.5,.5]^2`. Proposed fixed quadrature: clip by `n dot z-c = +/-|dF||n|`; integrate full-F/full-B polygons exactly; fan-triangulate the intervening strip and apply fixed8×8 Gauss-Legendre via `z=v0+r(v1-v0)+(1-r)t(v2-v0)`, Jacobian `abs(cross(v1-v0,v2-v0))*(1-r)`. The independent verifier must establish adequacy before scored output; this proposal does not certify quadrature error. No scored-output refinement sweep.

**Output is the pixel-cell integrated sharp composite**, obtained by `cell_moments(n,c,0,0,target,target) dot coefficients`. Picking the layer at the centre, or taking one fitted intercept, is wrong for straddling cells. Return raw-DN estimates to the existing four planes; the writer applies WB once. Black512, white15360, injected gain.25DN/e and RN4e are existing inputs, not fitted constants.

## Fixed support and refusal

Both design and independent verifier selected radius2 native: a5×5 square of original observed photosites per target, restricted to the same spectral colour, across all five frames. Treat only the input-defined strip `abs(x-.15*y-142)<=8`; keep other sites unchanged. Require complete observed support inside the active area; never invent missing sensor cells or clamp their coordinates. Footprint moments describe scene coordinates and do not read a latent image outside the sensor.

The verifier proposed at least12 observations, a diagonal-normalized six-variable normal solve, minimum normalized Cholesky pivot1e-4, no ridge, robust weights, adaptive support or rank repair. Output uses the sharp-composite target row above. Nonfinite/rank-deficient fits abstain. Predicted variance is `q^T N^-1 q` with the injected observational variances; a proposed conservative ceiling is the minimum contributing single-observation variance. This is an engineering refusal, not proof of beating the current merge. The verifier owns the final prospective variance policy and numerical tolerances. Existing flat temporal noise remains decisive. The independently chosen boundary-model destroyer moves `c` from142 to146, retaining the original truth and scoring regions.

## Actual saved inputs and consumers

All paths below are relative to the repository root.

- Input root: `experiments/m194g-larger-pupil/software-noise-intended-1/`. Its `noise-manifest.json` is SHA256 `80007e235c58c0cdee5549ffd3e3173a9e39886a35fb458cf0670a8ac5a47a67`; admission is `experiments/m194g-larger-pupil/independent-noise-files-1/noise-admission.json`, SHA256 `088272bfbeca6d00a816a5de72eeaf7aac8f8ca6e0ef68941ab236655fa298e7`.
- Exactly18 saved bundles: scenes `flat` and `textured`, each `noise-off` and `seed-{701,709,719,727,733,739,743,751}`. Each bundle contains `frame-{0,1,2,3,4}.cfa`, five distinct original files, each153600bytes, little-endian u16[240,320]. The manifest carries each individual hash. No new noise draw is needed.
- The original admitted source remains in `crates/strehl-cli/src/merge_cmd/noise-pupil-bridge.rs`. The landed thin experiment adapter is `experiments/native-boundary-radiance/bridge.rs`, test `merge_cmd::known_scene_benchmark::noise_pupil_bridge::boundary_radiance_bridge::m194g_boundary_radiance_consumer`. Its namespace is `STREHL_BOUNDARY_BRIDGE_`: `MODE=off|apply|displaced|no-treatment`, `SCENE`, `SEED`, `NOISE_ADMISSION`, `NOISE_ADMISSION_SHA256`, `OUTPUT`, `RECEIPT`. The adapter fixes internal subset `all`, HardFloor and the existing count observer; it reuses the admitted source/consumer rather than changing the old bridge contract. `run-matrix.py` owns the exact fresh18-pair scene invocation.
- Verified current crop metadata from `experiments/m194g-larger-pupil/production-matrix-1/case-00-plan.json`: native output300×226 at offset(10,8), quad crop(5,4,150,113), four levels150×113,75×57,38×29,19×15. Convert each compact site back to full native coordinates before moments.
- Existing HardFloor baselines under `experiments/m194g-larger-pupil/production-matrix-1/`: flat case ordinals `[0,3,4,7,8,11,12,15,16]`; textured `[19,20,23,24,27,28,31,32,35]`, ordered noise-off then the eight seeds. `run-index.json` binds each `case-NN.tif`, plan and receipt. Each of these18 saved baselines is the exact-output reference for a fresh current-feature-off render of the same input. Root chose fresh comparison baselines before execution; do not replay the old38-output population.
- Existing ideal: `experiments/m194g-larger-pupil/independent-quality-target-1/target.json` references `scalar.npy` (SHA256 `91fbd5bf692f9411c4394d4a60e805d998eec0061553c5fcba2059f2e505e795`). Only the scorer reads it. Existing reader `independent-rgb-tiff.py::read_rgb_tiff`, and metrics `independent-quality-metrics.py`, both under `experiments/m194g-larger-pupil/`, supply TIFF parsing and fixed errors/temporal variance. TIFF codes map to DN by14848/65535; no second black subtraction. Reuse the existing target-to-RGB scaling in the quality adapter/readout.
- Existing regions from `independent-quality-metrics.py::regions`: W is native x[104,216),y[104,136); boundary is `abs(x-.15*y-142)<=8` intersect W; surface and endpoint masks are already defined there. Keep them fixed. The flat scene has common radiance, not a contrast-boundary positive control.
- Genuine-colour no-treatment control: `experiments/m194b-known-scene/producer-output-1/color/noise-off/manifest.json`, nine saved `frames/frame-00.cfa` through `frame-08.cfa`, via `known-scene-benchmark.rs` / `merge_cmd::known_scene_benchmark::m194b_known_scene_consumer`, namespace `STREHL_M194B_`. It contains real independent chromatic waves but different geometry and no chromatic defocus. The landed explicit wrapper test is `merge_cmd::known_scene_benchmark::m194b_boundary_radiance_no_treatment_consumer`; the old `m194b_known_scene_consumer` supplies its off comparison. Never apply M194g oracle geometry to this different scene. Compare disabled/no-treatment complete outputs.

## Proposed finite population

Root revised this prospective population before execution:18 fresh current-feature-off HardFloor baselines paired with18 candidate outputs, then one displaced-boundary textured/noise-off destroyer and one genuine-colour disabled/no-treatment pair: **at most39 primary TIFFs**, with early stop on failure. Compare all18 fresh baselines byte-for-byte with their corresponding saved M194g HardFloor outputs. Run the nine flat pairs first; proceed to the nine textured pairs only if the flat decision permits it. This replaces the earlier23-output proposal: the small render cost is accepted to remove ambiguity across source/feature changes. No endpoints, floor-pedestal reruns, parameter sweep or new fixture. Moment/affine/rank controls precede these outputs and must show actual treatment when expected. Runtime and memory are costs to measure; this design makes no speed, native-quality or SOTA claim.

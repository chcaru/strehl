# M194d — positive band weights at the admission floor

2026-09-07. Root report; fixed production comparison and independent
output review complete. Preregistration committed at `5f55c9ee7dc15d47e04ded53cd11eea929e28fc2`
before product edits and outputs. Immediate baseline is M194c commit
`04128e041dabc0bdb86c64526cd8155dd0a0fd07`, including its accepted storage
correction and measured flat-noise regression.

**MEASURED:** this fixed weighting reduces flat-region temporal variance by
54.21%/68.70%/53.53% in R/G/B on the existing eight-repeat software fixture.
The noise-off textured plane loses at most 0.008669 DN of registered wave
amplitude; its error rises slightly against both reference targets in all
three channels. No registered engineering
review trigger fires. Sparse worsening still exists: the largest increase in
absolute truth error is 33.451259 DN inside the fixed ROI. This supports further
development of this operator, not default promotion or a SOTA claim.

**VERIFIED by the strict comparison:** all 40 explicit HardFloor outputs match
the 40 archived M194c TIFFs in whole-file bytes and decoded pixels. The candidate
changes 19 of 40 outputs; all 20 single-input outputs and noise-off flat/full9
are byte identical to HardFloor. The prior single-plane detail deficit remains.

## Question, intervention and prior art

The hard floor can give exactly zero weight to every frame, then let a tiny
crossing by one frame replace the all-frame mean. The scoped intervention is
one fixed positive baseline weight in the existing streaming BandMerge. The
prior-art and calibration distinction are recorded in
[implementation-plan.md](../../experiments/m194d-band-admission/implementation-plan.md),
[independent-comparison-design.md](../../experiments/m194d-band-admission/independent-comparison-design.md)
and [literature-scope.md](../../experiments/m194d-band-admission/literature-scope.md).
They include the existing soft-weight proposals, M138's corrected draft,
the available M143 review account, M69's texture-dependent uncertainty and
the limitations of the old A1 selected-winner interpretation. This milestone
does not calibrate that statistical model.

For band energy E and existing floor F in DN², the new `FloorPedestalV1` uses
`q=max(E-F,0)`, `a=q/max(F,1 DN²)`, then
`exp(clamp(p*ln(hypot(a,1)/64),-80,80))` for every frame. The dimensionless
constant 1 is fixed and heuristic. The existing exponent schedule, Gaussian
base average, probe floor, injected noise, hull and writer remain. A finite
weight alone does not bound the product or sum: candidate-only guards refuse
nonfinite energy/floor, accumulated sums, resolved coefficients and collapsed
image before hull projection. Unsupported candidate configurations refuse.

`MergeConfig.admission` defaults to `HardFloor`. The experimental mode is
available to the dedicated test consumer; no ordinary CLI flag or quality
default changes. The production weight loop still calculates the legacy
significance temporary, but the candidate does not consume it or depend on
its `NU_SMOOTH` calibration. Positive weights do not establish independent
noise averaging or calibrated probabilities. Blurred-frame dilution remains
the central risk to test beyond a single depth.

## Fixed comparison and reproducibility

The controller rendered 80 actual production TIFFs on one copied executable:
40 HardFloor controls, followed by 40 FloorPedestalV1 outputs. Inputs are the
same 20 M194b manifests and 180 u16 CFA files: flat and scalar plane, each
noise-off plus eight fixed noise repetitions; analytic color and color-null
noise-off. Each has full9 and original-frame4/single4 arms. The single input
keeps its original local-zero probe index. No seed, gate, floor or target was
tuned after the result.

The inherited curved placement track, quad crop (9,7,142,106), native output
284×212 at offset (18,14), and fixed native ROI x[64,256), y[64,176) are unchanged.
The 21,504-pixel mask, two reference targets, cell-integration approximation,
three bands, gate 2, two workers, full-resolution MHC, CameraLinear output,
Catmull-Rom gather, mean base and InputRange hull remain exactly bound. All
measurements below are post-WB DN. See [M194b](M194b-known-scene.md) for the
forward model and physical limitations. The optical-observation and ideal
targets are distinct; neither is a proven attainable floor.

Commands actually run from the repository root:

```text
python -X utf8 experiments/m194d-band-admission/run-experiment.py --out experiments/m194d-band-admission/experiment-1
python -X utf8 experiments/m194d-band-admission/compare-experiment.py --controller experiments/m194d-band-admission/experiment-1/controller.json --controller-sha b3e9a71a538d16f6e0f2c399cb530c71a00fa74cd1194362d41417610f5a1e59 --out experiments/m194d-band-admission/experiment-1/comparison-1.json
python -X utf8 experiments/m194d-band-admission/compare-experiment-v2.py --controller experiments/m194d-band-admission/experiment-1/controller.json --controller-sha b3e9a71a538d16f6e0f2c399cb530c71a00fa74cd1194362d41417610f5a1e59 --out experiments/m194d-band-admission/experiment-1/comparison-2.json
```

The second command failed on a reader Path/string mismatch; the third reads
the same outputs. The original source remains byte frozen. The v2 change wraps
the recorded log path for the unchanged hash API and records its own source
identity; scoring arithmetic, renders and thresholds are unchanged. The failed
invocation was repeated once to preserve its raw traceback on disk, again exit1.

| Artifact under `experiments/m194d-band-admission/` | SHA-256 |
| --- | --- |
| `experiment-1/controller.json` | `b3e9a71a538d16f6e0f2c399cb530c71a00fa74cd1194362d41417610f5a1e59` |
| `experiment-1/build.json` | `7e3567a176e66dd7b8db3ebb16f2e4d2d5774216e0c3530b990df80a15fd7559` |
| `experiment-1/hard-floor/run-index.json` | `803198980a5d6dce228f66d7b0c502e2629594ee5f7bc2ca653351c4feb12407` |
| `experiment-1/floor-pedestal-v1/run-index.json` | `6d2ccccb1096f1e1974c6d618620f59abb89d6358e1a13c14f703e744c750c05` |
| `experiment-1/hard-floor-score.json` | `14616913fe3cbddea5ed25306ebadefd4b5c414c57cf6ced578700ff04c22947` |
| `experiment-1/floor-pedestal-v1-score.json` | `ac0022a639862791952b728e9e4bcd655bfcd4a49840b30765c7be81b30dcb04` |
| `experiment-1/comparison-2.json` | `a64df70677d1dc66c81f6e088b0196a23883bc9c480cbe156c6b104e0cadc306` |
| `compare-experiment-v2.py` | `9cc3fd5652a4e17d9036e6b69300b4e0bef50089893c3ba0fa40424e15b00fb1` |

The controller completed at 11:36:57 UTC. This timestamp is provenance, not
a runtime claim. Source snapshots, actual compiler rebuild, exact invocation
and controlled environment, copied executable, producer/commission hashes,
plans, receipts, outputs and numerical sources are bound in the records.
Compiler/test source bindings include external Rust files and the correct
including crate root. A test-only source in the CLI attestation is not evidence
that its core tests executed; the independent core executable has its own record.

## Measured noise, detail and color

Lower noisy error can reward blur. The flat control, noise-off waves, ideal
target and color controls are retained beside the noise result. Higher wave
amplitude can reward overshoot or incorrect phase; both complex responses
remain in the score files. These readings do not rank overall image quality.

| Full9 measurement | HardFloor | FloorPedestalV1 |
| --- | --- | --- |
| Flat temporal sigma, R/G/B DN | 13.761687 / 13.709154 / 14.212334 | 9.312671 / 7.669237 / 9.688014 |
| Flat mean-MSE-derived RMSE, R/G/B DN | 13.767683 / 13.704966 / 14.210180 | 9.320313 / 7.667677 / 9.681739 |
| Plane temporal sigma, green DN | 9.735954 | 9.734750 |
| Noisy plane optical-observation RMSE, green DN | 14.130740 | 14.130737 |
| Noisy plane ideal-target RMSE, green DN | 70.129129 | 70.134400 |
| Noise-off plane first wave amplitude, green DN | 374.277655 | 374.275325 |
| Noise-off plane second wave amplitude, green DN | 150.441934 | 150.434084 |
| Noise-off analytic color RMSE, R/G/B DN | 77.481183 / 38.292922 / 77.634263 | 77.481139 / 38.292704 / 77.634123 |
| Noise-off color-null RMSE, green DN | 29.406718 | 29.406580 |

All three channels' flat temporal variance falls in the paired eight-repeat
population; ratios candidate/baseline are 0.457936 / 0.312956 / 0.464664.
The green paired variance difference is −129.123700 DN² with delete-one-repeat
jackknife SE 2.749813 DN²; paired mean-MSE difference is −129.032809 DN² with
whole-repeat SEM 2.750136 DN². There are eight repetitions, not one independent
sample per pixel or channel. Flat ideal and observation targets coincide and
their duplicate rows are not corroboration.

The plane effect is small but not zero. Green ideal MSE rises 0.739367 DN²
with paired SEM 0.010847 DN²; its temporal variance falls 0.023449 DN² with
jackknife SE 0.001847 DN². Optical-observation MSE changes −0.000074 DN² with
SEM 0.001945 DN². The latter does not establish a directional gain. Noise-off
plane ideal RMSE rises 0.004911 DN in green, and all six channel/wave amplitudes
fall, by 0.001971–0.008668 DN. These are measured changes, not equivalence
claims. Noise-off optical-observation RMSE also rises in all channels:
0.001855 / 0.001113 / 0.001693 DN in R/G/B. Thus the near-zero noisy
optical-target change does not erase the measured noise-free cost. The major
pre-existing ideal-detail and analytic-color deficits remain.

The fixed engineering triggers were >1 DN RMSE increase in any registered
case/channel/target, >2% temporal-variance rise, or >1 DN noise-off wave loss.
None fires. Their absence is not a statistical-quality admission test.

## Sparse error: repair and remaining harm

Whole-image movement reaches 556 TIFF LSB = 125.970672 DN, at seed733,
blue/native (155,51), outside the fixed ROI. Movement alone cannot say whether
truth fidelity improves. The fixed ROI comparison stores both directions of
absolute truth-error change and native coordinates, as well as residual maxima
and p99/p99.9 under the declared linear-quantile convention.

The previous M194c adverse red sample, flat/repeat709/full9 at native (142,170),
moves from 3101.461387 to 2995.655085 DN against truth 3000.000089 DN. Its
absolute error falls 97.116293 DN. This selected historical site cannot stand
in for the rest of the population.

The largest new worsening is a different red sample, flat/repeat743/full9 at
native (203,146): 2999.506706 → 3033.944732 DN, against 3000.000089 DN truth.
Absolute error rises 33.451259 DN. At flat/repeat709, red/native (222,72)
worsens 22.656596 DN even while that image's flat RMSE falls. Keep these
adverse sites; a lower mean is not pointwise dominance. Descriptive tail
diagnostics introduce no new acceptance threshold.

The independent reader uses its prospectively chosen nearest-rank p99.9 rather
than root's linear quantile. All 24 noisy-flat repeat/channel p99.9 values
improve; the largest candidate/baseline ratio in R/G/B is
0.433579 / 0.333959 / 0.432302. Across the eight flat/full9 repeats, with
172,032 pixel sites per channel, absolute truth error worsens by >10 DN at
858 / 312 / 988 sites and improves by >10 DN at 13,651 / 14,693 / 14,006 sites.
These counts describe dependent pixels, not independent trials. At the named
historical red coordinate (142,170), four of the other seven repetitions
worsen. The chosen seed709 repair is not a universal same-site repair.

## Implementation and independent controls

Freshly compiled broad suites pass 559 core and 138 CLI tests, with three CLI
tests ignored. Final author controls pass on the frozen source. Clippy exits0
with visible Checking for both crates; inherited warnings remain. Three new
test-only modulo spellings were cleaned before the final source freeze.

The independent [component report](../../experiments/m194d-band-admission/independent-evidence.md)
re-chooses the threshold stimulus using period-two stripes and a real cutoff
placebo. The candidate gives 4098 DN where the old/cutoff arms give 4106 DN
just above the floor; exact-floor arms all give 4098 DN. The strong-frame
control, lifecycle, accumulation, absorption, resolution and pre-hull numerical
refusals have actual power. Five independent core tests pass, including one
deliberately expected lifecycle panic. Forty actual
consumer TIFFs across both gather paths provide 16 layout/poison identities,
eight counter off/placebo identities and 12 pixel-changing site/model/warp
controls. The initially failed reader missed a libtest prefix; the preserved
same images pass the separately bound corrected reader, without a rerender.

The sparse reader passes 26 independent checks. Initial malformed-domain
controls found complex conversion, coordinate-range and arithmetic-overflow
holes; their failed records and original helper remain. Explicit refusals
were added before the quality outputs, and all 16 malformed cases then refuse.
These were instrument-domain defects, not defects measured in the TIFFs.

The independent mode controls pass 46 checks over 29 subprocesses and three
TIFFs. Both modes have valid companions; 22 malformed or coherently rehashed
mode, environment, plan, source and old-binary substitutions refuse. Explicit
off-mode matches the archived control and repeated-off whole-file null. These
are plumbing controls, not 46 independent quality measurements.

The original M194b entry also renders its declared plane/noise-off/full9 control
without an admission environment. Its TIFF/pixels match the archive. Retained
author instrument failures distinguish the root's later compiler-artifact build
from the unchanged copied author executable, and distinguish the expected new
plan software source stamp from unchanged settings/pixels. No old artifact is
rewritten to make a guard pass.

Independent actual-output review reads all 120 TIFFs: 40 candidate, 40 off-mode
and 40 archived baseline. Re-chosen cell/pupil quadrature, direct complex waves,
Welford temporal variance and paired repeat uncertainty agree with the root
readout. RMSE-change discrepancy is below 1.71e-10 DN and paired-MSE-change
discrepancy below 3.12e-9 DN²; these are arithmetic-agreement diagnostics, not physical accuracy.
The review independently finds the same small plane tradeoff and no engineering
trigger. New boundary checks pass 18/18: two unchanged complete-package
companions and 16 rehashed controller, index, plan, receipt,
environment and source contradictions. The original package still passes after
the private mutations. The v2 reader correction is independently confirmed as
the Path wrapper plus reader identity, with no numerical change.

The final actual-output read is
`independent-comparison-read-1.json`, SHA-256
`763174a931e3a953189c20ed2404eefd18f5e51f2cb57fc8dd1b043a5afe2b4f`;
the binding result is `independent-comparison-bindings-run-1/result.json`,
SHA-256 `04f96184beb98440d5ac05c86197110e892a609a1a03fb2635346479ffdb470c`.
See the [independent review](../../experiments/m194d-band-admission/independent-comparison-review.md)
and [author evidence](../../experiments/m194d-band-admission/author-report.md).

## Scope and next decision

The component placebo establishes the threshold behavior. The complete-image
comparison attributes its result to this full operator change; it cannot assign
all benefit to the cutoff alone because above-floor weights also change.

Continue this fixed operator as an experimental candidate with a flat-noise
benefit, small measured plane-detail tradeoff and sparse worsening. Preserve HardFloor
as the default and the committed M194c storage correction. Do not tune the
heuristic constant or probe to improve these already observed fixtures. The
next useful quality question is whether the flat-noise benefit survives weak
detail and two-depth occlusion, where admitting blurred frames can cause real
damage that this one-plane plant cannot express. Commission that forward-model
extension independently before scoring it. Geometry/output authority and the
frozen systems protocol remain separate open work.

No capture or holdout was read. No new SOTA axis, Phase-1 gate, camera-noise
calibration, alignment estimate, physical occlusion model or performance result
is admitted. The requirement checklist is discharged by actual production
gather/streaming tests, injected-model controls, fixed repeat/flat/target reads,
source and TIFF byte bindings, independent re-choice, explicit source-scoped
edits and preserved failures. No SYNTHESIS numbers were allocated or folded.

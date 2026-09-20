# Boundary and actual-RAW-gather screen

**MEASURED, 2026-09-19: structural controls pass; the frozen photographic
admission rule refuses this recipe.** No RAW photograph or production change
was made by this screen. This is a narrower conclusion than saying the
candidate is worse than the baseline.

Root ran these commands with Python312 (the runner records exact commands,
environment, source hashes, executable hashes and Windows job limits):

```
python -I -B experiments/boundary-cfa-wavelet/run.py build --out experiments/boundary-cfa-wavelet/build-1
python -I -B experiments/boundary-cfa-wavelet/run.py build --out experiments/boundary-cfa-wavelet/build-2
python -I -B -X faulthandler experiments/boundary-cfa-wavelet/run.py controls --build experiments/boundary-cfa-wavelet/build-2 --out experiments/boundary-cfa-wavelet/controls-1
```

Build1 failed at compilation: a missing QuadSource trait import and two
unsupported hexadecimal-format calls on the hash output. Root fixed only
those three plumbing errors. Build2 freshly compiled both core and CLI and
finished in125.218s. Both independent tests passed in the bounded4.843s job;
the test result is not photographic admission. The quality test deliberately
writes the separate false decision to screen.json instead of failing the
test harness. Peak job committed memory was375156736bytes.

## What passed

Reflection/crop/phase checks, rectangular transform inversion and energy,
complete coefficient packing, original-source variance routing, active-area
identity samples and original immutability all passed. The actual fractional
GPU gather exercised overlapping original source support. The enumerated
four-state covariance test rejected the wrong independent-extended-site
approximation. No sensor calibration follows from these operator controls.

The fixed8-pair source-space floor agrees with the independent64-realization
reference: pooled high-rank ratios1.0047712139251164 at identity and
1.005300662620787 at the held fractional similarity. Every fixed band-level
uncertainty check passes; the factor-two destroyer fails as required. The
conditional simulation still uses the injected calibration and noisy supplied
signal. It is not an exact per-pixel variance measurement or a new noise model.

Observer on/off gives byte-identical baseline/candidate RGB and all8 collapsed
CFA planes on the live fractional weak-red case. The full source/executable
bindings are in build-2 and controls-1. No full-original-buffer statistic is
used as scene signal, and no aligned-source volume is retained.

## Quality result and its limits

All12 cases exercise their intended property. At both ISOs, identity passes
all fixed guards and benefit checks. The held fractional similarity passes
flat and coarse guards and all baseline-relative RGB, boundary and corner
nonregression checks. It misses two requirements:

| ISO | Warp | Flat RGB error / baseline | Weak-red RGB error / baseline | Weak-red component / focused source | Decision |
| --- | --- | --- | --- | --- | --- |
| 100 | identity | 0.83781 | 0.91738 | 0.906795 | admit bounded next step |
| 400 | identity | 0.83766 | 0.91769 | 0.906697 | admit bounded next step |
| 100 | fractional | 1.01246 | 0.97209 | 0.887259 | refuse |
| 400 | fractional | 1.00914 | 0.97159 | 0.887325 | refuse |

Fractional weak-red retention is below the frozen0.90 focused-source bar;
neither flat nor weak-red achieves the separately required5% RGB-error
benefit. The baseline itself retains only0.1852 of the fractional red truth
component, whereas this candidate retains about0.4777 (focused source about
0.5384). Thus the refused candidate still recovers substantially more of this
particular component than baseline. Error can reward blur; component recovery
can reward excess contrast. Neither establishes photographic quality alone.

The comparison is complete7 complex bands on the128-square extension against
the actual baseline's3 Laplacian bands plus15x13 mean base, with different
depth-dependent exponent schedules. It is not a basis-only ablation. The
varying-focus fixture is not a physical occlusion/specular-light model.
Passing it cannot predict cleanup of the real vitamin-C streaks.

The screen SHA256 is
7519410caf5ec14f87357160a0be401edc75ab78d6bf1c6cf4a8f255ebe1adf5.
Do not promote, relabel the fixed screen as passing, or tune its thresholds.
Independent result review and resource review determine the next concrete
experiment. Any separately chosen observational photograph must retain this
refusal and state why that observation is informative despite it.

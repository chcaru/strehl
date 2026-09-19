# Full-context RAW placement result — September 19

**MEASURED BY NATIVE INSPECTION: a modest local improvement survives the complete
299-frame chip render, with seven Laplacian levels plus the base.** Root and an
independent photographic reviewer agree that existing rail cores and crossings
are easier to distinguish. The four frozen transition views show no obvious
seam. Cyan/magenta fringes and stipple remain conspicuous. This is neither SOTA
evidence nor an acceptance of quality across the whole image.

## What now reaches the photograph

The default-off `STREHL_LOCAL_PLACEMENT_FILE` configuration is consumed by the
normal pyramid merge, through both CPU and experimental GPU direct gathering.
It adds measured source-native displacements before the existing per-channel
lateral chromatic-aberration transform. It reconstructs one small unaligned
source patch from original u16 CFA, using the existing MHC, Catmull-Rom and
rounded storage conversion. The synthetic noise probe traverses the same hook.
The camera noise model is not re-estimated or replaced.

The configuration binds the original source directory, count, sensor geometry,
filenames and original transform bits. Unsupported geometry or source stencils
refuse. The one fixed 392×392 support has a 32-pixel interior smoothstep, with
full correction in its 328×328 core. The displacement tapers; two rendered
images are never blended. Only chip frames 146–153 are configured, and reference
149 receives exactly zero correction. No global sidecar is rewritten.

The full-stack test uses the existing actual-consumer entry point solely to pin
the same development tone in both arms. Its image observer is disabled. All
299 original RAWs, the original map, colour development, seven levels and the
merge settings are identical. The production hook is not test-only; the source
and compiled production CLI are retained alongside the test executable.

## Independent correctness evidence

`controls-3/process.log` records five passing generated tests from a fresh
release build. These re-choose geometry: asymmetric image and crop, odd active
origin, odd support origin, nonidentity scale/rotation, and deliberately strong
nonzero colour transforms. Acceptance was fixed in `independent-design.md`.

- Disabled, zero, absent-frame and outside-support gathered values are exact.
- The 107,584 full-weight noisy samples equal the old uniformly shifted gather
  bit for bit; 107,173 differ from the unchanged gather. The noisy fixture
  prevents an affine signal from hiding an interpolation-kernel defect.
- Independently expanded affine equations check direction, factor two, CFA
  phase and the taper. Their wrong-sign/factor/phase controls disagree.
- Constant and flat-noise controls exercise 44,516 taper samples. The seeded
  noise variance ratio is 0.841227, within the prospectively fixed 4× sanity
  bound. This is an operator check, not a camera calibration or quality metric.
- Bad configuration, nonfinite values and incomplete source support refuse.
  Original generated u16 samples remain identical. Two-green invocation equals
  the corresponding four-plane samples.

The independent review explains the remaining limits. In particular, the probe
estimates spatially aggregated band gains: shared sampling does not establish
per-pixel noise calibration inside the corrected region.

## Full chip output

`comparison-1/photographic-review.md` is the independent photographic decision.
Every view is a native crop, at most 328 pixels per dimension. No sharpness
energy score is used. Narrower coloured fringes can look sharper, so the
decision follows the existing dark rail/crossing structure instead of sparkle.
The broad lower junction remains mottled.

The fresh disabled baseline has **zero differing output pixels** against the
retained earlier matched chip baseline (`previous-baseline-comparison.json`).
The TIFF file hashes differ; pixel identity is the verified claim.

The intervention changes 4,597,115 output pixels. This only proves liveness.
The far control looks unchanged at native size but is not byte-identical:
its maximum difference is 33/65535. The local gather support does not bound
downstream changes from pyramid filters and spatially aggregated probe gains.

Complete TIFFs are retained locally in `baseline-1/output/replay.tiff` and
`candidate-1/output/replay.tiff`; compact native views and hashes are retained
in `comparison-1`. Baseline/candidate wall times were 99.390 / 91.000 seconds.
These are single operational observations, not evidence of a speed improvement
or measured overhead. The source files' sizes and mtimes remained unchanged;
this is not a whole-corpus content-hash audit.

## Commands and reproducibility

Run from the repository root using the installed Python 3.12 executable with
`-I -B`. Output directories are create-new. `--build` for `run.py controls`,
`baseline` and `candidate` must currently be an **absolute path**.

```
python -I -B experiments/full-context-placement/run.py configure
python -I -B experiments/full-context-placement/run.py build --build experiments/full-context-placement/build-2
python -I -B experiments/full-context-placement/run.py controls --build <absolute-build-2> --out experiments/full-context-placement/controls-2
python -I -B experiments/full-context-placement/run.py baseline --build <absolute-build-2>
python -I -B experiments/full-context-placement/run.py candidate --build <absolute-build-2>
python -I -B experiments/full-context-placement/compare.py
python -I -B experiments/full-context-placement/run.py build --build experiments/full-context-placement/build-3
python -I -B experiments/full-context-placement/run.py controls --build <absolute-build-3> --out experiments/full-context-placement/controls-3
```

The exact expanded executable paths, arguments, environment, bounds, source
bindings and terminal child-process accounting live in each invocation/process
receipt. Build 3 adds the independent noisy-core assertion only; its recorded
production source hashes equal build 2. Their executable hashes differ, so no
binary identity is claimed. Five strengthened controls pass on build 3.

The ordinary feature set also passes `check-default.py`. Its second receipt
requires a fresh `strehl` binary check artifact with an empty feature list,
as well as the `Checking strehl-cli` line. The first wrapper required that text
alone and rejected a successful check whose package status said `Compiling`
because its build script also ran; no compiler error occurred. The second
check makes freshness explicit instead of weakening the source check.

This result justifies keeping the measured local correction as an experimental
consumer. It does not justify enabling it automatically on arbitrary stacks.
Next-scene evidence and the program decision are recorded under
`experiments/quality-september19` and in the current quality-path proposal.

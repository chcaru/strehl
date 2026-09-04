# M-COVER-NATIVE Phase A preregistration

## Scope and questions

This lane executes **Phase A, Q1 and Q2 only**. It does not edit Rust and it
does not begin Q3 or Q4.

- **Q1:** Does the shipped `CoverMode::Crop` clear scorecard v1.1 section 1.5
  native-scale geometry on the exact eight frozen `SCORECARD-BASELINE` bee
  arms?
- **Q2:** If it does, does Crop fail another current scorecard prerequisite:
  native-size output, fixed common-input overlap, site survival, differential
  attrition, residual geometry, or formal comparability to a full-frame
  comparator?

The answer is not allowed to move a score. The inherited whole-image ECC
estimator was commissioned and added after the frozen score bytes. It is a
post-score rejection-only estimator, not a literal discrete-landmark fit.

## Frozen lane and provenance

- Binary:
  `experiments\SCORECARD-BASELINE\work\bin\strehl.exe`
- Required SHA-256:
  `814eb719608cc0f085fbd49e7529eb6fa4e50031070f5f57af4fc2812cee4363`
- Required version: `strehl 0.0.0 (4b60b1ba9f56)`
- Inputs: the existing
  `experiments\SCORECARD-BASELINE\work\inputs\<arm>` directories, unchanged.
- Solves: byte copies of all eight existing
  `experiments\SCORECARD-BASELINE\work\cache\*.warpmap.txt` files in this
  lane's ignored `work\cache`; filenames are preserved.
- References and sites: the frozen baseline `work\input-cache` arrays and
  `out\SITE-MANIFEST.json`, unchanged.
- Estimators: import `audit_geometry.py`, `measure.py`, and `common.py` from
  `experiments\SCORECARD-BASELINE` under `python -B`. Rebind only
  `audit_geometry.OUT` to this lane's `out` and `audit_geometry.WORK` to the
  frozen baseline `work`, then call `audit_geometry.main()` unchanged.
- `audit_geometry.PAIRS`, thresholds, downsample, ECC settings,
  `measure.COMMON_SHAPE`, references, and sites remain untouched.

All eight arms are required so inherited `audit_geometry.main()` and `PAIRS`
execute unchanged, including the worst frozen arm, `m2-second-first16`.

## Invocation and environment

The control command is:

```text
strehl.exe stack <exact frozen input dir> --out <ignored control TIFF> --linear-srgb --demosaic
```

Each Crop command is:

```text
strehl.exe stack <exact frozen input dir> --out <ignored Crop TIFF> --linear-srgb --demosaic --cover crop
```

Commands run serially and refuse an existing output. Effective thread
variables are exactly:

```text
RAYON_NUM_THREADS=6
OMP_NUM_THREADS=6
OPENBLAS_NUM_THREADS=6
MKL_NUM_THREADS=6
NUMEXPR_NUM_THREADS=6
PYTHONIOENCODING=utf-8
STREHL_CACHE_DIR=<absolute private work\cache>
```

Before every binary invocation, every other ambient `STREHL_*` variable is
removed. This includes `STREHL_COVER`, `STREHL_WARPMAP`,
`STREHL_PYRAMID_WORKERS`, `STREHL_ALIGN`, `STREHL_SMOOTH`,
`STREHL_SMOOTH_HUBER`, `STREHL_FIX_HALO*`, `STREHL_GATE_FLOOR`,
`STREHL_DEFECT*`, `STREHL_EDGE_*`, `STREHL_ACUITY`,
`STREHL_FULLRES_GATHER`, `STREHL_ONLY_FRAME`, `STREHL_MERGE`, and
`STREHL_VEIL*`. The preflight manifest records all `STREHL_*` names present in
the frozen source and their effective unset/set state.

The intentionally omitted CLI values are frozen as: all frames (`--limit`
unset); default `pyramid` merge; 7 bands; band-noise gate 2.0; coarse exponent
2.0; 1.4x per-octave sharpening; soft selection; mean base; no display sRGB
curve; linear sRGB on; full-resolution Malvar demosaic on; exposure 0; auto
exposure off; no estimator gate/focus/ROIs/maps/statistics; confidence tail
0.05; Catmull-Rom resampler; gear-matched lateral-CA default; and no optional
output maps. The pyramid banner is authoritative where a globally named option
does not apply: it reports photometric gain and the estimator-only stages as
not applied. The control omits `--cover` and therefore resolves to Scale; the
test arm passes `--cover crop`.

## Stop-before-Crop control

Before any Crop render, rerender `m2-second-first16` without `--cover`.
Required SHA-256:

`3d46f11413e5cf37bdeb730eb6faf66c266ac52107e1b5af1e032052080d16bc`

If it differs, write the control record and stop. Do not render, tune, retry, or
interpret Crop.

## Frozen failure inputs and gates

These outcomes are named before any real value is read:

1. The eight original Scale arms are RED at **0.2901% through 0.4619%** ECC
   scale disagreement.
2. The inherited estimator must put its planted 0.300% synthetic scale case
   RED.
3. Its identity and translation nulls must remain GREEN.
4. Any output smaller than frozen `COMMON_SHAPE = 4608 x 6912` is RED and an
   `output_luma` exception is a result, not missing data.
5. Any output whose array dimensions differ from the native active image
   `4688 x 7032` is RED for the native-size program-output clause.
6. Retaining less than 99.0% of the frozen common-input overlap is RED.
7. Fewer than 80% of preregistered sites surviving identically is RED.
8. More than 2 percentage points of differential site attrition is RED.
9. A non-translation residual above 0.10 native px is RED.
10. The Scale control hash mismatch is a hard stop before Crop interpretation.

The inherited ECC similarity gates are scale disagreement at most 0.10% and
rotation disagreement at most 0.02 degrees. `measure.geometry` supplies the
separate non-translation residual. The returned `aligned` array is removed
before JSON serialization.

## Measurements

For every render, record argv, effective environment/defaults, return code,
diagnostic wall time, TIFF dimensions/dtype/byte count/SHA-256, alignment and
coverage banners, parsed coverage `k` and Crop rectangle, and private-cache
hashes before/after. Require the same reference frame, placed/refused counts,
resampler, and printed coverage `k` as the frozen Scale counterpart.

Commission the inherited ECC estimator before reading real values. Then:

1. run unchanged `audit_geometry.main()` over all eight Crop outputs;
2. call unchanged `measure.output_luma` and `measure.geometry` per Crop arm;
3. place the existing frozen Scale ECC and residual readings beside Crop;
4. derive the Crop rectangle's full-resolution scene origin and confirm output
   dimensions against that integer mapping;
5. test containment of frozen `input_crop = [40, 58, 4608, 6912]`;
6. test every preregistered M1/M2 site rectangle in the applicable arms and
   compute differential attrition.

## Q2 decision rule

Each current scorecard clause is ruled separately. A same-native-pitch common
crop can be scientifically comparable when its scene-coordinate mapping and
fixed overlap are established. That does not waive the current formal rule
that each program emit a native-size 16-bit linear TIFF. Comparator render
geometry is not measured in this phase, and the common-ProPhoto-TIFF adapter
remains absent.

This lane does not implement a border-profile instrument. `BUILD-CROP.md`,
`cover-default.md`, and live `M-COVER-BORDER` own the outer-pixel question.
Q2 may cite that warning as unresolved or previously measured, but will not
reuse its numbers as new measurements.

## Prior art read before the gates

- `docs/research/BUILD-CROP.md`
- `docs/research/cover-default.md`
- `docs/research/M103-halfdrift.md`
- `docs/research/M112-real-pixels.md`
- `docs/research/M95-coverage.md`
- `docs/research/M104-resample-verify.md`
- `docs/research/M99-photometric.md`
- `docs/research/M95-dose.md`
- `docs/research/V-RIM.md`
- `docs/research/M-PHASE0-SPLIT2.md`
- `docs/research/SCORECARD-BASELINE.md`
- live `experiments/M-COVER-BORDER` preregistration and amendments

`M8-overshoot` is outside this lane and is not read or duplicated.


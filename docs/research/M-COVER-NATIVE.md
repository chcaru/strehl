# M-COVER-NATIVE — Phase A Q1/Q2

## Answer

**MEASURED — Q1: no, the complete §1.5 geometry gate does not clear.** The
shipped `CoverMode::Crop` removes the Scale arm's 0.2901–0.4619% magnification
failure: all eight Crop arms measure 0.0174–0.0231% scale disagreement and
remain within 0.02 degrees rotation. But all eight fail the separately required
`<=0.10 output px RMS` non-translation residual, at 0.3162–1.4765 px. The M1
geometry prerequisite therefore remains blocked.

**VERIFIED/DERIVED — Q2: Crop also violates the native-size output contract.**
Every TIFF is a same-pitch, unity-scale crop large enough to contain 100% of
the frozen common overlap, with 100% site survival and 0.0 percentage-point
differential attrition. Scientifically, that establishes a fixed common region
that can be compared after the permitted translation removal. Formally, the
current scorecard says every program must emit a native-size TIFF; Crop emits
smaller TIFFs. The absent common-ProPhoto-TIFF adapter, unmeasured comparator
render geometry, non-landmark rejection-only ECC audit, and residual failures
independently keep the comparison `UNMEASURED`.

This report covers Q1 and Q2 only. Q3 and Q4 were not started.

## Frozen provenance and control

**VERIFIED.**

| Item | Frozen/result value |
|---|---|
| binary | `experiments\SCORECARD-BASELINE\work\bin\strehl.exe` |
| binary SHA-256 | `814eb719608cc0f085fbd49e7529eb6fa4e50031070f5f57af4fc2812cee4363` |
| binary version | `strehl 0.0.0 (4b60b1ba9f56)` |
| exact input instances | 112 files across eight existing frozen arm directories; all matched the 64 unique hashes in `INPUT-MANIFEST.json` |
| frozen dependency audit | all 160 hashed files unchanged before/after |
| frozen cache | all eight baseline warp maps unchanged |
| private cache | eight byte copies, filenames preserved, unchanged before/after every recorded run |
| Scale control arm | `m2-second-first16`, no `--cover` argument |
| required/control SHA-256 | `3d46f11413e5cf37bdeb730eb6faf66c266ac52107e1b5af1e032052080d16bc` / exact match |
| control dimensions | native `7032 x 4688`, array `4688 x 7032 x 3`, `uint16` |

The control matched before any Crop interpretation. No tuning or replacement
solve was attempted.

**DEVIATION, VERIFIED:** the tracked diff/status of every protected path
remained unchanged, and the frozen baseline itself remained byte-identical.
During the run, ignored filesystem content under protected
`experiments\M8-overshoot` changed concurrently: the final provenance snapshot
grew from 5,403 to 5,729 files. Independent verification observed that growth
continuing after finalization, so no stable later whole-tree count is claimed.
This lane did not read file content there, write there,
revert it, or use it. Therefore whole-tree immutability of that one protected
path cannot be claimed, although its Git-visible state was unchanged.

## Exact invocation

**VERIFIED.** Commands ran serially. The absolute command for the Scale control
was:

```text
C:\dev\blog\death-of-software\projects\strehl\experiments\SCORECARD-BASELINE\work\bin\strehl.exe stack C:\dev\blog\death-of-software\projects\strehl\experiments\SCORECARD-BASELINE\work\inputs\m2-second-first16 --out C:\dev\blog\death-of-software\projects\strehl\experiments\M-COVER-NATIVE\out\renders\control-scale-m2-second-first16.tiff --linear-srgb --demosaic
```

The eight Crop invocations were the same frozen binary and corresponding
absolute frozen input/output paths:

```text
...\strehl.exe stack ...\work\inputs\m1-bright-a12        --out ...\out\renders\m1-bright-a12.tiff        --linear-srgb --demosaic --cover crop
...\strehl.exe stack ...\work\inputs\m1-bright-b12        --out ...\out\renders\m1-bright-b12.tiff        --linear-srgb --demosaic --cover crop
...\strehl.exe stack ...\work\inputs\m1-second-a12        --out ...\out\renders\m1-second-a12.tiff        --linear-srgb --demosaic --cover crop
...\strehl.exe stack ...\work\inputs\m1-second-b12        --out ...\out\renders\m1-second-b12.tiff        --linear-srgb --demosaic --cover crop
...\strehl.exe stack ...\work\inputs\m2-bright-first16    --out ...\out\renders\m2-bright-first16.tiff    --linear-srgb --demosaic --cover crop
...\strehl.exe stack ...\work\inputs\m2-bright-second16   --out ...\out\renders\m2-bright-second16.tiff   --linear-srgb --demosaic --cover crop
...\strehl.exe stack ...\work\inputs\m2-second-first16    --out ...\out\renders\m2-second-first16.tiff    --linear-srgb --demosaic --cover crop
...\strehl.exe stack ...\work\inputs\m2-second-second16   --out ...\out\renders\m2-second-second16.tiff   --linear-srgb --demosaic --cover crop
```

`RENDER-MANIFEST.json` contains every fully expanded absolute argv.

**VERIFIED environment:** `RAYON_NUM_THREADS=6`, `OMP_NUM_THREADS=6`,
`OPENBLAS_NUM_THREADS=6`, `MKL_NUM_THREADS=6`,
`NUMEXPR_NUM_THREADS=6`, `PYTHONIOENCODING=utf-8`, and
`STREHL_CACHE_DIR=<this lane>\work\cache`. Every other ambient `STREHL_*`
variable was removed before each binary invocation.

**VERIFIED defaults:** all files in each exact directory (`--limit` omitted);
default pyramid merge; 7 bands; gate 2.0; coarsest exponent 2.0; 1.4x
per-octave exponent ramp; soft selection; mean base; linear sRGB without the
display curve; full-resolution Malvar demosaic; exposure 0; auto exposure off;
Catmull-Rom; gear-matched lateral-CA default; no optional maps, estimator
controls, ROIs, or statistics. The binary banner states that photometric gain
and other estimator-only stages are not applied on this pyramid path. Scale was
the omitted control default; Crop was explicit.

The first Crop binary completed before the original harness selected the wrong
one of two coverage banners. `AMENDMENT-1.md` froze the parser repair before the
remaining seven renders. The completed TIFF was not overwritten or rerendered;
its exact command/log/output were recovered, and its binary `total: 10.6 s`
banner is the diagnostic wall value because the outer timer was lost.

## Estimator commissioning

**MEASURED before real values.** This is the unchanged frozen
`audit_geometry.py` whole-image ECC estimator: the images are area-downsampled
8x, an affine ECC fit is made over the whole image, and scale is derived from
the affine determinant. It is not literal discrete input-derived landmarks.
It was added after the score bytes and can reject an arm but cannot rescue or
score it.

| Commissioning case | Scale disagreement | Rotation | Expected/result |
|---|---:|---:|---|
| identity null | 0.000000% | -0.000000 deg | GREEN / GREEN |
| translation null | 0.008363% | -0.005718 deg | GREEN / GREEN |
| planted 0.300% scale + rotation | 0.303140% | -0.024093 deg | RED / RED |

The unchanged commission returned `commissioned=true`,
`null_stayed_green=true`, and `plant_went_red=true`. OpenCV's estimator thread
count was set to 6.

## Q1 — frozen Scale versus Crop geometry

**MEASURED.** `audit_geometry.OUT` alone was rebound to this lane's `out` and
`audit_geometry.WORK` to the frozen baseline `work`; unchanged
`audit_geometry.main()` then executed all eight inherited `PAIRS`. The Scale
columns are the committed frozen readings. The Crop residual calls unchanged
`measure.output_luma` and `measure.geometry`; the returned aligned image was
removed before JSON.

| Arm | Scale ECC scale | Crop ECC scale | Crop rotation | Scale residual RMS px | Crop residual RMS px | §1.5 Crop geometry |
|---|---:|---:|---:|---:|---:|---|
| `m1-bright-a12` | 0.294655% | 0.017553% | -0.000704 deg | 3.343651 | 0.663325 | FAIL residual |
| `m1-bright-b12` | 0.301891% | 0.017422% | -0.003205 deg | 3.083829 | 1.170470 | FAIL residual |
| `m1-second-a12` | 0.290072% | 0.020748% | +0.000216 deg | 3.593049 | 0.678233 | FAIL residual |
| `m1-second-b12` | 0.290358% | 0.021350% | -0.001268 deg | 3.187475 | 0.489898 | FAIL residual |
| `m2-bright-first16` | 0.337678% | 0.023079% | +0.002455 deg | 5.053711 | 1.476482 | FAIL residual |
| `m2-bright-second16` | 0.299185% | 0.018739% | -0.002527 deg | 3.266497 | 0.800000 | FAIL residual |
| `m2-second-first16` | 0.461888% | 0.021416% | +0.000001 deg | 5.094114 | 0.911043 | FAIL residual |
| `m2-second-second16` | 0.299620% | 0.018310% | +0.000529 deg | 3.445287 | 0.316228 | FAIL residual |

**MEASURED verdicts:**

- Scale disagreement `<=0.10%`: PASS, 8/8 Crop arms.
- Rotation disagreement `<=0.02 deg`: PASS, 8/8 Crop arms.
- Non-translation residual `<=0.10 output px RMS`: FAIL, 0/8 Crop arms.
- Complete §1.5 geometry conjunction: FAIL, 0/8.

The residual instrument removes a global translation with the frozen Fourier
phase-ramp path and measures four local translation residuals; it does not
replace the frozen post-score ECC with a new fitted-landmark implementation.

## Crop outputs and integer scene mapping

**VERIFIED/DERIVED.** The banner's Crop rectangle is in half-resolution CFA
plane pixels. The writer crops by integer addressing and doubles both axes for
the demosaiced output. Every observed TIFF dimension equals exactly twice its
banner rectangle; no coverage scale is composed.

| Arm | `k` | Plane crop `(x,y,w,h)` | Output width x height | Bytes | SHA-256 |
|---|---:|---|---:|---:|---|
| `m1-bright-a12` | 0.9973 | `(5,4,3506,2336)` | `7012 x 4672` | 196,563,208 | `995bec815fbc9d7b0b29ec4d9b8a0fcbcf622ac084cfe5d5c6765d2fb1adc3ee` |
| `m1-bright-b12` | 0.9972 | `(5,4,3506,2336)` | `7012 x 4672` | 196,563,208 | `b6468ca016396f63767ee8f61270bfc4126167e3b931e781abf6e29ebfb371db` |
| `m1-second-a12` | 0.9973 | `(5,4,3506,2336)` | `7012 x 4672` | 196,563,208 | `2508c70feab85b2331b420453e92c93f96d80ced5b868051c30b9be3bc9fae2a` |
| `m1-second-b12` | 0.9973 | `(5,4,3506,2336)` | `7012 x 4672` | 196,563,208 | `ec03b3051c83f76536848f17effee15d136519a4eb9fd73f5f5ee740f96cedc1` |
| `m2-bright-first16` | 0.9969 | `(6,4,3504,2336)` | `7008 x 4672` | 196,451,080 | `e883de25b493cdf8c55d6e7008a5810e0dc92e4553e635a0920f9f87e1b93f83` |
| `m2-bright-second16` | 0.9972 | `(5,4,3506,2336)` | `7012 x 4672` | 196,563,208 | `a3d71e96623fd55f11125292ac6807414e61c156d0ff38a915871153e6db29b7` |
| `m2-second-first16` | 0.9956 | `(8,6,3500,2332)` | `7000 x 4664` | 195,890,824 | `a0b38ce9cab2cd0c1030da21d8d44dc5832055045c03dc89c5d45e27a893ee1c` |
| `m2-second-second16` | 0.9972 | `(5,4,3506,2336)` | `7012 x 4672` | 196,563,208 | `7f58d9c124ebdf20af69a2c85f43905d24d1ecd1eb37d87c872ca26f6f5b3129` |

All outputs are `HxWx3 uint16` linear-sRGB TIFFs. None equals native active
`7032 x 4688` (`4688 x 7032` array order), but all exceed frozen
`COMMON_SHAPE = 4608 x 6912`.

The corresponding full-resolution Crop rectangles in `(y,x,h,w)` are:

- `(8,10,4672,7012)` for six arms;
- `(8,12,4672,7008)` for `m2-bright-first16`;
- `(12,16,4664,7000)` for `m2-second-first16`.

**DERIVED:** every rectangle contains the complete registered common-input
rectangle `(40,58,4608,6912)`, so retained common overlap is exactly 100.0% in
every arm. The unchanged `output_luma` centre slice starts at scene coordinate
`(40,60)` in every Crop arm, two pixels right of the input-manifest origin.
That fixed 2 px translation is explicitly measurable and removable by the
scorecard-permitted analytic translation step; no scale or metric resampling is
needed. The exact registered `(40,58)` region also remains present in every
output.

## Site survival

**DERIVED from the verified integer rectangles and frozen site manifest.**

| Site family/comparison | Sites per arm | Survival | Differential attrition |
|---|---:|---:|---:|
| M1 bright (`a12`, `b12`) | 486 | 100.0%, 100.0% | 0.0 pp |
| M1 second light (`a12`, `b12`) | 486 | 100.0%, 100.0% | 0.0 pp |
| M2 bright (`first16`, `second16`) | 455 | 100.0%, 100.0% | 0.0 pp |
| M2 second light (`first16`, `second16`) | 455 | 100.0%, 100.0% | 0.0 pp |

Thus the `>=80%` site-survival and `<=2 pp` differential-attrition clauses
pass. This is a geometric survival claim only; it does not certify the Crop
outer pixels.

## Q2 — actual current scorecard rules

**VERIFIED:** current §1.5 content and frozen v1.1 §1.5 are identical after the
repository's CRLF/LF normalization: 778 bytes,
SHA-256 `39efbd5c6f8d251c8bb4ed1c64e1a73b084511886229c6670e7bdca008e35ef9`.

The current file states:

- lines 156–157: “Write **uncompressed** 16-bit **linear ProPhoto RGB, D50**
  TIFFs at the native active-image dimensions.”
- lines 163–166: the programs must receive the exact same TIFF bytes; without a
  strehl adapter or boundary hash identity, competitive quality remains
  `UNMEASURED`.
- lines 175–177: “Each program must emit a native-size 16-bit linear TIFF,”
  with no resized output after stacking.
- line 225: “Outputs must retain native scale. Resize is a hard invalidation.”
- lines 226–229: crops are frozen from common-input overlap, must retain
  `>=99.0%`, translation may be removed analytically, and frequency metrics may
  not resample an output.
- lines 230–232: scale `<=0.10%`, rotation `<=0.02 deg`, and non-translation
  residual `<=0.10 output px RMS`.
- lines 233–235: `>=80%` identical site survival and no more than `2 percentage
  points` differential attrition.

### Per-clause verdict

| Current clause | Verdict | Basis |
|---|---|---|
| §1.2 common native-size linear ProPhoto input | **UNMET / UNMEASURED** | This is the registered native-RAW product diagnostic, not the absent common-TIFF arm; no strehl TIFF adapter or internal byte-identity proof was added. |
| §1.3 16-bit linear output | **PASS for container/linearity** | TIFF pages are `uint16 RGB`; banners say linear sRGB with no transfer curve. |
| §1.3 native-size program output | **FAIL 8/8** | Crop outputs are `7000–7012 x 4664–4672`, not `7032 x 4688`. |
| §1.3 no resized post-output | **PASS for this path** | Crop is integer addressing at unity pitch; no output resize/upsample occurs. |
| §1.5 native scale / hard resize invalidation | **PASS 8/8 as rejection audit** | ECC scale is 0.0174–0.0231%; banners state unity scale and no coverage scale. |
| §1.5 fixed common-overlap FOV `>=99%` | **PASS 8/8** | Exact integer containment gives 100.0%. |
| §1.5 analytic translation / no metric resampling | **PASS for this geometry procedure** | The residual path uses the frozen Fourier translation; centre/common extraction is slicing. No frequency score was run. |
| §1.5 scale `<=0.10%`, rotation `<=0.02 deg` | **PASS 8/8** | Table above. |
| §1.5 non-translation residual `<=0.10 px` | **FAIL 8/8** | 0.3162–1.4765 px RMS. |
| §1.5 sites `>=80%`, differential attrition `<=2 pp` | **PASS** | 100.0% survival, 0.0 pp differential attrition. |
| Formal comparability to a full-frame comparator | **UNMEASURED / not admitted** | Native-size output fails; comparator render geometry was not measured; common-TIFF adapter remains absent; the ECC audit is not literal input-landmark scoring. |
| Scientific comparability of the shared crop | **ARGUED yes, conditionally** | Exact same-pitch scene mapping and 100% fixed-overlap/site containment permit a common crop after translation removal, but this does not waive formal scorecard clauses or certify borders. |

## Prior-art boundary

**VERIFIED as design provenance, not remeasurement.**

- `BUILD-CROP.md` and `cover-default.md` establish Crop as the no-coverage-
  resample arm while warning against trusting its outer pixels; Scale remained
  the default.
- `M103-halfdrift.md` separates geometry repair from a sharpness claim.
- `M112-real-pixels.md` motivates evaluating only verified covered support.
- `M95-coverage.md` and `M95-dose.md` show that coverage resampling is not the
  whole quality mechanism.
- `M104-resample-verify.md` distinguishes native sampling from field of view.
- `M99-photometric.md` requires scene-fixed interpretation of level changes.
- `V-RIM.md` disqualifies its rim statistic as a generic border certificate.
- `M-PHASE0-SPLIT2.md` licenses analytic translation without metric
  resampling.
- `SCORECARD-BASELINE.md` records the original Scale geometry rejection and
  absent common-TIFF adapter.
- Live `M-COVER-BORDER` owns border contamination. This phase did not open its
  results as a new measurement and did not implement a border-profile
  instrument.

No `M8-overshoot` content was read or duplicated.

## Limitations

- **UNVERIFIED:** comparator output geometry; no comparator was rendered or
  measured here.
- **UNVERIFIED:** formal common-input identity; the common-ProPhoto-TIFF adapter
  is still absent.
- **UNVERIFIED in this phase:** Crop outer-pixel cleanliness. Existing Crop
  design records warn about the boundary, and `M-COVER-BORDER` owns its live
  instrument.
- **LIMITED:** the ECC audit is whole-image, downsampled, affine, and
  post-score rejection-only, whereas current §1.5 literally names
  input-derived landmarks.
- **MEASURED failure:** the unchanged four-tile residual instrument rejects all
  eight Crop arms even though the ECC scale/rotation estimates pass.
- **DEVIATION:** concurrent ignored-file growth under protected
  `experiments\M8-overshoot` prevents a whole-tree “unchanged” claim for that
  path; frozen inputs, caches, tracked protected state, and all owned outputs
  remained auditable.

## Ruling

**MEASURED/VERIFIED: the M1 geometry gate does not unblock.** Crop fixes the
specific native-scale magnification failure and preserves the complete frozen
overlap/sites at native pitch, but it fails the 0.10 px residual in every arm
and fails the scorecard's native-size program-output clause in every arm.
Formal competitive comparison remains `UNMEASURED`.

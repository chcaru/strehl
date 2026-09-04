# M171 — aperture metadata does not force a realized-detail ordering

**Status: PHYSICS PREFLIGHT FAILED; STOPPED BEFORE RAW PIXEL DECODE, CANDIDATE
IMPLEMENTATION OR M167 ADJUDICATION.**

## 1. Physics verdict first

**VERIFIED/DERIVED: no.**  The existing aperture ladder cannot be the external
truth reference on aperture metadata alone.  Its *ideal clear-pupil*
diffraction MTF is ordered, but the realized lens + teleconverter + focus-state
MTF is not physically forced to have that order.  F-number supplies an upper
envelope, not the missing lower bound on the widest aperture.  A physically
valid aberrated pupil consistent with the same EXIF reverses f/5.6 and f/8.

This is the frozen stop condition in
`experiments/M171-aperture-reference/PREREGISTRATION.md`.  No image statistic
can repair the truth label after this failure: measuring the edge in the same
outputs and then calling that measurement external truth would give up the
output-independent observation that Amendment 6 requires.

### 1.1 What the files actually say

**VERIFIED BY RUNNING.**  ExifTool 13.58 read metadata, but no pixel arrays,
from all 789 ARWs under `requests\19-razor-edge`.  Every file reports:

- camera `ILCE-7CM2`;
- lens `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`;
- `LensType3 = 33094`;
- focal length and 35-mm-equivalent focal length both `200 mm`;
- maximum aperture `5.59591869015324`;
- ISO 100; and
- the directory's f/5.6, f/8 or f/11 value in `FNumber`.

The six exhaustive groups were:

| geometry | EXIF f-number | files | exposure | capture span |
| --- | ---: | ---: | ---: | --- |
| diagonal tilt | 5.6 | 279 | 2.5 s | 16:29:45–16:43:31 |
| diagonal tilt | 8 | 210 | 2.5 s | 16:45:30–16:55:50 |
| diagonal tilt | 11 | 143 | 2.5 s | 16:57:45–17:04:46 |
| horizontal flat | 5.6 | 67 | 3.2 s | 15:48:31–15:52:30 |
| horizontal flat | 8 | 50 | 3.2 s | 15:43:12–15:46:09 |
| horizontal flat | 11 | 40 | 3.2 s | 15:32:46–15:35:08 |

The full records and dates are in
`experiments/M171-aperture-reference/out/audit.json`.

### 1.2 The two-stop arithmetic is right, but it was applied twice

**VERIFIED/DERIVED.**  A 2x teleconverter doubles focal length while preserving
the entrance-pupil diameter, so it doubles the f-number and reduces nominal
irradiance by four, exactly two stops.  Sony explicitly specifies a two-stop
loss for its SEL20TC; Viltrox specifies 2x conversion and accurate aperture
reporting for its Sony unit.  Viltrox does not publish a measured T-stop, so
additional real transmission loss is **not established**.

The recorded values are already post-teleconverter system values.  The bare
lens is 100 mm f/2.8; the files report a 200 mm lens with maximum aperture
f/5.5959.  Those are exactly `2 × 100 mm` and `2 × f/2.8`.  Consequently:

| quantity | recorded system values | values in the proposed argument |
| --- | --- | --- |
| f-number | **5.6 / 8 / 11** | 11 / 16 / 22 |
| interpretation | TC applied once by camera | TC applied a second time |

The proposed Airy diameters, 14.762 / 21.472 / 29.524 µm, are arithmetically
correct for f/11 / f/16 / f/22, but those are not the three EXIF f-numbers.

**NOT IDENTIFIED BY EXIF.**  Macro working f-number is approximately
`Nw = (1 + |m|/P)N`, where `m` is magnification and `P` is pupil
magnification.  EXIF does not identify both.  This correction remains
monotone in recorded `N` at fixed geometry, but its unknown size prevents an
absolute cutoff calculation from metadata alone.

### 1.3 Sensor sampling and the nominal-N ideal diffraction calculation

**VERIFIED from Sony specifications; DERIVED arithmetic.**  Sony specifies a
35.9 × 23.9 mm sensor and 7008 × 4672 effective-pixel output.  This gives
5.1227169 µm horizontal and 5.1155822 µm vertical pitch, with horizontal
Nyquist 97.6045 lp/mm.

For wavelength 550 nm, the clear circular-pupil model is:

```text
Airy first-zero diameter = 2.44 λ N
cutoff                   = 1 / (λ N)
x                        = frequency λ N
MTF(x)                   = (2/π) [acos(x) - x sqrt(1-x²)], 0 <= x < 1
```

**DERIVED and independently regression-checked.**  These rows use recorded
nominal system `N`; at macro distance the unknown working factor multiplies
`N`, lowering every cutoff and MTF without changing the ideal ordering.

| recorded N | Airy diameter | sensor pixels | cutoff | ideal MTF at Nyquist |
| ---: | ---: | ---: | ---: | ---: |
| 5.6 | 7.5152 µm | 1.4670 px | 324.6753 lp/mm | 0.623083 |
| 8 | 10.7360 µm | 2.0958 px | 227.2727 lp/mm | 0.470502 |
| 11 | 14.7620 µm | 2.8817 px | 165.2893 lp/mm | 0.294469 |

This proves the **ideal diffraction term** is monotone.  It does not prove that
the optical system is diffraction-limited.  “Airy diameter exceeds a pixel” is
not a wavefront-aberration measurement, a Strehl bound or a lower MTF bound.

### 1.4 Why the realized ordering is not forced

**DERIVED.**  For pupil `P = A exp(i 2πW/λ)`, incoherent OTF is the normalized
autocorrelation of `P`.  The triangle inequality makes the ideal clear-pupil
MTF an upper bound on an aberrated pupil at each frequency.  Therefore:

```text
MTFactual(f/8) <= MTFideal(f/8) < MTFideal(f/5.6)
```

does **not** imply:

```text
MTFactual(f/8) < MTFactual(f/5.6).
```

There is no EXIF observation of `W` and no certified lower bound on
`MTFactual(f/5.6)`.  This matters especially because recorded f/5.6 is the
wide-open setting of the f/2.8 master plus 2x teleconverter; stopping down can
reduce spherical aberration, coma, astigmatism and focus error while diffraction
moves in the opposite direction.

**VERIFIED BY RUNNING an existence counterexample; not asserted as a fit to
this lens.**  `audit.py` evaluated the pupil autocorrelation for primary
spherical aberration `W040 = 0.60 waves` at recorded f/5.6, scaled as `N^-4`
when stopping down, with an illustrative common macro working factor 3.72.  At
20 lp/mm:

| recorded N | illustrative working N | W040 | ideal MTF | aberrated MTF |
| ---: | ---: | ---: | ---: | ---: |
| 5.6 | 20.832 | 0.6000 waves | 0.710809 | **0.30** |
| 8 | 29.760 | 0.1441 waves | 0.590761 | **0.55** |
| 11 | 40.920 | 0.0403 waves | 0.446878 | **0.44** |

Thus f/8 beats f/5.6 even though its ideal envelope is lower.  The numerical
pupil autocorrelation agrees with the analytic unaberrated MTF to maximum
absolute error 0.000094, below the 0.0002 bar.  A separate 512-to-1024 grid
convergence check on the aberrated rows changed any MTF by at most 0.000535,
below its 0.001 bar, and all three two-decimal reports were stable across both
grids.

The 0.60-wave value is deliberately only a counterexample.  M171 does not know
the captured unit's wavefront error.  That ignorance is exactly why the EXIF
ordering is not forced; the burden was to rule the reversal out, not to show
that it is guaranteed.

## 2. Development/holdout declaration

The declaration was frozen in commit `f8696659` before any M171 pixel decode or
candidate execution.

- **Development:** all six `19-razor-edge` stacks.  The three horizontal-flat
  stacks were already burned by M128.  Direct evidence does not prove that the
  diagonal block, after a 37-minute gap and geometry change, is the same
  uninterrupted unit; M171 conservatively assigned those three stacks to
  development prospectively, before opening any of their pixels.
- **Holdout:** none assigned and none spent by M171.  The
  `7-aperture-pairs` fabric session is already represented by decoded-frame
  artifacts throughout M129 despite an older register calling three rows
  clean.  The miscellaneous razor directory has only one aperture and cannot
  form a ladder.

**Disclosure.**  During preflight planning, an agent surfaced historical M128
numbers before the declaration.  They belong to the already-burned development
unit and were not used for the physical decision.  No clean unit was opened.

## 3. Preregistration and commissioning evidence

**VERIFIED BY RUNNING.**

- `audit.py --self-test` passed the ideal planted improvement
  (`MTF40: 0.843535 > 0.777072`) and planted degradation
  (`0.694911 < 0.777072`).
- The unmodified metadata audit passed all 789 records and returned
  `verdict = NOT_FORCED`, `candidate_built = false`,
  `m167_executed = false` and `confidence_interval = "NO CI"`.
- The read-only tree had 791 files / 28,397,995,881 bytes immediately before
  and after the audit.  ExifTool performed metadata reads only.
- `commission.py` caught 20/20 anchored mutations and hard-errored on a missing
  anchor.  Source SHA-256 was unchanged before/after.

The literal RED evidence is serialized in
`experiments/M171-aperture-reference/out/commission.json`:

| planted defect | RED evidence |
| --- | --- |
| missing stack member | frame-count mismatch |
| metadata path outside the declared root | outside-root refusal |
| wrong camera, lens or lens ID | corresponding identity mismatch |
| wrong f-number, ISO, exposure, focus type or missing capture time | corresponding EXIF mismatch |
| wrong sensor width | pixel-pitch reference mismatch |
| wrong focal length or 35-mm focal length | corresponding focal-length mismatch |
| wrong post-TC maximum aperture | unexpected `MaxApertureValue` |
| Airy radius substituted for diameter | Airy reference mismatch |
| halved MTF normalization | analytic/numerical validation failure |
| planted improvement made equal to base | directional control failure |
| planted degradation made equal to base | directional control failure |
| spherical-aberration reversal erased | frozen stop-verdict failure |
| counterexample ignored | frozen stop-verdict failure |

Because the physical gate failed, **no detail candidate was built**, no RAW
pixel was decoded, no confidence interval exists (**NO CI**), and M167 was not
invoked.  A six-stack equal-count execution would require at least 40 frames
per arm per geometry, 240 RAW decodes; a one-geometry execution would require
120.  Neither was started.

## 4. Self-assessment against M167 P1–P6

| predicate | result |
| --- | --- |
| P1 flat ROI | **NOT RUN — no candidate** |
| P2 planted improvement | **NOT RUN BY M167**; physics audit's own directional control passed |
| P3 planted degradation | **NOT RUN BY M167**; physics audit's own directional control passed |
| P4 signed blur monotonicity | **NOT RUN — no candidate** |
| P5 sharpening discrimination | **NOT RUN — no candidate; no claim of USM safety** |
| P6 fail closed | **NOT RUN — no candidate** |

Passing P1–P6 could not rescue this aperture truth source: the candidate would
still be adjudicated against a label that the external observation does not
force.  The requested depth-of-field, exposure/noise, frame-count and
diffraction-versus-defocus controls therefore were not executed.

## 5. Sources

- Sony A7C II sensor specification:
  <https://helpguide.sony.net/ilc/2360/v1/en/contents/231h_specifications_ilc2360.html>
- Sony 7008 × 4672 image dimensions:
  <https://helpguide.sony.net/ilc/2360/v1/en/contents/0404M_jpeg_image_size.html>
- Sony FE 100mm F2.8 Macro GM specification:
  <https://www.sony.jp/ichigan/products/SEL100M28GM/spec.html>
- Viltrox 2x Sony teleconverter:
  <https://viltrox.com/products/tc-2-0x-teleconverter-for-sony>
- Sony's explicit two-stop statement for a 2x teleconverter:
  <https://www.sony.jp/ichigan/products/SEL20TC/feature_1.html>
- Airy diameter/cutoff:
  <https://www.edmundoptics.com/knowledge-center/application-notes/imaging/limitations-on-resolution-and-contrast-the-airy-disk/>
- Ideal circular-pupil MTF:
  <https://www.edmundoptics.com/knowledge-center/application-notes/optics/introduction-to-modulation-transfer-function/>

## 6. Reproduction

From the repository root:

```powershell
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMEXPR_NUM_THREADS='1'
$env:BLIS_NUM_THREADS='1'
$env:VECLIB_MAXIMUM_THREADS='1'
$env:PYTHONDONTWRITEBYTECODE='1'
python -B experiments\M171-aperture-reference\audit.py --self-test
python -B experiments\M171-aperture-reference\commission.py `
  --output experiments\M171-aperture-reference\out\commission.json
python -B experiments\M171-aperture-reference\audit.py `
  --output experiments\M171-aperture-reference\out\audit.json
```

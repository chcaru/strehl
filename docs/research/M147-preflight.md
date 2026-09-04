# M147 — in-field magnification preflight

Status: **PROVISIONAL INSTRUMENT; DO NOT SHOOT; REAL 2.03x OPTICAL PAIR
PENDING**

## 0. Verdict first

**MEASURED.** The current estimator recovers a real same-state null at
`1.0003525x`, returns an interval containing `1.0`, and correctly fails the
`2.0x` gate. It recovers a planted `2.031200x` resampling ratio at
`2.0312252x` and its provisional lower bound clears `2.0`. Both full-resolution
RAWs in the null complete in `21.66 s`.

**UNVERIFIED.** This is not yet a commissioned field gate. There is no real
converter-on/converter-off grid pair in the corpus, empirical interval
coverage has not yet been established, and the current `0.25%` systematic
allowance is an explicit unbound development choice rather than a measured
quantity. The real-optics interval width near `2.03x` is the gating unknown.

**DECISION.** Do not shoot the 891-frame session. The owner-facing two-frame
request is live as Ask 2a: photograph the same physically unmoved calibration
slide once with the converter fitted at maximum reproduction and once with it
removed near `1.32x`. Those two RAWs decide whether the registered target has
enough margin or must move.

## 1. What the tool measures

**DERIVED.** For one physical grid pitch `g`, sensor pitch `p`, and
magnifications `m_ref` and `m_TC0`, the measured sensor-pixel periods are

```text
P_ref = g * m_ref / p
P_TC0 = g * m_TC0 / p
P_ref / P_TC0 = m_ref / m_TC0.
```

The grid pitch and sensor pitch cancel. The tool therefore divides measured
periods directly. It never derives absolute magnification and never reads EXIF
focal length into the decision. The cancellation argument in the capture
design is correct.

**IMPLEMENTED.** `experiments/M147-preflight/preflight.py`:

1. accepts two explicitly role-labelled `.ARW` paths;
2. hashes the original files with SHA-256;
3. copies `rawpy.raw_image_visible` while the decoder context is alive;
4. uses the two native CFA green sub-lattices independently, with no demosaic
   and no resize;
5. detrends overlapping local `512 x 512` green-site tiles and applies a Hann
   window;
6. finds two non-collinear reciprocal-lattice peaks in each local 2-D Fourier
   spectrum, refines their coordinates parabolically, and converts their
   determinant to local pixels per grid period;
7. selects the dominant period family, refuses a competitive second family,
   and records local measurements in non-overlapping spatial blocks;
8. requires agreement between green phases, local period stability, adequate
   peak evidence, and compatible two-axis scale and rotation; and
9. divides the reference and TC0 period estimates directly.

This local reciprocal-lattice design was chosen because defocus attenuates a
periodic peak without moving it, affine illumination is removed before the
FFT, and rotation changes the two peak vectors without changing their
determinant. Spatial block results remain in the JSON rather than being
discarded behind one global number.

## 2. Interval and gate

**IMPLEMENTED.** The current interval independently resamples the accepted
spatial-block period estimates in each image for `10,000` deterministic draws
(seed `14720260904`), recomputes the ratio of medians, takes percentile
`[0.025, 0.975]`, envelopes all four cross-green ratios, and expands the
result by a provisional relative `0.0025` on each side.

**UNVERIFIED.** The bootstrap addresses extraction variation across measured
grid regions. It does not by itself prove coverage for converter-dependent
distortion, different optical blur, target non-coplanarity, repositioning, or
drift after the two preflight exposures. The extra `0.0025` was chosen as a
development allowance. It has no empirical or physical derivation and must
remain visibly unbound until commissioning supplies one.

**IMPLEMENTED.** A numerical reading is eligible only after RAW, lattice,
spatial stability, green-phase, anisotropy, rotation, and precision checks.
The decision then uses unrounded values:

```text
PASS if and only if interval_lower >= 2.0.
```

A point estimate above `2.0` with a lower bound below `2.0` is a `FAIL`. A
measurement refusal is also a `FAIL` and carries no ratio.

## 3. Results so far

The source frame for development is burned material and none of these values
is a score.

| Arm | Input/truth | Recovered ratio | Provisional interval | Width | Result |
|---|---:|---:|---:|---:|---|
| Real same-state null | consecutive `DSC00042/43.ARW`; truth `1.0` | `1.0003525064` | `[0.9928949949, 1.0078309377]` | `1.4931%` | truth covered; gate `FAIL` |
| Uniform scale plant | real `DSC00042.ARW` resampled to truth `2.031200` | `2.0312251532` | `[2.0212588972, 2.0462767512]` | `1.2317%` | provisional `PASS` |

**MEASURED.** The null error is `+0.0353%`. Its two axis ratios are
`1.0002931` and `1.0002962`; the reported anisotropy is
`0.0000030543`. The interval contains `1.0` and the tool does not confuse a
clean measurement with a pass.

**MEASURED.** The uniform plant error is `+0.00124%` relative. Its lower bound
is `2.0212589`. This demonstrates sensitivity to the required scale, but the
plant reuses correlated source pixels and introduces interpolation. Its
narrower interval is suspicious rather than evidence that the optical case
will be equally precise.

**MEASURED.** The null artifact records parameter SHA-256
`b56bd70421c6d1a7e9613394669d942107fe927acca148d37c785602a8a364b1`
and source SHA-256
`dd38a1fd91325e0cf5347aabf9160003f7384b962267828436c8c372e97db293`.
The first path-scoped checkpoint is commit
`98066cbd1f3ae2abca7b649c5b850590930d582c`.

## 4. Missing real pair

**VERIFIED.** M141's complete inventory reports that all `10,509` inventoried
ARWs use focal length `200 mm` and lens identity
`FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`. It explicitly concludes that
no frame proves the bare-lens TC0 state
(`docs/research/M141-capture-inventory.md:255-274`). The repository therefore
contains no real converter-on/converter-off grid pair at any ratio.

**REQUIRED.** The pending two-frame measurement must use:

1. the calibration slide, converter installed, maximum reproduction; and
2. the same physically unmoved slide, converter removed, TC0 near `1.32x`.

Use original full-resolution ARWs. Preserve the target plane and camera
roll/yaw; move axially to reframe. No scored session should begin before this
pair produces a commissioned lower bound at least `2.0`.

## 5. Operator command

Run from the repository root after the two frames exist:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python experiments\M147-preflight\preflight.py `
  --reference-arw "D:\path\TR-REF-PREFLIGHT.ARW" `
  --tc0-arw "D:\path\TC0-PREFLIGHT.ARW" `
  --output-json "experiments\M147-preflight\out\field-result.json"
```

Expected successful form:

```text
M147 MAGNIFICATION PREFLIGHT
Reference period: <value> sensor px
TC0 period:      <value> sensor px
Sampling ratio:  <value>
Conservative 95% interval: [<lower>, <upper>]
Verdict: PASS
PASS: the interval lower bound is at least 2.0. Preserve the rig settings and proceed with the capture protocol.
Artifact: <absolute path>
Elapsed: <seconds> s
```

Anything other than literal `Verdict: PASS` means do not shoot. On a measured
ratio failure the tool reports the approximate percentage by which to reduce
TC0 magnification and also asks the operator to verify converter seating and
maximum reference reproduction. On a quality refusal it tells the operator
whether to refocus, reframe, correct the target plane, or retake.

## 6. Commissioning still required

**UNVERIFIED.** Before field admission, retained artifacts must demonstrate:

| Arm | Required question |
|---|---|
| Scale plants around the margin | Are errors just inside and outside the `1.54%` design margin recovered with correct sign and magnitude? |
| Perspective | Does spatially varying projective scale become visible locally or refuse rather than average into a pass? |
| Anisotropic scale | Does a one-axis defect trigger the anisotropy refusal? |
| Wrong-period alias | Does a fundamental/second-harmonic conflict select the physical period or return `AMBIGUOUS_LATTICE`, never a confident factor-two answer? |
| Blur | Does mild blur preserve scale and hopeless blur refuse? |
| Partial grid | Does adequate retained coverage measure correctly while inadequate coverage returns `GRID_TOO_SMALL` or `NO_COHERENT_GRID`? |
| Degenerate input | Does a no-grid image refuse without a number? |
| Interval coverage | Does the claimed interval cover planted truth at approximately its nominal rate under independent perturbations? |
| Real optical pair | What is the interval width near `2.03x` with the actual converter states? |

The real optical pair is decisive. A synthetic result cannot bind the
converter-dependent systematic. If the real interval cannot clear `2.0` at
the registered setup, move the TC0 target lower; do not narrow the interval or
relax a quality gate after seeing the result.

## 7. Commands already run

Real null:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python experiments\M147-preflight\preflight.py `
  --reference-arw "D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl\flat-et1s-sw4-cpl\DSC00042.ARW" `
  --tc0-arw "D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl\flat-et1s-sw4-cpl\DSC00043.ARW" `
  --output-json experiments\M147-preflight\out\null.json
```

Uniform-scale development probe:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python experiments\M147-preflight\try_plants.py `
  "D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl\flat-et1s-sw4-cpl\DSC00042.ARW" `
  2.0312
```

No command wrote beneath `D:\personal\macro` or `D:\edited\macro`.

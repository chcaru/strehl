# strehl — pre-registered SOTA scorecard

**Status: SPEC / PRE-REGISTRATION v1.6 (2026-09-03).** The v1.0 metric, bar, and
control protocol was written before implementation lanes reported outcomes.
Subsequent revisions quarantine leaked evidence, classify captures before use, or
withdraw/tighten an instrument defeated by independent commissioning; each change is
recorded below. No v1.6 score output has been read. The competitive position remains
**UNKNOWN**.

**Revision 1.6 — underpowered S25 sharpening result superseded:** the earlier
24-seed `0.995819x` USM reading is replaced by the 64-site `1.028294x` result
against the unchanged 1% bar. This strengthens, but does not otherwise alter, M1's
withdrawal. It also preserves the independently successful PCHIP tone-witness
construction for future instruments.

**Revision 1.5 — M12 terms separated; existing evidence ruled out of protocol:**
fixed-worker reproducibility is now named **determinism**, while equality across
worker counts is named **scaling invariance**. Existing source admissions and a
reported unaligned N=20 1/4/8-worker sweep are strong diagnostic evidence that the
former holds and the latter fails, but they are not the registered N=33/105/299
native-product matrix. M12 therefore remains `UNMEASURED`; no host run was performed
for this revision.

**Revision 1.4 — defeated detail instrument withdrawn; M8 tightened before use:**
M1 now has no active statistic or bar because both registered outputs failed
independent commissioning. This revision also records which axes are scientifically
measurable now and splits M8 into per-frame resampler- and final-output hull
certificates. It registers no result and consumes no holdout.

**Revision 1.3 — fresh slide classified before outcomes:** the six
`high-res-calibration-slide-cpl` stacks arrived with input metadata only. They form one
657-frame physical-subject/session unit, assigned deliberately to development for the
flat-path geometry/resampling investigation. All six report IBIS on, so none is
admissible as an independent-repeat FRC arm. No render, metric, or visual verdict was
used for this assignment.

**Revision 1.2 — holdout quarantine:** the v1.1 baseline at `bc8f315a` reached no
metric because the geometry gate refused every arm. Separately, W1 rendered and swept
the calibration-grid-1 sw4 capture and disclosed outcomes before it was halted. The
entire same-subject calibration-grid session is therefore burned as future holdout
evidence; see §2.3 and quarantine commit `0c503d84`. No scorecard value changes from
`UNMEASURED`.

**Revision 1.1, still before any score render:** adds joint anti-cheat constraints,
caps every licensed detail claim at `0.25 cyc/px`, and makes decode/storage control
explicit in the timing protocol. It imports no phase-1 acceptance bar and no measured
quality result.

This document owns the definition and protocol, not a result. The first render of any
scored capture **under this protocol** seals v1.6; pre-existing unrelated masters are
not score outputs. A later change to an instrument, bar, eligibility rule, comparator
setting, capture, or aggregation rule requires a numbered revision and a fresh
holdout capture. Existing score outputs may then be used only for development.

## 0. What “SOTA” means here

The governing proposal does define it:

> “**SOTA = a pre-registered scorecard, versus named comparators, on axes with
> commissioned instruments.**”

That sentence and its requirement that every instrument first fail a relevant plant
and pass an untuned null are in `2026-08-sota-path.md` §1, lines 164–167. Its
end-state is conjunctive: detail at or beyond the best shipping comparator, strictly
lower noise, zero invented structure, bounded occlusion veil, calibrated per-pixel
acuity / effective sample count / physical depth, and competitive CPU speed
(`2026-08-sota-path.md` §1, lines 189–197). **Therefore, for strehl, SOTA means that
the shipping default passes every primary bar below against licensed Zerene Stacker
and Helicon Focus under one common linear-input protocol, while also emitting
independently calibrated trust and depth products and meeting the registered resource
bars.** It is not an average, a weighted score, or “wins most axes.”

The proposal supplies several exact systems bars and the exact `0.0000%` hull bar.
It leaves the veil, acuity, colour, coverage, and several other acceptance numbers as
literal `[bar]` placeholders. Numbers below marked **SCORECARD ADDITION** are this
document’s proposed completions, not claims that the governing proposal already made.

### 0.1 Decision rule

1. Every primary metric is a hard gate. No win compensates for a loss.
2. `UNMEASURED`, an uncommissioned checker, an invalid comparator arm, or an
   under-powered capture blocks a SOTA claim; it is not a pass or a loss.
3. A comparative quality gate uses the **best qualifying comparator envelope**:
   Zerene PMax, Zerene DMap, and Helicon Methods A, B, and C, each at its frozen
   factory setting and with user post-processing disabled. “Best” is chosen in the
   comparator-favouring direction for each metric.
4. Once a replacement M1 is admitted, a comparator mode may define a noise, artifact,
   speed, or memory envelope only if it passes the input/output transfer audit and
   retains at least `98%` of the highest replacement-M1 information score achieved by
   any registered mode on that capture. This stops a deliberately blurred fast/quiet
   mode from becoming the quality comparator. In v1.6 no mode can yet be
   quality-qualified.
5. Each capture must pass independently, and the pooled one-sided 95% confidence bar
   must also pass. Pooling may not rescue a failed capture.
6. All confidence intervals resample independent physical sites, not pixels:
   10,000 fixed-seed (`20260902`) hierarchical bootstrap draws by capture, then
   non-overlapping site. Rates use a Wilson one-sided 95% bound.
7. No pass/fail decision or public numerical detail claim may use a frequency above
   `0.25 cyc/native px`. A checker that reads higher must emit only the explicit
   `UNLICENSED_GT_0.25` label.

### 0.2 Joint anti-cheat constraints

The bars remain hard gates, but the natural tradeoffs below are scored and published
as **joint tuples from the same output bytes and settings**. No program may submit one
render for one member and another render for its opposite. The per-axis comparator
envelope remains an additional conservative bar; Pareto plots use each actual
program/mode as one point and never splice modes into a fictional point.

| Joint constraint | Cheat and opposed movement | Binding rule |
| --- | --- | --- |
| M1 information + M2 noise + M4 flat power + M8 hull | Harder averaging can lower noise by losing information; sharpening can flatter transfer while increasing flat power or leaving the source hull. | M1 presently has no admissible statistic. When it is replaced, publish the replacement detail value with `(eta, Q_flat, M8-R, M8-O)` from the same output and pass every bar simultaneously. Until then neither a noise-only nor a detail claim is valid. |
| M3 boundary integrity + local source coherence/width | Blur can hide a halo or veil while widening the edge and reducing agreement with the independently sharp source. | The same boundary render must pass M3's width bar and M5's local `rho_best>=0.90`; the build must also pass a future commissioned M1 on independent-repeat captures. |
| M6 clipping + §1.3 transfer + M5 highlight coherence | Darkening/tone compression avoids clipping; smoothing hides clipped texture. | The same output must pass the ramp, clipping, and highlight-coherence bars. |
| M9 false certification + M9 coverage | Universal confidence overclaims; universal refusal obtains perfect precision by saying nothing. | Publish `(false_certification, true_band_coverage)` from one map; both bars must pass. |
| M11 runtime + M12 determinism/scaling invariance/memory | Serial execution can make fixed-worker runs deterministic by abandoning the speed claim. | The primary CPU result is the 16-worker output; it must meet M11, reproduce at fixed width, and be byte-identical to 1/2/4/8-worker outputs while meeting M12. |

This opposed-pair framing is not universal. M7 colour has an external target, M10
depth has physical/hidden truth, and M8 has an exact independently reconstructed
invariant; inventing an “opposite” for them would be weaker than their conventional
controls. Joint constraints supplement, rather than replace, each metric's planted
defect and untuned null.

## 1. Measurement contract

### 1.1 Freeze before outputs

Before any stacker runs, commit these files under `experiments/SCORECARD/`:

- `INPUT-MANIFEST.json`: source ARW path, size, timestamp, SHA-256, EXIF dump,
  decoder binary hash, and every linear-development setting;
- `SITE-MANIFEST.json`: input-derived tile, edge, patch, and exclusion coordinates;
- `RUN-MANIFEST.json`: hardware, OS, power plan, program hashes, licences, versions,
  complete settings, worker count, cache state, and output contract;
- synthetic plants and their hidden truth in separate files. The checker receives
  truth only after the renderer has finished.

Site selection may inspect the common inputs but never a stacker output. The site
manifest is then hashed and immutable.

### 1.2 One common linear input

Competitive quality is measured only at a common merge boundary:

1. Decode each ARW once with one independently versioned LibRaw-based converter whose
   executable hash is frozen before rendering.
2. Apply sensor black/white levels and one frozen deterministic-pattern map estimated
   from independent matching dark/flat captures; if no matching map exists, M1/M9 are
   `UNMEASURED`. Apply the recorded camera white balance and one camera matrix once.
   Demosaic once. Write **uncompressed** 16-bit **linear ProPhoto RGB, D50** TIFFs at
   the native active-image dimensions.
3. Ignore every XMP sidecar. Disable auto-brightening, exposure compensation, tone
   curves, contrast, clarity, texture, sharpening, denoising, chromatic-aberration
   correction, lens correction, local contrast, gamut compression, and output resize.
4. Strip development tags from the derivative and embed only the frozen linear ICC,
   provenance, and source hash. Hash the pixel payload and whole TIFF.
5. Zerene, Helicon, and strehl must receive the exact same TIFF bytes. A strehl TIFF
   adapter or a bit-for-bit hash identity at strehl’s internal pre-merge linear-frame
   boundary is a prerequisite. Until one exists, **competitive quality remains
   UNMEASURED**; feeding TIFFs only to the commercial tools is forbidden.

This deliberately separates the fair merge comparison from a native-RAW product run.
A native-RAW run is reported as a product diagnostic but cannot establish a
competitive detail, noise, clipping, or colour win unless its pre-merge samples pass
the same identity audit.

### 1.3 Output transfer and the tone sentinel

Each program must emit a native-size 16-bit linear TIFF. No output may be histogram
matched, auto-exposed, white-balanced, sharpened, denoised, resized, or tone-mapped
after stacking. Numerical metrics run in linear light before any display conversion.
Visual crops, when supplied, use one external colour transform, are cut 1:1 at
`<=400 px`, and are never resampled, per `AGENTS.md` rule 48 (lines 801–835).

The common input set includes eight identical copies of a 33-step neutral linear ramp
from `0.02` to `0.98`. For every channel, fit `y = ax + b` on steps 2–32. An arm is
invalid unless all of these hold:

- `0.995 <= a <= 1.005`;
- `|b| <= 0.001`;
- maximum absolute affine residual `<= 0.002`;
- RMS affine residual `<= 0.0005`;
- no interior step clips and ordering is strictly monotone.

The input audit additionally fails if any file or sidecar contains a non-zero
`Contrast2012`, `Sharpness`, `Clarity`, `Texture`, `LuminanceSmoothing`, tone-curve,
or equivalent development instruction. Because all programs consume one hashed
linear TIFF and all metrics run before a common external display transfer, the
`Contrast2012=+100` asymmetry that killed the previous comparison cannot occur in one
arm. It would change the shared input hash or fail the ramp.

### 1.4 Comparator settings

Use the newest generally available stable release of each product on the
`RUN-MANIFEST.json` freeze date. Freeze its version, installer/binary hash, licence,
and screenshots/export of every relevant setting before the first scored output; do
not choose among old/new releases after viewing results.

- **Zerene Stacker:** licensed current shipping build; automatic PMax and automatic
  DMap; no retouching; output contrast/brightness/sharpening at neutral/off.
- **Helicon Focus:** licensed current shipping build; Methods A, B, and C at factory
  defaults; no retouching; built-in post-sharpening, denoising, and auto-adjustment
  neutral/off.
- **strehl:** the shipping default at the scored commit; no per-subject environment
  overrides or experimental quality flags.

If a named control is unavailable in a particular version, record the exact UI and
exclude that mode. If either product cannot produce a linear output that passes §1.3,
the named-comparator requirement is unmet and the SOTA verdict remains `UNMEASURED`.
No expert hand retouch is admitted because it has no reproducible operating point.

For higher-is-better metrics, the comparator envelope is the maximum qualifying value
over all registered modes. For lower-is-better metrics it is the minimum. For speed it
is the fastest mode that passes the complete quality scorecard. This is intentionally
conservative toward strehl.

### 1.5 Geometry and exclusions

- Outputs must retain native scale. Resize is a hard invalidation.
- Crops are fixed from the common-input overlap before outputs exist. Retained field of
  view must be `>=99.0%` of that overlap.
- Translation may be removed analytically as a Fourier phase ramp. Frequency metrics
  may not resample an output.
- A similarity fit from input-derived landmarks must have scale disagreement
  `<=0.10%`, rotation disagreement `<=0.02 deg`, and non-translation residual
  `<=0.10 output px RMS`; otherwise that capture/arm is `UNMEASURED`.
- At least `80%` of pre-registered sites and at least the metric-specific minimum must
  survive identically in every arm. Differential site attrition over `2 percentage
  points` invalidates the comparison.

### 1.6 Commissioning before scoring

`AGENTS.md` requires a flat control beside every sharpness metric (rule 9, lines
185–190), the fooling direction beside every metric (rule 18, lines 257–266), an input
that can make each gate fail (rule 20, lines 267–284), and an independently obtained
term rather than subject/object identity (rule 35, lines 457–462). Accordingly:

1. Each checker must fail its metric-specific positive plant at the registered
   sensitivity and pass an untuned null.
2. The checker may consume common inputs, external calibration data, and final
   outputs. It may not import strehl’s focus map, weights, contributor mask, noise
   constants, depth estimate, or certificate to construct its own answer.
3. The “all red” omnibus plant applies pre-sensor blur, added shot/read noise, a 6%
   edge halo and veil, a 32-px selector patchwork, a three-frame focus gap, 1%
   highlight clipping, a channel hue rotation, 6-sigma out-of-hull samples, an
   overconfident certificate, permuted depth, a 60-second timed delay, and a 7-GiB
   allocation. Every applicable gate must fail.
4. A failed commissioning result voids the metric. It may not be repaired against the
   scored captures under v1.6.

## 2. Frozen capture set

### 2.1 Read-only inventory

The trees were enumerated with `Get-ChildItem -Force` on 2026-09-02 and were never
written:

- `D:\personal\macro`: `10,067` files, `9,852` ARWs, `429.352 GiB`;
- `D:\personal\macro\requests`: `3,261` files, `3,251` ARWs, `115.321 GiB`.

The prompt’s approximate requests count of 3,361 is not the current filesystem count.
All input derivatives, manifests, and outputs must be written beneath
`experiments/SCORECARD/`, never to either capture tree.

### 2.2 Scored and control captures

**Literal rule:** only a row whose evidence class begins `HOLDOUT` is holdout. No
other wording implies holdout status.

| Capture | Verified ARWs / metadata | Evidence class | Registered role |
| --- | ---: | --- | --- |
| `requests\30-calibration-grid\calibration-grid-1-sw1-cpl` | 91; ISO 100, 1 s, f/5.6 | **BURNED — DEVELOPMENT ONLY, NOT HOLDOUT** | Former dense checker reference. Same subject/session as leaked sw4; cannot score M1/M5/M9. |
| `requests\30-calibration-grid\calibration-grid-1-sw4-cpl` | 55; ISO 100, 1 s, f/5.6 | **BURNED — DEVELOPMENT ONLY, NOT HOLDOUT** | W1 swept `k` and observed outcomes; quarantine `0c503d84`. |
| `requests\30-calibration-grid\calibration-grid-2-sw4-cpl` | 46; ISO 100, 1 s, f/5.6 | **BURNED — DEVELOPMENT ONLY, NOT HOLDOUT** | Former scored repeat B; collateral same-subject/session burn. |
| `requests\30-calibration-grid\calibration-grid-1-sw10-cpl` | 23; ISO 100, 1 s, f/5.6 | **BURNED — DEVELOPMENT ONLY, NOT HOLDOUT** | Former sparse-step arm A; collateral same-subject/session burn. |
| `requests\30-calibration-grid\calibration-grid-2-sw10-cpl` | 27; ISO 100, 1 s, f/5.6 | **BURNED — DEVELOPMENT ONLY, NOT HOLDOUT** | Former sparse-step arm B; collateral same-subject/session burn. |
| `requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl\flat-et6s-sw4-cpl` | 65; ISO 100, 6 s, f/5.6, 200 mm; IBIS on | **DEVELOPMENT — NOT HOLDOUT** | Flat-path identity and `cover=scale` resampling diagnostic; longest-exposure SNR rung. |
| `requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl\flat-et2.5s-sw4-cpl` | 61; ISO 100, 2.5 s, f/5.6, 200 mm; IBIS on | **DEVELOPMENT — NOT HOLDOUT** | Flat-path identity and `cover=scale` diagnostic; middle SNR rung. |
| `requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl\flat-et1s-sw4-cpl` | 60; ISO 100, 1 s, f/5.6, 200 mm; IBIS on | **DEVELOPMENT — NOT HOLDOUT** | Flat-path identity and `cover=scale` diagnostic; exposure-matched control for the tilted block. |
| `requests\misc-diagnostic\high-res-calibration-slide-cpl\tilted-sw4-cpl` | 182; ISO 100, 1 s, f/5.6, 200 mm; IBIS on | **DEVELOPMENT — NOT HOLDOUT** | Dense controlled-tilt M5/M10 commissioning and geometry diagnostic. Never an FRC repeat or checker reference for a score. |
| `requests\misc-diagnostic\high-res-calibration-slide-cpl\tilted-sw10-cpl` | 92; ISO 100, 1 s, f/5.6, 200 mm; IBIS on | **DEVELOPMENT — NOT HOLDOUT** | Sparse-step controlled-tilt M5 commissioning. Distinct geometry, not a repeat of the all-axis stack and never an FRC arm. |
| `requests\misc-diagnostic\high-res-calibration-slide-cpl\very-tilted-all-axis-sw10-cpl` | 197; ISO 100, 1 s, f/5.6, 200 mm; IBIS on | **DEVELOPMENT — NOT HOLDOUT** | Sparse-step all-axis M5/M10 commissioning. Distinct geometry, not a repeat of tilted-sw10 and never an FRC arm. |
| `requests\7-aperture-pairs\fabric-weave-f5.6-sw5-cpl` | 210; ISO 100, 1.3 s | **HOLDOUT — QUALITY** | Natural oriented high-frequency and colour-seam stress. |
| `requests\7-aperture-pairs\fabric-weave-f8-sw5-cpl` | 150; ISO 100, 1.3 s | **HOLDOUT — QUALITY** | Aperture robustness. |
| `requests\7-aperture-pairs\fabric-weave-f11-sw5-cpl` | 109; ISO 100, 1.3 s | **HOLDOUT — QUALITY** | Aperture robustness / diffraction control. |
| `requests\8-tilted-planar\ruler-incline-ang10.26deg-inches-f5.6-sw7-cpl` | 120 | **HOLDOUT — QUALITY** | M5 depth coverage and conditional M10 physical-depth slope. |
| `requests\8-tilted-planar\ruler-incline-ang10.26deg-inches-f8-sw7-cpl` | 85 | **HOLDOUT — QUALITY** | Cross-aperture depth consistency. |
| `requests\8-tilted-planar\ruler-incline-ang10.26deg-inches-f11-sw7-cpl` | 65 | **HOLDOUT — QUALITY** | Cross-aperture depth consistency. |
| `requests\12-bee-iso-var-no-bracket-32-repeat-diff-light` | 576 total | **HOLDOUT — QUALITY** | Independent repeated exposures for M1/M2/M9. Bright ISO 100 is `DSC00328.ARW`–`DSC00359.ARW`; second-light ISO 100 is `DSC00584.ARW`–`DSC00615.ARW`, 32 each, 1.6 s, f/5.6. |
| `requests\10-paper-iso-var` | 110 total | **CONTROL — NOT HOLDOUT** | Flat/noise transfer control. ISO 100, 1/8 s is `DSC00245.ARW`–`DSC00249.ARW`. The actual EXIF census includes ISO 250 although the README list omits it. |
| `requests\6-11-extended-dark-frames` | 506 | **CONTROL — NOT HOLDOUT** | Independent temporal-noise and fixed-pattern floor; never an image-quality subject. |
| `requests\19-razor-edge\horizontal-flat\razor-edge-horizontal-flat-sw4-f5.6-cpl` | 67 | **CONTROL — NOT HOLDOUT** | Isolated bright-on-dark boundary control for M3 only. The razor is forbidden for M1. |
| `duck-tape-side-layers-cpl` | 197 | **HOLDOUT — QUALITY** | Thin fibres crossing textured ground; occlusion/ghost stress. |
| `chia-seeds-cpl` | 130 | **HOLDOUT — QUALITY** | Deep-crevice broad-veil specimen. |
| `flower-bud-with-background-fern-cpl` | 299 | **HOLDOUT — QUALITY** | Dense multi-layer occlusion and coverage stress. |
| `coffee-bubbles` | 19 | **DEVELOPMENT — NOT HOLDOUT** | High-ISO patchwork/mottle commissioning subject. |
| `medication-pill-cpl` | 146 | **HOLDOUT — QUALITY** | Low-contrast powder/focus-election stress. |
| `foam` | 100 | **HOLDOUT — QUALITY** | Specular, coloured, near-rail highlight stress. |
| `requests\misc-diagnostic\flat-round-3V-battery-cpl\flat-round-3V-battery-iso100-sw4-cpl` | 30 | **HOLDOUT — QUALITY** | Reflective neutral metal, fine scratches, clipping/colour-seam stress. |
| `maldon-sea-salt-cpl` | 255 | **HOLDOUT — QUALITY** | Translucent facets and recoverable highlights. |
| `highly-angled-ruler-mm-cpl` | 299 | **HOLDOUT — QUALITY** | Neutral edges and lateral-colour stress. |
| `bee-1-cpl` | 299, `DSC00001.ARW`–`DSC00299.ARW` | **HOLDOUT — PERFORMANCE** | 33 MP wall-clock and memory master. First 100 frames are the live-latency arm. |
| `coffee-bean` | 105 ARWs, `DSC00016.ARW`–`DSC00120.ARW` | **FIXED HISTORICAL BENCHMARK — NOT HOLDOUT** | Comparator continuity and medium-N speed; never used to recover the retracted detail claim. |
| `113MSDCF` | 63 ARWs, `DSC00001.ARW`–`DSC00063.ARW` | **HISTORICAL CONTROL — NOT HOLDOUT** | `Contrast2012` regression sentinel only; not a primary acuity subject. |

The razor’s measured `1.23 green px` locus raggedness makes it
resolution-ineligible; using it for M1 would repeat a known failure. It remains useful
for broad boundary profiles, where the checker does not self-register the edge to
sharpen it.

### 2.3 Holdout units and burn log

The holdout unit is **subject plus uninterrupted capture session**, not a directory or
step width. Rendering, tuning, or reading an outcome on any member burns every member
of that unit. A `HOLDOUT` capture may be decoded to build the frozen common input and
input-only site manifest, but no output, metric, visual verdict, parameter sweep, or
code-acceptance decision may be seen before the registered score run.

All five `30-calibration-grid` stacks are one unit. Its README says subject, light,
aperture, ISO, and composition were constant and only step width changed. EXIF places
the five stacks contiguously on 2026-09-01 from 20:57:42 through 21:09:06. There is no
other calibration-grid capture group in `D:\personal\macro`.

W1 swept `k=0.00:0.05:8.00` (161 values) on
`calibration-grid-1-sw4-cpl` and read real-stack sentinel outcomes before halt:
detail `1.063350`, flat power `1.329831`. Commit `0c503d84` quarantines that pilot.
Therefore sw1, both sw4 stacks, and both sw10 stacks are all burned. The later W1
targets `flat-on-ruler-cpl`, `coffee-bubbles`, and `113MSDCF` do not extend the burn:
none is labelled holdout here.

The fresh high-resolution slide is conservatively one **657-frame unit** spanning
20:13:04–21:01:58. The 16 min 45 s gap is a target reconfiguration inside the same
evening's capture session, not independent evidence: the physical slide, camera,
lens/teleconverter, ISO, and aperture remain the same. Exposure, step width,
directory, and flat/tilted geometry do not split a subject into six holdouts.
Touching any member would therefore burn all six.

All six carry `ImageStabilization: On`. Registration-based M5 development is allowed,
but repeat-pair FRC/M9 truth use is forbidden. The entire unit is deliberately spent
on development: constant depth makes the flat block the cleaner identity/resampling
test for the known `cover=scale` geometry defect, its exposure changes make an SNR
ladder rather than matched repeats, and reserving the tilted views while tuning on the
same slide would create target leakage.

**Axis consequence:** these captures advance M5 coverage-instrument development and
M10 planarity/order commissioning, but they close no holdout gap. M1 keeps only its
same-focus bee sentinel; M5 retains ruler/natural holdouts but still lacks its
replacement controlled-slide holdout; M9 retains bee repeats but lacks independent
depth-stack truth.

**Even after an M1 replacement exists, M1, M5, and M9 cannot pass v1.6** until a
fresh untouched subject/session supplies,
at identical subject geometry, exposure, ISO, aperture, and focal length with
**IBIS off**:

1. one dense checker-only reference pass;
2. two independent sw4 scored passes; and
3. two independent sw10 sparse-step passes.

A single repeated pair at only one step width does not close both registered arms.

### 2.4 Missing or insufficient truth captures

No enumerated capture is a traceable colour target spanning the focus sweep. `foam`,
fabric, metal, and neutral paper can reveal seams or casts but cannot supply true
CIELAB values. M7 is therefore registered now but cannot be scored until a tilted
ColorChecker Classic or Digital SG, grey card, illuminant measurement, and darks are
captured. Natural-object agreement is not colour fidelity.

The tilted ruler is sufficient for M5 coverage, but its README records the angle only
as “approximately 10.26 deg.” Unless an independent record bounds that angle tightly
enough for M10’s 2.5% truth-uncertainty gate, the physical-scale part of M10 also
requires a new metrology capture. Image-derived focus may not be used to certify the
angle it is being tested against.

The high-resolution slide currently has no committed target-pitch certificate or
external flat/tilted pose measurement. Its development unit may commission M10
planarity and ordering, but it cannot contribute to M10's physical-depth bars. A
future holdout requires those input-only truths to be frozen before any output is
viewed.

## 3. Scorecard at a glance

| ID | Primary metric | Success bar |
| --- | --- | --- |
| M1 | Sharpening-safe resolved information | **NO ADMISSIBLE BAR — WITHDRAWN.** `f_licensed` is blind; native `S_25` fails sharpening and tone, while tone-hardened derivatives reverse the optical controls. |
| M2 | Noise efficiency at matched information | Cross-fit efficiency `<=1.10`; 95% upper bound of strehl / quietest qualifying comparator `<=0.950`. |
| M3 | Occlusion halo and broad veil | Median excess `<=1%` edge step, p99 `<=5%`; edges above 5% `<=1%` with Wilson upper bound `<=2%`; local source coherence `>=0.90`; no worse than best comparator. |
| M4 | Non-edge artifact rate | Median flat-patchwork ratio `<=1.00`; sites above `1.25` or ghost ratio above `0.10`: `<=1%`, Wilson upper bound `<=2%`; no worse than best comparator. |
| M5 | Depth-of-field coverage / stack failure | `>=99%` of eligible tiles pass `rho_best>=0.90` and focus margin `>=0.05`; Wilson lower bound `>=98%`; longest failed run `<=1%` of sweep. |
| M6 | Recoverable highlight/shadow retention | Recoverable high-rail and low-rail clipping each `<=0.10%`; highlight-detail retention `>=0.90`; no worse than best comparator. |
| M7 | Colour fidelity | Median DeltaE00 `<=1.0`, p95 `<=2.0`, maximum `<=3.0`, boundary-seam p99 `<=1.0`; ICC/300-DPI conformance `100%`; no worse than best comparator. |
| M8 | Invented values / source-hull certificate | Per-frame resampler-hull violations and final-output source-hull violations: each exactly `0.0000%`. |
| M9 | Acuity / `n_eff` certificate calibration | False-certification Wilson upper bound `<=1%`; true-band coverage `>=90%`; nominal 95% interval coverage `93%`–`97%`; variance ratio `0.90`–`1.10`. |
| M10 | Physical depth product | Valid target pixels `>=99%`; rank correlation `>=0.99`; median error `<=0.5` focus step, p95 `<=1.0` step; physical slope error `<=5%`. |
| M11 | Wall-clock throughput | Warm common-input throughput `>=2.00x` fastest quality-qualified comparator; candidate/default baseline ratio `<=2.00`; native-RAW CPU at 16 workers `<=0.15 s/frame`; hybrid `<=0.06 s/frame`; cold `<=warm+20 s`; 100-frame live master `<=10 s` after last shutter. |
| M12 | Memory, determinism, and scaling invariance | Warm peak process-tree memory `<=6 GiB`; 299/33-frame peak ratio `<=1.10`; every fixed-worker repeat is byte-identical and the outputs at 1/2/4/8/16 workers are mutually byte-identical while 16 workers passes M11; N-mod-4 per-frame spread `<=2%`. |

M8, the M11 comparator/CPU/hybrid/cold/live targets, the M12 6-GiB bar, and byte
invariance come directly from the proposal
(`2026-08-sota-path.md` lines 1582–1584 and 1957–1985). The remaining numerical
completions — including freezing D5's “roughly 2x” as `<=2.00` — are
**SCORECARD ADDITIONS** because the proposal is silent, approximate, or contains
`[bar]`.

### 3.1 Measurement readiness as of v1.6

This table separates scientific blockers from the baseline's single pre-metric
refusal. Codes are the owner's requested categories: **(a)** missing admissible
detail instrument, **(b)** unresolved native-scale/`cover=scale` geometry,
**(c)** missing or under-powered capture, **(d)** unavailable common-input
Zerene/Helicon output, and **(e)** scientifically measurable now. An **(e)** does not
mean a result has been run.

| Axis | Class | What can and cannot be measured now |
|---|---|---|
| M1 | **(a)(b)(c)(d)** | No active detail statistic or bar exists; scored matched repeats and comparator arms are also absent. |
| M2 | **(a)(b)(d)** | Residual noise can be computed diagnostically, but the registered matched-information verdict cannot. |
| M3 | **(a)(b)(d)** | Artifact counts without a licensed detail/matched-presentation arm cannot support the competitive claim. |
| M4 | **(a)(b)(d)** | Flatness is computable diagnostically, but its detail-preserving comparator verdict is blocked. |
| M5 | **(a)(b)(c)(d)** | No scored dense/sparse repeat unit exists, and failure coverage needs a licensed detail test. |
| M6 | **(a)(b)(c)(d)** | The rail census is executable, but the registered capture set has fewer than 10,000 recoverable samples and the full axis includes detail retention and comparators. |
| M7 | **(b)(c)(d)** | No traceable colour target exists. |
| M8 | **(e)** | The v1.4 source-hull invariant needs neither detail nor a comparator and may use the development-only flat slide. Its checker still must be commissioned before a result is admitted. |
| M9 | **(a)(b)(c)** | Repeat calibration captures are absent and the shipping product emits no admissible acuity/variance certificate. |
| M10 | **(b)(c)** | No scored geometric-truth capture or compatible depth product exists. The tilted slide is development-only. |
| M11 | **(a)(b)(d)** | A quiet host is additionally required; native-decode timing alone is a diagnostic, not the registered competitive verdict. |
| M12 | **(e), scheduled; formal value UNMEASURED** | Hashes and process-tree RSS need no detail, comparator or holdout. Existing out-of-protocol evidence diagnoses fixed-worker determinism as holding and cross-worker scaling invariance as failing, but the registered N/worker matrix still requires the reserved quiet host. |

Thus M8 is the only complete quality axis ready now. M12 is scientifically
unblocked, but its complete registered run is deliberately deferred to a quiet host.
M6's clipping preflight and several other submetrics may be run as diagnostics; they
are not complete axis verdicts.

## 4. Metric cards

### M1 — WITHDRAWN: no admissible detail instrument

**What it must measure and why.** A focus stacker must preserve independently
repeatable scene information across the depth sweep, not merely raise edge contrast.
Raw band power, MTF50, acutance, SFR and other presentation statistics can all rise
after an information-free sharpening pass.

**Why the v1.3 M1 instrument is withdrawn.** Independent commissioning established
both failure modes that this pre-registration was intended to expose:

- `f_licensed` remained pinned at `0.15 cyc/px` for the base, physical blur, genuine
  improvement and unsharp-mask arms. It is sharpening-invariant only because it is
  blind.
- The earlier 24-seed native `S_25` run read USM/base `0.995819x`
  (`-0.418%`) and therefore appeared to pass the frozen 1% commissioning bar.
  The identical arms on the expanded 64-site control read `1.028294x`
  (`+2.829%`), **RED against the unchanged 1% bar**. The bar did not move; the
  sample grew. The flattering 24-seed result was underpowered and is superseded
  (`docs/research/M-PHASE0-SLANTEDGE.md` lines 269 and 276–278).
- Native `S_25` also moved `4.8400x` under gamma-3 tone and `18818.9045x` under
  a logistic tone curve. Its noise range was `0.004972x`–`10.381863x`, and its
  0.5/1/5/12-degree response was `1.42205/1.18548/1/0.65802`. Derivatives that
  hardened tone reversed the optical controls: blur `1.268326x` and genuine
  improvement `0.923468x` (ibid., lines 269–274).

Accordingly, **the `S_25` requirement is withdrawn plainly, not weakened**, and the
old `f_licensed`/`S_25` formulae are not claim-bearing scorecard outputs. Three
independent slanted-edge implementations are also presentation diagnostics only:
they report roughly a 9.9% “resolution” gain after post-render unsharp masking.

**Current sharpening-safe inventory.** No admissible detail statistic in this
repository is sharpening-safe: no statistic that still responds correctly to physical
blur and genuine improvement survives sharpening. Q25 rewards the same
information-free USM by `5.560744x`; all three slanted-edge implementations report
roughly 9.9% improvement; and native `S_25` now reads `1.028294x`, outside its
unchanged 1% bar. Hardened `S_25` derivatives that suppress USM are not
counterexamples because they cease to be resolution statistics: blur scores sharper
and genuine improvement scores worse.
This complete candidate sweep requires a future instrument to have a structural
reason sharpening cannot improve it; a small empirical battery alone is not evidence.

**Reusable positive from the failed lane.** An external 33-step PCHIP linearisation
moved affine, gamma, and logistic tone arms by at most `0.0141%` without disturbing
the USM result. Tone invariance therefore does not require an ordinal statistic.
Future candidates may reuse this independent tone witness, but it does not excuse
their own sharpening, optical-direction, noise, angle, and null controls
(ibid., lines 286–289).

**Effect on M1 replacement.** None of M1's status, missing captures, or absence of a
numeric bar changes. The superseding result strengthens the admission requirement:
a replacement needs structural sharpening protection plus the full commissioned
battery; it does not resurrect or select a statistic.

**Input needed by a future replacement.** The capture deficiency remains:

- one dense checker-only reference;
- two independent sw4 passes at identical geometry and exposure, IBIS off;
- two independent sw10 passes at identical geometry and exposure, IBIS off;
- matched dark/flat captures and a non-periodic independent-reference sentinel.

The burned grid and the development-only high-resolution slide may commission a new
instrument but may never provide its scored value.

**Exact computation.** None is admitted in v1.6. A replacement must be
pre-registered before its fresh holdout is rendered, must use no frequency above
`0.25 cyc/native px`, and must be implemented and audited independently of the
pipeline producing the render.

**Success.** There is deliberately no active numeric success bar. M1 remains
**UNMEASURED**, and no detail, matched-information, quality-qualified comparator or
SOTA claim is licensed until a replacement statistic and numeric bar survive
commissioning.

**Known defeat.** Sharpening can fake edge/detail transfer; monotone tone can fake
spectral ratios; averaging can improve noise by destroying detail; shared fixed
pattern or deterministic hallucination can make repeat renders agree; a periodic
checker can carry its own answer.

**Required controls for any replacement.** It must distinguish untuned null,
pre-sensor blur and genuine optical improvement in the correct directions; refuse
post-render unsharp-mask, gamma, logistic-tone, noise and edge-angle challenges; fail
a common-mode A/B plant absent from the independent reference; and report a flat ROI
as no detail evidence. Its sharpening battery must use at least 64 independent sites
and retain its frozen bar as sample size grows; a structural invariance argument is
still required because empirical non-rejection is not a guarantee. Those challenge
outcomes and numerical admission bars must be frozen in a later revision before score
data are read.

### M2 — noise efficiency at matched information

**What it measures and why.** Focus stacking should average independent sensor noise
without trading it for blur, selected grain, or low-frequency patchwork.

**Input.** The two 32-frame ISO-100 bee repeat blocks, the ISO-100 paper block, and
the dark/FPN captures. For each 32-frame block, frames 1–16 are stacked and frames
17–32 form an external mean reference, then the roles reverse. Flat ROIs are selected
on the other illumination block and frozen before output. At least 32 non-overlapping
ROIs total and 16 per light must qualify.

**Exact computation.**

1. Candidate 128x128 ROIs must be in the lowest quartile of input-only
   `0.02–0.08 cyc/px` structure and contain no clipped samples.
2. For each cross-fit output `O` and held-out 16-frame mean `R`, compute the
   `0.15–0.35 cyc/px` residual and
   `sigma_res = 1.4826 * MAD(BP(O-R))`.
3. Estimate per-frame temporal `sigma_1` from pairwise frame differences, never from
   spatial texture. The ideal difference of two independent 16-frame means is
   `sigma_ideal = sigma_1 * sqrt(2/16)`.
4. `eta = sigma_res / sigma_ideal`. The comparator ratio uses paired ROIs and only
   modes within `98%` of a future replacement-M1 information envelope. No comparator
   mode qualifies in v1.6.

The `0.15–0.35 cyc/px` quantity here is a noise residual, not a detail or acuity
reading; it does not license any spatial-resolution claim above `0.25 cyc/px`.

**Success.** The proposal says “strictly lower noise” but supplies no practical
margin (`2026-08-sota-path.md` lines 192–195). **SCORECARD ADDITION:**
`eta <=1.10` and `UCB95(sigma_strehl / min(sigma_comparator)) <=0.950`.

**Known defeat.** Blur, denoising, black crush, lower gain, or selecting an unusually
flat ROI can lower the statistic without improving the stack.

**Control.** Input-only cross-light ROI selection prevents output cherry-picking;
§1.3 fixes gain and tone; a future replacement M1 must remain green. A
Gaussian-output-blur plant must improve raw noise while failing the edge-width/gain
guard. Added independent noise of `0.25 sigma_1` must increase `eta` by at least
`0.20`; the untouched temporal mean must fall in `0.90 <= eta <=1.10`. Until M1 is
replaced, `eta` is diagnostic only.

### M3 — occlusion halo and broad veil

**What it measures and why.** Focus stacking combines different depth layers at one
boundary. It can create overshoot/undershoot rims, ghost edges, or a broad pedestal
from the out-of-focus foreground. The proposal explicitly requires a bounded veil but
leaves `[bar]` blank (`2026-08-sota-path.md` lines 192–197).

**Input.** Duck-tape fibres, chia crevices, flower/fern boundaries, and the horizontal
razor as an isolated boundary control. At least 500 pre-registered edges overall and
50 per capture must qualify. Broad-veil sites require 400 px of input-verified
background reach; otherwise that capture is `UNMEASURED` for veil.

**Exact computation.**

1. Locate edges and normals from common inputs only. Never align each profile to its
   own measured edge peak.
2. For the narrow halo arm, use median source plateaus at
   `s in [-64,-48]` and `s in [48,64]`. For the broad-veil arm, use
   `[-400,-320]` and `[320,400]`. Orient the profile dark-to-bright and normalize by
   the independently selected source-plateau difference to a unit step. A plateau
   step below `10*sigma_temporal` is ineligible.
3. At each normal coordinate `s`, externally warp every source profile and form its
   sample interval `[L(s), U(s)]`.
4. `h_e = max_{2<=|s|<=32} max(O(s)-U(s), L(s)-O(s), 0)`.
5. Select the far-side reference frame using the opposite-side low band. For
   `16<=|s|<=200`, `v_e = mean(|O(s)-R_far(s)|)`.
6. Record the 10–90% edge-width ratio to the independently selected sharp source.
7. In the surrounding 128x128 patch, compute M5's normalized complex coherence
   `rho_edge` to that same sharp source over `0.15–0.25 cyc/px`.
8. An edge is affected if `max(h_e,v_e)>0.05`.

**Success.** **SCORECARD ADDITION:** median `h_e` and `v_e <=0.01`; p99 of each
`<=0.05`; affected-edge point rate `<=1%` and Wilson UCB95 `<=2%`; median edge-width
ratio in `[0.95,1.05]`; median `rho_edge>=0.90`; strehl’s paired p99 is no greater
than the best comparator’s.

**Known defeat.** Blur hides a rim; cropping hides the far shoulder; per-edge
normalisation can erase a veil; an optical halo already present in every source can be
mislabelled as a stacker artifact.

**Control.** The score is excess over the source interval/reference, not absolute
optical halo. A future replacement M1, `rho_edge`, and the width guard catch blur.
Crops and plateaus are frozen. A 6% planted rim and 6% 200-px veil must be detected on
at least 95% of sites; untouched raw frames must have false-positive rate `<=1%`.
Any checker that convicts the raw null is not admitted.

### M4 — non-edge artifact rate

**What it measures and why.** Spatially varying frame election can manufacture
20–60 px patchwork on flat ground, while bad registration can create double contours.
Neither is adequately represented by a single “halo” number.

**Input.** Input-flat sites from medication-pill, bee background, foam, and
coffee-bubbles for commissioning; holdout structured edge sites from fabric, duck
tape, and flower/fern. The burned grid may commission the detector but cannot score.
At least 500 sites overall and 50 per scored capture must qualify.

**Exact computation.**

1. A flat tile qualifies only if every input frame’s `1/60–1/20 cyc/px` power is below
   the independently measured temporal-noise 99th percentile.
2. Construct 1,000 spatially constant convex input blends with frozen
   Dirichlet(1) weights, plus every single frame and the uniform mean. Let `B99` be the
   99th percentile of their band RMS.
3. `Q_flat = RMS(BP_20-60(O)) / max(B99, noise_floor)`.
4. On an edge, let `g_ghost` be the largest secondary same-sign normal-gradient peak
   2–20 px from the main peak divided by the main peak.
5. A site fails if `Q_flat>1.25`, `g_ghost>0.10`, or it fails M3’s 5% boundary limit.

**Success.** **SCORECARD ADDITION:** median `Q_flat<=1.00`; failed-site point rate
`<=1%`, Wilson UCB95 `<=2%`; strehl’s rate is no greater than the best comparator’s.

**Known defeat.** Blur or aggressive denoising suppresses patchwork and secondary
edges. A checker built from strehl’s own weight map would simply restate the
generator.

**Control.** A future replacement M1 must catch blur. The checker sees inputs and
final pixels, never weights. A planted 32-px spatial selector must make at least 95%
of planted flat tiles exceed `Q=1.25`; a fixed-weight mean must produce no more than
1% failures. Shifting the output by one tile must destroy edge correspondence without
changing its spatial spectrum, demonstrating that the edge arm is not merely a
texture detector.

### M5 — depth-of-field coverage and stack failures

**What it measures and why.** A stack may be sharp where it succeeds yet leave focus
holes, choose the wrong depth, lose a thin layer, or crop away difficult regions.

**Input.** The three new tilted-slide stacks are development-only commissioning
captures; they do not replace the burned grid's holdout arm. Remaining holdouts are
all three tilted-ruler apertures, flower/fern, duck tape, and medication-pill. The
burned grid is also development-only. Sites are 128x128 input-fixed tiles. At least
500 eligible tiles overall and 50 per capture must qualify. M5 remains
`UNMEASURED` until a fresh controlled-slide holdout replaces the burned arm.

**Exact computation.**

1. Determine each tile’s best source frame from the input-only `0.05–0.12 cyc/px`
   band or, on the ruler/grid, from physical target contrast. Evaluate
   `0.15–0.25 cyc/px`.
   A tile is eligible only when its best/far source-signal ratio is `>=2.0` with
   bootstrap lower bound `>=1.5`.
2. For output `O_k` and each source-frame spectrum `I_j,k`, compute
   `rho_j = |sum(O_k conj(I_j,k))| /
   sqrt(sum(|O_k|^2) sum(|I_j,k|^2))` in the evaluation band. Let `rho_best` use the
   independently elected frame. Let `rho_far` be the maximum over frames at least
   three focus steps away.
3. A tile passes when `rho_best>=0.90` and
   `rho_best-rho_far>=0.05`.
4. Coverage is passing eligible tiles divided by all input-eligible tiles. A connected
   run is measured along the known focus-sweep direction.

**Success.** **SCORECARD ADDITION:** coverage point estimate `>=99%`, Wilson LCB95
`>=98%`, longest failed run `<=1%` of the sweep dimension, retained FOV `>=99%`, and
strehl coverage no lower than the best comparator.

**Known defeat.** A single sharp plane can look excellent in selected tiles; cropping
can remove failures; a common blur can preserve correlation while making the
presentation soft; an eligibility map derived from the output can omit the hard
sites.

**Control.** The denominator and best frame come only from common inputs and are
frozen. Coherence is gain-invariant. A future replacement M1 must catch softening.
Removing the smallest contiguous run of at least three frames that covers at least
10% of the eligible target depth must reduce measured coverage by at least 5
percentage points and place the longest failure in that slab. A complete-stack null
may move coverage by at most 1 point. M1's future replacement remains the separate
resolution gate.

### M6 — recoverable highlight and shadow retention

**What it measures and why.** A focus stacker sees different blur discs and sometimes
different valid exposures at each pixel. It should recover an unsaturated contributor
instead of clipping a highlight or crushing a shadow.

**Input.** Foam, Maldon salt, ISO-100 battery, highly angled ruler, and qualifying
bright sites from the grid/fabric captures. Each scored capture needs at least 20
non-overlapping highlight/shadow tiles and 10,000 recoverable pixels.

**Exact computation.**

1. A high-rail pixel is recoverable when at least one common input is `>=0.98` and at
   least one aligned input lies in `[0.20,0.95]`. A low-rail pixel is recoverable when
   at least one input is `<=0.02` and another lies in `[0.05,0.80]`.
2. `clip_high` is the fraction of recoverable high pixels with output
   `>=65534/65535`; `clip_low` is the mirrored fraction `<=1/65535`.
3. On recoverable-highlight tiles, compute M5’s `rho_best` against the independently
   selected unsaturated source; report the median as highlight-detail retention.

**Success.** **SCORECARD ADDITION:** `clip_high<=0.001`,
`clip_low<=0.001`, highlight-detail retention `>=0.90`, and none of the three values
is worse than the best comparator.

**Known defeat.** Darkening or compressing the output avoids clipping; excluding the
brightest pixels changes the denominator; smoothing hides clipped texture.

**Control.** Recoverability is input-defined. The tone ramp requires unit gain, while
mid-grey gain must remain within `0.5%` and the 99th-percentile linear luminance within
`1%` of the common reference. A plant clipping exactly 1% of recoverable pixels must
be recovered within `0.1 percentage point`; a darkened arm must fail §1.3.

### M7 — colour fidelity

**What it measures and why.** Frame-dependent white balance, per-channel focus
selection, clipping, and chromatic registration can make seams or move real colours
even when luminance detail is good. D7 requires colour/print polish but supplies no
colourimetric score or bar (`2026-08-sota-path.md` lines 1682–1689).

**Input.** A missing, required tilted ColorChecker capture under a measured illuminant,
with published patch values, grey card, darks, and enough focus travel to place patches
on different elected frames. At least 24 valid patches, including all neutral patches
and at least 12 chromatic patches, must survive. Fabric, foam, battery, and ruler
remain seam diagnostics only and cannot substitute for the target.

**Exact computation.**

1. Convert the common linear output through its frozen ICC to CIELAB D50.
2. Erode each target patch by 20%; use the median Lab value.
3. Compute CIEDE2000 to the traceable patch value. No per-output matrix, white-balance,
   exposure, or gamut fit is permitted.
4. Across input-defined focus boundaries, compute the p99 DeltaE00 discontinuity after
   subtracting the target’s true patch-to-patch difference.
5. Verify that every scored deliverable embeds the byte-identical frozen ICC and
   carries 300-DPI resolution tags.

**Success.** **SCORECARD ADDITION:** median DeltaE00 `<=1.0`, p95 `<=2.0`, maximum
`<=3.0`, boundary-seam p99 `<=1.0`, ICC/300-DPI conformance `100%`, and no summary is
worse than the best comparator.

**Known defeat.** Desaturation flatters neutral-only data; fitting a matrix to the
same patches makes the checker carry the answer; tone/gamut mapping can trade
luminance for chroma.

**Control.** All chromatic and neutral patches score; no output-specific fit is
allowed. A 10-degree hue rotation and a 5% desaturation must fail at least 90% of their
affected patches; an identity colour transform must pass. The absent target makes the
current honest state `UNMEASURED`, not “close enough on natural objects.”

### M8 — invented values / source-hull certificate

**What it measures and why.** A merge or restoration stage can ring beyond any
observed linear sample. The proposal explicitly requires a per-file hull census of
`0.0000%` or coordinates for every exception
(`2026-08-sota-path.md` lines 1579–1584).

**Input.** Every scored quality capture. Before a scored run, commission the
instrument on the development-only flat 1/2.5/6-second high-resolution-slide stacks.
This use consumes no holdout. The active placement, including the cover transform, and
the linear decoded source planes are evidence inputs.

**Exact computation.**

M8 has two mandatory censuses because a final broad hull can hide an interpolator
excursion that another frame happens to bracket. M8-R is a **SCORECARD ADDITION**;
M8-O is the proposal's per-file invariant.

1. **M8-R, per-frame resampler hull.** At the linear pre-merge and pre-clamp `f32`
   boundary, record the actual gathered value `r_k(x,y,c)` for every geometrically
   valid placed frame, sample and channel. The trace contains values and coordinates,
   never a producer-computed hull or pass flag.
2. Independently map each output sample centre through the frozen placement. For
   Catmull-Rom, read the exact 4x4 discrete source support used at that coordinate and
   define `lo_k=min(support_16)` and `hi_k=max(support_16)`. Boundary coordinate
   clamping must be reimplemented from the written resampler contract, not called from
   strehl.
3. Let
   `tau_R = 8*ULP_f32(max(1, abs(lo_k), abs(hi_k)))`. Count an M8-R violation when
   `r_k < lo_k-tau_R` or `r_k > hi_k+tau_R`. Sensor noise is already present in the
   16 observed support samples, so temporal `5*sigma` is not a legitimate tolerance.
   Here `ULP_f32(z)` is the distance from positive `f32` value `z` to its next
   representable value.
4. **M8-O, final-output hull.** At the same linear coordinate and channel, define
   `lo_O=min_k(lo_k)` and `hi_O=max_k(hi_k)` over every geometrically valid input
   frame, never strehl's elected contributor list. Compare the actual final linear
   output `O` to this interval. For a 16-bit serialized audit only, add exactly
   `0.5/65535` quantisation tolerance to the largest contributing `tau_R`; no tone,
   noise or scene-adaptive tolerance is allowed.
5. For both censuses report denominator, violation count and fraction, maximum signed
   excess, and every violating `(capture, frame, x, y, channel)` coordinate. Separately
   report the one-frame/reference-frame arm: under `crop`, an integer identity
   placement must be a source copy within `tau_R`.

**Success.** **PROPOSAL BAR (M8-O):** final-output violation fraction exactly
`0.0000%`. **SCORECARD ADDITION (M8-R):** resampler violation fraction exactly
`0.0000%`; the crop/reference identity arm also has zero violations. A missing
pre-clamp trace is `UNMEASURED`, not a pass.

**Current cover hypothesis.** The v1.3 definition was too weak: its all-frame hull and
`5*sigma` tolerance could pass Catmull-Rom overshoot if another frame bracketed the
excursion, merge/clamping removed it, or the noise tolerance absorbed it. The default
Catmull-Rom kernel has negative lobes and explicitly permits hard-edge overshoot, while
`cover=scale` resamples even the identity reference placement. Therefore scale-induced
overshoot is plausible but not yet measured. M8-R will catch it at the stage where it
is created; M8-O determines whether it survives to the deliverable. This is
sharpening-independent source support, not a resolution statistic.

**Known defeat.** Final clamping can erase M8-O evidence; a broad all-frame hull can
bracket a per-frame excursion; a producer-supplied contributor mask or hull can omit
the disproof; and destructive clipping can force a zero rate.

**Control.** The checker is a separate implementation that reads source planes,
placements and raw value traces and imports neither strehl's sampler nor its
contributor/hull code. A synthetic hard step at a frozen fractional phase must cause
at least one Catmull-Rom M8-R violation; copy and convex-bilinear nulls must produce
zero. Every sample deliberately planted at `hi+32*tau` or `lo-32*tau` must be found.
The crop/reference identity arm must produce zero. A future M1, M5 and M6 are the
opposed controls against buying an overall quality verdict through clamping; while M1
is absent, M8 may prove only this internal invariant, not SOTA.

### M9 — acuity and effective-sample certificate calibration

**What it measures and why.** The proposal’s differentiator is not merely a good
image, but a file that says where and at what frequency it is trustworthy. A
certificate generated and checked by the same noise/focus model is the repository’s
signature cancellation defect. D2 proposes a CRLB channel and an empirical channel
(`2026-08-sota-path.md` lines 1554–1573), but the proposed same-capture split channel
is no longer admissible.

**Input.** All six new slide stacks are development-only, and IBIS independently
disqualifies them as repeat-pair truth. M9 requires a new dense checker-only pass, two
matched sw4 passes, and two matched sw10 passes with IBIS off, plus the independent
bee repeat groups and dark/FPN calibration. The burned grid may commission but may
not score. Same-frame odd/even halves are forbidden. At least 500 independent
tile-band truth cells and 500 claimed-valid cells are required. Bee same-focus
repeats alone cannot close M9's depth-stack certificate claim.

**Exact computation.**

1. For each tile and 0.05-cyc/px band whose upper edge is `<=0.25 cyc/px`, truth is
   the future independently commissioned M1 condition. The withdrawn v1.3
   `D>=1 && FRC>=1/7` rule is not truth in v1.6.
2. A claimed band is the highest licensed band strehl’s output certificate marks
   valid. Bands above `0.25 cyc/px` must be labelled `UNLICENSED` and cannot improve
   the score.
3. False-certification rate is
   `count(claimed_valid && !truth_valid) / count(claimed_valid)`;
   coverage is
   `count(claimed_valid && truth_valid) / count(truth_valid)`.
4. For each reported `n_eff`/variance decile, compare predicted variance to empirical
   repeat variance and count whether nominal 95% intervals contain the held-out
   reference.

**Success.** **SCORECARD ADDITION:** false-certification Wilson UCB95 `<=1%`;
true-band coverage `>=90%`; nominal 95% coverage in `[93%,97%]`; empirical/predicted
variance ratio in `[0.90,1.10]` for at least 90% of deciles.

**Known defeat.** Reusing the same frames, fixed pattern, focus operator, or noise
constant in generator and checker can make every calibration plot close by
construction. A certificate can also pass by refusing almost every pixel.

**Control.** Truth uses independent repeated exposures, external FPN treatment, and
a future M1 independent reference, never strehl’s model channel. The coverage bar
prevents universal refusal. A certificate with every band valid must exceed the
false-certification bar; one with every band invalid must fail coverage. Multiplying
only the reported variance by 1.25 must move the variance ratio outside the pass
interval. With M1 absent, M9 has no empirical acuity truth and is `UNMEASURED`.

### M10 — physical depth product

**What it measures and why.** The proposal calls for depth in physical units, not an
unlabelled frame index (`2026-08-sota-path.md` lines 192–197). A focus stacker’s depth
map is useful only if its ordering, scale, and uncertainty survive an external
geometric truth.

**Input.** The three 10.26-degree tilted-ruler stacks, the flat battery null, and an
independently implemented non-planar synthetic two-layer target whose latent depths
are hidden from the estimator. The ruler’s 1/64-inch markings set lateral scale. The
fresh tilted-slide unit is development-only planarity/order commissioning and cannot
be promoted to score evidence after diagnostic use. At least 20 non-overlapping ruler
strips and 10,000 target pixels must qualify.

**Exact computation.**

1. Map ruler ticks to physical `x`; external truth is
   `z_true=x*tan(theta_ext)` after one fitted origin only. `theta_ext` must come from
   a measurement independent of image focus and be frozen with uncertainty small
   enough to contribute at most `2.5%` slope error. The README’s “approximately
   10.26 deg” is a candidate value, not by itself traceable truth. No slope is fitted
   from strehl’s depth output.
2. Convert predicted depth to the same units using the declared capture model.
3. Report valid-pixel fraction, Spearman rank correlation, median and p95 absolute
   error in both micrometres and measured focus-step equivalents, and fitted
   predicted/true slope ratio.
4. On the flat battery, report p95 depth range. On the synthetic two-layer target,
   report layer confusion and boundary bias separately.

**Success.** **SCORECARD ADDITION:** valid target pixels `>=99%`; rank correlation
`>=0.99`; median absolute error `<=0.5` focus step; p95 `<=1.0` step; ruler slope error
`<=5%`; flat-null p95 range `<=0.5` step; synthetic layer confusion `<=1%`.

**Known defeat.** A hard-coded plane passes a tilted ruler; a checker using the same
breathing/focus model repeats its assumptions; a smoothness prior hides layer errors.

**Control.** The non-planar hidden-truth target defeats a plane, and the physical
ruler defeats a purely synthetic checker. Truth construction may not import strehl’s
focus or breathing model. Permuting the synthetic depth labels must force rank
correlation below `0.5`; an exact truth map must pass every bar. If the ruler angle
cannot be independently bounded tightly enough for the 5% slope bar, physical depth
is `UNMEASURED`.

### M11 — wall-clock throughput

**What it measures and why.** A focus stacker must turn a bracket into the delivered
master, not merely time one merge kernel. The proposal registers `>=2x` comparator,
`<=0.15 s/frame` CPU, `<=0.06 s/frame` hybrid, cold overhead `<=20 s`, and a
100-frame post-shutter latency `<=10 s`
(`2026-08-sota-path.md` lines 1957–1985).
It separately requires default quality work to remain within roughly `2x` the frozen
pre-feature wall clock (`2026-08-sota-path.md` lines 1648–1652).

**Input.** `bee-1-cpl` at N=299 and its first 100 frames; `coffee-bean` at N=105;
the first 33 bee frames; and bee prefixes N=96/97/98/99 for the modulo ladder.

**Exact computation.**

1. Run two required arms. The **comparative arm** starts from the common linear TIFFs
   and determines the `>=2x` comparator ratio. The **product arm** starts from the
   original ARWs through strehl’s shipping path and determines the absolute CPU,
   hybrid, cold, live-latency, and baseline-regression bars. Neither arm substitutes
   for the other.
2. Measure process start through closed, flushed, hashed TIFF plus manifest. Include
   the arm’s input decode/load, registration, stack, colour handling, and write.
3. The primary comparator ratio uses **warm-cache, uncompressed common TIFFs** from
   the same volume. This removes different RAW developers/decoders and prevents
   storage throughput from defining the win. Cold comparative values are reported but
   cannot establish the `>=2x` claim.
4. In the native-RAW product arm, report decode wall/CPU time separately from fold and
   write time. Do not subtract decode from the product result. If a comparator exposes
   no trustworthy stage timing, its native-RAW timing is diagnostic only; the
   common-TIFF arm remains the competitive timing.
5. Run one warm-up, then six alternating-order sweeps. Report the minimum per setting,
   with CPU time, busy fraction, GPU utilisation, bytes read/written, and per-stage
   banners. Cold and warm are separate.
6. Monitor the whole process tree; wait for all children and asynchronous writes.
7. Comparator speed uses the fastest mode that passes all quality gates at identical
   dimensions, bit depth, ICC, and common input.

**Success.** **PROPOSAL BARS:** warm common-input strehl throughput `>=2.00x` the
best comparator; native-RAW CPU-only at 16 workers `<=0.15 s/frame`; hybrid
`<=0.06 s/frame`; cold `<=warm+20 s`; first-100 streaming master closed and readable
`<=10 s` after `DSC00100.ARW` becomes available.
**SCORECARD FREEZE OF D5'S “ROUGHLY 2x”:**
candidate/default-baseline warm-wall ratio `<=2.00`. The baseline build/hash and its
complete settings are frozen before the candidate is timed.

**Known defeat.** Faster storage, a different RAW decoder, warm caches labelled cold,
timing only the merge, asynchronous exit, lower output quality, omitted
registration/write, or a favourable sweep order can fake speed.

**Control.** The warm uncompressed common-input arm controls storage and RAW decode;
the native arm prices strehl's actual decode bottleneck rather than hiding it.
Alternating sweeps and per-setting minima follow `AGENTS.md` rule 16. Input/output
hashes and quality qualification prevent omitted work. A planted 1-second sleep must
add `1.00+/-0.05 s`; a child that writes after parent exit must remain inside the
timer. A cold arm must begin after a documented reboot or equivalent machine-wide
cache reset on a dedicated benchmark host.

### M12 — memory, determinism, and scaling invariance

**What it measures and why.** Deep stacks must remain bounded and reproducible.
Worker-count dependence or hidden spill can make a fast-looking configuration
non-product behaviour.

**Input.** The same N=33/105/299 and worker-count matrix as M11.

**Exact computation.**

1. Run the comparative common-TIFF arm and native-ARW product arm separately. The
   absolute 6-GiB, scaling, determinism, and N-mod-4 bars apply to the native product
   arm; comparative memory is reported but is not a substitute.
2. Sample process-tree private committed bytes and working set every 10 ms; report
   peak committed bytes.
3. After one warm-up, hash the highest-precision delivered bytes from each of the six
   scored repetitions at worker counts 1/2/4/8/16 for each registered N. Do not hash
   a later 8-bit proxy.
4. **M12-D, fixed-worker determinism:** for each `(N, worker_count)`, count distinct
   hashes across its six repetitions.
5. **M12-S, cross-worker scaling invariance:** for each N, count distinct hashes
   across the canonical outputs at worker counts 1/2/4/8/16.
6. Compute warm-memory ratio `peak_N299/peak_N33`.
7. For N=96–99, divide warm wall time by N and compute
   `(max-min)/min`.

**Success.** The proposal bars are warm peak `<=6 GiB` and byte invariance. The
**SCORECARD ADDITIONS** that make “flat” numeric are
`peak_N299/peak_N33<=1.10` and N-mod-4 per-frame spread `<=2%`. M12-D requires
exactly one distinct hash in every fixed-worker six-run cell. M12-S requires exactly
one distinct hash across all five worker counts at every N, and the 16-worker output
must simultaneously pass M11. A product may pass M12-D while failing M12-S; the two
verdicts must never be conflated.

**Existing-evidence ruling.** The repository contains strong mechanism evidence but
not a scorecard reading. `byte-freeze.rs` says changing
`STREHL_PYRAMID_WORKERS` changes reduction order and moves 1 DN on about 0.2% of
pixels; `merge_cmd.rs` records 2 versus 7 workers differing on 0.2573% of a 205-frame
stack, maximum 1 DN (`byte-freeze.rs` lines 512–515; `merge_cmd.rs` lines
5322–5329). Both are outside the registered N/worker matrix. The reported
18-run sweep has six stable repetitions at each of 1/4/8 workers and three different
cross-worker hashes; its `C6765BFA...` arm matches the registered N=20
`coffee-bean-20-gate2-pyramid` byte-freeze, not N=33/105/299. That row freezes
`env_align=0`, `alignment_mode=off`, an empty scratch cache, and a pyramid path whose
own banner says photometric gain, clip census, outlier rejection, halo correction and
through-focus statistics were not applied. It also lacks workers 2 and 16 and a
scorecard command/output manifest proving the hashed artifact is the registered
highest-precision native product deliverable. Therefore it is
**diagnostic M12-D PASS / diagnostic M12-S FAIL**, while both formal sub-bars and M12
overall remain **UNMEASURED**.

**Known defeat.** Disk spill lowers RAM, monitoring only the parent misses workers,
and nondeterminism can disappear if outputs are rounded before hashing.

**Control.** Record process-tree memory, temp-file bytes, page faults, and child
lifetime. Allocate a planted 7-GiB child buffer and require the monitor to exceed the
bar; write one random output LSB and require the hash gate to fail. Hash the highest
precision common deliverable, not a later 8-bit proxy.

**Remaining registered run.** Reserve one uninterrupted **120-minute quiet-host
window**. Run native ARWs at N=33/105/299 with workers 1/2/4/8/16, one warm-up then
six alternating-order scored repetitions per cell, hashing every deliverable and
sampling the whole process tree every 10 ms. Run N=96/97/98/99 at 16 workers with the
same warm-up/six-sweep timing protocol for the modulo bar. This single run supplies
M12-D, M12-S, peak memory, `peak_N299/peak_N33`, and N-mod-4 spread; do not spend a
separate host window rediscovering the already-understood reduction-order mechanism.

## 5. Metrics deliberately rejected as primary evidence

1. **Raw band power, coarse-normalised band power, extreme-zone rank, acutance,
   MTF50, and slanted-edge SFR:** post-hoc sharpening or a tone curve can raise them
   without adding information. SFR remains a target/presentation diagnostic labelled
   unsafe; it cannot decide M1.
2. **The v1.3 `f_licensed` / `S_25` composite:** dropped. The cutoff is blind to both
   physical blur and genuine improvement. Native `S_25` moves `1.028294x` under
   USM on the superseding 64-site battery, outside the unchanged 1% bar; the earlier
   24-seed `0.995819x` apparent pass is underpowered and superseded. It also moves
   `18818.9045x` under a logistic tone curve, spans `0.004972x`–`10.381863x`
   under noise, and is angle-dependent. Tone-hardened derivatives reverse the optical
   controls. A control defeated every form, so it cannot remain a requirement merely
   because no replacement exists.
3. **Same-frame split-half FRC/SNR:** dropped. The proposal describes the halves as
   independent (`2026-08-sota-path.md` lines 1694–1733), but the commissioned lane
   found a common-mode adversary at `0.972099` and a null at `0.438734` against the
   `0.25` bar; reopening requires an independent repeated bracket, sensor-pattern
   subtraction, a non-degenerate partition, and a transferring tuner plant
   (`docs/STATUS.md` lines 156–198). M1/M9 therefore use repeated exposures only.
4. **SSIMULACRA2 / butteraugli on natural stacks:** the proposal names them
   (`2026-08-sota-path.md` lines 1525–1536) but supplies neither an all-in-focus truth
   image nor a bar. Comparing two unknown renders does not create a reference.
   They may commission synthetic plants, but do not rank real outputs in v1.6.
5. **A single composite “SOTA score”:** weights would let noise purchase a halo or
   speed purchase lost depth. The proposal’s end-state is conjunctive.
6. **Natural-object colour agreement:** programs can agree and all be wrong. M7 waits
   for a traceable target.

## 6. Honest current position

No score below was produced under §§1–4. Historical measurements, including apparent
wins, are not imported into this table. In particular, the previous “17–27% detail
deficit” is withdrawn: the comparator arm carried `Contrast2012=+100`, and tone alone
explained 94.8%, 109.9%, and 267.1% of the apparent three-band gaps
(`docs/research/V-HEADTOHEAD2.md` lines 23–27 and 57–70). The correct present
competitive statement is **unknown**.

| ID | Metric | strehl | Zerene Stacker | Helicon Focus | Current standing |
| --- | --- | --- | --- | --- | --- |
| M1 | Sharpening-safe resolved information | **UNMEASURED** | **UNMEASURED** | **UNMEASURED** | No admissible instrument or active bar; fresh dense reference and matched IBIS-off sw4/sw10 pairs are also absent. |
| M2 | Noise efficiency | **UNMEASURED** | **UNMEASURED** | **UNMEASURED** | Prior numbers were not produced under this matched-information protocol. |
| M3 | Halo / veil | **UNMEASURED** | **UNMEASURED** | **UNMEASURED** | Full-reach sites and new checker must commission. |
| M4 | Artifact rate | **UNMEASURED** | **UNMEASURED** | **UNMEASURED** | No v1.6 site manifest or control run exists. |
| M5 | DOF coverage / failure rate | **UNMEASURED** | **UNMEASURED** | **UNMEASURED** | New tilted block advances development only; a replacement controlled-slide holdout remains absent. |
| M6 | Highlight/shadow retention | **UNMEASURED** | **UNMEASURED** | **UNMEASURED** | The current rail census is under-powered; detail, geometry and comparator arms are blocked. |
| M7 | Colour fidelity | **UNMEASURED** | **UNMEASURED** | **UNMEASURED** | Traceable tilted colour target absent. |
| M8 | Independent source-hull census | **UNMEASURED** | **UNMEASURED** | **UNMEASURED** | M8-R/M8-O are ready to commission on the development-only flat slide; no result has been read. |
| M9 | Certificate calibration | **UNMEASURED** | **UNMEASURED** | **UNMEASURED** | New slide is development-only and has IBIS on; fresh depth-stack truth remains absent. |
| M10 | Physical depth accuracy | **UNMEASURED** | **UNMEASURED** | **UNMEASURED** | New slide can commission planarity/order only; it is not holdout or physical truth. |
| M11 | Wall-clock throughput | **UNMEASURED** | **UNMEASURED** | **UNMEASURED** | Existing timings are not the complete common-input v1.6 run; quiet host required. |
| M12 | Memory / determinism / scaling invariance | **UNMEASURED** | **UNMEASURED** | **UNMEASURED** | Out-of-protocol evidence is diagnostic M12-D PASS / M12-S FAIL; the v1.6 N=33/105/299 matrix and memory/modulo arms await a quiet host. |

## 7. Corrections and gaps in the governing proposal

The proposal is authoritative about direction, but these parts cannot stand as written:

1. **D1/D8’s empirical spine is invalid.** Same-frame halves are not independent.
   The proposal itself priced fixed-pattern and quantisation correlation
   (`2026-08-sota-path.md` lines 1727–1733), but phase 0 showed the confound is verdict
   changing, not a small correction. Independent repeated captures replace it here.
2. **Slanted-edge SFR is not a SOTA resolution metric.** It is useful for chart
   qualification and presentation transfer, but sharpening can raise it after the
   fact. The proposal’s D1 pairing of FRC and SFR therefore cannot be used as two
   independent votes.
3. **The comparator prerequisite is larger than a licence/export.** The proposal says
   the scorecard needs a Zerene licence, chart/export, and sharp subject
   (`2026-08-sota-path.md` lines 183–187). It also needs a common linear merge boundary
   in strehl. Without that, repeating the old RAW-versus-developed-TIFF asymmetry is
   unavoidable.
4. **Colour fidelity is unspecified and presently uncapturable.** D7 discusses ICC,
   soft proof, and tone policy but names no traceable target, DeltaE computation, or
   bar. Natural subjects cannot close that gap.
5. **Perceptual metrics are named without a reference.** SSIMULACRA2 and butteraugli
   cannot rank natural all-in-focus outputs when no truth image exists.
6. **Several headline bars are placeholders.** Occlusion veil, certified acuity,
   field coverage, and CPU `[X]` are not executable in §1. This scorecard marks its
   numeric completions as additions rather than attributing them to the proposal.
7. **The proposal’s competitive axis table is historical, not this scorecard.** Its
   “ahead” labels for noise, clipping, invented structure, and speed were obtained
   under different instruments and, in the old head-to-head, asymmetric development.
   None is a v1.6 current-position value.
8. **D2’s CRLB channel cannot certify itself.** The same noise model cannot generate
   admission and then validate its own certificate. M9 requires independent repeated
   exposures and external fixed-pattern treatment.
9. **Phase-0 outcomes narrow the implementation path.** C1/PHASE flips inside the
   measured convention interval and is therefore not robust (`docs/STATUS.md` lines
   203–223). C10/XSPEC measured `R=0.70852` with lower bound `0.66732` against required
   point/lower bars `2.0/1.5` (`docs/research/M-PHASE0-XSPEC.md` lines 31–35).
   C4c/DPAR is killed with the proposed effect 30x above the commissioned detection
   bound (`docs/STATUS.md` lines 118–145). Decode saturates at 16 threads and storage
   is about 4.5x faster, so I/O is not the bottleneck (`docs/STATUS.md` lines
   107–116). These results do not change the score bars, but they invalidate proposal
   text that treats those channels or I/O assumptions as open SOTA leverage.

### 7.1 Disposition of the independent opposed-pair stress test

- **Accepted:** noise and information must be quoted jointly from the same output;
  confidence precision and coverage are an opposed pair; and determinism must be
  demonstrated at the worker count that also meets runtime.
- **Accepted with correction:** “averaging fails MTF” becomes “averaging must fail a
  future commissioned sharpening-safe information constraint.” Standalone MTF remains
  inadmissible, and v1.6 has no such instrument.
- **Accepted with correction:** a future detail instrument, M4, and M8 should bracket
  sharpening together. Hull is corroborative, not guaranteed: a mild or explicitly
  clamped sharpening pass can remain inside the hull, so hull alone is not the
  opposite of sharpening.
- **Rejected:** making every metric a Pareto pair. Colour and physical depth have
  external truths, while the source hull is an invariant; forced opposites would be
  weaker than their independent controls.
- **Rejected:** assuming a fixed detail/noise tradeoff slope. A genuinely better
  algorithm may improve both. The scorecard requires simultaneous bars and reports
  Pareto points, but does not encode the phase-1 lane's internal acceptance numbers.

## 8. Publication rule

A result report must reproduce this scorecard verbatim by hash, publish every invalid
and refused arm, include commands and complete manifests, and state the verdict as:

- `PASS — SOTA under scorecard v1.6` is unavailable because M1 has no admitted
  instrument or bar; a later pre-results revision with a commissioned M1 is required;
- `FAIL`, when any commissioned primary gate misses;
- `UNMEASURED`, when any required metric, capture, comparator, or instrument is absent
  or invalid.

Until such a report exists, the only defensible public sentence is:

> **strehl’s competitive position against Zerene Stacker and Helicon Focus is
> unknown.**

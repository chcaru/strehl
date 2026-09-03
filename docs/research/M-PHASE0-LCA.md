# M-PHASE0-LCA — chromatic z-diversity is real, but this census is NOT ROBUST

Lane: `experiments/M-PHASE0-LCA/`. Preregistered and committed as `f0f63f71`
before this lane computed any real-capture focus statistic.

## 1. Verdict

**NOT ROBUST.**

The dispatch summary was wrong about the claim. C2 in
`docs/proposals/2026-08-sota-path.md`, under “C2. Chromatic z-diversity — the
bracket is three focus sweeps,” concerns **longitudinal/axial chromatic
aberration**: wavelength-dependent best-focus position along the bracket. It
does not concern lateral CA's wavelength-dependent radial magnification.

The preregistered primary result clears the historic M107 bar:

> **A = 0.5367 frames, stratified tile-bootstrap 95% CI [0.5101, 0.5883].**

`A` is the minimum, over three subjects, of
`abs(median_tile(k_R - (k_G1+k_G2)/2))`. All three medians have the
prior-registered negative sign, and every same-wavelength G1-G2 null clears the
0.125-frame gate. The primary arm therefore says **SURVIVE**.

That is not the filed verdict. In the registered field-radius ladder, the only
quartile with enough valid tiles from all three subjects reads **NARROWED**:
`A = 0.5170`, 95% CI `[0.4237, 0.5883]`. The centre and the other three
quartiles are indeterminate because the ruler registration retained fewer than
two tiles. A second registered rung, the 96-plane-pixel tile, fails its null
gate at 0.1389 frame. The protocol says a category change anywhere on a
registered ladder files NOT ROBUST. It changed.

This does **not** retract the older existence result. M107 and BUILD-CHROMA
already measured the same physical effect with two other instruments. It means
this lane cannot certify C2's requested *whole-field, build-the-offset* step.

Primary and ladder values come from
`out/measurement.json::primary_actionability` and
`::robustness.{parameter_ladder,radial_ladder}`. The arithmetic and hashes are
rechecked by `src/verify.py`.

### Protocol repair disclosed

A preliminary run occurred after preregistration while the instrument and
external fixtures were still untracked. That violated §7's stronger promise
that the fixed table and predicate would already be committed. Independent
review caught the breach and also found that equal G1/G2 peaks made the
external fixture blind to using G1 alone as the green reference.

Commit `a50a6ce41e50013575e667bc9675310ba5ed1add` freezes the repaired
instrument and four external fixtures. The repair adds unequal, separately
fixed G1/G2 inputs and plants the exact G1-only defect. **After that commit,**
all five preliminary curve caches were deleted and all 343 RAW frames were
decoded again; `measurement.json::cache.*.reused` is false for every stack and
records that commit as its run HEAD. The numbers below are only that
post-freeze run. This forward repair gives the reported run immutable inputs;
it cannot make the discarded preliminary run retrospectively compliant, so
the chronology breach remains disclosed rather than erased.

## 2. The corpus had already answered the existence question

The mandatory `prior_art.py` invocation returned `NO PRIOR REPORTS`; direct
search showed that answer was false. This is a search-instrument miss, not
absence of evidence.

* `SYNTHESIS.md` fact 1413, sourced to M107 `a16976f`, reports red leading
  green by **0.67–1.07 frames** and blue by **0.36–0.75 frames** on five of
  five stacks, with `|k_G1-k_G2| <= 0.008` and red losing 8.96–14.74% of its
  gradient energy.
* `experiments/M107-chroma/PRE-REGISTRATION.md`, “Instrument B” and “B3,”
  registered the per-channel focus peaks, same-wavelength null, and
  **0.5-frame** magnitude bar before measurement. Its sign-straddling
  prediction failed and was disclosed in current fact 1416 rather than
  rewritten: red and blue are on the same side of green.
* `experiments/M107-chroma/src/e3_controls.py` carries four real-data controls.
  Its zero-free-parameter N2b arm swaps R and G1 data and requires the measured
  signal and null to exchange places. That is materially stronger than
  regenerating curves with the peak estimator itself.
* `docs/research/BUILD-CHROMA.md` independently replicated M107 with a
  whole-field instrument: red **−0.66 to −0.90**, blue **−0.48 to −0.75**
  frames on four stacks; G1-G2 **+0.0005 to +0.0113**. It also measured a
  nonzero centre intercept, separating axial from lateral CA.

No retraction of fact 1413 or BUILD-CHROMA's axial result was found. Later
retractions in that chain concern the **lateral** coefficient, colour-matrix
contamination, and render-domain descriptions, not the focus-axis result.

Two limits prevent the cleaner `ALREADY ANSWERED IN CORPUS` label here.
BUILD-CHROMA's original `C:\dev\strehl-out\BUILD-CHROMA` outputs are gone, so
its exact run cannot be audited from artifacts; and this lane preregistered
that any field-radius category change overrides a clean primary result. That
override fired. The corpus answers “does axial CA exist?”; this lane does not
robustly answer “can one field-valid offset be built now?”

## 3. Instrument

`src/lca_lib.py::peak_fit` implements the proposal's mandated M33 estimator:
for each tile and CFA channel it finds the discrete maximum, subtracts that
curve's fifth-percentile baseline, and fits a quadratic through the logarithms
of the three samples around the maximum. The vertex is the sub-frame peak.

The input path is:

1. copy `rawpy.raw_image_visible` before its context closes;
2. assert RGGB `[[0,1],[3,2]]`, `RGBG`, black 512;
3. split native R/G1/G2/B planes — no demosaic, white balance, colour matrix,
   or rendered data;
4. solve direct-to-reference phase correlation on G1 only, fit a robust smooth
   track, round it to integer plane pixels, and apply it unchanged to all four
   channels;
5. measure mean native-CFA Sobel `Gx²+Gy²` in a fixed 8×6 field grid;
6. fit each channel's focus peak and form
   `delta_R=k_R-(k_G1+k_G2)/2`, `delta_B` analogously, and the control
   `delta_null=k_G1-k_G2`.

The independent unit is a tile. No uncertainty treats the 144×144 pixels or
the frames inside a focus curve as independent replicates.

### Captures

| role | exact directory | frames |
|---|---|---:|
| primary grid | `D:\personal\macro\requests\30-calibration-grid\calibration-grid-1-sw4-cpl` | 55 |
| primary fabric | `D:\personal\macro\requests\7-aperture-pairs\fabric-weave-f11-sw5-cpl` | 109 |
| primary ruler | `D:\personal\macro\requests\8-tilted-planar\ruler-incline-ang10.26deg-inches-f11-sw7-cpl` | 65 |
| grid step ladder | same grid subject, `sw1` / `sw4` / `sw10` | 91 / 55 / 23 |

`measurement.json::capture_inventory_before` records every name, byte count,
and mtime. The post-run inventory is exactly identical. No capture file was
written.

## 4. Commissioning

**8/8 controls GREEN; 9/9 planted defects RED. Every plant fired.**

| control | untreated reading | planted defect that went RED |
|---|---|---|
| fixed external focus table and separate fixed predicate | `dR=-0.750000`, `dB=+0.500000`, null `0` | replace log fit with linear fit (`dR=-0.770391`) |
| signed offsets and frame units | all four peaks within 0.01 frame of fixed predicate | invert vertex sign; double frame coordinate |
| separate fixed unequal-green input/predicate | G1/G2 = 4.5/5.5, green mean = 5.0; `dR=-0.75`, `dB=+0.75` | use G1 alone as green; `dR=-0.25`, `dB=+1.25` |
| fixed RGGB mosaic | R/G1/G2/B = 101/202/303/404 | swap G2 and B sites |
| phase-correlation convention | 5/5 fixed `numpy.roll` shifts recovered | invert returned registration sign |
| G1-G2 null sensitivity | `0.000000` frame | shift G2 by one frame |
| dose and ceiling ladder | estimator reads 0/0.25/0.5/**1.0**/2.0 at those doses; slope 1.0 | clamp output to 0.25, slope falls to 0.20 |
| decoder contract | two rawpy copies hash-identical; Rust probe agrees on body, ISO, height and black | admit 7168×5120 padded buffer as active |

The first row is cancellation-immune for the peak fit:
`fixtures/fixed-curves.json` and `fixed-predicate.json` are fixed data, not
output from `peak_fit`; the checker demonstrates power by making the domain
substitution it targets. The new unequal-green row separately commissions the
load-bearing `(G1+G2)/2` operation against
`fixed-offset-{input,predicate}.json`; its G1-only plant changes the answer and
goes RED. The dose control is judged against what the estimator reads when one
frame is fully present — **1.0 frame** — not merely against the physical dose.

The decoder comparison records one honest disagreement. rawpy/LibRaw exposes
7028 visible columns; strehl/rawler reports 7032 active columns. This lane
uses only rawpy's copied 7028. Height, body, ISO and black agree. Pixel identity
between the two decoders was not available from the Rust probe and is not
claimed.

Full readings: `out/commission.json`. Its own summary is not trusted blindly:
`src/verify.py` requires the exact registered control/plant, cache, parameter,
radial, and step identities; recomputes counts and categories from detailed
ladder rows; checks every numeric null/category implication; and checks the
headline and result tables against the machine-readable result. Its eighteen
in-memory plants include coordinated summary flips, deletion of required
controls/caches/ladder arms, and value-preserving swaps between labelled
report rows; an honestly reported failed commission also goes RED. **18/18 go
RED.**

## 5. Primary measurement

Primary: common integer registration, 144-plane-pixel tiles, baseline p5,
prominence 1.5, log-domain fit.

| stack | valid tiles | delta R, frames (95% CI) | delta B, frames (95% CI) | G1-G2 null, frames (95% CI) |
|---|---:|---:|---:|---:|
| grid `sw4` | 47/48 | **−1.7384** [−1.7953, −1.5572] | −1.7866 [−1.9418, −1.6835] | −0.0108 [−0.0276, +0.0190] |
| fabric f/11 `sw5` | 16/48 | **−0.6594** [−0.9011, −0.5818] | −0.4431 [−0.4833, −0.3674] | +0.0089 [−0.0043, +0.0237] |
| ruler f/11 `sw7` | 4/48 | **−0.5367** [−0.5883, −0.5101] | −0.2852 [−0.3014, −0.2191] | −0.0346 [−0.0886, −0.0073] |

Every red and blue estimate is ahead of green, reproducing M107's
same-side-secondary-spectrum result. The same-wavelength null is much smaller,
but the ruler null is statistically nonzero on only four retained tiles and in
the direction that flatters the result. Its preregistered magnitude gate still
passes; its direction is a reason not to promote the primary SURVIVE.

Green's median HWHM is 8.5 / 5.25 / 2.5 frames for grid/fabric/ruler. The
corresponding red offsets are **0.205 / 0.126 / 0.215 HWHM**, derived directly
from the two stored fields. This lane's green-elected red energy forfeits are
**3.09% / 1.84% / 4.71%** (blue 3.34% / 0.49% / 1.11%).

Those costs are lower than M107's selected-ROI 8.96–14.74%. The methods do not
support choosing one as “the” render payoff: this lane measures one aggregate
tile curve, while M107 measured dense selected points. No shifted-gather
render was made, so neither number is an end-to-end quality gain.

Trace: `measurement.json::primary_stack_summaries`, produced by
`measure.py::summarise_cache`; `A` and its cluster bootstrap come from
`measure.py::combined_actionability`.

## 6. Stress tests and why the verdict is not robust

### 6.1 Parameter ladder

Across arm × tile side × baseline × prominence there are 54 rungs.

* All **27 unregistered** rungs say SURVIVE, with `A=0.5574..0.5658`.
  Common registration is not manufacturing the primary effect.
* Registered 144- and 192-pixel tiles: **18/18 SURVIVE**,
  `A=0.5367..0.5478`.
* Registered 96-pixel tiles: **9/9 VOID_NULL_GATE**. The effect itself remains
  `A=0.5497`, but the four-tile ruler G1-G2 uncertainty pushes
  `|median|+halfwidth` to **0.1389**, beyond the registered 0.125 limit.
* Baseline 0/5/10 and prominence 1.2/1.5/2.0 do not materially move A within a
  fixed arm/tile side.
* The linear-domain dissenting estimator, which the proposal does not permit
  as primary, also says SURVIVE: `A=0.5523 [0.5204,0.5967]`.

### 6.2 Field radius

Only radial quartile 2 retains at least two tiles from every subject. It reads
`A=0.5170 [0.4237,0.5883]`, **NARROWED**. Centre, Q1, Q3 and Q4 are
indeterminate. There is no contrary sign; there is no measurement with enough
power to certify the field.

The immediate cause is visible before any statistic: registration accepts
47/48 grid tiles, 18/48 fabric tiles, and only **4/48 ruler tiles**. The reason
direct-to-reference phase correlation rejects the other ruler tiles was not
established. Calling them “bad data” after seeing the result would weaken the
registered design, so they remain rejected and the field-radius bar remains
failed.

### 6.3 Real focus-step ladder

The same grid target at fixed f/5.6 reads:

| setting | valid tiles | delta R (95% CI on magnitude) | green HWHM | `abs(delta_R)/HWHM` |
|---|---:|---:|---:|---:|
| `sw1` | 30 | −3.4133 [3.2273, 3.5824] | 16.5 | 0.2069 |
| `sw4` | 47 | −1.7384 [1.5572, 1.7953] | 8.5 | 0.2045 |
| `sw10` | 47 | −0.8770 [0.8463, 0.9158] | 4.0 | 0.2192 |

All three clear SURVIVE, and normalising by the response's own HWHM collapses
the three readings to 0.2045–0.2192. That is strong physical corroboration:
the estimator tracks one approximately fixed fraction of the channel's
through-focus width rather than one fixed number of frames.

It also kills the simplest implementation. A gear-profile constant such as
`delta_R=-0.7 frames` cannot be correct at all capture step settings. The
camera's `sw` menu is not a calibrated linear distance — `delta_R*sw` is not
constant — so multiplying by the menu value is not licensed either.

## 7. What changes in the Rust source

**Nothing changes in Rust as a direct result of this verdict.**

That is explicit, and it is not “the effect is too small.” The effect already
exists in three instruments and the primary magnitude clears the build bar.
Nothing changes because the proposed correction is not yet identified in the
units the product needs, and this lane failed its field-radius robustness
requirement. Baking a constant now would convert a real optical effect into a
wrong profile.

The result also corrects the proposal's claim that the middle option is “a
one-line change in gather indexing.” On the current default path:

* `crates/strehl-core/src/pyramid.rs::BandMerge::add_frame_with_gain` builds
  one green-luma weight field and stores one shared `den`; every plane from
  that **same frame** is accumulated against it.
* `crates/strehl-cli/src/merge_cmd.rs::BandWorker::fold` decodes, deinterleaves,
  folds, and drops one frame at a time. A fractional temporal shift needs at
  least adjacent-frame R/B samples, and chunk boundaries need a temporal halo.
* `crates/strehl-core/src/merge.rs::Estimator::fold` likewise accepts one
  `frame_index`, one source quad, and one regularised field for all planes.
* `crates/strehl-core/src/optics.rs::OpticalProfile` currently represents
  spatial `eps_r/eps_b` and translation only. Axial focus displacement is a
  different quantity and must not reuse those fields.

If a follow-up first derives a per-stack conversion from response width to
frame displacement and restores field coverage, then the concrete source work
is: add separately typed axial calibration to `optics.rs`; add a bounded
adjacent-frame/chunk-halo gather in `merge_cmd.rs`; let `pyramid.rs` consume
green weights with temporally shifted R/B planes; and give `merge.rs` the same
channel-specific second-pass source mapping. Until then, these modules remain
unchanged.

The claim's current value is therefore diagnostic, not zero: **do not spend
4–4.5× on per-channel election, and do not bake a frame scalar.** The only
licensed next implementation is a per-stack calibration seam, not the
correction itself.

## 8. What was not verified

1. The field-radius requirement was not verified: 4/48 ruler registrations
   left only one usable quartile across all subjects.
2. No shifted-gather Rust implementation or end-to-end render was built, so
   this lane did not verify that recovering 1.8–4.7% focus-energy loss improves
   visible or FRC-scored output.
3. No physical focus distance was decoded. The camera step-width setting is
   not metric and cannot calibrate a profile by itself.
4. Aperture independence was not isolated. That premise belongs to the
   dispatch's mistaken lateral-CA summary; this C2 lane has f/5.6 grid and
   f/11 natural subjects, so aperture and subject differ together.
5. Rust/rawler and rawpy/LibRaw pixel arrays were not compared sample for
   sample. Their metadata contracts agree except for the disclosed
   7032-versus-7028 active-width convention.
6. BUILD-CHROMA's original external outputs are absent. Its committed code and
   report survive, but the old execution artifact cannot be hash-verified.
7. The preliminary-run fixture chronology did not meet the preregistered
   committed-input promise. The definitive artifacts were rebuilt from RAW
   after the repaired instrument/fixtures were frozen at `a50a6ce4`, but that
   forward repair does not erase the disclosed deviation.

## 9. Reproduction and artifact identity

Run from the repository root:

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH=(Get-Location).Path
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
python experiments\M-PHASE0-LCA\src\commission.py
python experiments\M-PHASE0-LCA\src\measure.py
python experiments\M-PHASE0-LCA\src\verify.py
```

Recorded environment: Python 3.12.10, rawpy 0.27.0, NumPy 2.4.4, SciPy 1.17.1,
Windows 11. The definitive from-RAW run recorded instrument-freeze HEAD
`a50a6ce41e50013575e667bc9675310ba5ed1add`; the preregistration itself is the
earlier lane-owned commit `f0f63f71`.

Curve-cache SHA-256:

| cache | SHA-256 |
|---|---|
| `grid_sw1.npz` | `30021b5924b8d4011d656f8f49cd43b83b08cac3adc77bd467afa9da78d8e845` |
| `grid_sw4.npz` | `39e2c25228b26d7ff68aa1ac2110ba98c6738fa4a451f183e289dec2a597833d` |
| `grid_sw10.npz` | `dcb37f7455af5b7d80c8085158e1260e7f73d82d7fd9d20a759318d9e031f266` |
| `fabric_f11_sw5.npz` | `a223f495631c3f2ea6815fb13ecda159f922aa8bf294ae880f39e8176d2cee96` |
| `ruler_f11_sw7.npz` | `e8ddc7a8ff73988f95d1836d1073b30478d606ad7cfa60796ae9b1a9c05b5984` |

`measure.py` fingerprints its own source, `lca_lib.py`, fixed configuration,
every input path/size/mtime, Python/platform/package versions, and the rawpy,
NumPy multiarray, and SciPy ndimage binary hashes into each cache. A repeat
with unchanged inputs reuses only an exact fingerprint match. The definitive
run rebuilt all five caches (`reused=false`). All generated artifacts are
under `experiments/M-PHASE0-LCA/out/`.

## 10. Re-scope audit: the requested build is locked out

On 2026-09-02 the orchestrator re-scoped this lane: audit the corpus claim that
C2 was already answered, then build only if that audit returned GO. The new
protocol was committed before replay as
`08cf9401fe79f4e15973c02aa89518b24ec687ed`. Its conjunctive Part-1 gate
returned **STOP**, so no Rust prototype or corrected render was permitted.

### 10.1 What reproduced

The missing BUILD-CHROMA artifacts were regenerated from all 1,002 RAW frames,
then scored by an independent implementation that does not import the legacy
peak/loss checker:

| stack | dR, frames | dB, frames | R forfeit | B forfeit |
|---|---:|---:|---:|---:|
| `lavendar-cpl` | -0.8075 | -0.7185 | 6.62% | 5.19% |
| `coffee-bean` | -0.8100 | -0.4845 | 7.36% | 3.51% |
| `couch-fibers-cpl` | -0.8977 | -0.7124 | 7.54% | 7.06% |
| `bee-2-cpl` | -0.6601 | -0.7540 | 4.22% | 7.13% |

All offset errors against the old report are below 0.00005 frame, and every
G1-G2 null clears 0.034 frame including uncertainty against the 0.125 gate.
The published channel-wise gain multisets reproduce: R
4.22/6.62/7.36/7.54% and B 3.51/5.19/7.06/7.13%.

The audit preregistration made one explicit error: BUILD-CHROMA printed those
four gains as channel-wise ranges without stack labels, and the new table
incorrectly assigned that printed order to the four stacks. The frozen
per-stack mapping therefore fails even though the multisets reproduce. It was
not rewritten after measurement.

### 10.2 Commissioning and cancellation

The new checker reads a committed external response table and a separately
committed answer. **2/2 controls are GREEN and 6/6 exact defects go RED**:
vertex-sign inversion, doubled frame scale, R/B swap, G1-only reference,
loss-sign inversion, and omitted affine normalisation. Its STOP finalizer has
one integrity control and five plants, all RED.

The old synthetic defocus generator uses Gaussian blur independently of the
three-point peak checker, so it is not literal generator/checker cancellation.
It remains supporting evidence only. The fixed predicate is the
cancellation-immune control; real G1-G2 data and M107's R↔G1 label swap are
additional data paths the peak checker did not generate.

### 10.3 Tone audit: the build-blocking failure

The legacy measurement itself is black-subtracted native-CFA linear RAW: no
demosaic, colour matrix, white balance, render tone curve, or comparator. The
old numbers are therefore not the same kind of developed-TIFF contrast
artifact that retracted V-HEADTOHEAD2.

That provenance is not enough to promote raw Sobel forfeit to a
tone-independent *recoverable output gain*. The preregistered affine-invariant
`Sobel energy / local variance` focus curves retained 24 valid tiles on
`coffee-bean`, but **zero accepted tiles** on `lavendar-cpl`,
`couch-fibers-cpl`, and `bee-2-cpl`. Both registered lavendar gamma arms
(0.8 and 1.2) also retained zero tiles. Direct RAW spot checks match those
caches within 7.1e-08 relative error; this is the metric declining, not a cache
indexing bug. The required four-stack tone gate cannot be evaluated and files
STOP.

### 10.4 It is axial, not lateral

The evidence supports **longitudinal/axial chromatic aberration**. It measures
peak position along focus-frame index. The independent radius fit gives:

* lavendar centre intercept -0.8183 frames,
  95% CI [-0.9725,-0.4531];
* coffee centre intercept -0.8765 frames,
  95% CI [-0.9343,-0.8216].

Both retain at least half the fitted edge magnitude. Lateral radial
magnification must be zero at the optical centre; the whole measured effect is
already present there.

The registered retraction scan covered 56 files: every `.md`, `.txt`, and
`.py` under `experiments/M107-chroma`, plus the exact BUILD-CHROMA, M107,
M107b, M113, M114-retraction, and V-CA notes. All 37
`RETRACT`/`WITHDRAW`/`AMEND` hits are recorded and classified. None withdraws
these axial peaks or raw forfeit. Existing withdrawals concern
lateral-epsilon focus dependence, M113's lateral bootstrap width, M114's
rendered gain/application factor, and V-CA's rendered blue-harm claim.

### 10.5 Product consequence

**No Rust changes were made under the re-scoped order.** In particular,
`STREHL_AXIAL_CA_SHIFT` was not added and the foreign concurrent
`merge_cmd.rs` work was not touched. Because Part 1 returned STOP, there is no
default/zero/corrected/wrong-sign render and no before/after gain to report.
Claiming the requested zero and wrong-sign controls without running them would
be worse than shipping nothing.

Before a build, a new preregistered audit must commission a tone-invariant
payoff statistic that retains valid peaks on all four stacks, freeze the
correct per-stack gain association, and return GO. Only then do the zero-output
identity and wrong-sign-harm render bars become licensed.

Machine-readable trace:
`out/c2-audit-commission.json`, `out/c2-audit.json`. The commission source was
frozen at `2bfbb13a7135ce560e11d57f897c11098e7219f7`; the RAW/cache producer at
`cb66893eabf3822ff0485f9fbc9d9c2319a81e8c`; and the result finalizer at
`7d7c6ef7a5aa2b906aad06d98e8845580d6c8cc2`. The JSON also records the exact
finalizer source hash rather than claiming circular commit provenance.
Independent ultra-verification recomputed every headline NPZ statistic,
checked RAW samples and cache fingerprints, and returned **VERIFIED** for
STOP/no-Rust.

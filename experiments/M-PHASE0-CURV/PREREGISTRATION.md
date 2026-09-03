# M-PHASE0-CURV — preregistration

**Status:** REGISTERED before this lane decoded any RAW pixel, computed any
through-focus response, fitted any focus surface, or inspected any image from
the nominated captures.

**Owned paths:** `experiments/M-PHASE0-CURV/` and
`docs/research/M-PHASE0-CURV.md` only.

**Read-only inputs:** `D:\personal\macro`, especially
`requests\8-tilted-planar`, `requests\30-calibration-grid`,
`flat-on-ruler-cpl`, and `dime-flat-narrow-slices-cpl`.

### Amendment A1 — registered after the first commissioning RED, before measurement

The first E8 run decoded one control frame and correctly went RED: Rust/rawler
reports active `7032 x 4688`, while rawpy's `raw_image_visible` is
`7028 x 4688`. Black agrees at 512; Rust exposes the usable white 15360 while
rawpy exposes container white 16383. This exact four-column convention is also
reported by the pre-existing M84 lane, so it is not silently reconciled by
cropping one arm to the other.

E8's original requirement that the two decoders "agree on active dimensions"
is **superseded** by a stricter fixed-contract check: height must agree at 4688,
rawpy width must equal Rust width minus exactly four, the two white semantics
must retain `15360 <= 16383`, and all other registered fields must agree. The
measurement coordinate system is rawpy-visible `7028 x 4688`, because that is
the buffer the Python response operator actually reads. The planted dimension
defect now mutates that fixed `-4` relation and must go RED.

The complete failed reading is preserved as
`out/commission-initial-red.json` (SHA-256
`d1814a701433a799f1e83bad6e9e607115d16b7b16da7c55f39b3060c41c7267`).
No focus response or image statistic had been computed when this amendment was
written.

## 1. The authoritative question, and a correction to the dispatch summary

The dispatch summary describes field curvature as potentially requiring a
different image merge. That is not C5's authoritative claim.
`docs/proposals/2026-08-sota-path.md` C5 says:

> per-pixel *selection* absorbs field curvature and it should not be modelled
> for image output.

Its concern is a future **metric depth product**. A solved focus field contains
scene depth plus the lens's focal-surface bowl; depth TIFFs, surface normals,
and reshoot advice in millimetres would inherit that bowl. C5 proposes fitting
the bowl on planar subjects and caching it in the optical profile behind the
gear guard.

This lane therefore asks:

> After removing the complete focus-index field permitted by a tilted flat
> plane, including a nonlinear frame-to-depth axis, is there a repeatable,
> lens-fixed, even cross-field focus offset large enough to contaminate a
> future depth product?

It does **not** test whether per-region selection can choose different frames.
The architecture already answers that: the default pyramid elects per band
coefficient (`pyramid.rs`), while the estimator elects a regularised
`best_index` per pixel (`merge.rs::FocusStats`). Neither assumes one globally
sharp frame.

## 2. Reconnaissance and prior evidence already seen

This lane is not blind. Before registration it:

* read C5, A5, `AGENTS.md`, `ARCHITECTURE.md`, and F §6.5;
* commissioned `experiments/ORCH-drift-check/prior_art.py` (both positive
  subjects and its negative subject passed), then searched `field curvature`,
  `focal surface`, `planar focus`, `sensor tilt`, `target tilt`, `bowl`, and
  spelling variants in both `docs/research/` and `experiments/`;
* listed directories and read EXIF only. No pixel was decoded.

The relevant corpus is conflicting but does not answer this question:

1. `F-camera-lens-optics.md` §6.5 argues that per-pixel selection absorbs field
   curvature for image output and explicitly labels its survey of other
   stackers UNVERIFIED.
2. `M-PHASE0-ZFIELD.md` measures focus-peak uncertainty and local plane
   coherence on eight non-planar M66 cubes. It reports a conditional,
   extrapolated A5 survival and explicitly says its cubes are unaligned and not
   the shipping 5x5 operator. It never fits a lens-fixed bowl. Its controls and
   checker are commissioned, so its warnings about pure-noise argmaxes and
   correlated spatial responses are adopted here; its verdict is not.
3. `M84-ruler-metrology.md` refuses metric truth from the ruler captures.
   `M84b-ruler-metrology.md` reaches the opposite verdict on the same captures,
   catches a 3.12-degree coordinate-frame error only through an independent
   implementation, and measures a 1.53x non-constant focus step. Neither fits
   field curvature. Their disagreement is a warning, not a vote.
4. `BUILD-CHROMA.md` reports a 0.25–0.34-frame centre-to-corner trend in blue
   relative to green on three stacks and says wavelength-dependent field
   curvature is one possible explanation. It calls the result under-powered;
   a later depth-dependent estimator failed its own planted-zero controls.
5. C5 itself names `flat-on-ruler-cpl` and
   `dime-flat-narrow-slices-cpl` as planar substrates. The former is known from
   M84b to carry about 3.3 degrees of target/sensor tilt. Tilt is therefore a
   required nuisance term, not evidence against using it.

EXIF reconnaissance fixed the roster before measurement:

| capture | frames | ISO | marked aperture | exposure | focus-distance tags |
|---|---:|---:|---:|---:|---|
| `ruler-incline-ang10.26deg-inches-f5.6-sw7-cpl` | 120 | 100 | f/5.6 | 4 s | 0.2738–0.2805 m |
| same, `f8` | 85 | 100 | f/8 | 4 s | 0.2738–0.2805 m |
| same, `f11` | 65 | 100 | f/11 | 4 s | 0.2738–0.2805 m |
| `flat-on-ruler-cpl` | 79 | 100 | f/5.6 | 0.3 s | 0.2707–0.2771 m |
| `dime-flat-narrow-slices-cpl` | 207 | 100 | f/5.6 | 0.8 s | 0.2738–0.2771 m |
| five `30-calibration-grid` runs | 23–91 | 100 | f/5.6 | 1 s | 0.2738–0.2771 m |

All report the same 200 mm lens-plus-2x-teleconverter path and IBIS on.

## 3. Estimand

### 3.1 Why an affine plane is insufficient

For a physical plane, inverse depth is affine in image coordinates. Frame index
is not depth: M84b measured a 1.53x change in micrometres per frame over one
bracket. A fit of

`best_frame = a + bx + cy + q(x^2+y^2)`

would therefore call the nonlinear focus axis "field curvature", especially on
the deliberately tilted ruler. That is the main defect this lane is designed
to catch.

Let `(x,y)` be active-image coordinates centred on the sensor and divided by
half the active-image height, preserving physical pixel aspect ratio. A robust
affine fit supplies the plane-gradient direction. Rotate into `u` along that
gradient and `v` perpendicular to it.

The primary robust model is

```
k_hat = b0 + b1*u + b2*u^2 + b3*u^3
              + b4*v + b5*u*v + b6*u^2*v
              + q*v^2 + error.
```

The arbitrary smooth relation between planar depth and frame index lives in
the powers of `u`. Linear target/sensor tilt is in `b1` and `b4`; small
direction drift is in the odd cross terms. The even cross-track coefficient
`q` cannot be produced by a flat plane under a one-dimensional focus-axis
mapping. Under C5's radially symmetric bowl assumption, the inseparable
along-tilt `q*u^2` is already absorbed by `b2`, and the identified `q*v^2`
recovers the same bowl coefficient.

**Primary statistic `Q_H`:** `q`, in native frame indices, evaluated at a
cross-track radius equal to half the active-image height (`|v| = 1`).
Positive means that, after standardising filename order to increasing EXIF
focus distance, the cross-track edge focuses later/farther than the centre.
The statistic is observed across most of that radius and does not extrapolate
to the corner.

An optical-centre translation changes only constant and linear terms of a
quadratic bowl, not `q`; no principal point is fitted or assumed.

### 3.2 Primary and ladders

The registered primary is the f/5.6 `8-tilted-planar` stack: widest aperture,
shallowest depth of field, frame-filling known planar metal texture. Its
f/8 and f/11 captures are the aperture/DoF ladder with target, light, exposure
time, focus step width, and composition held fixed.

Target ladder:

1. `flat-on-ruler-cpl`;
2. `dime-flat-narrow-slices-cpl`;
3. `30-calibration-grid`, diagnostic only because the clear film is 0.1 mm
   above textured paper and can produce two focus layers.

`7-aperture-pairs` is **excluded from the curvature estimate** because its own
README says the fabric is non-planar and waved. It cannot distinguish target
shape from lens shape. The planar ruler already supplies the required aperture
ladder.

Other mandatory ladders:

* scene-axis polynomial degree 2, 3 (primary), and 4;
* primary 7-point log-quadratic peak versus a half-height centroid;
* spatial support using the central 60%, 80%, and full registered valid field;
* separate G1, G2, and their response average.

## 4. RAW response and peak estimator

Only copied `rawpy.RawPy.raw_image_visible` data are used; the copy/conversion
occurs inside the context manager. The RGGB contract is checked. G1 and G2 are
kept separate, black-subtracted, then each is 2x2 area-averaged on its own
green lattice. No demosaic, white balance, tone curve, merge, alignment,
resampling between frames, or best-frame image is used.

The fixed spatial grid is 31 by 21 sites spanning active-image fractions
`x = 0.06..0.94`, `y = 0.08..0.92`. At every frame and site:

```
R = box17(Sobel_x^2 + Sobel_y^2) / max(box17(signal), 32 DN)^2.
```

`scipy.ndimage.sobel` is called on one 2-D frame plane at a time, never on a
frame cube. Tile clipping above 15360 and signal-floor failures are recorded.
The response division removes exposure scale but can be fooled upward by noise
in a dark/flat tile; the peak-reality gate below is the defence. It can also be
fooled by texture moving through a fixed site under focus breathing; large
support, G1/G2 replication, the target ladder, and a spatial shift placebo are
the defences. The metric is evidence about **peak location only**, never image
quality.

For each site's response curve:

1. estimate curve noise by the 5-point fourth-difference MAD used by ZFIELD;
2. smooth only along frame index with a 9-point, cubic Savitzky–Golay filter;
3. fit a quadratic to seven log-response samples around the interior maximum;
4. take its vertex as the primary `k_hat`;
5. independently compute the centroid of the contiguous above-half-prominence
   region.

A site is valid only if all are true:

* the discrete maximum is at least four frames from either bracket end;
* the log quadratic is concave, its vertex lies inside its seven samples, and
  adjusted `R^2 >= 0.80`;
* `(peak - median) / sigma_curve >= 6`;
* primary G1 and G2 peaks differ by at most 3.0 frames;
* fewer than 0.1% of the local samples clip and local mean exceeds 32 DN.

Validity is decided without reading a spatial-model residual. At least 180
sites, 12 occupied 5-by-4 spatial bootstrap blocks, 30 sites on each side of
`v=0`, and a `v` span of 1.2 are required. A stack failing these gates is
UNSCORABLE, never zero-curvature.

## 5. Fit, uncertainty, and deciding number

The surface fit uses Huber IRLS (`c = 1.345`), equal site weights, and at most
50 iterations. Equal weights avoid letting a sharp/noisy response choose the
spatial model that later certifies it.

The interval for `Q_H` is a deterministic 2,000-draw percentile bootstrap over
5-by-4 spatial blocks, re-estimating the plane direction and every nuisance
coefficient each draw. This treats target micro-relief and neighbouring
response correlation as cluster effects rather than 651 independent pixels.
The separate-green and alternate-peak estimates are sensitivities, not
additional pseudo-replicates.

The **single deciding number** is f/5.6 `Q_H` with that 95% interval.

Per stack:

* **MATERIAL:** the whole 95% interval has one sign and its endpoint nearest
  zero has `|Q_H| >= 0.50` frame.
* **DETECTED-SMALL:** the interval excludes zero and `|Q_H| >= 0.25` frame, but
  it is not MATERIAL.
* **NEGLIGIBLE:** the entire 95% interval lies inside `[-0.25,+0.25]` frame.
* **UNRESOLVED:** anything else.

The 0.25/0.50-frame bars are fixed before pixels are seen. Half a native frame
is the smallest bowl that changes a nearest-frame depth label over a full
step; one quarter frame is the practical null band relative to the
0.24–0.60-frame median per-pixel uncertainties already measured on several
ZFIELD stacks. These are depth-product bars, not image-quality bars.

Lane verdict:

* **SURVIVE:** primary is MATERIAL; f/8 and f/11 are same-sign DETECTED or
  MATERIAL; and at least one independent target is same-sign DETECTED after
  frame-direction standardisation.
* **KILL:** all three controlled-aperture ruler rungs are NEGLIGIBLE and no
  independent target is DETECTED.
* **NARROWED:** evidence is real but only DETECTED-SMALL, capture-specific, or
  unscorable at the replication bar.
* **NOT ROBUST:** any aperture, target, field-radius, polynomial-degree, or
  peak-estimator ladder flips between MATERIAL and NEGLIGIBLE, or two detected
  rungs flip sign. UNSCORABLE/UNRESOLVED is disclosed and narrows evidence but
  is not manufactured into a flip.
* **ALREADY ANSWERED IN CORPUS:** only if a commissioned, non-retracted prior
  report with this same tilt-separated statistic is found before decode. The
  completed search found none.

No random-effects pooling across different focus-step widths is allowed.

## 6. Commissioning before real measurement

Every control runs before the first real RAW decode and writes its readings to
`out/commission.json`. A control counts only if the unmodified path is GREEN
and the named planted defect makes the same check RED.

1. **E1, cancellation-immune external plane.** Read, but never modify,
   `experiments/M84b-ruler-metrology/out/depth-truth-params.json`, SHA-256
   `745bbbc...c63973d69`. Its independently produced projective plane and
   nonlinear `n_model_poly_k2k1k0` are a fixed external predicate: after the
   registered nuisance model, `|Q_H| <= 0.05` frame. This fixture was produced
   by code this lane does not import. Plant: fit only affine tilt plus radial
   `r^2`; the deliberately nonlinear plane must violate the same bound.
2. **E2, known curvature dose ladder.** An independent response-cube generator
   supplies `Q_H = {-2,-1,-0.5,0,+0.5,+1,+2}` frames with strong tilt and a
   nonlinear focus axis. Across 32 fixed seeds, recovered sign must be correct
   on every nonzero dose, median magnitude must be 0.80–1.20x truth, and the
   dose-response slope must be 0.80–1.20. The actual readings at the fully
   present ±2-frame doses are recorded; no comparison to physical truth is
   inferred from nominal plant size alone. Plant: invert the `v^2` coefficient
   at extraction; sign recovery must go RED.
3. **E3, tilt/nonlinearity null.** Zero-curvature response cubes sweep tilt and
   quadratic/cubic frame-axis distortion; `|Q_H| <= 0.10`. Plant: replace the
   registered model by affine-plus-radius-squared; at least one case must go
   RED.
4. **E4, flat/no-focus control.** Pure-noise curves must yield fewer than 2%
   valid sites and no scorable surface. Plant: bypass the peak-reality gate;
   the check must go RED. This is also the mandatory flat-ROI control.
5. **E5, aperture-width control.** With identical planted `Q_H=1`, response
   widths 2, 4, and 8 frames must retain the sign and stay within 20% of the
   narrow-width reading; the estimated interval may widen. Plant: couple
   reported peak position to response width; the equality check must go RED.
6. **E6, centre/axis invariance.** Translating the synthetic optical centre by
   0.3 half-heights must move `Q_H` by less than 0.02 frame. Plant: drop the
   constant/linear nuisance terms; the check must go RED.
7. **E7, ladder verdict.** A fixed mock ladder containing a material positive
   rung and a negligible rung must return NOT ROBUST. Plant: inspect only the
   primary rung; the check must go RED.
8. **E8, RAW contract and checker.** As superseded by Amendment A1, Rust
   `strehl probe --limit 1` and rawpy must match the fixed decoder relation:
   4688 rows in both, rawpy's visible width exactly four columns below Rust's
   7032-column active area, black 512 in both, and usable/container whites
   15360/16383. Two rawpy reads must have byte-identical visible mosaics. Plant
   a wrong CFA/dimension relation in memory and require rejection.
   Separately, the final checker self-test changes the deciding number and
   verdict in an in-memory report string; both mutations must go RED.

The external E1 predicate discharges the cancellation warning: its input and
answer existed before this lane and were not generated by the code under test.

## 7. Falsification and confounds

* **Sensor/target tilt:** fully absorbed by affine terms and tested by E1/E3.
* **Nonuniform focus step / perspective:** absorbed as a polynomial along `u`;
  polynomial-degree ladder must not flip the verdict.
* **Target warp or relief:** cannot be separated from optics on one capture.
  A lens claim requires same-sign target replication; disagreement is NOT
  ROBUST, not averaging.
* **Depth of field:** f/5.6 is primary; f/8/f/11 and E5 test masking.
* **Focus breathing / moving texture:** fixed field coordinates are required
  for an optical field measurement, but moving texture can shift the response.
  A circular spatial shift of site curves by one-quarter frame width preserves
  all marginal curves while destroying lens-centred correspondence; it must
  reduce a detected `|Q_H|` below 50% or the finding is labelled spatially
  nonspecific and NARROWED.
* **IBIS:** on in every stack and can add frame motion. It cannot create a
  repeatable even field term by itself, but it inflates peak noise and is named
  as a limitation.
* **Astigmatism:** this estimator recovers only the mean even cross-track
  focus surface; sagittal/tangential separation remains C7. No full 2-D bowl
  is claimed without that assumption.
* **Selection bias:** sites are gated on curve reality before spatial fitting;
  no statistic is evaluated only "at the best image frame".

### Declared bias directions (rule 18)

| bias | direction it can fool `Q_H` | defence |
|---|---|---|
| fitting only an affine tilted plane | **up**, falsely favours C5 | nonlinear `u` terms; E1/E3 |
| target warp/coin relief | **up or sign-changing**, falsely favours C5 | independent-target ladder; no absolute pooling |
| wider aperture gives narrower response peaks | **up in precision**, can favour f/5.6 | aperture-width E5 and aperture ladder |
| stopping down broadens peaks | **toward zero / unresolved**, can kill C5 | report validity and interval, never set failed sites to zero |
| argmax over noise | **up in apparent confidence**, favours C5 | fourth-difference noise, prominence/fit/replicate gates, E4 |
| fixed sensor sites see shifted texture | **up or down** | large support and spatial-shift placebo |
| Huber rejection of real edge curvature | **toward zero**, against C5 | equal weights, ordinary least-squares sensitivity |
| assuming a radially symmetric bowl | **up in generality** | report cross-track coefficient; do not claim C7 |

The declared prior preference is **against caching a profile**: a clean
same-sign bowl is the satisfying result and therefore the one most likely to be
manufactured by tilt leakage or target shape. Ambiguous evidence will narrow,
not survive, C5.

## 8. Read-only and publication checks

Before and after measurement, `Get-ChildItem -Force -File -Recurse` records
file count, ARW count, total bytes, and newest write time for every capture
root. Every generated file goes under this lane's `out/`.

The final checker is independently implemented: it reads the committed
per-site peak table and output JSON, rebuilds the primary design matrix without
importing the fitter, verifies the deciding number and interval/ladder
classification, pins all report numbers, and checks that no capture path was
written. Its own mutations are commissioned before it is trusted.

The report must state what changes in real Rust modules. A SURVIVE result can
justify a depth-only calibration in `crates/strehl-core/src/optics.rs` and a
future subtraction at depth export; it cannot justify changing image election
in `pyramid.rs` or `merge.rs`. A non-robust or killed result changes no Rust and
must say why.

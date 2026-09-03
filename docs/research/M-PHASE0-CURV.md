# M-PHASE0-CURV — tilt-separated field-curvature census

VERDICT: NARROWED

DECIDING_Q_H_FRAMES: 0.316961 [0.078558, 0.543411]

**Claim:** C5, field curvature as contamination of a future metric-depth
product.
**Capture:** `8-tilted-planar`, f/5.6, 120 frames.
**Statistic:** cross-track edge-minus-centre focus offset at one half-image
height, after a cubic nuisance fit along the tilted planar depth axis.
**Primary class:** DETECTED-SMALL (395 valid sites, 17 occupied bootstrap
blocks; deterministic 2,000-draw block-bootstrap 95% interval).

## 1. Committed verdict

The widest-aperture planar ruler has a small positive cross-track term:
`Q_H = +0.316961` native frame with 95% CI `[+0.078558,+0.543411]`. It clears
the registered quarter-frame detection bar, but not the half-frame MATERIAL
bar.

It does not replicate:

* the same composition at f/8 reads `+0.047308 [-0.265968,+0.261226]`;
* at f/11 it reads `-0.119684 [-0.956738,+0.184732]`;
* the independent flat ruler reads
  `-0.235769 [-0.634028,+0.192562]`;
* the dime reads `+1.165698 [-8.326319,+8.362806]`.

All four are UNRESOLVED. No rung is a contrary detection, so the registered
MATERIAL-to-NEGLIGIBLE/sign-flip definition of NOT ROBUST is not met.
Nevertheless, SURVIVE requires a MATERIAL primary plus same-sign aperture and
target detections, and KILL requires all aperture rungs NEGLIGIBLE. Neither
replication bar is met. The registered spatial placebo also fails badly
(§7). The verdict is therefore **NARROWED**, not SURVIVE, KILL, or NOT ROBUST.

The deciding values are in
`experiments/M-PHASE0-CURV/out/results.json`; the 2,000 bootstrap samples and
the complete 651-site table are in that JSON and
`out/primary-f5p6-peaks.csv`. The result JSON SHA-256 at report time is
`4bfed7175e2bb4f54570194e4ba7b8bac06025eb6fb108b13dc9592ff329389a`.

## 2. The dispatch summary was not C5's actual claim

The proposal says that per-pixel selection already absorbs field curvature
for **image output**
(`docs/proposals/2026-08-sota-path.md:1166-1169`). C5 instead says a future
A5 focus field contains scene depth plus the lens focal-surface bowl, so a
metric depth TIFF, normals, and millimetre reshoot advice would inherit that
bowl (`:1168-1179`).

That distinction matches the code:

* the default merge is already local, with per-band/coefficient selection in
  `crates/strehl-core/src/pyramid.rs`;
* the estimator stores a per-pixel `FocusStats::best_index` in
  `crates/strehl-core/src/merge.rs:867-870,960-961`.

This lane therefore did **not** ask whether one global frame is sharp. It
asked whether a lens-fixed even cross-field term remains after allowing a
tilted flat target and a nonlinear frame-to-depth map.

## 3. Corpus search before decode

The search covered `docs/research/` and `experiments/` under `field
curvature`, `focal surface`, `planar focus`, `sensor tilt`, `target tilt`,
`bowl`, and spelling variants. The existing commissioned prior-art search
tool was first made to pass both its positive fixtures and negative subject.
No commissioned, non-retracted report had this lane's tilt-separated
cross-track statistic.

The closest evidence was non-dispositive:

* `F-camera-lens-optics.md` §6.5 argues that local image election needs no
  curvature model, but does not measure a depth-product bowl.
* `M-PHASE0-ZFIELD.md` commissions peak uncertainty/coherence on unaligned,
  non-planar cubes; it does not fit a planar bowl.
* `M84-ruler-metrology.md` and `M84b-ruler-metrology.md` disagree on ruler
  metrology. M84b's independent implementation caught a coordinate error,
  making independent checking mandatory here.
* `BUILD-CHROMA.md` reports only an underpowered blue-versus-green radial
  trend; its later depth-dependent estimator failed controls.

The preregistration, corpus account, bars, declared bias directions, roster,
and decoder amendments were committed before outcome response measurement in
`experiments/M-PHASE0-CURV/PREREGISTRATION.md`.

## 4. Instrument and tilt separation

For each RAW, `measure.py` copies rawpy's visible CFA mosaic inside the
decoder context, retains G1 and G2 separately, subtracts black 512, and
2-by-2 area-averages each green lattice. It evaluates a fixed 31-by-21 grid:

```text
R = box17(Sobel_x^2 + Sobel_y^2) / max(box17(signal), 32 DN)^2
```

No demosaic, tone curve, merge, alignment, or selected image enters the
statistic. Filenames were verified to run in nondecreasing EXIF
`FocusDistance2` order.

The robust affine peak surface first estimates the planar-gradient direction.
Coordinates are rotated to `u` along that direction and `v` across it, with
both coordinates measured in half-active-image heights. The registered fit is

```text
k = b0 + b1*u + b2*u^2 + b3*u^3
       + b4*v + b5*u*v + b6*u^2*v + q*v^2.
```

The arbitrary nonlinear focus-step/perspective relation is absorbed along
`u`; sensor/target tilt is linear; odd cross terms permit direction drift.
The identified `q*v^2` is even and cross-track, so a tilted flat plane passed
through any one-dimensional focus map cannot generate it. `Q_H=q` is the
edge-minus-centre offset at `|v|=1`. Optical-centre translation changes only
constant/linear terms, not `q`.

Sites were accepted before reading a surface residual: interior peak, concave
seven-point log quadratic, vertex inside the fit, adjusted R² at least 0.80,
prominence at least 6 curve-noise sigma, G1/G2 agreement within 3 frames,
local clipping below 0.1%, and signal above 32 DN. A stack also needed 180
sites, 12 of 20 spatial blocks, 30 sites on each side, and cross-track span
1.2. `curvlib.py`, `measure.py`, and `analyse.py` are the executable
specification.

## 5. Commissioning

The final suite is **10/10 controls GREEN and 12/12 planted defects RED**.
`out/commission.json` has every predicate and reading; its report-time
SHA-256 is
`dba7e36ccf10298d629bbd5021895d4dad6dc4b804980eccd8839940499a6d40`.

| control | unmodified reading | planted defect and RED reading |
|---|---|---|
| E1 external, cancellation-immune M84b plane | `Q_H=+0.001419` | affine-plus-radius leakage `-3.875761` |
| E2 known dose ladder | ±2-frame full doses read `-2.000135/+1.999944`; slope `1.000016` | inverted coefficient read `-1.998695` on positive dose |
| E3 tilt/nonlinear-axis null | three nulls `+0.000461,-0.000217,+0.000002` | affine-radius leakage `+0.852623,+1.090647,+0.929568` |
| E4 pure noise | `0/651` sites valid | bypass admitted `651/651` |
| E5 response width | planted +1 read `1.002410,0.999131,1.003699` at widths 2/4/8 | production width-coupling plant read `2.872472` |
| E6 centre translation | `1.000827` versus `1.009002` | dropping linear protection read `42.643934` |
| E7 production verdict path | contradictory fixed ladder => NOT ROBUST | primary-only path => SURVIVE |
| E8 decode + independent checker | fixed Rust/rawpy contract and all checker mutations rejected | wrong active dimension, stale number, flipped verdict all RED |
| E9 2-D response | fixed in-focus frame 7 recovered; response strictly decreased over eight blur doses | frame-axis Sobel peaked at frame 6 |
| E10 fitted cross-track support | 195 sites, 15 blocks, fitted-`v` span `2.52`, 91 sites per side passed despite smaller sensor-axis span `1.00` | treating sensor-axis span as a lower bound returned false |

E1 is the required cancellation-immune predicate. Its input and answer were
created by M84b code that this lane neither imports nor modifies, pinned by
SHA-256
`745bbbcedb3da04842740a88a01ce21109a75393dcc371804d62874c63973d69`.

The first E8 run correctly went RED because Rust reports `7032x4688` and a
usable white of 15360, whereas rawpy exposes `7028x4688` and container white
16383. The exact failed artifact is preserved as
`out/commission-initial-red.json` (SHA-256
`d1814a701433a799f1e83bad6e9e607115d16b7b16da7c55f39b3060c41c7267`);
Amendment A1 froze the four-column contract before any response measurement.
Amendment A2 added the synthetic-image response control after an audit found
that response-curve controls did not exercise Sobel axis isolation.

## 6. Real-capture census

All intervals are deterministic 2,000-draw 5-by-4 spatial block bootstraps.
`n` is the number of pre-model valid sites.

| stack | frames | n | Q_H frames [95% CI] | registered class |
|---|---:|---:|---:|---|
| tilted ruler f/5.6 | 120 | 395 | `+0.316961 [+0.078558,+0.543411]` | DETECTED-SMALL |
| tilted ruler f/8 | 85 | 422 | `+0.047308 [-0.265968,+0.261226]` | UNRESOLVED |
| tilted ruler f/11 | 65 | 504 | `-0.119684 [-0.956738,+0.184732]` | UNRESOLVED |
| flat ruler f/5.6 | 79 | 648 | `-0.235769 [-0.634028,+0.192562]` | UNRESOLVED |
| dime f/5.6 | 207 | 599 | `+1.165698 [-8.326319,+8.362806]` | UNRESOLVED |
| grid 1, step 1 | 91 | 639 | `-0.344699 [-1.733895,+1.213831]` | UNRESOLVED |
| grid 1, step 4 | 55 | 651 | `-0.159713 [-0.842402,+0.569289]` | UNRESOLVED |
| grid 1, step 10 | 23 | 651 | `-0.098090 [-0.421483,+0.271571]` | UNRESOLVED |
| grid 2, step 4 | 46 | 651 | `-0.194658 [-0.860990,+0.568827]` | UNRESOLVED |
| grid 2, step 10 | 27 | 651 | `-0.104855 [-0.419763,+0.237931]` | UNRESOLVED |

The calibration grids remain diagnostic: their clear film over paper can
create two depth layers. None is treated as a clean optical replication.
Every response cache has a SHA-256 in its corresponding
`out/*-measure.json`; every peak table hash is in `out/results.json`.

## 7. Attempts to break the primary

| ladder | Q_H [95% CI] | result |
|---|---:|---|
| `u` degree 2 | `+0.310140 [+0.074907,+0.512094]` | DETECTED-SMALL |
| degree 3, primary | `+0.316961 [+0.078558,+0.543411]` | DETECTED-SMALL |
| degree 4 | `+0.355900 [+0.102006,+0.632901]` | DETECTED-SMALL |
| half-height centroid | `+0.291141 [-0.042377,+0.563980]` | UNRESOLVED |
| central 80% | `+0.140472 [-0.244100,+0.493849]` | UNRESOLVED |
| full registered field | `+0.316961 [+0.078558,+0.543411]` | DETECTED-SMALL |
| G1 only | `+0.307311 [+0.050090,+0.525442]` | DETECTED-SMALL |
| G2 only | `+0.351273 [+0.148587,+0.582179]` | DETECTED-SMALL |
| ordinary least squares | `-0.108829 [-1.284622,+1.285371]` | UNRESOLVED |

The central 60% had 186 valid sites but only 10 occupied blocks and span
1.19, below the registered 12-block/1.2 gates, so it is UNSCORABLE rather than
zero. The detection therefore appears only when the outer registered field is
included. The two green lattices and polynomial degrees agree, but the
alternate peak loses detection and OLS is noisy with the opposite point sign.
The primary robust fit downweights 21.8% of sites and has residual RMS 1.650
frames (95th absolute residual 1.048), another reason not to promote a
0.32-frame term to a lens profile.

The preregistered circular eight-column (one-quarter-width) spatial shift did
not suppress the result. It produced `Q_H=+22.397291
[+1.827118,+38.021160]`, 70.66 times the primary magnitude. Circularly
wrapping a scene with a strong horizontal depth gradient creates a
discontinuity, so this reading is not a physical curvature estimate. It is
nevertheless a decisive **failed placebo** under the frozen rule: the small
primary cannot be labelled lens-centred, and the lane remains NARROWED.

The first post-decode analysis attempt also stopped before writing
`results.json`: the placebo tried to roll three stale peak-shape keys that the
peak table did not export. The repair restricted the roll to actual
curve-derived fields and the full deterministic analysis was rerun. A later
audit found E7's conceptual mock had not called the production verdict
function and the first checker only echoed the JSON verdict. Before filing,
the decision tree was moved into `curvlib.py`, E7 commissioned that exact
path, and `check_results.py` independently reimplemented classification,
ladders, and the lane decision. At that stage the suite remained 9/9 and
11/11.

A final read-only verifier then found that P5's first implementation planted a
spatial `v^2` offset directly instead of invoking the production
`width_coupling` defect hook. Before filing, P5 was repaired to exercise that
exact registered mechanism; it still went RED at `2.872472`. The same audit
removed an unnecessary coordinate-span pre-gate (the registered fitted-`v`
span remains enforced) and added an independent regeneration of every
bootstrap resample. These repairs changed neither the deciding number nor any
real-data classification.

The verifier correctly noted that the repaired support gate itself still
lacked a plant. E10/P12 now commission the exact production gate on a fixed
point cloud whose fitted cross-track span is `2.52` although its smaller
sensor-axis span is only `1.00`; reinstating the defective proxy goes RED.
That brings the final suite to 10 controls and 12 plants.

## 8. Read-only and independent checks

`snapshot.ps1 before` and `after` independently inventoried the four capture
roots with `Get-ChildItem -Force -File -Recurse`. File count, ARW count, total
bytes, and newest write time match exactly. The measured inventory is 798
ARWs and about 35.6 GB across the four roots; no capture file was written.

`check_results.py` does not import `curvlib.py`. It independently:

1. rebuilds the Huber design from `primary-f5p6-peaks.csv`;
2. independently regenerates all 2,000 spatial-block resamples and their
   percentile interval (maximum sample difference `0.0`);
3. reclassifies every stack and sensitivity;
4. rebuilds all ladder flips and the lane decision;
5. pins the report verdict/deciding number; and
6. compares the before/after capture inventories.

The all-GREEN reading is preserved in `out/check-final.json`.

Tool versions: Python 3.12.10, NumPy 2.4.4, SciPy 1.17.1, rawpy 0.27.0,
ExifTool 13.58.

## 9. What changes in Rust

**Nothing changes in Rust as a result of this verdict.**

Specifically:

* do **not** add a focal-surface coefficient to
  `crates/strehl-core/src/optics.rs::OpticalProfile`;
* do **not** change local image election in
  `crates/strehl-core/src/pyramid.rs` or
  `crates/strehl-core/src/merge.rs`.

The first prohibition follows from the evidence: only one estimator on one
aperture detects a small term, no aperture or independent planar target
replicates it, the detection needs the outer field, and the spatial placebo
fails. Caching this as lens data would turn target shape, focus breathing, or
estimator sensitivity into a permanent calibration. The second prohibition
follows from C5 itself: per-region image election already absorbs curvature.

This lane is still useful as a constraint on future A5/C5 work. A metric depth
export must carry an *uncalibrated focal-surface systematic* rather than claim
that the current optical profile removes it. A future profile change needs a
new rigid planar capture with independently certified flatness, alignment or
feature tracking to separate breathing, repeat apertures, and a non-wrapping
spatial placebo.

## 10. What was not verified

* The detected `+0.32` frame term could not be attributed uniquely to the
  lens rather than target micro-relief, breathing through fixed sensor sites,
  IBIS motion, or robust-fit/outlier behaviour.
* Target flatness was not independently surveyed in physical units. The dime
  in particular is not a clean full-field plane despite the proposal's
  shorthand.
* Frame index was not converted to micrometres; EXIF distance is too
  quantised for that job, and M84b's ruler calibration was used only as an
  external null predicate.
* This estimates one mean even cross-track coefficient. It does not separate
  sagittal/tangential surfaces, astigmatism, a general two-dimensional bowl,
  or aperture-dependent pupil effects.
* No future A5 depth exporter exists to test end to end, and no claim is made
  about visual image quality.

## 11. Reproduction

From the repository root in PowerShell:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONPATH = (Get-Location).Path
python experiments/M-PHASE0-CURV/src/commission.py
python experiments/M-PHASE0-CURV/src/measure.py
python experiments/M-PHASE0-CURV/src/analyse.py
python experiments/M-PHASE0-CURV/src/check_results.py
```

The RAW command is intentionally expensive and refuses to overwrite caches
without `--force`. The committed response caches let the last two commands
reproduce the result without touching capture pixels.

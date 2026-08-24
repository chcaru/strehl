# M84b — pre-registration: physical ground truth from the ruler stacks

**Frozen before any plane fit, magnification estimate, focus-axis calibration,
depth map, or M5 cross-check was computed.** Committed in its own commit, ahead
of every primary result, per the dispatch.

Every claim in this file is labelled **MEASURED**, **DERIVED** or **ARGUED**.
Numbers taken from other milestones are namespaced ("M5's fact 27"), never bare.

---

## 0a. Stem disclosure — a live two-claimant collision on `M84`

**MEASURED.** At the moment of freezing, **two agents are live on this
milestone**, both dispatched with the same brief:

| agent id | registry name | model | uptime at discovery | state |
| --- | --- | --- | ---: | --- |
| `6f883d30-d01b-457c-a3bc-dca64462ecef` | `M84` | gpt-5.6-sol | 1084 s | live; committed `f6ee015 Preregister M84 ruler metrology` at 23:22:00 and was writing `src/analyse_control.py` at 23:27:13 |
| `7a2b1be4-4c9a-41ec-9ece-497e9d505153` | `M84b` | claude-opus-5 | 953 s | live; this document |

**MEASURED.** `AGENTS.md`'s milestone ledger records the `M84` row as
`live (7a2b1be4, relaunched on claude-opus-5)`, and my own dispatch states that
an earlier agent "stood down after about a minute". **Neither is true of
`6f883d30`, which is still running and has already committed to
`experiments/M84-ruler-metrology/`.** This is rule 41's failure mode with two
*live* claimants rather than two sequential ones, and rule 27's third trap
inverted: a stand-down was assumed to be an observation.

**ARGUED resolution, adopted unilaterally by me to avoid clobbering.**
`6f883d30` keeps the `M84` stem, because it committed first.
I take the `M84b` stem, which is the name the agent registry already gives me,
and write **only** to `experiments/M84b-ruler-metrology/` and
`docs/research/M84b-ruler-metrology.md`. I notified `6f883d30` of the boundary
and of three reconnaissance findings before freezing this. I have **not** read
its analysis code or its results, and I will not, until my own numbers are
published; the cross-check against it is stated in my report with the time it
was made.

**ARGUED.** This is a better outcome than one agent. Rule 12 says the author
never verifies their own work, and rule 24 says a verifier must *re-choose*
rather than recompute. Two independent designs on the same physical target, by
two different models, is exactly that. Our methods differ materially: `M84`
fits a full 2-D metric homography and solves for focal length from the
homography's orthogonality constraints; `M84b` fits a 1-D projective law to the
graduation lattice and closes the absolute scale by transferring the tick length
from the flat-on stack. Agreement would be strong. Disagreement is stronger.

---

## 0b. Reconnaissance already performed, and therefore not blind

**MEASURED disclosure.** This is not a blind pre-registration. Before freezing,
M84b ran five reconnaissance steps against the two stacks. They are declared
here in full so a reader can discount anything that looks chosen after the fact.
The scripts are `src/00-preview.py`, `src/01-recon.py`, `src/02-recon-ticks.py`,
`src/03-build-cache.py` and `src/04-recon-index.py`; their logs are in `out/`.

What was known at freeze time:

| # | Reconnaissance observation | Value seen |
| --- | --- | --- |
| R0 | Both stacks decode; quad-grid green plane | `3514 x 2344`, black 512, white 16383 |
| R1 | `flat-on-ruler-cpl` EXIF is uniform | 79 frames, ISO 100, f/5.6, 200 mm, 0.3 s, `FocusDistance2` 0.2707-0.2771 m |
| R2 | `highly-angled-ruler-mm-cpl` EXIF is uniform | 299 frames, ISO 100, f/5.6, 200 mm, 1/4 s, `FocusDistance2` 0.2707-0.3000 m |
| R3 | Flat-on tick comb period, four row bands, frame 19 | `270.31` quad px by FFT; `269.5` median gap by direct dark-run centroids over 14 runs |
| R4 | Flat-on tick-height hierarchy, eyeballed on a preview | a taller tick about every 5 minors, the tallest about every 10 |
| R5 | Angled stack local tick period in the in-focus band | falls from about `176` to about `59` quad px as the band marches right |
| R6 | Angled stack in-focus band marches monotonically | sharpest 128-quad-px tile column 13 -> 18 over frames 0 -> 298 |
| R7 | Angled focus-index map | a smooth left-to-right ramp over roughly `x in [1520, 2640]` quad px, plus an occluder near `x 1080-1600 / y 1040-1760` and a separate bright surface across the bottom |
| R8 | Flat-on focus-index map and tile argmax | broadly uniform with a systematic gradient; sharpest tile moves `(0,1)` at frame 19 to `(6,26)` at frame 39, i.e. **the flat-on target has real residual tilt** |
| R9 | Frame mean rises across the angled sweep | `1414.7` to `2051.7` DN, a 45 % brightening |

**ARGUED.** R3 and R4 make the pitch inference in §3 non-blind in the sense that
the *scale* is already known to about a part in a thousand. The pitch decision
rule in §3 is nevertheless registered here **before** the physical pitch is
committed to, and its falsifier is an external constant the reconnaissance never
touched: the lens's maximum magnification.

**MEASURED.** Nothing under `D:\personal\macro` was written to. All reads use
the rule-32 idiom: `raw_image_visible` is copied inside the `with` block on the
same line.

---

## 1. Scope, ownership, and what is used as the focus operator

**MEASURED.** M84b owns `experiments/M84b-ruler-metrology/` and
`docs/research/M84b-ruler-metrology.md` only. It does not modify anything under
`crates/`, which M82 holds; nor `experiments/M84-ruler-metrology/`, which
`6f883d30` holds; nor `docs/research/SYNTHESIS.md`, `AGENTS.md` or
`docs/captures-needed.md`, which the orchestrator holds.

**ARGUED.** The focus response used here is **implemented in Python inside this
experiment**, not invoked from the `strehl` binary. The reason is that the
quantity M84b needs is a *per-graduation, spatially aggregated* through-focus
curve, which the CLI does not emit, and because rule 4 forbids leaning on a raw
per-pixel argmax. The operator is a normalised squared-gradient response,
box-smoothed, defined in `src/` and restated in the report. M84b therefore does
not inherit, and does not test, the shipped operator's calibration.

---

## 2. Stacks, N, ROIs and flags

**MEASURED.** All inputs are read-only. Frames are filename-sorted. No frame is
excluded except where a registered validity rule below excludes it, and every
such exclusion is reported with its count.

| Role | Stack | N | ISO | Marked N | Focal length |
| --- | --- | ---: | ---: | --- | --- |
| **Control, run FIRST** | `D:\personal\macro\flat-on-ruler-cpl` | 79 | 100 | f/5.6 | 200 mm |
| Primary | `D:\personal\macro\highly-angled-ruler-mm-cpl` | 299 | 100 | f/5.6 | 200 mm |

**MEASURED.** Working representation: the quad-grid green plane, `(G1+G2)/2`,
black-subtracted, `3514 x 2344`. One quad pixel spans **two** sensor pixels in
each axis. Every length in this document is in **quad px** unless it says sensor
px or µm.

**ROIs, frozen here.**

| Tag | Stack | ROI, quad px `x0,y0,w,h` | Purpose |
| --- | --- | --- | --- |
| `F-COMB` | flat-on | `0,1980,3514,364` | The full-width minor-tick comb near the bottom edge |
| `F-TALL` | flat-on | `0,1100,3514,880` | The band where only the 5 mm and 10 mm ticks reach, for the height hierarchy |
| `A-RULE` | angled | `1100,900,1900,900` | The band carrying the graduated face across the depth ramp |
| `A-WIDE` | angled | `0,0,3514,2344` | Whole frame, for the validity mask and the depth map only |

**ARGUED.** `A-RULE` is set from R7's index map, which showed the ramp between
about `x = 1520` and `x = 2640` quad px. The registered ROI is deliberately
wider than that on both sides, so the fit is not trimmed to the region that
already looked good.

**Non-default flags.** None; no `strehl` binary is invoked for any registered
result. Python 3.12.10, numpy 2.4.4, scipy 1.17.1, rawpy 0.27.0, exiftool 13.58.

**Constants imported from the corpus, with provenance read at its own file.**

| Symbol | Value | Source |
| --- | --- | --- |
| sensor pixel pitch | **5.12 µm ± 0.3 %** | `docs/research/F-camera-lens-optics.md:91` and `:1171`; DERIVED as 35.9 mm / 7008 px, sensor width UNVERIFIED at ±0.3 % |
| lens maximum magnification | **1.4x native, 2.8x with SEL20TC** | `docs/research/F-camera-lens-optics.md:13`, labelled VERIFIED |
| bellows composite | **B = 1 + m/p ∈ [2.41, 3.06]** | SYNTHESIS fact 27, from M5 |
| EXIF `FNumber` is the marked aperture | not bellows-corrected | SYNTHESIS fact 28, from M5 §7 |

**ARGUED.** The pixel pitch is the single largest imported uncertainty in the
magnification result and it is itself DERIVED, not measured. Its ±0.3 % is
carried through every metric number M84b publishes and is stated **separately**
from M84b's own statistical error, so a later measurement of the sensor width
can rescale M84b's numbers without re-running anything.

**ARGUED correction to my own dispatch, registered before measuring.** The
dispatch describes the rig as "the Sony FE 100mm F2.8 Macro GM with a 2x
teleconverter", which is right, but the corpus records the lens as **1.4x
native**, not 1:1 (`F-camera-lens-optics.md:13`, VERIFIED). The ceiling is
therefore **2.8x, not 2.0x**. This matters because it is the falsifier in §3.

---

## 3. The graduation pitch: measured, then decided by a registered rule

**ARGUED.** The dispatch forbids assuming the pitch. M84b therefore measures the
tick spacing in the image, enumerates candidate physical pitches, and decides
among them by a rule frozen here.

### 3.1 How graduations are located

1. Within `F-COMB`, average rows to form a 1-D profile `I(x)` for each of a
   registered set of row bands.
2. Estimate a slowly varying background `B(x)` by a 601-quad-px median filter,
   and form the darkness `D(x) = max(B(x) - I(x), 0)`.
3. Detect tick supports as maximal runs of `D(x)` above 35 % of the local
   maximum over a ±200 px window; require a run length of at least 8 quad px.
4. Take each tick's position as the **darkness-weighted centroid** of `D(x)`
   over its run, extended symmetrically to the run's half-maximum crossings.
5. Discard any run touching the ROI boundary.

Report, per band, the number of ticks, the median inter-tick gap, and the robust
scatter of the residual to a straight line in tick index. Registered bar: §7.

### 3.2 Candidate pitches and the decision rule

**Registered.** Candidates are `P ∈ {0.5, 1.0, 2.0} mm`. For each, the implied
magnification is `m = pitch_image_µm / (1000 * P)`, with
`pitch_image_µm = pitch_quad_px * 2 * 5.12`.

A candidate is **REFUTED** if it implies `m > 2.8`, the lens's VERIFIED maximum
with the SEL20TC (`F-camera-lens-optics.md:13`), or `m < 0.1`.

Among surviving candidates the decision is made by the **tick-height
hierarchy**, measured in `F-TALL` and `F-COMB`:

- For each minor tick index `k`, measure the tick's vertical extent.
- Compute the index period of the *longest* ticks, `Q_long`, and of the
  intermediate ticks, `Q_mid`.
- **Registered rule.** On a metric rule the longest ticks are the centimetre
  marks. Therefore the minor pitch is `P = 10 mm / Q_long`. Accept that value if
  and only if it is one of the surviving candidates, `Q_long` is an integer
  within ±0.15, and `Q_mid` is `Q_long / 2` within ±0.15.
- If the hierarchy is not clean, the pitch is reported **UNDECIDED** and every
  downstream metric number is published as a family indexed by `P`.

**ARGUED.** This rule is decisive between 1 mm and 2 mm, which the magnification
bound alone is not: a 1 mm rule carries its longest mark every 10 minors, and a
2 mm rule would carry it every 5.

**Falsifier the reconnaissance could not have rigged.** `P = 0.5 mm` implies
`m ≈ 5.5`, roughly twice the lens's mechanical maximum. If the tick period had
come out at half the observed value, the 2.8x ceiling would have refuted the
obvious candidate. That is the sense in which this rule has power to reject.

---

## 4. Geometry: the plane fit, and how convergence is decided

### 4.1 Model

**DERIVED.** For a plane viewed by a perspective camera, and for graduations
equally spaced by `P` along a straight line on that plane, the image abscissa of
graduation `k` obeys a one-dimensional projective law

```text
x(k) = (A + B k) / (1 + C k)
```

with `A` the near-end position, `B` proportional to the near-end image pitch, and
`C` the fractional depth change per graduation. Writing `u` for the object
distance from the front principal plane,

```text
u_k / u_0 = 1 + C k        MEASURED, dimensionless, needs no closure
C         = P sin(theta) / u_0
|B|       = m_0 P cos(theta)      in image length units
```

where `theta` is the angle between the ruler's long axis and the plane normal to
the optical axis. `theta = 0` is fronto-parallel.

**ARGUED, and this is a correction to my dispatch, registered before measuring.**
The dispatch says "a plane's depth is affine in image coordinates". That holds
for an affine camera; under perspective it is **inverse depth** that is affine.
R5 saw the local tick period fall about 3x across the ruler, and the projective
law gives `dx/dk ∝ 1/u^2`, so the difference is not negligible here. M84b fits
the projective form and **reports the affine form's error** rather than assuming
either.

### 4.2 Fitting and convergence

**Registered.** Fit `A, B, C` by Huber IRLS on the tick centroids, Huber constant
`1.345 * sigma_MAD`, initialised from the linear (`C = 0`) solution.

**Convergence is declared** when the relative change in every parameter falls
below `1e-10` between successive iterations, within at most `200` iterations,
from at least **three** distinct initialisations that must agree to `1e-6`
relative. Non-convergence, or disagreement between initialisations, is reported
as a failure and blocks the depth map.

**Uncertainty** on `A, B, C` is a **1000-sample bootstrap over ticks**, not the
linearised covariance, because the residuals are not assumed Gaussian.

### 4.3 The zero-tilt control, run FIRST

**Registered.** `flat-on-ruler-cpl` is analysed **before** the angled stack and
its result is reported whatever it says.

- Fit the same projective model to the flat-on comb.
- A fronto-parallel target has `C = 0`.
- **Registered bar Z1.** `|C_flat|` must be at least **5x** smaller than
  `|C_angled|`. If it is not, the method cannot tell a flat target from a steeply
  tilted one, and **no ground-truth claim is made from either stack**.
- **Registered bar Z2.** The implied flat-on tilt must satisfy
  `|theta_flat| < 15 deg`.
- **Registered bar Z3.** A pure constant-pitch (similarity) model must fit the
  flat-on comb with residual RMS below the §7 `L1` bar. If a fronto-parallel
  target needs a projective term to fit, the tick localiser has a systematic and
  every downstream number inherits it.

**ARGUED, and deliberately different from the sibling M84's bar.** Z2 is set at
15 deg, not at a few degrees, and Z1 is a **ratio** rather than an absolute.
The target was hand-placed, not optically aligned, and R8 already shows real
residual tilt on it. The dispatch's requirement is that the method *recognise*
a flat target; it is not that the owner achieved optical alignment by hand. A
bar that demands the latter reports a false negative on a usable capture. The
measured flat-on tilt is reported as a number either way.

### 4.4 Planarity, and what would refute it

**Registered.** After the projective fit on the angled stack, test the residuals
for structure:

- residual autocorrelation at lag 1 over tick index;
- the ratio of the residual's 5-tick moving-average amplitude to its
  high-frequency scatter.
- **Registered bar P1.** If that ratio exceeds **3.0**, the target is declared
  **not planar** at the accuracy claimed, and the depth map is published only
  with the empirical residual folded into its uncertainty, or withdrawn.

### 4.5 Are the two stacks the same physical ruler?

**Registered check S1.** The absolute closure in §5 requires it. Compare the
tick-height hierarchy `(Q_long, Q_mid)` and the ratio of tick length to tick
pitch between the two stacks. If they disagree by more than 5 %, the closure is
withdrawn and §5's fallback is used instead.

---

## 5. Magnification, and the absolute closure

### 5.1 Magnification at the subject, flat-on

**Registered primary.** `m_flat = pitch_quad_px * 2 * 5.12 µm / (1000 * P µm)`.

Uncertainty combines, in quadrature and reported separately:

- the bootstrap sd of the fitted pitch across ticks, row bands and a registered
  set of frames;
- the ±0.3 % pixel-pitch systematic imported from
  `F-camera-lens-optics.md:1171`;
- a residual-tilt correction: a flat-on tilt `theta_flat` shortens the apparent
  pitch by `cos(theta_flat)`, so `m` is corrected by `1/cos(theta_flat)` and the
  correction's own uncertainty is carried.

**Registered comparison, decided before looking.** The corpus holds **two
different beliefs** about this rig's magnification: SYNTHESIS fact 12 discusses
"a 2x teleconverter at m = 2.8", and SYNTHESIS fact 27 states its conclusion
"with m ≈ 2.0". They cannot both describe one capture. M84b reports which, if
either, its measurement supports, and reports a disagreement as a finding.

### 5.2 The absolute closure, and its fallback

**DERIVED.** The angled fit gives `C = P sin(theta)/u_0` and
`|B| = m_0 P cos(theta)`: two equations in three unknowns `m_0, theta, u_0`. One
more independent quantity closes it. M84b registers the **tick-length aspect
ratio** as that quantity:

1. Measure the physical minor-tick length `L` from the flat-on stack:
   `L = (tick image length) / m_flat`. MEASURED.
2. Measure the near-end tick image length in the angled stack; divide by `L` to
   get `m_0`. MEASURED, conditional on §4.5's check S1.
3. `cos(theta) = |B| / (m_0 P)`; `u_0 = P sin(theta) / C`. DERIVED.

**Registered validity condition for the closure.** It assumes the tilt axis lies
close to the image-vertical, so that the tick-length direction is
unforeshortened. Test: the angled tick *lengths* must scale as `1/(1 + C k)` —
the same `C` the positions gave — to within **5 %** over the fitted range. If
they do not, the tilt axis is not vertical and the closure is **withdrawn**.

**Registered fallback if the closure is withdrawn or fails.** M84b publishes:

- the **assumption-free** results, which need no closure: `u_k/u_0 = 1 + C k`,
  the fractional depth advance per frame `(1/u_0) du/dn`, and the relative depth
  map; and
- the absolute scale only as an interval spanned by `u_0` over an explicitly
  stated range, with every micron figure carried as a family in `u_0`.

**ARGUED.** The fallback is a real result, not a consolation. A relative depth
map exact to a fraction of a percent is already the first physical ground truth
this project has had.

---

## 6. The focus axis in microns per frame

### 6.1 Per-graduation through-focus peak

**Registered.** For each located graduation `k` in `A-RULE`:

1. Form a spatial support around the tick: the tick's own run, dilated by
   ±1 local pitch in `x`, over a registered `y` band of 300 quad px centred on
   the ROI.
2. Compute the response `R(n)` for that support in every frame `n`, as the
   support mean of the normalised squared-gradient operator. **This is a
   spatially aggregated statistic, not a per-pixel argmax** (rule 4).
3. Estimate the peak frame `n*(k)` as the **centroid of `R(n) - median(R)`** over
   the contiguous region above half its maximum, and separately by a 3-point
   parabolic fit at the discrete argmax. Both are reported; the centroid is
   primary.

**Registered placebo.** The same pipeline is run with the frame axis randomly
permuted, fixed seed `0x4d84_0001`. It must destroy the `n*`-versus-`k`
relationship: the registered bar is that the permuted arm's `|Pearson r|` falls
below **0.2** while the real arm's exceeds **0.9**. Rule 39: this is the null the
slope is measured against.

**Registered photometric caution.** R9 showed the angled stack's frame mean
rising 45 % across the sweep. The response is normalised by the local level
squared for exactly that reason, and M84b reports the correlation between the
un-normalised response and the frame mean as a disclosure.

### 6.2 The calibration and the constancy test

**DERIVED.** `du/dn = u_0 * C * (dk/dn) = P sin(theta) * (dk/dn)` µm per frame,
with `dk/dn` the reciprocal slope of `n*(k)`.

**Registered constancy test.** Split the usable frame range into **five** equal
segments; fit `k(n)` within each; report the five local slopes.

- **Declared CONSTANT** if `max/min` of the five segment slopes is `< 1.25`.
- Otherwise report the drift, its sign and its shape, and say so plainly. The
  corpus assumes a constant step in several places and has never checked it
  against physics.

**Registered bar.** The `n*(k)` relation must be monotone over at least 80 % of
adjacent tick pairs, else the focus-axis calibration is withdrawn.

### 6.3 Focus breathing disclosure

**Registered.** Each tick's position is taken in its **own** best-focus frame,
which is the physically meaningful position. As a by-product M84b reports the
drift of a fixed tick's position between the first and last frames, which is the
corpus's focus-breathing magnification drift (rule 6, fact 43) seen directly. It
is reported, not corrected.

---

## 7. Accuracy bars, committed before looking

**Registered.** These decide the VERDICT. They are fixed here.

| Bar | Quantity | Success requires |
| --- | --- | --- |
| **L1** | Tick-centroid residual RMS to the fitted model, flat-on | `< 1.0` quad px, i.e. `< 0.37 %` of a graduation |
| **L2** | Tick-centroid residual RMS to the fitted model, angled | `< 2 %` of the **local** tick pitch at each tick |
| **L3** | Fraction of the `A-RULE` span where ticks localise at all | `>= 50 %` |
| **M1** | Magnification relative uncertainty, statistical only | `sigma_m / m < 1.0 %` |
| **M2** | Magnification relative uncertainty including the imported pixel pitch | reported separately; not a pass/fail bar |
| **D1** | Relative depth `u_k/u_0` uncertainty over the valid mask | `< 0.5 %` |
| **D2** | Absolute per-pixel depth uncertainty, median over the valid mask | `< 25 µm` |
| **Z1, Z2, Z3** | The zero-tilt control, §4.3 | as stated there |
| **P1** | Planarity residual structure, §4.4 | ratio `< 3.0` |

**DERIVED.** The `25 µm` in D2 is about the total depth of field at this rig,
computed as `2 * N_eff * c / m^2` with `c` one sensor pixel and `N_eff` from
M5's fact 27 composite: at `m = 2.8` and `B = 3.06`, `N_eff = 17.1` and
`DoF = 2*17.1*5.12/2.8^2 = 22.3 µm`; at `B = 3.76` (`p = 1` with `m = 2.8`),
`N_eff = 21.1` and `DoF = 27.5 µm`. The bar is set at the midpoint, `25 µm`.
**A depth truth whose uncertainty exceeds the depth of field is not truth.**

### 7.1 What would refute the capture as ground truth

**Registered.** M84b declares the capture **NOT usable for micron-scale truth**,
and reports the resolution limit instead, if any of the following holds:

1. `L2` fails: graduations cannot be located to 2 % of the local pitch.
2. `L3` fails: under half the ruler's extent yields ticks at all.
3. `Z1` or `Z2` fails: the method cannot recognise the flat control.
4. `P1` fails **and** the residual structure exceeds the D2 bar in microns.
5. `D2` fails: the depth uncertainty exceeds the depth of field.

**ARGUED.** Reporting the limit is a complete result. If diffraction at 2x
teleconversion prevents graduation localisation, the number M84b owes the
project is the localisation sigma in microns and the capture that would fix it.

---

## 8. Controls that can fail, and the planted error

### 8.1 Byte-planted geometric mutation

**Registered.** Modelled on
`experiments/M81-estimation-merge/unit_mutation_control.py`. A control script
plants, as **Python byte-strings**, a known geometric error in the analysis
source, verifies the plant **by read-back**, runs the pipeline's self-test,
requires a **non-zero exit**, and restores the source **byte-for-byte**,
asserting equality of the full file bytes afterwards.

Two independent plants are registered, and both must be caught:

- **Plant G1, wrong pitch.** `PITCH_MM = 1.0` becomes `PITCH_MM = 1.1`. The
  self-test's synthetic-scale assertion must reject it.
- **Plant G2, sign-inverted geometry.** The sign of the projective coefficient
  in the synthetic-geometry self-test is inverted. The recovered tilt must then
  disagree with the planted tilt and the self-test must reject it.

**Registered.** The self-test must announce its test count, and a run that
announces zero tests is a failure regardless of exit code (rule 36).

### 8.2 Synthetic positive control with a known answer

**Registered.** Before touching either real stack's geometry, the fitter is
exercised on a synthetic tick lattice generated from known
`(m_0, theta, u_0, P)`, at a noise level matching the measured centroid scatter.
It must recover `theta` to `< 0.5 deg` and `u_0` to `< 1 %`. A fitter that
cannot recover a lattice it was handed has no business fitting a photograph.

### 8.3 A control the reconnaissance cannot have rigged

**Registered.** The lens's 2.8x maximum magnification is an external constant
from `F-camera-lens-optics.md:13`. M84b's magnification measurement is free to
exceed it, and if it does, then either the pitch inference, the pixel pitch, or
the corpus's lens identification is wrong — and M84b says so rather than
choosing the pitch that fits.

---

## 9. Deliverables

**Registered.** `docs/research/M84b-ruler-metrology.md` carrying, in order:

1. A **VERDICT** block: can this capture serve as physical ground truth, and at
   what accuracy, in microns.
2. The stem-collision disclosure of §0a.
3. The zero-tilt control's result, first, whatever it says.
4. The pitch inference and its decision rule's outcome.
5. Magnification with uncertainty, and the comparison against the corpus's own
   two beliefs.
6. The focus-axis calibration in µm per frame, and whether the step is constant.
7. The M5 cross-check, namespaced.
8. The depth map's specification: units, uncertainty, validity mask.
9. A **candidate facts** table, numbered `P1, P2, ...` per rule 28.

**Registered artefact.**
`experiments/M84b-ruler-metrology/out/depth-truth-highly-angled-ruler-mm-cpl.npz`
carrying `depth_um`, `depth_sigma_um`, `valid`, and a metadata block naming the
parameters, their uncertainties, and the commit that produced them. Uncertainty
and validity are the load-bearing fields, not resolution.

---

## 10. Rule checklist discharged at publication

**Registered.** Per rule 22, the report must name, per rule, the command or line
that discharges it, for at least rules 4, 8, 9, 10, 13, 17, 20, 24, 28, 32, 36,
38, 39, 41 and 42.

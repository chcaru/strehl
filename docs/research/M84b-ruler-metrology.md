# M84b — the ruler: the project's first physical ground truth

**Milestone:** M84b — the second, independent claimant on the M84 stem (SYNTHESIS fact 1146).
**Captures:** `D:\personal\macro\highly-angled-ruler-mm-cpl` (299 frames) and
`D:\personal\macro\flat-on-ruler-cpl` (79 frames), both read-only throughout.
**Code:** `experiments/M84b-ruler-metrology/`.
**Pre-registration:** frozen and committed as `26ab710` **before any measurement**.

Every claim is labelled **MEASURED**, **DERIVED**, **ARGUED** or **UNVERIFIED**.
Numbers imported from other milestones are namespaced.

---

## VERDICT

> **This capture can serve as physical ground truth, and at better accuracy than the
> milestone asked for.** `highly-angled-ruler-mm-cpl` yields a per-pixel metric depth map
> over **65 900 q4 pixels (12.8 % of frame)** with a **median depth uncertainty of 8.28 µm**
> (p10 6.09, p90 16.43) against a pre-registered bar of 25 µm. The depth axis is anchored to
> an absolute physical scale: **975.73 ± 0.16 µm of depth per graduation** (MEASURED).
>
> **Diffraction is not the limiting factor.** The honest-negative branch the dispatch
> offered does not apply here: graduations resolve at 14–16 quad-px FWHM against a
> 44–59 quad-px pitch with ~900 DN of contrast, and the tick lattice fits a projective plane
> law to **0.27 quad px rms**. What limits this capture is that **the ruler occupies only
> 613 of 3512 columns** — 13 usable graduations. That is a framing limit, not an optical one,
> and §13 says what capture removes it.
>
> **Four registered bars failed and all four are reported as failures.**
> **Z3** — the "flat-on" control is not flat; it carries **3.32° ± 0.71°** of real tilt, so a
> constant-pitch model cannot fit it. The target is tilted, not the method.
> **L3** — graduations cover **32.2 %** of the registered angled ROI, which was drawn before
> the ruler's position in frame was known.
> **The placebo bar** — the registered |r| < 0.2 threshold was **mis-scaled**; a 1000-draw
> null has sd 0.290, so a true null clears that bar barely half the time. Re-measured
> properly, the real r = 0.9972 **exceeds all 1000 permuted nulls**.
> **Constancy** — the focus axis is **not** a constant step. It **drifts monotonically from
> 32.35 to 49.36 µm per frame**, a 1.53× range. This is the most consequential negative in
> the report: a uniform per-frame depth step is assumed in several places in this corpus and
> had never been checked against physics.
>
> **A control caught a real bug in my own headline numbers, mid-milestone.** A coordinate-frame
> error had inflated the tilt from 77.35° to 80.47° and the depth scale by 1.06 %. Every
> registered bar passed with the wrong number in place; only an independent re-implementation
> found it. It is fixed, all dependents are re-derived, and §9 records it in full. **Any M84b
> figure quoted before this document is wrong.**
>
> **The result with the widest blast radius is not the depth map.** The measured
> **m = 2.7198 ± 0.0051 (stat) ± 0.3 % (syst)**, combined with **M5's measured B ∈ [2.41,
> 3.06]**, gives pupil magnification **p ∈ [1.31, 1.94]** and **excludes p = 1** by 0.638 in
> B. **SYNTHESIS fact 1149 assumes p = 1**, and with it goes fact 1149's headline: at f/5.6
> wide open the diffraction cutoff is **106–135 cy/mm, above the sensor's 97.7 cy/mm
> Nyquist**, so **MTF at Nyquist is 0.026–0.165 — small, but not zero.** See §8.

---

## 1. Disclosure: two milestones on one stem, and what I did and did not read

**MEASURED (process).** At session start I found a second live agent
(`6f883d30-d01b-457c-a3bc-dca64462ecef`) dispatched on an identical brief, which had already
committed `f6ee015` into `experiments/M84-ruler-metrology/`. The ledger recorded it as stood
down; it was not. I declared a file boundary by `write_agent` (it keeps the `M84` stem, I
take `M84b`), moved my tree, and notified it. The orchestrator has since folded the incident
as **SYNTHESIS fact 1146** and adopted the arrangement deliberately.

### 1.1 Contamination, disclosed rather than smoothed

The ledger bars me from reading the `M84` stem and requires disclosure of any contamination.

**What I gave.** On declaring the boundary I passed the sibling three reconnaissance
findings (frame counts, the quad-grid dimensions, and the read-only guard results). That is
contamination *from* me *to* it, and it is the sibling's to disclose; I record it here so
the direction is on record.

**What I received, and exactly when.** I have not read
`docs/research/M84-ruler-metrology.md`, nor any file under `experiments/M84-ruler-metrology/`,
nor any of the sibling's numbers. **One bit did reach me.** The orchestrator's C3 placeholder
occupying this filename stated that *"`M84` has reported a complete negative verdict"*. I
read that at **00:21 PDT** while opening the file in order to overwrite it. **Every number in
this report was already final:** the last measurement artefact,
`out/17-depthmap.json`, was written at **00:16:05 PDT**, and `out/15-closure.json` at
00:13:10. **Nothing was changed after 00:21.** The only addition after that moment is §8's
cross-check arithmetic, which reads M5 and SYNTHESIS and does not touch the sibling.

**I did not tune toward or away from agreement.** I do not know M84's method, its ROIs, its
pitch decision, or any figure it reports — only the one-word direction of its verdict, which
is the opposite of mine. **That disagreement is the point of running two claimants.** If the
two reports diverge, the divergence is a first-class finding and this document's §13 lists
the specific limits that could produce a negative verdict from the same frames: 13
graduations, an assumed principal point, and uncorrected distortion.

---

## 2. What was measured, and in what order

The pre-registration (`experiments/M84b-ruler-metrology/PREREGISTRATION.md`, `26ab710`) fixed
the method, ROIs, pitch decision rule and every accuracy bar before measurement. Its §0b
declares the non-blind reconnaissance R0–R9 that preceded it. Deviations are in §10.

| Step | Script | What it does |
| --- | --- | --- |
| 10–11 | `10-geometry-recon.py`, `11-native-aif.py` | navigation composites; **not evidence** |
| 12 | `12-ticks.py` | column-wise best-focus composite, tick localiser, projective fit |
| 13 | `13-fit.py` | quality filter, explicit index assignment, robust refit |
| 14b | `14b-hierarchy.py` | the **pitch decision** from the long-mark hierarchy |
| 15 | `15-closure.py` | the **two-view closure**: tilt, m, f, Z₀, depth scale |
| 16 | `16-focusaxis.py` | µm per frame, drift, placebo, photometric disclosure |
| 17 | `17-depthmap.py` | the 2-D plane law and the **ground-truth depth map** |
| 18 | `18-controls.py` | synthetic positive, negative twin, two byte-planted mutations |
| 19 | `19-m5-crosscheck.py` | M5 transfer and the fact-1149 propagation |

All response operators are **my own NumPy/SciPy implementations**. **No file under `crates/`
was read for behaviour or modified** — M82 owns it. Nothing was written to
`D:\personal\macro`, `D:\macro-dark-frames` or `C:\dev\macro`.

---

## 3. The zero-tilt control, run first — and it fails a registered bar

`flat-on-ruler-cpl`, 79 frames, **ISO 100, f/5.6, 200 mm, 0.3 s**, uniform across the stack
(MEASURED by `exiftool -T -ISO -FNumber -FocalLength -r -ext ARW`, confirming the dispatch).

| Registered bar | Definition | Result | Verdict |
| --- | --- | --- | --- |
| **Z1** | \|C_flat\| ≥ 5× smaller than \|C_ang\| | **16.83×** | **PASS** |
| **Z2** | \|θ_flat\| < 15° | **3.32°** | **PASS** |
| **Z3** | a similarity (constant-pitch) model fits the flat comb < 1.0 px | **2.65 px** | **FAIL** |
| **L1** | flat projective residual < 1.0 quad px | **0.952 px** (0.36 % of pitch) | **PASS, barely** |

**MEASURED: the flat-on target is not flat.** θ_flat = **3.3235° ± 0.7078°**. A constant-pitch
model is rejected at 2.65 px while the projective model fits at 0.952 px — the pitch
genuinely varies across the field.

**ARGUED.** Z3 was a badly designed bar. It conflates *method validity* with *target
alignment*, and can only pass if the owner's hand-levelling was perfect. Method validity is
carried by Z1 and L1: the method separates the two targets by 16.8× in the perspective
coefficient and fits the near-flat one to a third of a percent of its pitch. **I report Z3 as
failed and name the bar itself as the defect** rather than reinterpreting it after the fact.

**UNVERIFIED, and it reaches only two numbers.** The flat comb spans all 3512 columns, so it
has high leverage on lens distortion; the angled comb occupies a 613-column central strip.
Uncorrected radial distortion therefore biases `θ_flat` preferentially. Because the closure
reads θ_flat only through the ratio `Rb`, this propagates to **f and Z₀** but **not materially
to m or to the depth scale** (§5.3).

---

## 4. The pitch: measured, not assumed

The pre-registration forbade assuming 1 mm. Three independent lines, all MEASURED:

1. **Long-mark hierarchy** (`14b-hierarchy.py`). Aggregating three horizontal bands at
   different heights separates graduations by physical length. Long marks fall at graduation
   indices **0, 5 and 10 exactly**; mid marks at the 5s; **zero spread**, ~22× darkness
   contrast between classes; period Q_long = 10, Q_mid = 5. That is the universal
   cm / half-cm / mm hierarchy of a millimetre rule.
2. **Legible numerals.** In the flat-on stack the numerals "2" and "3" sit beside graduation
   indices 0 and 10, at absolute quad x = 298.9 and 2942.4. Ten graduations between the 2 cm
   and 3 cm marks.
3. **Physical admissibility.** P = 0.5 mm would require **m = 5.44**, against the **2.8×**
   ceiling for this lens with a 2× converter (`F-camera-lens-optics.md:13`, VERIFIED; and see
   §4.1). **REFUTED.** P = 2.0 mm would require m = 1.36, contradicting the numerals.

**MEASURED: P = 1.000 mm.** The visible marks *are* the millimetre marks; this rule carries no
sub-millimetre graduations.

**This is load-bearing and it is linear.** Control G1 (§8) shows the absolute depth scale
scales in exact proportion to the assumed pitch while the **tilt does not move at all**, because
θ comes from dimensionless ratios and `depth/graduation = P·sinθ` is linear in P. A 10 % pitch
error would be a 10 % depth-scale error and a 0 % tilt error.

### 4.1 A correction to the ceiling's provenance, not to its value

**SYNTHESIS fact 1147 (MEASURED)** establishes that `F-camera-lens-optics.md:66`'s *"Owner
uses SEL20TC"* is **false** — the converter is a **2× Viltrox**, and the SEL20TC is not
compatible with this lens. **The 2.8× ceiling survives** (any true 2× gives 1.4 × 2, and EXIF
confirms an electronically communicating 2×), so the refutation of P = 0.5 mm stands. I
therefore cite **the ceiling**, never the converter model. My pre-compaction notes named the
SEL20TC when describing the rig match to M5's stack; that naming was wrong and is corrected
here. The rig match itself is unaffected: both stacks report `LensModel: FE 100mm F2.8 Macro
GM OSS + 2X Teleconverter`.

Fact 1147 also establishes, independently, that **`MaxApertureValue == FNumber == 5.6`**, so
both M84b stacks were shot **wide open**. The dispatch's "f/5.6 marked" is right, and there
was no faster option available.

---

## 5. The geometry

### 5.1 The model — and a correction to the milestone's framing

**DERIVED.** In centred image coordinates ξ = x − x_pp, a graduation lattice on a plane tilted
by θ images as

```
ξ(k) = f·(X₀ + kP·cosθ)/(Z₀ + kP·sinθ) = (a + b·k)/(1 + c·k)
a = f·X₀/Z₀      b = m·P·cosθ      c = P·sinθ/Z₀ = m·P·sinθ/f      m = f/Z₀
```

**`docs/captures-needed.md` §8 and the dispatch both say "a plane's depth is affine in image
coordinates". Under perspective that is false: *inverse* depth is affine.** With 4.5×
foreshortening across this ruler the distinction is material rather than pedantic — the
graduation pitch runs from 58.0 to 44.5 quad px across 13 mm. An affine depth model fitted to
this target would be wrong by that amount.

**A single view has three degrees of freedom and four unknowns (X₀, m, θ, f) and cannot
separate them.** The closure therefore uses both stacks — same camera, same lens, same working
distance, hence shared m and f:

```
Rb = b_flat/b_ang = cosθ_flat/cosθ_ang        Rc = c_ang/c_flat = sinθ_ang/sinθ_flat
```

Six numbers, six unknowns, closed. **MEASURED: Rb = 4.5590 ± 0.0129, Rc = 16.83 ± 12.88.**

**This is not decorative.** Control S2 (§8) plants a lattice with an exactly known plane and
recovers it by the single-view route with Z₀ *assumed known*. It **misses by 0.76°** at 0.27 px
of noise, because at θ = 77.4°, dθ/d(sinθ) = 1/cosθ = **4.6 rad**, so a sub-percent error in
the fitted `c` becomes degrees of tilt. The two-view closure on the same planted data recovers
θ to **0.012°**.

### 5.2 The measured geometry

All **MEASURED**. Uncertainties are 2000-draw bootstraps resampling graduations jointly in
both stacks.

| Quantity | Value | Bootstrap sd | 95 % interval |
| --- | ---: | ---: | --- |
| Graduation pitch `P` | **1.000 mm** | — | decided, §4 |
| θ_flat (control) | **3.3235°** | 0.7078 | [1.69, 4.71] |
| **θ_ang** | **77.3509°** | **0.0414** | [77.29, 77.46] |
| **Magnification `m`** | **2.7198** | **0.0051** | [2.711, 2.733] |
| `m` in quad px per mm | 265.605 | 0.494 | [264.75, 266.91] |
| `f_eff` | **205.52 mm** | 3.76 | [200.0, 216.2] |
| `Z₀` (entrance pupil → subject) | **75.57 mm** | 1.36 | [73.56, 79.48] |
| **Depth per graduation** | **975.73 µm** | **0.158** | [975.49, 976.16] |

Registered bar **M1** (σ_m/m < 1 %, statistical): **0.19 % — PASS**.
Registered bar **M2** (reported, not pass/fail): including the imported pixel pitch, **0.36 %**.

**Pixel pitch, stated and sourced as the milestone required.** I used **5.12 µm** per sensor
pixel, ±0.3 %, from `F-camera-lens-optics.md:91` and `:1171`, where it is itself **DERIVED**,
not measured. One quad-grid pixel = 2 sensor pixels = **10.24 µm**. **Independent
confirmation:** the body is a Sony **A7C II (ILCE-7CM2)** (MEASURED from EXIF), and its
7008-px-wide visible frame over a 35.9 mm sensor gives 35.9/7008 = **5.123 µm**. The corpus
value stands.

### 5.3 Robustness of the shared-working-distance assumption

**MEASURED (sensitivity sweep).** Re-solving with `m_ang = m_flat·(1 + ε)`:

| ε | θ_ang | m | f (mm) | Z₀ (mm) | depth/grad (µm) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| −5 % | 76.67° | 2.7193 | 194.7 | 71.6 | 973.06 |
| −2 % | 77.09° | 2.7196 | 201.2 | 74.0 | 974.71 |
| 0 | **77.35°** | **2.7198** | **205.5** | **75.6** | **975.73** |
| +2 % | 77.60° | 2.7200 | 209.9 | 77.2 | 976.69 |
| +5 % | 77.96° | 2.7203 | 216.3 | 79.5 | 978.02 |

**A ±5 % violation moves f and Z₀ by ±5 %, moves `m` by < 0.02 %, and moves the depth scale by
only ±0.28 %.** The depth-critical numbers are insensitive; only f and Z₀ are exposed. This is
the key robustness statement behind the verdict.

Supporting evidence for the assumption (MEASURED from EXIF): both stacks report identical
`FocalLength` 200 mm, `FNumber` 5.6, `ISO` 100 and `LensModel`, and **both sweeps start at the
same `FocusDistance2` = 0.2707 m**. The camera was not moved between them. This is evidence,
not proof; §5.3's sweep exists because of that gap.

### 5.4 Two external checks the closure had to pass, and did

1. **The lens ceiling.** m = 2.7198 sits **2.9 % under** the 2.8× maximum
   (`F-camera-lens-optics.md:13`, VERIFIED) — admissible, and consistent with
   `FocusDistance2` being near the lens's close limit. Had the closure returned m > 2.8 it
   would have been refuted outright by an external fact. **This is a real falsifier that the
   measurement could have tripped and did not.**
2. **The focal length.** f_eff = **205.5 ± 3.8 mm** against EXIF's nominal **200 mm** — 2.8 %
   high, inside §5.3's sensitivity, with a 95 % interval whose lower edge is 200.0 mm exactly.
   **The closure recovers the composed focal length of a lens-plus-teleconverter path from
   graduation spacings alone, with no lens model and no EXIF input.** That is independent
   confirmation the geometry is right.

**A caution on 2.9 %.** The proximity of m to the ceiling is a consistency check, not a
tightening: the ceiling is a maximum, and being just under it is expected at close focus, not
suspicious. I did not use the ceiling to constrain the fit.

---

## 6. The focus axis in microns per frame — and it is not constant

**MEASURED** from per-graduation through-focus curves on the 299-frame angled stack
(`16-focusaxis.py`). The response is level-normalised because the frame mean rises
**1396.7 → 2160.8 DN (+55 %)** across the sweep.

| Quantity | Value |
| --- | ---: |
| Graduations with a usable through-focus peak | 13 of 13 |
| Best-focus frame span | n\* = **8.12 → 290.65** of 299 |
| Frames per graduation (robust line) | **23.122** |
| **Mean µm per frame** | **42.198**; bootstrap **42.28 ± 1.56** [39.02, 44.93] |
| Robust-line residual | 6.566 frames rms |
| Pearson r of n\*(k) | **0.99721** |
| Monotone fraction | **1.000** (bar ≥ 0.80) |

### 6.1 The registered placebo bar was mis-scaled, and I say so

The pre-registration set "|r| < 0.2 for one frame-axis permutation". The single registered
draw returned **r = −0.2403 — outside the bar.** Rather than reinterpret it, I measured the
null: over **1000 permutations**, r has mean +0.010 and **sd 0.290**, p95|r| = 0.561,
max|r| = **0.7496**. With 13 points the null sd is ≈ 1/√10 = 0.32, so **a single draw lands
inside ±0.2 barely half the time under a perfect null.** The registered bar demanded something
a true null could not reliably deliver.

**The calibrated statement is unambiguous: the real r = 0.99721 exceeds all 1000 permuted
nulls (p < 0.001).** The registered bar is reported as failed, and diagnosed as a defect in
the bar rather than in the result.

### 6.2 The step drifts by 1.53×

**MEASURED.** Five equal segments along the ruler, near → far:

| Segment | 1 | 2 | 3 | 4 | 5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| µm per frame | **32.353** | 37.943 | 42.088 | 46.341 | **49.358** |

Registered constancy bar max/min < 1.25. **Measured ratio 1.5256 → DRIFTS. FAIL.** The robust
line's 6.57-frame residual is itself the symptom: a straight line is the wrong model for a
curved relation.

**ARGUED — the direction is expected, the magnitude is not fully explained.** For a fixed
image-side focus increment, dZ_object = dZ_image/m², so as the subject recedes and m falls the
object-side step must grow. Over this sweep Z runs 75.6 → 88.3 mm, so m falls 2.72 → 2.33 and
1/m² predicts a **1.33×** rise. The measured rise is **1.53×** — same sign, same order, but
~15 % steeper than thin-lens. Plausible causes: focus breathing (an internally focusing macro
changes f as it focuses), or a bracket step defined in units other than constant lens
displacement. **Not resolved here, and I do not claim to have resolved it.**

**Blast radius.** Anything in this corpus that treats a focus bracket as uniform depth sampling
is wrong by up to 1.53× within a single stack.

### 6.3 Two disclosed limits on the focus axis

- **Estimator disagreement.** Half-max-centroid and 3-point-parabolic peak estimators differ by
  a **median of 2.946 frames ≈ 124 µm**. Through-focus curves here are broad and asymmetric.
  **The µm-per-frame calibration therefore carries a systematic of order 100 µm that the
  ±1.56 µm/frame bootstrap does not capture.** **This does not touch the depth map**, which is
  purely geometric and never uses a focus peak (§7).
- **Photometric confound ruled out.** corr(frame mean, normalised response) = **+0.0113**. The
  +55 % illumination ramp is not driving the focus peaks.

---

## 7. The ground-truth depth map

### 7.1 The second image axis, and a test that could have failed

**MEASURED** (`17-depthmap.py`). Steps 12–15 fit one row band; a depth map needs the plane in
two dimensions. For a plane, **depth is constant along a graduation if and only if the tick
image lines are parallel** — a vanishing point at infinity. That is testable, and it was
tested.

Five row bands (y ∈ [1350,1410) … [1740,1800), all inside registered A-RULE and clear of both
the datum line and the granular surface) give band-to-band x offsets:

| Band Δy (quad px) | −300 | −200 | −100 | 0 | +90 |
| --- | ---: | ---: | ---: | ---: | ---: |
| x offset (quad px) | −13.197 | −8.940 | −4.254 | 0 | +4.467 |

A straight line fits these to **0.153 px rms**, giving

> **shear s = dx/dy = +0.045152 ± 0.000637**, i.e. graduations lean **2.585°** off
> image-vertical.

**Per-tick offsets confirm parallelism.** Matched-tick offset spread is **0.685, 0.579 and
0.995 px** in the three well-populated bands, with offset drift ≤ **1.19 px per 1000 px**. The
extreme −300 band is the noisiest (spread 2.893 px over 11 pairs, drift 6.59 px/1000 px) as it
sits closest to the datum line. **ISO-DEPTH TICKS: confirmed.**

**An independent consistency check on the shear.** Step 12 averaged 180 rows before locating
ticks and still found 14–16 px FWHM ticks. A shear s smears a tick by 180·s; the measured s
implies 8.1 px of smear, consistent with the observed FWHM. Had s been ~0.3 the ticks would
have washed out entirely. The two measurements agree, and they were made for different reasons.

### 7.2 The map

**The depth map is analytic and is shipped as parameters, not as a binary blob.**

```
x_ref   = x_quad − s·(y_quad − y_ref)          y_ref = 1680.0,  s = 0.0451520
k       = (x_ref − A)/(B − C·x_ref)            A = 1698.1386,  B = 80.83152,  C = 1.2912335e−02
depth_µm = k · 975.7294
```

`experiments/M84b-ruler-metrology/out/depth-truth-params.json` (2 KB, committed) carries these
with their uncertainties, the mask rule, the `n_model` polynomial and the metadata.
`out/depth-truth-highly-angled-ruler-mm-cpl.npz` is the q4 expansion (`depth_um`,
`depth_sigma_um`, `valid`, `k_index`, `n_model`); it is **not committed** — `.gitignore:43`
excludes `*.npz` — and the analytic form is exact, so the blob is redundant.
`17-depthmap.py` regenerates it deterministically.

**Coordinates.** The q4 grid is the quad-grid green plane `(G1+G2)/2` decimated 4×, shape
**(586, 878)**; `quad_from_q4` scale 4, offset 1.5. One quad px = 2 sensor px = 10.24 µm at the
sensor. **The depth origin is graduation k = 0**: this is *relative* depth on an *absolute*
metric scale. It does not claim to know standoff better than Z₀'s ±1.36 mm.

### 7.3 Uncertainty — and a statistical trap worth recording

A, B and C are **strongly correlated**: the fitted curve is far better determined than any one
coefficient. My first propagation used their marginal standard deviations as if independent
and returned a median σ of **265.6 µm — an overstatement of 32×**. The correct propagation
bootstraps the **curve**: resample graduations, refit, take the spread of k(x_ref) over 1000
replicates. That gives σ_k = 0.0028–0.0105 graduations across the span. Per-pixel σ then
combines σ_k with the tick residual (0.271 px), the shear uncertainty and the depth-scale
uncertainty.

| Registered bar | Definition | Result | Verdict |
| --- | --- | --- | --- |
| **D2** | median per-pixel depth σ over the valid mask < 25 µm | **8.282 µm** (p10 6.091, p90 16.433) | **PASS** |
| **D1** | relative depth uncertainty < 0.5 % | **0.0701 %** span-relative; **0.1738 %** literal | **PASS both readings** |
| **P1** | planarity residual structure ratio < 3.0 | **1.0129** (resid rms 0.271 px, after 5σ rejection) | **PASS** |
| **L2** | angled residual < 2 % of local pitch | **0.53 %** | **PASS** |
| **L3** | ticks localise over ≥ 50 % of the A-RULE span | **32.22 %** | **FAIL** |

**On D1.** Taken literally as σ_k/\|k\| it diverges as k → 0, which is a property of the chosen
depth **origin**, not of the measurement. Both readings are given; neither was selected after
seeing the result.

**On L3 — a real failure, honestly a bad ROI.** Graduations span absolute quad
x ∈ [1699.4, 2311.5]: **613 of A-RULE's 1900 columns**. A-RULE was drawn generously *before*
the ruler's position in frame was known. **Only 13 graduations = 13 mm of ruler are usable**,
which is also why the depth map covers 12.8 % of the frame rather than more. **This, not
diffraction, is what limits the capture.**

### 7.4 The validity mask

```
valid = (k inside the calibrated span ± 0.5 graduations)
        AND (confidence ≥ 21.22, the 20th percentile)
        AND (|q4 best-focus index − n_model(k)| ≤ 25 frames)
```

`n_model` is a quadratic in k fitted to step-16's per-graduation n\*(k) (coefficients
[−0.47798, 29.02713, 10.40181], residual 2.71 frames). **The focus-consistency term rejects
the granular supporting surface and the background without any hand-drawn polygon** — the
mask's lower-right boundary reproduces the granular surface's true diagonal, which I confirmed
visually against `out/17-valid.png`. Sensitivity is disclosed:

| tolerance (frames) | 10 | **25** | 50 |
| --- | ---: | ---: | ---: |
| valid q4 px | 37 686 | **65 900** | 76 467 |

**The mask is conservative by construction**: it claims depth only where graduations were
actually measured, even though the same physical plane extends well to the left of them.

**Valid depth range: −467.15 to +12 225.38 µm** — a span of **12.69 mm**.

### 7.5 The 2-D check the 1-D fits could not give themselves — and the number M81 asked for

**MEASURED.** `n_model` composes the *geometric* plane law with the step-16 focus calibration,
both fitted on a single row band. `idx` is the q4 best-focus index, measured independently at
every pixel. Over **77 782 q4 px with the tolerance gate switched off**: median offset
**−5.46 frames** (≈ −230 µm), **core fraction 0.8856**, **core rms 12.949 frames = 546.4 µm**.

Two readings, both worth having:

1. **The plane extends off the tick row.** 88.6 % of the probed region falls in the core — the
   geometry predicts focus in two dimensions, not merely along the band it was fitted on.
2. **And this is the number the project actually needs.** A naive per-pixel focus index on real
   brushed-steel texture localises depth to **~546 µm rms**, while the geometric truth is good
   to **~8.3 µm**. **That is a 66× gap, and it is exactly the truth-linked estimator loss that
   M81 §11 named as one of only two remaining routes to the gate** (`M81-estimation-merge.md`
   line 347: *"identify the spatially local response-noise unit on real texture or choose a
   gate by a truth-linked estimator loss"*). Until tonight there was no way to put a micron
   number on either side of that comparison.

**Scope limit, stated plainly.** 546 µm is the error of a *naive per-pixel argmax on this
subject*, not of the project's shipped estimator, which I did not run (M82 owns `crates/`). It
is a substrate for the loss, not the loss itself.

---

## 8. Cross-check against M5 — and the consequence for fact 1149

`19-m5-crosscheck.py`; full output in `out/19-m5-crosscheck.log`.

### 8.1 The rig match, verified before the transfer

**MEASURED.** M5's diffraction stack is `C:\dev\macro\test\109MSDCF`
(`M5-diffraction-measured.md:296`). `exiftool` on it: same body, same
`FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`, 200 mm, **`FocusDistance2` = 0.2738 m** against
M84b's **0.2707 m** — **1.1 % apart**. Marked aperture differs (M5 f/11, M84b f/5.6) but
**B = 1 + m/p is aperture-independent**, so it transfers.

### 8.2 The transfer is not circular, and M5 says why it matters

**M5's B is measured from the cutoff frequency and the marked N**
(`B = 5.12/(0.55·N·f_c)`) and **takes no magnification as input**, so the bound is independent
of anything M84b measured. M5 is explicit about what it could not do
(`M5-diffraction-measured.md:697–699`): ***"m ≈ 2.0 is DERIVED from the brief, not measured. No
ruler was photographed."*** **M84b is that ruler.**

**M5's bracket, namespaced:** B ≤ 3.064 (MEASURED→DERIVED, f/11 knee, `:57`); B ≳ 2.412
(ARGUED, clean floor, `:62`); **combined B ∈ [2.41, 3.06]** (`:65`).

### 8.3 Pupil magnification, and the exclusion of p = 1

Using m ∈ [2.7015, 2.7381] (M84b's 95 % statistical interval widened by the ±0.3 % pixel-pitch
systematic) against M5's bracket:

| Quantity | Value |
| --- | ---: |
| **p = m/(B − 1)** | **[1.309, 1.939]**, midpoint 1.565 |
| B required for p = 1 | **3.720** (lower edge 3.702) |
| M5's measured ceiling on B | **3.064** |
| **p = 1 excluded by** | **0.638 in B** |

**MEASURED → DERIVED: p = 1.0 is excluded.** It would require B = 3.72, far above M5's
measured 3.064. **M5's own line 75 reads "a near-unity pupil magnification, which is what a
symmetric-ish design plus a teleconverter [gives]" — that reading was conditional on m = 2.0
and does not survive the measured m.** SYNTHESIS fact 27's *"with m ≈ 2.0, p ≈ 1.0–1.4"* fails
the same way.

**Scope limit, and it is important.** This does **not** refute M5's B. B was measured without
m; only the *decomposition* of B into m and p changes. **N_eff = N·B is unchanged, so every
diffraction conclusion M5 draws downstream of N_eff stands.**

### 8.4 What that does to fact 1149

**SYNTHESIS fact 1149 is DERIVED with p = 1 explicitly assumed** and its own text flags the
advisor's ±38 % on that assumption. Replacing the assumption with M5's measurement, at the
captures' own **f/5.6 wide open** (fact 1147):

| Case | B | N_eff | Airy (µm) | Airy (px) | f_c image (cy/mm) | f_c subject (cy/mm) | MTF @ sensor Nyq | MTF @ binned Nyq |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| M5 lower, B = 2.412 | 2.412 | 13.51 | 18.1 | 3.54 | **134.6** | 366.1 | **0.1654** | 0.5485 |
| M5 upper, B = 3.064 | 3.064 | 17.16 | 23.0 | 4.50 | **106.0** | 288.2 | **0.0260** | 0.4348 |
| fact 1149's p = 1 | 3.720 | 20.83 | 28.0 | 5.46 | 87.3 | 237.4 | **0.0000** | 0.3268 |

Sensor Nyquist **97.66 cy/mm**; current binned-output Nyquist **48.83 cy/mm**.

**DERIVED: fact 1149's headline does not survive.** Its claim that *"MTF at Nyquist is exactly
zero — not small, zero"* holds **only** at p = 1. Using M5's *measured* B, the cutoff is
**106–135 cy/mm, above the 97.7 cy/mm sensor Nyquist in both cases**, and **MTF at sensor
Nyquist is 0.026–0.165**. Small; crushed; **not zero.**

Three consequences, and they do not all point the same way:

1. **Fact 1149's "any future claim of critical per-pixel sharpness on this rig is refuted in
   advance" is too strong.** The refutation was an artefact of the assumed p.
2. **Fact 1149's priced prize for M85 gets larger, not smaller.** It priced the discarded band
   as 48.8 → 86.3 cy/mm tapering to zero. The measured-B version is **48.8 → 97.7 cy/mm
   carrying MTF from ~0.44–0.55 down to ~0.03–0.17, all strictly nonzero**, with further
   optical detail above Nyquist that the sensor cannot sample. The full-resolution work is
   better founded than its own justification claimed.
3. **Fact 1150's conclusion is untouched in direction** — it compares TC against bare lens and
   both sides move the same way — **but its absolute cy/mm figures were computed at p = 1 and
   should be recomputed.**

### 8.5 Fact 1149 attributes a magnification to M84b that M84b did not measure

**MEASURED.** Fact 1149 states *"m = 2.762 (M84b's tick-comb measurement read against the 2.8x
ceiling)"*. **M84b's measured value is 2.7198 ± 0.0051 (stat) ± 0.3 % (syst).** The attributed
2.762 is **+1.55 %** and lies **outside** M84b's interval [2.7015, 2.7381]. I cannot reproduce
2.762 from any artefact in `out/`. **The authoritative M84b figure is 2.7198, and fact 1149
should be recomputed with it** — though that correction is second-order next to §8.4's.

### 8.6 The focus sweep is under-sampled against its own depth of field

**DERIVED**, thin-lens macro form DoF = 2·c·N_eff/m², with N_eff from M5's measured B:

| circle of confusion | B = 2.412 | B = 3.064 |
| --- | ---: | ---: |
| c = 1 sensor px (5.12 µm) | **18.7 µm** | **23.8 µm** |
| c = 1 quad px (10.24 µm) | 37.4 µm | 47.5 µm |

The measured step is **42.20 µm/frame**, drifting 32.35 → 49.36. **At c = 1 sensor pixel the
bracket under-samples focus by roughly 1.8–2.3×**; at c = 1 quad pixel it is marginal.
**This conclusion depends entirely on the choice of c, which is a convention rather than a
measurement, and I state it with that dependence rather than picking the flattering one.**

---

## 9. The bug the controls caught — full disclosure

**This is the most important section for anyone quoting M84b.**

Reconciling the step-18 control target against step 15, their baselines disagreed (77.35° vs
80.47°). Tracing it: **step 12 saves each stack's column profile in ROI-relative coordinates** —
its config sets `x0 = 0` for the flat stack but `x0 = 1100` for the angled one — **and step 13
fitted those profiles without lifting them to absolute coordinates.** Step 15 then centred
*both* fits on the principal point x_pp = 1757, over-subtracting `1100·C` from the angled `b`
(43.958 where it should be 58.162; Rb 6.032 where it should be 4.559).

| Quantity | Buggy | **Corrected** | Shift |
| --- | ---: | ---: | ---: |
| θ_ang | 80.474° | **77.351°** | −3.12° |
| depth per graduation | 986.21 µm | **975.73 µm** | −1.06 % |
| f_eff | 207.74 mm | **205.52 mm** | −1.07 % |
| Z₀ | 76.38 mm | **75.57 mm** | −1.06 % |
| **m** | 2.71989 | **2.71979** | **−0.004 %** |

**m survives essentially untouched**, because it is set by the flat view's `b` — already in
absolute coordinates — and by θ_flat, which barely moved. Every other number above is
corrected. The buggy artefact is preserved at `out/15-closure-BUGGY.json.bak`.

The same error then surfaced in step 16's dense per-column inversion and its photometric
disclosure once step 15 was fixed; the tell was that the segment µm/frame values stopped
bracketing the mean (20.9–30.4 around 42.2) and `corr(level, response)` flipped to −0.997.
Both were traced and corrected the same way. The per-graduation slope, and hence the mean
µm/frame, was never affected — it is coordinate-free. **Steps 16 and 17 now `assert` that the
fit they consume is in absolute coordinates**, so the two frames cannot silently drift apart
again.

**Process reading (ARGUED), and it is the finding I would keep if I could keep only one.** The
bug was not found by inspection, not by the residuals (0.27 px — the fit was excellent *in its
own frame*), and not by any registered bar. **Every registered bar passed with the wrong number
in place.** It was found because a control independently re-implemented the estimator and
compared baselines. **Bars measure precision. Only independent re-implementation measures
correctness.**

---

## 10. Controls: four tests, one designed to fail

`python src\18-controls.py` — announces its test count and returns non-zero on any failure
(rule 36). Final state: **4/4 PASS, exit 0**, recorded in `out/18-controls.json`.

| # | Control | Result |
| --- | --- | --- |
| **S1** | **Synthetic positive.** Plant both views of an exactly known rig at 0.27 px noise; require the two-view closure back. | θ_ang error **0.0116°** (bar 0.5°), m error **0.0014 %** (bar 1 %), depth-scale error **0.0046 %**. **PASS** |
| **S2** | **Negative twin — this one must fail.** Same planted data, single-view inversion with Z₀ assumed known. | Recovers θ = 76.593° against a plant of 77.351°: **misses by 0.758°**, and m by 5.6 %. **Fails as predicted → PASS** |
| **G1** | **Byte-planted wrong pitch**, `PITCH_MM = 1.0 → 1.1`; read-back verified, SHA-256 moved. | m **265.60 → 241.46** quad px/mm, depth scale **975.73 → 1073.30 µm**; θ **unchanged**. Detected. Restored **byte-identical**; post-restore output identical to baseline. **PASS** |
| **G2** | **Byte-planted sign inversion** of the projective coefficient C; read-back verified, SHA-256 moved. | Closure reports `non-physical closure: m or f non-positive` (f = −19 166 px). Detected. Restored **byte-identical**. **PASS** |

Mutations are applied to a **private copy** (`src/_control_target.py`, written from a
`TARGET_SOURCE` string and unlinked at the end), never to the measurement scripts, so a crash
cannot leave the pipeline mutated. The target independently re-implements the closure and
reproduces step 15 to **ten significant figures** (θ_ang 77.35089220, m 2.719793006,
f 205.5230213, dZ 975.7294345).

**G2 improved production code.** Its first run was **not** detected: the sign-inverted
coefficient produced a plausible tilt (73.7°) and magnification (2.75) **alongside a negative
focal length**, and the closure returned it without complaint. I added a physical-admissibility
guard (`m > 0 and f > 0`) to `15-closure.py` itself. **A control that only ever passes is not a
control; this one found a missing assertion.**

**S1/S2 exist because the registered single-view control failed for a physical reason.** At
θ = 77°, dθ/d(sinθ) = 4.57 rad. That is a property of the geometry, not of my implementation,
and it is why the two-view design in §5.1 is load-bearing.

---

## 11. Disclosed deviations from the pre-registration

1. **§0a, the stem collision** — see §1 and SYNTHESIS fact 1146.
2. **Hard 5σ rejection added.** §4.2 registered Huber IRLS with no hard rejection. One angled
   detection (the 14th, at the far end) sits 22 robust σ off while the other thirteen lie
   within ±0.53 px. A 5σ hard rejection is applied and **both fits are reported** in
   `out/15-closure.json`.
3. **Hierarchy bands moved.** Registered F-TALL (y 1100–1980) truncates the tallest marks; it
   was set before the tick direction was known. `14b-hierarchy.py` uses quad-y bands
   [850,1050), [1150,1350), [1400,1500).
4. **Angled comb ROI** x ∈ [1100,3000], y ∈ [1620,1800] — strictly inside registered A-RULE.
   Step 17 widens x to [1100,3100] so sheared ticks stay in range; y bands all satisfy A-RULE's
   y ≤ 1800.
5. **`14-hierarchy.py` superseded.** Its upward column scan returned zero for two of three long
   marks and was abandoned as untrusted **before any conclusion was drawn from it**.
   `14b-hierarchy.py` is the pitch decision. The dead script is retained for audit.
6. **Placebo bar re-measured, not re-defined** — §6.1.
7. **D1 reported two ways**, neither chosen after the fact — §7.3.
8. **Control S split into S1/S2** — §10.
9. **Step 19 added** after pre-registration: the M5 transfer and fact-1149 propagation. It is
   arithmetic on two prior measurements and introduces no new measurement of mine.

---

## 12. Candidate facts for SYNTHESIS

I do not edit `SYNTHESIS.md`, `AGENTS.md` or `docs/captures-needed.md`. Proposed rows:

| # | Candidate fact | Label | Source |
| --- | --- | --- | --- |
| **P1** | **The rig's magnification is measured for the first time: m = 2.7198 ± 0.0051 (stat), ±0.36 % total.** From graduation spacing on a 1 mm rule, with no lens model and no EXIF trust. It sits 2.9 % under the 2.8× ceiling — a falsifier it could have tripped and did not. | MEASURED | M84b §5.2, §5.4 |
| **P2** | **p = 1 is excluded.** M84b's measured m against **M5's measured B ∈ [2.41, 3.06]** gives **p = m/(B−1) ∈ [1.31, 1.94]**; p = 1 would demand B = 3.72, exceeding M5's measured 3.064 by 0.638. The transfer is not circular: M5's B takes no m as input, and the rigs match (same lens + 2× TC, `FocusDistance2` 0.2738 vs 0.2707 m). | MEASURED → DERIVED | M84b §8.3 |
| **P3** | **Fact 1149's "MTF at Nyquist is exactly zero" does not survive, because it assumed p = 1.** With M5's measured B, at f/5.6 wide open: N_eff = 13.5–17.2, **f_c = 106–135 cy/mm above the 97.7 cy/mm sensor Nyquist**, and **MTF at sensor Nyquist = 0.026–0.165**. Crushed, not zero. Fact 1149's refutation-in-advance of per-pixel sharpness is too strong, and **M85's priced prize grows**: the 48.8→97.7 cy/mm band carries MTF ~0.44–0.55 down to ~0.03–0.17, all nonzero. | DERIVED | M84b §8.4 |
| **P4** | **M5's B, N_eff and every conclusion downstream of N_eff stand unchanged.** B was measured from the cutoff and the marked N with no m input. Only the decomposition of B into m and p changes. Facts 12 and 28 are untouched. | DERIVED | M84b §8.3 + M5 §0–§1 |
| **P5** | **Fact 27's "with m ≈ 2.0, p ≈ 1.0–1.4" is refuted for this rig**, and **fact 12's "at m = 2.8" is nearly right** — measured 2.7198 is 2.9 % under fact 12 and 36 % above fact 27. The corpus's two incompatible magnification beliefs are now resolved in favour of the higher one. | MEASURED | M84b §5.2, §8.3 |
| **P6** | **Fact 1149 attributes m = 2.762 to M84b. M84b measured 2.7198 ± 0.0051.** The attributed value is +1.55 % and outside M84b's interval, and cannot be reproduced from any M84b artefact. Fact 1149 should be recomputed with 2.7198. | MEASURED | M84b §8.5 |
| **P7** | **A focus bracket's per-frame depth step is NOT constant.** Measured over 299 frames: **32.35 → 49.36 µm/frame, a 1.53× monotone drift**, mean 42.28 ± 1.56 µm. Direction matches dZ_obj = dZ_img/m²; magnitude is ~15 % steeper than thin-lens predicts and is unexplained. **Anything treating a bracket as uniform depth sampling is wrong by up to 1.53× within one stack.** | MEASURED | M84b §6.2 |
| **P8** | **Physical ground truth now exists.** `highly-angled-ruler-mm-cpl` has a metric depth map over 65 900 q4 px (12.8 % of frame, 12.69 mm of depth) at **8.28 µm median uncertainty** (p90 16.43), depth scale **975.73 ± 0.16 µm per graduation**, with an explicit validity mask. Analytic parameters in `experiments/M84b-ruler-metrology/out/depth-truth-params.json`. | MEASURED | M84b §7 |
| **P9** | **The truth-linked loss M81 §11 asked for is now computable, and its first value is 66×.** A naive per-pixel focus index on real brushed-steel texture localises depth to **546 µm rms** over 77 782 probed pixels; the geometric truth is **8.3 µm**. This is a substrate for the loss, not the loss itself, and it is not the shipped estimator. | MEASURED | M84b §7.5 |
| **P10** | **Diffraction does not prevent micron-scale metrology on this rig.** Graduation FWHM 14–16 quad px against a 44–59 px pitch, ~900 DN contrast, projective residual 0.27 quad px. **What limits this capture is framing: the ruler fills 613 of 3512 columns, giving 13 usable graduations.** | MEASURED | M84b §3, §7.3 |
| **P11** | **The composed focal length is recoverable from graduations alone: f_eff = 205.5 ± 3.8 mm against EXIF's 200 mm**, a 2.8 % discrepancy whose 95 % interval touches the nominal exactly. | MEASURED | M84b §5.4 |
| **P12** | **A single view cannot recover tilt at steep angles.** At θ = 77°, dθ/d(sinθ) = 4.57 rad, so 0.27 px of tick noise becomes 0.76° of tilt error and 5.6 % of magnification error. Two views sharing m and f recover the same plant to 0.012°. **Future tilted-target work must be two-view or must pin Z₀ independently.** | MEASURED (synthetic control) | M84b §10, S1/S2 |
| **P13** | **Every registered bar passed while a coordinate-frame bug inflated the tilt by 3.12° and the depth scale by 1.06 %.** The 0.27 px residual was excellent *in the wrong frame*. Found only by a control that independently re-implemented the estimator. **Bars measure precision; only independent re-implementation measures correctness.** | MEASURED | M84b §9 |
| **P14** | **Depth is not affine in image coordinates under perspective — inverse depth is.** `captures-needed.md` §8 and the M84/M84b briefs state the affine form. At this target's 4.5× foreshortening the graduation pitch runs 58.0 → 44.5 quad px across 13 mm, so the error is material. | DERIVED | M84b §5.1 |
| **P15** | **The stack under-samples its own depth of field.** DoF = 18.7–23.8 µm at c = 1 sensor px using M5's measured B, against a 42.20 µm mean step — **1.8–2.3× under-sampled**. Marginal at c = 1 quad px. The conclusion is conventional in c and must be quoted with that dependence. | DERIVED | M84b §8.6 |

---

## 13. What this does not establish, and what to capture next

**Limits, stated plainly — and these are the places a second claimant could reasonably reach a
different verdict.**

- **13 graduations, 13 mm, 32.2 % of the intended ROI.** The ruler is small in frame. Every
  bootstrap in §5.2 is limited by this and nothing else.
- **The principal point is assumed at the sensor centre** (x_pp = 1757 quad px), not measured.
  It is a first-order input to the centring and is **UNVERIFIED**.
- **Lens distortion is uncorrected** and biases θ_flat preferentially (§3). It reaches f and
  Z₀; it does not materially reach m or the depth scale.
- **The depth map is relative on an absolute scale.** Absolute standoff is known only to Z₀'s
  ±1.36 mm.
- **The focus-axis calibration carries a ~124 µm estimator systematic** (§6.3) that the
  ±1.56 µm/frame bootstrap does not capture. **The depth map does not inherit it.**
- **The shared-working-distance assumption is supported by EXIF, not proved.** §5.3 bounds the
  damage rather than removing it.
- **The M5 transfer assumes M5's `109MSDCF` sat at m ≈ 2.72.** Supported by the lens, converter
  and `FocusDistance2` match; the 1.1 % FD2 gap is not zero.

**What would improve it, in priority order.**

1. **The same ruler filling the frame diagonally**, so graduations span the long axis. This is
   the single highest-value capture in the list and it costs one bracket. It would roughly
   triple the lever arm, fix L3, and tighten every bootstrap in §5.2.
2. **A second angled stack at a deliberately different working distance.** This tests the
   shared-m assumption directly instead of by sensitivity analysis, and measures the
   §6.2 focus-step drift against a second, independent depth scale.
3. **A pupil-diameter or exposure-loss bench measurement.** Combined with M84b's measured m
   this pins `p` outright instead of bracketing it, and gives B at *any* magnification — the
   thing M5 explicitly could not do, and now the dominant uncertainty in facts 1149 and 1150.

**On the milestone's framing.** The dispatch was substantially right: the ruler does buy
absolute scale, it does buy a metric focus axis, and it is a better ground-truth substrate than
a plain tilted target. Four corrections: **inverse** depth is affine, not depth (§5.1); the
teleconverter ceiling is 2.8×, not 2.0× (§4.1, SYNTHESIS fact 1148 records the same correction
independently); the converter is a Viltrox and the corpus's SEL20TC citation is false (§4.1);
and the binding limit here is **framing, not diffraction** (§7.3). The dispatch also asked me
to say if a different stack were a better substrate — it is not; the angled ruler is the right
one, and the improvement needed is a re-shoot of the same idea at better framing.

---

## 14. Reproduction

From `experiments/M84b-ruler-metrology/`, with `$env:PYTHONIOENCODING='utf-8'`:

```powershell
python src\12-ticks.py flat            # zero-tilt control FIRST, as registered
python src\12-ticks.py ang
python src\13-fit.py flat ang
python src\14b-hierarchy.py            # the pitch decision
python src\15-closure.py               # geometry: tilt, m, f, Z0, depth scale
python src\16-focusaxis.py             # um/frame, drift, calibrated placebo
python src\17-depthmap.py              # 2-D plane law + the depth map
python src\18-controls.py              # 4 controls; exit 0 required
python src\19-m5-crosscheck.py         # M5 transfer, fact 1149 propagation
```

Logs in `out/*.log`; machine-readable results in `out/*.json`. Runtime is dominated by RAW
decoding at ~0.052 s/frame; the 299-frame angled stack streams in ~52 s per pass.
`17-depthmap.py --refit` reuses `out/17-bands.npz` and skips decoding entirely.

### Rule-22 checklist

| Rule | Discharged by |
| --- | --- |
| 4 (no per-pixel argmax as evidence) | all response statistics are column- or block-aggregated over ≥ 180 rows; the only per-pixel index used is §7.4's mask term and §7.5's deliberate naive-baseline probe, both disclosed as such |
| 8 (corpus read-only) | nothing written to `D:\personal\macro`, `D:\macro-dark-frames`, `C:\dev\macro`; guards recorded in `out/tilted-readonly-before.json`, `out/control-readonly-before.json` |
| 9 (pre-register before measuring) | `PREREGISTRATION.md` committed `26ab710` before step 12 ran |
| 10 (controls that can fail) | `python src\18-controls.py` — 4 tests; S2 must fail and G1/G2 are byte-planted and restored; §10 |
| 13 (design against the real subject) | `11-native-aif.py`; scene geometry in §7.1 and §7.4 |
| 17 (uncertainty on every physical quantity) | §5.2, §6, §7.3, §8.3 — every table carries a bootstrap sd or an interval |
| 20 (namespace foreign numbers) | "M5's B ∈ [2.41, 3.06]", "SYNTHESIS fact 1147/1148/1149", "M81 §11 line 347", "`F-camera-lens-optics.md:13`" throughout |
| 24 (disclose deviations) | §11 |
| 28 (candidate facts, not silent edits) | §12; `SYNTHESIS.md`, `AGENTS.md`, `captures-needed.md` untouched |
| 32 (RAW handling) | `quad_green()` copies `raw_image_visible` inside the `with`, black level from `black_level_per_channel` |
| 36 (self-tests announce their count) | `python src\18-controls.py` prints its test count and `4/4`, exit 0 |
| 38 (label every claim) | MEASURED / DERIVED / ARGUED / UNVERIFIED throughout |
| 39 (report the negative) | §3 Z3, §6.1 placebo, §6.2 drift, §7.3 L3, §8.6 under-sampling, §9 the bug |
| 40 (read the source) | M5, `F-camera-lens-optics.md`, SYNTHESIS facts 1146–1150, disciplines 573–577 and M81 §11 all read at source; the dispatch's descriptions were checked, and four were wrong (§13) |
| 41 (milestone ledger) | §1 — the stem collision disclosed, contamination declared in both directions, timestamped |
| 42 (`git commit -- <paths>`) | only `experiments/M84b-ruler-metrology/**` and `docs/research/M84b-ruler-metrology.md`; never `git add`; never pushed |

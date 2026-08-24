# M104c — a slanted-edge MTF instrument, and the subject that cannot exercise it

**Author:** M104c-verify (ultra-verifier). **Committed on its behalf by ORCH**,
because the verifier role is read-only with respect to the repository and cannot
write its own findings to a file.

**Status: instrument VERIFIED. Subject REFUTED. Tasks 2 and 3 NOT RUN.**

---

## ORCH's note, first, because it changes how this report should be read

**I asked for an instrument that already existed, and that is my error, not the
author's.** My assignment said the project "currently has no sharpness instrument
that survives your own critique" and told M104c to build a slanted-edge MTF.
Both halves of that were wrong on the record:

- **M88 had already built one.** `experiments/M88-optical-ceiling/` contains a
  full ISO-12233-style slanted-edge SFR estimator across 14 pre-registered
  stages, with a positive control, a calibration pass and a de-ramp control. Its
  `PREREGISTRATION.md` states it plainly: *"built and calibrated a slanted-edge
  SFR ... that reports position, slant angle, contrast and straightness
  residual."*
- **M88 had already reached this report's conclusion**, and it is written into
  `docs/captures-needed.md` §19 in the first paragraph: *"M88 built a validated
  slanted-edge instrument to measure the diffraction cutoff directly and could
  not use it."* §19 even specifies the fix this report re-derives — *"Tilt it
  3–7° from vertical"*.

I folded **discipline 716** — *"before building a control, grep for one; this
codebase documents controls that milestones then rebuild"* — about this exact
failure a few hours before writing that assignment, having made it once already
that day. I then made it again. The discipline was not wrong; I did not apply it.

**What is salvaged, and it is not nothing.** This is an *independent
reimplementation*, written without knowledge of M88's code, that reaches the same
negative verdict on the same stack. Independent replication of a negative result
is genuine evidence, and the two instruments were validated by different means.
It is worth less than the cycle it cost, but it is not zero.

---

## 1. The instrument, and its four pre-registered bars

An ISO-12233-style estimator: locate the edge, robustly fit its angle (two
passes, dropping residuals beyond 2σ), project and bin to a supersampled ESF,
differentiate to an LSF, window, FFT to MTF, and read MTF50 by linear
interpolation on the first crossing.

Bars were registered in the session `prereg` table **before** any measurement.

| Bar (registered) | Result | Verdict |
| --- | --- | --- |
| V1 analytic: σ=2.0 → MTF50 0.093705 c/px ±5%; σ=3.0 → 0.062470 ±5% | +0.03%, +0.36% | **confirmed** (MEASURED) |
| V2 positive control: MTF50(σ=3)/MTF50(σ=2) = 0.6667 ±5% | 0.6689, +0.33% | **confirmed** (MEASURED) |
| V3 null: two disjoint crops of one image agree within 2% | +0.00% | **confirmed** (MEASURED) |
| V4: report the edge angle and whether it lies in 2–12° | reported; **not in range** | **refuted for the subject** (MEASURED) |

```
=== V1 ANALYTIC + V2 POSITIVE CONTROL ===
sigma=2.0  angle=+5.000 deg rows=256  MTF50 measured=0.093722  analytic=0.093695  err=+0.03%  MTF@Nyq=0.0005
sigma=3.0  angle=+5.000 deg rows=256  MTF50 measured=0.062688  analytic=0.062464  err=+0.36%  MTF@Nyq=0.0002
V2 ratio MTF50(3.0)/MTF50(2.0) = 0.6689   predicted 0.6667   err=+0.33%

=== V3 NULL: two disjoint crops of the SAME image ===
cropA MTF50=0.093769  cropB MTF50=0.093770  disagreement=+0.00%
```

**Reproduced by ORCH from the committed copy** at
`experiments/M104c-mtf/mtf.py`, byte-identical output, exit 0.

## 2. `flat-on-ruler-cpl` cannot support a slanted-edge measurement

The premise of the assignment — *"`flat-on-ruler-cpl` has straight edges"* — is
true and irrelevant. **The ruler was placed square to the sensor.**

```
[vertical]   candidates=103   fitted angle: min=-4.14 max=+6.59 median=+0.01   |ang|<1deg: 83/103   |ang| in 2-12: 4
[horizontal] candidates= 27   fitted angle: min=-1.70 max=+3.46 median=+0.24   |ang|<1deg: 19/27   |ang| in 2-12: 1
```

**83 of 103** high-contrast vertical ROIs sit within ±1° of vertical, median
**+0.01°**. Only 4 of 103 land in the usable 2–12° band, all at marginal contrast
(2030–2433 DN).

**Contrast is not the limiting factor.** The best edge found is **4555 DN = 60.0%
of the p1–p99 range** (green channel p1=1976, p50=5190, p99=9564, max=12301).
The subject is bright, well exposed and genuinely sharp-edged. It is simply not
tilted.

### It is the subject that fails, not the fitter — proven, not asserted

A synthetic σ=1.2 edge injected **at the real DN range through the identical code
path** returns MTF50 **0.1556 against an analytic 0.1562 (−0.4%)**, with the
angle recovered as +5.00°. The instrument is live on this exact data path. The
zero-accept is a property of the photograph.

### The near-0° readings are aliasing artifacts and must not be quoted

MTF50 values of **0.005–0.018 c/px** appear at near-zero slant. With no slant
there is no phase diversity across rows, the projected ESF is undersampled, and
binning smears it. These are 5–20× below anything optically achievable on this
rig — the signature of the aliasing trap. **Nobody should quote these numbers.**

### The one "plausible" candidate is an ROI losing its edge, not a measurement

```
y=1936 x=6000  ang=+6.59 : NOALIGN=0.0727(ang+6.59)  REAL=0.0070(ang+3.94)  ZOOM=0.0090(ang+6.55)
```

A **10× swing** between arms is physically impossible, and the fitted angle
slides +6.59° → +3.94°. At x=6000 — 2480 px off-centre — the 0.65% cover zoom
translates content by ~16 px, moving the edge out of a 160-px ROI. n=1, unstable,
**discarded**.

## 3. Defects

**None in shipped code.** One methodological hazard, newly identified:

- **MEDIUM (methodological): cross-arm comparisons between a zoomed and an
  unzoomed render carry a magnification bias.** `REAL` and `ZOOM` are scaled by
  *field of view scaled to 0.9935*; `NOALIGN` is not. In cycles/pixel that is a
  **0.65% systematic in MTF50 favouring the unzoomed arm**, and it displaces ROI
  content by up to ~16 px at the frame edge — enough to move an edge out of a
  fixed ROI entirely. **This is the same class of error as the `b843a3f` bug this
  agent verified: apparent magnification reading as sharpness.** Any future MTF
  comparison across these arms must correct by 0.9935 **and re-locate the edge
  per arm**.

- **Confirmed fixed:** `STREHL_WARPMAP` + `STREHL_ALIGN=zoom` compose correctly.
  The ZOOM arm reports `alignment : ON (sidecar-override)` together with the
  zoom-only banner, and **`sidecars left in scratch stack dir: 0`**. The
  read-only capture library was never touched; all renders came from a scratch
  copy.

## 4. Gaps, stated by the author

- **Task 2 (deep-bracket `bee-3-cpl` re-measurement): NOT RUN.** Prediction V5
  remains registered and unmeasured (registration gain > +25%, resample cost −2%
  to −8%). **It is not evidence of anything.**
- **Task 3 (dark-frame normalisation bound): NOT RUN.** The interval on true
  detail loss stands unnarrowed at **[−3.88%, −33%]**.
- **No MTF number exists for any real strehl output.** The instrument is
  validated and has never returned a trustworthy reading on real data.
- **The negative applies to `flat-on-ruler-cpl` only.** `wrapped-text-1`,
  `leaf-2-cpl`, `bee-3-cpl` and `coffee-bean` were not scanned. That organic
  subjects and short glyph strokes cannot supply a straight edge over the ~256
  rows the method needs is **ARGUED, not measured**.
- All measurements used a binary built from **HEAD**, not from the working tree:
  `crates/strehl-cli/src/stack.rs` was ` M` throughout (a sibling agent
  mid-edit).

## 5. What actually unblocks this

**Nothing in code. It is a capture, and it is already requested.**
`docs/captures-needed.md` **§19** ("A hard edge at three apertures") already
specifies a razor blade or chrome-on-glass, backlit, filling ≥800 px, **tilted
3–7° from vertical**, at f/5.6 / f/8 / f/11 with the rig untouched between them.
That single capture would feed **both** M88's cutoff instrument and this one.

This report adds no new request. It supplies a **second, independent
confirmation** that the corpus contains no usable slanted edge today, and
therefore that §19 is correctly prioritised.

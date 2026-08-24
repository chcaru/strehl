# M102 — PREREGISTRATION

Written and committed **before any measurement arm was run.** The only thing
run before this file existed was `src/s1_spike_dng.py`, a feasibility spike
declared as such in its own docstring: it settles whether the shipped decoder
accepts a synthetic file at all, which decides the ARCHITECTURE, not a result.
No bar below depends on any number it produced.

Milestone: build a generator of synthetic focus stacks physically faithful to
this rig, using constants this project has already MEASURED, so that ground
truth is *specified* rather than designed-and-hoped-for.

---

## 0. Architecture decision, made before the bars and argued in the report

**Out-of-tree: a Python generator under `experiments/M102-simulator/` that
emits DNG files the shipped `strehl` binary ingests unmodified.**
Not `crates/strehl-core/src/simulate.rs`. Four reasons, the first decisive:

1. **I am barred from editing `lib.rs`.** An in-tree `simulate.rs` could not be
   declared as a module, so it would not compile and could not be tested
   tonight. An untested generator is worth less than none, because it invites
   trust it has not earned.
2. **Emitting *files* is a strictly stronger test than handing arrays to
   `merge`.** An in-crate generator that produces arrays bypasses decode,
   black-level subtraction, the CFA and the demosaic — and requirement 4 names
   CFA sampling as "the single most common way a synthetic stack fails to
   express a real defect". The file route exercises every stage the real
   capture exercises.
3. **Collision risk.** Roughly ten agents are live in the Rust tree tonight.
4. **Requirement 5 asks the generator's ISO to come from my own
   `sensor_for()`**, which is Python (M92b, `s13_sensor_guard.py`). In-tree
   would require reimplementing it, and a reimplementation is exactly the
   confound M92 was warned about.

Acknowledged cost: **no CI test**. Mitigation proposed in the report — commit
one small synthetic DNG as a fixture so a future in-tree test can assert
against it without depending on Python.

---

## 1. Bars — round-trip

The shipped selector `strehl argmax-baseline --index-map` emits a per-pixel
winning frame index. The generator plants a per-pixel depth, and the optics
model maps depth to the frame at which that depth is in best focus. That
planted index is the truth.

**Region of definition.** Fact 73 MEASURED that the focus operator reads an
identical value at sigma = 0,1,2,3 on an untextured edge: the focus measure is
*undefined* on smooth regions. Scoring there would measure the operator's
blind spot, not the simulator. So the round-trip is scored on the **textured
mask only**, which the generator knows exactly because it planted the texture.
The smooth region is scored separately and *no bar is set on it* — it is
reported as a descriptive number.

- **R1 (primary).** Median absolute index error on the textured mask
  **<= 1.0 frame**.
- **R2.** Fraction of textured pixels within **+/- 2 frames >= 0.90**.
- **R3 (bias).** Median *signed* index error within **+/- 1.0 frame** of zero.
  R3 is the one that catches a systematic schedule offset; R1 alone would not
  distinguish a one-frame shift from symmetric scatter.
- **R4 (occlusion, descriptive, no bar).** The same three numbers computed on
  the occluded band alone. The corpus has no ground truth for occlusion and
  the shipped merge "does not yet model occlusion" (its own `stack --help`).
  A bar here would be a bar on a known-unmodelled effect. Reported, not gated.

Verdict language: round-trip **PASSES** iff R1 and R2 and R3 all hold.

## 2. Bars — realism, on statistics that do not depend on scene content

Compared against real `bee-3-cpl`. Every bar is a *ratio* or an *absolute
difference in a normalised unit*, because the synthetic scene is not the real
scene and any bar on an absolute scene-dependent quantity would fail for
reasons unrelated to the hypothesis (my own discipline 609).

- **N1 — noise.** Per-frame measured noise vs the calibrated prediction
  `sigma^2 = g*S + (RN*g)^2` at that frame's own mean level, with `g` and `RN`
  from `sensor_for()` and the stack's true EXIF ISO. Bar: **measured/predicted
  within [0.90, 1.10]** on the synthetic stack. The same ratio is reported for
  the real stack for context; **no bar is placed on the real stack**, because
  a failure there is a fact about the sensor model, not about my generator.
- **N2 — through-focus response width.** The half-width of the normalised
  through-focus focus response, in frames, at a matched sampling density.
  Bar: synthetic width within **a factor of 2.0** of the real width. A factor
  of two is deliberately loose: the real stack's focus step is set by the
  owner's rail and mine is a free parameter, so a tight bar here would be a
  bar on a parameter I chose, not on physics.
- **N3 — disconnected competitive set.** M96 MEASURED 25.247% of pixels with
  a disconnected competitive set on the real stack, mean gap 29.12 frames.
  Reported for the synthetic stack. Bar: the synthetic fraction is
  **non-zero and below 60%**. This is a weak bar on purpose — it asserts the
  simulator *produces the phenomenon* without asserting it reproduces a
  number that depends on the real scene's depth complexity.
- **N4 — focus-measure histogram.** Reported as a shape comparison. **No
  numeric bar.** Declared here so that a favourable-looking histogram cannot
  be promoted to evidence after the fact.

Verdict language: realism **PASSES** iff N1 and N2 and N3 hold. N4 is
descriptive by pre-registration.

## 3. Bars — a defect it must catch

Per discipline 615, **the plant must not perturb the mechanism it is measuring
through.** The round-trip measures the index map through the focus operator,
so a plant that changes the focus content would capture the very election it
is meant to bias.

- **D1 — one-frame index offset.** The generator renders the defocus schedule
  shifted by exactly +1 frame relative to the index it records as truth. Every
  frame is a physically valid frame of the same stack; no pixel statistic, no
  noise level and no texture changes. Only the *correspondence* moves.
  **Bar: R3 (median signed error) must go red, and must land within +/- 0.5
  of -1.0 or +1.0 frame.** Recovering the sign and magnitude is the check;
  merely going red is not enough, because a plant that reddens the bar for the
  wrong reason is worse than no plant.
- **D2 — unmodelled warp.** An extra global scale of 0.5% of the half-diagonal
  (~21 px) is applied to the second half of the stack only, on top of the
  modelled breathing track. Noise, texture and defocus are untouched.
  **Bar: R1 must go red (median absolute index error > 1.0 frame).**

Both plants are applied by a `--plant` flag on the generator, so no file is
edited to run them and nothing has to be restored afterwards.

## 4. Bars — a no-op it must ignore

Per my own discipline 618: a guard proven only against true positives has an
unmeasured false-positive rate.

- **Z1 — reseed.** Regenerate with a different noise RNG seed and nothing
  else. **Bar: R1, R2, R3 all stay green.**
- **Z2 — harmless tag.** Regenerate byte-identically except for an extra
  valid-but-ignored TIFF tag (ImageDescription) in every file.
  **Bar: R1, R2, R3 all stay green, and the recovered index map must be
  bit-identical to the unplanted arm.** Z2 is the stronger of the two: it
  asserts the instrument is not sensitive to a change that carries no physics.

## 5. What counts as the milestone failing

Stated now so it cannot be renegotiated later:

- If the round-trip fails R1/R2/R3 on the unplanted arm, the simulator is
  **NOT ESTABLISHED** as an instrument, regardless of how good the realism
  figures look.
- If D1 or D2 fails to go red, the round-trip is **not a check** — it has
  never been made to fail — and the milestone reports NOT ESTABLISHED even if
  every other bar is green.
- If Z1 or Z2 goes red, the instrument has a false-positive rate and the
  milestone reports that number rather than suppressing it.
- **"Where this simulator lies" is a required deliverable.** If it is empty,
  the milestone has failed to look.

## 6. Declared in advance: known infidelities I already expect

Listed now so they cannot be presented later as discoveries.

1. The colour matrix written into the DNG is plausible, not measured on this
   body. It affects `--srgb` rendering only; every bar above is measured on
   the linear binned output, which does not use it.
2. `lambda = 0.55 um` is DERIVED by inverting fact 12's extinction point, not
   measured. It reproduces fact 12 to three digits.
3. The defocus PSF is a filled disc convolved with the diffraction PSF. Real
   defocus at these apertures has aberration structure this does not model.
4. The scale track is linear in frame index, because fact 1177 MEASURED the
   drift as smooth and monotonic — but "smooth and monotonic" does not imply
   "linear", and I have not measured the curvature.
5. No dust, no hot pixels, no fixed-pattern noise. Fact 610 MEASURED FPN at
   rho = 0.3094 of single-frame noise variance on this body; the generator
   models only the shot + read terms. This one is likely to matter and is
   expected to show up in N1.

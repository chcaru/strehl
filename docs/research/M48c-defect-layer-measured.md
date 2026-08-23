# M48c — the sensor defect layer, measured

**Facts, disciplines and open questions in this file are numbered LOCALLY from 1.**
The orchestrator renumbers on fold.

Every claim is labelled **MEASURED**, **DERIVED** or **ARGUED**.

Source data: the 242 dark frames at `D:\macro-dark-frames` (11 ISOs × 22 frames,
first two of each set dropped as settling per the owner's instruction, n=20), and
the 19-frame `coffee-bubbles` stack at `D:\personal\macro`. Both read-only;
neither was written to. Scripts: `experiments/m48c-defect-layer/src/01`–`08`.

---

## 0. The brief's premise, and why it should be read before the numbers

**Fact 1 (MEASURED).** The brief states "Nothing has ever planned it, and you are
the only agent who has worked the sensor model… nothing has used [the darks] for
this." That is wrong in three independent places, and I checked before measuring
anything:

- `experiments/m22-hot-pixels/` (6 scripts) uses **these exact 242 darks for
  exactly this purpose**. `docs/research/M22-hot-pixels-measured.md` reports
  11,393 hot pixels (0.0346%), recurrence-across-ISO-groups as the
  discriminator (fact 160), and in-situ impact ≤0.39σ (fact 161).
- `experiments/m29-static-defects/` (6 scripts, committed outputs) and
  `docs/research/M29-static-defects-measured.md` settle dust: D = 0.999 at
  n_eff ≈ 3 (fact 230), a detection limit of 32–50% shadow against real dust of
  1–15% (fact 232), and a flat-field capture spec.
- **SYNTHESIS §8 already carries the "dust and hot pixels" clause struck
  through**, annotated "now MEASURED, and worse than stated", citing M22 and M29
  by name.

**Fact 2 (ARGUED).** The genuinely unmeasured part is narrower than the brief and
both prior reports name it precisely. §8: "*The trail-smearing half of the
original risk stands unmeasured*". M22 §7: "*Smearing under warp… was not tested
at all.*" That is the brief's question 3, and it is the only part of this
commission that was actually open. This report spends its effort there.

---

## 1. Detection criterion, pre-registered

**Fact 3 (MEASURED).** The criterion was committed in
`src/01-defect-census.py`'s docstring at commit `a2e1598` **before the script was
run**, so "pre-registered" is a checkable claim rather than a courtesy. Two
criteria were declared:

- **A — model-only.** Flag a pixel whose temporal-mean excess over its four
  same-plane neighbours exceeds `K·σ_pred/√T`, with σ_pred from
  `profile.rs`/`noise.rs` at S = 0. Declared false-positive rate at K = 6 on a
  Gaussian: **0.0081 pixels per plane per ISO**.
- **B — robust.** The same statistic with σ estimated by 1.4826·MAD *of the
  observed excess map*, K = 6, and a recurrence requirement of ≥ 6 of 11 ISOs.

**Fact 4 (MEASURED).** Criterion A flagged **4,965–15,599 pixels per plane per
ISO** against its predicted 0.0081 — an over-flagging factor of order 10⁶. The
pre-registration explicitly predicted this failure and named its cause (the
model has no DSNU term, so it cannot describe the pixel-to-pixel spread of a
dark frame). Criterion B is used throughout. A is reported because a criterion
that was declared and then failed is evidence about the model, not clutter.

---

## 2. The census (brief question 1)

**Fact 5 (MEASURED).** Hot defects meeting criterion B with recurrence ≥ 6/11:
**13,650 of 32,947,264 pixels = 0.0414%**. Excluding the one-pixel border the
highpass cannot evaluate, 13,630.

**Fact 6 (MEASURED).** This **independently corroborates M22 to 19.8%**
(0.0414% against M22's 0.0346%) by a different criterion and a different code
path. Agreement at that level across two independent criteria is the useful
content; the residual 19.8% is criterion choice, not disagreement about the
sensor.

**Fact 7 (MEASURED).** **Cold/dark defects: 131 = 0.0004%**, i.e. **104× rarer
than hot**. M22 never tested for these. They are real but negligible.

**Fact 8 (MEASURED).** **99.8% of defects are isolated singletons** (13,591 of
13,620 connected components). **The largest cluster on the sensor is 3 pixels.**
There are no column defects, no row defects, and no blobs. A defect map for this
sensor is a list of isolated coordinates; no cluster-aware machinery is needed.

**Fact 9 (MEASURED).** The population is **grossly asymmetric by sensor row
parity**. Recurrent defects per plane: **R 101, G1 98, G2 7,757, B 5,674.** In
RGGB the quad is `R G1 / G2 B`, so R and G1 are even sensor rows and G2 and B are
odd. **Odd rows carry 68× more recurrent defects than even rows** (13,431 vs
199). The same asymmetry appears in the raw per-ISO flag counts at all 11 ISOs,
at a weaker 2.1–4.7×.

**Fact 10 (ARGUED).** Thermally generated charge has no mechanism to prefer odd
rows. An interleaved/dual readout chain does. This points at the readout
architecture rather than the photodiode array, and it means any defect map for
this body must be stored in **sensor** coordinates with known row parity — a map
resampled or flipped without tracking parity would be silently wrong. I did not
identify the mechanism further; it was not commissioned.

---

## 3. Stability across ISO (brief question 2), and what it turned up

This is where the milestone stopped being a census.

**Fact 11 (MEASURED).** My first two attempts at "are the defects stable across
ISO" were both uninterpretable, **for the same reason, and I did not see it until
the second one contradicted the first**:

- Thresholding at `K·σ_obs` (scripts 01/02): counts **rise** ~20× from ISO 50 to
  ISO 2000.
- Thresholding at a fixed **electron** excess (script 03): counts **fall**, by
  350× across ISO 400 (4,198 → 12 at 12 e⁻).

Both thresholds move with ISO. Neither experiment can distinguish "more defects
at high ISO" from "the same defects seen through a different instrument". This
is SYNTHESIS discipline 331 (a precision that cannot see a systematic it shares)
in a third costume.

**Fact 12 (MEASURED).** Script 03's one flat column is worth keeping: at a
**48 e⁻** threshold the count is **exactly 3 at every ISO ≥ 200** (2–3 at ISO
50/100), spread 1.00×. This independently reproduces M22's "only **3 pixels** on
the entire sensor are both always-hot and above 100 DN dark excess — there is no
severe tail", by a different method and in a different unit.

**Fact 13 (MEASURED).** Script 06 removes the threshold entirely: take the
**same fixed 13,630 pixels** at every ISO and report their median excess. Dark
current is generated at the photodiode, *before* the analogue gain, from
temperature and integration time — so a fixed pixel set must imply the same
electron excess at every ISO. Measured, through `profile.rs`'s
`g = max(iso,100)/436.8`:

| ISO | g | median excess DN | implied e⁻ |
|---|---|---|---|
| 50 | 0.2289 | 1.4219 | 6.211 |
| 100 | 0.2289 | 1.3500 | 5.897 |
| 200 | 0.4579 | 3.0563 | 6.675 |
| 250 | 0.5723 | 3.6219 | 6.328 |
| 400 | 0.9158 | 2.8219 | **3.081** |
| 500 | 1.1447 | 3.6281 | 3.170 |
| 640 | 1.4652 | 4.3594 | 2.975 |
| 800 | 1.8315 | 5.4562 | 2.979 |
| 1000 | 2.2894 | 7.1312 | 3.115 |
| 1600 | 3.6630 | 10.6969 | 2.920 |
| 2000 | 4.5788 | 14.4000 | 3.145 |

Two flat plateaus — 5.90–6.67 e⁻ below ISO 400, 2.92–3.17 e⁻ at and above it —
with the step falling **exactly at `second_base_iso = 400`**.

**Fact 14 (MEASURED).** Fitting `excess_DN = c + e·g` separately in each mode:

- high mode (ISO ≥ 400): **c = −0.055 DN**, e = 3.0765 e⁻, residuals ≤ 4.8%
- low mode (ISO < 400): **c = −0.125 DN**, e = 6.6855 e⁻, residuals ≤ 4.1%
- all 11 together: c = +0.858 DN, e = 2.79 e⁻, residuals up to **32.2%**

Within each mode the additive term is **consistent with zero** and the excess is
purely proportional to `g`. Across the boundary the constant of proportionality
steps by **6.6855 / 3.0765 = 2.174×**. A single model spanning both modes fits
badly. This **refutes** my own working hypothesis that a constant DN-domain
offset (M48 Finding 5's ~0.49 DN floor) was responsible: had it been, `c` would
have come out near +0.5 DN in both fits, and it did not.

**Fact 15 (MEASURED).** The step survives every attempt to break it (script 08,
8 variants): out-of-sample selection using only high-mode detections (ratio
2.51), only low-mode detections (3.65), amplitude strata (2.61–2.67), and
recurrence thresholds 3/6/9/11 (2.54–3.19). **The ratio is never near 1.** Its
drift across variants is a plane-weighting artefact — script 06 averages
per-plane medians, script 08 pools planes, and the plane mix changes with
selection strictness. The two independent within-mode fits of fact 14 are the
better-conditioned estimate, so **2.17× is the number I stand behind**, with the
variant spread saying the uncertainty is roughly ±0.3, not ±0.02.

**Fact 16 (MEASURED).** The two mundane explanations are excluded from EXIF:

- **Exposure**: all 11 groups are **1/100 s**, spread 1.000×. Dark current is
  proportional to integration time; identical time cannot produce a 2.17× step.
- **Temperature**: all 242 frames were shot within **3 minutes 23 seconds**
  (14:47:03 → 14:50:26), and the ISO order is **scrambled with respect to gain
  mode** — 400, 800 and 1600 were shot *before* 50, 200 and 250. No monotone
  thermal drift can produce a step that sorts perfectly by gain mode while being
  interleaved in time.

**Fact 17 (DERIVED).** Dark current cannot depend on the ISO dial. Therefore the
DN→electron conversion used above `second_base_iso` is wrong relative to the one
below it by **2.17×**. `profile.rs` models the dual-gain switch as a change in
`read_noise_e` alone: `gain_dn_per_e` is `iso.max(base_iso)/gain_divisor`, a
single straight line straight through ISO 400. The PTC that calibrated
`gain_divisor` was taken at **ISO 160**, in the low mode; every ISO ≥ 400 is
extrapolation.

**Fact 18 (DERIVED).** **This is a labelling failure, not an arithmetic one, and
the distinction is the whole point.** `read_noise_e_high` was fitted to dark
σ_DN *through this same gain relation*, so the product `RN_e × g` reproduces the
measured DN by construction. **Every DN-domain prediction of the shipped noise
model is unaffected.** What is not identified above ISO 400 is the *split*:
`gain_divisor` and `read_noise_e_high` are degenerate there and only their
product is measured. This is precisely the metric-validity class SYNTHESIS §5's
preamble calls the project's worst — the arithmetic is right and the column
heading is wrong.

**Fact 19 (DERIVED).** Read in electrons rather than DN, the high-mode read
noise is **≈ 2.69 e⁻** (1.2392 × 2.17), not 1.2392, and the dual-gain read-noise
improvement is **≈ 1.56×** (4.20 → 2.69), not the ≈ 3.39× the shipped constants
imply. **This qualifies my own M48 headline**: 1.2392 remains the correct value
to *ship*, because it is the value that makes σ_DN right given this gain
relation, but it should not be quoted as this sensor's physical read noise.

**Fact 20 (ARGUED).** A dual-conversion-gain sensor with a ~1.6× read-noise
improvement is ordinary; ~3.4× would be exceptional. The corrected reading is
the more physically plausible of the two. This is an argument from plausibility
and is **not** independent evidence — it is listed so it is not mistaken for
some.

**Fact 21 (ARGUED). I did not change the constants, and that is deliberate.**
Fixing this means making gain mode-dependent, which is a model *shape* change,
on the strength of one measurement made on **dark frames**. My own discipline
326, written last milestone, is that dark-frame numbers have twice failed to
survive contact with illuminated data. The conversion gain is a property of the
sense node and should apply equally to signal and dark electrons, so this one
*ought* to transfer — but "ought" is exactly what discipline 326 warns about.
What is shipped instead is documentation of the degeneracy plus a tripwire test.

**Fact 22 (ARGUED).** The measurement that would settle it is a **photon-transfer
curve at ISO 500 or 1000**, which the corpus can already support — 261 of 421
frames are at those two settings — and which nothing has run. That is a
zero-capture, existing-data experiment and it is the highest-value follow-up in
this report.

---

## 4. Does the merge already handle them? (brief question 3 — the one the owner cares about)

**Fact 23 (MEASURED).** **The shipped merge does not align, and the brief's
framing does not apply to it.** The brief's premise is "a hot pixel is fixed in
sensor coordinates while the subject moves under alignment". I verified against
code rather than the doc comment (fact 581's precedent): a workspace-wide search
for `fn align|warp|homography|affine|translate|shift_by|register\(|resample`
returns **no alignment implementation anywhere** — every hit is plugin *registry*
registration, the affine photon-transfer noise relation, or a capture-geometry
comment. `strehl merge --help` and `main.rs:98` agree: "It does not yet align,
deconvolve, reject outliers, or model occlusion."

**Fact 24 (MEASURED).** Empirical confirmation from the merged output itself: a
column-offset scan over −4..+4 comparing the defect map against the merged TIFF
peaks **unambiguously at offset 0** (contrast 33.0 against negative values at
every other offset). A warped pipeline would smear a sensor-fixed defect and
produce no such peak.

**Fact 25 (MEASURED).** Merge run on `coffee-bubbles` (19 frames, ISO 1000, gate
2.0): mean n_eff **2.109**, n_eff = 1 at **37.45%** of pixels, output 3516×2344
16-bit linear, exit 0.

**Fact 26 (MEASURED).** Defect amplitude in the merged output versus a plain
unaligned mean of the same 19 frames, **D = merged / mean**, rescaled by a
TIFF↔DN slope fitted on 200k random pixels: **D = 1.23–1.44**. The merge does
not dilute static defects. **This inverted my stated expectation**, which was
D = 1 exactly on the grounds that a non-aligning merge cannot move a defect.

**Fact 27 (MEASURED). The result in fact 26 is real but its obvious
interpretation is wrong, and a pre-registered control is what caught it.** The
merge is a sharpness *selector*, so it may lift every high-contrast pixel
relative to a mean — in which case a slope fitted on flat random pixels
under-corrects at every sharp pixel and D > 1 falls out for defects and genuine
detail alike. Script 05 was committed **before running** with the criterion:
draw non-defect control pixels matched to each defect's unaligned highpass
amplitude within ±10%, and compare. Measured on the plane with adequate
statistics (B, n = 4,766 defects, 6,184 matched controls):

| population | D |
|---|---|
| defects | 1.2251 |
| contrast-matched non-defect pixels | 1.3236 |
| **ratio** | **0.926** |

**Fact 28 (MEASURED).** Repeat draws of the control give 1.005 and 0.926 for the
same defect set — differing by 8% from nothing but the random control sample.
That bounds the method's own reproducibility better than any internal error bar
would. **The honest statement is D_defect / D_control = 1.00 ± 0.08.**

**Fact 29 (DERIVED). The answer to the brief's question is: neither best case nor
worst — the estimator is blind.** The shipped merge amplifies a static hot pixel
by 1.23–1.32× relative to a plain mean, and amplifies *genuine subject detail of
matched contrast by the same factor, within 8%*. It has no defect-specific
behaviour in either direction. It will therefore never remove a hot pixel, and a
defect map cannot be deferred to it.

**Fact 30 (ARGUED). This is the baseline that makes the alignment work
falsifiable, and that is its main value.** Today D_defect/D_control = 1.00 ±
0.08 because nothing moves. When alignment lands, a sensor-fixed defect *will*
land on different scene points in different frames while real detail does not,
so the ratio must fall below 1 if the estimator handles it and stay at 1 if it
does not. **Re-running script 07 unchanged after alignment is a ready-made,
pre-registered acceptance test for a subsystem that does not exist yet.**

**Fact 31 (MEASURED).** A separate mechanism, reported so it is not confused with
the estimator: the merged output is binned from one 2×2 quad per output pixel, so
its **green channel is (G1+G2)/2**. A G1-only defect therefore arrives at
**0.635× amplitude** (measured; ~0.5 expected) for reasons that have nothing to
do with the merge. All D measurements above are on **R and B only**, where the
quad→channel mapping is 1:1.

---

## 5. Dust (brief question 4) — scoped OUT, with reasons

**Fact 32 (ARGUED).** Dust should not be attacked in this milestone and I did not
attempt it. M29 has already measured it (D = 0.999 at n_eff ≈ 3; detection limit
32–50% shadow against real dust of 1–15%; the floor is scene texture with
exponent +0.025), and it is **blocked on flat fields that do not exist**
(`captures-needed.md` §4, scheduled). Building a dust detector before the flats
land would be speculative work of exactly the kind the brief warned against.
Note also that under a *non-aligning* merge, dust does not smear into trails at
all — it stays a fixed low-contrast attenuation, so the "harder half" of the risk
is not yet live in the shipped pipeline either.

---

## 6. The coordinate trap (fact 691), resolved by measurement

**Fact 33 (MEASURED).** rawpy reports a visible frame of 4688×7028 → plane
**2344×3514**; rawler, which the shipped pipeline uses, reports plane
**2344×3516**. Both are present in this milestone's outputs. I declared **rawpy
canonical** for the map, and every JSON carries `raw_visible_shape`,
`plane_shape`, `cfa_offsets` and `canonical_decoder` so a mismatch is detectable
rather than silent. The relationship was then **measured, not assumed**: the
offset scan of fact 24 peaks at 0, so rawpy's 3514 columns are the **leading**
3514 of rawler's 3516, and the two extra columns are trailing.

---

## 7. My own errors

**Error 1 (the worst).** Scripts 04 and 05 selected their defect pixels with
`hotmask & (hp > 0)`. `hotmask-*.npy` is a uint16 **eleven-bit ISO bitmask**
(bit 0 = ISO 50 … bit 10 = ISO 2000, max 2047), not a boolean map. numpy promotes
the bool operand to 0/1, so this **bitwise-ANDs to bit zero** and silently
selected "detected at ISO 50" instead of "recurrent". No exception was raised and
the resulting counts were plausible. It surfaced only when script 06 tried to use
the same array as a boolean index and blew up on a 215 GiB allocation. ISO 50 is
close to the worst possible accidental choice: a pull ISO reading out at base
gain, the least sensitive of the 11, at which only 26.1% of defects are detected.
Script 07 re-ran both measurements against the correct set **and against the
accidental one, side by side**, so the size of the error is a number: plane B's
answer moved 0.929 → 0.926 (immaterial), plane R's moved 0.991 → 1.385 but on
n = 74, too few to interpret. **The conclusion survived; it was not entitled to.**

**Error 2.** I pre-registered that `F = σ_obs/σ_pred > 1` at every ISO. It is
**below 1 at three of eleven** (0.95 at ISO 200, 0.93 at 1600, 0.91 at 2000). The
cause is my own M48 fact 556: σ_pred is built on the pooled-RMS read noise, which
is inflated by the hot-pixel tail, so the model over-predicts a *typical* pixel.
The prediction was wrong in a direction my own prior work had already explained.

**Error 3.** I hypothesised that a constant DN-domain offset (M48 Finding 5's
~0.49 DN floor) explained the electron-domain step, and it was refuted by the
within-mode fits of fact 14 (c = −0.055 and −0.125 DN, both ≈ 0, not +0.5). I
had constructed a story that connected two of my own findings, and the data
declined it. Recorded because the story was appealing and wrong.

**Error 4.** σ_obs is **quantised** and I did not anticipate it: the MAD of a mean
of 20 integer frames lands on exact multiples of 1/20 DN, so measured σ_obs takes
only the values 6, 6, 6, 7, 7, 9, 9, 10, 14, 17 twentieths × 1.4826. All four
planes fall in the *same* bin at most ISOs, so **σ_obs cannot resolve plane
differences at all** — which is why fact 9's asymmetry had to be read off flag
counts rather than off σ. Systematic of ±8.3% at ISO 50 falling to ±2.9% at ISO
2000. Disclosed in script 02's docstring when found.

**Error 5.** My "null set" placebo in script 08 is badly designed and I report it
as failed rather than quietly dropping it. Random non-defect pixels have ~zero
excess (−0.055 e⁻ low, −0.007 e⁻ high), and the *ratio* of two near-zero medians
is unbounded — it returned 7.78, which discriminates nothing. It does establish
that the pipeline has no additive pedestal, which is worth something, but it is
not the placebo I claimed. A correct placebo would inject a synthetic
DN-constant signal and confirm the pipeline reports a ratio of exactly `g_hi/g_lo`.

---

## 8. Disciplines

**Discipline 1.** *When a count changes with a threshold, check whether the
threshold moved.* Two experiments here gave opposite ISO trends (counts up 20×,
counts down 350×) purely because both thresholds were ISO-dependent. The fix is
not a better threshold but **no threshold**: measure a fixed population.

**Discipline 2.** *A signal with a known invariance is worth more than a signal
with a large amplitude.* Dark current's value is not that it is big — it is that
it **cannot** depend on the ISO dial. That single invariance breaks the
gain/read-noise degeneracy that dark σ_DN alone can never break, and it is the
only reason fact 17 exists.

**Discipline 3.** *A selective estimator lifts every high-contrast pixel, so any
"the estimator concentrates X" claim needs a contrast-matched control.* Without
one, script 04 would have reported that the merge concentrates defects by 23–44%.
With one, the defect-specific component is zero within 8%.

**Discipline 4.** *Estimate reproducibility by re-drawing, not by propagating.*
Two draws of the matched control differed by 8% — larger than any error bar I
would have computed analytically, and free.

**Discipline 5.** *A bitmask is not a boolean, and numpy will not tell you.*
`uint16_bitmask & bool_array` silently extracts bit 0. Any array whose semantics
are "bit k means condition k" should be loaded through a named accessor, never
indexed directly.

**Discipline 6.** *Exclude the mundane explanation from metadata before claiming
the interesting one.* Exposure time and capture timestamp are two EXIF reads and
they eliminated the two cheapest alternatives to fact 17. The interleaved capture
order was the stronger of the two exclusions and it was free.

---

## 9. Open questions

**Question 1.** **A PTC at ISO 500 or 1000 would settle fact 17 using data the
corpus already has** (261 of 421 frames). Is the 2.17× a conversion-gain change,
and if so is the low mode or the high mode the correctly calibrated one? The
ISO-160 PTC constrains only the low mode. This is the highest-value follow-up
here and needs no captures.

**Question 2.** If fact 17 holds, the **shot-noise term above ISO 400 is
over-predicted by √2.17 ≈ 1.47× in σ**, which affects the majority of the corpus.
I did **not** verify this against illuminated data and it does not follow from
the dark measurement alone. It should not be acted on until question 1 is
answered.

**Question 3.** What causes the 68× odd/even row asymmetry (fact 9)? It looks
architectural, and if it is, a defect map for this body must carry row parity
explicitly.

**Question 4.** SYNTHESIS question 159 asks whether applying M22's map changes
the FRC/censoring results. Facts 29 and 30 say the merge will not do it for you,
so that question is now live rather than hypothetical.

**Question 5.** M22's central limitation is untouched by this work and remains
the binding one: **the darks are 1/100 s while real stacks run 1/8 s to 5/2 s**,
up to 250× longer. Every number in this report describes the 1/100 s defect
population. M22 estimates only 5 of ~839 scene-independent defects detectable in
real frames appear in the dark map. **A defect map built from these darks is
complete for the wrong exposure**, and a dark set at working exposure is the
capture that would fix it.

**Question 6.** Is a defect map worth building at all? Facts 5, 8 and 29 together
say: 0.0414% of pixels, 99.8% isolated singletons, largest cluster 3 px, and the
merge will never remove them. That is a cheap subsystem — a coordinate list and a
neighbour median — but question 5 says the map to build it from does not exist
yet. My recommendation is to **defer the subsystem and take the dark frames at
working exposure first**, which is one capture request rather than a module.

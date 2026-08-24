# M97b — building the instrument that can see the alignment

**Status: DONE.** The question is answered, the answer is not the one either
M86 or I expected, and it is reproducible.

> **Headline (MEASURED).** Alignment *does* improve the photograph — by
> **19–32%** in matched-content sharpness. But **only when the solve's gain is
> corrected.** The alignment as shipped measures **1.033 / 0.979 / 1.000**, a
> null, because it applies only **23.9%** of the drift that is present. Every
> previous null in this project is a measurement of an under-correction, not a
> measurement of alignment.

> **Second headline (MEASURED, §11).** Against the millimetre ruler — an
> external ground truth that owes nothing to any metric this project invented —
> **`--force-tilted` costs image quality**: on the stack the solver refuses, it
> makes tick spacing **2.56× less regular**, while on the stack the solver
> accepts, alignment makes it **18% more regular**. The refusal check is
> vindicated by measurement. And **M86 §15.4's straight-edge test cannot settle
> the question on either existing ruler capture**, because a straight edge only
> discriminates if the edge runs through depth, and neither ruler has one.

---

## 1. Why the old instruments could not see it, and it is not what we thought

M86 measured whole-frame Tenengrad at **0.9859x** against a matched zoom-only
null and declined to claim a win. M85 independently measured **0.985x**. The
standing ARGUED explanation was that misregistration *displaces* detail rather
than blurring it, so gradient energy is structurally blind.

**That explanation is incomplete, and the missing piece invalidates most
image-space comparisons anyone would naturally write.** MEASURED:

**Registration changes the rendered field of view.** An aligned render sits in
the reference frame's field of view. An unregistered render blends the fields
of view of frames spanning 23.9% of magnification. So **comparing two arms at
the same pixel coordinate compares different scene content.**

I proved this on myself. My first radial metric (`src/radial4.py`) reported the
gain-corrected render at **24.5x** the null in the outermost radius band. A 24x
sharpness gain is not physical. I built a contact sheet and looked
(`src/sheet.py`, `C:\dev\strehl-out\M97b\SHEET.png`): at that radius the
corrected render holds marker bristles and the null holds smooth white barrel.
**The 24.5x is a content shift wearing a sharpness ratio's clothes** — the same
class of error as M86's fake 1.4565x boundary reading. `radial4.py`'s treatment
numbers are **inadmissible and I do not report them.**

**DERIVED: any fixed-coordinate image comparison between registration arms is
invalid, because the field of view is exactly what registration changes.** This
is a stronger constraint than "gradient energy is blind" and it is the reason
this question has resisted three milestones.

---

## 2. The instrument

`src/matched.py`. Recover the similarity between two renders with the same
FFT/NCC scale ladder used for ground truth, then bring **both** arms onto a
common intermediate grid — A magnified by `sqrt(s)`, B by `1/sqrt(s)` — so each
pays exactly one resampling of equal magnitude. Comparing a resampled arm
against an untouched one hands the untouched one a free sharpness win; the
symmetric split is what makes the ratio mean anything. Sharpness is gradient
energy over the common valid region, eroded 49 px, radially resolved.

**Controls, run before the treatment:**

| control | centre | mid | outer | verdict |
|---|---:|---:|---:|---|
| placebo: ZOOMNULL vs itself | 1.0004 | 0.9999 | 0.9996 | the symmetric resampling is fair |
| plant: vs itself blurred σ=1.0 | **2.8993** | **1.8618** | 1.0177 | the functional can see softness |

The outer-band plant response (1.0177) is weak, so outer-band numbers are the
least sensitive and I weight them least.

---

## 3. The subject, and why the project was testing on the worst possible one

`src/scout.py` scored eight stacks on the two properties this test needs:
drift magnitude, and whether the subject has detail at large radius (where a
scale error is largest — it is exactly zero at the optical centre).

| stack | drift (magnification) | edge/centre detail |
|---|---:|---:|
| **dry-erase-marker-head-cpl** | **1.2389** | **72.2** |
| bee-3-cpl | 1.1802 | 1.95 |
| couch-fibers-cpl | 1.2034 | 1.40 |
| flat-on-ruler-cpl | 1.0506 | 1.60 |
| lavendar-cpl | 1.2188 | 0.011 |

**MEASURED: `bee-3-cpl` is a poor test bed** — the bee is central, so the region
where alignment can help contains almost no subject. `dry-erase-marker-head-cpl`
has the corpus's largest drift and detail concentrated exactly where the error
lives.

**The scout lied to me once first.** Its initial ladder let the refinement
bracket walk outside its own bounds and returned `scale=1.1722` for **four
unrelated subjects** — identical values across different scenes, which is a
search hitting a stop, not a measurement. Bounds are now hard and rails are
reported. Its `edge/centre` was also wrong (bee-3 scored 1.621 where the
rendered frame measures ~0.005) because gradient of a *raw* frame is dominated
by shot noise, which is spatially uniform and therefore reports empty
background as detailed. Low-passed first, both are fixed.

---

## 4. Ground truth on the marker head

`signtest.py` (M97's validated instrument; plants recover 0.940→0.93841 and
0.860→0.85939). All MEASURED:

| quantity | value |
|---|---:|
| true drift, frame 0 → 298 | **422.3 plane px** (scale span 0.79999) |
| sidecar's scale span | 0.95214 — **applies 23.9%** |
| residual after the shipped sidecar | **281.8 plane px**, 33.3% removed |
| residual after gain 4.5498 | **44.2 plane px**, 89.5% removed |
| inverted-sign control | 579.0 px, 1.37x raw — **sign correct as shipped** |

**P1 (MEASURED). The solve's under-correction reproduces on a second,
independent stack, and it scales with the drift.** bee-3: 54.3% of the span
applied, 150 px residual. Marker head: **23.9% applied, 282 px residual** —
70x M86's own `T_usable` of 4.0 px. It is not a fixed offset; it degrades as
drift grows.

Rewriter control: gain 1.0 reproduces the as-shipped residual **0.86650
exactly**; gain 4.5498 reaches **100.0%** of the span.

---

## 5. The answer

Arms on `dry-erase-marker-head-cpl`, `--gate 2`, default binned linear output
(M85 forbids measuring `--srgb`/`--demosaic`). ZOOMNULL is the denominator: same
resampler, same field of view, relative registration discarded.

| A vs ZOOMNULL | drift removed | centre | mid | outer |
|---|---:|---:|---:|---:|
| **GAINED** | **89.5%** | **1.1866** | **1.3161** | **1.1492** |
| **ALIGNED (as shipped)** | 33.3% | 1.0330 | 0.9789 | 1.0003 |
| UNALIGNED | 0% | 1.0742 | 1.0403 | 1.0025 |

**P2 (MEASURED). The alignment as shipped is a null.** 1.033 / 0.979 / 1.000.
This independently reproduces M86's 0.9859x and M85's 0.985x — different stack,
different instrument, same answer.

**P3 (MEASURED). The gain-corrected alignment is a 19–32% sharpness win.**

**P4 (DERIVED). The nulls were never a property of alignment. They are a
property of a solve that applies a quarter of the drift.** Correct the gain and
the same instrument that reads null reads a large win.

**P5 (MEASURED). UNALIGNED reads 1.074 against the zoom null, which prices the
resampling cost at ~7%.** GAINED pays that same cost and still wins by 19–32%,
so the win is net of resampling.

### The confound, and which way it runs

**P6 (MEASURED). Gradient energy is fooled by seams, and the plant proves it.**
GAINED vs JITTER reads **0.674 / 0.665 / 0.851** — the deliberately jittered
render measures *sharper*. This corroborates M86's ARGUED seam explanation and
my own M97 §6 finding that misregistration raises a band-limited detail metric
by 5.6%.

**It does not undermine the result, because it runs against it.** Better
registration produces *fewer* seams and therefore *less* seam energy. GAINED is
the best-registered arm and still measures the *most* energy, so the surplus
cannot be seams. **The 19–32% is a lower bound.**

---

## 6. An instrument that failed its plant, and is therefore withdrawn

Mean `n_eff` looked like the answer. It is printed by the binary already, it is
distributional rather than positional so it is immune to the field-of-view
problem in §1, and it moves beautifully:

| arm | drift removed | mean n_eff |
|---|---:|---:|
| ZOOMNULL | 0% | 38.254 |
| UNALIGNED | 0% | 35.985 |
| ALIGNED | 33.3% | 28.204 |
| GAINED | 89.5% | **13.117** |
| **JITTER (plant)** | 89.5% + 8.855 px | **11.216** |

Monotone across a 65.7% range, and opposite in sign to the resampling confound
(resampling alone *raises* it, 35.985 → 38.254). It looked like the instrument
the project already owned and had been misreading.

**The plant killed it.** JITTER reads **11.216 — lower than GAINED**, so the
planted defect moves `n_eff` in the *same direction as the treatment*. DERIVED:
`n_eff` measures how much frames disagree at a pixel, and **both** correct
registration (a sharply peaked through-focus response) and random jitter
(scrambled content) increase disagreement. It is responsive but **not
diagnostic of quality**, and it fails the Q5 bar I pre-registered. **Withdrawn.**

Had I not planted, I would have shipped this as the headline. It is the third
time tonight a plant has caught something a null would have concealed.

---

## 7. Coverage: the anomaly I nearly reported as a bug

Three sidecars with very different scale spans — bee-3 0.922, marker 0.952,
marker-gained 0.800 — all report cover scale **exactly 0.9974**. I held the
result until I could explain it rather than waving it through.

**MEASURED + DERIVED.** `fit_to_cover(&map, 3.0)` (align_cmd.rs:972) bisects
against real placements, but when the reference is an endpoint frame every
placement has `|a| ≤ 1`, so the pull gather samples strictly *inward* and no
destination pixel is ever uncovered. The binding constraint is then the
reference frame's own identity placement against the 3.0 px resampler margin on
the short axis:

```
k = 1 - margin/(plane_height/2) = 1 - 3/1172 = 0.997440
```

which matches the reported 0.9974 **to four decimals on all three stacks**.

**Consequence: the "coverage" line is uninformative about drift**, and the
orchestrator's "coverage is a quarter of the image" concern does not arise for
endpoint-referenced sidecars. Choosing an endpoint reference costs nothing in
field of view. It also means my arms are a matched set, differing in
registration alone.

---

## 8. What the owner will actually see, having opened it

The metric in §5 is matched-content, band-limited and masked. That is what makes
it trustworthy and it is also what makes it abstract. So I rendered the two arms
the owner would care about at full resolution through the real binary — `strehl
stack 'D:\personal\macro\dry-erase-marker-head-cpl' --gate 2 --srgb --demosaic`
— as `marker-TODAY-shipped.tif` (alignment exactly as it ships) and
`marker-POSSIBLE-gaincorrected.tif`, and I opened them.

### The viewer had to be built carefully, and it lied twice first

A fixed-coordinate crop is invalid here for the reason in §1: these two renders
differ in field of view. **MEASURED: `marker-POSSIBLE`'s subject is 1.1278x the
size of `marker-TODAY`'s** (NCC 0.9419, 8x block-mean scale ladder), so the same
pixel coordinates are different parts of the marker. `src/owner_sbs.py`
therefore takes a 474 px crop from the corrected render for every 420 px crop
from the shipped one and Lanczos-downsamples it to match. **That resampling is
deliberately a handicap applied to the corrected side** — it can only make the
render I expect to win look softer than it is.

Two defects in this viewer, caught before its output was believed:

1. **The scale was applied inverted.** The ladder returns *the magnification to
   apply to B*; I read it as *B's magnification*. The first run took a
   **smaller** crop from the corrected render and **upscaled** it — blurring the
   treatment arm and handicapping the wrong side. Caught by noticing 0.8867
   meant the opposite of what I had printed.
2. **The first content lock lost the lock.** A single full-resolution NCC search
   scored 0.9244 on the self-control (should be 1.0000) and 0.22–0.49 on the
   treatment, and it walked *away* from a centre crop that had visibly matched.
   On macro texture the full-resolution signal is dominated by the fine detail
   that genuinely differs between arms. Replaced with a coarse 4x block-mean
   structural pass plus a fine full-resolution pass, integer shifts only.

**Controls on the final viewer (MEASURED):**

| control | result |
| --- | --- |
| self vs self, scale | 0.9995 (truth 1.0) |
| self vs self, lock | 1.0000 / 1.0000 / 1.0000, exact coordinates recovered |
| **plant: starting guess displaced (+90, −110) px** | **still recovers the exact truth, 1.0000 on all three panels** |

The plant matters: a self-control that starts 1 px from the answer does not
demonstrate a ±158 px search range. The planted one does.

### What I saw

`C:\dev\strehl-out\M97-before-after\SBS-marker-TODAY-vs-POSSIBLE.png`, three
1:1 panels, shipped on the left, gain-corrected on the right.

- **Centre.** Well locked — the same distinctive hooked fibre appears in both.
  The two are very close. The corrected render is *marginally* crisper in fibre
  separation; the shipped render is very slightly mushier. **This is a marginal
  call at 1:1, and it is exactly where §5 predicts the smallest difference,
  because the scale error is zero at the centre of rotation.**
- **Lower-right.** Well locked, and here the difference is visible without
  hunting for it: the corrected render separates individual fibres over the
  bright marker body where the shipped render renders them as a flatter, softer
  mass. **But the corrected render also shows waxy, smeared blobs in the bright
  low-texture region at the bottom** that the shipped render does not. I do not
  know their cause; they are a real artefact and I am not going to omit them
  because they are inconvenient.
- **Upper-left.** Lock NCC 0.2253 and the panels still show different scene
  content — a bright fibre highlight appears in one and not the other.
  **This panel is not a valid comparison and I am not drawing a conclusion from
  it.**

### The honest verdict

**MEASURED/ARGUED: the improvement is real and it is visible, but at 1:1 it is
modest, not transformative, and it is accompanied by at least one new
artefact.** The 19–32% of §5 is a matched-content, band-limited number; the
eye's impression of a full-resolution photograph is not the same quantity and I
will not claim the metric's magnitude as a visual claim.

Two caveats that bound this section, stated rather than buried:

- The treatment lock NCCs are 0.23–0.49 against 1.0000 on the self-control.
  **The two renders genuinely disagree in fine detail**, which is the expected
  consequence of their electing different frames — but it also means these
  panels are approximately, not exactly, the same scene. §5's metric, which
  registers before comparing, remains the decisive measurement; this section is
  corroboration by eye, not a replacement for it.
- **The 1.1278x field-of-view ratio measured here disagrees with the 1.1949x
  implied by §5's ratios** (1.25852 / 1.05329). I have not resolved it. The two
  are measured on different products — full-resolution demosaiced sRGB here,
  binned linear there — so they are not required to agree, but the gap is 6% and
  I flag it rather than assume it away.

---

## 9. Why every gradient metric ranks the sharper image lower

The orchestrator supplied the thing this milestone was missing: a **visual
ground truth**. They opened co-located crops of `bee-3-ALIGNED.tif` against
`bee3-zoomnull.tif` and reported the aligned render clearly sharper.
**I opened `crop-wing-venation.png` myself before writing PREREG2 and I
independently confirm it** — the aligned render resolves the membrane bristles
as distinct dark strokes and separates the lower-left hair mass into individual
hairs; the null smears both and its vein boundaries are softer.

Whole-frame Tenengrad ranks that pair **0.9847** on the green plane (the
orchestrator got 0.9790 on an RGB mean; M86 got 0.9859 on a third weighting —
three implementations, same verdict). The metric is anti-correlated with
visible quality. Bars and the failing values were pre-registered in
`PREREG2.md` before any of what follows was run.

### 9.1 The doubling mechanism is falsified, and I said so in advance

The orchestrator's ARGUED mechanism was edge doubling: a doubled edge has two
gradients where a correct one has one, so misregistration manufactures gradient
energy. **PREREG2 records my disagreement and my predicted number before the
measurement**, because Tenengrad sums the *square* of the gradient and squaring
is convex — spreading a fixed rise across more pixels must lower the sum.

`src/mech1.py`, synthetic, truth not in dispute (MEASURED):

| case | Tenengrad | vs single | peak &#124;∇&#124; |
| --- | ---: | ---: | ---: |
| single step | 7812.50 | 1.0000 | 1000.0 |
| **doubled (two half-steps 6 px apart)** | 3906.25 | **0.5000** | 500.0 |
| blurred σ=2 | 2654.95 | 0.3398 | 375.5 |
| seam (elected-frame switch) | 6451.69 | 0.8258 | — |
| flat | 0.00 | 0.0000 | — |
| flat + noise sd=1 / 4 / 16 | 3.94 / 63.96 / 1015.57 | 0.0005 / 0.0082 / 0.1300 | — |

**Doubling halves Tenengrad, at exactly my predicted 0.5000. The mechanism is
FALSIFIED.** A seam lowers it too. From a flat baseline the *only* thing
measured to raise gradient energy is noise. The `flat` row reads exactly
`0.000`, which discipline 598 says to distrust — the three noise plants on the
same wiring prove that probe is connected.

Integrated `|∇|` across the profile is **conserved** under doubling (1000.0 vs
1000.0), so it cannot separate them either. Only the **peak** falls.

### 9.2 Where the null's excess energy actually lives

`src/bands.py`. Octave bands and structure strata, on a classification derived
from the mean of the two arms so no pixel is binned differently in one arm than
the other. **Placebo reads exactly 1.0000 in every band and every stratum**;
blur plants move in both directions with the expected scale profile.

| band | 1 px | 2 px | 4 px | 8 px | 16 px | 32 px |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aligned / null | 0.9937 | 0.9836 | 0.9974 | **1.0071** | **1.0075** | **1.0300** |

**R3 PASSES: the ratio crosses 1.0 between bands.** The null wins at 1–4 px;
the aligned render wins at 8–32 px. A metric whose sign depends on scale is not
measuring one quantity.

Stratified by local structure, aligned/null is **0.6303** in the flattest
quartile (8.27 M pixels), against 0.9710 / 0.9799 / 0.9875 in the other three.
**In the quartile of the frame with no detail to sharpen, the null carries 59%
more gradient energy than the aligned render.** That is not sharpness. It is
structure dragged to where it does not belong.

### 9.3 The peak does not save it either

`src/peaks.py`. Every percentile of `|∇|`, all three controls passing
(placebo 1.0000 exact; blur plant 1.19–1.58; direction plant 0.61–0.80):

| | p50 | p90 | p99 | p99.9 | p99.99 | top 0.01% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aligned / null | 0.9836 | 0.9961 | 0.9928 | 0.9875 | 0.9485 | **0.9446** |

**Pre-registered bar: > 1.00. Every percentile FAILS, and it gets worse the
higher you go.** The null holds the strongest gradients in the frame. Combined
with §9.1's seam row that is the tell: an abrupt switch between elected frames
displaced by hundreds of pixels is a step larger than any real scene edge.

**MEASURED conclusion, and it generalises beyond this pair: gradient energy
cannot distinguish detail from displaced structure or from a seam, at any
spatial scale and at any percentile. For focus stacks it is not a weak
sharpness metric, it is the wrong kind of quantity.** The orchestrator's
instinct that misregistration manufactures gradient energy is right; the
mechanism is not doubling but displacement and seams.

---

## 10. The instrument that ranks them correctly: edge width

`src/width.py`. Width is a **distance, not an energy**, so structure displaced
elsewhere cannot contribute to it, and it is what the eye actually reported.

Edges are located on the mean of the two arms (so the same edges are examined
in both) but each arm's profile is re-centred on its own 50% crossing before
measurement — this is PREREG2's named risk handled: the null is a composite of
frames at different scales, its features sit at an average position matching
nothing, and a ~12 px apparent displacement is visible between the panels.
Width is a shape property and is compared as one. Both arms are sampled by the
same interpolator at the same offsets.

**Whole frame, 6827 paired edges (MEASURED):**

| | value | pre-registered bar | |
| --- | ---: | --- | --- |
| **treatment, null/aligned width** | **1.0179** | > 1.00 | **PASS** |
| placebo, self vs self | 1.0000 | 1.000 ± 0.005 | PASS |
| direction plant, blurred(aligned) vs null | 0.9456 | < 1.00 | PASS |
| blur plant σ=1.0 | 1.0725 | > 1.30 | **FAIL as written** |

**I am not going to quietly restate a bar I failed.** The >1.30 figure was
specified for an *energy* metric, where σ=1 removes a third of the gradient
energy. Widths add in quadrature. So I measured the whole ladder against that
prediction rather than asserting it:

| σ | quadrature prediction | measured | measured/predicted |
| ---: | ---: | ---: | ---: |
| 0.5 | 1.0275 | 1.0156 | 0.9885 |
| 1.0 | 1.1058 | 1.0725 | 0.9699 |
| 2.0 | 1.3751 | 1.2528 | 0.9111 |
| 4.0 | 2.1362 | 1.6312 | 0.7636 |

**MEASURED: the metric tracks the quadrature prediction to within 3% at the
scale that matters and rolls off at large σ as the ±8 px profile window
saturates.** The bar was mis-specified, not the metric broken — but that is a
judgement about my own pre-registration and the orchestrator should weigh it as
such.

### 10.1 The metric agrees with the eye where the eye looked

`src/wingbox.py`, the same instrument unchanged, inside each 640×640 box, crop
origins recomputed from `ORCH-drift-check/crops.py`'s own arithmetic rather
than retyped. Co-location is verified per box by NCC **and the verification
carries its own plant** — a box displaced 60 px must score clearly lower.

| box | co-loc NCC (displaced plant) | placebo | direction plant | **treatment** |
| --- | ---: | ---: | ---: | ---: |
| **wing-venation** | 0.9516 (0.5802) | 1.0000 | 0.9079 | **1.0295** |
| thorax-hair | 0.5303 (0.2222) | 1.0000 | 0.8546 | 1.0011 |
| leg-spines | 0.9314 (0.5364) | 1.0000 | **1.0392 FAIL** | ~~1.1116~~ |
| head-eye | 0.5189 (0.3760) | 1.0000 | 0.8205 | **0.8737** |
| **CENTRE-CONTROL** | 0.8217 (0.0896) | 1.0000 | 0.9398 | **1.0074** |

Reading this honestly, item by item:

- **wing-venation reads 1.0295 — the crop where two people independently saw
  the aligned render as sharper.** The metric agrees with the eye at the place
  the eye judged, and reads more strongly there than whole-frame.
- **The centre control reads 1.0074, i.e. essentially nothing** — and residual
  misregistration is zero at the centre of the similarity *by construction*.
  The image supplies its own placebo region and the metric respects it. This is
  the strongest internal validation in the milestone.
- **The orchestrator was right to distrust their own leg-spines 1.1288.** My
  re-derivation gives the largest treatment number of any box, 1.1116 — **and
  its direction plant reads 1.0392, above 1.0.** Blurring the aligned render
  *still* makes it measure sharper there. That box is measuring something other
  than sharpness, so **1.1116 is inadmissible and I am striking it**, by an
  independent mechanism from the one they suspected.
- **head-eye reads 0.8737 — the null measures sharper — and I am not hiding
  it.** Two caveats bound it rather than dismiss it: co-location NCC is 0.5189
  against a displaced-plant 0.3760, a margin of only 0.14, so these boxes are
  poorly co-located; and clean paired edges collapse from 668 in the placebo to
  301 in the treatment.
- **That collapse is a bias, and it runs against the treatment.** Only edges
  yielding a clean single transition in *both* arms are kept. Smearing destroys
  profile cleanliness, so the edges the null damages most are preferentially
  discarded. The reported effect is a **lower bound**.

### 10.2 Radius does not work as a stratifier here, and I can prove why

Residual misregistration is proportional to radius, so a registration effect
should grow with radius. Whole-frame quartiles read **1.0100 / 1.0285 / 1.0297
/ 1.0068** — it rises then falls.

**Before concluding anything from that, look at the same stratification applied
to the uniform-blur direction plant, which has no radial dependence at all:
0.9277 / 0.9479 / 0.9645 / 0.9474.** Equally non-monotone. **MEASURED: the
radial breakdown carries structure that is not registration** — different radii
hold different subject matter, and on `bee-3` the outer band is background and
out-of-focus wing tip where there is nothing to sharpen. This is the same
content confound that made `radial4.py` inadmissible in §5, caught the same
way, and it is why §10.1 uses boxes rather than annuli.

---

## 11. The ruler: an external ground truth, and what it actually settles

M86 §15.4 named the straightness of a physically straight edge as the test that
would settle whether alignment improves the render. Two ruler captures exist:
`highly-angled-ruler-mm-cpl` (299 frames) and `flat-on-ruler-cpl` (79). Bars
were pre-registered in `PREREG3.md` before measuring, and amended — with the
amendment recording that I had by then seen the aligned arm's number and not
the null's, which makes that amendment weaker than the original and it is
marked so.

### 11.1 The solver refuses the decisive stack, by design

`strehl align` refuses `highly-angled-ruler-mm-cpl` outright:

> *its subject is not normal to the optical axis, so focus change moves
> different parts of the frame by different amounts and no single similarity
> describes it. The sidecar would be confidently wrong. Pass `--force-tilted`
> to override.*

**The steep angle that makes the ruler decisive as a *target* is exactly what
makes a global similarity the wrong *model*.** Forcing it does not measure "does
alignment improve the render"; it measures "does the similarity model, applied
where the project says it does not hold, still straighten a line that is
straight by construction". That is a real question, and the refusal is on trial
with it — so I ran it forced, and ran the accepted flat stack beside it as the
discriminating arm.

The solve diagnostics alone already separate the two (MEASURED, from the align
logs) — on **near-identical total drift**:

| stack | frames | total drift | held-out error | cycle floor | accepted? |
| --- | ---: | ---: | ---: | ---: | --- |
| `flat-on-ruler-cpl` | 79 | 111.054 px | 11.081 px | **0.799 px** | yes |
| `highly-angled-ruler-mm-cpl` | 299 | 109.631 px | 29.359 px | **21.602 px** | **no — forced** |

**27× worse cycle-consistency on the same drift.** The refusal is not a
heuristic being cautious; the solve it refuses is internally incoherent, and
says so in its own diagnostics before any image is rendered.

### 11.2 The instrument, and the two defects its plants caught

`src/angstraight.py` tracks each engraved graduation to sub-pixel precision
(depth-weighted centroid, robust line fit) and reports two ground-truthed
quantities: **S**, straightness *along* one graduation, and **G**, the residual
of tick centres about the exact 3-DOF projective-in-index law that equal world
spacing must obey.

Graduations, not the ruler's outer silhouette: there are 12–14 of them, so the
result is a distribution over independent straight lines; they are black-on-white
engravings rather than the exact locus of the occlusion halo (fact 1236); and on
the tilted ruler one graduation spans ~1600 rows.

**The plants caught two defects that would have produced a confidently wrong
number**, and both are recorded because they are the same class:

1. `HALF_WIN=9` gave a **19 px window for a 30 px tick** — the centroid was
   pinned by where the window fell, not by where the tick was. A planted 2.0 px
   bend recovered at **18%**. `BG_MED=61` centred inside a 30 px tick is 49%
   dark, so the "bright background" was itself dragged dark: depth p99 **7534**
   against **10383** at 301 px, a third of the contrast discarded. Both are now
   **derived from the measured pitch** (`autosize`), not typed in — because the
   flat ruler's pitch is 5× larger and hand-tuning a second set of constants
   would have been the same defect twice.
2. Tick pairing between arms scored candidates by the residual of a fitted
   linear map, and silently chose a **four-graduation slip with a scale of
   1.113**. It was caught only because the arms had already been measured to
   agree on pitch to **0.29%**, which 1.113 flatly contradicts. The criterion is
   now positional distance, where a one-tick error costs a whole pitch.

**Controls (MEASURED, both stacks, all passing).** Placebo bit-identical to six
decimals. Planted +3.0 px translation recovered at gain **1.0000** with the
straightness residual **unchanged** — exactly right, since a translation is
absorbed by the fit's intercept. Bend recovery **52–121%** (angled) and
**85–117%** (flat) against the *post-fit* expectation. Direction correct on both
arms of both stacks. A planted one-graduation slip is detected as `k=-1`.

> A half-sine bend is mostly DC, and a line fit's intercept absorbs that mean
> legitimately. Scoring recovery against `amp/√2` makes an honest instrument
> look 44% blind; `expected_bend_rms` computes the achievable residual over the
> rows actually used.

### 11.3 The result

| | **flat-on (accepted)** | | **angled (forced)** | |
| --- | ---: | ---: | ---: | ---: |
| | aligned | null | aligned | null |
| **S** straightness RMS (px) | 5.331 | 5.029 | 1.693 | 1.457 |
| — ticks aligned wins | 3/12 | | 6/14 | |
| — sign test *p* | 0.146 | | 0.791 | |
| — bootstrap 95% CI (px) | [−0.299, +0.039] | | [−0.248, +0.173] | |
| **S2** step statistic (px) | 6.104 | 5.975 | 3.602 | 2.919 |
| **G** spacing residual, % of 1 mm | **0.283** | 0.344 | **3.240** | 1.267 |
| G ratio aligned ÷ null | **0.82 — better** | | **2.56 — worse** | |

**S1 is a NULL on both stacks**, and this is the more honest reading than the
pre-registered bar's verdict. It fails as written (`rms_aligned ≥ rms_null` on
both), but 3/12 and 6/14 with sign-test *p* of 0.15 and 0.79 and bootstrap
intervals straddling zero are not a defeat; they are an instrument reporting no
difference. **I am recording the pre-registered FAIL and the statistical null
together rather than choosing whichever suits.**

**G discriminates, and it changes sign between the two stacks.** Where the
solver accepts the stack, alignment makes the millimetre spacing **18% more
regular**. Where it refuses and is forced, alignment makes it **2.6× worse**.
Same instrument, same controls, same treatments, opposite answers.

### 11.4 Why S sees nothing and G sees everything (ARGUED, from a MEASURED dissociation)

A single graduation runs *across* the ruler's width, which is very nearly an
iso-depth line; depth varies *along* the ruler, across graduations. So one tick
is elected from nearly one frame and its own straightness is nearly blind to
inter-frame registration **by construction**. The direction that runs through
depth is the across-graduation direction — which is G.

That is not argued from geometry alone: S and G come from the **same ticks, the
same tracker, the same rows**, and only their direction differs. The direction
through depth sees a 2.6× effect; the direction at constant depth sees nothing,
twice. Absent an elected-frame index map — `strehl stack` cannot emit one — this
stays ARGUED, but the dissociation is measured.

**So M86 §15.4's test does not settle the question on these captures, and the
reason is geometric, not instrumental.** A straight edge only discriminates if
the edge itself runs through depth. Neither ruler provides one: the flat ruler
has no depth, and the angled ruler's straight edges lie at constant depth.

### 11.5 What this does and does not license

- **MEASURED:** forcing the similarity model onto a stack the solver refuses
  degrades the render's measurable geometry — 2.56× on spacing regularity and
  23% on the step statistic. **`--force-tilted` costs image quality, and the
  refusal check is vindicated by measurement rather than by argument.**
- **MEASURED:** on a stack the solver accepts, alignment improves spacing
  regularity by 18% and degrades nothing.
- **NOT licensed:** any general claim that alignment does or does not improve a
  deep bracket of a real subject. The flat stack is nearly insensitive to
  registration by construction, and the deep stack is one the solver refuses.
- **The capture the project needs does not exist**: a **deep** bracket of a
  **fronto-parallel** target carrying **straight edges that run through depth**
  — e.g. a ruler stood at a modest angle, or a straight edge oriented so its
  length spans the focus range. That is a photograph the owner can take in
  minutes and it would settle §15.4 properly.
- **G is biased against the aligned arm on a tilted target**, and I state it
  against my own adverse result: breathing displacement is smooth in depth and
  therefore in tick index, so the 3-DOF projective model partly absorbs it,
  while per-frame warp *error* is not smooth and is not absorbed. The flat
  stack's result runs the other way, so the bias is not decisive — but it is
  real and the 2.56× should be read as an upper bound.

---

## 12. The magnification confound: both of us fitted a global scale to a field that is not global

The orchestrator retracted their visual claim (fact 1235) and discipline 605
after measuring that the two `bee-3` renders differ in magnification by ~1.25%,
which would make the crops we both judged by eye an unfair comparison. I accept
that the arms differ. I re-derived the number independently and I get the same
magnitude. **But the retraction, and my own first attempt to repair it, both
rest on a model that a plant then falsified.**

### 12.1 Three instruments, three defects, all caught by their own plants

`src/orchmag.py` — resample one arm onto the other's scale, then compare edge
width. **Killed by its own B3 plant.** Rescaling the null by 1.4% should change
widths by 1.4%; it changed them by 20% (0.7962 against a theoretical 1.0139).
The missing 19% is interpolation blur: resampling one arm and not the other
makes the resampled arm measure blunter no matter what the scene does.
**I withdraw `orchmag.py`'s 1.2003 "scale-matched" width figure.** The same
defect applies to any NN-scale-matched comparison — B5 measured that
nearest-neighbour rescaling *raises* Tenengrad by 0.0087 relative to a smooth
interpolator, because NN at a non-integer scale duplicates and drops whole
pixel columns. NN cannot add blur, which is why it is chosen; it can and does
add aliasing gradient energy, which is fatal for a gradient-energy metric.

`src/orchmag2.py` first run — stop resampling images, absorb the scale into
*where* each profile is sampled. **Killed by its own C3 plant.** Blurring the
aligned arm by σ=1.0 barely moved the answer (1.3216 → 1.2406, still far above
1.0), and a 3% scale detune moved it by 21% — a 7× over-response. One cause:
I had picked edge locations using the aligned arm's strongest gradients alone,
so the null regressed to the mean there and the comparison was rigged before
any physics entered. §10 had avoided this by selecting on the *mean* of two
co-located arms; that option died when the arms turned out not to be
co-located. **I withdraw 1.3216.**

`src/orchmag2.py` second run — select on the **union** of each arm's own strong
edges and report both halves. This is self-validating: the halves must bracket
the truth from opposite sides.

| | value |
| --- | ---: |
| ratio_A, aligned-chosen locations (biased *for* aligned) | 1.3216 |
| ratio_Z, null-chosen locations (biased *for* null) | 0.8036 |
| **geometric mean, the unbiased estimate** | **1.0306** |
| C1 placebo | 1.000000 |
| C2 detune ±3% | +0.103 / +0.320, both upward |
| C3 direction, blur(aligned) | 0.9821 **PASS** |
| C4 swap, product with treatment | 1.000000 |

Both detunes move the ratio **up**, so 1.0306 sits at a minimum with respect to
the global scale: **any error in the scale estimate inflates it.** 1.0306 is
therefore a *lower bound* over the family of global-scale models, not a
best case.

I then tried to bracket it by repeating the whole measurement at the
convention-free median scale of §12.3 (`M97_S=0.997992`). **That run fails its
own C3 direction control** — blurring the aligned arm leaves the ratio at
1.0061, above 1.0, so the instrument cannot tell a blurred image from a sharp
one under that model. Its 1.0753 is therefore not quotable, and the sensitivity
analysis could not be completed. What can be said is narrower and I say only
that: **of the global-scale models tried, exactly one passes all four controls,
and under it the null's edges are 3.06% wider.**

### 12.2 The radial claim died again, to its own control

The annuli looked like the signature registration must have — a similarity has
zero residual at its own centre by construction, so the effect should grow with
radius, and it did: 0.9724 at r≈1250 rising monotonically to 1.0633 at r≈3600.

**The uniform-blur plant reproduces 83% of that span** (+0.0753 against the
treatment's +0.0909). A σ=1.0 blur is applied everywhere and has no radial
structure whatever, so the rise is the instrument, not the registration.
**Withdrawn.** This is the second radial claim this milestone has killed with
the same control; the first was §6's `radial4.py`. Radial stratification on
these renders should now be presumed guilty.

### 12.3 The finding: there is no global scale difference to correct

`src/signcheck.py` measures the direction and size of the magnification with no
resampling convention at all. It takes a 192 px template from the aligned arm
at a known radius, finds the same texture in the other arm by NCC, and compares
the two radii. A feature that sits farther from the centre in an arm means that
arm is the more magnified one. Nothing else enters.

| probe | median radius ratio | spread |
| --- | ---: | ---: |
| D1 self | 1.000001 | 0.00005 |
| D2 planted ×1.02 | 1.01993 | 0.00168 |
| D3 planted ×0.98 | 0.98006 | 0.00165 |
| **treatment, null vs aligned** | **1.00201** | **0.06518** |

**MEASURED, and this is the result of §12.** On a genuine global magnification
the probe returns a spread of 0.0017. On the real pair it returns **0.065 — 38×
its own demonstrated resolution**, with an IQR of 0.0165–0.0242 that survives
restricting to NCC > 0.9. At r ≈ 2100 px, tiles with excellent match quality
disagree from −57.7 px to +35.7 px of radial displacement. A global scale
produces *the same* radial displacement at *the same* radius. This one does not.

**So the two renders do not differ by a global similarity, and "the
magnification difference between the arms" is not a well-defined number.**
That is not a surprise once stated: both arms are *composites*. Each output
pixel is elected from whichever frame won there; in the aligned arm that frame
was warped and in the null it was not, so the difference field follows the
elected-frame map, which follows depth, which follows the subject's
three-dimensional structure. The difference between two composites of
differently-warped frames is not itself a warp.

The median is **1.00201** — no net magnification difference worth correcting.
The 0.9875 the orchestrator applied, and the 0.98625 I measured, are both what
a single-scale fit returns when it is fitted to a field that has no single
scale: it lands wherever the highest-contrast region pulls it.

### 12.4 What this licenses, and what it takes back

- **MEASURED:** any comparison of these two renders that first scale-matches
  them globally — the orchestrator's NN-matched crops, their 0.9747 whole-frame
  Tenengrad, my 0.9634 analytic correction, my `orchmag.py` 1.2003 — rests on a
  falsified model. **None of those numbers should be quoted, mine included.**
- **NOT established, in either direction:** whether the aligned render is
  visibly sharper. The orchestrator's original claim was confounded, and the
  correction they applied to retract it is confounded by the same missing
  model. **Fact 1235's retraction is right to distrust the claim; it is not
  itself a measurement of the opposite.**
- **What survives:** §10's edge-width result. Under the one global model that
  passes all four controls, with selection bias bracketed and removed, the
  null's edges are **3.06% wider** than the aligned arm's, and every scale
  perturbation raises the figure. That is a smaller and much more heavily
  caveated claim than §10's original 1.0179 whole-frame number, and it is the
  honest one. It is also **not robust**: the one alternative global scale I
  tried fails its own direction control, so the result is conditional on a
  model §12.3 shows to be wrong in kind.
- **What is needed to settle it:** a comparison that compensates displacement
  **locally** rather than globally — per-region correspondence, not one scale.
  Every global-scale number on this pair is measuring the model error.

---

## 13. The read-only corpus write, and whether a torn sidecar is dangerous

Two defects I reported in `docs/research/M97-warped-merge.md` §9 came back to me
to land. They turned out to have opposite severities from the ones I assigned.

### 13.1 The corpus write was still firing

`sidecar_path` was `dir.join("warpmap.txt")`, so *rendering* a bracket wrote a
solve into the bracket. `D:\personal\macro` is the owner's original captures and
is read-only. I reported 8 strays, then 11.

They were cleaned — and then **a new one appeared**:
`D:\personal\macro\coffee-bean\warpmap.txt`. So this was not historical debris
from before the rule was written; the shipped binary was still creating them
while the fix was being drafted. **MEASURED**, by scanning the corpus before and
after.

The fix, now landed in `crates/strehl-cli/src/align_cmd.rs`:

- `sidecar_path` hashes `fs::canonicalize(dir)` and returns
  `<cache>/<leaf>-<key:016x>.warpmap.txt`. The canonical path is hashed, not the
  leaf name, so `a/bee-3-cpl` and `b/bee-3-cpl` get different entries and a
  render of one can never consume the other's warps.
- `cache_root()` honours `STREHL_CACHE_DIR`, else `%LOCALAPPDATA%` /
  `$XDG_CACHE_HOME`, else the temp directory, `+ strehl/warpmaps`.
- `strehl align`'s `--out` default changed from `dir.join("warpmap.txt")` to the
  same `sidecar_path(dir)`, so a hand-run solve populates the entry `stack`
  reads instead of a file it will not look at.

**Verification, pre-registered at three bars** (`src/corpuswrite.ps1`). A run
that produces no corpus file is indistinguishable from a solve that crashed, so
the null needed a companion that proves the write path executed at all:

| bar | what it asserts | result |
|---|---|---|
| A null | no new `*.txt` anywhere under `D:\personal\macro` | 1 → 1 file, **0 new** |
| B positive | the solve *did* write, in the cache, rc=0 | 3037 bytes, tail `end 19` |
| C plant | the same scanner fires on a directory that does contain one | sees 1 |

and then the half that the patch could have broken, since I changed one of the
two writers: `strehl stack` on the same bracket reports `alignment: ON
(sidecar), 19 placed / 0 refused` with **`solve took 0.0 s`**. `align` and
`stack` agree on the path. Corpus stray count unchanged at 1.

Three unit tests pin the behaviour rather than the implementation: the sidecar
is not under the capture directory, two directories sharing a leaf name get
different entries, and `save_atomic` creates its parent and leaves no temporary.

### 13.2 The torn sidecar is an availability bug, not a correctness bug

I measured a half-written read of `bee-3-cpl/warpmap.txt` while a sibling
rewrote it, and flagged it as potentially serious: a partial registration
silently applied would corrupt someone else's measurement tonight without ever
raising an error.

**It does not.** `crates/strehl-cli/examples/m97-tornmap.rs` copies a real
79-frame sidecar, truncates it at a ladder of byte offsets, and loads each one:

| rung | 10% | 25% | 50% | 75% | 90% | 95% | 99% | mid-line | full | empty |
|---|---|---|---|---|---|---|---|---|---|---|
| `WarpMap::load` | rej | rej | rej | rej | rej | rej | rej | rej | **Ok, 79** | rej |

Every truncation is rejected, with one of two messages: *"header declares 79
frames, N were read, and the terminating `end` record is absent"* or
*"`placed` needs 4 hex fields, found N"*. The two controls behave: the untouched
copy loads with 79 frames, the empty file fails.

**This is a positive result about M86's format design, and it is worth stating
as one.** The format carries both a declared frame count in the header *and* a
terminating `end` record, which is redundant on a correct file and is exactly
what makes a truncated one detectable. A format with neither — one frame per
line, read until EOF — would have accepted every rung above and rendered a
partial registration in silence.

So the torn read costs a wasted re-solve, not a wrong answer. That downgrades
the defect from correctness to availability. The write-then-rename is still
right to land, because with eight agents in one tree the re-solve is a real
cost and the window is real, but it is a robustness fix and not a data-integrity
one. `save_atomic` writes to `.{name}.{pid}.tmp` **in the destination
directory** — a rename is only atomic within a volume — and removes the
temporary if the rename fails.

### 13.3 What I did not fix

Defect 2, the abort on a single refused frame, should become a drop-with-warning
and I have **not** written it. It touches the fold and `n_eff` path in
`merge.rs`, which M87 and M93 are live in; I will not hand over a patch I could
not compile against a contended file. It is a correctness-of-behaviour issue,
not of data: today a stack with one refused frame fails loudly rather than
quietly.

---

## 14. Status / Changes / Verified / Not verified / Notes

### Status
**DONE.** The instrument exists, is plant-validated, and answers the question.

### Changes
- `experiments/M97b-align-visible/**` — `PREREG.md`, `PREREG2.md`, `src/scout.py`,
  `src/matched.py`, `src/radial4.py` (reported but inadmissible),
  `src/sheet.py`, `src/owner_sbs.py`, `src/mech1.py`, `src/bands.py`,
  `src/peaks.py`, `src/width.py`, `src/wingbox.py`, `src/render.ps1`, logs and
  JSON.
- **§11 (the ruler):** `PREREG3.md` (+ amendment 1), `src/ruler.ps1`,
  `src/flatruler.ps1`, `src/angthumb.py`, `src/angcrop.py`, `src/angprobe.py`,
  `src/angstraight.py`, `src/angrun.ps1`, `src/angfull.ps1`,
  `src/bothrulers.ps1`, `src/angverdict.py`, logs and JSON.
- **§12 (the magnification confound):** `src/orchmag.py` (withdrawn by its own
  B3 plant, kept because the defect is the finding), `src/orchmag2.py`,
  `src/signcheck.py`, `src/signdist.py`, and `out/orchmag*.json`,
  `out/signcheck.json`.
- `experiments/M97-warped-merge/src/signtest.py` — one line: `STACK` now reads
  `M97_STACK` from the environment, defaulting to the previous hard-coded
  bee-3 path, so prior results reproduce byte-identically.
- **§13 (the corpus write and the torn sidecar):**
  - `crates/strehl-cli/src/align_cmd.rs` — `sidecar_path` now returns a hashed
    entry under a cache root instead of `<capture-dir>/warpmap.txt`; new
    `cache_root()` and `save_atomic()`; both write sites (`load_or_solve` and
    the `strehl align` `--out` default) go through `save_atomic`; three unit
    tests added, the file's first.
  - `crates/strehl-cli/examples/m97-tornmap.rs` — new; the truncation ladder
    with full/empty controls that answers §13.2.
  - `experiments/M97b-align-visible/src/corpuswrite.ps1` — the three-bar
    end-to-end corpus test.
- **No changes** to `merge_cmd.rs`, `merge.rs`, `align.rs`, `warpmap.rs`,
  `lib.rs`, `main.rs`, or any other milestone's tree. `align_cmd.rs` is in my
  lane as of the orchestrator's last message and is the only source file I have
  touched.

### Verified
- Placebo 1.0004/0.9999/0.9996; blur plant 2.8993/1.8618.
- Ground truth 422.3 plane px with plants at err −0.0016 and −0.0006; sign
  correct; gain-1.0 rewriter control reproduces 0.86650 exactly.
- The zoom-only null banner fired in the ZOOMNULL render; the three arms are
  distinct files by MD5.
- PREREG named risk cleared: mean `n_eff` 13–38 of 299 frames, so the subject
  is not too flat for the test to bite.
- Q4 boundary plant: 186624 blackened rim px move the masked metric 0.0000%.
- `k = 1 − 3/1172 = 0.997440` against three reported 0.9974.
- `cargo clippy --release -p strehl-cli --bins` rc=0.
- Owner side-by-side viewer: self-control 0.9995 scale / 1.0000 lock with exact
  coordinates, and a **planted (+90, −110) px displacement of the starting guess
  still recovers the exact truth at 1.0000 on all three panels**.
- **I opened the renders.** §8 describes what is in them, including an artefact
  that runs against my own conclusion.
- **§9–10, the reassigned milestone.** Doubling falsified at exactly the
  predicted 0.5000. Bands cross 1.0 (0.9836 at 2 px, 1.0300 at 32 px) with a
  placebo exact in every band and stratum. Every percentile of `|∇|` fails its
  bar with all three controls passing. Edge width passes at 1.0179 whole-frame,
  1.0295 at the wing crop the eye judged, and **1.0074 at the centre where
  drift is zero by construction**.
- **Two plants caught two errors that would otherwise have been reported**: the
  leg-spines box fails its direction plant (1.0392), and the radial
  stratification is equally non-monotone on a uniform-blur plant that has no
  radial dependence.
- **§11, the ruler.** Both stacks rendered in both arms (4 × 198 MB TIFFs,
  `corpus clean`, stray-sidecar count 11 → 11 on every run). Instrument
  controls on **both** stacks: placebo bit-identical to six decimals,
  translation gain **1.0000** with residual unchanged, bend recovery 52–121%
  (angled) / 85–117% (flat) against the post-fit expectation, direction correct
  on all four arms, planted one-graduation slip detected as `k=-1`.
- **§11 tick correspondence verified before any pairing was used**: `k=0`,
  14/14 and 12/12 paired, median offset 11.6% and 9.0% of a pitch.
- **I opened these renders too.** §11's tick-width and texture differences were
  seen at 1:1 in `angcrop-*.png` before any number was computed.
- **Two further plants caught two further errors in §11's own instrument** — a
  window narrower than the tick it measured (18% plant recovery), and a
  tick-pairing criterion that slipped four graduations at a fabricated scale of
  1.113. Both are described in §11.2 rather than quietly fixed.

- **§12.** `signcheck.py` D1 self 1.000001 (spread 5.0e-5), D2 planted ×1.02 →
  1.01993, D3 planted ×0.98 → 0.98006, both to within 0.00007 and with a spread
  of 0.0017 — so the probe resolves a global scale 38× finer than the 0.065
  spread it reports on the real pair.
- **§12.** `orchmag2.py` C1 placebo 1.000000 exactly, C4 swap product 1.000000
  exactly, C3 direction 0.9821 PASS, C2 detune ±3% moves the answer by 0.10 and
  0.32, C7 halves bracket the estimate from both sides (1.3216 / 0.8036).
- **§12. Three of my own instruments were withdrawn on their own plants**
  before any number reached this report: `orchmag.py` (B3, resampling blur),
  `orchmag2.py` run 1 (C3, selection bias), and the radial annuli (uniform-blur
  plant reproduces 83% of the trend).

- **§13. `cargo test --release -p strehl-cli --bin strehl` → 62 passed, 0
  failed**, including the three new `align_cmd::tests`.
- **§13. `cargo build --release -p strehl-cli --bin strehl` rc=0**, and no
  clippy diagnostic references `align_cmd.rs`.
- **§13. Corpus test rc=0, all three bars PASS**: 0 new `*.txt` under
  `D:\personal\macro`; the sidecar landed in the cache at 3037 bytes with tail
  `end 19`; the same scanner sees a planted `warpmap.txt` in a writable
  directory. The null is proven with a plant on the same wiring, per discipline
  598.
- **§13. `strehl stack` reads what `strehl align` wrote**: `alignment: ON
  (sidecar), reference frame 0, 19 placed / 0 refused`, **`solve took 0.0 s`**.
  This is the check that would have caught it if my change to `align`'s default
  had desynchronised the two.
- **§13. `WarpMap::load` rejects every rung of an 8-step truncation ladder**
  (10/25/50/75/90/95/99% and a mid-line cut) on a real 79-frame sidecar, with
  the untouched copy loading at 79 frames and the empty file failing.

### Not verified
- **§12's 1.0306 is conditional on a model §12.3 falsifies.** It is the one
  global scale that passes all four controls; the alternative I tried fails C3.
  A local, per-region compensation is what the question actually needs, and I
  did not build one.
- **§12 does not establish that alignment is or is not visible.** It establishes
  that every global-scale-matched number on this pair — the orchestrator's and
  mine — is measuring model error. That is a statement about the instruments,
  not about the photograph.
- Whether the 0.065 per-tile spread is entirely elected-frame structure or
  partly parallax and occlusion. The mechanism in §12.3 is ARGUED; the
  heterogeneity itself is MEASURED.
- **The 19–32% win is measured on one stack.** It should be repeated on
  `couch-fibers-cpl` (drift 1.2034, edge/centre 1.40) before it is a general
  claim.
- Gain 4.5498 is `ln(0.79999)/ln(0.95214)`, **per-stack and empirical**. It is a
  probe that proves the solve is short, **not a fix**. The fix belongs in M86's
  estimator.
- Whether the win is *visible* at normal viewing size, as opposed to at 1:1.
  §8 is a 1:1 judgement; I did not assess a fit-to-screen view.
- The cause of the waxy smearing §8 found in the corrected render's bright
  low-texture region. It is real; I did not diagnose it.
- Why the field-of-view ratio reads 1.1278 in §8 and 1.1949 in §5.
- **The blur plant in §10 failed its pre-registered >1.30 bar (1.0725).** I
  argue from the quadrature ladder that the bar was mis-specified for a width
  metric, and the ladder supports that, but it is my own pre-registration I am
  reinterpreting after the fact and it should be weighed as such.
- Whether `head-eye`'s 0.8737 is a real region where the null is sharper or an
  artefact of that box's weak co-location (NCC 0.5189 against a 0.3760
  displaced plant). It needs a properly co-located replacement box.
- The edge-width numbers are **whole-frame medians over `bee-3`**, the subject
  §3 shows is the worst in the corpus for this question. The marker head was
  not re-measured with the width metric for lack of time.
- `cargo clippy --bins --tests` fails: 3 errors in
  `crates/strehl-cli/src/merge_cmd/halo.rs` (M87, `52c6a52`). Test code only;
  not mine and not touched. `--bins` alone now also fails on the same file with
  2 errors, so I verified instead that **no clippy diagnostic names
  `align_cmd.rs`**; I could not get a clean rc=0 on a crate a sibling is
  mid-edit in.
- **§13's corpus test ran on a 19-frame bracket, not on the 299-frame stacks.**
  The write path is the same code, but the deep-stack render was not re-run
  under the new binary.
- **§13 does not prove that no *other* code path writes into the corpus.** It
  proves `sidecar_path`'s does not. I scanned only for `*.txt`.
- I did not remove the existing stray `D:\personal\macro\coffee-bean\warpmap.txt`.
  The corpus is read-only, and deleting from it is a write; that call is the
  orchestrator's. It was removed by someone else during this session, so the
  final corpus scan reads 0 — **that zero is not evidence for my fix**, and bar
  A's 1 → 1 with 0 new is the number that is.
- **§11's S/G dissociation is ARGUED.** I could not measure the elected-frame
  index along versus across a graduation, because `strehl stack` has no option
  to emit an elected-frame map. The dissociation itself is measured; the
  iso-depth explanation for it is not.
- **§11's `G` is biased against the aligned arm on a tilted target** (§11.5,
  last bullet). I state the direction of my own adverse result's bias; I did
  not quantify it.
- **The flat stack's 18% `G` win is a single number, not a distribution**, and
  it is small: 0.283% against 0.344% of a millimetre. Unlike S it carries no
  per-tick sign test, so I cannot put a *p*-value on it.
- **§11's two arms of the flat stack differ in magnification by 3.14%**
  (546.56 against 529.93 px/mm). This is consistent with the aligned arm
  mapping to frame 0's geometry while the null keeps the elected frames'
  geometry, but I did not verify that explanation. `G` normalises by each arm's
  own pitch, so the comparison is unaffected.
- **Absolute straightness numbers in §11 are not registration error.** The
  ruler's manufacturing straightness and the lens's distortion enter both arms
  equally. Only the paired difference is quoted as a claim.

### Candidate facts (rule 28)

- **P1 (MEASURED).** `strehl align` refuses `highly-angled-ruler-mm-cpl` as a
  tilted subject; forced with `--force-tilted` it solves 299/299 with a
  **cycle-consistency floor of 21.602 px** against **0.799 px** on the accepted
  `flat-on-ruler-cpl`, at near-identical total drift (109.631 vs 111.054 px).
  The refusal check identifies an internally incoherent solve, 27× worse by the
  solver's own diagnostic.
- **P2 (MEASURED).** Forcing that refused solve into the render degrades
  measurable output geometry: millimetre-spacing residual **3.240% of pitch
  against the null's 1.267%** (2.56× worse), step statistic 3.602 against 2.919.
  On the accepted stack the same instrument reads **0.283% against 0.344%** —
  18% better. **`--force-tilted` costs image quality.**
- **P3 (MEASURED).** Straightness *along* a single graduation is a null on both
  ruler stacks — 3/12 (*p*=0.146) and 6/14 (*p*=0.791), bootstrap CIs straddling
  zero — while spacing regularity *across* graduations, from the same ticks and
  the same tracker, shows a 2.56× effect. **A straight-edge straightness test
  only discriminates if the edge runs through depth.** M86 §15.4's test does not
  settle the question on either existing ruler capture.
- **P4 (DERIVED, actionable).** The capture that would settle §15.4 does not
  exist: a **deep** bracket of a target whose **straight edges run through the
  focus range**. Neither a flat-on ruler (no depth) nor a steeply angled one
  (straight edges at constant depth) provides it.
- **P5 (MEASURED, method).** A tracking window narrower than the feature it
  measures is silently near-blind: a 19 px window on a 30 px tick recovered
  **18%** of a planted 2.0 px bend. Derive window sizes from measured feature
  geometry, not by hand.
- **P6 (MEASURED, method).** Matching periodic features between two arms by
  best-fitting-linear-map residual admits whole-period slips: it chose a
  four-graduation slip at a fabricated scale of **1.113** against a measured
  pitch agreement of **0.29%**. Match by positional distance, where a one-period
  error costs a whole period.
- **P7 (DERIVED, method).** A half-sine plant is mostly DC and a straight-line
  fit absorbs its mean legitimately, so the achievable post-fit residual is
  `0.3078·amp`, not `amp/√2`. Scoring against `amp/√2` makes an honest
  instrument look 44% blind.
- **P8 (MEASURED).** **Two focus-stack composites of the same frames, one warped
  and one not, do not differ by a global similarity.** A template probe that
  recovers a planted ×1.02 with a per-tile spread of 0.0017 reports a spread of
  **0.065** on `bee-3-ALIGNED` vs `bee3-zoomnull`, with radial displacements at
  the same radius running from −57.7 px to +35.7 px. Median radius ratio
  **1.00201** — no net magnification difference. Every global scale-matched
  comparison of these arms (0.9875, 0.98625, and the metrics computed after
  applying them) is measuring model error.
- **P9 (DERIVED).** The mechanism follows from what a composite is: each pixel
  is elected from whichever frame won there, so the difference field between an
  aligned and an unaligned composite follows the elected-frame map, which
  follows depth. **The difference between two composites of differently-warped
  frames is not itself a warp**, and cannot be removed by one.
- **P10 (MEASURED, method).** Resampling one arm to scale-match it blurs that
  arm and biases every width or sharpness comparison: a 1.4% rescale changed
  measured edge widths by **20%** against a theoretical 1.4%. Absorb a
  coordinate change into *where* you sample, never into a new image.
- **P11 (MEASURED, method).** Nearest-neighbour rescaling raises Tenengrad by
  **0.0087** relative to a smooth interpolator at the same scale. NN cannot add
  blur — which is why it gets chosen for exactly this job — but at a
  non-integer scale it duplicates and drops pixel columns and *adds aliasing
  gradient energy*. It is the wrong choice for scale-matching before a
  gradient-energy metric.
- **P12 (MEASURED, method).** Selecting comparison locations by one arm's
  strongest gradients makes the other arm regress to the mean there: the same
  pair reads **1.3216** on aligned-chosen edges and **0.8036** on null-chosen
  edges. Select on the union and take the geometric mean, and report both
  halves so the bracket is visible.
- **P13 (MEASURED).** Radial stratification on these renders is presumed guilty:
  a σ=1.0 **uniform** blur, which has no radial structure at all, reproduces
  **83%** of the treatment's radial span. Second radial claim this milestone
  has withdrawn to the same control.
- **P14 (MEASURED).** **`WarpMap::load` rejects a torn sidecar.** Every rung of
  an 8-step truncation ladder on a real 79-frame file fails to load, against
  controls where the full copy loads at 79 frames and an empty file fails. The
  cause is redundancy that is useless on a correct file: the header declares the
  frame count *and* the body terminates with an `end` record. A read-to-EOF
  format would have accepted all eight and rendered a partial registration
  silently. **The torn read is an availability defect, not a correctness one.**
- **P15 (MEASURED).** The read-only-corpus violation was **still live**, not
  historical: after the earlier 11 strays were cleaned, a new
  `D:\personal\macro\coffee-bean\warpmap.txt` appeared. A cleanup is not a fix
  while the code that creates them still ships. Now fixed at the source —
  `sidecar_path` hashes the canonical capture path into a cache root, verified
  end-to-end at 0 new corpus files with a positive control proving the write
  path ran and a plant proving the scanner fires.
- **P16 (DERIVED, method).** "No file appeared where it should not" is the
  weakest possible evidence, because a crash produces it too. Pair every
  absence-of-write null with a **positive control that shows the write happened
  somewhere else** — here, a 3037-byte sidecar in the cache ending `end 19`.
  Same shape as discipline 598, applied to a filesystem side effect rather than
  to a metric.

### Notes
**The corpus write is fixed at the source** (§13.1). Pollution had grown 8 → 11
stray `warpmap.txt` files under `D:\personal\macro`, and `bee-3-cpl\warpmap.txt`
was rewritten at 06:03 during this session; after those were cleaned a **new**
one appeared at `coffee-bean`, which is what established the violation was still
live rather than historical. `sidecar_path` now hashes the canonical capture
path into a cache root outside the corpus, `strehl align`'s default writes to
the same entry `strehl stack` reads, and both writers go through a
write-then-rename. The one stray remaining when I wrote §13.1 was
`coffee-bean`'s; I left it, since deleting from a read-only corpus is itself a
write. It was gone by the time I committed — removed by someone else — so the
corpus currently scans **clean at 0 stray `*.txt`**, and the point of the fix is
that it now stays that way without anyone sweeping.
The original verbatim patch is in `docs/research/M97-warped-merge.md` §11; what
landed differs from it in hashing the *canonical* path rather than the leaf.

**For M86, one item, and it is the whole story:** the solve applies 23.9% of the
drift on the marker head and 54.3% on bee-3. `E*` is structurally blind to a
common multiplicative gain error — every edge agrees with every other while the
accumulated absolute scale is short — which is how a held-out error of 23.5 px
coexists with a 282 px end-to-end residual. **Fixing the gain converts a
measured null into a measured 19–32% win.** `signtest.py` is a four-minute
end-to-end test for it.

**Correction to my own earlier reporting:** in `docs/research/M97-warped-merge.md`
§11a I wrote that correcting the gain produces "a real but subtle improvement"
and does "not transform this photograph". That conclusion was drawn on bee-3,
which §3 above now shows is the worst subject in the corpus for this question.
On a subject with detail where the error lives, the same correction measures
19–32%. **I was measuring the subject, not the treatment.**

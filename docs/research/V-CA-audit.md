# V-CA — Audit of the "enable the CA correction" recommendation

**Auditor:** V-CA (independent verification agent, read-only on `crates/`)
**Commissioned by:** the owner, to apply **discipline 821** to ORCH's CA recommendation
before it reaches a user-facing brief.
**Tree audited:** worktree detached at `30ae92b`. HEAD moves under many live agents; every
claim below is pinned to a file + line as read at that SHA.

---

> ## Should ORCH tell the owner to enable the CA correction? **NO.**
>
> Not "not yet pending one more measurement" — **no**, on the recommendation as written.
> The correction is real and it does work on the owner's own glass. But **no report author
> anywhere in the corpus recommends default-on, two authors explicitly recommend against it,
> the shipped source code says "Off by default, and it must stay that way", and ORCH itself
> wrote fact 1593 saying "It cannot simply be switched on."** ORCH's brief would be
> contradicting ORCH's own recorded finding.
>
> **What ORCH should say instead:** the flag exists, it works, and the owner should try it
> **on his own A7C II + FE 100 GM + 2x TC + X4 CPL captures specifically** —
> `STREHL_FIX_CA=a7c2-fe100gm-2xtc-x4cpl` — quoting **−29.4 % at the edge** and
> **−20.5 % near edges**, not 61.0 %, and naming the side effects.

---

## The headline finding

This is **not** an exact repeat of the halo failure (fact 1596), and saying otherwise would be
its own version of not reading past the headline. On the halo, the promoted 87.9 % came from
**ROI crops of an unaligned, gate-0 merge** while the shipped value was 72.9 %. Here, the
61.0 % / 58.7 % figures come from a **full-frame, aligned, default-gate, default-resampler,
full-stack render**. I checked the argv. **That part is clean, and it must be said plainly.**

The failure is a different one, and it is worse in one respect:

1. **The number is real but mis-described.** "61.0 % edge chroma reduction" is not a chroma
   reduction. It is the fall in *edge-localised chroma **excess*** — a derived contrast
   against a baseline five pixels away. The same correction on the same file reduces raw
   edge chroma by **−29.4 %**, near-edge chroma by **−20.5 %**, and whole-frame chroma by
   **−4.9 %**. ORCH quoted the largest of five available numbers for one effect, without the
   qualifier that makes it mean what it means.
2. **The recommendation itself has no source.** No author recommends it. Two recommend
   against. So does the code. So does ORCH's own fact 1593.

---

## Q1 — Does any report author recommend enabling `STREHL_FIX_CA` by default?

**No. Two authors and the shipped code recommend the opposite. Nobody recommends for.**

### 1a. The report that was *asked the exact question* answered no

`docs/research/M107b-lateral-correction.md`, section title at **L728**:

> ## 15. Wiring: the design answer, and why I did not wire it

and its opening line: *"Asked whether the lateral-CA correction is ready to go default-on…"*

Sub-section title at **L733**:

> ### 15.1 (1) Transferable? **NOT ESTABLISHED. It ships behind a flag.**

Verbatim conclusion, **L752-753**:

> **So: flag-gated, and it stays flag-gated until someone measures a second configuration.**
> Default-on would be a regression risk taken on a coefficient whose transfer is measured to
> be uneven.

This is discipline 821's exact shape: a section whose *title* is the refusal, answering the
*precise* question ORCH is about to answer the other way.

### 1b. The shipped source says the same thing, in a doc comment

`crates/strehl-core/src/optics.rs`, doc comment on `profile_from_setting`, **L417-425**:

> /// Resolve the lateral-CA profile from the `STREHL_FIX_CA` setting.
> ///
> /// **Off by default, and it must stay that way.** The out-of-sample transfer arm
> /// (L4) **split**: a profile fitted on `tweezers-cpl` recovered 95.0 % of the
> /// in-sample reduction on `bee-3-cpl`, but the reverse direction recovered only
> /// 54.1 % against a registered 60 % bar. … Default-on would be a regression risk
> /// taken on a coefficient whose transfer is measured to be uneven.

There is also a **shipped unit test named for the invariant** —
`the_ca_gate_is_off_by_default_and_refuses_to_guess`, `optics.rs` **L907-915**. Enabling by
default requires deleting a test that says in its name that you must not.

### 1c. ORCH already wrote the refusal itself

`SYNTHESIS.md` **fact 1593** (author: ORCH):

> It cannot simply be switched on… Defaulting it on would apply one photographer's measured
> aberration to everybody's glass. The correct default is "on when the capture matches a
> known profile, off otherwise", and the matching half does not exist.

And **fact 1608** (ORCH, OBSERVED) records the CA correction as *"un-adjudicated pending an
audit of whether its 61.0 %/58.7 % figures come from the shipped pipeline and whether it was
ever raced against a negative-strength arm rather than against OFF"* — i.e. ORCH commissioned
this audit and is now poised to pre-empt its own finding.

### 1d. The one pro-shipping sentence, quoted honestly

`M110-sheet.md` **L1081**, closing §14.9:

> **Verdict: better, not merely different — but for different and stronger reasons than the
> ones on offer.** The evidence is the radial monotonicity and the inert-null floor, not the
> fringe percentage. **I would ship it on this evidence.**

This is a genuine positive and it is the strongest thing in the corpus. But it is about
shipping *the feature* — which shipped, behind a flag — not about *defaulting it on*, a
question M110 never asks. The very next section (§14.10, L1084-1096) lists five things the
same author could not verify.

**Method note (rule 43 — an assertion of absence is a claim).** I measured the absence rather
than asserting it: `experiments/V-CA/v4_absence_check.py` whitespace-collapses every `.md`
under `docs/` (wrapped Markdown breaks phrases across lines) and searches sentence-by-sentence
for any of *default-on / on by default / enabled by default / should be turned on / turn it on
/ switch it on / ship it on* co-occurring with the CA gate. **Three sentence hits, none of
them a recommendation**; the only relevant one is M107b §15's title. Limitation: the scan is
sentence-scoped, so "I would ship it on this evidence" (no "CA" token in that sentence) is a
known false negative — I found and quoted it manually above.

---

## Q2 — Where do 61.0 % and 58.7 % come from, exactly?

**Source:** `M110-sheet.md` §16.4, **L1243-1244**:

> Taking the far band as baseline, the **edge-localised chroma excess falls 61.0 % on
> `bee-3-cpl` and 58.7 % on `flat-on-ruler-cpl`.**

Recorded as **fact 1589** in `SYNTHESIS.md`.

**Pipeline, from the actual argv in `C:\dev\strehl-out\M110-sheet\manifest.json`:**

| ORCH's failure question | answer for the CA figure |
|---|---|
| Full frame or ROI crop? | **Full frame** (band 0 alone is 668,469 px of a 7032x4688 frame) |
| Aligned or unaligned? | **Aligned** — `strehl align` run, `STREHL_WARPMAP` passed to the merge |
| Which merge gate? | **Default** — no `--gate` flag, so `DEFAULT_GATE = 4.0` |
| Demosaiced or CFA-native? | **Demosaiced** |
| sRGB or linear? | **`--srgb`**, with a pinned manual `--exposure=1.54` |
| Full stack or limited? | **Full** — `limit: None`; 299 frames (bee), 79 (flat-on-ruler) |
| Resampler | shipped default `catmull-rom` |
| Is this what the project ships? | **Yes.** Default gate, default kernel, alignment on, full stack. |

**So the halo failure does not repeat here.** This is the shipped pipeline.

**But the statistic is not what ORCH calls it.** "Edge-localised chroma excess" =
`mean|R−Y|(band 0) − mean|R−Y|(band 5)`. It is a *contrast against a 5-px-distant baseline*,
not chroma removed. The corpus contains at least five numbers for the same effect, and ORCH
quoted the largest:

| statistic | `bee-3-cpl` | source |
|---|---|---|
| **edge-localised chroma *excess* fall** | **61.0 %** | M110 §16.4 / fact 1589 — *ORCH's headline* |
| decile-10 mean \|R−Y\| | −49.75 % | M110 §14.2 |
| raw \|R−Y\| at band 0 | **−29.4 %** | M110 §16.4 table, L1230 |
| W3 mean \|R−Y\| near edges | **−20.66 %** | M107b §19.2 |
| M107b's own edge-chroma metric | **−9.76 %** | M107b §18.6 |
| **whole-frame mean \|R−Y\|** | **−4.91 %** | **this audit, measured** |

M107b §19.2 gives the governing instruction, and ORCH did not follow it:

> A comparison sheet cropped to high-contrast edges will overstate the correction; a
> whole-frame chroma average will understate it. **Both numbers should travel together.**

### My independent re-derivation

`experiments/V-CA/v1_band_sensitivity.py` re-implements the band profile from the raw TIFFs
with a **different gradient stencil** (Sobel, where M110 used a central-difference sum) and
sweeps the free baseline-band parameter K:

```
bee-3-cpl          K=5  excess 1253.0 -> 492.7   FALL 60.68 %   (M110: 61.0 %)
flat-on-ruler-cpl  K=5  excess 2337.6 -> 950.6   FALL 59.33 %   (M110: 58.7 %)
band 0 raw:  bee  3173.6 -> 2229.4  = -29.75 %   (M110: -29.4 %)
             flat 4026.3 -> 2037.1  = -49.41 %   (M110: -49.3 %)
```

**M110's arithmetic reproduces on a different stencil.** And the K-sweep clears the
free-parameter worry rather than confirming it: the fall plateaus at ~60 % for every K >= 4
(bee: 61.4/60.7/60.7/60.5/60.3/60.2/60.4 for K=4..10). **K=5 was not cherry-picked.** That is
a point in M110's favour and I record it as one.

---

## Q3 — Is "visibly cleaner by eye" a real observation or ORCH's paraphrase?

**It is a real, primary observation — by two independent agents — and ORCH's paraphrase is
fair on the upside and silent on everything the observers said next.**

**M110 §14.9** (L1073-1081), at 5x on unamplified pixels:

> - **Fringe sites — clearly better.** … In `ca` the cyan members are largely gone. The image
>   reads cleaner and more natural. It does **not** look odd.
> - **Near-neutral textured sites — better, not worse.** … **The predicted cost did not appear
>   where it was predicted.**
> - **Corner — the largest visible win in the matrix**, and it is in the extrapolated zone.

**M107b §18.6:** *"visibly better, and by more than I expected."*

### What the observers said about side effects — the part ORCH's phrasing drops

1. **The residual changes character.** M110 §14.7, **L1040-1041**:
   > genuinely improves — but residual chroma is now **biased toward red** rather than
   > balanced. That is an improvement and a change in the character of the artefact at the
   > same time.
2. **The fringe does not shrink; it fades.** §16.4, L1246-1252 — see Q4.
3. **The same author who said "visibly better" revised his own confidence down.** M107b §19.2,
   on re-measurement: W3 mean |R−Y| near edges **−20.66 %**, W1 fringe area **−10.20 %**,
   W3 sign-retention bar **FAILED at 75.1 %** against a >90 % bar.
4. **The by-eye read was never separated from its own resampler.** Fact 1519: *"the arm set
   cannot yet separate the correction from its own resampler."* See Q7.
5. **Specular highlights / texture loss:** nobody looked. No author reports on specular
   highlight rendering. My own measurement (Q4) shows **luma is not softened** — green's
   high-band energy moves **+0.59 %** (bee) / **+0.46 %** (flat) — so the "does it soften the
   image" worry is bounded and largely answered in the correction's favour. **Red loses
   7.4–20.6 % of its high-band energy at edges**, which is either the fringe being removed or
   interpolation blur, and no arm in the corpus distinguishes those.

**Verdict on Q3:** the by-eye claim is real and I would not strike it. But "visibly cleaner"
compresses "cleaner, with a red-biased residual, fainter-but-equally-wide fringes, a failed
sign-retention bar, and a confound the author flagged and could not remove."

---

## Q4 — The measured harms

### Confirmed: fainter, not thinner

`M110-sheet.md` §16.4, **L1246-1252**:

> But **the profile does not measurably contract.** Peak-to-baseline contrast drops from 2.45x
> to 1.93x (`flat-on-ruler`) and 1.63x to 1.27x (`bee`), and half-maximum width is unchanged or
> marginally wider … **It gets fainter, not thinner.** … but a sheet claiming narrower fringes
> would be overselling it.

Re-derived from the raw band table in `ca_overshoot_default_vs_ca.json`: **2.4513 → 1.9317**
and **1.6312 → 1.2717**. Exact match. M110's own **discipline 59** was written for this:
*"Separate amplitude from extent before claiming an artefact was removed… so a 60 % amplitude
drop is not reported as a fringe that shrank."* **ORCH's brief is about to do exactly what
discipline 59 forbids.**

### Confirmed: the green/blue footprint — but the alarm is smaller than the number

`M110-sheet.md` §14.8, **L1044-1064**, confirmed exactly by my own pixel count:

| plane | M110 | V-CA measured | mean \|Δ\| | max \|Δ\| |
|---|---|---|---|---|
| R | 98.66 % | **98.66 %** | 540.2 DN | 35,291 DN (137.3 lv) |
| G | **94.41 %** | **94.41 %** | 50.03 DN | 9,418 DN (36.6 lv) |
| B | 67.67 % | **67.67 %** | 54.17 DN | 13,845 DN (53.9 lv) |

`mean|ΔG| / mean|ΔR|` = **0.0926**, inside M110's stated 0.087–0.110 band.

> **Is a correction that touches 94.4 % of pixels' green channel safe to enable by default?**
>
> **On this evidence, the 94.4 % is not the reason to say no — and I will not pretend it is.**
> A fraction is not a magnitude. `experiments/V-CA/v3_green_tail.py` measures the size of
> those touches in 8-bit display levels (1 lv = 257 DN):
>
> ```
> bee-3-cpl   G:  p50 0.066 lv   p90 0.525   p99 1.681   max 36.6
>                 >1 lv: 3.40 % of px      >4 lv: 0.03 % of px
> flat-ruler  G:  p50 0.288 lv   p90 1.128   p99 2.603   max 31.9
>                 >1 lv: 12.45 % of px     >4 lv: 0.17 % of px
> ```
>
> The 94.41 % is dominated by ±1 DN in a 16-bit render. Green is visually untouched for
> ~96.6 % of pixels on `bee-3-cpl`. **The honest harm is elsewhere.**

**The real unquantified side effect is blue.** `eps_b: None` (`optics.rs` L320) declares blue
geometrically untouched, and M110 recorded that 67.67 % of blue pixels move anyway. Nobody
recorded *by how much*. I did:

```
bee-3-cpl   B:  >1 lv on 6.46 % of px    >4 lv on 0.70 %   max 53.9 lv
flat-ruler  B:  >1 lv on 14.07 % of px   >4 lv on 2.26 %   max 98.5 lv
```

A correction documented as red-only moves blue by **more than 4 display levels on up to
2.26 % of pixels, peaking at 98 levels** — over a third of the display range on a single
pixel. And M110 §14.8, L1061-1063, on the mechanism:

> I have measured the footprint but **not identified the mechanism** — frame election
> responding to a changed sharpness measure, and chroma-guided demosaic coupling, are both
> consistent with what I see and **I have not separated them**.

**That** is the Q4 answer that should worry a decision-maker: not the 94.4 %, but a
visible-magnitude effect on a channel the profile says it does not touch, by a mechanism its
own author says is unidentified.

### Also confirmed

- **M113 §3:** the correction **over-corrects and flips the sign of the residual** on both
  stacks it tested (−529.9 → +132.3 ppm bee; −654.9 → +36.5 ppm couch).
- **M107b §19.2:** the W3 sign-retention bar **FAILED at 75.1 %** — though M110 fact 54 /
  SYNTHESIS fact 1588 reinterpret this as a defect in the *bar* (a flip with shrinkage is
  success), which I accept.
- **M110 fact 53:** the unenforced extrapolation past `support_r_max` does **not** overshoot —
  a genuine null in the correction's favour, and I record it.

---

## Q5 — Generality

**There is essentially none, and where it was tested it split.**

| axis | evidence | result |
|---|---|---|
| (a) other scenes, same gear | M107b §15.1 L4 arm | **SPLIT: 0.950 one way, 0.541 the other, against a registered 0.60 bar** |
| (b) 2x TC in / out | `optics.rs` L307-308, M107b §15.2 | **None.** The TC is *in the profile name*; the gate "refuses to guess" precisely because there is no evidence for TC-out |
| (c) CPL in / out | profile name `…-x4cpl` | **None.** No arm ever measured CPL-out |
| (d) other apertures / magnifications | `optics.rs` L311-313 | **None, and it is recorded as absent** |

`optics.rs` **L311-313**, the project being honest with itself:

> // Not recorded by the capture metadata M107 had to hand. Absent rather than
> // guessed: lateral CA varies with aperture and magnification, so a guess here
> // would silently widen the profile's claimed applicability.
> measured_at: None,

**The profile does not know the aperture or magnification it was fitted at**, while its own
comment says the quantity varies with both.

### The 23.6 % scene-to-scene spread

**Found:** `M113-ca.md` §5, and SYNTHESIS **fact 1570**. The fitted coefficient differs
between two scenes shot through *the same glass*: **−529.9 ppm** (`bee-3-cpl`) vs
**−654.9 ppm** (couch). Re-derived: `(654.9 − 529.9) / 529.9 = ` **23.5894 %**. Per-ring
bootstrap sd is only **8–23 ppm**, so the spread is ~5–15 sigma — **real, not noise**.

**Was it ever explained? No.** It is *attributed* to scene spectrum by argument plus a
channel-ratio table — never by a spectrally-controlled experiment. M113 §7 concedes:
**"Two stacks is two."**

**What it implies for a default-on correction:** the shipped `eps_r = −704.5e-6` is a single
scalar. If the true per-scene value varies by ±24 % *on one lens*, then on any given frame the
correction is 24 % wrong in an unknown direction — and M113 §3 measured that this is enough to
**flip the residual's sign**, i.e. to turn a red fringe into a cyan one. Under-correction
leaves a fringe; over-correction *creates* the complementary fringe. A default-on correction
would do that silently, to images the user never asked to have modified.

### And the fit is under-powered by its own author's standard

`M107-chroma.md` §9.2:

> **Before implementing, the parameters should be re-fitted on a purpose-shot… target with
> >= 100 ROIs**… My 20 ROIs are enough to establish the mechanism, **not to calibrate a
> shipped correction.**

The shipped profile is fitted on **20 ROIs** (`optics.rs` L309, `n_regions: 20`). The author
of the measurement says that is a fifth of what a shipped correction needs. It shipped anyway
— **which was fine behind a flag, and is not fine as a default.**

---

## Q6 — The dispatch gap

**Confirmed, independently, and there is no guard of any kind.**

I reproduced fact 1592 rather than citing it:

```
git grep -nE '0x010f|0x0110|"Make"|"Model"|LensSpec|maker_note|lens_model|camera_model' -- 'crates/**/*.rs'
  -> exit 1, no output
```

**`strehl` parses no camera, lens, or teleconverter identity anywhere in the codebase.**

`profile_from_setting` (`optics.rs` L446) validates only that the *string the operator typed*
matches a known key. Fact 1594: key-existence validation catches typos but **cannot catch a
gear mismatch**, and the failure is silent in the dangerous direction — a user on a Canon RF
100 who types the Sony key gets a Sony aberration model applied to Canon glass with no error
and no warning.

**So "on by default" means: apply one photographer's measured aberration model, fitted on 20
ROIs through a Sony A7C II + FE 100 GM + 2x Viltrox TC + Breakthrough X4 CPL at an unrecorded
aperture and magnification, to every user's every photograph, with the software structurally
incapable of noticing that it is the wrong lens.**

### The minimum safe form of "on by default"

Every one of these is missing today:

1. **Parse camera + lens + TC identity from RAW metadata** — does not exist (verified above).
2. **Match it against `OpticalProfile::optical_path`** — no matching code exists.
3. **Record and check aperture and magnification** — `measured_at: None`; there is nothing to
   check against.
4. **Refuse (fall back to OFF) on any mismatch or any unknown field** — silent-off, never
   silent-on.
5. **Clamp or refuse beyond `support_r_max = 0.788`** — currently "Declared, not enforced"
   (`optics.rs` L315-317).

This is exactly ORCH's own fact 1593: *"The correct default is 'on when the capture matches a
known profile, off otherwise', and **the matching half does not exist**."*

Context for how far out of line default-on would be: **fact 1579** — of seven env gates on the
render path, **only `STREHL_ALIGN` defaults on.**

---

## Q7 — Is it distinguishable from a no-op plus resampling blur?

**No. That control has never been run. This is the audit's cleanest finding.**

### The corpus already knows this is the missing arm

- **Fact 1519:** *"the arm set cannot yet separate the correction from its own resampler…"*
  Applying the correction necessarily resamples R, which low-passes it, and single-sensel
  chroma speckle is exactly what a mild low-pass suppresses.
- **Fact 1517:** M114's `zero` arm is **byte-identical to `off`** — the code short-circuits on
  a zero coefficient, so it never resamples. `zero` is not a placebo.
- **Fact 1584:** ORCH's tangential-rotation placebo is **disqualified** — it under-blurs by
  **93.41 %** on oriented hair-like content.
- **Facts 1585/1586:** the correct control is **the same correction at negative strength**,
  blur-neutral to 1.11e-16, and the comparison must be **`anti` vs `on`**, never vs `off`.
- **Discipline 816** demands precisely this control.

### Has it been run? No.

I searched `experiments/` and every report. The only ± work that exists is
`M107-chroma/src/r11_calibrate.py` / `r12_iterative.py`, which plant ±704.5 ppm **in Python on
an already-rendered TIFF** — an instrument check, not a pipeline arm. **Fact 1529** explains
why no render arm exists: **there is no strength or scale knob anywhere in the codebase**, so
producing an `anti` render requires a source change to `optics.rs`.

**Every published CA A/B in this project is treatment-vs-OFF: "correction + resampling" versus
"neither".** Discipline 816's control has not been run once.

### What I could measure instead — and it does not settle it

`experiments/V-CA/v2_blur_and_edges.py`. Green is resampled identically in both arms, so it is
a natural reference for how much high-band change is *not* attributable to the extra red
resample. Laplacian RMS, off → on:

| subject | plane | whole frame | on edge pixels |
|---|---|---|---|
| `bee-3-cpl` | R | **−5.12 %** | **−7.38 %** |
| | G | +0.59 % | +0.64 % |
| | B | −4.64 % | −6.85 % |
| `flat-on-ruler-cpl` | R | **−10.75 %** | **−20.62 %** |
| | G | +0.46 % | +0.27 % |
| | B | −8.13 % | −12.74 % |

**Two readings, and I cannot choose between them:**

- **Benign:** a chroma fringe *is* high-frequency content in R, so removing it legitimately
  lowers R's Laplacian RMS. Green is untouched (+0.6 %), so **luma detail is not lost** — the
  "does it soften the image" fear is measurably unfounded.
- **Confounded:** red loses up to **20.6 %** of its high-band energy at edges, exactly what a
  mild low-pass would do, and exactly the nuisance fact 1519 named.

**An `anti` arm separates these in one render** — it resamples identically but *doubles* the
fringe, so blur-driven and correction-driven chroma reduction move in opposite directions.
Until that arm is run, **"the correction reduces chroma" and "resampling red blurs it" are
observationally equivalent on every arm this project has published.**

I also record the reassuring side honestly: green's high-band energy **rises** slightly in
both subjects, so whatever is happening, the merged image is not being softened in luma.

---

## The strongest argument FOR enabling (stated as well as I can make it)

I hold myself to arguing this properly before I reject it.

1. **Radial monotonicity.** M110 §14.4: the chroma reduction is **zero at the frame centre and
   rises monotonically to the corner**, on three independent subjects. That is the signature
   of *lateral CA specifically* — a resampling artefact or a global recolour would not have it.
   This is the single strongest piece of evidence in the corpus and it is very strong.
2. **The predicted cost was beaten by an inert null.** M110 §14.3: the decile-1 "+555 %" cost
   M107 predicted is **smaller than the same statistic under RMS-matched inert noise** on all
   four subjects. The headline cost is a binning artefact, not a harm.
3. **Two independent by-eye reads agree**, plus ORCH's, at 5x on unamplified pixels, including
   at the site chosen specifically as where the predicted cost should land, where it did not.
4. **The extrapolation is safe where it was feared.** M110 fact 53: no discontinuity at
   `support_r_max`, no upward overshoot trend beyond it — 9.73 → 9.78 → 9.47 %.
5. **It is free.** The `WarpMap` is held exactly fixed; the correction folds into the existing
   gather with no second resample.
6. **The pipeline is the shipped one.** Unlike the halo case, the 61.0 % is a full-frame,
   aligned, default-gate, default-kernel, full-stack render. I verified the argv.
7. **My own K-sweep exonerates the statistic** from cherry-picking: the fall plateaus at ~60 %
   for every K >= 4.

**This is a good correction and it deserves to exist.** Nothing above is in dispute. The
argument for *the feature* is strong. The argument for *the default* is a different argument,
and nobody has made it.

---

## The strongest argument AGAINST enabling

> A correction fitted from **20 ROIs** — a fifth of what its own author says a shipped
> correction needs — on **one photographer's single optical path**, at an **aperture and
> magnification nobody recorded**, whose coefficient is **measured to differ 23.6 % between
> two scenes through that same glass** for a reason that was argued but never tested, whose
> only out-of-sample transfer test **split 0.950 / 0.541 against a 0.60 bar**, which
> **over-corrects hard enough to flip the residual's sign** on both stacks that checked, which
> moves **blue** — a channel it declares it does not touch — by more than four display levels
> on up to 2.26 % of pixels by a mechanism its own author says he **has not identified**, which
> has **never once been compared against anything but an arm that does no resampling at all**,
> and which the software is **structurally incapable of knowing is even the right lens** —
> would be switched on for every user's photographs on the strength of **the largest of five
> different numbers describing the same effect**, quoted without the qualifier that makes it
> mean *"contrast against a five-pixel baseline"* rather than *"chroma removed"*, and described
> as removing fringes when the project's own **discipline 59** was written to stop exactly that
> sentence from being said about exactly this measurement.
>
> And the person who would be told this is a photographer who is going to open the resulting
> file and look at it.

---

## What ORCH should actually put in the brief

**Keep the default OFF.** Recommend the flag, scoped honestly:

> The chromatic-aberration correction is finished and it works. It is off by default because
> it was fitted on your gear only and the software cannot tell whether a given capture came
> from that gear. On your A7C II + FE 100 GM + 2x TC + X4 CPL shots, set
> `STREHL_FIX_CA=a7c2-fe100gm-2xtc-x4cpl` and compare: edge chroma drops **~29 %** at the
> fringe and **~20 %** in the near-edge region (whole-frame, **~5 %** on `bee-3-cpl`). Two
> agents and I looked at 5x crops and thought it clearly better. Three caveats: fringes get
> **fainter, not thinner** — the width is unchanged; what residual remains is **red-biased**
> rather than balanced; and it has never been tested against the one control that would prove
> the improvement is the correction rather than the resampling it does along the way. **Worth
> turning on for your own frames. Not yet safe as a default for anyone else's.**

## What would change this verdict

1. **Run the `anti` arm** (negative-strength, `anti` vs `on`, per facts 1585/1586 and
   discipline 816). This needs a strength knob in `optics.rs` (fact 1529). **Highest value,
   one render.**
2. **Re-measure the 61.0 % in binned-linear space.** M113 measured `--srgb` as
   cross-channel-contaminated (chain transfer 1.3073 vs 0.9399/0.9813 binned-linear), and
   `--srgb`'s own `--help` says *"For looking at, NOT for measuring."* **Nobody has ever
   re-measured the headline in the clean space.** Cheap: the `lin-*.tif` renders exist.
3. **Parse camera/lens/TC identity and gate the profile on a verified match** (Q6's five
   requirements). This is what makes default-on *possible*, not merely arguable.
4. **Measure a second optical configuration** — TC out, or CPL out — which is literally what
   M107b §15.1 said the flag stays on until.
5. **Re-fit on >= 100 ROIs** per M107 §9.2.

---

## Artefacts

Under `experiments/V-CA/` (created by this audit; nothing under `crates/` was modified):

| file | what it establishes |
|---|---|
| `v1_band_sensitivity.py` | Independent band re-derivation on a different stencil; K-sweep; whole-frame chroma; per-plane change footprint |
| `v2_blur_and_edges.py` | Edge-population ladder; per-plane high-band energy (the blur bound for Q7) |
| `v3_green_tail.py` | Magnitude distribution of the green/blue changes in display levels |
| `v4_absence_check.py` | Whitespace-collapsed sentence scan of all `docs/**/*.md` for a default-on recommendation (rule 43) |

Verification run: `cargo test -p strehl-core --lib optics::` — `Compiling strehl-core`
present (rule 33), **16 passed, 0 failed**, including
`the_ca_gate_is_off_by_default_and_refuses_to_guess`.

---

## Addendum — re-confirmed against a moving HEAD

HEAD moved three times during this audit (`30ae92b` -> `6814edc` -> `5c942bf` -> `ddd683a`),
so I re-ran the load-bearing Q6 check against the live tree rather than trusting the worktree
snapshot:

```
git --no-pager grep -nE '0x010f|0x0110|"Make"|"Model"|LensSpec|maker_note|lens_model|camera_model|LensModel' -- 'crates/**/*.rs'
$code = $LASTEXITCODE
  -> exit=1 at HEAD ddd683a   (1 = NO gear identity parsing anywhere in crates/)
```

**Q6 stands at current HEAD: `strehl` still parses no camera, lens or teleconverter identity.**

**However — `M119-gear-identity` is in flight.** `git worktree list` shows an active detached
worktree at `C:/dev/strehl-out/M119-gear-identity/wt`. There is no `M119` row in `AGENTS.md`
and no `docs/research/M119*.md`, so **it has not landed**. If M119 delivers RAW gear-identity
parsing, it closes requirement (1) of Q6's five — the largest single blocker. That is a reason
for ORCH to **wait for M119 and re-adjudicate**, not a reason to enable now: identity parsing
alone still leaves the transfer split (Q5), the unrecorded `measured_at` (Q5), and the missing
`anti` arm (Q7) open.

**Methodology note (AGENTS.md rules 46/47).** My first run of that grep reported `exit=0`
because the invocation was written as `$null = git ... 2>&1`, which clobbers `$LASTEXITCODE` —
the same class of corruption the rules record for `Select-Object -First`. Had I trusted it I
would have reported the dispatch gap as **closed** when it is open. Run the command bare and
capture `$LASTEXITCODE` in the next statement.

---

# Addendum 2 — follow-up audit, and three corrections to my own report

Commissioned to read `M114`'s CA verification and to press hardest on Q7. Both mandates
produced findings that **go against my own first report**. Recording them first.

## 2.0 The M114 premise is false — there is no M114 report

I was told M114-ca-verify had been running ~2.5 h and might have written `docs/research/M114-*.md`.
**No such file exists.** `AGENTS.md:845` reads:

> | `M114` | **Allocated but never dispatched.** The stem was reserved during the deconvolution
> planning burst and the work it was reserved for became `M115`. … | **retired unused.** Do not
> reallocate. |

Three commits *are* prefixed `M114` (`fad9ea9`, `43cb380`, `30ae92b`) and predate the retirement.
So the ledger row and the commit history disagree — **`M114` is recorded as never dispatched while
three commits carry its stem.** That is a corpus defect, not a CA finding, but rule 41 exists
precisely to stop stem collisions and this row will mislead the next reader.

## 2.1 CORRECTION 1 — my blue-channel harm finding is WITHDRAWN

`6814edc` (**19:36**) landed *"M110: RETRACTION — section 14's green/blue coupling was the sRGB
colour matrix"*, six minutes before I wrote my report (19:40). §14.8's *"I have measured the
footprint but not identified the mechanism"* — which I quoted as live — **had already been
withdrawn by its own author.**

The mechanism is `camera_to_srgb`. M110's three cells, which I have now reproduced:

| cell | `\|dG\|/\|dR\|` | G changed | B changed |
|---|---|---|---|
| A sRGB + demosaic *(what §14 and I measured)* | 0.0741 | 94.4 % | 67.7 % |
| B linear + demosaic | 0.0000 | 24.4 % | 24.6 % |
| **C linear + binned** | **0.0000** | **0 px, max delta 0 DN** | **0 px** |

My own re-measurement on `lind-*.tif` (`v5`) returns **G 24.42 %, B 24.58 %** — matching M110's
cell B to three digits. In the measurement space green moves >4 display levels on **0.00 %** of
pixels and blue on **0.02 %**.

**So my Q4 headline — "the real harm is blue moving >4 lv on up to 2.26 % of pixels by an
unidentified mechanism" — is wrong.** It was correct arithmetic on a viewing render, which is
exactly the error M110 §14 made and which new **discipline 65** now names: *"Never diagnose a
mechanism on a viewing render."* I made the error I was auditing.

**This is now a defect in SYNTHESIS.** ORCH folded my claim into **fact 1663** at `e20c61b`
(**19:47**), eleven minutes *after* the retraction that kills it. Fact 1663's clause *"movement of
blue … by >4 display levels on up to 2.26 % of pixels by an unidentified mechanism"* should be
struck. **CA is a pure red-plane operation in camera space, exactly as designed.**

## 2.2 CORRECTION 2 — the Q7 framing is wrong, and fact 1538 already said so

My Q7 asserted: *"Every published CA A/B is treatment-vs-OFF, i.e. correction + resampling versus
neither."* **That is false, and the refutation predates my audit.** `SYNTHESIS.md` **fact 1538**
(M107b, MEASURED):

> **Lateral-CA correction is exactly FREE.** A radial magnification about a point is itself a
> `Similarity`, and `Similarity` is closed under composition, so the correction folds into the
> transform the gather already applies — verified to **<= 1e-12 relative over 20 000 randomised
> transforms and points**. There is **no second interpolation** … Note this also means fact 1519's
> placebo problem is **structural: there is no separable 'resampling step' to control for, because
> the correction never adds one.**

With alignment on — as in every published arm — **both** arms resample red exactly once. The
correction changes *where* red is sampled, not *how many times*. There is no extra interpolation to
confound the comparison.

I cited fact 1538 in my own report's "argument for" as *"It is free"* and **failed to carry it into
Q7**, which is a rule-38 failure of exactly the kind discipline 821 describes: I read the row and
did not read it end to end. ORCH folded the error into **fact 1664** (*"never been compared against
anything but an arm that does no resampling at all"*); that clause should be struck too.

## 2.3 Q7 answered directly: the interpolation-null control

Fact 1538 removes the *second-resample* confound but not the whole question — the two arms still
sample red at **different subpixel phases**, and Catmull-Rom blur is a function of phase. That
residual confound is testable without any source change, and the corpus has not tested it.

The shipped correction is a pure radial magnification (the `_RADIAL` variant zeroes translation),
so the phase offset between arms is exactly

    d(r) = |eps_r| * r  pixels,   eps_r = 704.5e-6,   d spans 0.000 .. 2.977 px

Catmull-Rom blur is **maximum at frac(d) = 0.5** and **exactly zero at frac(d) = 0**, where the
offset is a whole-pixel shift and no interpolation occurs.

> **Blur hypothesis predicts the apparent chroma reduction peaks at frac(d) = 0.5.**

`experiments/V-CA/v6_interp_phase_test.py` detrends fall% against a cubic in `d` (the CA effect
grows with radius and `d` is monotone in radius) and regresses the residual on `cos(2*pi*d)`, which
is +1 at every integer and −1 at every half-integer:

| space | fall% at frac(d)~0 *(no blur)* | fall% at frac(d)~0.5 *(max blur)* | `cos(2*pi*d)` coeff | perm. p |
|---|---|---|---|---|
| **linear + demosaic** | **35.00 %** | **22.73 %** | **+5.12 pp** | 0.102 |
| sRGB | **31.37 %** | **25.80 %** | **+4.50 pp** | 0.00045 |

**The reduction is LARGEST exactly where interpolation blur is zero and SMALLEST where it is
maximal — the opposite phase from the blur hypothesis, in both spaces.**

> ### How much of the 61 % could be interpolation?
> **Essentially none, and the sign of the worry is backwards.** Interpolation is a **cost** to the
> correction, not the source of its apparent benefit: it suppresses the measured reduction by
> ~5 pp on the detrended fit, and by ~12 pp between best and worst phase (35.0 % → 22.7 %). A
> blur-driven artefact cannot produce this phase.

**Honest limits.** (i) The linear arm's p = 0.102 does **not** clear 0.05; only the sRGB arm does,
and the sign agrees in both. (ii) The permutation test permutes contiguous annuli, so residual
spatial autocorrelation makes both p-values optimistic. (iii) The merge averages 299 frames at
varying alignment phases; a period-1 oscillation is only observable because that phase distribution
is concentrated, which I did not independently verify. **(iv) This test rules out blur. It does not
test whether the coefficient's sign and magnitude are right** — and given fact 1536, that is the
control that actually matters.

## 2.4 The argument for an `anti` arm survives, for a different reason

Fact **1536** (M107b, MEASURED):

> **THE SHIPPED CORRECTION'S SIGN WAS INVERTED, AND IT SURVIVED 9/9 GREEN UNIT TESTS PLUS
> INDEPENDENT MUTATION TESTING.** The unit committed at `d551488` applied its correction in the
> wrong direction, making the aberration **7.2 % WORSE** on a real render. **The coefficients were
> right; only the application direction was wrong.** It was caught in a **render-domain preview**,
> not by the suite.

**This correction has already shipped a sign inversion once, and its own test suite could not see
it.** That, not the blur confound, is the case for a negative-strength arm: an `anti` arm is a
render-domain sign-and-magnitude check, and the render domain is the only place the last sign error
was caught.

**Proposed minimal `anti` profile — data-only, proposed not built.** A duplicate `OpticalProfile`
const with negated coefficients under a new key, e.g. `a7c2-fe100gm-2xtc-x4cpl-anti` with
`eps_r: +704.5e-6`, added to the `profile_from_setting` table. No logic change, no new branch, no
collision with M107's ownership of the file's behaviour. Expected result if the correction is
sound: `anti` roughly **doubles** edge chroma where `on` roughly halves it, and the `anti`-vs-`on`
midpoint reproduces `off`. Expected if the gain is an artefact: `anti` also reduces chroma.

## 2.5 Q2 re-measured in the measurement space — the headline SURVIVES and grows

Fact 1665 (folded from my report) records that the headline had never been measured where the
project says to measure. It has now been. `v5_linear_and_interp_null.py`, `bee-3-cpl`,
`lind-default.tif` vs `lind-ca.tif` (linear + demosaic, full resolution, no colour matrix, no gamma):

| statistic | sRGB *(published)* | **linear (measurement space)** |
|---|---|---|
| whole-frame mean \|R−Y\| | −4.91 % | **−3.58 %** |
| **band 0 raw** | −29.36 % | **−28.93 %** |
| edge-localised excess, K=5 | 60.96 % | **73.07 %** |
| edge-localised excess, K=3 | 64.32 % | **79.99 %** |

**The `--srgb` render was not inflating the headline — it was deflating it.** In the clean space
the excess falls **73.1 %**, not 61.0 %. The robust member of the family, raw band-0 chroma, is
**−28.9 % against −29.4 %** — stable to half a point across a colour-matrix and gamma change, which
is the strongest evidence yet that it measures the correction rather than the pipeline.

**My Q2 gap is closed, and it closed in the correction's favour.** I flagged the sRGB measurement
as a risk; the risk did not materialise.

## 2.6 Q6 update — M119 landed the extraction half; the matching half is still missing

`43cee3b` (19:52) landed `strehl_raw::identity()` — 874 lines, every field `Option`, infallible, off
the decode path, **verified against `exiftool` on 56 files across all 24 macro stacks: 448 fields,
0 disagreements**. It reads the **2x teleconverter two independent ways** (`LensModel`, and
`LensType3` = 33094 for the composed path vs 32893 bare, deciphered from maker-note tag `0x940c`).

**Requirement (1) of my five is now done, and done well.** But:

```
git grep -nE 'identity\(|CaptureIdentity' -- 'crates/**/*.rs'   [excluding identity.rs itself]
  -> crates/strehl-raw/examples/identity.rs:22
     crates/strehl-raw/src/lib.rs:37 (re-export)
```

**Nothing calls it.** No code compares a `CaptureIdentity` to `OpticalProfile::optical_path`. The
commit says so itself: *"This is the missing half — extraction only."* Requirements (2)–(5) stand.

**And one requirement can never be met.** From the same commit: *"**The CPL reports nothing and
never will.**"* The shipped key is `a7c2-fe100gm-2xtc-**x4cpl**`. Even with perfect identity
matching, the polariser — part of the fitted optical path — is **permanently unverifiable from
metadata**. Any future auto-dispatch must either ignore the CPL term or ask the operator.

## 2.7 What ORCH did with my report — checked

`2f9cc81`: the brief now says keep the default OFF, recommends the flag scoped to the owner's own
frames, and replaces `61.0 %` with *"~29 pct at the fringe, ~20 pct near-edge, ~5 pct whole-frame"*.
**ORCH also caught a defect I missed**: its own switchboard implied `STREHL_FIX_CA=1`, which the
code deliberately rejects — it verified the accepted string against `optics.rs` rather than copying
it from my report. That is the right instinct and it would have put a broken command in the owner's
hands.

**One flag on `393935f`**, which is newer: the brief now tells the owner the CA switch *"is a
PREREQUISITE for ever shipping a sharper kernel, not an independent corner tidy-up."* That raises
the stakes on the CA coefficient being right, and it rests on M118's by-eye read that `lanczos3`
makes fringing more conspicuous. I have not audited M118. **The composition claim inherits every
open item above, including the untested sign.**

---

## Revised verdict

> ## Should ORCH tell the owner to enable the CA correction by default? **STILL NO — but the case against has narrowed sharply, and two of my own arguments have fallen.**

**Withdrawn from my case against:** the blue/green harm (§2.1 — it was the colour matrix), the
resampling confound as a *second-interpolation* problem (§2.2 — fact 1538), and the
measurement-space doubt (§2.5 — the headline grows in the clean space). The blur worry the follow-up
was commissioned to press is **measured and refuted in sign** (§2.3).

**What still stands, and it is enough:**

1. **No author recommends it** — unchanged, and now ORCH's own disciplines 847-848.
2. **The transfer split 0.950 / 0.541** against a 0.60 bar — unchanged.
3. **The 23.6 % scene-to-scene coefficient spread** was never explained — and `ddd683a` records that
   *"the spectral hypothesis dies, the effect survives"*, so the one candidate explanation is now
   **dead** and the spread is unexplained rather than merely untested.
4. **The dispatch gap is half-closed and cannot fully close** — no matching code, and the CPL is
   permanently unreadable (§2.6).
5. **The sign shipped inverted once and 9/9 unit tests plus mutation testing missed it** (fact 1536),
   and **no render-domain sign check has been run since** — the `anti` arm (§2.4).

**Strongest argument against, restated for the narrowed case:**

> This correction has already shipped pointing the wrong way, and the only thing that caught it was
> a render-domain preview that nobody has repeated. Its coefficient still varies 23.6 % between two
> scenes through the same glass for a reason that has now been actively falsified rather than merely
> left open. It cannot be dispatched automatically, because the software still has no code joining
> the identity it can now read to the profile it would apply — and one term of that profile, the
> polariser, can never be read at all. Turning it on by default would apply an unverified sign to
> every user's photographs through glass the product cannot confirm, on the strength of a number no
> author ever recommended acting on.

**Cheapest thing that would change this:** the `anti` arm (§2.4). It is one data-only profile entry
and one render, and it checks the exact failure this correction has already committed once.

---

# Addendum 3 — PIL 16-bit RGB hazard: V-CA's exposure

**Answer to ORCH's question 1: V-CA is EXPOSED-BY-PROXIMITY BUT UNAFFECTED. Every number in
this report was read with `tifffile`. Zero PIL decodes. The margin was not comfortable.**

## 3.1 My own scripts — proven, not asserted

All nine V-CA scripts import `tifffile` and call `tifffile.imread`. Not one contains
`np.asarray(Image.open(...))`. Per ORCH's rule *"re-run rather than reason"*,
`v7_pil_exposure_selfcheck.py` proves it on the exact files, rather than grepping the source:

| file | tifffile | levels | PIL mode | PIL dtype | PIL levels |
|---|---|---|---|---|---|
| `bee-3-cpl/default.tif` | `uint16` | **55 194** | RGB | **uint8** | **234** |
| `bee-3-cpl/ca.tif` | `uint16` | 55 196 | RGB | uint8 | 233 |
| `bee-3-cpl/lind-default.tif` | `uint16` | 21 476 | RGB | uint8 | 112 |
| `bee-3-cpl/lind-ca.tif` | `uint16` | 21 467 | RGB | uint8 | 115 |
| `flat-on-ruler-cpl/default.tif` | `uint16` | 40 914 | RGB | uint8 | 231 |
| `flat-on-ruler-cpl/ca.tif` | `uint16` | 40 401 | RGB | uint8 | 214 |

**The hazard reproduces exactly on this project's own CA renders: a 236x loss of level
resolution, silent, RGB only.**

## 3.2 How close this came — three of my five headline numbers are BELOW the 8-bit floor

PIL's quantisation step on a 0..65535 range is **257 counts**. Against that floor:

| V-CA number | 16-bit counts | PIL steps | |
|---|---|---|---|
| whole-frame chroma change (bee, LINEAR) | 17.70 | **0.07** | **BELOW FLOOR** |
| mean \|dG\| (bee, sRGB) | 50.03 | **0.19** | **BELOW FLOOR** |
| mean \|dB\| (bee, sRGB) | 54.17 | **0.21** | **BELOW FLOOR** |
| **band-0 chroma change (bee, LINEAR)** | **236.96** | **0.92** | **BELOW FLOOR** |
| band-0 chroma change (bee, sRGB) | 918.09 | 3.57 | above floor |

Had V-CA used PIL:

- **§2.1 would have been unrecoverable.** The green/blue footprint work — mean `|dG|` of 50
  counts — is **a fifth of one quantisation step**. It would have read as an exact zero, and
  I would have "confirmed" that CA never touches green. That is ORCH's *"worst — a clean
  null"*, and I would have reached the right conclusion for an entirely fabricated reason.
- **§2.5 would have been destroyed.** The linear-space re-measurement that closed fact 1665
  and moved the headline from 61.0 % to **73.07 %** rests on a band-0 change of **237 counts
  = 0.92 steps**. The whole finding lives inside the quantisation error.
- **§2.3, the interpolation-null control, would have been noise.** It resolves ~5 pp
  differences between radial annuli in the linear render — far below one PIL step.

**The single most decision-relevant result in this audit — that the CA headline survives and
grows in the measurement space — would have been invisible.**

## 3.3 The CA headline's own scripts are CLEAN

Checked because a hazard in `ca_overshoot.py` would have invalidated 61.0 %/58.7 % outright:

| script | produces | reader |
|---|---|---|
| `M110-sheet/ca_overshoot.py` | **the 61.0 % / 58.7 % band table** | `tifffile` |
| `M110-sheet/ca_decile.py` | the decile-10 −49.75 % | `tifffile` |
| `M110-sheet/ca_matrix_test.py` | the retraction's cells A/B/C | `tifffile` |
| `M110-sheet/ca_camera_space.py` | cell C, the exact zero | `tifffile` |
| `M110-sheet/sheet.py` | the comparison sheets | `tifffile` read; PIL only `ImageDraw`/`ImageFont` |

`sheet.py:625` already carries the warning: *"The dtype is asserted, not assumed.
`PIL.Image.open` on a 16-bit RGB TIFF…"* — **M110 knew, and guarded.**

Milestone-level scan of everything backing a number I cited:

```
M107-chroma      42 scripts   17 use tifffile   PIL-decoder-pattern = 0
M113-ca          14 scripts    0 use tifffile   PIL-decoder-pattern = 0  (reads no TIFF pixels)
M113-spectral    13 scripts    2 use tifffile   PIL-decoder-pattern = 1  (= its own s9_pilaudit.py)
M114-ca-verify   22 scripts   17 use tifffile   PIL-decoder-pattern = 1  (= r10a, see below)
```

**No number cited anywhere in this audit traces to a PIL-decoded 16-bit RGB TIFF.**

## 3.4 TWO OF THE 27 ARE FALSE POSITIVES — and one is the CA-relevant one

`from PIL import Image` + `Image.open` is **not** sufficient evidence of exposure. Three uses
have to be separated, and only the first loses data:

- **DECODER** — `np.asarray(Image.open(p))`, `.convert()` → **exposed**
- **TAGS** — `Image.open(p).tag_v2`, then a raw/memmap byte read → **not exposed**
- **WRITER** — `Image.fromarray`, `ImageDraw`, `ImageFont`, `.save()` → **not exposed**

### `ORCH-drift-check/ca_radial.py` — NOT EXPOSED (proven)

Its docstring says *"The TIFF layout is READ FROM THE TAGS, not assumed, then memory-mapped,"*
and `load_tiff_u16` asserts `bits == 16`, `spp == 3`, `compression == 1`, `planar == 1` before
reading pixel bytes at the offset from tag 273. `v9_ca_radial_proof.py` runs that loader
against `tifffile` on a real render:

```
   loader returns a 3-tuple: memmap, int, int
   ca_radial.load_tiff_u16 -> dtype=uint16 shape=(4688, 7032, 3) min=0 max=65535
   tifffile.imread         -> dtype=uint16 shape=(4688, 7032, 3) min=0 max=65535
   BYTE-IDENTICAL TO tifffile: True
   distinct levels  loader 55194   tifffile 55194
```

**This matters specifically because `ca_radial.py` is the radial-support test for the CA
correction** — the arm behind fact 53's "no discontinuity at `support_r_max`", which I cited in
my argument *for* the correction. It is sound.

### `M114-ca-verify/src/r10a_crop_locate.py` — NOT EXPOSED

`r10a:33` reads the render as `(tifffile.imread(REND) >> 8).astype(np.uint8)` — a **deliberate,
declared** downconversion, and the task is **locating a crop by spatial match**, not computing a
metric. Its `Image.open` at `:70` reads an **already-8-bit contact-sheet PNG**. Correct on both
counts.

## 3.5 The list of 27 is both over- and under-inclusive

Scanning all of `experiments/` for scripts that touch PIL **and** `.tif` finds **137**, not 27,
classified by use: **42 decoder-pattern, 23 unclear, 2 tags-only, 70 writer-only.**

But my own classifier over-counts: at least **eight** of its 42 "exposed" hits are *deliberate
hazard-audit scripts* that call PIL on purpose to demonstrate the bug — `pil16_probe.py`,
`pil_exposure_check.py`, `pil16_exposure_audit.py`, `s9_pilaudit.py`, `13_pil_audit.py`,
`pil_exposure_audit.py`, `pil16_price.py`, `reader_blast_radius.py`, plus my own `v7`/`v8`.
**Grep cannot do this triage.** The fleet is clearly already responding — M107, M111, M113,
M120, M122, M97, V-M111 and V-M116 all have audit scripts on disk.

**Recommended discriminator, mechanical and cheap:** flag only
`np.asarray(Image.open(...))` / `.convert(` / `np.array(im`, then confirm at runtime with
`assert arr.dtype == np.uint16`. `Image.open(p).mode == 'RGB'` on a file whose tags say 16-bit
is the one-line diagnostic ORCH names, and it is correct.

## 3.6 Does anything in this audit change?

**No.** All numbers stand as reported. The corrections in Addendum 2 (§2.1 blue harm withdrawn,
§2.2 Q7 framing wrong, §2.5 headline grows in linear space) are unaffected — every one was
measured through `tifffile`, and §2.5's survival is now doubly notable because it is a signal
that a PIL read would have erased.

**The general lesson, in this project's idiom:** ORCH is right that the check costs one line.
The sharper version is that **`v7` is the check** — read the same file both ways and print the
level counts side by side. A reader that silently narrows data cannot be caught by reading
code; it can only be caught by reading the same bytes twice.

---

# Addendum 4 — the triage rule is wrong in both directions (measured)

ORCH's correction offers two triage questions: *"is my statistic absolute?"* and *"does it
divide a small quantity by a large one?"* — if both are no, you are probably fine.

**I planted ORCH's narrowing on the CA renders and re-ran every statistic V-CA reported
through it.** `v10_planted_narrowing.py` reproduces what PIL returns (keep the high byte)
without going through PIL, so the arms stay aligned and only the narrowing changes.

| statistic | class under ORCH's rule | truth | narrowed | **error** |
|---|---|---|---|---|
| **excess fall %** *(the headline)* | ratio — safe | 60.961 | 60.931 | **−0.0 %** |
| band-0 raw change % | ratio — safe | −29.360 | −29.362 | **0.0 %** |
| whole-frame change % | **small/large — suspect** | −4.910 | −4.906 | **−0.1 %** |
| mean \|dG\| DN | **absolute — suspect** | 50.034 | 50.236 | **+0.4 %** |
| mean \|dR\| DN | **absolute — suspect** | 540.176 | 542.249 | **+0.4 %** |
| \|dG\|/\|dR\| | **small/large — suspect** | 0.0926 | 0.0926 | **0.0 %** |
| **% px green changed** | **ratio — SAFE** | **94.410** | **17.549** | **−81.4 %** |

Same on the linear arm (excess fall −0.7 %, mean `|dG|` +0.3 %, **% px changed −84.2 %**).

## 4.1 What this shows

1. **"Ratios are largely protected" — CONFIRMED, and stronger than ORCH measured.** The
   headline moved **−0.0 %** (sRGB) and **−0.7 %** (linear), against ORCH's −1.0 %. Second
   instrument, same answer.
2. **"Absolute quantities are destroyed" — REFUTED for means.** `mean |dG| = 50 DN` is an
   absolute quantity **one fifth of a quantisation step**, and it survives with **+0.4 %**
   error. Quantisation error is ~zero-mean, so it cancels as `1/sqrt(N)` over 33 M pixels.
3. **"Small-over-large compresses toward a null" — REFUTED here.** `|dG|/|dR|` moved
   **0.0 %**; whole-frame change moved **−0.1 %**. Both survive because numerator *and*
   denominator are means over many pixels.
4. **The one statistic that IS annihilated is the one ORCH's rule waves through.**
   *"% of pixels changed"* is a bounded dimensionless fraction — a ratio — and it is wrong by
   **81–84 %**.

> **ORCH's rule flags two statistics that are fine to 0.4 % and passes the only one that is
> off by 84 %.** Distributed to the fleet it would cause exactly the cost ORCH just recorded
> against itself: needless re-runs of correct work, plus a miss on the real defect.

## 4.2 The discriminator that actually predicts the damage

Not absolute-vs-ratio. **Does the statistic AVERAGE, or does it THRESHOLD?**

- **Averaging** (means, sums, ratios of means): quantisation error is zero-mean and cancels.
  **Survives to <1 % even when the per-pixel signal is a fifth of one step.**
- **Thresholding / counting / ranking / hashing**: quantisation is **not** zero-mean at the
  threshold. Every difference smaller than one step rounds to **exactly zero**, so the count
  collapses in one direction only. **Destroyed.** This class includes: pixel-changed
  fractions, sign-flip and retention rates, medians and percentiles near the floor,
  distinct-level counts, and byte-hash identity.
- **Second moments** (variance, RMS, noise power, SNR): a third class. Uniform quantisation
  adds a *variance floor* of `step^2/12` ~ `257^2/12` ~ 5 500 DN^2. Additive, not
  cancelling — which is exactly why ORCH measured noise power 3.5x high and band SNR 0.438x
  of truth. **Biased upward, always.**

**Proposed triage questions, in place of ORCH's two:**

1. **Does my statistic count, threshold, rank, or hash pixels?** → **destroyed, re-run.**
2. **Is it a variance, RMS, noise power or SNR?** → **biased high by an additive floor, re-run.**
3. **Is it a mean, or a ratio of means, over many pixels?** → **survives to <1 %; say so with
   this number as the reason.**

## 4.3 Applied to V-CA's own numbers

All were read with `tifffile`, so nothing changes — but under the corrected rule:

- **Safe class (means and ratios of means):** the 61.0 % / 73.07 % excess fall, band-0 raw
  −29.4 % / −28.9 %, whole-frame −4.91 % / −3.58 %, `|dG|/|dR|` = 0.0926, and the
  interpolation-null fall-% profile in §2.3. Each verified to **<0.8 %** under a planted
  narrowing.
- **Destroyed class, had I used PIL:** the **94.41 % / 67.67 % pixel-changed footprints** and
  the **display-level percentiles** in §2.1 — the numbers I already withdrew for the
  independent reason that they measured the sRGB colour matrix. **Both of my reasons for
  striking them are now independent and both hold.**
- **Second-moment class:** the **Laplacian RMS** figures in Q7 (R −7.38 %, G +0.64 %). These
  would have carried an additive floor and read *too high*, in both arms — the ratio would
  have partly protected them, but I flag the class explicitly.

## 4.4 A third false positive on the list — `M103-halfdrift/src/crop2.py`

ORCH asked M103 for an exposure answer. Not my lane and not authoritative, but I already had
the scan, and one entry is the same class of error ORCH just apologised for:

| script | `np.asarray(Image.open(...))` on pixels | `tifffile` | reading |
|---|---|---|---|
| **`crop2.py`** | **0** | **7** | **pixels via `tifffile`; PIL only `fromarray`/`ImageDraw`** |
| `blobs.py` | 2 | 0 | `:136` decodes a **`.png` it just wrote** — 8-bit by construction |
| `waxmap.py` | 1 | 0 | `:143` `np.asarray(Image.open(p))` — **suspect, check `p`'s type** |
| `waxsweep.py` | 2 | 0 | `:90-91` pulls **green as float64** from two arms — **most suspect** |

**`crop2.py` is a false positive** — third one found on this list. `blobs.py:136` is a PNG
read-back and almost certainly harmless; `blobs.py:72` needs its return value checked.
**`waxsweep.py:90-91` is the one to look at first** — it is a two-arm sweep, and per §4.2 a
sweep of *means* would survive while any thresholded or counted quantity in it would not.

## 4.5 Recorded against ORCH's own lesson

ORCH's lesson — *"a triage list distributed to a fleet needs its own negative control"* — is
right, and the correction extends to the **rule** shipped with the list, not just its entries.
The rule was stated from the mechanism (narrowing loses precision, so absolute things suffer)
rather than measured against a statistic known to be fine. **One planted-narrowing run over
seven statistics falsified half of it.** The plant is cheap, it needs no PIL, and it is the
negative control the rule itself was missing.

---

# Addendum 5 — the published family does NOT survive the clean space. Correct the brief.

> ## ORCH's three published numbers are all materially overstated, and on a second subject two members CHANGE SIGN. My own Addendum 2 §2.5 was measured in the wrong space and is withdrawn.

**`bee-3-cpl`, sRGB (what the brief quotes) -> binned-linear (the measurement space):**

| family member | **sRGB (published)** | **binned-linear** | shift |
|---|---|---|---|
| whole-frame mean \|R−Y\| | **−4.91 %** | **−2.93 %** | +1.98 pp |
| near-edge (top-decile grad) | **−20.45 %** | **−14.25 %** | +6.20 pp |
| raw edge chroma (band 0) | **−29.36 %** | **−16.00 %** | **+13.36 pp** |
| decile-10 of \|R−Y\| (M110) | −18.85 % | −18.43 % | +0.42 pp |
| edge-localised excess K=5 | −60.96 % | **−31.14 %** | **+29.82 pp** |

**The brief says −29.4 / −20.5 / −4.9. In the measurement space those are −16.0 / −14.3 / −2.9.**
The edge number is overstated by a factor of **1.8x**; the headline excess **halves**.

**`wrapped-text-1` — worse, and it is the second subject:**

| family member | sRGB | binned-linear |
|---|---|---|
| whole-frame | −12.24 % | −4.06 % |
| near-edge | −36.38 % | **−3.20 %** |
| raw edge chroma (band 0) | −37.08 % | **+4.01 %  SIGN FLIP** |
| decile-10 | −53.12 % | −38.66 % |
| edge-localised excess K=5 | −48.02 % | **+9.40 %  SIGN FLIP** |

**On `wrapped-text-1`, in the space the project says to measure in, the correction makes
band-0 edge chroma WORSE.**

## 5.1 Where the inflation comes from — it is the demosaic, not the colour matrix

Three renders isolate the three factors. Edge-localised excess K=5, `bee-3-cpl`:

| render | matrix+gamma | demosaic | binning | excess fall |
|---|---|---|---|---|
| `default`/`ca` (sRGB) | **on** | on | off | **60.96 %** |
| `lind-*` (linear+demosaic) | off | **on** | off | **73.07 %** |
| `lin-*` (binned linear) | off | **off** | on | **31.14 %** |

**Removing the colour matrix and gamma RAISES the number (61 -> 73). Removing the demosaic
HALVES it (73 -> 31).** The contamination M113 warned about is real but points the other way;
the dominant inflation is the **demosaic**, which interpolates R and B using G as a guide, so a
red-plane shift changes demosaic behaviour and amplifies the apparent chroma change.

**This is a finding about my instrument, and I report it as one.** Addendum 2 §2.5 claimed *"the
headline SURVIVES and GROWS… 73.07 %"*. That was measured on `lind-*.tif` — linear **with the
demosaic still in**. I treated "linear" as synonymous with "clean" and it is not: M110's own
cell C is binned-linear, and I had cited that table two sections earlier. **§2.5 is withdrawn.**
The correct statement is that the headline **halves** in the measurement space.

## 5.2 Verified before reporting — three checks

`v12_verify_clean_space.py`:

**(1) The arm is live and the files are correct.** Red moved on **96.875 %** (`bee-3-cpl`) and
**97.393 %** (`wrapped-text-1`); green and blue moved on **exactly 0 pixels, max delta 0 DN**.
**This independently reproduces M110's cell C and its retraction** — CA is a pure red-plane
operation in camera space, confirmed by a second body.

**(2) M110 §14.4's radial monotonicity — the strongest pro-correction evidence in the corpus —
DOES NOT SURVIVE.** Red-chroma change on edge pixels by normalised radius:

| r | `bee-3-cpl` | `wrapped-text-1` |
|---|---|---|
| 0.0–0.1 | −2.85 % | — |
| 0.1–0.2 | **+6.05 %** | **+7.78 %** |
| 0.2–0.3 | **+23.47 %** | **+9.70 %** |
| 0.3–0.4 | **+6.84 %** | **+19.03 %** |
| 0.4–0.5 | −22.34 % | **+7.63 %** |
| 0.5–0.6 | −6.79 % | **+2.92 %** |
| 0.6–0.7 | −17.48 % | −6.34 % |
| 0.7–0.8 | −35.99 % | −4.98 % |
| 0.8–0.9 | **−46.82 %** | **+0.75 %** |

Not zero-at-centre and not monotone. There is a **positive (harmful) lobe from r ≈ 0.1 to 0.4
on `bee-3-cpl`, peaking at +23.5 % worse**, and on `wrapped-text-1` the harmful lobe covers
**r = 0.1 to 0.6** and the corner never recovers. The corner result on `bee-3-cpl` (−46.8 %) is
real and large — **the correction works at the periphery and damages the mid-field.**

*Honest alternative reading, which I cannot exclude:* at r = 0.2–0.3 the displacement is
`704.5e-6 x ~1000 sensels = 0.70 sensels = 0.35 binned px` — **sub-pixel in the measurement
grid**, so the positive lobe may be interpolation of red at small displacement rather than
over-correction. Either way it is a measured harm in the clean space that no report records,
and the `anti` arm would separate the two.

**(3) On the owner's flagship subject the dominant fringe is one the correction cannot touch.**
On `bee-3-cpl` edge pixels, `|B−Y| / |R−Y| = 1.356` in the OFF arm — **blue/yellow fringing is
36 % larger than red/cyan**, and `eps_b = None` leaves it at **−1.27 %** (a second-order effect
of `Y` moving, since blue itself moved on 0 pixels). Per fact 1537 the red-only correction does
fix both sides of a *red/cyan* fringe — but it is structurally blind to the larger defect here.

## 5.3 ORCH's broader test: is the family space-dependent? YES, and worse than reordering

- **Ordering changes.** sRGB (`bee`): excess > raw-edge > near-edge > decile-10 > whole-frame.
  Binned-linear: excess > **decile-10 > raw-edge > near-edge** > whole-frame — decile-10 moves
  from 4th to 2nd, overtaking two members.
- **Spacing changes.** Raw-edge/whole-frame is **6.0x** in sRGB and **5.5x** in binned-linear on
  `bee`; on `wrapped-text-1` it goes from **3.0x** to **−1.0x** — the ratio changes sign.
- **Members change sign.** Two of five on `wrapped-text-1`.

> **Discipline 847 is not strong enough.** It says choose the honest member of the family. The
> measurement says **the family itself is space-dependent, and two of its members reverse sign
> between spaces.** No member is quotable without naming the space, and "edge chroma fell 29 %"
> is not a fact about the correction — it is a fact about the correction *as seen through a
> demosaic*.

## 5.4 Recommended correction to the brief

Both spaces are legitimate for different claims, and the brief should say which it is quoting:

- **What the owner will SEE** in his sRGB export: −29.4 % edge, −20.5 % near-edge, −4.9 %
  whole-frame. **These are not wrong** — they describe the picture he opens.
- **How much red/green misregistration is PHYSICALLY removed**: −16.0 % edge, −14.3 %
  near-edge, −2.9 % whole-frame.

Suggested wording: *"On your own gear this removes about **16 %** of the physical red/green
misregistration at edges, which shows up as roughly **29 %** less edge colour fringing in the
JPEG you look at — the difference is the demosaic amplifying it. On a second test subject it
gave no benefit at all, and it makes the mid-field slightly worse while clearly helping the
corners. Blue/yellow fringing, which on your bee frames is the larger defect, is untouched."*

**If ORCH prefers one number: quote −16.0 %, and name the space.** It is the member that is
stable under the transform that matters and it is the one that will still be true tomorrow.

## 5.5 The `anti` arm — exact patch, and it cannot be approximated

**It cannot be approximated with anything that exists.** Three candidates, all fail:

1. **Apply the profile twice** — composition gives scale `(1+eps)^2 = 1 + 2eps + eps^2`, i.e.
   **double strength, not negated**. Two negatives cannot make a positive here.
2. **An existing negative-coefficient path** — there is none; both consts carry
   `eps_r = -704.5e-6`, and `PROFILES` (`optics.rs:332`) has exactly one entry.
3. **`STREHL_WARPMAP`** — the alignment transform applies to **all channels equally**, so it
   cannot express a red-only magnification. Fact 1529 stands: no strength knob exists.

**Minimum patch — 3 statements, no logic change, no new env var.** The file's own idiom
(`_RADIAL` at `optics.rs:374-377`) is struct-update syntax:

```rust
// optics.rs, beside A7C2_FE100GM_2XTC_X4CPL_RADIAL (~line 377)
#[cfg(any(test, feature = "ca-anti"))]
pub const A7C2_FE100GM_2XTC_X4CPL_ANTI: OpticalProfile = OpticalProfile {
    key: "a7c2-fe100gm-2xtc-x4cpl-anti",
    eps_r: 704.5e-6,            // NEGATED; blur-identical, aberration doubled
    translation: (0.0, 0.0),    // match _RADIAL: translation is not applied
    ..A7C2_FE100GM_2XTC_X4CPL
};

// optics.rs, in profile_from_setting, immediately after the block at 457-459
#[cfg(any(test, feature = "ca-anti"))]
if raw == A7C2_FE100GM_2XTC_X4CPL_ANTI.key {
    return Ok(Some(&A7C2_FE100GM_2XTC_X4CPL_ANTI));
}
```

**Design notes for whoever owns the file:**

- **Do NOT add it to `PROFILES`** (`optics.rs:332`, `[&OpticalProfile; 1]`). That array is
  iterated at `:359` for key lookup and at `:403` to print *"known profiles"* in the error
  message. Adding it there would (a) require a type change to `; 2]`, and (b) **advertise an
  intentionally-wrong correction to every user who mistypes the key**. The explicit `if` keeps
  it working and unadvertised.
- **`#[cfg(any(test, feature = "ca-anti"))]` means a shipped binary cannot enable it at all** —
  the research render is built with `--features ca-anti`. Without this gate the anti arm is a
  live footgun.
- **No existing test breaks.** `the_two_profiles_differ_only_in_translation` (`:957`) compares
  only the named pair; `the_profile_names_its_whole_path` (`:1037`) touches only the one const;
  `l1_zero_correction_is_bitwise_identity` (`:531`) is unaffected. The `..` struct-update
  inherits `optical_path`, `measured_from`, `support_r_max` and `fit_r` unchanged, so
  provenance cannot silently diverge.
- **A strength-knob alternative is worse.** `active_profile_scaled(scale: f64)` would have to
  return an **owned** `OpticalProfile` rather than `&'static`, rippling into **`align_cmd.rs:324`** and
  **`align_cmd.rs:1317`** (verified at HEAD; the `merge.rs` hits are doc-comment references
  only, so the true ripple is two call sites plus a lifetime change) — against three statements
  for the data-only form. **Recommend the data-only form.**

**Registered prediction, before the render.** If the correction is sound: `anti` should roughly
**double** edge chroma where `on` roughly halves it, and `(anti + on)/2` should reproduce `off`.
If the measured gain is an artefact of moving red at all: **`anti` will also reduce chroma.**
Given §5.2's mid-field harmful lobe, the most informative cut is **fall-% by radius** — the
prediction is that `anti`'s profile is the mirror of `on`'s about zero at every radius.

---

# Addendum 6 — matrix correction confirmed; V-CA exposure NIL; and the rings artefact says the shipped coefficient over-corrects every subject ever measured

## 6.1 ORCH's matrix correction: confirmed independently, and it is stronger than stated

Re-derived from the crate's own constants (`color.rs:79-83` `SRGB_TO_XYZ_D65`,
`strehl-raw/src/lib.rs:376-380` the A7C II `xyz_to_cam`), not by running ORCH's script —
`experiments/V-CA/v13_matrix_check.py`:

```
CRATE  inv(rownorm(A@S)):        CORPUS rownorm(inv(A@S)):
 [ 1.636062 -0.448619 -0.187443]   [ 1.197506 -0.125014 -0.072492]
 [-0.115165  1.488971 -0.373806]   [-0.453042  2.230018 -0.776976]
 [-0.004740 -0.323601  1.328341]   [-0.008259 -0.214665  1.222924]

leak g->R, r->G   crate : 27.4%  7.7%
leak g->R, r->G   corpus: 10.4%  20.3%
max|crate - ORCH's quoted matrix| = 4.79e-07
crate green row = [-0.115165 1.488971 -0.373806];  color.rs:221 doc = [-0.115 1.489 -0.374]
agree to 3dp? True     corpus green row -> doc match? False
```

`color.rs:191-208` read directly: step 2 row-normalises `cam_from_srgb`, step 3 inverts.
**Normalise-then-invert. ORCH is right on every count**, including the swap (27.4/7.7 vs the
corpus's 10.4/20.3) and the doc-comment cross-check.

**One refinement, and it is good news: no render has ever been affected.** `git log --follow`
shows `color.rs` has been touched by exactly three commits — `e59f1b0` (M85, first),
`fb2f4ef` (M100), `3e58676` (M109). **The first version already reads `// 2. Row-normalise` /
`// 3. Invert`.** The *arithmetic* has been correct since the file was created, not merely
documented correctly since `3e58676`. So the blast radius is strictly **paper numbers computed
by applying the corpus constants in Python**; every TIFF the crate has ever written used the
correct matrix.

## 6.2 V-CA exposure: NIL, and I can prove it rather than argue it

- **No V-CA script contains any matrix constant.** Mechanical scan of all 15 scripts for
  `1.636|0.4486|0.1151|1.4889|camera_to_srgb|xyz_to_cam|rownorm|10.4|20.3` returns **zero hits**.
- **No number in this report was produced by applying a matrix.** My clean-space work reads
  crate-written renders. `image_out.rs:353` asserts the linear path's own caveat string is
  **`"linear camera-native RGB"`** — `lin-*.tif` has **no matrix applied at all**, which is also
  what M110 L1343 says (*"in camera space"*). §5.1's demosaic-vs-matrix attribution is therefore
  **not** the kind ORCH flagged: it compares three renders, and does not multiply by anything.
- **I never quoted ±15 ppm, the leak percentages, or fact 1587's universal form.** Grep of
  `V-CA-audit.md` for `15 ppm|10.4 %|20.3 %|0.00 % exactly` returns nothing.

## 6.3 The two other corrections, checked against the artefacts I hold

**Fact 1587 / overshoot — ORCH's correction is confirmed to the digit**, from
`M110-sheet/ca_overshoot_default_vs_ca.json`, which I have on disk:

| ORCH's claim | artefact | verdict |
|---|---|---|
| `0.00 %` is the off-vs-off control | `null_control_worst: 0.0`, a **separate field** from `overshoot_inert_null` | confirmed |
| real null runs 4.68–25.73 % | `overshoot_inert_null` min **4.68** (bee r 0.0-0.1), max **25.73** (flat-on-ruler r 0.1-0.2) | confirmed |
| artefact `overshoot_pct` reaches 18.82 % | `overshoot_real`, flat-on-ruler-cpl, r 0.3-0.4: **18.82** | confirmed |

*My own citation survives:* §Q5 L480 cites the **real** per-radius values (9.73 -> 9.78 -> 9.47 %
beyond `support_r_max`), which is the narrow no-discontinuity claim, not the universal null.
**But L302 restates M110 fact 53 as *"does not overshoot — a genuine null in the correction's
favour"*, which inherits exactly the scope inflation ORCH describes.** The artefact shows real
overshoot of 8.6–9.9 % across bee's mid-field. **L302 is corrected: the null is "no discontinuity
at the support boundary", not "no overshoot".**

**±15 ppm — retraction confirmed, but ORCH's replacement number is not the worst case.**
`M113-ca/c10_rings.json`, `couch-fibers-cpl/off/rows[0]`, `rbar = 0.1103`:
`eps_sd = 8.003298e-05` = **80.0 ppm**. Exact. However the file's sd is governed by ring
population and spans **3.1 ppm (n=178) to 127.9 ppm (n=7, bee's outermost ring)**. The honest
statement is not "80.0 not 15" but **"the tolerance is radius- and n-dependent over 3.1–127.9
ppm and no single number is quotable"** — the same disease as discipline 847, one level down.
Worst case is **8.5x** the retracted figure, not 5x.

## 6.4 The finding: the shipped coefficient over-corrects BOTH subjects it was ever fitted against

`v15_overshoot_mechanism.py`, reading `c10_rings.json` `eps_global`:

| subject | uncorrected `eps` | after correction | applied | vs shipped −704.5 |
|---|---|---|---|---|
| `bee-3-cpl` | **−529.9 ppm** | **+132.3 ppm** | 662.2 | −6.0 % |
| `couch-fibers-cpl` | **−654.9 ppm** | **+36.5 ppm** | 691.3 | −1.9 % |

**The residual is positive on both subjects — the correction pushes past zero and re-introduces
the aberration with the opposite sign.** On `bee-3-cpl` the residual is **25.0 % of the
aberration it started with**. And it is not noise: **every one of bee's seven rings is positive**,
at +130.9 ± 5.3 (25σ) and +133.2 ± 4.4 (30σ) in the two best-populated rings.

**Why: one constant, two different lenses-worth of aberration.** The shipped `eps_r = −704.5 ppm`
(`optics.rs:319`) is **larger in magnitude than both measured subjects** (−529.9 and −654.9).
It over-corrects everything that has ever been put in front of it.

**This is also where the 23.6 % lives.** In Q5 I reported the scene-to-scene spread as
*"actively unexplained"* and cited it by fact number. **Per ORCH's new discipline, here is the
artefact:** `c10_rings.json`, `eps_global` of the two `off` arms — 529.9 vs 654.9 ppm is
**23.6 % of the smaller, to one decimal.** It is not an abstraction; it is the difference
between a 5.6 % residual and a 25.0 % residual on the two subjects that exist.

## 6.5 This ADJUDICATES my own §5.2, and partly against me

§5.2 offered two readings of the mid-field positive lobe I measured in binned-linear
(+23.47 % worse red chroma at r 0.2–0.3 on bee): genuine over-correction, or interpolation blur
at sub-pixel displacement. **The rings artefact is an independent geometric instrument on the
same subject, and it favours the interpolation reading.** In displacement terms bee improves at
every radius:

- r = 0.234: `529.9e-6 x 0.234 x 4225 px` = **0.52 px** -> residual `141.6e-6` = **0.14 px**
- r = 0.873: **1.95 px** -> **0.22 px**

**Red/green registration gets better everywhere on bee, including the mid-field where my chroma
stencil said it got worse.** A ring fit measures misregistration directly; `|R−Y|` is a colour
proxy that also responds to blur. Where the two disagree at sub-pixel displacement, the ring fit
is the better instrument. **§5.2's "the correction damages the mid-field" is withdrawn** in
favour of "the correction's *residual* is smallest in displacement terms everywhere, but moving
red by a fraction of a pixel blurs it, and that blur is what my chroma statistic detected."

That said, §5.2's *measurement* stands and matters for the owner: **the thing he will see in the
mid-field is slightly more red blur, not less fringing** — because at 0.14 px there is nothing
left to unfringe, only interpolation to pay for.

## 6.6 Net effect on the verdict

**Unchanged: NO to default-on, and §6.4 is now among the strongest reasons.** A correction whose
single hard-coded coefficient over-corrects **100 % of the subjects it has ever been measured
against** — by 5.6 % on one and 25.0 % on the other — is a correction with no established
scale, let alone one established across bodies and lenses. This is the 23.6 % generality problem
restated in the only units that matter: **residual aberration after correction.**

**And it sharpens the `anti` proposal in §5.5 into something better.** The right experiment is
no longer a two-point on/anti contrast but a **strength sweep**, because the artefact now
predicts the optimum is *not* at 1.0x: bee's minimum residual is near **0.752x** the shipped
coefficient (529.9/704.5) and couch's near **0.930x** (654.9/704.5). The same data-only patch delivers it — add consts at
`eps_r` = −352.25e-6 (0.5x), −528.4e-6 (0.75x), −880.6e-6 (1.25x) and +704.5e-6 (the anti arm)
and the sweep is four renders with no logic change at all.

---

# Addendum 7 — the ALIGN=0 trap (cleared, two ways), a 9-dose response on my own estimators, and the withdrawal of MY replacement rule too

## 7.1 `STREHL_ALIGN=0` — ORCH's claim confirmed in code, and my audit cleared twice over

**The claim is real.** `merge_cmd.rs:2012` names it explicitly:

> *"The precedent not to repeat is STREHL_FIX_CA, a byte-identical no-op under
> `STREHL_ALIGN=0` that says nothing at all."*

Mechanism confirmed: `active_profile()` is called at **`align_cmd.rs:1317`, inside
`warp_frame_in_place`** — so if `align_enabled()` (`align_cmd.rs:880`) is false, the CA profile is
never consulted. This is the structural-inertness trap, and **it would have voided this entire
audit had my renders hit it.** They did not, and I can show it two independent ways:

1. **Documentary.** `M110-sheet/manifest.json` sets `STREHL_FIX_CA` and a per-scene
   `STREHL_WARPMAP` sidecar for every arm, and **contains no `STREHL_ALIGN` at all**.
   `byte-freezes.tsv:47` states the convention: *"`0` = registration off. `unset` = on."*
2. **Empirical, and stronger.** §5.2 measured **R moving on 96.875 % of pixels, max delta
   11 069 DN**. A byte-identical no-op cannot produce that. **The "is the arm live" check I ran
   for a different reason is exactly the guard against this hazard, and it passed.**

**Generalisable point for the fleet:** the defence against a structurally-inert gate is not
reading the env record — it is measuring that the two arms differ *at all* before measuring by
how much. That check costs one line and subsumes the code read.

## 7.2 A 9-dose response on my own estimators — `v16_dose_response.py`

ORCH's replacement instruction is "measure it with a dose-response control." **My v10 was a
single-dose plant**, so I built the sweep. `bee-3-cpl`, sRGB pair, 3 298 065 edge pixels,
identical stencil at every dose:

| bits | levels | fall_edge % | \|dG\|/\|dR\| | % px R chg | var-ratio |
|---|---|---|---|---|---|
| **16** | 56 185 | **−19.123** | **0.0926** | **98.656** | **0.6482** |
| 12 | 3 887 | −19.123 | 0.0926 | 93.109 | 0.6482 |
| 10 | 1 018 | −19.121 | 0.0926 | 80.517 | 0.6482 |
| **8** | 256 | **−19.107** | **0.0926** | **61.155** | **0.6484** |
| 6 | 64 | −18.903 | 0.0924 | 34.040 | 0.6515 |

Error against the true 16-bit value:

| bits | fall_edge | \|dG\|/\|dR\| | % px chg | var-ratio |
|---|---|---|---|---|
| 12 | −0.0 % | −0.0 % | **−5.6 %** | 0.0 % |
| 8 | **+0.1 %** | **0.0 %** | **−38.0 %** | 0.0 % |
| 6 | +1.2 % | −0.3 % | **−65.5 %** | +0.5 % |

**My headline is immune at 9 doses, monotone, no reversal.** The counting statistic degrades
monotonically to −65.5 %. **No V-CA script uses a differencing, split-half or paired noise
estimator** (mechanical scan of all 17: zero hits), so ORCH's correlated-error hazard — the one
that books quantisation as signal — does not reach any clearance I published.

## 7.3 Two numbers that do not fit, chased rather than banked

**M111's term-disparity prediction fails on my statistic.** My `|dG|/|dR|` has
**D = max/min = 10.80** — high disparity, where M111 measures median |shift| ≈ 8.04 %.
**Measured: 0.0 % at 8-bit, −0.3 % at 6-bit.** Two orders of magnitude off the prediction.

**M115's sign reversal does not appear.** My var-ratio, a second-moment ratio, moves
0.6482 → 0.6515 (**+0.5 %** at 6-bit). No inversion, no widening.

**Both reconcile, and neither report is wrong.** `v17_operative_variable.py`:

- **M111:** D governs cancellation *at fixed N*. M111's D-bins are per-tile over 1547 tiles;
  my ratio averages **N = 3 298 065** edge pixels, where zero-mean error falls as
  `1/sqrt(N) = 5.5e-4`. **N, not D, is doing the work** — the two results are the same law at
  different N.
- **M115:** the asymptote needs `q >~ P_noise`. At 8-bit my headline's
  **`q/P = 0.00141`** — the perturbation lands three orders of magnitude below the measured
  power. **M115's regime is small-signal; mine is not.** Its result is untouched.

## 7.4 And this kills MY replacement rule — and the one I was about to propose

Addendum 4 offered **"averaging vs thresholding"** as the correct axis. The dose-response shows
it is **directionally right for the wrong stated reason**, and the obvious repair is also wrong:

| statistic | `q/P` at 8-bit | 8-bit error |
|---|---|---|
| edge \|R−Y\| (headline) | 0.00141 | **+0.1 %** |
| `% px R changed` | **0.00425** | **−38.0 %** |
| \|dG\| (the ratio's numerator) | **0.52499** | 0.0 % *(in the ratio)* |

**A statistic with `q/P = 0.004` is destroyed while one with `q/P = 0.525` survives perfectly.**
So `q/P` — the variable I was one paragraph from proposing — **does not predict failure either**.

The mechanism that does fit all four: **`% px changed` is a discontinuous functional.** It asks
`dR != 0`, so an arbitrarily small perturbation flips the answer and no favourable `q/P` or `N`
can rescue it. The others are smooth functionals, where error goes as `q/(P·sqrt(N))`.
**Averaging sets the *rate* for the smooth class; smoothness sets the *class*.**

**I am not proposing that as a fleet rule.** I have measured it on one dataset with four
statistics, which is exactly the evidence base from which I over-generalised last time.
Addendum 4's taxonomy is **withdrawn** to the status of a measurement on V-CA's own estimators.
ORCH's conclusion is the right one and I have now reproduced it against myself: **two candidate
form-rules, mine and `q/P`, both fail on my own four statistics. Expand the algebra or run the
dose-response. There is no third option.**

## 7.5 Verdict

**Unchanged: NO to default-on.** Nothing in this round touches the substantive case — it
confirms my instruments rather than my conclusions. The `STREHL_ALIGN=0` trap is cleared, the
headline survives a 9-dose sweep at +0.1 %, and §6.4's finding stands untouched: **the shipped
coefficient over-corrects 100 % of the subjects it has ever been measured against.**

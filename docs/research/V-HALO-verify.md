# V-HALO: independent verification of BUILD-HALO (3315a91, e5e62d4)

**VERDICT: CONFIRMED WITH QUALIFICATION.**

The fix does what it says on the tin mechanically — I reproduced both of its arms
byte-for-byte from a pinned tree — but two of its supporting numbers do not
survive, and its own sharpness evidence is measuring the artefact it introduced.
**It is not print-worthy, and the disqualifier has changed identity.**

Scope: everything below verifies commit `e5e62d4` (tree `e5e62d46...`). While I
worked, `bca6df3` ("halo v2: interpolate the depth grid and feather the treatment
boundary") landed, plus further uncommitted edits to `edgeaware.rs`. **None of
v2 is verified here.** That v2 exists is itself corroboration of section 4 below.

All measurements are mine and are **UNVERIFIED** by anyone else.

---

## 0. Method: the pin, and its commissioning

Two implementers were editing the tree throughout. I did not hash arms; I removed
the confound. `git archive` of the explicit SHA `e5e62d46...` into
`C:\dev\strehl-out\V-HALO\pin`, built there, and every arm below rendered from
that binary. This was the right call: HEAD moved from `e5e62d4` to `bca6df3`
mid-session and `edgeaware.rs` was modified in the live working tree.

**The pin resolves to its own sources**, proved rather than assumed: planting a
sabotage caused `cargo` to print
`Compiling strehl-core v0.0.0 (C:\dev\strehl-out\V-HALO\pin\crates\strehl-core)`.

**Commissioned with two sabotages, both required to go RED:**

| sabotage | target | expected | observed | |
|---|---|---|---|---|
| S1 | `LayerSupport::apply_at` discards the masked mean (`edgeaware.rs:614`) | `EDGE_AWARE=1` collapses onto the `off` hash | `sabo-on` = `D2DC0272…` = `off` | **RED** |
| S2 | `window_radius()` ignores `STREHL_WINDOW_RADIUS` (`focus.rs:111`) | ladder rungs become byte-identical | `sabo-w3` = `sabo-w26` = `895E458D…` | **RED** |
| control | no sabotage | arms differ | `on` `21191A3B…` != `off` `D2DC0272…`; `w3` `0D25ED22…` != `w26` `FDCA03B0…` | **live** |

Both instruments distinguish a live feature from an inert one. Pin restored from
`$env:TEMP` copies and confirmed content-identical to the pinned commit (949 and
1176 lines, exact match).

---

## 1. The mechanism slope — CONFIRMED IN SLOPE, TWO NUMBERS KILLED

### 1.1 The analytic half is exact and already unit-tested

`focus::tests::centre_tap_fraction_and_read_extent_are_what_m13_specified`
**measures** the read extent by perturbing one pixel and counting how many
outputs move. It asserts `taps == (2*(SOBEL_RADIUS + WINDOW_RADIUS)+1)^2 == 841`.
It passes in the pin. So the *support* identity is not a fit, it is exact: the
focus field at `p` cannot see content beyond Chebyshev radius `1 + w`. Slope 1 is
an upper bound by construction.

### 1.2 The empirical ladder: slope replicates, per-rung values do not

I re-rendered all six rungs from the pin (bee-3-cpl, 299 frames, `--gate 0`,
`STREHL_ALIGN=0`) and scored them.

| `WINDOW_RADIUS` | 3 | 6 | 9 | 13 | 20 | 26 |
|---|---|---|---|---|---|---|
| **published** rim cutoff | 9.25 | 9.75 | 10.75 | 14.00 | 21.25 | 29.00 |
| **my** rim cutoff | 30.00 | 30.00 | 11.50 | 15.00 | 24.25 | `nan` |
| **published** rim `w50` | 8.75 | 8.75 | 9.50 | 10.75 | 19.00 | 25.75 |
| **my** rim `w50` | 17.75 | 26.50 | 11.00 | 13.00 | 20.25 | 28.50 |
| **my** accepted edge count | 21 | 32 | 44 | 79 | 118 | 129 |

My rim `w50` over w9..w26 regresses on `W` with **slope +1.043**. The
dose-response is real and it is monotone. **The mechanism claim survives.**

Four things do not:

**(a) The intercept `1.08` is not in the data.** I refit their own published
table every way it can be fit — `cutoff`, `rim w50`, `C w50`, against `W`, `W+1`
and `W+2`, over all 57 subsets of >=3 rungs. **No fit returns an intercept within
0.05 of 1.08.** The headline fit (`cutoff ~ W`, w9..w26) reproduces their slope
exactly at **1.0750** and returns an intercept of **0.4750 +/- 1.1761**. With four
points quantised at 0.25 px the intercept is not measured at all; "intercept 1.08,
that is `SOBEL_RADIUS`" is an unfalsifiable read of a number that is +/-1.2 wide and
whose point estimate is closer to 0.5 than to 1. The claim should rest on the
slope and on section 1.1, and say so.

**(b) The ladder is unpaired, three times worse than the read they disqualified
for it.** Section 5.2 rejects the before/after because "`scan()` re-detects edges
in each arm's own image, and the edge counts differ by 2x". Across the section 1
ladder the accepted edge count runs **21 -> 129, a 6.1x drift**, and it rises
monotonically with `w` — wider window, more veil, smoother far plateaus, more
edges pass the `sd/A <= 0.10` flatness gate. The population is selected on the
very quantity the halo produces. The counts are not reported in section 1.

**(c) The paired read cannot measure the ladder either.** Scoring every rung on
one frozen donor edge set returns **`bright: ext=+nan` on 4 of 5 arms**
(`C_d0` inflates to 54.96 / 49.20 / 49.20 / 43.52 px, all beyond
`PLATEAU[0] = 30`). There is no paired measurement of this ladder, in either
direction.

**(d) The top rung sits on the instrument's ceiling.** `outer_cutoff` searches
only `dist <= PLATEAU[0] = 30`. Their w26 value of 29.00 is 1 px under the cap;
mine returns `nan`. The rung carrying the most regression leverage is at the
ceiling, and `PLATEAU = (30,45)` leaves a w26 rim only 3 px of clearance before
the "far plateau" it normalises against.

**Is the estimator itself a function of `w`?** Not directly — `scan()` is never
passed `w`, and `DMAX`, `DSTEP`, `PLATEAU`, `NEAR`, `BANDS`, `GRAD_PCT`, `ISO`,
`FLAT_TOL`, `MIN_AMPLITUDE` and the cached classifier are all fixed. The
circularity is indirect and is (b): the edge *set* is re-derived per rung from a
percentile of that rung's own gradient field.

### 1.3 The report contradicts itself on the same arm

Section 1's `w13` rung and section 5.2's `bee-3-cpl` "before" are **the same
render measured with the same instrument** (bee-3-cpl, gate 0, `ALIGN=0`,
`WINDOW_RADIUS=13`). The document reports both:

| | rim `w50` | rim cutoff | `C` `w50` | `C` peak | n |
|---|---|---|---|---|---|
| section 1, `w13` | 10.75 | 14.00 | 13.50 | — | — |
| section 5.2, "before" | — | — | 17.25 | +0.634 | 36 |
| **my render** | 13.00 | 15.00 | **17.25** | **+0.63424** | **36** |

My independent render reproduces **section 5.2 exactly**, to five decimals and to
the edge count, and hashes to `895E458D…` — the hash `3315a91`'s own commit
message quotes. **Section 1's ladder does not reproduce from the pinned tree.**
Section 9 and section 5.2 do. Whatever section 1 was measured on, it was not this
code; its per-rung numbers should not be quoted.

---

## 2. Dark when unset — CONFIRMED BYTE-EXACTLY, one hash in the report is wrong

Rendered from my pin, `bee-2-cpl`, product default gate, alignment on:

| arm | SHA-256 | |
|---|---|---|
| `STREHL_EDGE_AWARE` unset | `D2DC02728033E359035C5BB1C122A5F8F93D50009CBD9F2D41B4885AE013331D` | |
| `STREHL_EDGE_AWARE=0` | `D2DC0272…E013331D` | identical |
| BUILD-RENDER frozen baseline | `D2DC0272…E013331D` | identical |
| BUILD-HALO `halo-off` | `D2DC0272…E013331D` | identical |
| `STREHL_EDGE_AWARE=1` | `21191A3B81291C9A0C83F694F803768B56DC239E357DDA93AEC00D94FFD20880` | **differs** |
| BUILD-HALO `halo-on` | `21191A3B…FFD20880` | identical |
| **S1-sabotaged** `=1` | `D2DC0272…E013331D` | **RED — collapses** |

Both of their arms reproduce bit-for-bit from a tree nothing else could write to.
The feature is genuinely dark when unset; it is genuinely live when set; and the
instrument tells those two states apart (S1). **Claim confirmed.** As a
side-effect this retires the section 8 concurrency confound for section 9 — their
frozen-ROI campaign was not contaminated.

**Defect (documentation, low):** `BUILD-HALO.md` section 3 states the flag-unset /
pristine-HEAD identity as "both `965AA23B...`". The true hash of that arm is
`895E458D…` — which is what commit `3315a91`'s message says, and what my own
render of it produces. `965AA23B` appears to be stale. The report and its own
commit message disagree on the evidence for the same claim.

**Cost:** 2.29x on my box (79.8 s -> 183.1 s), against their 2.07x (51.5 s ->
106.8 s). My box was contended; same order, not contradicted.

---

## 3. "Not a blur: 0 of 15 worse, +6.7%" — REPRODUCED EXACTLY, AND REFUTED AS EVIDENCE

I recomputed their statistics in linear (`tifffile`, `uint16` asserted, no PIL) on
their own deliverables at the frozen ROIs:

- detail crops, `hp_energy` ratio mean **1.0671**, **0 of 15 worse** — their
  +6.7%, exactly.
- flat crops, `noise_sd` ratio mean **1.0461** — their +4.6%, exactly.

Their arithmetic is right. The inference is not.

**(a) The same statistic rises on crops chosen for having no structure.**

| crop class | `hp_energy` all 15 | untouched crops | treated >=10% of pixels |
|---|---|---|---|
| detail | **1.0671** | 1.0029 (n=4) | **1.1227** (n=7) |
| **flat** | **1.1679** | 1.0000 (n=3) | **1.3057** (n=7) |
| edge | 1.2239 | — | 1.2553 (n=13) |

High-pass energy rising **+16.8%** on flat crops — and **+30.6%** on the flat
crops the operator actually fires on — cannot be sharpening. A featureless patch
has no detail to sharpen. Something is being *added*.

**(b) The statistic tracks how hard the operator fired, not quality.**
Pearson r(changed %, `hp_energy` ratio) = **+0.4994**;
r(changed %, `noise_sd` ratio) = **+0.7935** (n=45).

**(c) The mean is diluted by crops the operator never touched.** 4 of 15 detail
crops changed <1% of their pixels (three at `p99|delta| = 0 DN`); **3 crops changed
exactly zero pixels** (`bee-2/flat2`, `lavendar/flat0`, `lavendar/flat1`). They
score exactly 1.0000 and are counted in "0 of 15 worse". Conditioned on
treatment, the noise cost is **+12.3% (detail)** and **+5.8% (flat)**, peaking at
**+36.6%** (`bee-3/detail2`), not +4.6%.

**(d) The decisive case.** `bee-2-cpl detail1` scores `hp_energy` **+23.1%** — one
of the best in the set. Look at it: the dark leg has a **serrated white edge
chewed into it**, a row of hard-edged tongues that do not exist in the baseline.
`flower-inner-edge-cpl edge2` scores **+61.8%**, the largest gain in the entire
crop set, and is a smooth defocused field carved into hard-edged tonal plates.
**The statistic ranks as most improved the two crops that are most damaged.**

Crop *selection* is clean — the ROIs are frozen in BUILD-RENDER's plan, derived
from the baseline, so they were not chosen to flatter. The defect is the
statistic, not the sampling.

I found **no evidence of blurring**. "Not a blur" is probably true. But the
evidence offered does not establish it, and the same number would have been
produced by an operator that only added artefacts.

---

## 4. The new artefact — NOT "MILD", NOT CONFINED TO TRANSITIONS, AND A BAD TRADE

Section 9.5 calls it "mild blotchiness at treated transitions, visible on
`bee-2-cpl` edge2 … much less objectionable than the halo it replaces". I judged
this on the pictures, in linear, with my own before | after | delta panels
(delta full-scale = 1% of range).

The correction field is **a mosaic of hard-edged, adjacent, opposite-sign lobes**.
That is the `N_LAYERS = 6` bin boundary crossing a smooth depth ramp: the layer
index flips and the masked mean flips with it. A correction that removes a
box-window veil must be band-limited to the >=13 px window scale; this one is not.

Instrument (band-pass 2–8 px contrast on ground the *before* image says is
featureless), with a negative control — the identical correction field gaussian-
smoothed at sigma 8:

| arm | mean ratio vs before |
|---|---|
| **negative control** (same delta, made smooth) | **0.982x** — control passes |
| real edge-aware arm | **1.105x** (range 1.01–1.23x) |

(My first attempt at this instrument scored the *control* at 5.2% area — it was
reading amplitude, not sharpness. I discarded it. Reporting that because an
uncommissioned version of it would have handed me a large and wrong number.)

The pooled number is modest because the artefact is local; the pictures are not
modest. On `bee-2-cpl flat1` a smooth surface acquires a dense field of hard-edged
worm-like patches. On `bee-3-cpl edge1` the soft veil around the claw becomes a
**hard-edged white cut-out collar with free-floating white islands**. On
`flower-inner-edge-cpl edge2` a continuous bokeh gradient becomes tonal plates.

**Plain opinion on the trade: on `bee-2-cpl` and `bee-3-cpl` it is a bad one.** A
soft low-contrast veil reads as optical defocus — wrong, but natural. A hard-edged
opposite-sign mosaic reads as a processing failure, and the eye finds artificial
contours in smooth areas far faster than it finds a wash. At print scale, on a
smooth background, that is the more disqualifying of the two.

That BUILD-HALO has since committed `bca6df3` ("interpolate the depth grid and
feather the treatment boundary") is independent corroboration that this artefact
is real and material. That work is not verified here.

---

## 5. What is genuinely good

Not everything here is a complaint.

- **`flower-inner-edge-cpl edge0` is a real, large win.** In linear, the muddy
  grey-green veil goes and the trichome silhouettes come back crisp against a
  genuinely dark background. It is as good as claimed.
- **The `flower-bud` rim really does survive**, and the confidence-veto sweep
  really is a fair test of it: at `conf 1.15` the tight bright sheath is
  unchanged by eye. The "this is not a too-conservative guard" argument holds.
- **Section 5.2's refusal to spin `C`** is correct, and I reproduce all three of
  its reasons independently: edge sets differ per arm (mine: 21–129), the paired
  read returns `nan` (mine: 4 of 5 arms), and `outer_cutoff` is capped at 30 px.
  The only fault is that the same three objections apply to section 1's ladder
  and were not applied there.
- Treated fractions reproduce exactly from the render logs: 19.97 / 19.43 /
  17.19 / 10.62 / 9.15 %.
- 384 `strehl-core` tests pass in the pin, including all 13 new `edgeaware` tests.

---

## 6. Test coverage gap

The 13 new tests cover `LayerSupport` and `SelectionScale` as units. **The 279
new lines in `merge_cmd.rs` have no tests** — the guide election at
`GUIDE_RADIUS`, the `tau` default (1/8 of the robust winner span), the `conf`
default, and the two-pass substitution are exercised only by whole-image renders.
The shipped wiring is an untested change, which is an unverified change.

---

## 7. The number that does not fit

**`hp_energy` rises +16.8% on the flat crops, and +93.6% on `flower-bud flat1`.**

BUILD-HALO's account is "every gradient statistic rises slightly, so this is not
a blur." Nothing in that account explains a 17–94% rise in high-pass energy inside
regions the ROI plan selected *for containing no structure*. There is exactly one
thing that can put high-frequency energy into a featureless patch, and it is not
sharpness. That number was available in the same table as the +6.7% and was not
read.

Runners-up: the intercept `1.08`, which is absent from every fit of its own
table; and the 6.1x edge-count drift across the rungs of the ladder that the
whole thesis rests on.

---

## 8. Is it print-worthy?

**No — and the reason has changed.**

BUILD-HALO's own verdict (NOT print-worthy, PARTIAL) is right, but its reasoning
is too kind to itself: "materially reduced on 3 of 5 subjects, survives on 2".
What I see on the images is:

- `flower-inner-edge-cpl`: **better overall.** Real improvement, plus one invented
  hard edge in the smooth background.
- `lavendar-cpl`: **essentially unchanged.** 9.15% treated, minimal visible effect.
- `flower-bud-…-fern-cpl`: **unchanged where it matters.** Sheath survives; some
  new hard-edged patches appear on flat ground.
- `bee-2-cpl`, `bee-3-cpl`: **worse overall.** The veil is genuinely pushed back,
  and it is replaced by a hard-edged quantisation mosaic and cut-out collars that
  I would reject in a print faster than I would reject the veil.

**What specifically disqualifies it:** not the halo any more, but the
`N_LAYERS = 6` nearest-bin quantisation. It converts a smooth defocus wash into
hard-edged, opposite-sign plates on smooth ground, including on ROIs the plan
classified as flat and detail. Until the depth axis is interpolated and the
treatment boundary feathered, the treated render is not shippable on the two bee
subjects. `bca6df3` is aimed at exactly this; it needs its own verification pass,
and it needs one that does not use `hp_energy` as the sharpness proof.

---

## 9. Reproducing this

```powershell
git archive --format=tar e5e62d46fa30f29a56722d74b536fc13fabc708f -o pin-src.tar
# extract to a path no other agent can write, build there, render every arm from it
```

Artefacts: `C:\dev\strehl-out\V-HALO\` — `pin\` (the frozen tree), `ladder\`
(6 rungs + election maps), `ident\` (byte-identity arms), `sabo\` (both sabotage
arms), `look\` (before | after | delta panels), `crop-stats.json`,
`ladder-m121.json`, `ladder-donor26.json`, `blotch2.json`.

**Everything in this document is my own measurement and has not been
independently verified.**

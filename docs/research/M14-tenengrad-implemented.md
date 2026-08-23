# M14 — Tenengrad at a 27×27 window, shipped

**Status:** implemented, gated, and reproduced against M13's own harness output.
**Implements:** M11 (`docs/research/M11-focus-bakeoff-measured.md`) fact 41 — the
operator; M13 (`docs/research/M13-window-depth-measured.md`) fact 60 — the window.
**Owns:** `crates/strehl-core/src/focus.rs`, `crates/strehl-core/examples/focus-window-cost.rs`.
**Reproduce:** every command in this report is quoted verbatim in §7.

> **NOT INDEPENDENTLY VERIFIED.** Project rule 12: the author never verifies
> their own work. Everything below is labelled MEASURED / VERIFIED / DERIVED /
> ARGUED / UNVERIFIED and every number has a command attached. §8 is a list of
> the places where the M11/M13 specs did not survive contact with the code —
> read that first if you are the verifier.

---

## 0. The headline

The shipped focus measure was `|mean_3×3(L) − mean_7×7(L)| / max(σ_L, 10⁻³)`.
It is now
`box_mean(√(Gx² + Gy²), radius = 13) / max(σ_L, 10⁻³)`.

Through the shipped CLI, on the same corpus and the same flat ROI M2 published
its baseline against:

| | ring(1,3) — was | tenengrad-w13 — is | M13's harness said |
| --- | --- | --- | --- |
| flat-ROI merged-noise ratio | **1.253×** | **1.068×** | 1.067839 |
| stacked green σ | 35.328 DN | **30.114 DN** | 30.1138 |
| single frame 11 σ | 28.201 DN | 28.201 DN | 28.2007 |
| distinct winners in ROI | 22 | **6** | 6 |
| index-map speckle | 34.381% (M2 §3.1) | **1.010%** | not measured |

**MEASURED**, both columns, by the commands in §7.1 and §7.2.
**VERIFIED**: the middle column reproduces M13's independently-computed
`tenengrad-w13, width=1` row to every digit the CLI prints. M13's number came
out of `experiments/m13-window-depth/`, a separate workspace with its own
re-implementation of the operator; this one came out of `crates/`. They agree.
That is the strongest single piece of evidence that the implementation is the
operator M11 and M13 actually measured, and not a lookalike.

The speckle line deserves a caveat, in §6.

---

## 1. What was implemented, exactly

```
gx = 0.125 · ( L(x+1,y−1) + 2·L(x+1,y) + L(x+1,y+1)
             − L(x−1,y−1) − 2·L(x−1,y) − L(x−1,y+1) )
gy = 0.125 · ( L(x−1,y+1) + 2·L(x,y+1) + L(x+1,y+1)
             − L(x−1,y−1) − 2·L(x,y−1) − L(x+1,y−1) )
g  = sqrt(gx² + gy²)                            replicate-clamped at the border
focus = box_mean(g, radius = WINDOW_RADIUS) / max(green_luma_sigma(L), 1e-3)
```

- `WINDOW_RADIUS = 13` → 27×27 box.
- `SOBEL_RADIUS = 1`, `SUPPORT_RADIUS = SOBEL_RADIUS + WINDOW_RADIUS = 14`.
- Read extent per output pixel: `(2·14 + 1)² = 841` taps. **DERIVED**, asserted.
- Border policy: the Sobel replicate-clamps; `box_mean` clamps the window. Both
  unchanged from what the experiments did.

Requirement 1 — the box filter is `crates/strehl-core/src/boxfilter.rs::box_mean`,
the pre-existing separable running sum. No new convolution was written. §5 is the
measurement that this is actually what is running.

Requirement 2 — `WINDOW_RADIUS` is a single `pub const` with a doc comment
citing M13 §6.1 and fact 60, naming the defensible w11–w15 basin, and pointing
at **SYNTHESIS open question 17**: every M13 measurement was taken at regulariser
`width = 1`, so the optimum may move narrower once the merge regulariser is on.
Changing the window is a one-line edit. `SUPPORT_RADIUS` is derived from it, so
any future tile-margin or halo sizing tracks it automatically.

---

## 2. How the normalisation was determined (requirement 3)

Not guessed. Read out of the experiment source, then **reproduced from the
committed CSVs**.

**Step 1 — read the source.** `experiments/m11-focus-bakeoff/src/measures.rs`
parses `tenengrad-w{N}` into `Kind::Tenengrad { window: N, squared: false }` with
`Norm::Pointwise` and `degree() == 1`. `Norm::Pointwise` divides the windowed
response by `green_luma_sigma(L(p))` at each pixel — the same divisor the ring
used, applied after the window, not before.
`experiments/m13-window-depth/src/measures.rs::parse` builds `tenengrad-w13` the
same way (its `-nonorm` suffix is what selects `Norm::None`).

**Step 2 — confirm against the published CSV columns.**
`experiments/m11-focus-bakeoff/data/noise-109MSDCF.csv` carries, on every
`tenengrad-w5` row: `norm=sigma`, `degree=1`, `support_radius=6`, `support_px=13`.

**Step 3 — recompute M11's published figures from M11's own data.** Using M13
§1.1's rule (N = σ(merged)/σ(single middle frame), spatial sd, `roi_kind=flat`,
`width=1`, median over the four flat ROIs within a stack, mean over the two
stacks), from `noise-109MSDCF.csv`:

| operator | recomputed N | published N |
| --- | --- | --- |
| `ring-1-3` | **1.3475** | 1.3475 |
| `tenengrad-w5` | **1.1324** | 1.1324 |
| `tenengrad-w0` | 1.0632 | — |
| `tenengrad-w2` | 1.2255 | — |
| `tenengrad-w8` | 1.1019 | — |
| `tenengrad-w11` | 1.0908 | — |

**VERIFIED.** The published numbers belong to the pointwise-σ, degree-1,
magnitude form and to no other arm. The recomputation script was written to the
session scratch folder deliberately and is *not* committed — `experiments/` is
not mine to write to, and a duplicate analysis script in `crates/` would rot.
The reproduction is cheap to redo; §7.6 states the rule precisely enough to
re-derive it in a dozen lines.

**Why the divisor was kept even though it is a proxy.** The module doc retains
the original admission: dividing by `σ` of the *luma at that pixel* is not the
standard deviation of the focus response, so it is a proxy, not a studentisation.
The temptation is to "improve" it. Resisted, on purpose: N = 1.1324 and the
0.85 selectivity are properties of *this* divisor. Substituting a better one
invalidates both published figures and makes the bake-off unusable as evidence
for the choice it justified. Changing the normalisation is a new bake-off, not
a tidy-up.

---

## 3. The pinned test (requirement 4)

`centre_tap_fraction_is_the_value_m9_measured` is **renamed**, not deleted:
`centre_tap_fraction_and_read_extent_are_what_m13_specified`. `m9_measured` was
the wrong provenance the moment the operator changed.

It asserts four things. Three are analytic; the interesting decision is what it
does *not* assert.

**(a) Tap count → 841, exactly.** `(2·(1 + 13) + 1)² = 841`, measured by counting
the output pixels a single centre perturbation moves. **DERIVED and asserted
exactly.** This is the analytic quantity M13 §6.4 asked for.

**(b) φ_nonorm(w0) = 0, exactly, over exactly 8 live taps.** The Sobel centre
weight is 0 in both Gx and Gy, so perturbing p cannot change the response *at*
p — while it does change the response at the 8 neighbours. **DERIVED**;
corroborated by `experiments/m13-window-depth/data/phi-109MSDCF-nonorm.csv`,
whose `tenengrad-w0-nonorm` row is 0.0000000000 over 8 taps. This is the cheap
exact anchor the brief pointed at, and it is the one assertion in the whole file
that cannot drift with the plant.

**(c) φ_nonorm(w13) against the analytic 1/(2w+1)² = 1/729.** Measured
**0.00135328** vs 0.00137174 → **ratio 0.9865**. M13 measured 0.94 on real
109MSDCF texture. The shortfall from 1.0 is the Sobel's own 3×3 support: the
841-tap read extent is wider than the 729-tap box, so the centre's share is
diluted. Smoother synthetic texture dilutes it less, which is why 0.9865 > 0.94.
Asserted as a bracket **(0.88, 1.00)** — wide enough to hold on either texture,
tight enough that a wrong window or a wrong kernel scale breaks it.

**(d) What it deliberately does NOT assert: M13 §6.4's suggested `0.10 < φ < 0.18`.**

This is the one place a suggested spec item was refused, so here is the evidence.
Under pointwise normalisation φ is a near-linear function of texture contrast.
Sweeping the probe amplitude on the *same* operator, same window, same δ = 8 DN:

| texture amplitude (DN) | φ(w13, σ-normalised) |
| --- | --- |
| 30 | 0.0085 |
| 60 | 0.0228 |
| 120 | 0.0516 |
| 240 | 0.1036 |
| 480 | 0.1864 |
| 960 | 0.2959 |
| 1920 | 0.3987 |

**MEASURED** (temporary instrumentation of the same test helper; the table is
reproduced in a comment in `focus.rs` beside the assertion).

φ spans **47×** across a 64× amplitude range. Landing inside 0.10–0.18 requires
choosing an amplitude near 330 DN — i.e. tuning the *plant* until it happens to
match the one ROI M13 probed. That is pinning a property of an ROI, dressed as a
property of the operator, which is precisely the failure M13 §6.4 was warning
against. Asserting the bracket would have been a worse version of the sin it was
written to prevent.

Why φ moves like that, since it is worth knowing: the numerator's centre tap is
1/841-ish of a windowed *mean of gradients* and is scale-free in the texture,
but the divisor `σ(L(p))` responds to the level, not the contrast. Raising the
texture amplitude raises the perturbation's share of the local response without
raising the divisor proportionally.

**What is asserted instead**, so the test still bites:
- a loose sanity band, φ ∈ (0.005, 0.30), which catches a dead or saturated operator;
- **φ > 20 · φ_nonorm** — fact 39's claim that at this window the divisor dominates
  the centre tap, on the shipped code path;
- **φ(480 DN) > 2.5 · φ(120 DN)** — the texture dependence *itself* is now a
  regression test. If someone later replaces the divisor with something
  scale-free, this assertion fails and forces them to come and read this section.

---

## 4. Memory (requirement 5) — unchanged, and stated loudly

**`FocusField` still holds exactly three f32 planes and `allocated_bytes()` is
still `3 · pixels · 4`.**

Before: `focus`, `outer`, `scratch`. After: `focus`, `grad`, `scratch`. The ring
needed a second box mean; Tenengrad needs a gradient plane. Same count, same
lifetime, same allocation site.

Consequences, spelled out so nobody has to re-derive them:
- **M8's ratchet** (`peak = 14.4 MiB + live · 342.8 MiB + ⌈log2 chunks⌉ · 110.04 MiB`,
  SYNTHESIS §5) is **not invalidated**. No published memory figure moves.
- `crates/strehl-cli/src/stack.rs:353`'s `per_worker_bytes = px · (14 + 12 + 4) + frame_bytes`
  is **still correct**: the 12 is FocusField's three f32 planes. The comment there
  now names the operator so the next reader does not have to check.
- `WorkerPlan` and the chunking arithmetic were not touched.

**ARGUED, one open edge:** the *read extent* grew from support radius 3 to 14
(4.7×). Nothing in `crates/` currently tiles the focus computation spatially — it
runs whole-plane per worker — so there is no tile margin to widen today. If
spatial tiling ever lands, it must size its halo from `SUPPORT_RADIUS`, which is
why that constant is `pub` and documented rather than being an inline `1 + 13`.

---

## 5. Cost is flat in the radius (requirement 1, measured)

`cargo run --release --example focus-window-cost -p strehl-core`,
768×460 tile (0.353 Mpx, M13's tile size), 40 reps per timing, 9 interleaved
sweeps, per-radius minimum:

| radius | window | ms/frame/Mpx (min) | median |
| --- | --- | --- | --- |
| 0 | 1×1 | 1.8892 | 1.9232 |
| 1 | 3×3 | 3.3676 | 3.6608 |
| 5 | 11×11 | 3.3362 | 3.3600 |
| **13** | **27×27** | **3.3285** | 3.3932 |
| 20 | 41×41 | 3.3414 | 3.3711 |
| 30 | 61×61 | 3.3250 | 3.3609 |
| 40 | 81×81 | 3.3254 | 3.3396 |

**Spread over w1–w40: 1.28%**, argmin at w30. M13 §5 measured 2.53% with its own
harness on real RAW. w1 → w13, the move this milestone actually makes: **1.18%**.
`FocusField::compute`, the shipped path, timed in the same sweeps: **3.3658**,
within 1.1% of the w13 row, as it should be — it is the same work.

**MEASURED.** Three runs of the same command gave spreads of 1.53%, 0.80% and
1.28%; the argmin landed at w40, w30 and w30. **There is no trend in the radius,
only scatter.** Requirement 1 is satisfied: an 841-tap gather would have shown a
factor of tens here, not one percent.

Two methodological notes, because the first version of this measurement was
wrong and a verifier should know how:

1. **A single sweep cannot measure this.** One forward sweep read −0.7% across
   w1→w30 (cost apparently *falling* with radius); one reverse sweep of the same
   binary read +19% over the same rows. The machine drifts more across a sweep
   than the radius effect is worth. The example therefore runs 9 sweeps in
   alternating direction and reports the per-radius **minimum**, which is the
   right estimator because contention only ever adds time.
2. **`FocusField::compute` first read 21% slower than the identical inline loop**,
   purely because it was timed in a block appended after the sweeps, by which
   point the core had been at load for a minute. Interleaving it into the sweeps
   collapsed the gap to 1.1%. The 21% was an artefact of my harness, not of the
   struct. Worth recording: it is exactly the size of gap someone would
   confidently explain with a story about aliasing.

The w0 row is the operator without any box at all, and it is the useful control:
the entire box pass costs ~1.44 ms/frame/Mpx **and that figure does not change
between a 3×3 and an 81×81 window**. That is the running sum, visible directly.

---

## 6. Tests

`cargo test --workspace`: **70 passed, 0 failed** (18 cli + 44 core + 8 raw).
Baseline before this milestone was 67 (18 + 41 + 8).

**The delta is +3 in `strehl-core`, and it is a replacement not an addition**:
5 focus tests removed, 8 added.

| removed | added |
| --- | --- |
| `a_flat_plane_has_zero_focus_everywhere_including_the_border` | same name, kept, retargeted |
| `a_sharper_edge_scores_higher_than_a_blurred_one` | `resolved_texture_scores_higher_than_the_same_texture_blurred` |
| `normalisation_penalises_the_same_contrast_at_a_higher_signal_level` | same name, kept |
| `focus_is_finite_and_non_negative_at_zero_signal` | same name, kept |
| `centre_tap_fraction_is_the_value_m9_measured` | `centre_tap_fraction_and_read_extent_are_what_m13_specified` |
| | `the_running_sum_agrees_with_a_naive_gather_of_the_same_operator` (new) |
| | `tenengrad_elects_less_of_the_pixels_own_noise_than_the_ring_did` (new) |
| | `tenengrad_picks_the_correct_frame_far_more_often_than_the_ring_did` (new) |

### 6.1 The two head-to-head tests (project rule 11)

Both instantiate M11's two axes on synthetic plants where the truth is known,
both run the **retired ring operator on the same plant** as the comparison, and
both carry a **random-selector placebo**. The ring lives on in the test module
as a verbatim private copy for exactly this purpose; it is not reachable from
the library.

**Noise axis** — `tenengrad_elects_less_of_the_pixels_own_noise_than_the_ring_did`.
128×128, 22 frames, flat 2000 DN plant, SplitMix64 + Irwin–Hall(12) noise, N
computed as M11 computes it (sd of the argmax-merged plane ÷ sd of one frame):

| selector | N |
| --- | --- |
| tenengrad-w13 | **1.0388** |
| ring(1,3) | 1.1646 |
| random placebo | 0.9935 |

**MEASURED**, printed by the test. The placebo sits at ~1.0 as it must — picking
a frame at random cannot amplify noise — which is what makes the ring's 1.1646
readable as *selection* rather than as a property of the plant (rule 13: the
plant can express the failure, and the placebo shows it is not expressing it
spuriously). Ordering matches M11's real-data ordering; the magnitudes are
smaller because a synthetic flat field has no texture for either operator to
latch onto.

**Selectivity axis** — `tenengrad_picks_the_correct_frame_far_more_often_than_the_ring_did`.
96×96, 15 frames, truth = frame 7, frame k blurred by `box_mean` at radius |k−7|:

| selector | exact-hit rate |
| --- | --- |
| tenengrad-w13 | **1.0000** |
| ring(1,3) | 0.6985 |
| random placebo | 0.0640 (chance = 1/15 = 0.0667) |

**MEASURED**, printed by the test.

**A caveat that must travel with this second table:** the plant is
**fronto-parallel** — one blur level per frame, no depth edge anywhere. M13 fact
62 is explicit that fronto-parallel evidence may not be quoted about the window,
because the whole cost of a wide window is what it does at an occluding edge.
This test is evidence that the *operator* discriminates defocus; it is **not**
evidence about `WINDOW_RADIUS` and the comment in the code says so. The window
ruling rests on M13's 36 occluding-edge cells and on nothing in `crates/`.

### 6.2 The test that had to be rewritten, and why

`a_sharper_edge_scores_higher_than_a_blurred_one` presented a single monotone
step, sharp vs blurred. **That test cannot pass for this operator, and it is
right that it cannot.** Mean |∇| over a window wider than the blur is total
variation ÷ area, and blurring a monotone edge conserves total variation exactly.
A step is invisible to a windowed gradient mean. The replacement plants texture
with structure at multiple scales, where blurring genuinely destroys variation.

**DERIVED**, and the derivation is in the test's comment so the next person to
"fix" it reads the reason first.

### 6.3 The new equivalence test

`the_running_sum_agrees_with_a_naive_gather_of_the_same_operator` computes the
identical operator through an explicit `(2w+1)²` gather and pins the O(1) path
against it, borders included. `boxfilter.rs` already had its own version of this;
this one pins the *composed* operator, which is what actually ships.

### 6.4 On the speckle figure

The 34.381% → 1.010% drop in §0 is **MEASURED** on both ends (M2 §3.1 for the
old, §7.2 for the new) but it should not be read as "Tenengrad is 34× less
speckly than the ring, all else equal", because all else is not equal:
**the 27×27 window is itself a smooth.** SYNTHESIS fact 23 records that
regularising the *ring's* focus field with a 17×17 smooth drops speckle
34.4% → 0.868% and noise 1.253× → 1.075×. Tenengrad-w13 with no regulariser at
all reaches 1.010% and 1.068×. **ARGUED:** the operator's own window is doing
most of the work the regulariser was doing, on a wider footprint (27 vs 17). The
honest statement is that the two are not additive and nobody has measured them
together — which is the same gap SYNTHESIS open question 17 already names from
the other side. Do not quote a combined figure until someone measures one.

**And 1.068× is still above 1.0.** Fact 23's conclusion applies here unchanged:
a better-regularised selector is still a selector, and only averaging goes below
a single frame (0.534×). This milestone moved the argmax baseline from
"noticeably worse than one frame" to "slightly worse than one frame". It did not
change what kind of thing the baseline is.

---

## 7. Exact commands

All run from `projects/strehl` with `$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"`.

**7.1 baseline, before the change** (ring still in `focus.rs`):
```
cargo build --release
.\target\release\strehl.exe stack 'C:\dev\macro\test\109MSDCF' -o out\baseline-ring.tif --flat-roi 2272,1344,256,256
```
→ RATIO 1.253×, stacked σ 35.328 DN, single frame 11 σ 28.201 DN, 22 distinct
winners. (Reproduces M2's published 1.2527×.)

**7.2 after the change:**
```
cargo build --release
.\target\release\strehl.exe stack 'C:\dev\macro\test\109MSDCF' -o out\m14-tenengrad.tif --flat-roi 2272,1344,256,256
```
→ RATIO 1.068×, stacked σ 30.114 DN, single frame 11 σ 28.201 DN, 6 distinct
winners, index speckle 1.010%.

**7.3 gates:**
```
cargo fmt --all -- --check          # exit 0
cargo clippy --workspace --all-targets -- -D warnings   # exit 0
cargo test --workspace              # 18 + 44 + 8 = 70 passed, 0 failed
```

**7.4 the head-to-head numbers:**
```
cargo test -p strehl-core --lib -- focus --nocapture
```

**7.5 cost vs radius:**
```
cargo run --release --example focus-window-cost -p strehl-core
```

**7.6 the normalisation reproduction** (rule, so it can be rewritten in any
language): from `experiments/m11-focus-bakeoff/data/noise-109MSDCF.csv`, filter
`roi_kind == 'flat'` and `width == 1`; per `(stack, measure)` take the median
over the four ROIs of `merged_sigma / single_sigma`; then take the mean over the
two stacks. `ring-1-3` → 1.3475, `tenengrad-w5` → 1.1324.

**7.7 note on `out/`:** the two TIFFs are ~49 MB each and `out/` is gitignored.
They are outputs, not test data — the commands above regenerate them in about
two minutes each from the read-only corpus.

---

## 8. What did not survive contact with the code

Read this section first if you are verifying.

**8.1 "Tenengrad (Sobel gradient energy)" is the wrong name for what M11 measured.**
The literature's Tenengrad is the gradient *energy*, Gx² + Gy². The arm behind the
published N = 1.1324 is `Kind::Tenengrad { squared: false }` with `degree = 1`,
i.e. the gradient **magnitude** √(Gx² + Gy²). M11 scored the squared form
separately as `tenengrad-sq-w*`. Implementing the energy would have been faithful
to the name and unfaithful to the number. The magnitude is what shipped and the
module doc records why. **VERIFIED** by reading
`experiments/m11-focus-bakeoff/src/measures.rs` and by §0's exact reproduction of
M13's ratio, which would not have matched had the degree been wrong.

**8.2 M13 §6.4's suggested φ bracket `0.10 < φ < 0.18` is not assertable in a unit
test.** §3(d). It is satisfiable only by tuning the synthetic plant's contrast to
match the ROI M13 probed. The suggestion was offered as one of two options and
the other option — the analytic un-normalised anchor — is the one taken. Not a
defect in M13; a thing that only becomes visible when you try to write it down.

**8.3 A monotone step cannot test this operator.** §6.2. The pre-existing edge
test was not merely retargeted, it was *unpassable* in its old form for a windowed
gradient mean. Anyone porting the old test forward verbatim would have concluded
the implementation was broken.

**8.4 Fact 35's φ↔excess correlation does not order these two operators.**
ρ = +0.583 over M11's 36 operators, i.e. higher centre-tap fraction associates
with more merged-noise excess. But along the *window* axis φ and N move in
opposite directions: M13 §1.4 has φ rising from w3 to w17 while §1.1 has N falling
monotonically. So the correlation is a between-operator regularity, not a
within-family one, and it cannot be used to argue for a narrow window.
**ARGUED**, from M13's own tables; flagged rather than resolved, since it is a
SYNTHESIS-level question and SYNTHESIS is not mine to edit.

**8.5 Nothing in the brief's requirement 5 triggered.** The memory shape is
unchanged. Recorded here because "we checked and it did not move" is a result.

---

## 9. Numerical care (requirement 6)

Three separate questions, three separate answers.

**9.1 Does squaring in f32 lose anything at 15360 DN white?**
Max |component| after the 1/8 scale is (1 + 2 + 1)/8 × 15360 = **7424 DN/px**, so
Gx² + Gy² ≤ **1.10 × 10⁸**. That is past 2²⁴ ≈ 1.68 × 10⁷, so the sum is not
exactly representable — but the error is *relative*, bounded by 2⁻²³, and the
sqrt halves it. Worst case ≈ 7424 × 2⁻²⁴ ≈ **4 × 10⁻⁴ DN** on a magnitude of
thousands of DN. Three orders of magnitude below DN quantisation.
**DERIVED. f32 is fine for the pointwise gradient, and the code keeps f32 there
deliberately** — it is one plane of 8.2 M elements per worker and doubling it
would move a published memory figure for no measurable accuracy.

**9.2 Where the width actually matters: the accumulation.** Gradient magnitudes
are **non-negative and never cancel**, unlike the ring's signed differences. A
27-wide sliding sum of them reaches ~2.8 × 10⁵ on this corpus, and a row of 3516
pixels performs ~3516 add/subtract pairs against that running total. In f32 each
step rounds at ~2 × 10⁻² DN and the errors random-walk: √3516 × 2 × 10⁻² ≈ **1 DN**
of drift against a windowed mean of order 50 DN — **percent-level, and
systematically worse at the right-hand end of every row**. `box_mean`'s f64
accumulator absorbs it. **DERIVED. The f64 accumulator was load-bearing before
and is more so now; it must not be weakened.** A comment to that effect is now in
`boxfilter.rs` at the accumulator, replacing the one that described the ring.

**9.3 The divisor.** `max(σ, 1e-3)` is unchanged, including the constant. σ is
bounded below by read noise on any real frame, so the clamp only fires on
synthetic zero-signal input; there is a test (`focus_is_finite_and_non_negative_at_zero_signal`)
that pins it.

---

## 10. Files touched

| file | change |
| --- | --- |
| `crates/strehl-core/src/focus.rs` | rewritten: the operator, the three consts, 8 tests |
| `crates/strehl-core/examples/focus-window-cost.rs` | new: §5's measurement |
| `crates/strehl-core/src/boxfilter.rs` | doc comments only — module doc and the accumulator comment described the ring |
| `crates/strehl-cli/src/main.rs` | Stack subcommand help said "ring-difference" |
| `crates/strehl-cli/src/stack.rs` | module doc said "ring difference focus volume"; the per-worker budget comment now names the operator |

No public API was removed except `INNER_RADIUS` and `OUTER_RADIUS`, which described
the ring. **VERIFIED** that the `experiments/*` crates (separate workspaces, not
built by `cargo test --workspace`) mention `strehl_core::focus::*` only in doc
comments, so nothing there breaks.

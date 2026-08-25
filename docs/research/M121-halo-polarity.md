# M121 — halo polarity: is the halo a selection artifact?

Milestone M121. Read-only on `crates/`. Every number below has a script under
`experiments/M121-halo-polarity/` and an output under `C:\dev\strehl-out\M121\`.

Claims are labelled **MEASURED**, **DERIVED** or **ARGUED** throughout.

---

## The assignment

ORCH proposed a mechanism for the bright halo tracing every silhouette — the
"cut-out sticker" look that facts 1623–1626 make the lead visible defect:

> The halo is not an occlusion artifact. It is the selection decision spilling
> outward from an edge by the radius of the focus-measure window. A background
> pixel within one window radius of a strong edge has no focus information of
> its own; its windowed focus measure is dominated by the edge, so it elects
> the frame in which the edge is sharp. In that frame the object is compact and
> contaminates the pixel least, so the pixel takes a value pushed *away* from
> the object's brightness.

Two predictions:

- **P-WIDTH** — the halo's width is set by the focus-measure window radius.
- **P-POLARITY** — the rim's sign is `sign(surround − object)`. A dark object on
  a bright surround gets a bright rim; **a bright object on a dark surround must
  get a dark rim.** The halo always increases local edge contrast.

## Verdict in one paragraph

**P-WIDTH survives, and survives well.** **P-POLARITY is NOT CONFIRMED, and it
was not cleanly refuted either — because on the available data the decisive
class does not exist.** The one edge class that carries a spatially bounded rim
shows the polarity ORCH observed. The opposite-polarity class was never validly
sampled: on `bee-3-cpl` almost none of its edges straddle a depth discontinuity,
and on `tweezers-cpl` the apparent signal fails two independent shape tests and
appears at a third of its amplitude in a single unmerged frame. ORCH's mechanism
is **not dead**, but the test it was built to survive has not yet been run. What
*is* now settled is that the halo is a **merge artifact with the merge's own
length scale**, which is more than the project had before.

---

## E1 — the window radius, from the shipped source

**MEASURED (by reading the source).**

| constant | value | file:line | role |
| --- | --- | --- | --- |
| `SOBEL_RADIUS` | 1 | `crates/strehl-core/src/focus.rs:108` | gradient kernel half-width |
| `WINDOW_RADIUS` | **13** | `crates/strehl-core/src/focus.rs:83` | box mean of gradient magnitude, a 27×27 box |
| `FINE_WINDOW_RADIUS` | 2 | `crates/strehl-core/src/focus.rs:105` | statistics field, **not** selection |
| `SUPPORT_RADIUS` | 14 | `crates/strehl-core/src/focus.rs:117` | |
| `REGULARISER_RADIUS` | 8 | `crates/strehl-core/src/merge.rs:93` | applied to the field *before* the argmax |
| `DEFAULT_GATE` | 4.0 | `crates/strehl-core/src/merge.rs:299` | the shipped gate |

The selection is a per-pixel argmax over the **regularised** field
(`merge.rs:852`, `FocusStats::fold`). It is **fixed, not adaptive**: all 30
references to `WINDOW_RADIUS` in `crates/strehl-core/src/` are constant
expressions, and none scales it with blur, depth, or content.

**DERIVED.** The furthest a single pixel's intensity can influence another
pixel's election is `SOBEL_RADIUS + WINDOW_RADIUS + REGULARISER_RADIUS =
1 + 13 + 8 = 22` plane pixels, with a trapezoidal (box⊗box) falloff, so the
response is near-flat to ~5 px and decays to zero at 22 px. **P-WIDTH therefore
predicts a rim whose half-power width is of order 13 px and which is over by
22 px.** Anything at 40 px, or at 3 px, refutes it.

**The codebase already agrees, and this was found rather than assumed.**
`crates/strehl-core/src/through_focus.rs:1145` computes exactly this chain for
its own test margin:

```rust
let margin =
    SOBEL_RADIUS + 1 + crate::focus::WINDOW_RADIUS + crate::merge::REGULARISER_RADIUS;
```

— "the widest any of them needs (Sobel + selection window + regulariser)", i.e.
23 px with its one-pixel safety margin. **The derivation above is not this
milestone's invention; it is a length scale the merge's own tests already
depend on.**

---

## The instrument, and what it cost to build

`experiments/M121-halo-polarity/halo_lib.py`, driven by a single `scan()` in
`runner.py` that **E2 and every control share**. Perpendicular profiles are
taken across detected step edges, oriented so luma increases with distance,
normalised by the edge amplitude `A = hi − lo`, and decomposed:

```
bright(d) = (p(+d) − hi)/A        dark(d) = (lo − p(−d))/A          d ≥ 0
S(d) = bright − dark              ADDITIVE   (both sides lifted)
C(d) = bright + dark              CONTRAST   (both pushed outward)
```

A symmetric edge transition is antisymmetric about the centre, so it **cancels
exactly in `S`** and doubles in `C`. `bright`, `dark` and `C` are read beyond a
transition exclusion `d0 = 1.6 × rise_p90`; `S` needs none.

**The headline reads `bright` and `dark` separately, not `S`/`C`.** The rim lives
in the *surround*, which is the flat side; requiring both plateaus clean throws
away most of exactly the edges the rim lives at (pair yield saturates at ~79,
per-side yield is 4–5× that — `yield_probe.py`).

**Three real defects were caught in the instrument before a single real pixel was
scored**, all by the plant (§ N3):

1. `peak_in_near` was a plain `argmax`, which structurally cannot return a
   negative number, so an additive-glow plant's dark side read `+0.001` instead
   of `−0.030`.
2. The edge transition swamped the raw per-side statistics: an artifact-free
   edge read as strongly contrast-*reducing*. This is what forced the `S`/`C`
   decomposition and the exclusion zone.
3. The bootstrap band was a fixed ±4 px window that straddled the rim's outer
   cutoff and under-read a 13 px plant by 35 %.

---

## E4 — controls. These come first, because without them nothing else counts.

### N3 — the positive control (a plant), run as a ladder

`n3_plant.py` → `C:\dev\strehl-out\M121\n3-plant.json`. **MEASURED.**

Synthetic edges at blur 1.5/2.0/2.5/3.0/4.0 × angle 0°/27°, with planted rims of
known amplitude (0.030 per side) and known width (13 px and 26 px).

| plant | expected | measured (blur 1.5, 0°) |
| --- | --- | --- |
| null | `S ≈ 0, C ≈ 0` | `S = +0.0002`, `C = −0.00002` |
| contrast, 13 px | `C ≈ +0.060`, `w50 ≈ 13` | `C = +0.0590`, `w50 = 13.25` |
| additive, 13 px | `S ≈ +0.060`, `w50 ≈ 13` | `S = +0.0578`, `w50 = 13.25` |
| contrast, 26 px | `C ≈ +0.060`, `w50 ≈ 26` | `C = +0.0597`, `w50 = 26.25` |

Per-side gates (the ones the headline actually uses) also pass: a contrast plant
reads `bright ≈ +0.030` **and** `dark ≈ +0.030`; an additive plant reads
`bright ≈ +0.030` and `dark ≈ −0.030`. Crosstalk ≤ 0.008.

**N3 FIRED. The instrument moves, it recovers both amplitude and width, and it
distinguishes an additive glow from a contrast rim.**

**Its limit, mapped rather than assumed (MEASURED):** the gates hold for a 10–90
edge rise ≤ **6.50 px**. At rise ≈ 10 px, `C` reads `+0.002` for a plant that is
certainly present — the transition exclusion has swallowed the rim. **E2 reads
this envelope out of `n3-plant.json` at runtime and hard-exits if N3 has not been
run**, so the analysis cannot drift away from its commissioning.

### N1 — no merge

`e4_controls.py`. **MEASURED.** The identical pipeline on the five single input
frames, on their own edges, pooled (no single frame yields enough edges, and
quoting the luckiest one would be the cherry-pick this control exists to stop).

| | n | rim | 95 % CI | SE |
| --- | --- | --- | --- | --- |
| N1 pooled, dark-object class | 57 | **+0.0023** | [+0.0012, +0.0033] | 0.0159 |
| merged, same class | 70 | **+0.0634** | [+0.0533, +0.0754] | — |

**The merged rim is 28× the no-merge floor.** N1 passes. The floor is not zero,
and is reported with its CI per rule 39.

**N1b (mean of the five frames) could not be measured**: the mean is blurry
everywhere, every edge falls outside the commissioned envelope, n = 0. That is a
gap, not a pass — it is stated here rather than quietly dropped.

### N2 — soft edges, run as a ladder rather than one bin

**MEASURED.** Rim vs the edge's own 10–90 rise, each bin read beyond its own
transition exclusion.

| rise bin (px) | n | rim | 95 % CI | envelope |
| --- | --- | --- | --- | --- |
| 1.0–4.0 | 41 | **+0.0952** | [+0.0888, +0.0991] | inside |
| 9.0–12.0 | 9 | −0.0376 | [−0.0487, +0.0176] | outside |
| 12.0–16.0 | 30 | **−0.0348** | [−0.0388, −0.0252] | outside |

**The rim is a property of sharp edges and disappears as the edge softens**,
which is what the mechanism predicts: a soft edge has no sharp frame to elect.
**Caveat, stated in the script itself:** the exclusion `d0 = 1.6 × rise` grows
with rise, so the read band shrinks and the soft bins are read at 25–28 px. A
null there is weak evidence, and the negative values are more likely the profile
not having settled than a real inverted rim.

### N4 — flat ROI (AGENTS.md rule 9). **This one fired, and it changed the analysis.**

**MEASURED.** 400 forced profiles at random positions and random orientations in
featureless background. First run: **113 accepted, reading `bright = −0.299`,
`dark = −0.336`.** Not zero. With no step present, `A` is noise, the recentring
locks onto the largest noise gradient, and every statistic is divided by it.

`amp_probe.py` then measured the two amplitude distributions:

| | n | amplitude |
| --- | --- | --- |
| real accepted edges | 58 | min **2879 DN** |
| flat-ROI noise steps | 113 | max **1052 DN**, p99 922 |
| flat-ROI, all five single frames | — | p99 ≤ 1936 DN |

A floor of **`A ≥ 2000 DN`** sits in the gap. It was chosen from the probe
**before any verdict was read**, and applied uniformly to E2, every control, and
the N3 plants. After it: **0 of 334 forced flat-ROI profiles are accepted.**

Two things are worth noting rather than hiding. First, the bias N4 exposed is
**negative**, and the measured rim is **positive**, so it could not have
manufactured the headline. Second, N4 now passes *because* of a filter added in
response to it; the filter is a hard threshold on a quantity with a clean 2.7×
separation, not a tuned parameter.

### Saturation — a fourth defect, found on the second subject

**MEASURED.** `tweezers-cpl` reaches the 16-bit ceiling. A clipped plateau is not
a plateau, and the first tweezers run read `+1.47` for one class — twenty times
the edge amplitude, which is nonsense. `scan()` now rejects any profile with a
plateau at or above 0.995 × 65535, or with more than 2 % of its samples there.
(On this subject only 0.002 % of pixels are at the ceiling, so this was *not* the
cause of that particular reading — see the tweezers section — but the check
belongs in the instrument regardless.)

---

## N5 — the PIL narrowing, planted rather than assumed

ORCH's fleet correction (2026-08-24) gives two triage questions: *is my
statistic absolute?* and *does it divide a small quantity by a large one?* My
answers are **no** and **yes**. The rim is `(p(+d) − hi)/A` with `A = hi − lo`:
a small overshoot over a large amplitude, both drawn from the same pixels of the
same read. Dimensionlessness protects it against the first hazard. The second is
the one ORCH flags as compressing *toward a clean null* — "the hardest error
here to catch, because nobody re-examines an arm that showed no effect."

**M121 reports a clean null.** Row two of the headline is `+0.0009` at 50 %
positive. That is precisely the arm nobody would re-examine, so it is re-examined
here.

**The mechanical answer is NOT EXPOSED, and it is checkable rather than
asserted.** Every pixel read in this milestone goes through `m121_io.load_u16`
(`tifffile.imread` + an immediate `assert dtype == np.uint16`) or through one of
two index-map readers that carry the same assert (`e2d_tweezers.py:62`,
`e3_election.py:124`). The index assert matters independently of this notice:
`bee-3-cpl` has **299 frames**, so a uint8 index map would wrap silently. There
is no `Image.open` anywhere in the milestone; the only uses of the `Image`
symbol are `Image.fromarray(...).save(...)` in three preview writers
(`e0b_look.py:33`, `e0c_crops.py:46`, `e2e_shape.py:78`).

But "my reader was correct" is a claim about code. `n5_quant.py` measures the
consequence instead.

**Fact 1615 reproduced live (MEASURED).** A genuine uint16 RGB TIFF written from
the shipped arm reads back through `tifffile` byte-exact and through
`np.asarray(Image.open(p))` as **uint8**: **18202 distinct levels → 80, a 227.5×
loss.** ORCH's occupied-range refinement is confirmed on independent data — the
crop occupies 20247 DN of the 65535 available, and it is that occupied span, not
the full range, that sets the survivors.

**The plant was commissioned before it was used.** A modelled defect that was
never checked against the real defect is worth nothing, so `commission_model()`
tries three candidate narrowings and requires one to be **byte-identical to
PIL's own output over all 786,432 samples**, hard-erroring otherwise. `shift8`
matched exactly. What follows therefore plants the real defect.

**Result — the headline and the null both hold (MEASURED).** The counterfactual
re-runs the entire headline on the narrowed arm with the headline's own
settings, which is what an agent who had used PIL throughout would have
reported. It reproduces the published clean numbers exactly, which validates the
path:

| row | clean | narrowed | shift | n |
|---|---|---|---|---|
| dark obj / bright surround (**headline**) | +0.0634 | +0.0619 | **−0.0015 (−2.4 %)** | 70/69 |
| bright obj / dark surround (**the null**) | +0.0009 | −0.0016 | −0.0025 | 18/19 |
| undecided, bright side | +0.0512 | +0.0515 | +0.0003 | 57/57 |
| undecided, dark side | +0.2398 | +0.1654 | **−0.0744 (−31 %)** | 38/37 |

The headline moves 2.4 % and keeps its sign, its width and its significance. The
null stays a null, and the shift is far inside its own CI of
[−0.0141, +0.0289]. **Neither verdict in this report is a quantisation
artifact.**

**The fourth row is the interesting one, and it refuted my first explanation.**
I predicted from ORCH's occupied-range rule that the row which moved most would
be the one on the lowest-amplitude edges. **Measured, it is the opposite:**
`undecided_dark_side` has the *highest* median amplitude of the four classes
(10260 DN, ~40 levels surviving) and still moved −31 %.

The real route is visible because the same class was measured twice under
different conditions:

| same class, same data, same defect | rim shift |
|---|---|
| matched edges, read band **pinned** (`d ≥ 8.92` both arms) | +0.2483 → +0.2492, **+0.4 %** |
| **free** re-detection, band recomputed | +0.2398 → +0.1654, **−31 %** |

**DERIVED: the narrowing damages a normalised statistic mainly through
re-detection and band placement, not through the pixel value.** Held at fixed
positions the statistic barely moves; allowed to re-detect edges and recompute
its transition-exclusion band on the narrowed data, the same statistic on the
same class moves two orders of magnitude more. This is a sharper triage question
than "is it a ratio": **does anything about where I measure get decided from the
narrowed pixels?** A milestone that scored at fixed coordinates is far less
exposed than one that found its own features.

It also explains why the headline survived. The headline's edge set is pinned by
`MIN_AMPLITUDE = 2000 DN` and by the commissioned rise envelope — a gate
introduced for an entirely unrelated reason (the N4 flat-ROI failure) — and that
gate is what keeps its detection stable under narrowing.

---

## N6 — a narrowing ladder, and where a first-moment statistic actually breaks

ORCH's correction #2 replaces the triage with *"does the statistic read pixel
**value**, or feature **position**?"* — location immune, dispersion destroyed,
with the immunity bounded at **~12 distinct levels per fitted window**.

**That dichotomy does not contain M121's statistic.** The rim is

```
rim = mean_band( p(+d) − hi ) / (hi − lo)
```

Every term is a **first moment** — a mean, or a difference of means. It reads
pixel value, so the new rule sorts it with the vulnerable half; but it is not a
dispersion statistic, so the stated mechanism for that vulnerability (absorbing
the quantisation variance) does not apply. There are three classes, not two:

1. **Location** — immune; error is zero-mean and uncorrelated with sub-pixel position.
2. **First moment** — *also* largely immune, for a different reason: the error is
   zero-mean and **averages down over the samples in the estimate**.
3. **Dispersion** — destroyed; the estimate *is* the variance quantisation adds to.

`n6_ladder.py` runs the full headline at eight narrowing rungs. **MEASURED:**

| bits | levels/edge amplitude | levels/rim signal | headline | retained | n |
|---|---|---|---|---|---|
| 0 | 6753.7 | 428.20 | +0.0634 | 100.0 % | 70 |
| 4 | 422.5 | 26.68 | +0.0632 | 99.6 % | 70 |
| 6 | 105.6 | 7.39 | +0.0700 | 110.4 % | 69 |
| **8 (the PIL defect)** | **26.3** | **1.63** | **+0.0619** | **97.7 %** | 69 |
| 9 | 13.1 | 0.72 | +0.0555 | 87.5 % | 73 |
| 10 | 6.5 | 0.60 | +0.0926 | **146.0 %** | 57 |
| 11 | 3.2 | 0.07 | +0.0232 | 36.6 % | 62 |
| 12 | 2.0 | 0.00 | +0.0000 | 0.0 % | 106 |

**ORCH's 12-level bound is CONFIRMED on a completely different statistic class** —
the break falls between 13.1 and 6.5 levels, straddling 12 almost exactly.

**But the scope in ORCH's rule is wrong for a ratio statistic.** At the PIL
defect the *signal* holds **1.63 levels**, seven times below the bound, and the
statistic still retains 97.7 %. What predicts the break is levels across the
**normalising denominator** — the edge amplitude — not levels across the
quantity being measured. For any statistic of the form *small ÷ large*,
**count the levels in the large one.** Counting the signal would have condemned
this measurement by a factor of seven.

**"Watch the sample count, not just the result" is directly validated.** The
first bad value is bits = 10 at 146 % — a plausible-looking 46 % over-read. Its
only warning is that **n drops 69 → 57**. Past that the failure stops being
quiet: the rim collapses to an exact `+0.0000` and n jumps to a nonsensical 106.
So on this estimator the dangerous rung is a single one, and the sample count is
its leading indicator.

---

## N7 — sweeping the support floor, which falsified a claim I had already made

ORCH: *"a support floor is a real defence… the protection is graded — watch the
sample count."* M121 has one, `MIN_AMPLITUDE = 2000 DN`, chosen from
`amp_probe.py` before any verdict was read — but chosen at one value and
**never swept**. `n7_floor.py` sweeps it. **MEASURED:**

| floor (DN) | headline | n | null | n |
|---|---|---|---|---|
| 0 | +0.0634 | 70 | +0.0009 | 18 |
| 500 | +0.0634 | 70 | +0.0009 | 18 |
| 1000 | +0.0634 | 70 | +0.0009 | 18 |
| 1500 | +0.0634 | 70 | +0.0009 | 18 |
| **2000 (shipped)** | **+0.0634** | **70** | **+0.0009** | **18** |
| 3000 | +0.0631 | 69 | +0.0009 | 18 |
| 4000 | +0.0565 | 69 | +0.0044 | 17 |
| 6000 | +0.0547 | 48 | +0.0052 | 15 |

Two things follow, and the second is a retraction.

**Good news: the headline does not depend on the threshold.** It is *identical*
across 0 → 2000 DN and varies by 13.7 % across the entire sweep including
settings that discard a third of the sample. The verdict is not an artifact of
where I put the floor.

**Retraction (this corrects what I sent ORCH after N5).** I claimed the floor
was what kept the headline's detection stable under narrowing. **That is false
and this sweep falsifies it.** `n` is pinned at 70 from 0 DN to 2000 DN — the
floor excludes **nothing** from the headline class, so it cannot be protecting
it. All 70 headline edges already sit above 2879 DN, as `amp_probe.py` said.
What actually protects the headline is that silhouette edges are *intrinsically*
high-amplitude (median 6754 DN), which keeps them far from N6's ~13-level cliff.
The floor's real and separate job is killing the flat-ROI false positives that
N4 caught — a different sample, where it took 113 → 0. Both statements are true;
I had merged them into one that was not.

**Saturation audit of my own controls (ORCH's new tell).** N2's rise ladder
`n = [41, 2, 5, 9, 30]` varies; `e2b`'s depth split varies; N7 varies
(70 → 48); N4's own sampling varied 113 → 0. **One block does read pinned:**
N3's `a0` rungs hold `n = 93` across every blur setting. That is *not* the
damaging kind — the swept parameter there is the plant's blur, not an exclusion
threshold, so a stable edge set is the intended matched design, and the ladder's
verdict does vary across it (pass → fail at blur 3). Checked rather than
assumed.

---

## N8 — `D`, and why it over-predicts this statistic

ORCH's addendum retires *"it's a ratio, so it cancels"* and asks for
`D = max/min` of the terms alongside any cancellation claim. Two things need
saying, and only the first is what was asked.

### The `D` values for every two-arm claim M121 makes

**MEASURED** (`n8_dstat.py`). "Margin after" applies ORCH's predicted shift in
the direction that *shrinks* the separation:

| claim | strong | weak | `D` | ORCH predicts | separation after |
|---|---|---|---|---|---|
| headline rim vs bright-object null | 0.0634 | 0.0009 | 70.4 | 8.0 % | 64.8× |
| N1 merged rim vs single-frame rim | 0.0634 | 0.0023 | 27.6 | 8.0 % | 25.3× |
| tweezers merged vs its own single frame | 0.1326 | 0.0474 | 2.8 | 6.2 % | 2.6× |
| N2 sharp-bin rim vs soft-bin rim | 0.0952 | 0.0348 | 2.7 | 6.2 % | 2.6× |
| **E3 election spill vs flat-bg control** | 10.50 | 6.67 | **1.6** | 3.8 % | **1.5×** |
| gate 4 vs gate 0 headline rim | 0.0658 | 0.0634 | 1.0 | 0.7 % | 1.0× |

ORCH is right that a defect contrast is lopsided by construction — the top two
rows are `D` = 70 and `D` = 28. But **no conclusion in this report turns over at
the predicted shift**, because those same rows carry 25–65× margins.

Two rows deserve comment. **The gate-4/gate-0 row is an *equality* claim** and
sits at `D` = 1.0, the most protected bin — the one place cancellation genuinely
does the work, and conveniently the one claim that needs it. **E3 is the thinnest
claim in the milestone**, 1.6 → 1.5× after the predicted shift; `D` independently
picks out the result I had already flagged as corroborative rather than decisive.
That agreement is the best evidence I have that the `D` framework is measuring
something real.

### Why `D` over-predicts the headline itself

The headline is **not** a two-arm ratio — it is a small first moment over a large
one, both from the same arm, with no second arm to cancel against. Taken
literally its terms give `D` between **5.2** (per-edge band median) and **15.8**
(pooled rim), landing in ORCH's `[5,8)` or `[8,∞)` bins, predicting **7.6–8.0 %**.

**N6 measured 2.4 %.**

The reason is that `D` models **cancellation**, and cancellation is not what
protects this statistic. **Averaging is.** MEASURED:

| quantity | value |
|---|---|
| per-edge rim, n | 70 |
| per-edge sd | 0.0789 |
| √n | 8.37× |
| a fully **independent** per-edge error of 8.04 % pools to | **0.96 %** |
| a fully **correlated** one stays at | **8.04 %** |
| **measured pooled shift (N6)** | **2.4 %** — 20 % of the way up |

So the per-edge quantisation error is largely, though not perfectly,
independent, and **averaging removes about 80 % of the damage `D` predicts.**
The 1/√N scaling is confirmed directly by bootstrap (with replacement — drawing
*without* replacement applies a finite-population correction that forces the
spread to exactly zero at `k = n` and flatters the result; my first version of
this ladder had that bug):

| n | 5 | 10 | 20 | 35 | 50 | 70 |
|---|---|---|---|---|---|---|
| sd(estimate) | 0.0279 | 0.0181 | 0.0118 | 0.0088 | 0.0069 | 0.0061 |
| ratio to sd/√n | 0.79 | 0.73 | 0.67 | 0.66 | 0.62 | **0.64** |

**The ratio is flat from n = 20 onward**, which is what 1/√N scaling looks like.

**DERIVED — there are three protection mechanisms, not one:**

| mechanism | governed by | applies to |
|---|---|---|
| **Cancellation** | `D` = max/min of terms | two-arm contrasts |
| **Position-insensitivity** | levels per fitted window (~12) | location statistics |
| **Averaging** | **sample count N** | first moments over many samples |

`D` is necessary but not sufficient: it correctly says M121's headline gets *no
cancellation protection*, and it is right — the protection comes from somewhere
else entirely. **A statistic can be deep in the unprotected regime on `D` and
still be robust, if N is large.** Report `D` *and* N.

### Input provenance (ORCH's ten-minute check)

*"A clean reader on a file that was already narrowed upstream is still a
narrowed measurement."* MEASURED (`prov_audit.py`) — all twelve inputs M121
reads are `uint16` at 16 bits per sample, with 11695–32156 distinct levels. The
strongest evidence is not the dtype but the reproduction: **the M93 gate-4 arm
is byte-identical (sha256 `e6132cd07b1348c4…`) to M121's own re-render from the
raw frames**, so it provably was not narrowed anywhere upstream.

`Image.open(` call sites in M121: **zero**. (The `PIL`-vs-`compiling` false
positive ORCH warns about cannot arise here for that reason, but the check was
run.)

**My own audit produced a false positive, which is the evening's lesson again.**
The heuristic "≤ 256 distinct levels means narrowed" flagged
`tweezers/index.tif` — which has exactly **100** levels because that stack has
exactly **100 frames**, numbered 0–99. It is complete, not narrowed. bee-3's
index map has 299 levels for 299 frames and passes the same test. **A level
count is only interpretable against what the file is supposed to contain**, and
my detector, like the original grep, went out without a negative control.

---

## Provenance (discipline 830)

Every arm was identified against the `strehl stack` log beside it, not from its
filename.

| file | what it actually is |
| --- | --- |
| `armM4-gate4-binlin.tif` | **the shipped path.** 299 frames of `bee-3-cpl`, `--gate 4.0`, alignment OFF, 3516×2344, sha256 `e6132cd07b1348c4…` |
| `armM-gate0-binlin.tif` | gate 0 — a **NEGATIVE CONTROL** (`merge.rs:3299`, `merge.rs:3341`: "gate 0 is the same [selector]… it must admit exactly the winner"), sha256 `895e458dd8f4722d…` |
| `armF-f{143,158,173,193,208}.tif` | single frames at identical geometry |

**M96's `elected-index.tif` is uint8 RGB — a colour-mapped preview, not raw
indices — and cannot be used for E3.** M111's `best_index.npy` dumps are
`dry-erase-marker-head-cpl` with alignment ON: wrong subject, wrong geometry.

So E3 re-rendered the subject:

```
STREHL_ALIGN=0 STREHL_WARPMAP=C:\dev\strehl-out\M121\e3\warpmap-scratch \
  cargo run --release -q -p strehl-cli -- stack D:\personal\macro\bee-3-cpl \
  --gate 4.0 -o C:\dev\strehl-out\M121\e3\armM4-repro.tif \
  --index-map C:\dev\strehl-out\M121\e3\index.tif
```

**The merged TIFF this produced is byte-identical to the shipped arm**
(sha256 `e6132cd07b1348c4…` both). The index map beside it is therefore the
shipped path's *own* election, not an approximation of it. `e3_election.py`
re-checks this hash at runtime and refuses to proceed if it ever stops matching.

All TIFFs are read with `tifffile` and asserted `uint16` on the following line
(fact 1615, discipline 828).

---

## E2 — the headline

`e2_polarity.py` → `C:\dev\strehl-out\M121\e2-polarity.json`. **MEASURED.**
Shipped gate-4 arm, edges inside the commissioned envelope (rise ≤ 6.50 px),
`A ≥ 2000 DN`. Rim is the value in the **surround**, read beyond
`d0 = 7.40 px`, in units of the edge amplitude. Positive = pushed *away* from
the object's brightness = contrast-enhancing.

### The sign table

| arm | edge polarity | n | rim in surround | 95 % CI | % +ve | w50 | cutoff |
| --- | --- | --- | --- | --- | --- | --- | --- |
| shipped, gate 4 | **dark obj / bright surround** | 70 | **+0.0634** | [+0.0533, +0.0754] | 93 % | 10.00 | 13.25 |
| shipped, gate 4 | **bright obj / dark surround** | 18 | **+0.0009** | [−0.0141, +0.0289] | 50 % | 27.00 | 28.50 |
| gate 0 (control) | dark obj / bright surround | 45 | +0.0658 | [+0.0343, +0.0906] | 96 % | 13.25 | 14.75 |
| gate 0 (control) | bright obj / dark surround | 14 | +0.0011 | [−0.0129, +0.0149] | 50 % | 28.00 | 30.00 |

Row one is the halo ORCH looked at: **a bright object-facing rim on the bright
surround, 93 % of edges, 28× the no-merge floor.**

Row two is not the opposite sign. It is **nothing at all**, and its CI is tight
enough (±0.02) to exclude both `+0.0634` (a contrast rim) and `−0.0634` (an
additive glow).

Gate 0 reads the same as gate 4 on both rows, consistent with fact 1625 — **the
gate does not touch the halo.** This is a sharper statement than it first looks.
`merge.rs:3341` establishes that **gate 0 admits exactly the winner and nothing
else**: it is the pure winner-take-all limit of the merge, with no noise-gated
averaging at all. The halo is unchanged between the pure-selection limit and the
shipped estimator, which is what a selection artifact — and only a selection
artifact — should do.

### Does the rim end?

`e2e_shape.py` → `e2e-shape.json`. **MEASURED.** Mean value by distance band:

| | 1.5–6 | 6–12 | 12–18 | 18–24 | 24–30 px |
| --- | --- | --- | --- | --- | --- |
| bee-3, dark obj / bright surround (n=70) | +0.2735 | +0.1911 | **−0.0036** | −0.0431 | −0.0240 |

**The rim is over by 12 px and slightly negative after.** It is a bounded rim,
not a gradient. This is the single most convincing piece of evidence in the
milestone, and it is a *shape*, not a p-value.

### The rim grows with depth discontinuity

`e2b_law.py`. **MEASURED.** Restricting to edges whose two sides elect frames
further apart:

| depth split | dark-object class | rim |
| --- | --- | --- |
| all | n = 70 | +0.0634 [+0.0533, +0.0754] |
| ≥ 1 frame | n = 66 | +0.0612 [+0.0532, +0.0736] |
| ≥ 2 frames | n = 34 | **+0.0817** [+0.0715, +0.1195] |

**ARGUED:** the rim being *larger* at edges that straddle a real depth step is
what a selection artifact should do and is hard to explain as an edge-rendering
effect.

---

## Why P-POLARITY is not decided

Row two of the sign table is the killer test, and **it was run on a sample that
cannot answer it.**

**MEASURED (`e2b_law.py`).** Of the 18 bright-object edges on `bee-3-cpl`, only
**5** straddle a depth discontinuity of even one frame. On a bee, "bright thing
on a dark background" is almost always a pale hair lying *on* the dark body —
same depth, no occlusion, no defocus discontinuity. **Under every mechanism,
including ORCH's, such an edge should show nothing.** Row two's null is therefore
consistent with the mechanism, consistent with its negation, and diagnostic of
neither.

Fact 1632 records that every one of ORCH's six errors tonight was in the setup —
what was compared to what. **Reporting row two as a refutation would be the
seventh.**

### The out-of-sample test, and why it does not rescue the situation

**MEASURED.** Fitting each candidate law to row one and predicting row two:

| law | predicted row two | observed | verdict |
| --- | --- | --- | --- |
| CONTRAST (rim ∝ `A`, ORCH's) | +0.0634 | +0.0009 [−0.0141, +0.0289] | rejected |
| ADDITIVE (rim = constant DN) | −0.0634 | +0.0009 | rejected |
| MULTIPLICATIVE (surround × (1+g)) | −0.0110 | +0.0009 | survives |

A multiplicative law — a few per cent of gain applied to the surround near an
edge — reproduces both rows, because a few per cent of a *dark* surround is
almost nothing. It was not in the brief; it came out of the measurement.

**But it does not survive its own in-sample test.** `e2c_level.py` uses the fact
that `hi` varies 1.8× and `A` varies 4.2× across the 70 dark-object edges, with
`corr(A, hi) = −0.39` — separable — and asks which normalisation is flat:

| law | coefficient of variation | 95 % CI |
| --- | --- | --- |
| CONTRAST (`rim/A`) | 0.811 | [0.587, 1.022] |
| ADDITIVE (`rim_DN`) | 0.948 | [0.680, 1.191] |
| MULTIPLICATIVE (`rim/hi`) | 1.270 | [0.714, 1.603] |

Regressions through the origin give `R² ≈ 0` for **all three** predictors
(`hi`: −0.047; `A`: +0.017; constant: 0.000). **The CIs overlap completely. This
test is underpowered and separates nothing.** Edge-to-edge scatter swamps the
between-law difference. Reported here because a null from a test that was set up
to discriminate is a result; if it is ever repeated on more edges it may decide
the question.

### The second subject, and why it did not deliver either

To get the missing class, this milestone rendered `tweezers-cpl` — bright metal
on a dark, deeply defocused ground — at the shipped settings with an index map
(`e2d_tweezers.py`; invocations recorded in `C:\dev\strehl-out\M121\tweezers\`).
The object side was decided from the **index map** (real elected depth), a
classifier that agrees with bee-3's five-frame classifier **81.7 %** of the time.

First reading: bright object / dark surround, **n = 96, rim = +0.1326
[+0.1284, +0.1395], 100 % of edges positive.** A dark rim on a bright object —
exactly P-POLARITY's killer prediction.

**It does not hold up, and two independent checks say so.**

| | 1.5–6 | 6–12 | 12–18 | 18–24 | 24–30 px |
| --- | --- | --- | --- | --- | --- |
| tweezers merged (n=96) | +0.0979 | +0.1343 | +0.1326 | +0.0884 | +0.0322 |
| tweezers, **single unmerged frame** (n=13) | −0.0120 | +0.0521 | +0.0431 | +0.0342 | +0.0194 |

1. **It does not end.** It is still strongly positive at 18–24 px and its `w50`
   is 22.75 px with a cutoff of 28.25 px — the edge of the measurement range.
   That is the signature of a slow background gradient (bokeh falloff around a
   bright object), which also means the "plateau" at 30–45 px used to normalise
   it is not flat.
2. **N1 shows the same shape at a third of the amplitude.** A single frame with
   no merge in its history reproduces the profile. On bee-3 the merged rim beats
   its N1 floor 28×; here it is 2.8×, on n = 13.

**So the tweezers result is rejected as evidence, by this milestone, against its
own hypothesis's interest.** The bright-object class remains untested.

---

## E3 — the elected-index read

`e3_election.py` → `e3-election.json`. **MEASURED**, on the byte-identical index
map. Walking outward along the edge normal, fraction of pixels electing the same
frame as the edge (±1 frame):

| d (px) | 0 | 4 | 8 | 10 | 12 | 14 | 18 | 22 | 26 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| agrees with edge | 1.000 | 0.810 | 0.759 | 0.552 | 0.397 | 0.241 | 0.138 | 0.069 | 0.052 |
| flat-background control | 1.000 | 0.670 | 0.415 | 0.348 | 0.243 | 0.200 | 0.100 | 0.063 | 0.058 |

| quantity | value |
| --- | --- |
| agreement half-width along the normal | **10.50 px** |
| agreement 10 % width | **21.10 px** |
| flat-background control half-width | 6.67 px |
| flat-background control 10 % width | 18.00 px |
| `focus.rs:83 WINDOW_RADIUS` | **13 px** |
| DERIVED total spill | **22 px** |
| E2's measured rim `w50` / cutoff | **10.00 / 13.25 px** |

**The election holds a plateau out to ~8 px, breaks between 10 and 14, and is at
the floor by 22.** That is the shape a fixed box window produces, and the
half-width (10.50 px) matches the rim's own half-width (10.00 px) to within a
quarter of a pixel.

The control matters: election also decorrelates with distance simply because
real depth varies smoothly. Seeding in flat background and walking a random
direction gives 6.67 px. The edge-driven agreement is **1.57× longer**. That is
the right direction but it is not a large margin, and the 10 % widths (21.1 vs
18.0) are closer still. **E3 corroborates; it does not by itself prove.**

---

## Verdicts

### P-WIDTH — **SURVIVES**, on three independent measurements

**MEASURED.**

| measurement | value | source |
| --- | --- | --- |
| rim `w50`, shipped arm | 10.00 px | `e2-polarity.json` |
| rim outer cutoff, shipped arm | 13.25 px | `e2-polarity.json` |
| rim gone by | 12–18 px band reads −0.004 | `e2e-shape.json` |
| election agreement half-width | 10.50 px | `e3-election.json` |
| election agreement 10 % width | 21.10 px | `e3-election.json` |
| **`WINDOW_RADIUS` (`focus.rs:83`)** | **13 px** | source |
| **DERIVED total spill** | **22 px** | source (`through_focus.rs:1145` uses the same chain) |

Nothing here is at 3 px or at 40 px. The rim's cutoff (13.25 px) lands on
`WINDOW_RADIUS`, and the election's 10 % width (21.10 px) lands on the derived
total spill. **P-WIDTH is confirmed.**

**ARGUED — the alternative it rules out:** the defocus blur radius on this
subject is much larger (soft-edge rise reaches 15–36 px, `e2_polarity.py`
unfiltered pass), the focus step is not a spatial length at all, and object sizes
in the accepted set span orders of magnitude. None of them predicts 13 px.

### P-POLARITY — **NOT CONFIRMED. NOT REFUTED. NOT TESTED.**

**MEASURED.** The sign table:

| edge polarity | n | rim in surround | reading |
| --- | --- | --- | --- |
| dark object / bright surround | 70 | **+0.0634** [+0.0533, +0.0754] | **bright rim — as ORCH observed** |
| bright object / dark surround | 18 | **+0.0009** [−0.0141, +0.0289] | **null — but only 5 of these edges straddle a depth step** |

**The prediction has been half-observed.** Where a bounded rim exists it is
contrast-enhancing, which is the polarity the mechanism requires. The other half
has no valid sample on any data this project currently holds: bee-3's
bright-object edges are not silhouettes, and tweezers' apparent signal is a
gradient that also appears without a merge.

The brief said: *"if rims are bright regardless of edge polarity, the mechanism
is dead, and that would point at something additive."* **That is not what
happened. Additive is rejected too** — a uniform additive glow predicts
`−0.0634` in row two and the CI excludes it. Row two is a null, not a bright rim.

### E3 — **corroborates**

The elected index does spill outward from silhouettes, with a half-width of
10.50 px against the rim's 10.00 px and a floor reached at the derived 22 px.
Against a flat-background control it is 1.57× longer, which is the right
direction with a modest margin.

### Controls

| control | result |
| --- | --- |
| **N3 positive control (plant)** | **FIRED.** Amplitude and width recovered; additive and contrast plants distinguished; envelope mapped to rise ≤ 6.50 px |
| **N1 no merge (pooled, 5 frames)** | **+0.0023** [+0.0012, +0.0033], **28× below** the merged rim |
| **N1b mean of 5 frames** | **NOT MEASURABLE** — every edge falls outside the envelope, n = 0 |
| **N2 soft edges** | rim **+0.0952** at rise 1–4 px, **−0.0348** at rise 12–16 px; falls away with softness, weak evidence at the soft end |
| **N4 flat ROI** | **fired at first run** (−0.30); fixed by a data-chosen amplitude floor; now **0 / 334 accepted** |
| **saturation** | fourth defect found and fixed; not the cause of the tweezers reading |

---

## Did ORCH's mechanism survive?

**It survived, weakened, with its decisive test still outstanding.**

**ARGUED.** In its favour, all MEASURED:

- The halo is a **merge artifact**: 28× its no-merge floor.
- It has the **merge's own length scale**, 10.00 px half-width against
  `WINDOW_RADIUS = 13`, gone by 13.25 px, with an election spill of matching
  width from the shipped path's own index map.
- It is a **property of sharp edges** and falls away as edges soften.
- It is **larger at edges that straddle a depth discontinuity** (+0.0817 at
  ≥ 2 frames vs +0.0634 overall).
- It is **unmoved by the noise gate** (gate 0: +0.0658 vs gate 4: +0.0634),
  which is what a pure selection artifact should do and which independently
  reproduces fact 1625.
- Where a bounded rim exists, its polarity is the one the mechanism predicts.

Against it:

- The killer prediction is untested. Nothing here shows the halo reverses sign.
- The in-sample level test that could have discriminated the laws is
  underpowered and separates nothing.
- E3's margin over its flat-background control is 1.57×, not 10×.

**The brief's own argument that F2's no-op is evidence stands up.** F2 modelled
the halo as veiling; a veiling model correctly does nothing to a selection
artifact. Nothing measured here contradicts that reading.

---

## E5 — the fix the mechanism implies

**Not implemented. ARGUED only, and conditional: P-WIDTH survived but P-POLARITY
did not, so this is a direction, not a licence to build.**

If the halo is selection spill, then no improvement in *modelling occlusion* can
touch it, and F1's failure is explained: F1 corrects the symptom by pushing
values back, which is why it works as a correction and looks milky — it removes
real background structure along with the rim, because it cannot tell them apart.

The remedy has to change **how the decision is made near strong edges**:

1. **Do not let a pixel with no focus information of its own inherit a
   neighbour's election.** The windowed focus measure has an implicit confidence:
   how much of the window's gradient energy comes from the pixel's own
   neighbourhood versus from a distant strong edge. Where that fraction is low
   the argmax is not evidence about this pixel and should be replaced by
   something depth-smooth or by a plain average.
2. **Make the merge an estimator with per-pixel weights rather than a windowed
   winner-take-all.** The existing noise gate already averages `n_eff` frames;
   the argmax that selects *which* frames is the winner-take-all step, and it is
   the one with the 13 px window on it.

**What would falsify the fix (rule 13/20):** an implementation of (1) that
suppresses the rim but leaves `w50` unchanged would show the rim was never
election-driven. An implementation that removes the rim *and* the 10.50 px
election spill together, with no loss of resolution on genuinely sharp detail,
confirms it. The input that would make this FAIL and that exists in the corpus:
a fine texture that is genuinely sharp in exactly one frame and sits within 13 px
of a strong silhouette — hairs at the edge of the bee's leg. If the fix cannot
keep those sharp it has traded the halo for softness, which is the trade F1
already lost.

**Do not build this on P-WIDTH alone.** Get the polarity test first.

---

## Proposed facts

Numbered `P1…` per rule 28; ORCH assigns absolute numbers.

- **P1 (MEASURED).** The shipped merge selects by per-pixel argmax over a focus
  field built from a 27×27 box mean of Sobel gradient magnitude
  (`WINDOW_RADIUS = 13`, `focus.rs:83`), then regularised over a further radius
  8 (`merge.rs:93`). The radius is fixed, not adaptive. DERIVED maximum spill:
  22 plane px — the same chain `through_focus.rs:1145` already uses as its test
  margin.
- **P2 (MEASURED).** On the shipped gate-4 arm, a dark object on a bright
  surround carries a bright rim in the surround of **+0.0634 [+0.0533, +0.0754]**
  of the edge amplitude, on 93 % of 70 accepted edges.
- **P3 (MEASURED).** That rim's half-width is **10.00 px** and its outer cutoff
  **13.25 px**; by 12–18 px it reads −0.004. It is a bounded rim, not a gradient.
  This matches `WINDOW_RADIUS = 13` and **P-WIDTH is confirmed.**
- **P4 (MEASURED).** The same pipeline on single unmerged frames reads
  **+0.0023 [+0.0012, +0.0033]** — 28× smaller. The halo is a merge artifact.
- **P5 (MEASURED).** The elected-frame index, read from an index map whose merged
  output is **byte-identical to the shipped arm**, agrees with the edge's own
  election out to a half-width of **10.50 px** and reaches the floor by 22 px,
  against 6.67 px for a flat-background control.
- **P6 (MEASURED).** The rim is **unchanged at gate 0** (+0.0658 vs +0.0634),
  independently reproducing fact 1625: the noise gate does not touch the halo.
  Because `merge.rs:3341` establishes gate 0 admits **exactly the winner**, this
  says the halo is identical in the pure winner-take-all limit and in the
  shipped estimator — a selection artifact, not an averaging artifact.
- **P7 (MEASURED).** The rim grows with depth discontinuity: **+0.0817** at edges
  whose sides elect frames ≥ 2 apart, vs +0.0634 overall.
- **P8 (MEASURED).** The rim falls away with edge softness: **+0.0952** at 10–90
  rise 1–4 px, **−0.0348** at rise 12–16 px.
- **P9 (MEASURED — a null).** On the shipped arm, bright objects on dark
  surrounds read **+0.0009 [−0.0141, +0.0289]**, n = 18. The CI excludes both a
  contrast rim (+0.0634) and an additive glow (−0.0634). **But only 5 of those 18
  edges straddle a depth discontinuity, so P-POLARITY is UNTESTED, not refuted.**
- **P10 (MEASURED).** `tweezers-cpl` appears to show the predicted dark rim
  (+0.1326, n = 96, 100 % positive) but the profile **does not end** within 30 px
  and a **single unmerged frame reproduces its shape** at a third of the
  amplitude. It is a background gradient and is rejected as evidence.
- **P11 (MEASURED).** `PIL.Image.open()` aside (fact 1615), **M96's
  `elected-index.tif` is uint8 RGB — a colour-mapped preview, not raw frame
  indices.** Any analysis that read frame numbers out of it read a colour map.
- **P12 (MEASURED).** `strehl stack --index-map` reproduces the shipped
  `armM4-gate4-binlin.tif` **byte for byte** under `STREHL_ALIGN=0`, so an
  election map at the exact shipped settings is cheap and available (~4 min).
- **P13 (MEASURED — instrument).** An edge-profile statistic normalised by edge
  amplitude reads **−0.30** in featureless background unless an amplitude floor
  is imposed; real edges and flat-ROI noise steps separate cleanly at
  **2879 DN vs 1052 DN**. Rule 9 caught this.
- **P14 (MEASURED — instrument).** The edge transition contaminates any
  per-side overshoot statistic; on this data the effect is large enough to make
  an artifact-free edge read as strongly contrast-reducing. The decomposition
  `S = bright − dark` is transition-immune by construction and is the reason the
  headline is trustworthy.
- **P15 (MEASURED).** The PIL uint8 narrowing was planted on the shipped arm
  with a model **commissioned byte-identical to PIL over 786,432 samples**. The
  M121 headline moves **−2.4 %** (+0.0634 → +0.0619) and the bright-object null
  stays null (+0.0009 → −0.0016, inside its own CI). **Neither M121 verdict is a
  quantisation artifact.** Fact 1615 also reproduces live at **227.5×** level
  loss (18202 → 80) on a crop occupying 20247 DN.
- **P16 (DERIVED).** The narrowing damages a normalised edge statistic mainly
  through **re-detection and band placement, not through the pixel value**: the
  same class on the same data moved **+0.4 % with the read band pinned** and
  **−31 % when allowed to re-detect**. The triage question "does it divide a
  small quantity by a large one" should be joined by **"is anything about *where*
  I measure decided from the narrowed pixels?"** Amplitude does not predict the
  damage — the worst-affected class had the *highest* median amplitude
  (10260 DN), refuting the obvious occupied-range explanation.
- **P17 (MEASURED).** ORCH's ~12-level bound holds on a **first-moment ratio**
  statistic, a class its rule does not cover: the M121 headline breaks between
  **13.1 and 6.5 levels**. But the levels must be counted across the
  **normalising denominator**, not the signal — at the PIL defect the signal
  holds **1.63 levels**, 7× below the bound, and the statistic still retains
  **97.7 %**. For any *small ÷ large* statistic, count the large one.
- **P18 (MEASURED).** The sample count is the leading indicator of narrowing
  damage. The one dangerous rung (146 % over-read, a plausible wrong number) is
  flagged only by `n` dropping 69 → 57; past it the failure is loud (exact
  `+0.0000`, n jumps to 106).
- **P19 (MEASURED — corrects an earlier M121 claim).** `MIN_AMPLITUDE = 2000 DN`
  excludes **nothing** from the headline class (`n = 70` at every floor from 0
  to 2000), so it is **not** what protects the headline under narrowing. The
  headline is floor-independent (13.7 % spread across the whole sweep). The
  floor's real job is the flat-ROI false positives of N4, where it took
  113 → 0.
- **P20 (MEASURED).** `D` for M121's two-arm claims runs 1.0 → 70.4. The two
  headline contrasts sit at `D` = 28 and `D` = 70, deep in ORCH's unprotected
  regime, but carry 25–65× margins, so no conclusion turns over at the
  predicted 8 % shift. The thinnest claim is E3 (1.6 → 1.5×) — which `D`
  independently identifies as the one already flagged corroborative-only.
- **P21 (MEASURED).** `D` over-predicts the M121 headline by 3.2× (predicts
  7.6–8.0 %, measured 2.4 %) because the headline gets **no cancellation
  protection at all** — it has one arm. Its protection is **averaging**:
  a fully independent per-edge error of 8.04 % pools to 0.96 % over n = 70,
  a fully correlated one stays at 8.04 %, and the measured 2.4 % sits 20 % of
  the way between. 1/√N scaling confirmed by bootstrap (ratio flat at ~0.64
  from n = 20 to 70).
- **P22 (DERIVED).** There are **three** protection mechanisms, not one:
  cancellation (governed by `D`), position-insensitivity (levels per window),
  and **averaging (governed by N)**. A statistic can be deep in the unprotected
  regime on `D` and still robust if N is large. **Report `D` and N together.**
- **P23 (MEASURED).** All twelve M121 inputs are uint16/16-bit; the M93 gate-4
  arm is byte-identical to M121's own re-render, proving it was not narrowed
  upstream. Zero `Image.open(` call sites.

---

## Things found that were not being looked for

1. **M96's `elected-index.tif` is a colour-mapped uint8 preview.** It is named
   like a data product. Anything downstream that treated it as frame indices
   read a palette. (P11)
2. **`--index-map` reproduces the shipped arm byte for byte.** Election maps at
   exact shipped settings are a 4-minute command, not an archaeology problem.
   Discipline 830's whole class of error is avoidable this way. (P12)
3. **The gate-0 arm and the shipped arm have the same halo to within noise.**
   Measured independently here, and it reproduces fact 1625 by a completely
   different route.
4. **The instrument read −0.30 on empty background** before rule 9's control was
   run. Any edge statistic in this project that divides by a locally-estimated
   amplitude has this failure mode. (P13)
5. **`tweezers-cpl` has a large, slow luminance gradient around its bright
   subject** that mimics a rim under amplitude normalisation and survives into a
   single frame. Any halo work on that subject needs the "does it end" check.
6. **On a bee there is essentially no bright-object-on-defocused-dark-background
   edge.** This is a *capture* gap, not an analysis gap, and it is what blocks
   P-POLARITY. See below.

---

## What is needed to finish this

**One capture, and it is small.** A subject with genuine bright objects
silhouetted against a **dark, deeply defocused background**, with the bright
object **not clipped** — pale hairs, a light-coloured seed head, or a
white-painted probe over a dark recessed ground, exposed 1–2 stops down so no
plateau reaches the ceiling. 100–300 frames at the usual step.

With that, row two of the sign table becomes a real test, and P-POLARITY is
decided in one afternoon by re-running `e2d_tweezers.py` against it. Until then
the mechanism has strong circumstantial support and no decisive test, and this
milestone recommends **against** building the E5 fix on the strength of P-WIDTH
alone.

---

## Scripts and outputs

| script | produces |
| --- | --- |
| `experiments/M121-halo-polarity/m121_io.py` | loaders; `uint16` assertions; arm provenance record |
| `…/e0_inventory.py` | `C:\dev\strehl-out\M121\e0-inventory.json` |
| `…/e0b_look.py`, `…/e0c_crops.py` | `C:\dev\strehl-out\M121\look\*.png` |
| `…/halo_lib.py` | the measurement core (`S`/`C`, widths, cutoffs) |
| `…/runner.py` | `scan()` — the single path E2 and every control share |
| `…/n3_plant.py` | `n3-plant.json` — commissioning ladder and envelope |
| `…/yield_probe.py` | edge-yield design study |
| `…/amp_probe.py` | the amplitude distributions behind the rule-9 floor |
| `…/e2_polarity.py` | `e2-polarity.json` — **the sign table** |
| `…/e2b_law.py` | `e2b-law.json` — out-of-sample law test, depth split |
| `…/e2c_level.py` | `e2c-level.json` — in-sample level test (underpowered) |
| `…/e2d_tweezers.py` | `e2d-tweezers.json` — second subject |
| `…/e2e_shape.py` | `e2e-shape.json` — band tables, "does it end", crops |
| `…/e3_election.py` | `e3-election.json` — election spill, byte-identity check |
| `…/e4_controls.py` | `e4-controls.json` — N1, N1b, N2 ladder, N4 |
| `…/n5_quant.py` | `n5-quant.json` — the PIL narrowing planted and commissioned |
| `…/n6_ladder.py` | `n6-ladder.json` — narrowing ladder; where the rim breaks |
| `…/n7_floor.py` | `n7-floor.json` — support-floor sweep and saturation audit |
| `…/n8_dstat.py` | `n8-dstat.json` — `D` for every two-arm claim; the averaging measurement |
| `…/prov_audit.py` | `input-provenance.json` — were M121's inputs narrowed upstream? |

Renders (invocations recorded beside each):
`C:\dev\strehl-out\M121\e3\` (bee-3, byte-identical to shipped),
`C:\dev\strehl-out\M121\tweezers\` (merged, index map, single frame).

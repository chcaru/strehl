# V-HALO: independent verification of BUILD-HALO

**VERDICT: CONFIRMED WITH QUALIFICATION.**

v2 (`bca6df3`) is a real, reproducible improvement and its reported numbers are
honest — I reproduced all three of its renders bit-for-bit and its revised noise
figures to within 0.2 points. But **two of its explanations are wrong**, and the
load-bearing mechanism claim is weaker than stated:

- the empirical dose-response slope **does not survive freezing the edge set**;
- v2's own gain comes from the depth-grid interpolation, **not** from the
  treatment-boundary feather it is named after;
- `FEATHER = 1.25`'s stated rationale is not what the code does, and the shipped
  diagnostic is mathematically incapable of detecting the failure it guards.

**It is still not print-worthy.** See section 8.

This document covers two passes: **v1** (`3315a91`/`e5e62d4`) and **v2**
(`bca6df3`). All measurements are mine and are **UNVERIFIED** by anyone else.
Section 0.1 lists errors I made and corrected, including one in the first
committed version of this file.

---

## 0. Method

Two implementers edit this tree continuously, so I did not hash arms — I removed
the confound. `git archive` of each explicit SHA into
`C:\dev\strehl-out\V-HALO\pin` (v1) and `…\pin2` (v2), built and rendered there.
Both pins proved they resolve to their own sources: patching them made cargo
print `Compiling strehl-core v0.0.0 (C:\dev\strehl-out\V-HALO\pin2\crates\...)`.

**Commissioned with sabotage; every arm required to go RED:**

| # | sabotage | observed | |
|---|---|---|---|
| S1 (v1) | `LayerSupport::apply_at` discards the masked mean | on-arm collapses to the off hash | RED |
| S2 (v1) | `window_radius()` ignores `STREHL_WINDOW_RADIUS` | all ladder rungs become byte-identical | RED |
| S1 (v2) | `apply_at:736` blend write discarded | on-arm → `D2DC0272…` = baseline exactly | RED |
| control | unsabotaged | on `27E1FCD8…` ≠ off `D2DC0272…` | live |

**The render pipeline is deterministic**: three repeat renders of
`flower-inner-edge-cpl` from one pin gave `50F99118…` every time. That matters,
because it makes byte-identity a valid instrument here.

### 0.1 My own errors, found and corrected

I report these because an unverified verifier is worth nothing.

1. **A wrong hash in the first committed version of this file.** I wrote that
   `BUILD-HALO.md` §3's `965AA23B…` was wrong and "the real hash is `895E458D…`,
   as my own render confirms". **My render is `85213987…`** — I confused two
   similar hex strings. I have reproduced *neither* `965AA23B` nor `895E458D`.
   The finding that survives is weaker and is stated in section 2.
2. **A stale-binary error that nearly produced a false headline.** `Copy-Item`
   restores a file with the *source's* mtime, so cargo saw it as clean and did
   not rebuild. Two renders were made with the wrong binary, and I briefly had
   evidence that BUILD-HALO's `flower-inner-edge` v2 deliverable was
   unreproducible. It is not — after forcing the rebuild it matches bit-for-bit.
   **Retracted.** Any build-flag A/B on this repo must assert that
   `Compiling strehl-core` actually appeared.
3. **Two measurement instruments discarded for failing their own controls**: a
   veil metric that selected the baseline's darkest quartile (regression to the
   mean — it scored *every* arm above baseline, contradicting the pictures), and
   an earlier blotch metric whose negative control failed. Section 4's blotch
   instrument is the rebuilt one and its control passes.

---

## 1. The mechanism — the analytic half is exact; the empirical slope is not robust

### 1.1 What is solid

`focus::tests::centre_tap_fraction_and_read_extent_are_what_m13_specified`
**measures** the read extent by perturbing one pixel and counting moved outputs,
asserting `taps == (2*(SOBEL_RADIUS + WINDOW_RADIUS)+1)^2 == 841`. It passes.
The focus field at `p` provably cannot see past Chebyshev radius `1 + w`. Slope 1
is an upper bound by construction, not a fit.

**Independent confirmation of the scale, without the rim estimator.** On
`bee-2-cpl` the residual v2 correction, profiled against distance from sharp
structure, peaks at `d = 0` (511 DN) and falls to half by **d ≈ 12 px**, gone by
~20. The whole effect lives inside `SOBEL_RADIUS + WINDOW_RADIUS = 14 px`. That
is the mechanism's spatial signature, measured on a different quantity
(`|after − before|`) from the one used to derive the slope.

### 1.2 What does not survive: the slope depends on who supplied the edges

The brief asked whether the rim estimator is itself a function of window radius.
Directly, **no**: `scan()` is never passed `w`, and `DMAX`, `DSTEP`, `PLATEAU`,
`NEAR`, `BANDS` and the classifier are fixed. The risk is indirect —
`edge_seeds` thresholds on a percentile of *that arm's own* gradient field, so a
wider window (smoother, more veiled background) admits a different edge set.

So I froze the edge set and re-measured. Seeds **and** normals taken from one
donor rung, acceptance decided by the donor alone, applied unchanged to all six
rungs, with an estimator carrying **no 30 px cap** (I search to `DMAX = 48`):

| donor | w3 | w6 | w9 | w13 | w20 | w26 | **slope** | n |
|---|---|---|---|---|---|---|---|---|
| **w3** | 24.25 | nan | 24.75 | 27.25 | 27.25 | 27.75 | **+0.161** | 32 |
| **w13** | nan | 14.75 | 15.25 | 15.25 | 26.00 | 35.75 | **+1.087** | 34 |
| **w26** | 20.75 | 20.75 | 21.00 | 20.00 | nan | nan | **−0.066** | 30 |
| *per-arm re-detection (published method)* | | | | | | | *+1.043* | |

**The measured slope is a property of the edge set, not of the image.** Freeze
the edges on w3 and it is +0.16; freeze on w26 and it is −0.07. Only the w13
donor — the shipped radius, the middle of the ladder — returns ≈1, and that is
also the donor whose normals are least wrong for every other rung.

I cannot separate two explanations: (a) per-arm edge re-detection manufactures
the slope, or (b) frozen normals degrade the profile for distant rungs. Either
way the conclusion for the report is the same: **the empirical slope of 1.07 is
not established.** It is one of several values this family of estimators returns
depending on a choice that was never reported. Four independent attempts — their
donor mode, my ring-median reach estimator, my frozen-edge normaliser, and this
cross-matrix — have failed to produce a stable paired read of this ladder.

Realised distinct luminance levels in the measured window: **26 417** across the
ladder sample, so no quantisation hazard in these pooled statistics.

### 1.3 Other defects in the §1 ladder, unchanged from my v1 pass

- **Unpaired, with 6.1× edge-count drift** (21 → 129, monotone in `w`) — three
  times the 2× drift §5.2 cites as disqualifying its own before/after. Counts
  are not reported in §1.
- **The published intercept 1.08 is absent from its own table.** Refitting every
  published row against `W`, `W+1`, `W+2` over all 57 subsets of ≥3 rungs yields
  no intercept within 0.05 of 1.08. The headline fit reproduces their slope
  exactly (1.0750) and gives intercept **0.4750 ± 1.1761** — undetermined.
- **The top rung sits on the instrument's ceiling.** `outer_cutoff` searches only
  `dist ≤ PLATEAU[0] = 30`; their w26 = 29.00 is 1 px under it.
- **§1 and §5.2 disagree about the same render.** Both describe `bee-3-cpl`,
  gate 0, `ALIGN=0`, radius 13. §1 says `C w50` 13.50; §5.2 says 17.25. My
  independent render gives **17.25, peak +0.63424, n = 36** — matching §5.2 to
  five decimals and contradicting §1.

**Recommendation:** rest the mechanism on §1.1, which is exact and already
unit-tested, and on the 14 px reach. Withdraw the slope and intercept figures.

---

## 2. Dark when unset — CONFIRMED byte-exactly, and still true after v2

Rendered from my own pins, `bee-2-cpl`, product default gate, alignment on:

| arm | SHA-256 | |
|---|---|---|
| `STREHL_EDGE_AWARE` unset (v2 pin) | `D2DC0272…E013331D` | |
| `STREHL_EDGE_AWARE=0` (v2 pin) | `D2DC0272…E013331D` | identical |
| BUILD-RENDER frozen baseline | `D2DC0272…E013331D` | identical |
| BUILD-HALO `halo-off` | `D2DC0272…E013331D` | identical |
| `=1`, v1 pin | `21191A3B…FFD20880` | differs |
| `=1`, v2 pin | `27E1FCD8…D87F5EC5` | differs, and from v1 |
| **S1-sabotaged `=1`** | `D2DC0272…E013331D` | **RED — collapses** |

The v2 dark path is byte-identical to v1's and to pristine HEAD, and the
flag-unset ladder rung is unchanged between pins (`85213987…` both). The feature
is genuinely dark when unset and genuinely live when set, and my instrument
tells those apart. **Claim confirmed.**

**All three v2 deliverables reproduce bit-for-bit** from `bca6df3`:
`bee-2-cpl` `27E1FCD8…`, `flower-inner-edge-cpl` `9995F6C1…`,
`flower-bud…-fern-cpl` `0B98147E…`. (Their file timestamps, 02:56–03:04, precede
the commit at 03:07:22 — they were rendered from the working tree that became
the commit. Benign, and confirmed benign by the hashes.)

**Residual defect (documentation, low):** `BUILD-HALO.md` §3 states the identity
as `965AA23B…`; commit `3315a91`'s own message states it as `895E458D…`. They
cannot both be right. I reproduced neither and cannot say which is correct —
only that the report and its commit message disagree about the evidence for the
same claim. **Corrected from my previous version of this file**, which wrongly
asserted `895E458D` was confirmed.

Cost, v2 on my box: 58.6 s → 140.9 s = **2.40×**.

---

## 3. `FEATHER = 1.25` — the stated rationale is not what the code does

The author names this its weakest link: chosen from one synthetic probe, and at
2.0 "almost nothing cleared all three guards … leaving halo on the plate while
every metric looked fine". I tested it on real composites by patching the
constant in my pin and rebuilding (verifying recompilation each time; and
verifying the patch was live — `bee-2-cpl` at 2.0 gives `9CCBA2EC…` ≠ 1.25's
`27E1FCD8…`).

**Finding 3a — the treated-pixel count is mathematically invariant to FEATHER.**
`smoothstep(lo, hi, v) = 0 ⟺ v ≤ lo`, and all three guards use `lo` = the
un-feathered threshold. So the *set* of treated pixels cannot change with
FEATHER, only each pixel's strength. Measured on `flower-inner-edge-cpl`:

| FEATHER | 1.0001 | 1.25 | 1.6 | 2.0 |
|---|---|---|---|---|
| shipped log "support masked" | 17.37% | 17.37% | 17.37% | 17.37% |

**The shipped diagnostic cannot detect the failure mode this constant exists to
prevent.** The number it prints is constant by construction while the effective
strength falls by a third. "Almost none [clear all three guards]" is not what
happens at 2.0 — the same pixels clear them, at reduced amplitude.

**Finding 3b — the sensitivity is real but gentle, and 1.25 is nearly hard.**
`flower-inner-edge-cpl`, all four hashes distinct:

| arm | flat `noise_sd` vs base | blotch (pp) | mean \|Δ\| |
|---|---|---|---|
| v1 (hard bins, hard guards) | +5.3% | 1.9275 | 28.37 |
| F = 1.0001 (tent bins, hard guards) | +1.3% | 0.4500 | 15.56 |
| **F = 1.25 (shipped)** | **+1.2%** | **0.4061** | **14.32** |
| F = 1.6 | +1.1% | 0.3461 | 12.07 |
| F = 2.0 | +0.7% | 0.2656 | 9.58 |

The shipped value sits 8% below the hard-switch limit in applied magnitude. The
curve is smooth and monotone — there is no cliff at 2.0, just a 33% dilution.
The constant is defensible; **the argument given for it is not.**

**Finding 3c — the unit test tests the wrong geometry, and says so.** Its own
comment reads: *"A synthetic hard step is the wrong probe here: it crosses tau
within a single pixel, so a tight feather correctly produces no partial zone at
all."* The probe was therefore changed to a quadratic depth ramp. But **an
occluding edge — the entire subject of this work — is a hard step in depth.** By
the test's own reasoning the feather produces no partial zone at a silhouette.
It smooths gentle depth ramps, which is not where the artefact was.

---

## 4. v2's own causal story is wrong: it is the tent, not the feather

This is the finding I would most want acted on. v2 bundles two changes — tent
interpolation of the depth grid, and `smoothstep` feathering of the three
guards. The author now says the grid was "real but minor" and the treatment
switch was "the larger discontinuity". Setting `FEATHER ≈ 1` isolates them,
because it leaves the tent in place and restores hard guards:

| step | blotch (pp) | share of the total repair |
|---|---|---|
| v1 → tent grid, hard guards (F = 1.0001) | 1.9275 → 0.4500 | **76.6%** |
| tent grid → + shipped feather (F = 1.25) | 0.4500 → 0.4061 | **2.3%** |

Same ordering in flat noise: +5.3% → +1.3% (tent), then +1.3% → +1.2%
(feather). **The depth-grid interpolation does essentially all of the work; the
treatment-boundary feather contributes about a fortieth.** The retraction was
made in the right direction — v2 is better — but the attribution is inverted.

Blotch instrument: 2–8 px DoG contrast restricted to ground the *baseline* says
is featureless, threshold set from the baseline's own quiet region. Negative
control — the shipped correction field gaussian-smoothed at σ = 8, i.e. the same
amplitude made smooth — scores **0.0281 pp** against the shipped arm's **0.4061
pp**, a 14× separation at comparable magnitude (\|Δ\| 10.00 vs 14.32). The
instrument reads sharpness of added structure, not amplitude. The baseline
anchors at 0.0000 by construction, so only comparisons among treated arms are
meaningful; the control supplies the scale.

---

## 5. The revised noise figures — CONFIRMED, and the reattribution holds

Measured in linear at the frozen ROIs, `tifffile`, `uint16` asserted, raw beside
ratio, no gate change:

| subject | class | raw base | raw v1 | raw v2 | v1 | v2 | claimed v2 |
|---|---|---|---|---|---|---|---|
| bee-2-cpl | flat `noise_sd` | 360.235 | 391.888 | 376.110 | +8.8% | **+4.4%** | +4.5% |
| flower-inner-edge-cpl | flat `noise_sd` | 155.633 | 163.905 | 157.563 | +5.3% | **+1.2%** | +1.3% |
| flower-bud…fern-cpl | flat `noise_sd` | 38.142 | 40.295 | 38.642 | +5.6% | **+1.3%** | +1.1% |
| bee-2-cpl | detail `hp_energy` | 1050.0 | 1161.9 | 1088.4 | +10.7% | +3.7% | — |
| bee-2-cpl | edge `hp_energy` | 685.8 | 881.7 | 816.9 | +28.6% | +19.1% | — |
| flower-inner | edge `hp_energy` | 308.9 | 370.9 | 317.5 | +20.1% | +2.8% | — |
| flower-bud | edge `hp_energy` | 444.0 | 568.9 | 467.6 | +28.1% | +5.3% | — |

All three revised figures reproduce to within 0.2 points. **Confirmed.**

**The reattribution away from `FOCUS_NOISE_SD` is sound**, and for a reason
stronger than the author gives: v2 changed *only* the smoothness of the blend —
not `FOCUS_NOISE_SD`, not the window radius — and removed 50–77% of the excess.
A cause that survives when its supposed driver is untouched is not the driver.
The FEATHER ladder in section 3b is the dose-response that confirms it. The
residual +4.4% on `bee-2-cpl` remains unattributed.

**"Is the lower `hp_energy` artefact removal or detail loss?"** Evidence says
removal: v2 is above baseline on **all nine** rows (+0.2% to +19.1%), so no
class lost structure relative to the untreated image, while measured blotch fell
4.7×. There is no evidence of blur. But this is the same statistic that in v1
ranked the two most damaged crops as most improved — it should not be the
deciding instrument in either direction, and it isn't here; the pictures are.

---

## 6. The coverage-boundary claim — UNVERIFIED, and the pictures sit awkwardly with it

The claim: the bright blobs hugging silhouettes are `MIN_LAYER_FRACTION`
withdrawing where a 13 px window no longer holds enough background.

The geometry is not obviously kind to it. For a **broad** silhouette, a
background pixel adjacent to the boundary has roughly half its window in the
background layer — far above `MIN_LAYER_FRACTION = 0.12`. Withdrawal should bite
on **thin** structures (antennae, claws, trichomes), where a pixel's own layer
really is a sliver. Yet the strongest surviving collar in the set is on
`flower-bud-with-background-fern-cpl edge0`, a large smooth convex bud — and the
Δ map there is a chain of rounded lobes of roughly constant size following the
outline, which is the signature of a box window, not of a coverage threshold.

I could not turn this into a measurement I trust: my frozen-silhouette reference
locked onto the trichome hairs rather than the bud outline, so the reach profile
is interpretable only on `bee-2-cpl`. **I therefore report the claim as
unverified, not refuted.** It is being used to justify the next phase of work,
so it deserves a direct test — instrument `blend` and the per-layer fractions and
dump them as planes, rather than inferring from composites.

---

## 7. Test coverage

388 tests pass in the v2 pin (was 384), including all 17 `edgeaware` tests and
the read-extent test. The four new v2 tests are real behavioural tests — the
tent-splat mass conservation and grid-continuity ones are genuine.

**The gap is unchanged:** the 279 new lines in `merge_cmd.rs` — guide election,
the `tau` and `conf` defaults, the two-pass substitution — still have no tests,
and `merge_cmd.rs` is untouched by v2. The shipped wiring remains an unverified
change. `FEATHER` has no test that ties it to a real composite.

---

## 8. Is it print-worthy?

**No.** The author's own verdict — "veiling halo materially reduced, tight rim
and coverage-boundary blobs remain" — understates one thing and overstates
another.

What I see, judging the linear images at the frozen ROIs:

- **`flower-inner-edge-cpl`: genuinely better, and v2 is much better than v1.**
  The trichome silhouettes are crisp against dark ground, and v1's carving of the
  smooth bokeh at `edge2` is largely repaired. This is a real win.
- **`flower-bud…fern-cpl`: unchanged where it matters.** The tight bright sheath
  survives, and a scalloped lobed collar still rings the bud.
- **`bee-2-cpl`: still disqualifying.** This is the part the report does not
  say. At `detail1` the dark leg still has **hard-edged pale plates carved into
  it** — a serrated bite out of a foreground object that does not exist in the
  baseline. v2 softened the *edges* of those plates; it did not remove them, and
  their geometry is essentially unchanged from v1. At `flat1` the smooth ground
  still carries hard-edged tongues and worm-like patches.

**What specifically disqualifies it:** on `bee-2-cpl`, structure invented on and
around foreground objects — pale plates cut into a dark leg, and hard-edged
mottling on smooth ground. A viewer reads that as damage, not as defocus. The
original veiling halo was a soft wash; this is a shaped, opaque artefact sitting
on the subject. At print scale it is the more objectionable of the two, and it
means the treated `bee-2-cpl` render is worse than its untreated baseline.

The honest summary is that v2 fixed the *background* half of its own artefact
(smooth bokeh is no longer carved) and left the *foreground* half intact.

---

## 9. The number that does not fit

**Blotch falls 1.9275 → 0.4500 pp when the depth grid is interpolated with the
guards still hard, and only 0.4500 → 0.4061 pp when the feather is added.**

v2 is named for the feather and its rationale section is written about the
treatment boundary. Its own dose-response says the feather is responsible for
2.3% of the repair and the tent for 76.6%. Nothing in the report's account of v2
explains that split — and it matters, because the constant now under scrutiny
(`FEATHER = 1.25`) governs the part that barely does anything, while the part
that does the work (`N_LAYERS`, the tent) has no sensitivity study at all.

Runners-up: the mechanism slope is +0.16, +1.09 or −0.07 depending on which arm
supplies the edge set; and the shipped "support masked" diagnostic prints
17.37% at every value of FEATHER.

---

## 10. Reproducing this

```powershell
git archive --format=tar bca6df3 -o pin2-src.tar     # extract somewhere unwritable by others
# build there; ALWAYS confirm "Compiling strehl-core" appears after any patch
```

Artefacts: `C:\dev\strehl-out\V-HALO\` — `pin\`, `pin2\`, `ladder\`, `ident2\`,
`feather\` (the FEATHER ladder), `sabo\`, `look2\` (base | v1 | v2 | Δ panels),
`v2-stats.json`.

**Everything in this document is my own measurement and has not been
independently verified.**

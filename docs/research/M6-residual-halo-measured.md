# M6 — the alignment residual is defocus, and the halo is not a scalar

**Status:** measured. Two independent results, answering SYNTHESIS §10 open
questions 6 and 10.

> **INDEPENDENTLY REPRODUCED** by the orchestrator, on a separate run, per the ultra rule that an
> author never verifies their own work. Four legs:
>
> | Leg | What was re-done | Result |
> | --- | --- | --- |
> | Halo arithmetic | Re-derived by hand from M3's fitted similarity for 109MSDCF, independently of this harness | Displacement **39.89 px** vs their 39.35; halo **32.76 px** vs their 32.39; overstatement ratio **1.217** vs their 1.202. Confirms both the number and, more importantly, the **displacement-vs-halo distinction** |
> | Self-tests | `m6_selftest.py` re-run in full | All pass. **Group 12 is the one that matters**: S6 recovers a *planted* directional bias at p=0.010 and stays null on a variance-only perturbation at p=0.208 — so **the S6 null on real data is informative, not merely underpowered** |
> | Halo table | `m6_controls.py` re-run | 19.42 / 32.39 / 89.23 px reproduced exactly |
> | Full statistics | `m6_measure.py` re-run end to end (~9 min) | Every headline figure reproduced exactly: γ = **+0.05966 / +0.04522**; S5 in-focus **0.172 / 0.144 px** vs far **0.689 / 0.247 px**; within-pair gap **+0.6672 px, p=0.0104**; within-tile **+0.5993 / +0.4602**; S6 b_rad **+0.00068 ± 0.01088**; S2 null on all three |
>
> The `coffee-bean` sign inversion at Δ=1,2 (−0.077, −0.083 px) reproduced too. It is disclosed in
> §2 below rather than smoothed over, which is the correct handling; it is carried into
> SYNTHESIS §3.3 as a caveat on the proposed fix.

Reproduction: `experiments/m6-residual-halo/README.md`. Every number below is
in `out/controls.txt` or `out/measure.txt`, produced by the exact commands in
that file. Rust harness: `experiments/m3-drift/src/main.rs`.

---

## Verdict

The 0.6–1.3 px residual M3 could not explain is **cause (b), blur-induced
correlation degradation** — MEASURED, high confidence. Tiles that are in focus
in both frames of a pair align to **0.144–0.172 px at Δ=1**, at or below M3 §0's
0.19 px estimator noise floor, while tiles far from focus in the same pairs
align to 0.25–0.69 px; the gap survives comparison *within the same frame pair*
and *within the same tile*. Cause (a), depth-dependent magnification, is not
detected by any of the three statistics that were shown able to find it when it
was planted. But the architectural consequence §3.4.2 hoped for **does not
follow**: the degradation is not radially organised and does not flip sign with
which frame is blurrier, so it does not look like a field-dependent asymmetric
PSF. On all three real stacks the signature matches the *symmetric*-blur control
case exactly. **A lens plugin therefore does not become genuine computation. It
stays a data file** — ARGUED from the measured signature. The right fix lives in
the aligner, not in gear knowledge: weight or reject tiles by how defocused they
are in the pair being matched, which needs no lens identity at all.

The halo at the exact frame corner is **32.4 plane px** for the 22-frame stack —
MEASURED, replacing B1's estimate of 39. The two figures differ because **39 is
a displacement, not a halo**: a halo is a rectangle expansion, so the comparable
quantity is `max(|dx|,|dy|)`, not the Euclidean norm. The corner:centre ratio is
**141×** and Spearman(radius, halo) is 0.963, so the halo is very nearly a pure
function of radius. **A scalar `halo()` does not survive** — but the waste
argument in B1 is the weaker of the two available arguments. Within one stack a
scalar costs only 1.2–2.1× in gather area. Across stacks the corner halo is
19.4 / 32.4 / 89.2 px for three stacks from the same camera, and a `halo() ->
usize` is answered without seeing the stack, so it must be sized for the worst
stack the lens will ever shoot: **4.3× and 8.1× waste** for the two smaller
stacks at 128 and 64 px tiles. That is what kills it.

---

## Headline table

| # | Claim | Value | Label |
| --- | --- | --- | --- |
| 1 | In-focus tiles, Δ=1, 109MSDCF / 119MSDCF | 0.172 / 0.144 px | MEASURED |
| 2 | Far-from-focus tiles, same pairs | 0.689 / 0.247 px | MEASURED |
| 3 | In-focus residual vs M3's 0.19 px noise floor | 0.76–0.91× | DERIVED from 1 |
| 4 | S1 γ, residual per frame of defocus mismatch | +0.0597 / +0.0452 px | MEASURED |
| 5 | S1 γ, real-data estimator floor (N0-integer) | +0.000003 ± 0.000032 px | MEASURED |
| 6 | S5 gap, within the same frame pair (119MSDCF) | +0.667 px, p=0.010 | MEASURED |
| 7 | S5 gap, within the same tile | +0.599 / +0.460 / +0.241 px | MEASURED |
| 8 | S2, depth-organised radial scale anomaly | ρ = +0.066 / +0.135 / −0.100, all p > 0.22 | MEASURED (null) |
| 9 | S6, radial peak displacement per frame of blur asymmetry | +0.033 / +0.001 / +0.020 px, none significant | MEASURED (null) |
| 10 | S6 on planted symmetric blur (P2) | +0.003 ± 0.013 px — flat, while S1 fires at +0.063 | MEASURED |
| 11 | S6 on planted asymmetric PSF (P3) | −0.039 ± 0.013 px, p=0.010 — fires | MEASURED |
| 12 | Corner halo, 109MSDCF (22 frames, −1.835%) | **32.39 plane px** (64.8 sensor px) | MEASURED |
| 13 | Corner halo, 119MSDCF (33 frames, −1.029%) | 19.42 plane px | MEASURED |
| 14 | Corner halo, coffee-bean (105 frames, −4.575%) | 89.23 plane px | MEASURED |
| 15 | Corner:centre halo ratio, 128 px tiles | 31.03 / 0.22 = **141×** | MEASURED |
| 16 | Halo vs radius | `halo = 0.015971·r − 0.740 px`, ρ = 0.963 | MEASURED |
| 17 | Per-stack scalar halo waste, 128 px tiles | 1.34 / 1.24 / 1.73× gather area | DERIVED |
| 18 | Cross-stack scalar halo waste, 128 px tiles | 3.48 / 4.25 / 1.86× gather area | DERIVED |
| 19 | B1's "39 px" | is the Euclidean displacement; the halo is 32.4 px | VERIFIED — B1 overstates by 1.202 |

Stack order throughout is 109MSDCF (f/11, ISO 160, 22 frames), 119MSDCF (f/5.6,
ISO 50, 33 frames), coffee-bean (f/8, ISO 50, 105 frames).

---

## Part 1 — what the residual is

### 1.1 The degeneracy that had to be broken first

M3 aligned every frame `k` to frame 0. Inside a single pair `(0, k)`, a tile's
depth `w` and the pair's defocus mismatch are related by

```
|w − k| − |w − 0| = k − 2w
```

which is a deterministic linear function. Depth and defocus are the *same
regressor* in M3's design, so M3 could not have separated (a) from (b) with the
data it collected, no matter how it was analysed — DERIVED, and it is why this
measurement needed new data rather than new arithmetic.

The fix is a **sliding baseline**: align `(j, j+Δ)` for every `j` at fixed Δ.
Each tile is then seen at many defocus levels with its depth held fixed, and
each defocus level is seen across many depths. All numbers below come from
per-tile displacements measured directly between the two frames of a pair; the
tile grid is registered into each frame through a smoothed model, but no
displacement is composed from another displacement, so AGENTS.md rule 6 holds.

### 1.2 The discriminating statistics, stated before they were computed

* **S1** — γ, from a two-way fixed-effects regression of per-tile residual
  magnitude on `|c − w|`, where `c` is the pair midpoint and `w` the tile's own
  best-focus frame. Tile and pair fixed effects absorb "this tile is hard" and
  "this pair aligns badly", so γ is identified only from the depth×pair-position
  interaction. Under (b), γ > 0. Under (a), γ = 0 because depth is a pure tile
  effect and the tile dummies absorb it.
* **S2** — Spearman correlation between the per-tile radial scale anomaly
  `dg = e_rad / |u − o|` and depth. Cause (a) *is* a depth-organised radial
  scale anomaly, so under (a) this is non-zero and monotone; under (b) it is not.
* **S4** — does the aligner *censor* by defocus? A tile that fails the
  correlation gate contributes no residual.
* **S5** — the brief's own prediction, computed directly: mean residual of tiles
  in focus in both frames against tiles far from focus, within each baseline.
* **S6** — added after S1/S5 resolved, to answer the question §3.4.2 actually
  cares about: is the effect a peak **bias** or a peak **variance**? Regress the
  *radial* residual component on the signed blur asymmetry
  `a = |mov − w| − |ref − w|`, tangential component as placebo.
* **S7** — split the per-tile residual into a repeatable part and a scatter
  part, with `|mean|²` de-biased by `scatter²/n`.

### 1.3 Controls, before any result

Six synthetic stacks, each built by warping **one real frame** so texture and
sensor noise are real and only the cause is planted. Drift −8.74e-4/frame to
match M3 §4's −1.835% over 21 frames; κ = 0.20; blur 0.35 px/frame; 14 frames.
The planted depth field is non-affine (ramp plus three Gaussian blobs) because
an affine depth field is exactly absorbable by an affine motion model and would
test nothing. Fresh sensor noise is drawn on every frame *after* blurring, so
blurred cases are not also quieter.

| case | contains | S1 γ | S2 ρ | S6 b_rad |
| --- | --- | --- | --- | --- |
| `N0-integer` | nothing (whole-pixel shifts) | +0.000003 ± 0.000032 quiet | +0.109 quiet | −0.00001 ± 0.00004 quiet |
| `N1-null` | *(intended: nothing)* | +0.0084 **fires** | +0.040 quiet | −0.052 ± 0.034 quiet |
| `P0-depth-only` | cause (a) | +0.0021 quiet | **−0.834 fires** | **+0.080 fires** |
| `P2-blur-only` | cause (b), symmetric PSF | **+0.0627 fires** | −0.099 quiet | +0.003 ± 0.013 quiet |
| `P1-both` | (a) + (b) | **+0.0688 fires** | **−0.706 fires** | **+0.077 fires** |
| `P3-asym-psf` | (b) + field-dependent asymmetric PSF | **+0.0650 fires** | **+0.198 fires** | **−0.039 fires** |

All three statistics pass their planted-cause controls (`out/controls.txt`).
Three things in this table are worth more than the pass:

**The null that was not a null.** `N1-null` was pre-registered as a null and is
not one. It applies one global similarity with no defocus anywhere, yet S1 fires
on it. The cause is the interpolator: **bilinear resampling attenuates high
spatial frequencies by an amount that depends on the sub-pixel phase**, so a
warped synthetic frame carries a per-tile, per-frame *sharpness* modulation that
nobody planted — median profile peakiness 0.082 against 0.024 for the same stack
shifted by whole pixels. There really is frame-varying blur in `N1-null`; the
statistic was right and the null was wrong. `N0-integer` was added afterwards,
touches no interpolator, and is the floor quoted above. This generalises beyond
this experiment: **any synthetic alignment benchmark built by resampling one
frame has this bias baked into it** — MEASURED, and worth carrying into any
future alignment work in this project.

**S6 is less specific than it was designed to be.** It was meant to isolate an
asymmetric PSF. It also fires on `P1-both`, which has a strictly symmetric
Gaussian PSF. The reason is structural: depth-dependent magnification displaces
tile `i` in pair `(j, j+Δ)` by `gstep·Δ·κ·dz_i·r_i`, a pair scalar times a tile
scalar times radius — a depth×pair *interaction* that additive fixed effects
cannot absorb and that correlates with `|mov−w| − |ref−w|`, since both are driven
by `w_i`. So a *positive* S6 does not distinguish an asymmetric PSF from cause
(a). A *null* S6 still rules out both at the planted amplitude, which is the
direction this result needs. The load-bearing control is `P2-blur-only`: heavy
symmetric defocus, S1 firing at +0.063, and S6 flat at +0.003 ± 0.013.

**A whole class of asymmetric PSF is invisible here, by construction.** If the
PSF centroid walks *signed-linearly* with defocus — `c·(k − w)·r` — then tile `i`
in pair `(j, j+Δ)` is displaced by `c·((j+Δ−w) − (j−w))·r = c·Δ·r`: constant per
pair, linear in radius, i.e. **exactly a scale change**, absorbed by the
similarity fit and leaving no residual at all. DERIVED. This is why the planted
`P3` control uses an unsigned walk (outward, growing with the amount of blur),
and why S6 regresses on `|mov−w| − |ref−w|` rather than on `mov − ref`. A
signed-linear field-dependent PSF cannot be detected by *any* residual-based
method, including this one.

### 1.4 Two depth labels, and their disagreement

The primary label is a per-tile focus profile measured on the **registered**
tile grid: for each tile and each frame, the ring-difference contrast at that
tile's canonical position warped into that frame. `w` is the argmax.

| stack | peakiness median | frac > 0.10 | w sd | w range | Spearman vs CLI index map | median abs diff |
| --- | --- | --- | --- | --- | --- | --- |
| 109MSDCF | 0.463 | 1.000 | 1.45 | 6.9–12.7 | 0.922 | 0.42 frames |
| 119MSDCF | 0.545 | 1.000 | 6.83 | 1.6–31.2 | 0.993 | 0.90 frames |
| coffee-bean | 0.929 | 0.792 | 26.35 | 1.8–104.0 | 0.545 | 3.83 frames |

The CLI's `--index-map` is computed on an **unaligned** stack, so it is smeared
radially by exactly the drift being measured — tens of plane px at the corner.
It is a cross-check, not a calibration, and the coffee-bean disagreement (ρ =
0.545) is expected given that stack's 4.6% total drift.

**109MSDCF's depth range is only 1.45 frames of standard deviation.** That is
enough for the regression, but it is the reason the within-pair contrast in
§1.6 has no groups for that stack: at any single `j`, essentially every tile is
on the same side of focus.

### 1.5 S1 — the residual grows with defocus mismatch

γ is px of residual per frame of defocus mismatch, with tile and pair fixed
effects, cluster-robust SE by tile, `p_perm` from 999 label permutations and
`p_torus` from 95 cyclic shifts of the depth field over the 12×8 grid. The torus
null preserves both the marginal distribution and the spatial autocorrelation of
the depth field and destroys only the causal coupling — the placebo §5 item 6
asks for. `ident` is the fraction of the regressor's variance surviving two-way
demeaning; below 0.02 the coefficient is a ratio of two small numbers and is not
quoted.

| stack | model | γ | ±SE | ident | p_perm | p_torus | n |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 109MSDCF | plain | **+0.05966** | 0.01211 | 0.143 | 0.0010 | 0.0104 | 7210 |
| 109MSDCF | + contrast, peak, radius | +0.06053 | 0.01334 | 0.143 | 0.0010 | 0.0104 | 7210 |
| 119MSDCF | plain | **+0.04522** | 0.00370 | 0.675 | 0.0010 | 0.0104 | 15599 |
| 119MSDCF | + contrast, peak, radius | +0.05054 | 0.00553 | 0.675 | 0.0010 | 0.0104 | 15599 |
| coffee-bean | plain | +0.00263 | 0.00203 | 0.620 | 0.1350 | 0.1042 | 43907 |
| coffee-bean | + contrast, peak, radius | +0.00633 | 0.00250 | 0.620 | 0.0020 | 0.0104 | 43907 |

γ is **unchanged** by controlling for tile contrast, correlation peak height and
field radius. That matters: the obvious deflationary reading of a defocus effect
is that blurred tiles are low-contrast and low-contrast tiles are just noisier.
Holding contrast and peak height fixed does not move γ, so this is not a
contrast artifact — MEASURED.

Against the `N0-integer` floor of +0.000003 ± 0.000032, γ on the two clean
stacks is 1400–1900× the floor's own standard error. The floor is four orders of
magnitude below the measured effect.

Effect size: γ times the typical `|c − w|` accounts for **69% / 105% / 8%** of
the mean per-tile residual for the three stacks (`out/measure.txt` §6).

### 1.6 S5 — the brief's own prediction, and the number that decides it

Tiles in focus in both frames (`|c − w| ≤ 2`) against tiles far from focus
(`|c − w| ≥ 8`), within each baseline:

| stack | Δ | n in focus | residual in focus | n far | residual far | gap |
| --- | --- | --- | --- | --- | --- | --- |
| 109MSDCF | 1 | 378 | **0.172** | 442 | 0.689 | +0.517 |
| 109MSDCF | 2 | 372 | 0.179 | 356 | 0.890 | +0.712 |
| 109MSDCF | 4 | 341 | 0.271 | 222 | 0.905 | +0.634 |
| 109MSDCF | 8 | 305 | 0.559 | 69 | 0.948 | +0.390 |
| 119MSDCF | 1 | 385 | **0.144** | 1681 | 0.247 | +0.103 |
| 119MSDCF | 4 | 381 | 0.309 | 1422 | 0.915 | +0.606 |
| 119MSDCF | 8 | 363 | 0.361 | 1127 | 1.315 | +0.954 |
| 119MSDCF | 16 | 301 | 0.508 | 578 | 1.417 | +0.909 |
| 119MSDCF | 30 | 22 | 1.003 | 22 | 2.382 | +1.379 |
| coffee-bean | 1 | 371 | 0.443 | 8521 | 0.366 | **−0.077** |
| coffee-bean | 8 | 318 | 2.680 | 6513 | 3.183 | +0.503 |
| coffee-bean | 16 | 229 | 2.454 | 2553 | 3.591 | +1.137 |

**In-focus tiles at Δ=1 align at 0.144–0.172 px — at or below M3 §0's 0.19 px
estimator noise floor.** M3's published 0.703 px at k=1 was an average over all
tiles regardless of focus. There is no residual left to explain for tiles that
are actually in focus in both frames. This is prediction (b) verbatim and the
opposite of prediction (a), which requires the residual to persist for
well-focused tiles.

The gap is not an artifact of which pairs or which tiles are being compared:

| stack | weighted gap | p_torus | within the same **pair** | p | within the same **tile** | p |
| --- | --- | --- | --- | --- | --- | --- |
| 109MSDCF | +0.6015 | 0.0417 | *(no pair has both, see §1.4)* | — | **+0.5993** | 0.0417 |
| 119MSDCF | +0.5790 | 0.0104 | **+0.6672** (160 groups) | 0.0104 | **+0.4602** (426 groups) | 0.0104 |
| coffee-bean | +0.2496 | 0.0208 | +0.3359 (258 groups) | 0.0208 | +0.2408 (421 groups) | 0.0208 |

The within-pair contrast compares tiles inside a single frame pair, so the two
groups share the same global motion, the same fit, and the same pair of frames.
The within-tile contrast compares the *same tile* across pairs, so the two groups
share texture, contrast, and field position exactly. Both survive. On 119MSDCF —
the stack with the widest depth spread and the best-identified regressor — the
within-pair gap is +0.667 px against a torus null p of 0.010.

### 1.7 S2 — cause (a) is not there

| stack | ρ(dg, w) | p_torus | ρ(res, \|w−mid\|) | p_torus | sd_rad | sd_tan | anisotropy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 109MSDCF | +0.066 | 0.229 | −0.013 | 0.542 | 0.853 | 0.341 | 2.498 |
| 119MSDCF | +0.135 | 0.490 | +0.434 | 0.021 | 0.926 | 0.553 | 1.673 |
| coffee-bean | −0.100 | 0.490 | −0.235 | 1.000 | 1.943 | 1.397 | 1.390 |

Nothing, on the statistic that fires at ρ = −0.834 and −0.706 when cause (a) is
planted. The sign is not even consistent across stacks.

Anisotropy (sd_rad/sd_tan) is **not** evidence either way and is reported only
so it is not mistaken for evidence: the controls give 1.522 for `N0-integer`,
4.711 for `N1-null`, 4.432 for `P0-depth-only` and 1.873 for `P2-blur-only`,
i.e. anisotropy is *highest* where there is no blur and lowest on the two cases
that do have it. It tracks how much of the residual is radial noise, not whether
depth-dependent magnification exists.

### 1.8 S6 and S7 — bias or variance, and why the lens plugin still dies

This is the part §3.4.2 actually turns on. A **symmetric** defocus PSF does not
move a correlation peak; it flattens it, which inflates the *variance* of the
estimate. A peak that is genuinely *displaced* requires an asymmetric,
field-dependent PSF — and that, not "blur matters", is what would make per-lens
PSF modelling into real computation.

| stack | b_rad (radial) | ±SE | p_torus | b_tan (placebo) | ±SE | n |
| --- | --- | --- | --- | --- | --- | --- |
| 109MSDCF | +0.03337 | 0.01825 | 0.094 | +0.00876 | 0.00804 | 7210 |
| 119MSDCF | **+0.00068** | 0.01088 | 0.969 | −0.00354 | 0.00695 | 15599 |
| coffee-bean | +0.01986 | 0.01165 | 0.052 | +0.00392 | 0.01201 | 43907 |
| *(P2, planted symmetric blur)* | +0.00295 | 0.01259 | 0.813 | −0.00809 | — | — |
| *(P3, planted asymmetric PSF)* | −0.03919 | 0.01342 | 0.010 | −0.01195 | — | — |
| *(P1, planted cause (a) + blur)* | +0.07722 | 0.01306 | 0.010 | −0.00074 | — | — |
| *(N0, real-data floor)* | −0.000012 | 0.000041 | 0.844 | +0.00001 | — | — |

**No real stack fires.** 119MSDCF — the stack with the strongest γ, the widest
depth spread and ident = 0.675 — is flat at +0.0007 ± 0.0109 against planted
signals of ±0.039 to +0.077. 109MSDCF and coffee-bean are marginally positive
(p = 0.094 and 0.052) but neither clears the pre-stated bar of `p_torus ≤ 0.05`
**and** `|b| > 2·SE`.

Read as an exclusion, and being explicit about power: 119MSDCF's 95% interval is
[−0.021, +0.022] against γ = +0.045. So a radially organised directional peak
displacement can account for **at most about half** of the measured defocus
effect on that stack, and the point estimate is 1.5% of it. On 109MSDCF the
interval [−0.003, +0.069] against γ = +0.060 is much weaker and excludes little.
UNVERIFIED: whether a directional component of order 0.02 px/frame exists on
109MSDCF and coffee-bean. Two of three stacks lean positive, and that should be
retested with more baselines before anyone concludes there is nothing there.

S7 confirms the same picture from the other direction. Within each tile and
defocus bin, the residual's repeatable part and its scatter part are both
averages over the *same* set of pairs — this is not a spatial-sd-versus-
temporal-sigma comparison, the error this project has made twice:

| stack | \|c−w\| bin | bias px | scatter px | bias/scatter |
| --- | --- | --- | --- | --- |
| 109MSDCF | 0–2 | 0.266 | 0.629 | 0.423 |
| 109MSDCF | 8–16 | 0.591 | 1.037 | 0.570 |
| 119MSDCF | 0–2 | 0.257 | 0.443 | 0.580 |
| 119MSDCF | 16+ | 0.684 | 1.117 | 0.612 |

Both parts grow with defocus and the scatter dominates throughout. There *is* a
repeatable per-tile component, but it is not radially organised (S2, S6) and it
does not flip with which frame is blurrier (S6).

**The signature match, which is the strongest single piece of evidence here:**

| statistic | `P0` depth-only | `P2` blur-only, symmetric | `P3` asymmetric PSF | 109MSDCF | 119MSDCF | coffee-bean |
| --- | --- | --- | --- | --- | --- | --- |
| S1 γ | quiet | **fires** | **fires** | **fires** | **fires** | **fires** (controlled) |
| S2 ρ | **fires** −0.83 | quiet | **fires** +0.20 | quiet | quiet | quiet |
| S6 b_rad | **fires** +0.080 | quiet | **fires** −0.039 | quiet | quiet | quiet |

All three real stacks match the `P2-blur-only` column on all three statistics,
and match no other column. ARGUED, from MEASURED components.

**Consequence for §3.4.2.** The gating question was: is a field-dependent
defocus PSF biasing the aligner? Measured answer: **no evidence of one**, on the
statistic that finds one when it is planted, in the stack where that statistic
has the most power. The residual is defocus-driven, but through peak
*degradation* rather than field-organised peak *displacement*. So the last
candidate for making a lens plugin into genuine per-lens computation does not
survive contact with the data, and the lens profile stays a data file — ARGUED.

The actionable finding is cheaper than a plugin: the aligner already has
everything it needs to fix this. `|c − w|` is computable from the focus measure
the stacker computes anyway, and S4 shows the aligner is *already* censoring in
the right direction but not enough.

### 1.9 S4 — the aligner is already censoring, which makes these numbers conservative

| stack | overall reject rate | slope per frame of mismatch | rate at \|c−w\|<2 | at 8–16 |
| --- | --- | --- | --- | --- |
| 109MSDCF | 0.201 | +0.02380 ± 0.00405 | 0.132 | 0.255 |
| 119MSDCF | 0.021 | +0.00225 ± 0.00066 | 0.005 | 0.034 |
| coffee-bean | 0.294 | +0.00168 ± 0.00037 | 0.254 | 0.299 |

Tiles that fail the correlation gate contribute no residual, and rejection rises
with defocus on all three stacks — the slope is positive and several σ from zero
in every case. Censoring therefore removes the *worst*-affected tiles from the
sample, so S1 and S5 both understate the effect — DERIVED. Every number in Part
1 is a lower bound in that sense.

119MSDCF barely censors at all (2.1% overall), which is a second reason its S1
and S5 numbers are the ones to trust: its sample is very nearly uncensored.

---

## Part 2 — how big the halo actually is

Pure arithmetic on the fitted per-frame similarity transforms, no image
processing. For each output tile, the bounding box of `S_k^{-1}(tile)` over all
frames `k`, expanded to whole pixels and clipped to the plane.

### 2.1 The correction to B1

| stack | drift | **corner halo** | halo, smoothed model | Euclidean displacement | sensor px |
| --- | --- | --- | --- | --- | --- |
| 109MSDCF | −1.8350% | **32.39** | 32.56 | 39.35 | 64.8 |
| 119MSDCF | −1.0291% | **19.42** | 18.76 | 23.60 | 38.8 |
| coffee-bean | −4.5745% | **89.23** | 83.82 | 108.22 | 178.5 |

**§3.4.1 B1's "39 plane pixels at the frame corner" is the Euclidean corner
displacement, not the halo** — VERIFIED, and it reproduces to 39.35 px on this
stack, so the arithmetic behind B1 was right and only its interpretation was
loose. A halo is a rectangle expansion in x and y, so the comparable quantity is
`max(|dx|,|dy|) = |g|·max(w,h)/2 = 0.018350 × 1758 = 32.3 px`, not
`|g|·√(w²+h²)/2 = |g|·2113 = 38.8 px`. B1 overstates the halo by the aspect
factor 2113/1758 = 1.202. This does not change B1's conclusion; it changes its
number.

### 2.2 The halo is a function of radius

109MSDCF, 128 px tiles:

| radius (plane px) | mean halo | max halo | n |
| --- | --- | --- | --- |
| 394 | 5.39 | 8.82 | 67 |
| 719 | 10.72 | 13.52 | 66 |
| 1102 | 17.02 | 20.55 | 66 |
| 1433 | 21.84 | 26.46 | 67 |
| 1850 | 28.73 | 31.24 | 67 |

`halo = 0.015971·r − 0.740 px`, Spearman ρ = 0.963. The corresponding fits are
`0.008969·r` for 119MSDCF and `0.039854·r` for coffee-bean, both at ρ ≥ 0.963.

| stack | tile | min | median | mean | max | centre | corner | max/median |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 109MSDCF | 64 | 0.25 | 18.20 | 18.02 | 31.24 | 0.25 | 31.03 | 1.72 |
| 109MSDCF | 128 | 0.22 | 18.15 | 17.84 | 31.24 | 0.22 | 31.03 | 1.72 |
| 109MSDCF | 256 | 0.22 | 17.13 | 17.01 | 28.89 | 0.22 | 28.68 | 1.69 |
| 119MSDCF | 128 | 0.44 | 10.40 | 10.23 | 18.80 | 0.44 | 18.80 | 1.81 |
| coffee-bean | 128 | 3.04 | 47.42 | 46.57 | 83.63 | 3.04 | 83.36 | 1.76 |

**Corner:centre ratio is 31.03 / 0.22 = 141×** at 128 px tiles — MEASURED. The
ratio is essentially unbounded in principle, since the halo goes to zero at the
scale centre; 141 is what a 128 px tile grid resolves. The *robust* shape
statistic is max/median, which is **1.69–1.83 across all three stacks and all
three tile sizes** — remarkably stable, and the number to quote if a single
figure for "how non-uniform is the halo" is wanted.

### 2.3 Does a scalar `halo()` survive? No — but not for B1's reason

A scalar must be the max over the frame. Within one stack that is cheap:

| stack | tile | scalar halo | mean needed | tiles needing <10% of it | gather area waste |
| --- | --- | --- | --- | --- | --- |
| 109MSDCF | 64 | 31.24 | 18.02 | 2.1% | 1.56× |
| 109MSDCF | 128 | 31.24 | 17.84 | 2.3% | 1.34× |
| 109MSDCF | 256 | 28.89 | 17.01 | 2.9% | 1.17× |
| 119MSDCF | 128 | 18.80 | 10.23 | 2.3% | 1.24× |
| coffee-bean | 128 | 83.63 | 46.57 | 1.9% | 1.73× |

Only about 2% of tiles need less than a tenth of the scalar, so the waste is not
concentrated in a few tiles near the centre — it is spread thinly across the
whole frame, which is why the area penalty is modest. **1.17–2.12× is not an
argument that would kill an interface.** If the only cost of `halo() -> usize`
were this, B1 would be over-claiming: at the tile sizes this stacker actually
uses, a scalar halo wastes about a third of the gather area, which is a real but
ordinary inefficiency.

The argument that does work is **stack dependence**. `halo() -> usize` is
answered by the plugin without seeing the stack, so it is one constant per lens
and must cover the worst stack that lens will ever shoot:

| stack | corner halo when only the first N frames are used |
| --- | --- |
| | N=5 / N=10 / N=20 / N=30 / N=50 / N=100 |
| 109MSDCF | 8.27 / 16.84 / 31.38 / 32.39 / 32.39 / 32.39 |
| 119MSDCF | 2.09 / 6.19 / 12.28 / 18.30 / 19.42 / 19.42 |
| coffee-bean | 0.87 / 4.26 / 18.61 / 32.40 / 56.32 / 89.23 |

The halo is **not a property of the lens. It is a property of the stack** — of
how far the focus rail travelled, which is the photographer's choice, made after
the plugin was compiled. Three stacks from the same camera need 19.4, 32.4 and
89.2 plane px. A single scalar serving all three must be 89.23 px, and then:

| stack | tile | needed (mean) | scalar | gather area waste | vs per-stack scalar |
| --- | --- | --- | --- | --- | --- |
| 109MSDCF | 64 | 18.02 | 89.23 | **5.75×** | 1.56× |
| 109MSDCF | 128 | 17.84 | 89.23 | **3.48×** | 1.34× |
| 119MSDCF | 64 | 10.28 | 89.23 | **8.14×** | 1.43× |
| 119MSDCF | 128 | 10.23 | 89.23 | **4.25×** | 1.24× |
| coffee-bean | 128 | 46.57 | 89.23 | 1.86× | 1.73× |

An 8× gather-area penalty on a 33-frame stack, to accommodate a 105-frame stack
that is not being processed, is not a defensible interface — ARGUED from
MEASURED numbers.

**Ruling: `halo() -> usize` does not survive; `source_roi(out, &Warp) -> Roi`
is correct.** B1's conclusion stands. Its stated reason (per-tile variation
within a frame) is the weaker of the two available reasons, at 1.2–2.1×. The
strong reason is that the required halo depends on the warp, and a scalar is
answered before the warp exists. Since `source_roi` takes the `&Warp`, it gets
both properties for free.

### 2.4 Is it stack-dependent? Yes, in magnitude; no, in shape

| stack | total drift | corner halo | max/median at 128 px | per-stack area waste |
| --- | --- | --- | --- | --- |
| 109MSDCF | −1.835% | 32.39 px | 1.72 | 1.34× |
| 119MSDCF | −1.029% | 19.42 px | 1.81 | 1.24× |
| coffee-bean | −4.575% | 89.23 px | 1.76 | 1.73× |

The absolute halo scales with total drift, which varies 4.4× across three stacks
from one camera. The *shape* — how much more the corner needs than the median —
is stable at 1.72–1.81. So a lens profile could legitimately supply the shape;
it cannot supply the magnitude.

Corner halo divided by total drift is 17.65 / 18.87 / 19.51 px per percent
across the three stacks, a 10% spread against a 4.4× spread in the halo itself.
The residual spread is expected: the scale centre is not at the frame centre
(measured at (−7.3, −56.1), (−78.6, −173.4) and (+153.2, −221.5) plane px), so
the worst corner is a slightly different distance from it in each stack.

---

## What is still not verified

1. **coffee-bean's γ is quiet in the plain model** (+0.0026 ± 0.0020, p_torus
   0.104) and its S5 gap is **negative at Δ=1 and Δ=2**. It only fires once
   contrast/peak/radius are controlled. The likely mechanism — at Δ=1 in a
   105-frame stack a far-from-focus tile is *equally* blurred in both frames, so
   there is no blur asymmetry, and heavily blurred pairs correlate very well —
   is a **hypothesis, not a measurement**. `|c − w|` measures the pair's mean
   defocus, not the asymmetry between the two frames, and asymmetry saturates
   once `|c − w| > Δ/2`, so a linear-in-`|c−w|` model is misspecified at large
   defocus. Not fixed here, because choosing a functional form after seeing the
   data is how the previous retraction happened.
2. **coffee-bean's direct-to-frame-0 fits are poor** — 101 of the 104
   direct pairs produced a fit at all, and those that did used a median of 18 of
   96 tiles at 4.61 px rms, against 60 tiles and 0.78 px for 109MSDCF. Every
   coffee-bean number carries that caveat. See "The reference-frame failure"
   below; it is a real finding but it degrades this stack's numbers.
3. **(a) and (b) are not mutually exclusive**, and this measurement bounds (a)
   rather than excluding it. S2's torus null band is wide — `N1-null` reached
   |ρ| = 0.247 by chance — so an (a) contribution below roughly ρ = 0.25 would
   not have been seen. What is measured is that (a) is not the *dominant* cause.
4. **S6's exclusion is strong on one stack and weak on two.** 119MSDCF excludes
   a directional component above ~0.022 px/frame. 109MSDCF (p = 0.094) and
   coffee-bean (p = 0.052) both lean positive and exclude little. The
   "no field-dependent PSF" conclusion rests mostly on 119MSDCF.
5. **A signed-linear field-dependent PSF is undetectable by construction** (§1.3)
   — it is exactly a scale change and is absorbed by the similarity fit. This
   measurement cannot rule that class out and neither can any other
   residual-based method.
6. **S6 is not specific** — it fires on cause (a) as well as on an asymmetric
   PSF (§1.3). Its null on real data is what is being used, not a positive.
7. **109MSDCF's depth spread is 1.45 frames**, too narrow for a within-pair S5
   contrast. That stack's S5 rests on the within-tile contrast alone.
8. **The tile grid inset differs from M3's.** `grid=m6` insets by 56 px so warped
   tiles stay in-plane; at k=1 it gives g = −7.36e-4 and rms 0.519 px where M3's
   grid gives −6.04e-4 and 0.703 px. Both are in the CSVs. The halo numbers use
   `grid=m3`, exactly M3's published grid.
9. **Anchor placement uses a smoothed model.** Tile anchors are placed by a
   robust polynomial smooth of the per-frame fit parameters, which costs a few
   px of anchor accuracy on coffee-bean. Displacements are still measured
   directly between frames; only the starting position is modelled. The raw fits
   are in the CSVs so the difference is auditable.
10. **No lens was varied.** All three stacks are one camera and, as far as this
    measurement knows, one lens. The claim "a lens plugin stays a data file" is
    an inference from the *absence of a field-dependent signature* on this lens,
    not from a comparison across lenses.

## Contradictions with existing SYNTHESIS facts

* **Fact 18** (the 0.6–1.3 px residual is unexplained) is now explained. It is
  defocus-driven peak degradation. Not a contradiction — a resolution.
* **§3.4.1 B1's "~39 plane pixels at the frame corner"** is superseded. 39.35 px
  is the Euclidean corner *displacement*; the corner *halo* is 32.39 px. B1's
  conclusion survives, its number does not.
* **§3.4.2's conditional** — "if the cause is (b), then a field-dependent
  defocus PSF is biasing the aligner, and modelling that PSF per lens is the one
  remaining candidate for genuine per-lens computation" — has a **false
  antecedent-to-consequent step**. The cause is (b), but the mechanism is
  symmetric peak degradation, not field-dependent peak displacement. The
  conditional's two halves come apart, and the lens plugin dies anyway.
* **AGENTS.md rule 6, "always align to a fixed reference"**, is qualified. On the
  105-frame stack, direct-to-frame-0 alignment degrades badly and in places fails
  outright — 3 of 104 pairs produced no fit, and those that did used a median of
  18 of 96 tiles at 4.61 px rms — because frames 0 and ~90 share almost no
  correlatable in-focus content (fact 4). The rule is right for 22 frames and
  broken at 105. This measurement worked around it with a smoothed anchor model
  rather than by chaining.

## The reference-frame failure, stated on its own

Because it is a result, not an inconvenience: **on a 105-frame focus bracket,
there is no single frame that can serve as an alignment reference for the whole
stack.** Frames at opposite ends of the bracket share almost no in-focus content,
so the correlation gate rejects most tiles and the fit degrades from 0.78 px rms
on 60 tiles (22-frame stack) to 4.61 px rms on 18 tiles, with outright failures
at the far end. This is a direct consequence of fact 4 and it means any
production aligner needs a strategy — an anchor ladder, a smoothed model, or an
all-pairs fit — for stacks beyond a few tens of frames. MEASURED.

## How to quote this

* "The alignment residual is defocus-driven; in-focus tiles align at the
  estimator noise floor" — MEASURED, S5, two stacks, within-pair and within-tile
  controlled.
* "There is no evidence of a field-dependent asymmetric PSF biasing the aligner"
  — MEASURED null on 119MSDCF, weak on the other two. Do not quote as
  "there is no such PSF"; quote as "not at an amplitude that would explain the
  residual".
* "The lens plugin stays a data file" — ARGUED, from the above. One lens.
* "The corner halo is 32.4 plane px on a 22-frame, −1.835% stack" — MEASURED.
  Always quote the drift with it; the halo is a property of the stack.
* "A scalar `halo()` costs 4–8× in gather area" — DERIVED, and only across
  stacks. Within one stack it costs 1.2–2.1×.

## Reproduction

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
cd C:\dev\blog\death-of-software\projects\strehl\experiments\m3-drift
cargo build --release
.\target\release\m3-drift.exe --synthetic C:\dev\macro\test\109MSDCF
.\target\release\m3-drift.exe --m6 C:\dev\macro\test\109MSDCF    ..\m6-residual-halo\data\109MSDCF    --iso 160 --deltas 1,2,4,8
.\target\release\m3-drift.exe --m6 C:\dev\macro\test\119MSDCF    ..\m6-residual-halo\data\119MSDCF    --iso 50  --deltas 1,2,4,8,16
.\target\release\m3-drift.exe --m6 C:\dev\macro\test\coffee-bean ..\m6-residual-halo\data\coffee-bean --iso 50  --deltas 1,2,4,8,16,32
.\target\release\m3-drift.exe --m6-control C:\dev\macro\test\109MSDCF ..\m6-residual-halo\data\control --iso 160 --n 14 --deltas 1,2,4
cd ..\m6-residual-halo
python m6_selftest.py
python m6_peakiness.py
python m6_controls.py | Out-File -Encoding utf8 out\controls.txt
python m6_measure.py  | Out-File -Encoding utf8 out\measure.txt
```

Winner-index maps (used only as the §1.4 cross-check) need the workspace CLI.
It was built once at commit `037d966e03f7931d6b2311585dc3147ee1d9233b` and the
binary copied to `experiments/m6-residual-halo/bin/strehl-m6.exe` (SHA-256
`4FD1F7E061E530D26FA137F3BDE56DF1BF51A8017E0FD72444A0754021244F6D`) so that
concurrent edits under `crates/` could not change it mid-measurement:

```powershell
cargo build --release -p strehl-cli
Copy-Item target\release\strehl.exe experiments\m6-residual-halo\bin\strehl-m6.exe -Force
.\bin\strehl-m6.exe stack C:\dev\macro\test\109MSDCF --out out\109MSDCF-stack.tiff --index-map out\109MSDCF-index.tiff
```

Constants: `TILE_PX=128`, grid 12×8, plane 3516×2344, `N_PERM=999`, 95 torus
shifts, `SEED=20260822`, `PEAKINESS_MIN=0.10`. Runtime: ~2.5 h for the three
`--m6` runs, ~25 min for the controls, ~4 min for the Python.

`C:\dev\macro` and `D:\macro-dark-frames` are read-only and nothing in this
measurement writes to either; all output goes to `experiments/m6-residual-halo/`.

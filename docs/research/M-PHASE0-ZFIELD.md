# M-PHASE0-ZFIELD — A5 survives phase 0, and the substrate nearly killed it by artefact

Lane: `experiments/M-PHASE0-ZFIELD/`. Registered at `6b0b08c2` before any statistic
was computed; Amendment 1 registered at `4c6d…` before any census statistic was
computed. Gates **A5**, `docs/proposals/2026-08-sota-path.md` lines 579–676.

## 1. Headline

**A5 survives its phase-0 kill gate, and it survives on a margin that the substrate
itself was hiding.**

Read naively, the eight M66 response cubes say kill: the median pixel's depth is
already placeable to **1.9%** WINNABLE against a 2% kill bar, because per-pixel σ_z is
*small* — median 0.023 to 0.599 frames against a corpus DOF/2 of 1.5 to 3.0 frames. On
that reading the surface has nothing to add, because the per-pixel estimate already
clears the admission bar almost everywhere.

That reading is wrong, and the reason is a property of the substrate, not of A5. M66's
response is smoothed over a 27×27 box and then a 17×17 box. The shipping estimator's
fine field is 5×5 (`FINE_WINDOW_RADIUS = 2`, `focus.rs:145`; both operators are
Tenengrad, `focus.rs:782–783`). Cascading the two boxes and comparing sums of squared
kernel weights, the shipping operator's response noise is **6.83×** larger than the
substrate's. Re-running the census at that noise level moves the verdict from KILL to
**SURVIVE**: WINNABLE rises from 1.91% to **14.02%** at DOF/2 = 1.5 and from 1.13% to
**10.12%** at DOF/2 = 3.0.

So the honest verdict is **SURVIVE, NOT ROBUST**, and the lane's most useful output is
the near-miss: a census that read its own substrate at face value would have killed a
proposal item on a smoothing artefact.

## 2. What was registered, and what it asked

A5's kill text: *"if σ_z is so large at corpus step sizes that the surface never beats
the per-pixel estimate outside already-easy regions, kill it for one sprint's cost."*

The preregistration turned that into a three-way partition of every pixel against the
half-width the surface would actually be used at — A5's admission rule is
`|z_i − z(x,y)| ≤ DOF/2` in frame-index units:

| Stratum | Definition |
| --- | --- |
| EASY | σ_z(per-pixel) ≤ DOF/2 — per-pixel already decides; the "already-easy region" the kill text excludes |
| WINNABLE | σ_z(per-pixel) > DOF/2 ≥ σ_z(surface) — the band A5 exists to serve |
| LOST | σ_z(surface) > DOF/2 — neither estimator decides |

Registered bar, fixed before measurement: **KILL** below 2% median WINNABLE, **SURVIVE**
at or above 10%, **INCONCLUSIVE** between. The eight M66 cubes are corpus-density
stacks, so the matched half-widths are the corpus pair, DOF/2 ∈ {1.5, 3.0}; reading them
against the recommended-step pair {0.65, 0.75} compares a corpus σ_z against a
recommended-step DOF and is a units error, which §Z5a records.

## 3. The instrument had to be rebuilt before it could measure anything

The controls ran before the census and found three defects. All three are disclosed in
Amendment 1 and none survived into the census.

**The registered σ_z was derived at a special point and applied everywhere.** §4 derived
`σ_z = σ_r/(|D|·√2)` at the symmetric point where the sub-frame offset is zero, then
used it at every pixel. Carrying the general offset through adds `√(1 + 12x*²)`, which
averages `√2` and reaches `2` at an interval edge. That is my error, not a finding.

**Even corrected, first-order propagation is optimistic by 1.34×.** Against a planted-ẑ
truth with a known ramp and a known 2-frame step, over 96 noise realisations:

| σ_z estimator | predicted | empirical sd | ratio |
| --- | --- | --- | --- |
| as registered | 0.1454 | 0.2634 | **0.552** |
| general-offset correction | 0.1965 | 0.2634 | **0.746** |
| parametric bootstrap | 0.3000 | 0.2634 | **1.139** |

**And the registered estimator called pure noise confidently placeable.** An argmax over
noise *is* a spike, and a spike reports high curvature, so the analytic form reported
high confidence where there was no peak at all:

| cube | analytic median σ_z | analytic EASY | bootstrap median σ_z | bootstrap EASY |
| --- | --- | --- | --- | --- |
| pure noise, n = 22 | 0.191 frames | **90.2%** | 5.85 frames | **0.24%** |
| pure noise, n = 105 | 0.142 frames | **97.9%** | 29.66 frames | **0.00%** |

§8 had registered the escape hatch — *"the lane must move to a Monte-Carlo σ_z"* — and it
fired. The replacement smooths each measured curve to a working truth, adds fresh noise
at that pixel's own measured σ_r, and re-runs **the real estimator**, so it inherits every
discreteness rather than modelling it. One mechanism repaired both defects; the separate
peak-reality gate that was contemplated is unnecessary. Its 1.139 ratio errs
**conservative**, which is a bias against A5, so it cannot manufacture the survive verdict
in §5.

**σ_r itself is trustworthy.** The 5-point 4th-difference MAD estimator recovers planted
noise to within **0.74%** across a 4× range. C3 was registered as an agreement test
against M69's two estimators and failed — this lane reads 0.0179 where M69's
Savitzky-Golay arm reads 0.0426 and its structure-function arm 0.0810. Agreement was the
wrong test: the three average residuals over 5, 11 and 12 frames respectively, so on a
real focus curve they must disagree and the widest span must read highest, which is the
observed ordering. Converted to a truth test, M69's structure arm falls from 2.28× to
1.14× as planted noise comes to dominate real curve structure, confirming the diagnosis.

All eight controls pass: `out/z2-controls.json`.

## 4. The census

Per-pixel, 30,000 sampled pixels per stack, native step. σ_z in frame-index units.

| stack | n | σ_z p50 | σ_z p95 | has signal | plane R² | EASY | WINNABLE | LOST |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 109MSDCF | 22 | 0.599 | 1.06 | 99.6% | 0.409 | 98.3% | 1.28% | 0.4% |
| 112MSDCF | 79 | 0.297 | 19.70 | 94.0% | 0.448 | 85.8% | 4.28% | 9.9% |
| 113MSDCF | 63 | 0.237 | 14.52 | 94.7% | 0.474 | 88.3% | 2.15% | 9.5% |
| 119MSDCF | 33 | 0.560 | 0.99 | 99.8% | 0.393 | 98.1% | 1.66% | 0.2% |
| bee-1 | 299 | 0.179 | 91.40 | 90.1% | 0.518 | 66.3% | 7.38% | 26.4% |
| coffee-bean | 105 | 0.023 | 30.19 | 79.8% | 0.926 | 68.0% | 0.47% | 31.5% |
| coffee-bubbles | 19 | 0.330 | 1.28 | 97.4% | 0.433 | 95.9% | 4.07% | 0.1% |
| foam | 100 | 0.032 | 0.15 | 100.0% | 0.470 | 99.5% | 0.41% | 0.1% |

Partition at DOF/2 = 1.5, at the window that maximises WINNABLE — a deliberate
generosity to A5, so that a kill would be unimpeachable. That window is 33×33 at every
stack, and it buys a pooling gain of only **2.19×**, not 33×, for the reason in §Z3
below.

Median across the eight stacks: WINNABLE **1.91%** at DOF/2 = 1.5 and **1.13%** at
DOF/2 = 3.0. Both are below the 2% bar. **On the substrate as it stands, the registered
rule says KILL.**

The kill would be by **EASY saturation**, not by LOST saturation — median EASY is 92.1%
and 94.4%. That distinction is the whole result, and control C5 exists to make it
credible: on a synthetic cube of high curvature and low noise, the partition returns
EASY 100.00% / LOST 0.00%, and on pure noise it returns EASY 0.00% / LOST 100.00%. The
instrument does separate "no room to improve" from "cannot estimate".

### Z3 — coherence, and why the pooling gain is small

Response noise is spatially correlated, because the operator is a box filter. On
113MSDCF the autocorrelation falls to 1/e at **8 px in x and 12 px in y** (d4 pixels),
so a 9×9 window contains `n_eff = 1.54` independent samples against a nominal 81 — a
deflation of **53×**. Pooling gains across the window ladder are 1.03, 1.09, 1.24, 1.57
and 2.19 for W = 3, 5, 9, 17, 33.

Bias B3 named this in advance as "the single most likely way this lane could wrongly let
A5 live". It is real and it is large, and it is why the census uses measured `n_eff`
rather than window area everywhere.

Depth itself is only moderately plane-like at 9×9: median local plane R² is 0.39–0.52 on
seven stacks and 0.926 on coffee-bean. A surface has real structure to lock onto, but
not an overwhelming amount.

## 5. The analysis that changed the verdict

Preregistration bias **B1** recorded that M66's regularisation "inflates apparent ẑ
coherence and pooling gain" and classified it as favouring A5. **B1 as registered is
incomplete, and the omitted half is the one that decides this lane.** The same smoothing
also shrinks σ_r, which shrinks σ_z, which inflates EASY — and that works *against* A5.
The census is dominated by the half I did not register.

The bootstrap answers it directly, because it builds σ_z by adding noise of a stated size
to a smoothed truth: inflating σ_r by F yields the σ_z that a noisier — that is, less
regularised — operator would have. Median over the eight stacks:

| F | WINNABLE @ DOF/2 = 1.5 | verdict | WINNABLE @ DOF/2 = 3.0 | verdict |
| --- | --- | --- | --- | --- |
| 1 (substrate as-is) | 1.91% | KILL | 1.13% | KILL |
| 2 | 5.86% | INCONCLUSIVE | 2.27% | INCONCLUSIVE |
| 4 | 10.22% | SURVIVE | 6.11% | INCONCLUSIVE |
| 5.40 | 12.11% | SURVIVE | 9.03% | INCONCLUSIVE |
| **6.83 (shipping operator)** | **14.02%** | **SURVIVE** | **10.12%** | **SURVIVE** |
| 8 | 15.35% | SURVIVE | 10.86% | SURVIVE |
| 16 | 16.42% | SURVIVE | 14.78% | SURVIVE |
| 32 | 22.57% | SURVIVE | 20.81% | SURVIVE |
| 64 | 16.47% | SURVIVE | 25.73% | SURVIVE |

**Where F = 6.83 comes from.** For white input noise the variance of a box mean is the
sum of squared kernel weights. In 1D: `box27` 0.037037, `box17` 0.058824, their cascade
0.029291, `box5` 0.2. Squaring for the separable 2D case gives 8.579e-4 for M66's
cascade and 0.04 for a 5×5, so `F = √(0.04 / 8.579e-4) = 6.83`. Taking only the 27×27
selection box, with no extra regulariser, gives 5.40; that is the conservative lower
bound and is carried in the table.

**The white-noise assumption is conservative in the survive direction.** Tenengrad
correlates adjacent pixels, so a 5×5 window averages fewer than 25 independent samples
while a 43-px-support cascade is barely affected. The true F is therefore **larger** than
6.83, which moves further into SURVIVE.

## 6. Verdict

**SURVIVE, NOT ROBUST.** At the shipping operator's noise level the median WINNABLE
fraction is 14.02% at DOF/2 = 1.5 and 10.12% at DOF/2 = 3.0, both at or above the
registered 10% survive bar. At the conservative lower bound F = 5.40 the DOF/2 = 3.0 arm
reads 9.03% and is INCONCLUSIVE. The registered robustness rule requires agreement at
every half-width, and it is not met, so the verdict is not robust.

**This does not license A5.** §8 registered the limit in advance: *"A SURVIVE verdict
does not license A5. Per B1/B3/B4 it licenses only the next, decode-bearing lane on the
shipping 5×5 operator with aligned frames."* That limit now carries its full weight,
because the entire verdict rests on an extrapolation in F rather than on a measurement of
the shipping operator. The correct next step is to measure σ_z on the real 5×5 field,
which requires the Rust seam in §8 below.

**What A5 got wrong, and it matters.** A5 anticipated failure by σ_z being *too large*.
On this substrate σ_z is *too small* — the risk to A5 is not that depth cannot be
estimated but that it is already estimated well enough per-pixel for admission to be
decided without a surface. Any future defence of A5 has to argue against EASY, not
against LOST.

## 7. Disclosed errors

1. **The σ_z derivation in §4 of the preregistration was wrong as applied** — evaluated
   at the symmetric point and used at every pixel, omitting a factor averaging √2
   (Amendment A1.1).
2. **Even corrected, the analytic σ_z is unusable**, understating by 1.34× and calling
   90–98% of a pure-noise cube placeable (A1.2, A1.3). It is retained in the code as a
   diagnostic only, and the note quotes both numbers so the size of the repair is visible.
3. **Bias B1 was registered with only one of its two halves** (§5). The omitted half —
   regularisation shrinking σ_z and inflating EASY — is what drives the census, and
   without the F analysis this lane would have reported KILL.
4. **C3 was the wrong test** and was replaced by a truth test (A1.4). The replacement is
   strictly harder for this lane's estimator.
5. **The verdict is an extrapolation.** No number here was measured on the shipping
   operator; F = 6.83 is computed from kernel weights under a white-input-noise
   assumption, not measured.
6. **`n_eff` was computed from a truncated autocorrelation, and the checker caught it.**
   `noise_autocorr` ran to lag 24 while the largest window is 33, so the tail beyond lag
   24 was dropped from `S = Σ(w−|d|)ρ(|d|)`. Dropping positive tail correlation
   *understates* `S` and therefore *overstates* `n_eff` and the pooling gain — the
   direction that favours A5. The bound is `max_lag ≥ max(W) − 1`; it is now 40. Effect
   on the 33×33 gain: 2.46 → **2.19**. Every number in this note is post-fix. No control
   caught this: all eight pass identically either way, because none of them exercises a
   window wider than the truncation. It was found only by `check_note.py`, which
   recomputes `n_eff` from the stored ρ without importing `zflib`. `zflib.n_eff` now
   hard-errors rather than padding the missing tail with zeros, and
   `src/commission_neff.py` plants the historical lag-24 truncation to prove that guard
   fires — a guard that has never fired may be a no-op.
7. **The checker itself had a defect, and commissioning found it.** `says()` searched the
   whole document, so a presence check was satisfied by *any* copy of the phrase. Flipping
   the §6 verdict from SURVIVE to KILL while leaving §1's copy intact left the checker
   **GREEN at 170/170** — the single most load-bearing sentence in the note was
   effectively unguarded. `says()` now takes a section anchor, and an unpinned phrase that
   occurs more than once is reported as a defect rather than passed. Both verdict sites
   are now checked at their own anchors, and `src/commission_note.py` carries the
   §6-only flip as a counted plant so the repair cannot silently regress. It is 9 plants,
   9 caught, with a null control.

## 8. What this asks of the proposal

1. **A5's phase-0 gate should be recorded as passed-with-conditions, not passed.** The
   condition is the decode-bearing lane on the 5×5 field.
2. **A5's kill text should be re-pointed at EASY.** As written it guards against σ_z
   being too large; the measured risk is the opposite.
3. **The Rust seam is now justified by evidence rather than convenience.** `--stats`
   (`main.rs:668`) builds a `ThroughFocus` (`merge_cmd.rs:4134`) that computes the fine
   triple, the sub-frame offset and the log-quadratic coefficient `a` per pixel
   (`through_focus.rs:158–202`, `:443–463`, `:483–505`) — and then reduces them straight
   to summary vectors and discards them: `merge_cmd.rs:6567–6568` calls
   `subframe_offset(i)` and `subframe_deficit(i)` across every pixel and collects only
   `Vec<f32>` for quantiling. `a` is never even stored; it is a local at
   `through_focus.rs:495`. Exporting those arrays behind a path-bearing option is the
   smallest change that would let this census be repeated on the real operator.
4. **Pooling gain must be quoted as measured `n_eff`, never window area.** The nominal
   9×9 gain of 9× is really 1.24×.

## 9. Reproduction

    python experiments/M-PHASE0-ZFIELD/src/z2_controls.py   # 8/8 GREEN, must run first
    python experiments/M-PHASE0-ZFIELD/src/z1_census.py     # -> out/z1-census.json
    python experiments/M-PHASE0-ZFIELD/src/z5_verdict.py    # -> out/z5-verdict.json
    python experiments/M-PHASE0-ZFIELD/src/commission_neff.py  # guard fires on the planted defect
    python experiments/M-PHASE0-ZFIELD/src/check_note.py    # 171/171 GREEN
    python experiments/M-PHASE0-ZFIELD/src/commission_note.py  # 9 plants, 9 caught, null control green

No RAW is decoded and nothing under `D:\personal\macro` is read or written.

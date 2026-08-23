# M15 — pre-registration

**Question:** SYNTHESIS §10 question 17 — *does the focus-measure window optimum
survive the merge regulariser?*

**Written and committed before any result was read.** The only M15 command run
before this file was committed was a **timing probe** (one cell, 22 measures x 6
regulariser widths, `data/_probe.csv`). Only its wall time (2.5 s), its row count
(132) and its byte size (28,792) were read; the file was deleted without any
column being read. That is disclosed here rather than hidden because a timing
probe that touches the treatment axis is exactly the sort of thing that should be
declared.

---

## 0. What is already known, and what is not

M13 measured the Tenengrad focus window optimum at **radius 13 (a 27x27 box)** by
regret over 36 occluding-edge cells (`docs/research/M13-window-depth-measured.md`,
SYNTHESIS facts 60-67). **All 7,200 of its edge measurements were taken at merge
regulariser `width = 1`, i.e. with the regulariser switched off** (fact 60, scope
clause).

The regulariser does the same *kind* of work the window does:

| mechanism | what it averages | when |
| --- | --- | --- |
| focus **window** (radius `w`) | Sobel gradient energy `\|grad L\|` | **before** the pointwise `1/sigma(L(p))` normalisation, inside the measure |
| merge **regulariser** (width `g`, radius `r = (g-1)/2`) | the finished focus field | **after** normalisation, per frame, before the argmax |

Both are running-sum box means over (almost) the same field, separated only by a
pointwise divisor. So they should be *strongly* substitutable a priori. M2 measured
the regulariser cutting merged-noise excess **1.2527x -> 1.0737x** (width 1 -> 17),
a larger noise reduction than the entire window axis provides (M13 §1.1: 1.1324 at
w5 -> 1.0778 at w40).

**The hypothesis:** if the regulariser already buys the variance reduction, the wide
window's *benefit* shrinks while its occlusion-halo *cost* does not, so the window
optimum moves **narrower** than w13.

---

## 1. Design

Reuse M13's harness unmodified — `experiments/m13-window-depth/`, binary
`target/release/m13-window-depth.exe`, subcommand `edge`. Nothing in `crates/**`,
`experiments/m13-window-depth/**` or any `docs/research/M*.md` is edited. The
harness already exposes the regulariser axis as `--widths`; M13 pinned it to `1`.

**Plant.** M13's occluding-edge plant, unchanged: a Porter-Duff `over` composite of
two real corpus textures at two planted depths, blurred per frame, real sensor noise
injected, nothing resampled. Every decision cell contains a genuine depth
discontinuity (SYNTHESIS §5 item 24). The zero-step cells are retained *as the null*
and are excluded from every decision.

**Cells.** `(stack, shape, step)`: 2 stacks (`109MSDCF`, `119MSDCF`) x 3 geometries
(`vertical`, `horizontal`, `bar`) x 6 depth steps (0, 2, 4, 8, 16, 32 frames) = 36.
**30 depth-step cells decide; 6 zero-step cells are the null.**

**Window ladder (24 points).**
`0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 23, 26, 33, 40`

M13's 20 points plus **w4, w7, w14, w16**. w14 and w16 because M13's ladder omits
them, so its "w13" was an argmin over a ladder that cannot distinguish w13 from w14.
w4 and w7 because the registered hypothesis predicts the optimum moves *narrower*,
and a claim about where it moved needs resolution where it is predicted to land.
The ladder endpoints are **w0 and w40**, unchanged from M13, so the
`interior`/`ENDPOINT` labelling is directly comparable.

**Regulariser ladder (9 points).**
`1, 3, 5, 9, 13, 17, 25, 33, 49` (odd, because the box is `2r+1`).

Justification, point by point:

- **1** — M13's setting. The control: regulariser off (`radius 0`, the harness
  bypasses the box entirely).
- **3, 5** — the narrow region M9 measured as *actively harmful* for `ring(1,3)`
  (1.3625x at width 3 against 1.2527x unregularised, fact 36). If the two mechanisms
  interact non-monotonically this is where it shows.
- **9, 17** — the two non-trivial points M2, M9, M11 and M13's own Gate 1 used.
  **17 is the project's reference operating point** (fact 23, SYNTHESIS §3.3), so
  the width-17 column is the headline.
- **13, 25** — fill either side of 17 so the surface is not read off three points.
- **33, 49** — beyond the point where M11 measured selectivity *declining*
  (fact 42: selectivity peaks near width 17 and declines by width 33). A stress
  region: if the window optimum is going to collapse to w0, it collapses here.

**Seeds (5).** M13's three — `20260823`, `771117`, `4242424` — plus `13371337` and
`90210`. Primary aggregation is over **all 5**; the **3-seed M13 subset** is reported
beside it as the exactly-comparable arm. Both are registered here; if they disagree
that is reported as the result.

**Grid:** 2 stacks x 3 shapes x 6 steps x 24 windows x 9 widths x 5 seeds =
**38,880 measurements**, against M13's 7,200.

**One invocation per (stack, seed) covering all 9 widths.** This is deliberate. The
harness sizes the tile margin as `max_w (g-1)/2 + max_support + max_blur_radius`, so
a per-width invocation would give each regulariser width a *different* tile and hence
a different noise realisation — a nuisance factor perfectly confounded with the
treatment. Running all widths in one process gives every width **the identical
plant, identical noise draw and identical focus volume**, which makes the comparison
paired. The price is that this run's `width = 1` rows are not bit-identical to M13's
(M13's margin was 24 px smaller). That is what Gate A below is for.

---

## 2. Guards that must pass before any result is read

**Gate 0 — corpus audit, `-Force`, before and after** (SYNTHESIS §5 items 22, 28).
Published in the report. Both the harness `audit` subcommand and an independent
`Get-ChildItem -Recurse -File -Force` enumeration. Expected: `C:\dev\macro`
**18530 files / 286,893,514,060 bytes**; `D:\macro-dark-frames` 242 / 8,179,392,512;
`D:\personal\macro` 632 / 18,194,001,522.

**Gate A — reproduce M13 at width 1 before extending it** (SYNTHESIS §5 item 15).
Re-run M13's edge sweep *exactly*: its 20-window ladder, its 3 seeds, `--widths 1`,
its ROIs, its shapes and steps. Then:

- **A1 (strong form):** the regenerated `edge-<stack>.csv` must be **byte-identical**
  to M13's committed `experiments/m13-window-depth/data/edge-<stack>.csv`. This is a
  stronger check than the brief requires and it also proves that no concurrent edit
  to `crates/**` has changed the numbers under me.
- **A2 (the published numbers):** over the **30 step>0 cells**, argmin of mean regret
  = **w13** at **3.171 DN**, argmin of worst-case regret = **w13** at **12.111 DN**;
  over the **6 zero-step cells**, argmin = **w40**, labelled **ENDPOINT**, at regret
  **0.000 DN**. Computed by `m15_analyse.py`, written independently of
  `m13_analyse.py`.

**If A2 fails, stop and report that.** The harness would differ from M13's and no
comparison after it would be valid. A1 failing while A2 passes is reported as a
non-blocking discrepancy with the diff.

**Gate B — the treatment is actually switched on (positive control).** The claim
"the optimum does not move" is worthless if `--widths` did nothing. Two checks:

- **B1:** `xcheck` on `109MSDCF` ROI `2272,1344,256,256` must reproduce M2's
  `ring-1-3` **1.2527x at width 1** and **1.0737x at width 17** (M13 Gate 1
  reproduced both to 4 dp).
- **B2:** merged-noise ratio `N` on M11's four committed flat ROIs per stack must
  **fall** as the regulariser widens, over the full 9-point width ladder, for
  `tenengrad-w5`, `tenengrad-w13`, `tenengrad-w40` and `ring-1-3`. Registered
  requirement: **`N(width 17) < N(width 1)` for `ring-1-3`**, by at least 0.10 ratio
  units (M2 measured 0.179). The Tenengrad arms are reported, not gated — M9 already
  showed the noise axis is not monotone for every operator.

**Gate C — the metric's known blind spot is asserted, not caveated**
(SYNTHESIS §5 item 26). Run the harness `selftest` and publish the complementarity
control (a planted compromise election of radius R must read `bleed_width = 0.0` and
`mis_width = R-1`). Then **search my own M15 edge data for a real instance** of the
blind spot — a (cell, window, width) triple where `bleed_fg` falls while `excess_dn`
rises — and publish it. If no such instance exists in M15 data, that is reported.

**Gate D — the placebo for "the axis I varied is what moved the answer".** At
**fixed** regulariser width, split the 5 seeds into two disjoint halves
(`{20260823, 771117}` vs `{4242424, 13371337, 90210}`) and recompute the whole
decision inside each half. The argmin displacement between halves is the **null
distribution of the shift under no treatment**. Registered: an effect is only
claimed if the treatment shift **exceeds** the placebo shift measured this way.

**Trap controls carried forward from M13, restated so they cannot be lost:**

- `acc` and `acc_band` are **nested sets** and are never quoted as agreeing.
  `far_rms` and `band_rms` are disjoint and may be compared.
- ROIs are taken from M13's `run-m13.ps1`, which itself took them from M11's
  committed CSVs, not from `run-m11.ps1` (the ROI trap). Flat ROI `single_sigma`
  ~28-30 DN, detail ~630-700 DN.
- Every decision cell has `step > 0`. A fronto-parallel plant cannot express the
  failure mode; the zero-step cells are the null, never a decision input.

---

## 3. The objective and the aggregation rule

Identical to M13's, so the comparison means something.

**Primary objective:** `E_excess` = the `excess_dn` column = `band_rms - floor_rms`,
reconstruction error in DN over the per-cell irreducible floor, in the band
`|d| <= 24` around the planted boundary. The floor is an oracle evaluated on the
**noise-free** stack for that exact cell and is constant across windows and widths.

**Aggregation, per regulariser width `g`:**

1. Filter rows to `width == g`.
2. Cell value `E(w, cell, g)` = **mean over seeds** of `excess_dn`.
3. `regret(w, cell, g) = E(w, cell, g) - min_{w'} E(w', cell, g)`, the min taken over
   the **window ladder at that same `g`**.
4. `meanregret(w, g)` = mean of `regret` over the 30 depth-step cells.
   `worstregret(w, g)` = max over the same 30 cells.
5. `w*(g)` = argmin of `meanregret(., g)`; `w*_worst(g)` = argmin of
   `worstregret(., g)`. **Each is labelled `interior` or `ENDPOINT`** — an endpoint
   argmin is *"no turnover found within the sweep"*, never an optimum
   (SYNTHESIS §5 item 25).

**Secondary objectives, reported for every width, decided by none of them alone:**
`max(mis_bg, mis_fg)` in px, `dmae_band` in frames (M13's other two), and `far_rms`
in DN (disjoint pixel set from `band_rms`, so it may be compared with it). `far_rms`
is in the set because `E_excess` is band-restricted and the regulariser's benefit on
smooth surface lives largely *outside* the band; if the two disagree, that
disagreement is the finding.

**Secondary aggregation — the joint surface.** The same regret rule over the joint
`(w, g)` grid: per cell, min over all 216 `(w, g)` pairs, then mean and worst-case
regret of each pair. This answers the question the project actually faces — what
`(window, regulariser)` pair to ship — and both parameters are realisable, so no
oracle is involved (SYNTHESIS §5 item 27).

**Reported restricted to M13's 20-window ladder as well**, so the `g = 1` row is
directly comparable with 3.171 / 12.111.

---

## 4. Hypotheses, stated so they can be refuted

Let `r = (g-1)/2` be the regulariser radius.

- **H_sub (perfect substitution).** The two mechanisms are interchangeable at the
  margin, so only the total effective smoothing matters:
  `w*(g) = max(0, w*(1) - r)`. Substitution rate `s = -d w* / d r = 1`.
  At `g = 17` this predicts **w5**; at `g = 27` it predicts **w0**.
- **H_none (no substitution).** `w*(g) = w*(1)` for every `g`. `s = 0`.
- **H_part (partial substitution).** `0 < s < 1`.
- **H_anti.** `s < 0` — the optimum moves *wider* under regularisation.

`s` is estimated by ordinary least squares of `w*(g)` on `r` over the 9 widths, and
also reported as the simple endpoint contrast `(w*(1) - w*(17)) / 8`.

---

## 5. Decision rule, registered on a realisable quantity

The decision the project faces is *"do we ship w13?"*. So the registered threshold is
on the **penalty for shipping w13**, which is realisable and decision-relevant — not
on an oracle (SYNTHESIS §5 item 27), and not on the argmin location, which is a
label rather than a cost.

> **`Delta(g) = meanregret(w13, g) - meanregret(w*(g), g)`** — the mean regret in DN
> that the project pays, at regulariser width `g`, by shipping M13's w13 instead of
> the best window at that width.

**Registered thresholds, both fixed from M13's own published numbers, not invented
after the fact:**

- **Primary: `Delta(g) <= 0.87 DN` => w13 survives at width `g`.** 0.87 DN is the
  flatness M13 published for its own w11-w15 basin (M13 §3.2: the w13->w15 gap).
  A penalty no larger than the width of the basin M13 already declared flat cannot
  justify changing the recommendation.
- **Sensitivity: `Delta(g) <= 0.29 DN`** — M13's w12->w13 gap, its tightest resolved
  step. Reported alongside; does not override the primary.
- **Resolvability floor:** M13 measured the median seed-to-seed sd of `E_excess` at
  **0.193 DN**. With 5 seeds the per-cell standard error is `0.193/sqrt(5) = 0.086`
  DN and the standard error of a 30-cell mean regret is `~0.016 DN`, so both
  thresholds sit far above the noise floor **if the seeds behave as M13's did**. The
  achieved seed sd is measured and published rather than assumed.
- **Worst-case arm:** the same `Delta` on `worstregret`, threshold **12.111 DN**
  (M13's own published worst-case regret at w13) — i.e. w13's worst case must not
  become worse under regularisation than it already is without it.

**The headline verdict is taken at `g = 17`**, the project's reference operating
point, and the width at which w13 *stops* surviving (if any) is reported explicitly.

---

## 6. The full outcome grid

Every cell of the outcome space, with the conclusion written before the data
(SYNTHESIS §5 item 14).

| # | Observation | Conclusion, registered |
| --- | --- | --- |
| **O1** | `w*(g)` decreases with `g` **and** `Delta(g) > 0.87 DN` at some `g <= 17` | **The optimum moves narrower and w13 does not survive.** The recommendation is regulariser-dependent. Report `w*(g)` for the whole ladder as the shipping table, headline the `g = 17` value, and state that SYNTHESIS fact 60 and §3.3's "27x27" must be rescoped to "unregularised". |
| **O2** | `w*(g)` decreases with `g` but `Delta(g) <= 0.87 DN` for all `g <= 17` | **The optimum moves but w13 survives.** Report the shift, report that it is inside M13's own published basin, and recommend shipping w13 unchanged while recording the drift as a scope note. |
| **O3** | `w*(g)` stays inside M13's basin **w11-w15** for all `g`, and `Delta(g) <= 0.87 DN` | **The optimum does not move. Question 17 closes; w13 ships with confidence.** This is a fine result and is reported plainly, as the conversion of a caveat into a settled fact. The redundancy hypothesis is **refuted**, and the report must then say *why* two box means over nearly the same field are not substitutable. |
| **O4** | `w*(g)` increases with `g` (`s < 0`) | **H_anti.** The hypothesis is refuted with the sign reversed: regularisation makes a *wider* window preferable. Report and rescope w13 as a lower bound under regularisation. |
| **O5** | The treatment shift does **not** exceed the Gate D placebo shift, or `\|Delta\|` is within `2 x` the measured mean-regret standard error | **Not resolvable at this design's power.** Report the achieved noise floor and the shift that *would* have been resolvable, and state that question 17 stays open. Do not report a direction. |
| **O6** | `w*(g)` is non-monotone in `g` — e.g. it moves narrower up to `g = 17` and then reverses, or the narrow widths 3-5 behave unlike 9-17 | **Report the whole surface, not a summary.** The decision is then taken by the largest `Delta(g)` over the widths the project would plausibly ship (`g` in 1..33), and the non-monotonicity is itself a reported finding. |
| **O7** | Any **zero-step** cell shows an `interior` argmin at any width | **The null fails.** Diagnose the control before believing it (SYNTHESIS §5 item 16); publish the original failure next to any repair. Two readings are possible and must be distinguished: a harness defect, or a genuine finding that the *regulariser* creates an interior optimum with no discontinuity — which would refute the generality of fact 61. |
| **O8** | Gate A2 fails | **Stop.** Report that the harness does not reproduce M13 and make no comparison. |
| **O9** | The joint `(w, g)` surface has its minimum at a `g > 1` with a `w` far from 13 | Report the joint optimum as the shipping recommendation **and** the `g = 17` conditional optimum, because the project has already committed to a regularised merge (SYNTHESIS §3.3, rule 4) and cannot choose `g = 1`. |

**On corroboration (SYNTHESIS §5 item 20).** Gate A is a *consistency check* on my
harness, not independent evidence for M13 — it is M13's own code on M13's own inputs.
The only results in this milestone disjoint from M13's measurements are the rows at
`width != 1` and the four new window radii (w4, w7, w14, w16). The report must label
which is which.

---

## 7. Deliverables

- `data/audit-before.txt`, `data/audit-after.txt` (+ PowerShell `-Force` twins).
- `data/repro-edge-109MSDCF.csv`, `data/repro-edge-119MSDCF.csv` — the Gate A
  replication of M13 at width 1, on M13's 20-window ladder.
- `data/edge-109MSDCF.csv`, `data/edge-119MSDCF.csv` — the main 24-window x 9-width
  x 5-seed sweep.
- `data/noise-109MSDCF.csv`, `data/noise-119MSDCF.csv` — Gate B2, `N` vs regulariser
  width on M11's committed flat ROIs.
- `data/xcheck-109MSDCF.txt` — Gate B1. `data/selftest.txt` — Gate C.
- `run-m15.ps1` — the whole chain, in order.
- `m15_analyse.py` — the analysis, written independently of `m13_analyse.py`, reading
  only `data/`. Every table names the stratum it filtered on.
- `data/analysis.txt` — its output.
- `docs/research/M15-regulariser-window-measured.md` — the report.

Nothing outside `experiments/m15-regulariser-window/**` and
`docs/research/M15-regulariser-window-measured.md` is written.

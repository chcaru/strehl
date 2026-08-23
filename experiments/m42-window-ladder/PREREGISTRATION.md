# M42 — pre-registration: the window ladder for `tenengrad-sq`

**Committed before any candidate number was read.** Answers `OWNER-QUESTIONS.md` **Q1**,
left open by M17: `WINDOW_RADIUS = 13` was selected by M13/M15 while the operator was the
gradient **magnitude**. M17 changed the recommended operator to the **squared** magnitude.
A window optimum is a property of the *operator/window pair*. Nobody has checked that 13
survives the operator change.

## 0. The state of the world I am starting from (checked, not assumed)

* `crates/strehl-core/src/focus.rs` at `542adfb` still computes
  `out = (gx*gx + gy*gy).sqrt()` (line 160) under `WINDOW_RADIUS = 13` (line 83). So
  **the squared operator is not in the shipped binary yet.** Q1's premise ("you have now
  changed the operator") is a decision recorded in SYNTHESIS (facts 103–105) and
  `OWNER-QUESTIONS.md`, not a code state. This matters for how a defect must be worded:
  a bad radius for `tenengrad-sq` is a **defect in a pending default**, not in shipped
  code — unless the ladder also moves the optimum for the *magnitude* operator, which
  would be a defect in shipped code. I will report both operators for exactly this reason.
* M13's ladder is `w ∈ {0,1,2,3,5,6,8,9,10,11,12,13,15,17,18,20,23,26,33,40}` — 20 windows
  (`experiments/m13-window-depth/run-m13.ps1`). I sweep the same 20 so the numbers drop
  straight into the corpus.
* Fact 60: argmin **w13**, mean regret **3.171**, worst **12.111**, over the 30
  depth-step cells. Fact 61: the 6 zero-step cells put their argmin at the **w40
  endpoint** at regret 0.000 — no interior optimum at all.
* Fact 152: at radius 13 occlusion bimodality enrichment is **0.36× — depleted** (4.38× at
  radius 2). A wider box is therefore *not* free even when it is free in DN and in ms.

## 1. Rule 24 — the choice points I am RE-MAKING, not re-computing

A verifier who re-runs M13's script with a new operator confirms M13's choices. These are
the choices that are **operator-specific**, and what I am doing differently:

| Choice | M13's setting | What I do, and why |
| --- | --- | --- |
| **Normalisation degree** | `÷σ¹` for a degree-1 response | The squared response's monotone partner is `÷σ²` (M17 fact 105). I sweep **both** `tenengrad-sq-wN` (÷σ²) and `tgrms-wN` (`√box_mean(g²)`, ÷σ¹). At regulariser width 1 these are provably identical; **carrying both is the check that my ladder has not silently changed the normalisation**, and it is the arm that would expose a degree confound if width > 1 were ever swept. |
| **Primary statistic** | regret vs the per-cell best **across windows** | I use **regret** as primary here (M17 used absolute `excess_dn`, correctly, because M17's treatment changed the *operator*). A window ladder is exactly the treatment regret was designed for, and it is the statistic fact 60 is quoted in, so the numbers must be comparable. Absolute `excess_dn` is reported alongside. **Regret is computed per operator**, over that operator's own 20 windows — mixing operators into one regret pool would let one operator's bad windows flatter the other's. |
| **Uncertainty on the argmin** | basin flatness vs a 0.87 DN threshold | Same threshold (borrowed, not invented), **plus** the 6 independent argmins from `2 stacks × 3 seeds` as an empirical spread. Discipline 31: an `interior` label is meaningless unless the winner is separated from its neighbours by more than the noise floor, so I report the **basin** — every window within 0.87 DN of the min — as the answer, and the point argmin as a label on it. |
| **Which cells** | 36 cells; 30 with a step, 6 zero-step | Same. The zero-step stratum is the **null control** and is scored separately (fact 61). |
| **Endpoint handling** | discipline 25 | An argmin at w0 or w40 is reported as **ENDPOINT — no turnover found within the sweep**, never as an optimum. |

## 2. Rule 20 — what would make each gate FAIL

Written before running. If nothing could fail it, it is arithmetic and is labelled so.

| Gate / metric | The input that makes it FAIL | Does such an input exist? |
| --- | --- | --- |
| **G1** M13's ladder reproduces (`tenengrad-wN`, argmin w13, mean regret 3.171, worst 12.111) | any change to the tile margin, plant geometry, seed set, Sobel scaling or box policy in my fork | **Yes — and it already happened once.** M17's first probe rendered `vertical@261` instead of `vertical@274` because a wide measure was dropped, changing every number. G1 has demonstrated power to reject. |
| **G2** zero-step null stratum puts `tenengrad-sq`'s argmin at an endpoint | an interior argmin on the zero-step cells would fail it | Yes: an interior argmin there is a perfectly expressible outcome, and would mean the squared operator manufactures a depth signal where there is no depth step — a red flag about the operator, not the ladder. |
| **G3** blind-spot D varies with radius | D constant in radius would fail the premise that radius matters for the cure | Yes — and for the *magnitude* operator D **is** ≈1.0000 at every radius ≥ ~8 (fact 73's own ladder: w1 0.376, w3 0.747, w13 1.000). So the metric demonstrably separates. |
| **G4** cost is flat in radius | `box_max`'s 4.90× (M17 fact 110) is the worked example of a filter that fails this | Yes; M17 measured a filter that fails it. |
| **argmin uncertainty** | if all 20 windows sit inside the 0.87 DN basin, the argmin is meaningless and I must say so | Yes — this is the outcome I most expect to have to report honestly. |

**A gate with no failing input that I am labelling as arithmetic, not evidence:**
`tgrms-wN` ≡ `tenengrad-sq-wN` at regulariser width 1 is a **DERIVED identity** (monotone
reparameterisation, M17 fact 105). Its agreement is arithmetic. It has power only as a
*harness* check — it would fail if my code accidentally applied the wrong normalisation
degree — and that is the only claim I will make from it.

**Rule 23 check.** All Sobel gradients in this harness are computed on a single 2-D `f32`
plane (`measures.rs::sobel_magnitude`, indexed `y*w + x` over one frame's `width × height`).
There is no 3-D cube and no `scipy.ndimage` anywhere in the measurement path; the Python
here only reads CSVs. **Not applicable, checked rather than assumed.**

## 3. What I will run

1. **Edge ladder.** 2 stacks × 3 shapes × 6 steps × 3 seeds × 20 windows × 2 operators
   (`tenengrad-wN`, `tenengrad-sq-wN`) + `tgrms-w13` as the degree check, regulariser
   width 1, M13's ROIs/frames/σ₀/α/noise/band/baseline. `--steps 0,2,4,8,16,32` and the
   presence of a `w40` measure are **mandatory** (they pin the tile margin — M17's trap).
2. **Noise ladder.** N on the 4 committed flat ROIs per stack, both operators, 20 windows.
3. **Blind-spot ladder.** D(σ3 vs σ0) on the hard step and the 9-px ramp, both operators,
   20 windows, with M17's null control (σ0 vs σ0) and both positive controls.
4. **Cost ladder.** Whole-measure ms/frame/Mpx for both operators across the ladder,
   alternating sweep direction, per-setting minimum, quoted as a **bound** if near-flat.

## 4. The decision rule

Let `B_sq` = the set of windows within **0.87 DN** of `tenengrad-sq`'s minimum mean regret.

| Verdict | Condition |
| --- | --- |
| **13 SURVIVES** | `13 ∈ B_sq` |
| **13 IS A DEFECT** | `13 ∉ B_sq`, and the gap from `13` to the basin exceeds 0.87 DN by more than the 6-argmin spread |
| **INDETERMINATE** | `13 ∉ B_sq` but the gap is inside the spread of the 6 per-stack-per-seed argmins |

If 13 survives on quality, the recommendation is still **not automatically 13**: fact 152
says radius 13 *depletes* the bimodality signal M18's seam needs (0.36× vs 4.38× at
radius 2), and axis 4 of this milestone measures whether the blind-spot cure itself is
radius-dependent. Those are reported as a **separate constraint** on the choice, not
folded into the quality number.

**A negative result — "13 survives, nothing to do" — is an acceptable and valuable
outcome and will be reported as the headline if that is what the numbers say.**

## 5. Predictions (so they can be falsified)

1. `tenengrad-sq`'s mean-regret basin **contains 13**, because M13's own basin (w11–w15,
   fact 60/81) is wide relative to how much squaring changes the statistic.
2. The squared operator's optimum sits at a **smaller or equal** radius than 13, because
   squaring up-weights the gradient ridge centre and so reaches its bias-variance balance
   sooner.
3. The blind-spot cure **is** radius-dependent and degrades toward 1.0 as the radius grows,
   because the TV-conservation argument is asymptotic in window-width ÷ blur-width;
   predicted D(w40) > D(w13) for `tenengrad-sq`.
4. Cost stays flat in radius for both operators (both are `box_mean`), so the combined
   cost of a different radius is **≤ 1.02×** — the M17 bound.
5. The zero-step null stratum puts `tenengrad-sq` at the **w40 endpoint**, as fact 61
   found for the magnitude.

# M125 — PRE-REGISTRATION

**Written and committed before the selection procedure was run and before its
score was read.** The commit that contains this file is named in
`docs/research/M125-photometric-auto.md` §0. Nothing below may be changed after
a score exists; an amendment, if one is needed, will be labelled post-hoc and
may only make a conclusion worse.

Subject: **make `STREHL_PHOTOMETRIC` decide per stack whether to apply, instead
of asking the owner to guess** — and establish whether the decision rule is real
rather than fitted.

Prior art read in full before writing this (AGENTS.md rule 40, discharged with
`python experiments\ORCH-drift-check\prior_art.py photometric auto threshold
drift`): `M122-photometric-promotion.md`, `M24-photometric-drift-measured.md`,
`M99-photometric.md`, `M91-photometry.md`, `M97q-photometric-wiring.md`,
`M103-halfdrift.md` (returned by the script, not in the brief), SYNTHESIS facts
1675–1687 and disciplines 862, 866, 853, 836, 837.

---

## 0. What is NOT being decided here

**The default does not move.** `STREHL_PHOTOMETRIC` unset, and
`--photometric off`, keep the exact behaviour that ships today. `auto` is
opt-in. M122's **KEEP-OFF** verdict on the unconditional switch stands and is
not overridden; this milestone builds the conditional form that M122's own
failure of criterion P3 implies, and a promotion of the default would need its
own pre-registered GO/NO-GO in a later milestone.

**No new quality claim about `--photometric` is made.** Every quality number
used here is M122's, re-scored under a different decision rule.

---

## 1. Data

All of it is M122's, already committed, already published:

| quantity | symbol | source |
|---|---|---|
| per-stack inter-frame level drift | `Dpp` | `C:\dev\strehl-out\M122\drift-corpus.json` (M24's estimator verbatim) |
| blotch response, registered form | `B12` | `C:\dev\strehl-out\M122\blotch-ab.json` |
| smooth-window level ratio A1/A0 | `lvl` | same file, per-window `lvl_ratio`, median over the 12 smooth windows |
| blotch response, level-normalised | `B12n` | `B12 / lvl`, as `posthoc.py` computes it |

n = **14** stacks, exactly M122's usable set (`correlate.json`'s `used`), with
M122's exclusion rules E2–E6 applied as they were. No stack is added and none
is removed.

### 1.1 Which statistic decides — registered now, with the reason

**`B12n` is the primary outcome. `B12` is a registered secondary sensitivity
arm and cannot change the verdict.**

The reason is measured and it is M122's own (its M20/M21, folded as its P7):
`hf` is an *absolute* laplacian RMS, so it scales with image level, and the
photometric arm can move the output level. On `113MSDCF` the smooth-window
level ratio is **1.0684** and `B12` is **1.0699**, so that entire "harm" is a
6.8 % gain and **not one extra unit of structure**; level-normalised it is
**1.0014**. Scoring a decision rule against `B12` would score it partly against
a known artefact of the instrument. `B12n` is the same statistic with that
artefact divided out.

**Disclosure, unprompted and load-bearing (AGENTS.md rules 12, 39).** The 14
`(Dpp, B12, B12n)` triples are *published prior data*. I read M122's report and
its committed JSON before writing this file, so this pre-registration **cannot
claim blindness to the inputs**. What it does fix, before any score exists, is
the *selection procedure*, the *loss*, the *acceptance criteria* and the
*controls*. Every conclusion below must be read with that limitation attached,
and it is the reason the placebo arm (§5) and the leave-one-out arm (§4) carry
the weight rather than the in-sample fit.

---

## 2. The rule family

One threshold, one direction:

> apply the photometric correction **iff `Dpp >= T`**.

`T` is a single scalar in per-cent peak-to-peak. Nothing else is fitted: no
per-stack term, no second predictor, no interaction. A one-parameter family on
14 points is already at the edge of what this corpus can support, and that is
the whole reason for §4 and §5.

`Dpp` is M24's estimator verbatim, computed over **exactly the frames the merge
consumes**: the mean of the CFA **G1** plane (`raw_image_visible[0::2, 1::2]`)
per frame, black-subtracted, then `100 * (max - min) / mean` across frames.

---

## 3. The loss

Per stack `i`, given a decision:

```
L_i(ON)  = B12n_i        L_i(OFF) = 1.0
```

`L_i(OFF) = 1.0` is not a convention: with the correction off the render **is**
A0, and `B12n(A0, A0) = 1.0` exactly. Lower is better. A score is the mean of
`L_i` over the stacks it is evaluated on.

Two degenerate baselines are scored identically and reported next to every
number:

* **ALWAYS-ON**: `S_on = mean_i(B12n_i)`
* **ALWAYS-OFF**: `S_off = 1.0` exactly

**How this loss can be fooled, stated before it is used (rule 18).** It is a
*mean*, so it pools a large win on one stack against small harms on several,
and it cannot see the difference between "helps everywhere a little" and "helps
one stack enormously and hurts the rest". That is exactly the failure M122's
criterion K2 caught, so the mean is **not** allowed to decide alone: criterion
C2 below is unpooled and has a veto.

---

## 4. Selection procedure, and how it is scored

**Candidate thresholds** are computed from the *training* stacks only:
`-inf`, the midpoints between adjacent sorted training `Dpp` values, and
`+inf`. `-inf` is exactly ALWAYS-ON and `+inf` is exactly ALWAYS-OFF, so the
degenerate rules are inside the family and the search can return them.

**Fit**: choose the candidate `T` minimising the mean training loss. **Ties are
broken toward the largest `T`** — the fewest stacks turned ON. Registered
before any score, and the reason is the cost asymmetry: a false ON is a
regression on a render that was already acceptable, a false OFF only forgoes a
gain.

**Leave-one-out**: for each of the 14 stacks, fit `T` on the other 13 and apply
it to the held-out stack. `S_auto` is the mean of the 14 held-out losses.
Nothing in-sample is reported as a result.

**Errors, reported separately and never pooled** (they are different costs):

* **FALSE-ON**: held-out stacks the rule turned ON whose `B12n > 1.0`. Report
  the count, the stacks, and the worst `B12n`.
* **FALSE-OFF**: held-out stacks the rule left OFF whose `B12n < 1.0`. Report
  the count, the stacks, and the largest forgone gain `1 - B12n`.

**Full-data threshold** `T*` is fitted on all 14 and is the number that would
ship. It is reported with the gap it sits in.

---

## 5. Controls

**PLACEBO (mandatory).** Shuffle the `Dpp` vector against the stack labels and
re-run **the entire procedure** — candidate generation, LOO fit, scoring —
2000 times with a fixed seed. Report the placebo distribution of `S_placebo`,
its mean and sd, and

```
p_placebo = fraction of shuffles with S_placebo <= S_auto
```

A shuffled predictor must collapse to no better than the better degenerate
baseline. If a shuffled predictor "works", the scoring is broken and nothing
ships.

**Power of the placebo, checked before it is trusted (rule 20).** The input
that makes the placebo *fail to reject* exists and is cheap: with the true
`Dpp` replaced by a shuffle, the procedure can still return `-inf`
(ALWAYS-ON), so `S_placebo = S_on` is reachable, and any shuffle that happens
to rank `tweezers-cpl` high scores well. The placebo therefore has a live path
to every outcome and is not arithmetic.

**PROCEDURE SELF-TEST (mandatory, run first).** On a synthetic 14-point set
where the ON/OFF truth is a clean function of the predictor, the LOO procedure
must recover `S_auto` equal to the oracle to within 1e-12; on a set where the
predictor carries no information, `S_auto` must not beat `S_on`. A procedure
that cannot pass both is not measuring anything.

**ORACLE**, reported for scale only, never as an acceptance bar:
`S_oracle = mean_i(min(B12n_i, 1.0))`. The gap `S_on - S_oracle` is the entire
headroom any rule in this family can win.

---

## 6. Acceptance criteria — the verdict is read off these and nothing else

| id | requirement |
|---|---|
| **C1** | `S_auto < S_on` **and** `S_auto < S_off`, strictly. Held-out. |
| **C2** | **No** held-out stack turned ON reads `B12n > 1.03`. M122's own K2 bar, inherited unchanged, unpooled, with a veto. |
| **C3** | `p_placebo <= 0.05`. |
| **C4** | Threshold stability: at least **12 of 14** folds must give the held-out stack the same ON/OFF decision as the full-data rule `T*`. |
| **C5** | `T*` sits in a gap between adjacent corpus `Dpp` values of at least **0.10 pp**, so the shipped constant is not balanced on a knife edge between two stacks the estimator cannot tell apart. |
| **power** | The corpus must carry variation in the decision: the full-data rule must turn ON at least 2 and at most 12 of the 14 stacks. A rule that is degenerate on its own training set has not been tested. |

**All six must pass to ship `auto`.** Any failure is a NO-SHIP and the
milestone reports the negative as its headline.

### 6.1 Kill criteria, stated so they cannot be softened later

* **K1** `S_auto >= S_on` — the threshold does not transfer; the rule is not
  learnable from 14 stacks. **This is a publishable result and is to be
  reported as the headline**, not worked around.
* **K2** `p_placebo > 0.05` — a shuffled predictor does as well; the scoring is
  broken.
* **K3** Any held-out ON stack with `B12n > 1.03` — the rule reproduces exactly
  the harm M122 refused the unconditional switch for.

### 6.2 If the verdict is NO-SHIP

Report the sample size that would be needed, by the following pre-registered
method: bootstrap-resample the 14 stacks with replacement to corpora of size
`m` in {14, 20, 30, 50, 80, 120}, run the whole LOO procedure on each, and
report the smallest `m` at which **>= 80 %** of 500 bootstrap corpora satisfy
C1. **Registered limitation, stated now:** resampling 14 stacks cannot
manufacture new *subjects*, so this bounds the precision limb only and is an
optimistic floor on the true requirement. It must be reported as such.

---

## 7. What gets built, and what must be proved about it

### 7.1 The three-valued mode (discipline 862)

`STREHL_PHOTOMETRIC` and `--photometric` become three-valued: `off`, `on`,
`auto`. **`unknown` must not collapse into `no` silently.** The named
precedent not to repeat is `STREHL_FIX_CA`, a byte-identical no-op under
`STREHL_ALIGN=0` with no warning.

`auto` **abstains loudly** — one `AUTO: ABSTAINED` line naming the reason, then
falls back to the current default (off) — in each of these cases:

* **U1 frame count outside the measured domain.** The rule was measured on
  stacks whose merged frame count lies in **[33, 100]**. `Dpp` is a
  peak-to-peak, so it grows with the number of frames, in the direction that
  makes the *costly* error (a false ON) more likely. Extrapolating it is not
  allowed.
* **U2 the drift estimator produced nothing usable** — no frames folded, or a
  non-finite or non-positive mean level.
* **U3 the scene has no background to fit a gain against.** Today this is a
  hard `exit 1` (M122 measured it on `112MSDCF`, 886 px, and `coffee-bubbles`,
  442 px, against a 1024 px floor). Under `auto` it must **abstain and render**;
  under an explicit `on` it stays a hard error, unchanged.
* **U4 the fit produced no correction** — every frame refused, or a gain span
  of exactly 1.0. M122 measured this on `dry-erase-marker-head-cpl`.

An abstention is not a decline: the log must distinguish
`AUTO: ABSTAINED (<reason>)` from `AUTO: DECLINED (drift ... below threshold
...)` from `AUTO: APPLIED (drift ... at or above threshold ...)`.

### 7.2 The drift estimator moves into the library

`Dpp` becomes a type in `strehl-core`, folded during pass one from the raw CFA
**before** registration and **before** any photometric gain, so it measures the
light and not the pipeline. **Commissioning bar, inherited from M122 and not
relaxed: it must reproduce M24's four published numbers — 0.91 %, 2.88 %,
11.70 %, 6.84 % — to within ±0.004 pp**, on M24's own frame subsets.

### 7.3 Proof obligations (rules 26, 39, 47)

Every one of these is a SHA-256 of a rendered TIFF, with the whole invocation
and environment recorded beside it:

* **H1** `--photometric off` and **no environment variable set at all**, new
  binary, byte-identical to the **current** binary's output, on **two** of the
  owner's stacks.
* **H2** `auto` on a stack the rule **declines**, byte-identical to `off`.
* **H3** `auto` on a stack the rule **accepts**, byte-identical to `on`.
* **H4 (plant, mandatory).** H1–H3 are equalities, and an equality proves
  nothing unless the instrument can report an inequality. A deliberately
  perturbed arm must produce a different hash in the same harness.

**H2 and H3 together are the claim that the rule is nothing but a switch**: it
selects between two existing pipelines and does not perturb the correction.

### 7.4 Test suite

The workspace suite must be run and reported in full. The brief's baseline is
**454 passed / 0 failed / 1 ignored at `8a46b47`**; HEAD has moved well past
that commit, so **the HEAD baseline is measured here before the edit** and both
numbers are reported. Rule 33: a `cargo test` with no `Compiling` line above it
is not evidence, and `-q` is never used.

---

## 8. Scope

Touched: `crates/strehl-core/src/photometric.rs`,
`crates/strehl-cli/src/merge_cmd.rs`, `crates/strehl-cli/src/main.rs`,
`docs/research/M125-photometric-auto.md`, `experiments/M125-photometric-auto/`.

Not touched, under any circumstance: `docs/research/SYNTHESIS.md`, `AGENTS.md`,
`docs/captures-needed.md`, `README.md`, `scripts/corpus_lint.py`, anything under
`experiments/ORCH-drift-check/`, and `D:\personal\macro` (read-only; outputs go
to `C:\dev\strehl-out\M125\`).

Committed with `git commit -m "..." -- <explicit paths>` only (rule 42). No
`git add -A`, no bare `git commit`, no `git checkout -- <path>`, no push.

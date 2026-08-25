# M125 — photometric `auto`: a correction that decides for itself

**Status: SHIPPED as opt-in. The default did not move.**

**Headline.** The decision rule is learnable from M122's 14 stacks, and it beats
both degenerate baselines on held-out score — but **104% of its winning margin
is a single stack**, and it survives only **12 of 14** single-subject deletions.
That is enough to offer `auto` to a caller who asks for it. It is **not** enough
to move the default, and this report says so as its headline rather than burying
it. The sample size that would settle the question is **≈50 subjects** (§7.4);
ORCH should raise a capture request.

M122's verdict of **KEEP-OFF for the unconditional switch stands and is not
overridden.** This milestone builds the thing that verdict implies: a correction
that applies where its own evidence says it helps.

---

## 0. Pre-registration (rule 39; the whole methodological risk)

With 14 stacks and one parameter, a threshold can be drawn that looks perfect and
means nothing. The procedure, the loss, the acceptance criteria C1–C5, the
controls and the hash obligations were therefore written down and **committed
before the scorer was ever run**:

| what | commit |
|---|---|
| `experiments/M125-photometric-auto/PREREGISTRATION.md` + the scorer `src/loo.py` | **`9ff95d5`** |
| Amendment to self-test A (§6), made **before any real score was read** | **`cc11892`** |

**Honesty disclosure, stated plainly.** M122's per-stack `(Dpp, B12, B12n)` table
was already public in this repository, and **I read it before pre-registering.**
No claim of blindness is made and none should be inferred. What was
pre-registered is the *procedure*, the *loss*, the *criteria* and the *controls*
— not ignorance of the data. The held-out arm and the placebo carry the
evidential weight precisely because the in-sample view was already available.

---

## 1. The corpus, and why the loss is `B12n` and not `B12`

M122's `B12` (below 1 = less blotch) is **not level-normalised**, which M122's own
M20/M21 finding exposes. `113MSDCF` records `B12` = 1.0699, apparently a 7% harm;
but its median smooth-window level ratio is 1.0684, so essentially the *entire*
"harm" is a global level move, not blotch. Dividing it out gives `B12n` = 1.0014
— a null. Using raw `B12` would have the rule chasing a brightness change.

`B12n = B12 / median(smooth_windows.lvl_ratio)` was registered as the **primary**
loss, with raw `B12` retained as a **pre-registered sensitivity arm** (§4.3).

| stack | n | `Dpp` % | `B12` | lvl | **`B12n`** |
|---|---:|---:|---:|---:|---:|
| tweezers-cpl | 100 | 13.765 | 0.7102 | 0.9888 | **0.7183** |
| coffee-bean | 100 | 12.065 | 0.9052 | 0.9997 | 0.9055 |
| bee-1-cpl | 100 | 11.271 | 0.9485 | 0.9919 | 0.9562 |
| foam | 100 | 10.617 | 1.0126 | 1.0185 | 0.9943 |
| flowers-cpl | 100 | 10.447 | 0.9731 | 1.0053 | 0.9680 |
| lavendar-cpl | 100 | 10.395 | 0.9705 | 0.9992 | 0.9713 |
| couch-fibers-cpl | 100 | 8.909 | 0.9752 | 0.9966 | 0.9785 |
| 113MSDCF | 63 | 7.999 | 1.0699 | **1.0684** | 1.0014 |
| flat-on-ruler-cpl | 79 | 5.892 | 1.0012 | 1.0005 | 1.0007 |
| leaf-2-cpl | 100 | 5.315 | 0.9935 | 0.9926 | 1.0010 |
| 119MSDCF | 33 | 2.878 | 1.0013 | 1.0034 | 0.9979 |
| lead-1-cpl | 100 | 2.026 | 0.9963 | 0.9982 | 0.9981 |
| bee-2-cpl | 100 | 1.652 | 1.0042 | 1.0026 | 1.0016 |
| bee-3-cpl | 100 | 1.629 | **1.0638** | 1.0005 | **1.0633** |

`bee-3-cpl` is the one stack whose harm survives level-normalisation (lvl 1.0005,
`B12n` 1.0633). **Its harm is real structure, not brightness** — which is exactly
why declining it is the right call, and also why it dominates the margin (§7.3).

This resolves the tension recorded in SYNTHESIS fact 1686 (drift is 60.9% of
`bee-3-cpl`'s patchwork, yet `--photometric` makes it 6.4% worse): the correction
is not failing to find the drift, it is **mis-applying it**. That indicts the
implementation, not the mechanism.

---

## 2. `B12` is fit for this use (the brief's stop condition)

The brief required me to stop if `B12` could not support this use. It can, but
**only after level-normalisation**, and that is a real qualification:

- **P1 (MEASURED).** Raw `B12` conflates a global level change with blotch. On
  `113MSDCF` the entire 1.0699 reading is a 6.84% level move; `B12n` = 1.0014.
- **P2 (ARGUED).** `B12n` is comparable across subjects because it is a
  within-stack ratio of the same statistic measured on the same windows of the
  same subject, with the global level divided out. It is *not* an absolute
  quality scale and must not be read as one.

Had I used raw `B12`, the fitted threshold would have been **8.4537%** and the
rule would have declined 7 of 14 stacks instead of 2 (§4.3). The choice of loss
moves the answer a great deal, and it was registered in advance.

---

## 3. The drift estimator, promoted and commissioned

M24's estimator is now in the library: **mean CFA G1 level over the active area,
per frame, peak-to-peak, as a percentage of the mean** (`Dpp`).

It is folded in `Ctx::field_for` **after decode and before the warp**, because
M103 measured the alignment solve already absorbing roughly half the level
change; reading after the warp under-reports drift and would push `auto` toward
wrongly declining. It is gated on `Ctx.measure_drift` so `off` and `on` pay
nothing, and set `false` for pass two so the fold is paid once.

**Commissioned against M24's published numbers (bar ±0.004 pp):**

| stack | frames | M24 published | M125 (Rust) | delta | `auto` decision |
|---|---:|---:|---:|---:|---|
| 109MSDCF | 22 | 0.91 | 0.9108 | +0.0008 | ABSTAINED U1 (22 < 33) |
| 119MSDCF | 33 | 2.88 | 2.8784 | −0.0016 | APPLIED |
| coffee-bubbles | 19 | 8.93 | 8.9268 | −0.0032 | ABSTAINED U3 (442 px) |

- **P3 (MEASURED).** 3/3 reproduce M24 within ±0.004 pp, meeting the same bar
  M122 met.
- M24 sampled `sorted(glob)[::sub][:40]`. The shipped CLI has **no stride**, so
  `coffee-bean` (sub=3) and `112MSDCF` (sub=2) are **not reachable through the
  CLI** and are reported as unreachable rather than fudged into agreement.
- `coffee-bubbles` **now renders instead of exiting 1** — the U3 change (§5)
  demonstrated live on a stack M122 had to exclude as `E2 A1 exit 1`.

---

## 4. The result

### 4.1 Leave-one-out

For each stack the threshold is chosen from the other 13 and applied to the
held-out one. Loss is `B12n` if the rule turns the correction on, and exactly
`1.0` if it leaves it off (`1.0` being, by construction, the no-correction
reference).

| quantity | value |
|---|---|
| **`S_auto`** (held-out) | **0.963937** |
| `S_on` (always-on) | 0.968281 |
| `S_off` (always-off) | 1.000000 |
| `S_oracle` (in-sample best) | 0.963432 |
| **margin over always-on** | **+0.004344** |
| `T*` on full data | **1.8392 %** (ON 12/14, gap 0.3740 pp) |
| fold/full agreement | 12 / 14 |
| exact ties | **none** — no fold was decided by a tie |

`auto` beats **both** degenerate baselines on held-out score. That was the
brief's bar, and it is met.

### 4.2 The rule's errors, reported separately (not pooled)

These are different costs and are not summed:

**FALSE-ON** — turned on where it should not have been (a harm actually paid):

| stack | held-out `B12n` |
|---|---:|
| 113MSDCF | 1.0014 |
| flat-on-ruler-cpl | 1.0007 |
| leaf-2-cpl | 1.0010 |

Worst harm actually inflicted: **1.0014**, i.e. **0.14%**, against a registered
tolerance of 1.03. The rule's mistakes in this direction are cheap.

**FALSE-OFF** — left off where it would have helped (a benefit forgone):

| stack | benefit forgone |
|---|---:|
| 119MSDCF | 0.0021 |
| lead-1-cpl | 0.0019 |

- **P4 (MEASURED).** The rule's errors are **asymmetric and both small**: three
  false-ONs costing ≤0.14% each, two false-OFFs forgoing ≤0.21% each. No
  single decision is expensive; the aggregate win rests elsewhere (§7.3).

### 4.3 Sensitivity arm — raw `B12`

| | `S_auto` | `S_on` | `T*` | n ON |
|---|---:|---:|---:|---:|
| raw `B12` | 0.970714 | 0.973246 | 8.4537 | 7/14 |

Still beats always-on, but the threshold moves from 1.84% to 8.45% and the rule
declines half the corpus. **The conclusion "auto beats always-on" is robust to
the loss; the specific threshold is not.**

---

## 5. The placebo

Drift values were shuffled against stacks and the *entire* selection re-run,
2000 times, seed 20260125.

| quantity | value |
|---|---|
| `p_placebo` | **0.0190** |
| placebo mean / sd | 0.973012 / 0.006939 |
| placebo best / worst | 0.963481 / 0.992623 |
| **fraction of shuffles that still beat always-on** | **0.305** |

- **P5 (MEASURED).** A shuffled predictor reproduces the observed `S_auto` in
  1.9% of runs. The scoring is not degenerate.
- **P6 (MEASURED, and a caution).** **30.5% of shuffled predictors still beat
  always-on.** "Beats always-on" is therefore a *weak* bar on this corpus — a
  nearly-1-in-3 coin. This is a caveat the pre-registration did not anticipate
  and it is reported because it weakens, not strengthens, the result. The
  placebo's real discriminating power is in the *magnitude* (p = 0.019), not in
  the sign of the comparison.

---

## 6. The pre-registered self-test failed, and why that is disclosed rather than hidden

Registered self-test **A** demanded that LOO on a synthetic separable plant
recover `S_auto` equal to the oracle to within `1e-12`. **It failed**, at
0.967857 vs 0.965000 — a delta of exactly +0.002857 = 0.04/14.

**First hypothesis: refuted by its own test.** I supposed an exact tie caused by
equally-spaced plant values. The sweep refuted it: moving the boundary point made
the deviation *worse* (+0.005714), and 68.2% of 2000 random spacings deviate.
The hypothesis was wrong and is recorded as wrong
(`src/diagnose_selftest.py`).

**The real cause — the bar was unsatisfiable as written.** Each held-out loss is
either `b_i` or `1.0`, while the oracle's loss is `min(b_i, 1.0)`, which is ≤
both. Therefore

> **`S_auto ≥ S_oracle` holds for every decision rule, by construction.**

Equality is unreachable whenever any fold decides differently from the oracle,
and LOO additionally mis-decides boundary-adjacent folds because removing a
boundary point moves the fitted midpoint across the held-out value.

- **P7 (DERIVED).** The registered self-test A was **unsatisfiable as written**.
  The measured delta ranged over `[+0.000000, +0.005714]` across 2000 random
  plants and was **never negative** — consistent with the proof.
- **P8 (DERIVED).** **The direction matters and it is the safe one.** The bias is
  always toward a *worse* `S_auto`, so it can only make C1 **harder** to pass.
  A rule that cleared C1 cleared it *despite* this penalty.

**Amendment A′**, committed at **`cc11892`** before any real score was read:
beat both degenerate baselines on a separable plant, and disagree with the oracle
on at most 2 folds. Both pass. **A's failure is still printed by the scorer on
every run** rather than deleted.

---

## 7. Robustness — post-hoc diagnostics that can only weaken the claim

Two warning signs that the pre-registration could not have anticipated —
bimodal fold thresholds (1.839 / 8.454) and C4 passing at *exactly* its 12/14 bar
— motivated `src/robust.py`. These are **post-hoc and declared as such**; they
were designed only to attack the result, never to rescue it.

### 7.1 D1 — the training objective is flat

`S` changes by less than 0.001 for every threshold in **T ∈ [1.64, 8.45]** (7 of
15 candidates). **The corpus cannot distinguish "decline the lowest stack" from
"decline the lowest seven."** The value 1.8392 is not meaningfully located.

### 7.2 D2 — C1 survives only 12 of 14 single-subject deletions

| dropped | margin | C1 |
|---|---:|---|
| **bee-3-cpl** | **−0.000312** | **FAIL** |
| **bee-2-cpl** | **−0.000312** | **FAIL** |
| any other single stack | +0.0032 … +0.0048 | pass |

### 7.3 D3 — one stack is the whole result

Decomposing the margin exactly (contribution = `(B12n_i − 1)/14` for each
declined stack):

| stack | contribution to margin |
|---|---:|
| **bee-3-cpl** | **+0.0045205** |
| bee-2-cpl | +0.0001134 |
| lead-1-cpl | −0.0001369 |
| 119MSDCF | −0.0001529 |
| **total** | **+0.0043440** |

- **P9 (MEASURED).** **`bee-3-cpl` alone contributes 104.1% of the winning
  margin.** Every other stack in the corpus is, on net, negative. The rule's
  entire measured advantage is the ability to decline one subject.

### 7.4 D5 — the sample size that would settle it

Bootstrap over subjects (500 trials for C1; 60 for the drop-one arm). A bootstrap
cannot manufacture new subjects, so this bounds the **precision** limb only and is
an **optimistic floor** on the true requirement.

| m | C1 satisfied | C1 also survives drop-one |
|---:|---:|---:|
| **14** (today) | **75.0%** | **38.3%** |
| 20 | 89.4% | 63.3% |
| 30 | 96.6% | 78.3% |
| **50** | 99.6% | **100.0%** |

- **P10 (MEASURED, optimistic floor).** **≈20 subjects** for C1 alone at 80%
  confidence; **≈50 subjects** for a C1 that also survives dropping any single
  subject. At today's m = 14, C1 holds in only **75%** of resamples — **the
  corpus is below its own 80% bar**, and the observed pass sits inside that 75%.

### 7.5 What this adds up to

- **P11 (ARGUED).** `auto` is **justified as opt-in** and **not justified as a
  default**. All six registered criteria passed, but the pass is one subject
  deep, the threshold is unlocated within a factor of five, and the corpus is
  underpowered by its own bootstrap. The brief's instruction not to move the
  default is not merely procedural caution — **this evidence is the reason it is
  correct.**

The shipped code says so itself: every `auto` decision prints the caveat inline
(§8), so nobody can read the decision without reading its limits.

---

## 8. What shipped

`STREHL_PHOTOMETRIC` and `--photometric` now take **`off` | `on` | `auto`**.

**The default is `off` and did not move.** `auto` is opt-in.

### 8.1 `unknown` does not collapse into `no` (discipline 862)

Four named abstentions, each printed with its reason and its numbers:

| code | condition |
|---|---|
| **U1** | frame count outside the measured domain `33..=100` |
| **U2** | drift unavailable (estimator folded no usable level) |
| **U3** | background region too small to fit a map (`kept < 1024` px) |
| **U4** | correction is a provable no-op (span == 1.0, or every frame refused) |

An abstention **falls back to the default loudly**, naming the reason. The
precedent this deliberately does not repeat is `STREHL_FIX_CA`, which is a
**silent no-op** under `STREHL_ALIGN=0` — `unknown` collapsed into `no`, already
flagged by fact-level review.

A real decline, live on `bee-3-cpl`:

```
mode            : auto (decides after pass one, from this stack's drift)
--- photometric auto decision (M125) ---
drift estimator : mean CFA G1 level over the active area, per frame, read
                  before registration and before any gain (M24's, promoted)
measured drift  : 1.1156% peak-to-peak over 40 frame(s)
threshold       : 1.84% (leave-one-out over M122's 14-stack corpus;
                  pre-registered before scoring)
AUTO: DECLINED   drift 1.116% is below the 1.84% threshold
  CAVEAT        : ... 104% of that margin is a single stack (bee-3-cpl).
                  ... enough to offer auto as opt-in and NOT enough to move
                  the default, which is why the default did not move.
```

### 8.2 Two behaviour changes, both deliberate

- **U3 asymmetry.** `kept < 1024` px remains a **hard error under explicit
  `on`** — the caller demanded a correction that cannot be fitted. Under `auto`
  it becomes a **loud abstention that still renders**, because the caller asked
  for a *decision*, and "there is no background to measure" is a legitimate
  answer. This is what lets `coffee-bubbles` render (§3).
- **Unrecognised spellings are refused, not guessed.** The predecessor read the
  environment as `!v.is_empty() && v != "0"`, which meant **`STREHL_PHOTOMETRIC=off`
  turned the correction ON** — a value whose plain meaning was the exact opposite
  of its effect.
  - **P12 (MEASURED).** Verified safe to change: the only script setting the
    variable sets it to `1`. Confirmed live — `banana` and `2` now exit 1 with a
    message naming the accepted spellings; `off`, `on`, `auto`, `AUTO` and unset
    all behave correctly.

`auto` cannot decide before pass one (drift is unknown until frames are read), so
it builds the region and folds flux **as if on**, then keeps or discards the map.
A declined `auto` therefore costs one extra decode plus the per-frame flux and
`Dpp` folds. **Output identity is proven by hash below, not argued from the
code.**

---

## 9. Proof by hash (rule 39)

Binaries: baseline (control, `b5b4142`)
`BE5E1760833BE0B920E5E1E96BC7C9C00D84B96A3EFD012C1A99A93B2B9236F8`;
M125 `60DEC43357FAA49E1A0E15E3E2669DADA15916BD80FA03B78DFEEB845604764C`.

All hashes are SHA-256 of the linear 16-bit TIFF (not `--srgb`). Full ledger in
`C:\dev\strehl-out\M125\ledger-proof.csv`.

| stack | arms proven identical | SHA-256 |
|---|---|---|
| tweezers-cpl | OLD-default · NEW-unset · NEW-off · NEW-env-off | `4881EC4E…C6834B9` |
| tweezers-cpl | NEW-on · NEW-bare-flag · **NEW-auto (accepted)** | `1259416C…D7313534` |
| bee-3-cpl | OLD-default · NEW-unset · NEW-off · NEW-env-off · **NEW-auto (declined)** | `478387EF…54E57015` |
| bee-3-cpl | NEW-on · NEW-bare-flag | `0D232054…ACA9504E` |

- **P13 (MEASURED).** With `off`, and with **no environment variable set at
  all**, output is **byte-identical to the current binary** on both stacks.
- **P14 (MEASURED).** `auto` on a stack the rule **declines** is byte-identical
  to `off`; `auto` on a stack the rule **accepts** is byte-identical to `on`.
  **The rule is provably nothing but a switch — it does not perturb the
  correction itself.**
- **P15 (MEASURED).** Three deliberate **plants** (H4a/H4b/H4c) were rendered to
  confirm the harness *can* report inequality; all three correctly reported
  DIFFERENT. A proof that cannot fail is not a proof.
- Bare `--photometric` (no value) remains backwards-compatible with the old
  boolean flag, proven by H3b.

---

## 10. Tests, lint, formatting

Measured, not derived. The HEAD baseline was taken in an **isolated git worktree
at `609cd45`** so that no other agent's uncommitted work was included.

| tree | result |
|---|---|
| HEAD `609cd45`, worktree, unmodified | **489 passed / 0 failed / 1 ignored** |
| HEAD + M125 | **506 passed / 0 failed / 1 ignored** |
| delta | **+17**, all in `strehl-core` (369 vs 352) |

Full rebuild with `Compiling` lines present for all four workspace crates (rule
33); `-q` was not used.

**On the brief's reference figure.** The brief cites 454/0/1 at `8a46b47`. HEAD
is far ahead of that commit and other agents have added tests since, so 454 is
not a valid comparator today; **489 at `609cd45` is**. Both are reported so the
discrepancy is visible rather than silently reconciled.

**Clippy.** Two warnings in my code, both fixed (`neg_cmp_op_on_partial_ord` in
`LevelDrift::dpp`; `assertions_on_constants` on the threshold tripwire test,
where the constant *is* what is under test, so an `#[allow]` with a stated reason
is correct). `photometric.rs` now produces **zero** clippy warnings. Four
warnings remain in `softgate.rs` — **pre-existing, not mine, not touched.**

**Formatting.** The tree is not rustfmt-clean at HEAD (a file I never touched has
9 hunks at `609cd45`), so `cargo fmt --check` cannot be read as a pass/fail gate
here. Measured per-file against HEAD instead:

| file | HEAD hunks | M125 hunks | verdict |
|---|---:|---:|---|
| photometric.rs | 10 | **9** | no new debt (one better) |
| merge_cmd.rs | 6 | 6 | no new debt |
| main.rs | 13 | 13 | no new debt |

Only my own hunks were fixed; the 29 pre-existing ones were deliberately left
alone so that other agents' lines do not appear in my commit.

---

## 11. Candidate facts

| # | label | fact |
|---|---|---|
| **P1** | MEASURED | Raw `B12` conflates global level with blotch: `113MSDCF`'s entire 1.0699 is a 6.84% level move; `B12n` = 1.0014. |
| **P2** | ARGUED | `B12n` is comparable across subjects as a within-stack ratio with level divided out; it is not an absolute quality scale. |
| **P3** | MEASURED | The promoted Rust drift estimator reproduces M24 on 3/3 CLI-reachable stacks within ±0.004 pp. |
| **P4** | MEASURED | The rule's errors are asymmetric and individually cheap: 3 false-ON ≤0.14% harm; 2 false-OFF ≤0.21% forgone. |
| **P5** | MEASURED | Shuffled-drift placebo reproduces the observed `S_auto` in 1.9% of 2000 runs. |
| **P6** | MEASURED | **30.5%** of shuffled predictors still beat always-on: "beats always-on" is a weak bar on this corpus. |
| **P7** | DERIVED | Registered self-test A was unsatisfiable as written: `S_auto ≥ S_oracle` for every rule, by construction. |
| **P8** | DERIVED | That bias runs toward a *worse* `S_auto`, so it can only make C1 harder; a rule that passed did so despite it. |
| **P9** | MEASURED | **`bee-3-cpl` alone contributes 104.1% of `auto`'s winning margin**; every other stack is net negative. |
| **P10** | MEASURED | ≈20 subjects needed for C1, ≈50 for a C1 surviving drop-one (optimistic floor). At m=14, C1 holds in only 75% of resamples. |
| **P11** | ARGUED | `auto` is justified as opt-in and **not** as a default; the evidence is one subject deep and the threshold unlocated over [1.64, 8.45]. |
| **P12** | MEASURED | The old env parse (`!v.is_empty() && v != "0"`) made `STREHL_PHOTOMETRIC=off` turn the correction **ON**; now refused. Only script use was `=1`. |
| **P13** | MEASURED | `off` and unset are byte-identical (SHA-256) to the current binary on `tweezers-cpl` and `bee-3-cpl`. |
| **P14** | MEASURED | `auto`-declined ≡ `off`; `auto`-accepted ≡ `on`, byte-identical. The rule is provably nothing but a switch. |
| **P15** | MEASURED | Three planted mismatches were correctly reported DIFFERENT, showing the hash harness can fail. |
| **P16** | MEASURED | Test suite 506/0/1 with M125 vs 489/0/1 at HEAD `609cd45`; +17 tests, all `strehl-core`. |
| **P17** | UNDETERMINED | Whether the 1.84% threshold is the *right* threshold. D1 shows the objective flat over [1.64, 8.45]; the corpus cannot locate it. |
| **P18** | UNDETERMINED | Whether `auto` helps on stacks with 101–298 frames, or fewer than 33. Outside the measured domain; `auto` abstains (U1) rather than extrapolating. |

---

## 12. Prior art consulted (rule 40)

`M122-photometric-promotion` (the `B12` statistic, the 14-stack table, the
KEEP-OFF verdict being extended, not overridden) · `M24-photometric-drift-measured`
(the estimator and its four reference numbers) · `M99-photometric` (geometry vs
camera) · `M91-photometry` (normalisation measured, priced, not shipped) ·
`M97q-photometric-wiring` (how `photometric.rs` reaches the merge) ·
`M103-halfdrift` (the alignment solve absorbs ~half the level change — the reason
drift is read *before* the warp) · `M100-exposure` / `M105b-exposure-ship`
(surfaced by `prior_art.py`, not in the brief).

SYNTHESIS facts 1675–1681, 1682–1687; disciplines 862 (three-valued modes) and
866.

**No `M125` ledger row exists in `AGENTS.md`.** That file is ORCH's; this report
does not edit it, `SYNTHESIS.md`, `docs/captures-needed.md`, `README.md`,
`scripts/corpus_lint.py`, or anything under `experiments/ORCH-drift-check/`.

---

## 13. What ORCH should do

1. **Fold P1–P18.** P9, P10 and P11 are the load-bearing ones.
2. **Raise a capture request for more subjects.** ≈50 to make this rule robust
   enough to *consider* moving the default; ≈20 for C1 alone. Both are optimistic
   floors. **Subject diversity matters more than frame count** — the corpus is
   short of *subjects*, not of frames.
3. **Do not schedule a default-promotion GO/NO-GO on this evidence.** P9 and P10
   say it would be premature.
4. Note the `STREHL_FIX_CA` silent no-op under `STREHL_ALIGN=0` remains
   outstanding — the same `unknown`-collapsed-into-`no` defect that discipline
   862 exists to prevent, and that M125 fixed only for photometric.

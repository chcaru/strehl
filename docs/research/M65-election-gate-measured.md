# M65 — `n_eff` under regularised versus raw election, at a matched tolerance, on real frames

**Status:** measurement complete. Facts are numbered locally from 1; the orchestrator
renumbers on fold.

**Pre-registration:** `experiments/M65-election-gate/PREREGISTRATION.md`, committed as
**`b695e5b`** before any arm was run. Where this report and that file disagree, that file
is the record.

---

## Headline

**Swapping the election field — electing the merge's winner on the raw focus field instead
of the regularised one, with the tolerance, the operator, the field the gate reads, the
noise model, the stack and the frames all held bit-identical — moves mean `n_eff` at the
shipped default gate by at most 23.35%, on every one of four real stacks, against a
materiality bar of 1.332 fixed in advance. The pre-registered decision D1 therefore returns
*NOT load-bearing*.**

**But the answer is gate-dependent, and the pre-registration did not anticipate that.** At
the shipped default (gate 4.0) the effect is below the bar on all four stacks. At gate 0.5 —
the tightest rung the product exposes — it is **above** the bar on all four stacks, reaching
**2.56×** on `113MSDCF`. The regulariser is not load-bearing for the gate *as the gate is
shipped*; the claim "not load-bearing" does not extend across the exposed knob's range.

**And the category error M60c derived is now measured.** On `113MSDCF`, **56.70%** of the
plane elects a *different frame* under raw versus regularised election, while the fully
unregularised, unit-matched arm changes mean `n_eff` at the shipped gate by **0.44%**. The
index map moves on more than half the plane and the acceptance set does not move at all.

**Control K5 is reported NOT MET.** Two sub-criteria failed, on every stack. One failure is
a defect in a criterion I wrote — my own §5 derivation, in the same pre-registration, proves
arm W could never satisfy it. The other is a mis-chosen ladder rung. By the letter of §4.3
this **voids D1 on all four stacks**. §7 diagnoses both and reports the post-hoc repair
measurement; the repair is weaker evidence than a clean pre-registered pass and is labelled
as such.

---

## 1. Prior art searched and read (rule 40)

M60c named this measurement and did not run it. I searched for anyone who had.

**Searches run** over `docs/research/**` and `experiments/**`: `n_eff`, `regularis`,
`electi`, `winner`, `gate`, then a decisive narrowing pass for `unregularis`,
`without the regulariser`, `regulariser off`, `raw election`, `elect(ing|ed|ion) on`.

**Read in full or in the relevant part:**

| file | why it mattered | did it already answer this? |
| --- | --- | --- |
| `M60c-speckle-citation-and-the-gate.md` | my direct predecessor; G12/G13/G14 are the hypotheses under test; names this exact measurement and declines to run it | **no, by design** |
| `M2-verification.md` §4 | the four speckle rows M60c traced fact 23 to; confirms the operator there is the retired **ring difference**, not Tenengrad | no — index-map quantity, no `n_eff` |
| `M62-sqrt-n.md` §§1–4, 6.2, 7.4, 11 + `experiments/M62-sqrt-n/src/11-focus-guard.py` | the existing `n_eff` instrumentation and its `109MSDCF` baselines (0.064–0.227 of N); §11's warning that `109MSDCF` is the corpus's easiest stack | no — one election field only |
| `M52-gate-cluster-verified.md` §5.1, §5.2, facts 324/436 | the gate's endpoint behaviour and the two comparators I use in §6: operator spread **4.54×** and stack spread **12.22×** in `n_eff` at gate 2.0 | no |
| `M18-merge-implemented.md` :228 and `M39-verify-detail-metric.md` :409 | fact 343's `1.0678×` unregularised-argmax arm, which M60c cites as pointing the other way | no — a flat-ROI noise ratio, not `n_eff` |
| `M9-support-coupling-measured.md` :46 | the closest prior *design*: a placebo run electing the winner on G1 and evaluating on G2 | no — support-width study, no gate arm |
| `M15-regulariser-window-measured.md`, `M53-flat-ratio.md`, `M53-flat-roi-statistic.md`, `M56/M58/M58b/M58c` | every other place the regulariser or "unregularised argmax" is measured or cited | no |
| `crates/strehl-core/src/merge.rs` | `Gate` (`:242`, doc `:195–236`), `FOCUS_NOISE_SD` (`:185`), `regularise` (`:191`), `FocusStats::beats` (`:375`), `Estimator::fold_inner` (`:693`), `mean_n_eff` (`:989`), calibration test (`:1197`) | — |
| `crates/strehl-cli/src/merge_cmd.rs`, `crates/strehl-cli/examples/m60-disagreement.rs` | the pipeline the harness mirrors, and the additive-example template | — |

**Fact 1 (MEASURED).** No prior report in `docs/research/` or `experiments/` measures
`n_eff` under a swapped election field. The nearest prior arms — fact 343's unregularised
argmax and M9's G1/G2 placebo — report flat-ROI noise ratios and regret, not acceptance-set
size. The measurement M60c named had not been run.

---

## 2. What was run

Instrument: `crates/strehl-cli/examples/m65-election.rs`. **Additive** — it modifies no
shared crate code and no shipped behaviour. It mirrors `merge_cmd.rs`'s two passes serially
and calls the shipped `FocusField::compute`, `regularise`, `FocusStats`, `Gate::admits` and
`Estimator`.

Arms, per the pre-registration §1 (`tau(t) = t·√2·FOCUS_NOISE_SD`):

| arm | winner index | reference the gate compares against | field read | tolerance |
| --- | --- | --- | --- | --- |
| **R** shipped | `argmax reg` | `max reg` | `reg` | `tau(t)` |
| **W** the arm M60c named | `argmax raw` | `reg` **at that index** | `reg` | `tau(t)` |
| **X** regulariser off, matched numeric tolerance | `argmax raw` | `max raw` | `raw` | `tau(t)` |
| **X′** regulariser off, matched noise-unit tolerance | `argmax raw` | `max raw` | `raw` | `tau(t)·k_sd` |

Stacks, all read-only from `D:\personal\macro`, all `3516 × 2344` = 8,241,504 px:
`119MSDCF` (33 frames, ISO 50, CPL off), `109MSDCF` (22, ISO 160, CPL off), `113MSDCF`
(63, ISO 500, CPL off), `coffee-bubbles` (19, ISO 1000, **CPL on**). The CPL straddle is
bounded exactly as pre-registered: the observable is a within-stack paired contrast on
identical decoded frames, so the filter cannot enter an arm difference; it can only affect
how one stack's ratio compares with another's, and the ISO reading is taken off the
CPL-off ladder.

Logs: `experiments/M65-election-gate/out/*.log`.

---

## 3. Controls first (pre-registration §4.3: no arm ratio is believed until these are reported)

| id | outcome | evidence |
| --- | --- | --- |
| **K1** replicated pure-noise procedure reproduces `FOCUS_NOISE_SD` | **PASS** | `σ_reg = 1.521409e-2 ± 7.468e-5` against the declared `1.521400e-2` — **0.00 SEM away**, bar was 4 SEM |
| **K2** harness's counter is the shipped one | **PASS** | exact f64 equality on every stack, e.g. `113MSDCF` arm R harness `8.580934863` = `Estimator::mean_n_eff()` `8.580934863`; arm X `6.924616187` = `6.924616187` |
| **K3** serial harness reproduces the shipped parallel CLI | **PASS** | see table below; worst relative difference **< 0.02%**, bar was 0.1% |
| **K4** the arm difference is carried only by disagreeing elections | **PASS** | **0 violations** over 6 gates × 4 stacks: no pixel with `win_R == win_W` had `n_R != n_W` |
| **K5** the plant can express the failure at both ends | **NOT MET** | §7 |
| **K6** the raw election reproduces the shipped tie-break | **PASS** | **0 mismatched px of 8,241,504** on every stack against `FocusStats(raw).best_index()` |

**Fact 2 (MEASURED — K3).** The serial harness's arm R reproduces the shipped parallel
`strehl merge` gate ladder on all four stacks:

| stack | gate 0.5 | 1.0 | 2.0 | 4.0 |
| --- | --- | --- | --- | --- |
| `109MSDCF` CLI / harness | 1.414 / 1.41357 | 1.884 / 1.88441 | 2.891 / 2.89097 | 4.987 / 4.98655 |
| `119MSDCF` | 1.399 / 1.39888 | 1.855 / 1.85515 | 2.847 / 2.84713 | 4.723 / 4.72303 |
| `113MSDCF` | 1.432 / 1.43222 | 2.194 / 2.19373 | 4.761 / 4.76102 | 8.581 / 8.58093 |
| `coffee-bubbles` | 1.238 / 1.23821 | 1.504 / 1.50397 | 2.109 / 2.10912 | 3.529 / 3.52885 |

The `109MSDCF` row also reproduces the ladder published in `merge_cmd.rs`'s own docs, which
is where the 1.332 materiality bar was taken from — the bar and the arms are computed off
the same pipeline.

**Fact 3 (MEASURED — K1, and new).** The 17×17 regulariser reduces the pure-noise focus
response SD from `1.883040e-2` to `1.521409e-2`. **`k_sd` = 1.23770** — the regulariser
removes only **19.2%** of the response noise, not the ~17× a 289-tap box mean of independent
samples would give. The reason is structural: the focus operator already averages a 27×27
window (`WINDOW_RADIUS = 13`), so neighbouring raw responses are heavily correlated before
the box mean sees them.

**Fact 4 (DERIVED from fact 3).** Fact 3 is the mechanism behind M60c's G14. The gate
compares a *difference of responses* against a tolerance proportional to the noise scale of
the field it reads. If regularising changes that scale by only 1.24×, the ratio the gate
actually uses is near-invariant to which field it reads, and arms R and X must sit close
together. They do: `|1 − rho_X|` at gate 4.0 is 3.7%, 3.4%, 19.3% and 7.2% across the four
stacks. **G14 is supported by measurement.**

*(K1 is deterministic — 12 fixed seeds — so it reproduces bit-identically on every run. It
is a re-derivation of the crate's constant, not six independent samples.)*

---

## 4. The primary result

**Fact 5 (MEASURED).** Mean `n_eff` by arm and gate, whole plane, four stacks.
`rho_A = mean n_eff(A) / mean n_eff(R)`; `dev(rho) = max(rho, 1/rho)`; bar = **1.332**.

`109MSDCF` — 22 frames, ISO 160

| gate | R | W | X | X′ | rho_W | rho_X | rho_X′ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.00 | 1.00000 | 1.58822 | 1.00000 | 1.00000 | 1.5882 | 1.0000 | 1.0000 |
| 0.50 | 1.41357 | 1.90566 | 1.36278 | 1.45748 | **1.3481** | 0.9641 | 1.0311 |
| 1.00 | 1.88441 | 2.33100 | 1.77993 | 1.99313 | 1.2370 | 0.9446 | 1.0577 |
| 2.00 | 2.89097 | 3.31299 | 2.71887 | 3.19325 | 1.1460 | 0.9405 | 1.1046 |
| **4.00** | **4.98655** | **5.39874** | **4.79988** | **5.88143** | **1.0827** | 0.9626 | 1.1795 |
| 64.00 | 20.99530 | 21.05565 | 20.88033 | 21.12160 | 1.0029 | 0.9945 | 1.0060 |

`119MSDCF` — 33 frames, ISO 50

| gate | R | W | X | X′ | rho_W | rho_X | rho_X′ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.00 | 1.00000 | 1.68244 | 1.00000 | 1.00000 | 1.6824 | 1.0000 | 1.0000 |
| 0.50 | 1.39888 | 1.99075 | 1.35281 | 1.44563 | **1.4231** | 0.9671 | 1.0334 |
| 1.00 | 1.85515 | 2.40699 | 1.76270 | 1.97310 | 1.2975 | 0.9502 | 1.0636 |
| 2.00 | 2.84713 | 3.37638 | 2.68619 | 3.14234 | 1.1859 | 0.9435 | 1.1037 |
| **4.00** | **4.72303** | **5.23143** | **4.56226** | **5.40427** | **1.1076** | 0.9660 | 1.1442 |
| 64.00 | 30.03333 | 30.15948 | 29.97915 | 30.47129 | 1.0042 | 0.9982 | 1.0146 |

`113MSDCF` — 63 frames, ISO 500

| gate | R | W | X | X′ | rho_W | rho_X | rho_X′ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.00 | 1.00000 | 2.85118 | 1.00000 | 1.00000 | 2.8512 | 1.0000 | 1.0000 |
| 0.50 | 1.43222 | 3.66546 | 1.24559 | 1.31954 | **2.5593** | 0.8697 | 0.9213 |
| 1.00 | 2.19373 | 4.79137 | 1.60832 | 1.83506 | **2.1841** | 0.7331 | 0.8365 |
| 2.00 | 4.76102 | 7.27449 | 2.85083 | 3.70918 | **1.5279** | 0.5988 | 0.7791 |
| **4.00** | **8.58093** | **10.11964** | **6.92462** | **8.54355** | **1.1793** | 0.8070 | **0.9956** |
| 64.00 | 35.95865 | 36.76194 | 34.98524 | 39.15770 | 1.0223 | 0.9729 | 1.0890 |

`coffee-bubbles` — 19 frames, ISO 1000, **CPL on**

| gate | R | W | X | X′ | rho_W | rho_X | rho_X′ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.00 | 1.00000 | 1.93639 | 1.00000 | 1.00000 | 1.9364 | 1.0000 | 1.0000 |
| 0.50 | 1.23821 | 2.14748 | 1.17691 | 1.22327 | **1.7343** | 0.9505 | 0.9879 |
| 1.00 | 1.50397 | 2.39736 | 1.38359 | 1.49288 | **1.5940** | 0.9200 | 0.9926 |
| 2.00 | 2.10912 | 2.98559 | 1.89452 | 2.18396 | **1.4156** | 0.8982 | 1.0355 |
| **4.00** | **3.52885** | **4.35276** | **3.27400** | **4.01767** | **1.2335** | 0.9278 | 1.1385 |
| 64.00 | 17.28982 | 17.43737 | 17.11129 | 17.42082 | 1.0085 | 0.9897 | 1.0076 |

### 4.1 D1 — the primary decision, arm W, at the shipped default gate 4.0

**Fact 6 (MEASURED).** `dev(rho_W)` at gate 4.0: **1.0827** (`109`), **1.1076** (`119`),
**1.1793** (`113`), **1.2335** (`coffee-bubbles`). The maximum, **1.2335**, is below the
1.332 bar on **every** stack.

**D1 verdict as pre-registered: the election field is NOT load-bearing for the gate at the
shipped default.** The `dev(rho_W) < 1.05` sub-clause — "indistinguishable from a no-op" —
is **NOT met**: the largest effect reaches 70% of the bar's margin. The result is *below the
smallest rung of the exposed knob*, not *absent*.

*(This verdict is subject to the K5 void reported in §7. Read §7 before acting on it.)*

### 4.2 D2 — arm X′, the genuinely open comparison

**Fact 7 (MEASURED).** `dev(rho_X′)` at gate 4.0: **1.1795**, **1.1442**, **1.0044**,
**1.1385**. All below 1.332. **D2 returns NOT load-bearing, agreeing with D1.** The
pre-registered "if D1 and D2 disagree I will report a split" clause is not triggered.

**Fact 8 (MEASURED).** Arm X′ does not cross the bar **at any gate on any stack**. Its
largest deviation anywhere in the 24-cell grid is `rho_X′ = 0.7791` at gate 2.0 on
`113MSDCF`, `dev` = **1.2835**. Turning the regulariser off entirely, at a unit-matched
tolerance, never moves mean `n_eff` by as much as one rung of the shipped gate ladder.

Note the sign: unlike arm W, arm X′'s deviation is **two-sided** — it is above 1 on three
stacks at gate 4.0 and below 1 on `113MSDCF` at gates 0.5–4.0. Arm X′ carries no arithmetic
guarantee (pre-registration §5) and its sign is therefore informative; it is not consistent
in direction across stacks.

### 4.3 D3 — arm X, reported and flagged confounded

**Fact 9 (MEASURED, CONFOUNDED).** `rho_X` at gate 4.0: 0.9626, 0.9660, 0.8070, 0.9278 —
below 1 on every stack and at every non-zero gate, i.e. the raw field at an unadjusted
numeric tolerance admits **fewer** frames. This is what fact 3 predicts arithmetically: the
raw field's noise is 1.2377× larger, so the same numeric tolerance is a 1.2377× *tighter*
gate in noise units. **No conclusion about the regulariser is drawn from arm X.** It is
reported because the gap between X and X′ is the size of the units confound, and that gap is
large: at gate 2.0 on `113MSDCF` it is 2.85083 vs 3.70918, a 30% difference produced by
nothing but the unit convention.

### 4.4 The gate dependence — the finding the pre-registration did not anticipate

**Fact 10 (MEASURED).** `dev(rho_W)` against the 1.332 bar, by gate:

| gate | `109` | `119` | `113` | `bubbles` | stacks over the bar |
| --- | --- | --- | --- | --- | --- |
| 0.50 | 1.3481 | 1.4231 | 2.5593 | 1.7343 | **4 of 4** |
| 1.00 | 1.2370 | 1.2975 | 2.1841 | 1.5940 | 2 of 4 |
| 2.00 | 1.1460 | 1.1859 | 1.5279 | 1.4156 | 2 of 4 |
| **4.00** | 1.0827 | 1.1076 | 1.1793 | 1.2335 | **0 of 4** |
| 64.00 | 1.0029 | 1.0042 | 1.0223 | 1.0085 | 0 of 4 |

**`dev(rho_W)` is monotone decreasing in the gate on every stack.** D1 pinned the decision
to gate 4.0 — the shipped default, and the loosest rung a user would normally reach. That
choice was made before any result was seen, and it is the right anchor for a claim about the
shipped product. It is also, in hindsight, the rung most favourable to a null.

**Fact 11 (DERIVED from fact 5 and pre-registration §5).** The mechanism is the reference
shift. Arm W's reference `reg[win_W]` sits *below* `max reg` by some amount `δ[i] ≥ 0`, so
arm W's admission band is the shipped band widened by `δ`. The *relative* size of that
widening is `δ/tau`, and `tau` grows linearly in the gate while `δ` does not depend on the
gate at all. A fixed reference shift is therefore material against a narrow band and
negligible against a wide one. Nothing about the world changes across the rows of fact 10;
only the yardstick does.

**ARGUED.** The honest statement of scope is: *the regulariser is not load-bearing for the
gate at the tolerance the product ships at, and is load-bearing at the tightest tolerance the
product exposes.* A one-line "not load-bearing" would be true of the default and false of the
knob. I decline to compress it further.

---

## 5. D4 — index versus value, M60c's G12, measured

**Fact 12 (MEASURED).** Election disagreement rate `P(win_R ≠ win_W)` — a property of the
winner **index map** — beside the change in the acceptance set at the shipped gate:

| stack | N | ISO | `P(win_R ≠ win_W)` | `rho_W` @4.0 | `rho_X′` @4.0 |
| --- | --- | --- | --- | --- | --- |
| `119MSDCF` | 33 | 50 | 27.71% | 1.1076 | 1.1442 |
| `109MSDCF` | 22 | 160 | 28.56% | 1.0827 | 1.1795 |
| `113MSDCF` | 63 | 500 | **56.70%** | 1.1793 | **0.9956** |
| `coffee-bubbles` | 19 | 1000 | 44.45% | 1.2335 | 1.1385 |

**This is M60c's G12, measured.** On `113MSDCF` the two elections choose a different frame
at **4,672,905 of 8,241,504 pixels** — more than half the plane — and the fully
unregularised, unit-matched merge admits a set whose mean size differs by **0.44%**
(8.58093 → 8.54355). A quantity defined on the index map moved by 56.70%; the quantity the
gate is defined on moved by less than one part in two hundred. **Speckle-like incoherence of
the winner index map is not the acceptance set, and cannot be used to argue about it.**

**Fact 13 (MEASURED).** Paired per-pixel differences at gate 4.0 confirm this is not an
averaging artefact — the arms differ *violently* pixel by pixel while their means barely
move:

| stack | `n_W − n_R` mean | range | non-zero px | `n_X′ − n_R` mean | range | non-zero px |
| --- | --- | --- | --- | --- | --- | --- |
| `109` | +0.41219 | `[+0, +21]` | 14.64% | +0.89488 | `[−15, +21]` | 63.72% |
| `119` | +0.50840 | `[+0, +32]` | 13.31% | +0.68123 | `[−24, +31]` | 59.74% |
| `113` | +1.53870 | `[+0, +62]` | 35.94% | **−0.03738** | `[−62, +60]` | **69.07%** |
| `bubbles` | +0.82391 | `[+0, +18]` | 26.74% | +0.48882 | `[−18, +18]` | 61.89% |

On `113MSDCF`, arm X′ differs from arm R at **69% of pixels**, by as much as **±62 frames** —
the entire stack — and the two means agree to 0.44%. The per-pixel disagreement is real and
enormous; it cancels in the mean.

**Fact 14 (MEASURED).** The `n_W − n_R` minimum is `+0` on all four stacks: no pixel anywhere
has `n_W < n_R`. This confirms pre-registration §5's derivation
(`A_W ⊇ A_R`, so `n_W[i] ≥ n_R[i]` identically) by direct measurement over 32,966,016
pixel-arm pairs. A derivation checked, not assumed.

### 5.1 Is the effect ISO-driven? A post-hoc probe, and a refusal

The four stacks differ in **N as well as ISO** (19, 22, 33, 63), and `n_eff` depends on both.
The pre-registration did not control for this. **POST-HOC**, I re-ran `119` and `113` at
`--limit 22` to match `109`'s frame count:

**Fact 15 (MEASURED, POST-HOC — not pre-registered).** At matched N = 22, CPL-off only:

| stack | ISO | `P(win_R ≠ win_W)` | `rho_W` @4.0 | `rho_X′` @4.0 |
| --- | --- | --- | --- | --- |
| `119MSDCF` | 50 | 24.16% | 1.0838 | 1.1638 |
| `109MSDCF` | 160 | 28.56% | 1.0827 | 1.1795 |
| `113MSDCF` | 500 | 36.58% | 1.0612 | 1.0543 |

**The index-map disagreement rises monotonically with ISO — 24.16% → 28.56% → 36.58% over a
10× ISO range — and `rho_W` does not move at all (1.0838, 1.0827, 1.0612).** This is the
sharpest form of fact 12: raising the sensor noise degrades the *winner index map* exactly as
a winner's-curse account of the argmax predicts, and leaves the *acceptance set* untouched.

It also shows the apparent ISO trend in the full-N table (1.1076 / 1.0827 / 1.1793) was
**N**, not ISO: `113MSDCF`'s `rho_W` falls from 1.1793 at N = 63 to 1.0612 at N = 22.

**Refused.** `--limit 22` truncates a 63-frame through-focus sweep rather than decimating it,
so the N-matched `113` arm covers less focus depth than the full stack. I therefore report
fact 15 as a **probe that removes one confound and introduces another**, and I do not claim a
clean ISO-independence result. Three points on one body is not an ISO curve.

---

## 6. How big is this compared with things already measured?

**Fact 16 (DERIVED, from fact 5 and M52 facts 324/436).** At gate 2.0 M52 measured mean
`n_eff` spreading **12.22×** across seven stacks and **4.54×** across five focus operators
each given its own correct noise constant. At the same gate this milestone measures the
election field moving `n_eff` by at most **1.53×**. **Choosing the stack matters ~8× more
than the election field; choosing the operator matters ~3× more.** Even at the gate where the
election field crosses the materiality bar, it is the smallest of the three knobs already
measured.

**Fact 17 (DERIVED, from fact 5).** Expressed in the currency the merge exists to buy — noise
reduction goes as `√n_eff` — the largest effect at the shipped gate, `rho_W = 1.2335`, is
`√1.2335` = **1.111×** in SNR, and the smallest, 1.0827, is **1.041×**. Roughly half the
size in the units that matter to a photograph.

---

## 7. Control K5: NOT MET, on every stack

**Fact 18 (MEASURED).** K5 as pre-registered required every arm to read mean `n_eff` = 1.000
at gate 0 and to reach the ceiling at gate 64. Outcome, by arm and stack:

| stack | arm R | arm W | arm X | arm X′ |
| --- | --- | --- | --- | --- |
| `109` | PASS | **FAIL** (gate 0 → 1.588217) | **FAIL** (gate 64 → 20.8803 of 22) | PASS |
| `119` | **FAIL** (gate 64 → 30.0333 of 33) | **FAIL** (both) | **FAIL** | **FAIL** |
| `113` | **FAIL** (gate 64 → 35.9586 of 63) | **FAIL** (both) | **FAIL** | **FAIL** |
| `bubbles` | **FAIL** (gate 64 → 17.2898 of 19) | **FAIL** (both) | **FAIL** | **FAIL** |

**K5 is NOT MET.** The pre-registration says an arm that cannot span the range "makes D1 void
on that stack". Applied literally, **D1 is void on all four stacks.** I am reporting that
rather than rewriting the criterion. Two distinct defects produced it, and they are not
equally serious.

### 7.1 Defect one: I pre-registered a criterion my own §5 proved unreachable

Arm W's gate-0 floor fails on all four stacks (1.588, 1.682, 2.851, 1.936). It **had** to.
Pre-registration §5 derives `n_W[i] ≥ n_R[i]` pointwise, with strict inequality wherever the
elections disagree — and the elections disagree on 27.7–56.7% of the plane (fact 12). At gate
0 the tolerance is exactly zero, so arm R reads 1.000 and arm W reads `1 + P(disagreement
admits an extra frame)`, necessarily above 1.

**This is a mis-specified criterion, not an instrument failure.** The same document that
defines K5 contains the proof that arm W cannot satisfy it. I did not notice the
contradiction when writing it. The correct floor criterion for arm W would have been "reads
1.000 when the elections agree", which is exactly what K4 tests — and K4 passes with **zero
violations**.

**This is disclosed, not reworded.** The criterion stands as written and stands as NOT MET.

### 7.2 Defect two: gate 64 is the wrong rung, and the right rung was already known

The ceiling failures are different in kind: they are a true statement about the data. At gate
64 the tolerance is `64·√2·0.015214` = **1.3771** in normalised-Tenengrad units, and on
`113MSDCF` that admits only 35.96 of 63 frames — 57%. **Real focus contrast on a through-focus
stack exceeds a 64σ tolerance over much of the plane.** That is consistent with the crate's own
`real_focus_contrast_is_far_larger_than_the_noise_scale` test and with M52 §5.1, which
measured the ceiling at gate **1e6**, not 64.

**Fact 19 (MEASURED, POST-HOC — the repair).** Extending the ladder to the rung M52 used:

| stack | N | gate 4 (R) | gate 1000 (R) | gate 1e6, **all four arms** |
| --- | --- | --- | --- | --- |
| `109` | 22 | 4.98655 | 22.00000 | **22.00000 = N** |
| `119` | 33 | 4.72303 | 32.99980 | **33.00000 = N** |
| `113` | 63 | 8.58093 | 63.00000 | **63.00000 = N** |
| `bubbles` | 19 | 3.52885 | 18.96883 | **19.00000 = N** |

**Every arm on every stack reaches exactly N.** The worry K5 existed to catch — that a null
result might mean a flat instrument rather than agreeing arms — is refuted by measurement:
arm R spans 1.0000 → N on all four stacks, and the instrument demonstrably produces large
ratios when a large ratio exists (`rho_W` = **2.8512** at gate 0 on `113MSDCF`). The null at
gate 4.0 is not a floor or ceiling effect.

**This repair is weaker evidence than a clean pre-registered pass, and I will not pretend
otherwise.** It was run after the arm results were known. It is labelled POST-HOC. The
correct reading is: *D1 is void by the letter of the pre-registration; the void is traceable
to two identified defects in the control's specification rather than to the arms; and a
re-run with a corrected K5 (floor conditioned on election agreement, ceiling at gate 1e6)
would be expected to pass.* That expectation is **ARGUED**, not measured — nobody has run the
corrected control as a pre-registration.

---

## 8. Answering M60c directly

| M60c finding | this milestone |
| --- | --- |
| **G12** — category error: speckle is a property of the winner *index map*, the gate admits on *value* | **CONFIRMED BY MEASUREMENT.** Facts 12, 13, 15. 56.70% index disagreement against 0.44% acceptance-set change on `113MSDCF`; index disagreement rises with ISO while `rho_W` does not |
| **G14** — the effect should be small because the tolerance is in units of a constant defined on the regularised field | **SUPPORTED, and the mechanism quantified.** Facts 3, 4: `k_sd` = 1.2377, so the two fields' noise scales differ by only 24% and the ratio the gate uses is near-invariant |
| **fact 343's operator-matched arm points the *other* way** (1.0678× unregularised vs 1.0739× regularised) | **Not reproduced and not contradicted** — different observable. On `n_eff`, arm X′ is two-sided across stacks (fact 8) and arm W is one-sided by arithmetic (fact 14). Nothing here licenses a directional claim |
| **the ARGUED status of the `Gate` doc comment** | The measurement M60c named has now been run. At the shipped gate the answer is **NOT load-bearing** (subject to §7). At gate 0.5 it is load-bearing. The doc comment's claim is not rescued at the default and is not universally false across the knob |

---

## 9. What was not measured, and where this is circular

**Not measured — nothing about image quality.** `n_eff` is an acceptance-set size. A larger
`n_eff` is not better; admitting genuinely out-of-focus frames is the opposite failure from
selecting one. Arm W admits more frames than arm R at every pixel by construction (fact 14),
and **no sharpness, edge-error, detail or speckle number is produced here.** Whether arm W's
extra admissions are good frames or bad ones is unmeasured, and it is the obvious next
milestone.

**Not measured — the winner's curse in isolation.** The arms differ in the elected index. The
bias in the winner's *value* is not separately estimated, because no ground-truth focus exists
on a real stack.

**Not measured — the ISO curve.** Fact 15 is three points on one body, from truncated sweeps.

**Not measured — a corrected K5 as a pre-registration.** See §7.2.

**Circularity, named (rule 34).** `tau` is expressed in units of `FOCUS_NOISE_SD`, a constant
measured **on the regularised field by the very operator under test**. Arm R is gated in its
own natural units; arms X and X′ are not. Arm X′ is the repair, using the crate's own
procedure — but `k_sd` is measured on a **synthetic unit-sigma plane**, not on the real
stacks, and a real focus field is not pure noise: fact 3's explanation (the 27×27 operator
window pre-correlates the samples) is a property of the operator, but the *degree* of
correlation on real texture is not the degree on white noise. **Arm X′ reduces the
circularity; it does not remove it.** Arm W is free of this particular circularity — its
tolerance, units and field are bit-identical to the shipped path — which is exactly why D1
was pinned to arm W and not to X′.

**Scope.** Four stacks, one camera body, one operator, one regulariser width. Three stacks
CPL-off, one CPL-on; the CPL cannot enter a within-stack paired contrast, but it bounds
cross-stack comparison. Nothing here transfers off this corpus.

---

## 10. Verification

All commands run at `projects/strehl`, Rust 1.98.0 MSVC.

```
cargo fmt --all -- --check           exit 0, no output
cargo clippy --workspace --all-targets
    Checking strehl-cli v0.0.0 (...\crates\strehl-cli)
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.22s
    (no warnings; one useless_vec in m65-election.rs was found and fixed)
cargo test --workspace
    Finished `test` profile [unoptimized + debuginfo] target(s) in 4.02s
    test result: ok. 40 passed; 0 failed; 0 ignored     (strehl-raw)
    test result: ok. 138 passed; 0 failed; 0 ignored    (strehl-core lib)
    test result: ok. 35 passed; 0 failed; 0 ignored     (strehl-core integration, 6.33s)
    test result: ok. 8 passed; 0 failed; 0 ignored      (strehl-plugin)
    test result: ok. 0 passed; test result: ok. 1 passed; test result: ok. 0 passed
    => 222 tests, 0 failed
cargo doc --no-deps -p strehl-core
    Documenting strehl-core v0.0.0
    warning: `strehl-core` (lib doc) generated 4 warnings
    Finished `dev` profile in 0.73s
cargo build --release --example m65-election
    Finished `release` profile [optimized] target(s) in 17.42s
```

**`cargo doc` emits 4 warnings, not the 3 the brief anticipated. None is mine — my diff in
`crates/strehl-core` is empty.** Located:

| warning | file:line |
| --- | --- |
| unresolved link to `crate::merge::ThroughFocus` | `focus.rs:99` (pre-existing) |
| unresolved link to `crate::merge::ThroughFocus` | `focus.rs:227` (pre-existing) |
| unresolved link to `NoiseModel::estimated` | `noise.rs:24` (pre-existing) |
| unresolved link to `tests::real_focus_contrast_is_far_larger_than_the_noise_scale` | **`merge.rs:278` — new since the brief was written** |

`merge.rs:278` sits inside the `Gate` doc block M60c edited. Flagging for the orchestrator; I
did not touch it.

**Regression check on my own refactor.** After fixing the clippy warning I rebuilt and re-ran
`109MSDCF`; the log is byte-identical to the pre-fix run (`Compare-Object` difference count
**0**). The clippy fix did not change a number.

---

## 11. Reproduction

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
cargo build --release --example m65-election
foreach ($s in '109MSDCF','119MSDCF','113MSDCF','coffee-bubbles') {
  .\target\release\examples\m65-election.exe "D:\personal\macro\$s"
}
# post-hoc probes
.\target\release\examples\m65-election.exe "D:\personal\macro\113MSDCF" --limit 22
.\target\release\examples\m65-election.exe "D:\personal\macro\109MSDCF" --gate 4 --gate 1000 --gate 1000000
```

Runtime: 9.0 s (`109`), 12.2 s (`119`), 26.6 s (`113`), 9.1 s (`coffee-bubbles`), serial.
The corpus is opened read-only; nothing is written to `D:\personal\macro`.

---

## 12. Facts, for the fold

| # | claim | label |
| --- | --- | --- |
| 1 | No prior report measures `n_eff` under a swapped election field; the measurement M60c named had not been run | MEASURED |
| 2 | The serial harness reproduces the shipped parallel CLI ladder on four stacks to < 0.02% (K3) | MEASURED |
| 3 | `k_sd` = **1.23770**; the 17×17 regulariser removes only 19.2% of the focus response's noise, because the operator's own 27×27 window pre-correlates the samples | MEASURED |
| 4 | Fact 3 is the mechanism behind M60c's G14: the two fields' noise scales differ by 24%, so the ratio the gate uses is near-invariant to which field it reads | DERIVED |
| 5 | Full mean-`n_eff` grid, 4 arms × 6 gates × 4 stacks | MEASURED |
| 6 | At the shipped default gate 4.0, `dev(rho_W)` ≤ **1.2335** on all four stacks, below the 1.332 bar — **D1: the election field is NOT load-bearing for the gate**; the "no-op" sub-clause at 1.05 is NOT met | MEASURED |
| 7 | `dev(rho_X′)` ≤ 1.1795 at gate 4.0 on all four stacks — **D2 agrees with D1**; no split to report | MEASURED |
| 8 | Arm X′ never crosses the bar at any gate on any stack; max `dev` = 1.2835 | MEASURED |
| 9 | Arm X admits fewer frames than R everywhere, as its 1.2377× units confound predicts; no conclusion drawn from it | MEASURED, CONFOUNDED |
| 10 | `dev(rho_W)` is monotone decreasing in the gate; it is over the bar on **4 of 4** stacks at gate 0.5 and **0 of 4** at gate 4.0. The answer is gate-dependent | MEASURED |
| 11 | The mechanism is a fixed reference shift `δ` measured against a tolerance linear in the gate: material against a narrow band, negligible against a wide one | DERIVED |
| 12 | **D4/G12 measured:** 56.70% of `113MSDCF` elects a different frame while the unit-matched acceptance set moves 0.44% | MEASURED |
| 13 | Arms differ at up to 69% of pixels by up to ±62 frames while their means agree to 0.44% — the per-pixel disagreement cancels in the mean | MEASURED |
| 14 | `n_W ≥ n_R` at every one of 32,966,016 pixel-arm pairs, confirming pre-registration §5 by measurement | MEASURED |
| 15 | At matched N = 22, index disagreement rises with ISO (24.2 → 28.6 → 36.6%) while `rho_W` does not (1.0838, 1.0827, 1.0612). The full-N ISO trend was N, not ISO | MEASURED, POST-HOC |
| 16 | The election field moves `n_eff` ≤ 1.53× at gate 2.0, against M52's 4.54× for operator choice and 12.22× for stack choice | DERIVED |
| 17 | In SNR units (`√n_eff`) the largest effect at the shipped gate is 1.111× | DERIVED |
| 18 | **K5 NOT MET on every stack**, from two defects: a floor criterion my own §5 proved arm W could not meet, and a ceiling rung (64) too narrow for real focus contrast. By the letter of §4.3 this voids D1 | MEASURED |
| 19 | At gate 1e6 every arm on every stack reads exactly N; the instrument is not flat, and `rho_W` reaches 2.8512 at gate 0 where a large ratio exists | MEASURED, POST-HOC |
| 20 | The tolerance's units are calibrated on the regularised field by the operator under test; arm X′ reduces this circularity but does not remove it, because `k_sd` is measured on synthetic white noise. Arm W is free of it, which is why D1 is pinned to W | DERIVED |
| 21 | `cargo doc -p strehl-core` now emits **4** unresolved-link warnings, not 3; the new one is `merge.rs:278`, inside the `Gate` doc block, and is not this milestone's | MEASURED |

---

## 13. Hand-off

- **`AGENTS.md` rule 4 still quotes fact 23's `34.4% -> 0.87%` speckle pair** — the same
  retired-ring-operator citation M60c repaired elsewhere. Not mine to edit.
- **`crates/strehl-core/src/merge.rs:278`** has an unresolved intra-doc link
  (`tests::real_focus_contrast_is_far_larger_than_the_noise_scale`), new since the M65 brief
  was written and inside the `Gate` doc block. Not mine to edit.
- **The obvious next milestone** is the one §9 names: arm W admits strictly more frames than
  arm R at every pixel, and nothing here says whether those extra frames are in focus. That
  is an image-quality question and this instrument cannot answer it.
- **A corrected K5** — floor conditioned on election agreement, ceiling at gate 1e6 — should
  be pre-registered before anyone treats §7's repair as settled.

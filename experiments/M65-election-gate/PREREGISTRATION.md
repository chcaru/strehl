# M65 — pre-registration: `n_eff` under regularised versus raw election, at a matched tolerance, on real frames

**Committed before any arm was run.** Nothing below was written after seeing a result.
The report is `docs/research/M65-election-gate-measured.md`; if it and this file disagree,
this file is the record.

---

## 0. The question, and why it is open

`Gate::admits(focus, best)` is `best - focus <= tolerance`. It admits on a **value**.
M60c retracted the claim that regularising the focus field *before* the election is
load-bearing for that gate, on three grounds (wrong operator, wrong quantity, and the
nearest operator-matched arm pointing the other way), marked it **ARGUED**, and named
exactly one measurement that would settle it:

> `n_eff` under regularised versus raw election at a matched tolerance, on real frames.

M60c deliberately did not run it. This is that run.

**Mechanism under test.** The winner is a maximum over N noisy responses, so the winner's
*value* carries a selection bias. The gate measures every other frame against that value.
Anything that changes the winner's value therefore changes the acceptance set, and the size
of the acceptance set is `n_eff`, which is what sets the merge's noise reduction. Whether
electing on the regularised field rather than the raw one changes that value **enough to
matter** is the open question.

**I do not state an expected direction anywhere in this file**, except where the direction
is a derived arithmetic property of the experimental design itself. §5 discloses the one
place that happens, because concealing it would let a tautology be reported as a finding.

---

## 1. Arms

All arms share: the stack, the frame list, the decode, `green_luma_with_clip`,
`FocusField::compute` (normalised Tenengrad, `WINDOW_RADIUS = 13`), the noise model from
`profile::noise_model_for`, the plane geometry, and the gate threshold ladder. They are run
in one process, in one pair of passes, over the same decoded frames.

Notation, per frame `k` and plane pixel `i`:

* `raw_k[i]` — `FocusField::compute` output, **unregularised**.
* `reg_k[i]` — `regularise(raw_k)`, the shipped 17x17 box mean.
* `tau(t) = Gate::new(t).tolerance() = t * sqrt(2) * FOCUS_NOISE_SD`.

| arm | winner index | reference value the gate compares against | field the gate reads | tolerance |
| --- | --- | --- | --- | --- |
| **R** — shipped | `argmax_k reg_k[i]` | `max_k reg_k[i]` | `reg` | `tau(t)` |
| **W** — raw election, everything else held | `argmax_k raw_k[i]` | `reg` **at that index** | `reg` | `tau(t)` |
| **X** — regulariser off, matched *numeric* tolerance | `argmax_k raw_k[i]` | `max_k raw_k[i]` | `raw` | `tau(t)` |
| **X'** — regulariser off, matched *noise-unit* tolerance | `argmax_k raw_k[i]` | `max_k raw_k[i]` | `raw` | `tau(t) * k_sd` |

**Arm W is the arm M60c named.** It is the only arm in which the tolerance, the units, the
field the gate reads, and the noise scale are all bit-identical to the shipped path, and the
*only* thing that differs is which frame was elected. Arms X and X' are the broader reading
("turn the regulariser off entirely") and are reported separately, never substituted for W.

In every arm the winner is admitted unconditionally, exactly as `Estimator::fold_inner`
does, so `n_eff >= 1` by construction in all four.

**`k_sd`** is the ratio of the unregularised to the regularised pure-noise response SD,
measured by re-running the crate's own procedure —
`merge::tests::the_focus_noise_constant_is_the_measured_one`, 12 fixed seeds, 512x512
unit-sigma plane, interior margin `SUPPORT_RADIUS + REGULARISER_RADIUS` — and reading the SD
off `field.values()` as well as off `regularise(...)`. Arm X' exists because
`FOCUS_NOISE_SD` is *defined* on the regularised field, so arm X's tolerance is calibrated
for a field it is not being applied to. That is a real confound and arm X' is the attempt to
remove it.

---

## 2. Observable

**Primary: mean `n_eff` per arm, per gate, per stack**, over the whole plane, where
`n_eff[i]` is the number of frames admitted at pixel `i`. This is the quantity that sets the
merge's noise reduction, and it is the quantity `Estimator::n_eff` already reports, so this
milestone builds no parallel instrument.

Reported alongside, at the shipped default gate:

* the paired per-pixel difference `n_W[i] - n_R[i]` (and `n_X'[i] - n_R[i]`) — its mean, its
  quantiles, and the fraction of pixels where it is non-zero;
* `P(win_R != win_W)`, the **election disagreement rate** — the *index-map* quantity, which
  M60c's G12 says is a different thing from the acceptance set. Measuring both in one run is
  the point;
* the `n_eff = 1` fraction per arm, since that is the fraction of the plane on which the
  merge has degenerated to a selector.

---

## 3. Stacks, and why these

Real frames, read-only, from `D:\personal\macro`. The mechanism is a **noise** phenomenon,
so the discriminating axis is sensor noise, i.e. ISO. Four stacks, chosen to give an ISO
ladder with three of the four on the same side of the polariser boundary:

| stack | frames | ISO | CPL (fact 845/925) | why |
| --- | --- | --- | --- | --- |
| `109MSDCF` | 22 | 160 | **off** | the only stack with a **published arm-R baseline** to check against (CLI ladder 1.414 / 1.884 / 2.891 / 4.987 at gates 0.5 / 1 / 2 / 4, quoted in `merge_cmd.rs`; M62's focus guard 0.064–0.227 of N). Control K3 needs it |
| `119MSDCF` | 33 | **50** | off | the quiet end of the ISO ladder, bare lens |
| `113MSDCF` | 63 | **500** | off | the loud end **without** crossing the polariser boundary. This is the stack that makes the ISO contrast interpretable |
| `coffee-bubbles` | 19 | **1000** | **on** | the loudest stack in the corpus at a small frame count |

**The CPL straddle is disclosed and bounded.** `coffee-bubbles` is CPL-on; the other three
are CPL-off. The observable is a **within-stack paired contrast on identical frames** — arm
R and arm W see the same decoded bytes — so the filter cannot enter the arm difference at
all. It can only affect how one stack's ratio compares with another's, and the ISO contrast
is therefore read off the **109 / 119 / 113 ladder**, which is entirely CPL-off.
`coffee-bubbles` is reported as a fourth point and is not required by any criterion.

`109MSDCF` is the corpus's easiest stack (no saturation, quietest photometrically, M24
0.91%), which M62 §11 says makes a clean result there systematically weaker evidence than it
looks. That is why it is not the only stack.

Gate ladder: **0.0, 0.5, 1.0, 2.0, 4.0, 64.0**. The middle four are the shipped ladder; 0.0
and 64.0 are the endpoints control K5 needs.

---

## 4. Criteria

### 4.1 Materiality bar, fixed now and not re-chosen later

"Load-bearing for the gate" needs a size, not an adjective. The bar is **the smallest step
of the knob the product actually exposes**: on `109MSDCF` the published gate ladder moves
mean `n_eff` 1.414 -> 1.884 between gates 0.5 and 1.0, a ratio of **1.332**. If swapping the
election field moves mean `n_eff` by less than the smallest rung of the gate ladder, it is
not load-bearing for the gate in any sense a user could act on.

Let `rho_A = mean n_eff(A) / mean n_eff(R)` and `dev(rho) = max(rho, 1/rho)`.

### 4.2 The pre-registered decisions

**D1 (primary, arm W).** At the shipped default gate 4.0:

* `dev(rho_W) >= 1.332` on **any** stack -> **the election field IS load-bearing for the
  gate.** Report magnitude and direction.
* `dev(rho_W) < 1.332` on **every** stack -> **the election field is NOT load-bearing for
  the gate**, and M60c's ARGUED status resolves to a measured negative.
* `dev(rho_W) < 1.05` on every stack -> additionally reported as *indistinguishable from a
  no-op at the scale of the exposed knob*.

**D2 (secondary, arm X').** The same three-way test on `rho_X'`, reported separately.

**D3 (arm X).** Reported, and flagged as **confounded**: at a matched numeric tolerance the
two fields have different noise scales, so arm X mixes the election change with a scale
change. No conclusion about the regulariser is drawn from arm X alone.

**D4 (index versus value, M60c G12).** `P(win_R != win_W)` is reported next to `rho_W`. A
large disagreement rate with `rho_W ~ 1` is a direct measurement of the category error M60c
derived: the index map moves and the acceptance set does not.

**If D1 and D2 disagree, I will report that they disagree and will not call the question
settled.** Naming a split is the outcome; picking the convenient half is not.

### 4.3 Controls that must be able to fail, and what failing means

Every one of these is checked and reported **before** any arm ratio is believed. If any
fails, the failure is the headline and the arm numbers are withheld.

| id | control | fails if |
| --- | --- | --- |
| **K1** | the replicated pure-noise procedure reproduces `FOCUS_NOISE_SD` | measured `sigma_reg` is more than 4 standard errors from `0.015214` — the crate's own bar in its own test |
| **K2** | the harness's admission counter is the shipped one | manual mean `n_eff` != `Estimator::mean_n_eff()` for arms R and X at gate 4.0 |
| **K3** | the serial harness reproduces the shipped parallel CLI | arm R mean `n_eff` differs from `strehl merge`'s printed value by >= 0.1% on any stack (M52's independent-merge bar was <= 0.09%) |
| **K4** | the arm difference is carried only by disagreeing elections | any pixel with `win_R == win_W` has `n_R != n_W` |
| **K5** | the plant can express the failure at both ends | any arm fails to read mean `n_eff` = 1.000 at gate 0, or < 0.95*N at gate 64. An arm that cannot span the range makes D1 void on that stack |
| **K6** | the raw election reproduces the shipped tie-break | the harness's raw winner index differs from `FocusStats(raw).best_index()` at any pixel |

K5 is the one that makes this a measurement rather than a demonstration: if the gate ladder
could not drive `n_eff` from 1 to N in *every* arm, a null result would mean the instrument
was flat, not that the arms agree.

---

## 5. The one derived sign, disclosed now rather than reported later as a finding

For arm W the reference value is `reg[win_W]`, and `reg[win_W] <= max_k reg_k` by definition
of a maximum. The admitted set is `{k : reg_k >= reference - tau}`, so lowering the reference
can only enlarge it:

```
A_W  =  {k : reg_k >= reg[win_W] - tau}  superset  {k : reg_k >= max_k reg_k - tau}  =  A_R
```

so **`n_W[i] >= n_R[i]` at every pixel, identically, and `rho_W >= 1` is arithmetic.**

Its sign therefore carries **no information about the world** and will not be reported as
one. The entire empirical content of arm W is its **magnitude**, which is bounded by nothing
and could be anything from 1.000 to N. Arm X' carries no such guarantee and is the genuinely
open comparison; that is why D2 exists and is stated two-sided.

---

## 6. What this cannot measure, declared in advance

* **Nothing about image quality.** `n_eff` is an acceptance-set size. A larger `n_eff` is
  not automatically better: admitting genuinely out-of-focus frames is the opposite failure
  from selecting one. No sharpness, edge-error, speckle or detail number is produced here,
  and none may be inferred from these ratios.
* **Nothing about the winner's curse in isolation.** The arms differ in the elected index;
  the bias in the winner's value is not separately estimated, because no ground-truth focus
  exists on a real stack.
* **The circularity, named now (rule 34).** The tolerance is expressed in units of
  `FOCUS_NOISE_SD`, a constant measured **on the regularised field** by the very operator
  under test. Arm R is therefore gated in its own natural units and arms X / X' are not.
  Arm X' is the attempt to repair this, using the crate's own measurement procedure — but
  `k_sd` is itself measured on a synthetic unit-sigma plane, not on the real stacks, and a
  real focus field is not pure noise. **Arm X' reduces the circularity; it does not remove
  it, and I will say so in the report.**
* **No claim transfers off these four stacks**, one camera body, one operator configuration.

---

## 7. Method

A new example, `crates/strehl-cli/examples/m65-election.rs`, additive: it modifies no shared
crate code and no shipped behaviour. It mirrors `merge_cmd.rs`'s two passes serially, the way
`examples/m60-disagreement.rs` already does, and calls the shipped `FocusField::compute`,
`regularise`, `FocusStats`, `Gate::admits` and `Estimator`. `cargo fmt --all -- --check`,
`cargo clippy --workspace --all-targets`, `cargo test --workspace` and
`cargo doc --no-deps -p strehl-core` are run and their real output quoted.

The corpus at `D:\personal\macro` is opened read-only. Nothing is written there.

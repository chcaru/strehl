# M45 — the plugin crate, implemented

**Status:** `crates/strehl-plugin/` exists, compiles, and is green. 33 tests +
1 doc-test. Workspace: **180 passed, 0 failed** (147 pre-existing + 33 mine).

This document reports what was built, the numbers reproduced, and — the part
the brief asked for most loudly — **what in workstream E §F5 turned out to be
wrong when it met a compiler.** Three things did. One of them is structural.

Every claim below is labelled **MEASURED**, **DERIVED** or **ARGUED**.

---

## 1. What the crate is for, in one paragraph

The merge admits a frame at a pixel when its focus response is within
`tol = t · √2 · FOCUS_NOISE_SD` of the peak. Fact 436: that relation is exactly
linear, `tol/t` constant to 2.0e-6 across 35× of gate. `FOCUS_NOISE_SD` is a
property of the **focus operator**, not of the merge — and across seven textbook
operators the true value spans 10.4× (fact 439). A contributed operator that
inherits the host's constant runs at effective gate `t/k`, and fact 438 is that
**nothing observable changes**. §F4's four plugin properties all pass such an
operator; §F4.6 marks it fault 5, "NOTHING BELOW CATCHES IT".

This crate implements §F5.3 **option A**: the host *measures* the operator at
registration. `FocusMeasure` has no method that could report a noise SD, and
`Calibration` has no public constructor. The fault is not detected — it is
**unrepresentable**.

---

## 2. What was built

| module | what it is |
|---|---|
| `measure.rs` | the `FocusMeasure` trait, `Window`, `Normalisation`, replicate-clamped `tap()` |
| `field.rs` | `FieldConfig` (`SHIPPED` = r8, `BARE` = none), `FieldWorkspace` — the pipeline |
| `rng.rs` | `NoiseSource` (3 generators), `unit_sigma_model()`, `CRATE_SEEDS` |
| `calibrate.rs` | **`calibrate()`** — the host-side measurement — plus `self_check()` |
| `reference.rs` | the seven fact-439 operators |
| `registry.rs` | `Registry`, `Registered`, dimensionless `Gate` |
| `examples/calibration-survey.rs` | the fact-439 table, re-measured in Rust |
| `examples/f5-design-probes.rs` | the three probes of §F5.3's own sketch (§7) |

### 2.1 The trait

```rust
pub trait FocusMeasure: Send + Sync {
    fn id(&self) -> &str;
    fn stencil_radius(&self) -> usize;
    fn window(&self) -> Window;              // None | Box{radius} | Custom{radius}
    fn normalisation(&self) -> Normalisation; // None | LumaSigma{degree} | Custom
    fn respond(&self, luma: &[f32], geom: PlaneGeometry, out: &mut [f32]);
    fn aggregate(&self, /* provided for Box */ ..);
    fn normalise(&self, field: &mut [f32], luma: &[f32], noise: &NoiseModel) { /* provided */ }
    fn support_radius(&self) -> usize { /* stencil + window */ }
}
```

**There is deliberately no `fn noise_sd()`.** That absence is the design.

The shape was chosen against the *real* operators, not against one: `Window`
carries a radius because some operators need one and some do not; `Normalisation`
is an enum because `|grad|` divides by σ¹ and `grad²` by σ², and a bool could not
say that; `respond`/`aggregate` are split because the box aggregation is the
part the host can do in O(1) per pixel with running sums and the plugin should
not reimplement.

Evidence it expresses the shipped operator without contortion — **MEASURED**:
`field::tests::the_shipped_operator_reproduces_focus_field_bit_for_bit` asserts
bit-for-bit equality of `Tenengrad::shipped()` through `FieldWorkspace` against
`strehl_core::focus::FocusField::compute`, and
`the_regularised_path_reproduces_focus_field_plus_merge_regularise` does the same
through `merge::regularise`. Not "close" — identical.

Evidence it expresses the other six — **MEASURED**: `reference.rs` implements
all seven and `examples/calibration-survey.rs` calibrates all seven (§4).

### 2.2 The pipeline order is load-bearing

```
respond → aggregate (operator's own box) → normalise (÷ luma σ) → host regularise (r8)
```

Exactly `FocusField::compute` then `merge::regularise`. Swapping aggregate and
normalise moves the constant silently. `FieldWorkspace::run` is the only place
this order is written down.

### 2.3 The registry hands out a dimensionless gate

`Registered::gate(t).tolerance() == t · √2`, with **no operator in it**, against
a field pre-divided by its own measured SD. `Registered::unnormalised_tolerance(t)
== t · √2 · measured_sd` is the migration path for a host that wants the
correctness property without the pre-normalisation.

---

## 3. Discipline 257: both targets, or the instrument refuses

`Registry::new` runs `self_check()` **before it will construct**, against both
in-crate constants in both of their configurations. A calibrator that cannot
reproduce the two numbers this repository already measured cannot register
anything.

**MEASURED** (`calibrate::tests::the_calibrator_reproduces_both_in_crate_constants`,
512² × 12 seeds, SplitMix64 + Box-Muller):

| target | configuration | crate constant | measured | deviation | in SEM |
|---|---|---|---|---|---|
| `FOCUS_NOISE_SD` | `\|grad\|` w13 **+ regulariser r8** | 0.015214 | 0.015211264 ± 7.57e-5 | **−0.018%** | 0.04 |
| `FINE_FOCUS_NOISE_SD` | `\|grad\|` w2, **no regulariser** | 0.090400 | 0.090399854 ± 1.70e-4 | **−0.000%** | 0.00 |

Both are an order of magnitude tighter than the Python reference (+0.47% and
+0.20%). Note the fine target agrees to 6 significant figures.

**Rule 20 — what would make this fail.** Dropping the regulariser from the
coarse arm. Measured, in
`dropping_the_regulariser_fails_the_coarse_target_and_not_the_fine_one`:
the unregularised coarse arm gives **0.018847**, which is **+23.88%** against
0.015214, while the fine arm is unmoved. That is M43's own +24.26% failure
signature reproduced in Rust to 0.3%. **The pattern of pass-and-fail is what
carries the diagnosis** — this is precisely why one target is not enough, and it
is why `self_check` refuses on *either*.

**Rule 24 — verification re-chooses, it does not re-compute.** The two targets
were re-measured under three deliberate re-choices of things a wrong
implementation could have compensated for
(`the_constants_survive_re_choosing_the_generator_the_transform_and_the_plane`):

| re-choice | coarse | fine |
|---|---|---|
| SplitMix64 + Box-Muller, 512² (baseline) | −0.02% | −0.00% |
| **PCG32** + Box-Muller, 512² | +0.34% | +0.25% |
| SplitMix64 + **Irwin-Hall(12)** | −0.54% | −0.53% |
| SplitMix64 + Box-Muller, **768²** | +0.60% | +0.26% |

All four within ±0.6%. The generator choice is not incidental: `merge.rs`
documents that a plain LCG made this constant vary **1.30× across seeds**
because the lattice aliases spatially against the 27-box/17-box chain. Two
independent generator families and a non-Box-Muller transform agreeing to 0.6%
is the evidence that this crate is not inheriting that failure.

---

## 4. Fault 5 is unrepresentable — demonstrated

**MEASURED** (`registry::tests::registering_a_mismatched_operator_yields_its_own_constant_not_the_hosts`):

Sum-modified-Laplacian — fact 439's worst case, *the* canonical shape-from-focus
operator, and therefore the likeliest third-party contribution — registered
against a host whose compiled-in constant is 0.015214:

```
SML w13 + r8: host-measured SD 1.0059252e-1 +/- 1.2548106e-3,
k = 6.6118 against the host's 1.5214e-2 (fact 439 measures 6.680).
A plugin inheriting the host constant would run --gate 1.0 at 0.1512.
```

**k = 6.6118 at the host-default plan; 6.6833 at M43's reference plan** (2048² ×
8 seeds) against fact 439's **6.680** — agreement to **0.06%**.

The full survey, re-measured in Rust at M43's exact reference configuration:

| operator | fact 439 `k` | this crate @2048²×8 | Δ | @512²×12 | gate@1.0 if it inherited |
|---|---|---|---|---|---|
| ring(1,3) | 0.6444 | **0.6455** | +0.17% | 0.6437 | 1.549 |
| tenengrad `\|grad\|` | 1.0081 | **1.0063** | −0.18% | 0.9998 | 0.994 |
| tenengrad-squared | 1.3671 | **1.3678** | +0.05% | 1.3592 | 0.731 |
| brenner | 1.9618 | **1.9703** | +0.43% | 1.9694 | 0.508 |
| local variance | 2.4749 | **2.4749** | +0.00% | 2.4806 | 0.404 |
| laplacian | 6.5904 | **6.5954** | +0.08% | 6.5235 | 0.152 |
| sum-modified-Laplacian | 6.6795 | **6.6833** | +0.06% | 6.6118 | 0.150 |

Spread **10.35×** against fact 439's 10.4×. An independent Rust reimplementation
reproduces a Python instrument on all seven operators to **±0.43%**.

**Why this is unrepresentable rather than merely detected** — **ARGUED**, but
structurally:

1. `FocusMeasure` has no method returning a noise SD. There is nothing for a
   contributor to fill in wrongly.
2. `Calibration` has private fields, no `pub fn new`, no `Default`. The only
   constructor is `calibrate()`.
3. `Registered` stores the `FieldConfig` it was calibrated under, and `field()`
   / `raw_field()` use *that* config — so a field cannot be produced under a
   configuration its constant does not describe.
4. `Registry::new` will not construct at all unless `self_check` passes both
   targets.

A contributor cannot express the fault. The type that would carry it does not
have a public way in.

**Bonus, not designed for** — `a_constant_returning_operator_is_refused`:
§F4.6's *fault 2* (an operator that returns a constant) falls out of this for
free, because its measured SD is 0 and `calibrate` returns
`DegenerateResponse`. `a_non_finite_operator_is_refused` covers NaN likewise.

---

## 5. The dimensionless gate

**MEASURED** (`the_gate_is_dimensionless_across_operators_that_differ_by_a_factor_of_six`):
for `t ∈ {0, 0.5, 1, 2, 5.94}`, `tenengrad.gate(t).tolerance()` and
`sml.gate(t).tolerance()` are `assert_eq!`-equal and equal to `t·√2`, while the
*un-normalised* tolerances differ by exactly the measured `k = 6.61`. The second
half is what stops the first from being a tautology: the operators really are
6.6× apart, so the equality is a property of the normalisation and not of the
operators being the same.

**MEASURED** (`the_normalised_field_has_unit_noise_sd_on_a_held_out_seed`): on a
seed outside `CRATE_SEEDS` and a *different generator* (PCG32), the
pre-normalised SML field has interior SD **0.9645** against a target of 1.0.
Held out, not restated.

---

## 6. Facts 503/504 — the flip count, and a control that caught itself

### 6.1 The result

**MEASURED** (`pre_normalising_the_field_changes_a_bounded_and_tiny_fraction_of_admissions`).
Plant: 32 independent unit-noise planes at 512², shipped operator, interior only
= **6,948,992 admission decisions**. Both arms come from the *real* API
(`raw_field` + `unnormalised_tolerance` vs `field` + `gate`), so what is measured
is the rounding this crate actually performs — a multiply by the reciprocal —
not an idealisation of it.

| gate `t` | flips | rate | control +1% | control +0.1% |
|---|---|---|---|---|
| 0.5 | 1 / 6,948,992 | **1.44e-7** | 1.18e-3 | 1.19e-4 |
| 1.0 | 5 / 6,948,992 | **7.20e-7** | 4.28e-3 | 4.30e-4 |
| 2.0 | 2 / 6,948,992 | **2.88e-7** | 7.95e-3 | 8.10e-4 |

**Fact 504 is confirmed in direction and refined in magnitude.** It predicted
1e-6 to 1e-5; the measured rate is **1.4e-7 to 7.2e-7**, roughly 1.4× to 7×
*below* the predicted range. The design claim survives: pre-normalisation is
behaviour-preserving to within ~7e-7 of decisions.

**§F5.5's proposed test is refuted.** §F5.5 says the check is "a one-line change
and a byte-identical-output test". A byte-identical-output test **would go red**:
there are 1–5 flips per 6.9M decisions at every gate tested. Fact 504 anticipated
exactly this. Anyone implementing §F5.5 literally would have written a red test
and had to decide, under pressure, whether the design was wrong. It is not; the
test would have been.

The assertion in the shipped test is therefore a **bounded rate < 1e-4**, never
byte-identity.

### 6.2 The control caught a bug in the control

Rule 20 asks what input would make the bound fail. The first version of this
test used, as its positive control, a field divided by `SD·1.001` compared
against a tolerance *also* divided by `SD·1.001`. It measured **0 flips in the
control and 0 in the treatment**, and failed with:

```
gate 0.5: a 0.1%-wrong normalisation flipped only 0.000e0 of decisions,
so the bound above has no power on this plant
```

The control was right and the control was the bug: dividing *both* sides by the
same constant is the identical comparison, so that "wrong" arm was algebraically
exact and could not flip anything. **A test asserting only `rate < 1e-4` would
have passed, green, with zero power**, and I would have reported a bound that
could not fail. Rule 15: the broken version is recorded here rather than tuned
into agreement, and a new test was written under a new name.

The corrected control biases *only the field*, leaving the gate believing the
constant is right — which is fault 5 in miniature. At **+1%** it changes
1.2e-3–7.9e-3 of decisions; at **+0.1%** it still changes 1.2e-4–8.1e-4. So the
instrument resolves a **0.1% error in the noise constant** — about 6600× finer
than the error fault 5 actually produces.

---

## 7. **What in §F5 turned out to be wrong**

This is the section the brief asked for. §F5.3's option A is *right*, and the
argument for preferring it to option B survived implementation intact. But the
sketch it gives is wrong in three ways, measured by
`examples/f5-design-probes.rs`.

§F5.3 gives:

```rust
fn calibrate(op: &dyn FocusMeasure, cfg: &FieldConfig) -> f32 {
    let field = cfg.run(op, &unit_noise_plane(512, 512), &unit_sigma_model());
    interior_sd(&field, cfg.support_radius())
}
```

### 7.1 It is non-deterministic, and that violates §F4's own P1 — **the structural one**

`unit_noise_plane(512, 512)` takes **no seed** and the routine takes **one
plane**. So the constant is a random variable, and the gate with it.

**MEASURED**: the shipped operator, calibrated on each of 12 single 512² planes:

```
single-plane constants: mean 1.521126e-2  sd 2.621e-4 (1.72% of the mean)
min 1.491723e-2  max 1.576361e-2  spread 5.56% of the mean
```

A single plane gives a **±1.72% (1σ)** estimate, with an observed spread of
**5.56%** across 12 planes. Two runs of the same host, on the same operator,
with the same configuration, would compute gates differing by up to 5.56%.

**That is registration-time non-determinism, which is exactly what §F4's P1
(confluence) forbids** — and P1 is one of the four properties §F5 was written to
supplement, not to break. The fix that closes fault 5 would, as sketched, open a
P1 violation.

The crate fixes it two ways: `CalibrationPlan` carries an explicit
`Vec<u64>` of seeds (defaulting to the 12 `merge.rs` itself measures over), and
**`calibrate()` refuses a single-seed plan outright**:

```
calibrate() with one plane is REFUSED:
calibration needs at least two seeds to have a standard error, got 1
```

with two seeds being the minimum at which a standard error exists at all. It
further refuses any plan whose relative SEM reaches 5% (`NoPower`), so "not
enough planes for this operator" is an error and not a quiet imprecision. At 12
seeds the shipped operator reaches 0.497% relative SEM and SML 1.247% —
**MEASURED**, and note that the noisier operator needs more planes for the same
precision, which a fixed one-plane routine cannot express.

**This is the most valuable thing in this report.** §F5.3 was written as prose
and the missing seed is invisible in prose. It is not invisible to a compiler.

### 7.2 The margin is the operator's, and it should be the operator's *plus the host's*

`interior_sd(&field, cfg.support_radius())` discards the operator's support —
14 for the shipped operator. But the field has then been through the host's r8
regulariser, whose box filter is replicate-clamped, so the outer 8 rows beyond
that are not stationary either. The correct margin is
`max(stencil+1, 2) + window + regulariser_radius` = **23**, not 14.

**MEASURED**:

| operator | margin 23 (correct) | margin 14 (§F5.3) | margin 0 |
|---|---|---|---|
| tenengrad | 1.521126e-2 | 1.525866e-2 (**+0.31%**) | 1.573307e-2 (+3.43%) |
| sml | 1.005925e-1 | 1.006177e-1 (**+0.03%**) | 1.037115e-1 (+3.10%) |

The bias is small — 0.31% — but it is **systematic and operator-dependent**
(0.31% vs 0.03%), so it does not cancel in the ratio between two operators. It
would also have made the coarse target land at +0.31% instead of −0.018%, i.e.
17× further from the crate constant, which under discipline 257's own SEM test
is the difference between 0.04 SEM and 0.6 SEM. Not fatal; wrong.

### 7.3 Fact 505's cost bound is exceeded by 3× per plane and 35× per registration

**MEASURED**, release build, `examples/f5-design-probes.rs` probe 3:

| operator | total | per plane | relative SEM |
|---|---|---|---|
| tenengrad | 60.28 ms / 12 seeds | **5.02 ms** | 0.497% |
| sml | 62.07 ms / 12 seeds | **5.17 ms** | 1.247% |

Fact 505 bounds option A at **~1.7 ms per stage**. The measured per-plane cost is
**5.02 ms — 2.95× the bound** — and because §7.1 forces ≥2 and in practice 12
planes, the per-registration cost is **60.3 ms, 35× the bound**.

Fact 505's derivation (52.4 ms per 8.241 MP plane, 512² is 3.18% of that) treats
the merge's pass-one time as an upper bound on one focus-field pass. It is not:
that 52.4 ms is measured on a *release* pipeline whose per-pixel cost is
dominated by memory bandwidth on a large plane, and a 512² plane does not scale
down linearly. The bound's *conclusion* survives — 60 ms once per registration
is still negligible — but the number is wrong and should not be quoted.

### 7.4 Two smaller things

- **`Window::Custom` and `Normalisation::Custom` cannot be enforced by the type
  system.** An operator declaring `Window::Custom{radius}` must override
  `aggregate`, and nothing in Rust's trait system can require that a *provided*
  method be overridden when an *associated value* takes a particular variant.
  The crate panics with a named message
  (`a_declared_custom_window_that_is_not_overridden_panics_rather_than_passing_through`),
  which is the best available, but it is a runtime check where §F5 implies a
  static one.
- **`respond(&self, ...)` forces multi-pass operators to allocate.** Ring and
  local-variance both need box means of the *input*, and the trait hands out only
  `&self` and one output buffer, so they allocate a temporary per call. For a
  calibration this is irrelevant; for a per-frame merge path it is a real cost,
  and a future `respond` should take a scratch buffer the way `aggregate` does.

### 7.5 What did **not** break

- Option A's four-count argument over option B survived intact. In particular
  point 2 — that a declared constant is under-determined because it depends on
  the host's regulariser radius — is visible directly in the crate: the same
  operator through `FieldConfig::SHIPPED` and `FieldConfig::BARE` gives 0.015211
  and 0.018847, a **23.9%** difference, from a parameter no plugin can see.
- §F5.4's two-target requirement is not merely advisable, it is *cheap*: both
  targets already exist in-crate, and `self_check` cost is one extra calibration.
- §F5.3's core claim — that the host owns everything needed to measure — is
  exactly true. `calibrate()` needs nothing from the plugin except the trait.

---

## 8. Verification performed

| command | result |
|---|---|
| `cargo test -p strehl-plugin --release` | **33 passed, 0 failed** + 1 doc-test |
| `cargo test --workspace` | **180 passed, 0 failed** (37 cli + 102 core + 33 plugin + 8 raw) |
| `cargo clippy --workspace --all-targets` | clean, 0 warnings |
| `cargo fmt --all -- --check` | clean, exit 0 |

The brief anticipated pre-existing `clippy`/`fmt` failures in
`crates/strehl-cli/src/merge_cmd.rs` and `crates/strehl-core/src/merge.rs` from
M40's in-flight work, and an unreachable 139-test baseline. **Neither is present
as of this run** — M40 appears to have resolved them; the workspace is green and
the pre-existing count is 147, not 139. No M40 file was modified by me.

### Files touched outside the new crate

Two, both strictly additive, both mine alone (verified against `git diff`):

- `Cargo.toml` — `crates/strehl-plugin` added to `members`; `strehl-plugin` added
  to `[workspace.dependencies]`.
- `Cargo.lock` — the new package stanza.

**`crates/strehl-core/src/merge.rs`, `through_focus.rs`, `focus.rs` and `lib.rs`
were not modified.** The crate consumes `strehl-core`'s public API only. The
flip-count experiment (§6) therefore runs on this crate's own field rather than
through the merge, as the brief permitted.

---

## 9. What this does not yet do

- **It is not wired into the merge.** `merge.rs` still uses the compiled-in
  constant. Wiring it is a small change — replace `FOCUS_NOISE_SD` in
  `Gate::tolerance` with a `Registered::unnormalised_tolerance` — but it belongs
  to whoever owns `merge.rs`, and §6 measures what that change would cost.
- **Only `FocusMeasure` is pluggable.** Merge strategies, alignment models and
  optical profiles are untouched. The calibration pattern generalises to any
  stage whose output feeds a noise-scaled threshold; whether it generalises to
  stages that do not is unexamined.
- **No dynamic loading.** Registration takes `Arc<dyn FocusMeasure>` from
  in-process code. Everything about the *contract* is exercised; nothing about
  ABI, versioning, or untrusted code is.
- **`WholeStack` operators are unaddressed.** §F5.3 flags them as the one case
  where option A degrades to option B, and this crate does not implement option
  B. An operator that cannot be run on a synthetic plane simply cannot be
  registered here.

---

## Proposed disciplines

*(unnumbered, per the brief)*

- **A load-time measurement must be seeded and replicated, or it is a P1
  violation dressed as a calibration.** A single unseeded probe makes
  registration non-deterministic; the resulting gate differed by 5.56% across
  planes here. State the seed list and the minimum replicate count in the
  contract, and refuse a plan that cannot produce a standard error.
- **A positive control must break a *different* symmetry from the treatment.**
  §6.2's first control divided both the field and the tolerance, which is the
  identical comparison — it had zero power and the treatment's bound would have
  passed vacuously. Before trusting a bound, check that the control arm actually
  exceeds it.
- **When a design's cost is bounded by derivation rather than measurement, quote
  the bound with its derivation attached or not at all.** Fact 505's 1.7 ms is a
  correct *conclusion* (the cost is negligible) resting on a number that is 3×
  low per plane and 35× low per registration.

## Proposed questions for the owner

*(unnumbered, per the brief)*

- Should the merge adopt the **pre-normalised** field (dimensionless `--gate`,
  ~7e-7 of admissions change) or the **measured-constant** field (identical
  arithmetic shape, zero admissions change, `--gate` still operator-dependent)?
  §F5.3 point 3 argues the former is the only version in which a shared preset
  is portable; the latter is a strictly smaller change. Both are implemented.
- Facts 509–511 say `tenengrad-sq` at r11 is already pending and moves the
  constant by k = 1.528. Should that change **also** re-derive `FOCUS_NOISE_SD`
  through this crate rather than hard-coding a new literal? It would be the
  first real use of the calibrator and would retire the constant permanently.
- `Window::Custom` and `Normalisation::Custom` are enforced by panic (§7.4).
  Is a runtime panic acceptable at registration, or should the trait be split so
  that a custom-window operator is a *different trait* and the invalid state is
  gone?

---

## Proposed SYNTHESIS entries

*(facts 520–539 reserved for M45; numbered `P1…` per rule 28 as the brief directs)*

| # | Fact | Consequence | Source |
|---|---|---|---|
| P1 | A Rust host-side calibrator reproduces `FOCUS_NOISE_SD` to **−0.018%** (0.04 SEM) and `FINE_FOCUS_NOISE_SD` to **−0.000%** (0.00 SEM) at 512² × 12 seeds, from the operator alone. | §F5.3 option A is implementable and more accurate than the Python reference (+0.47% / +0.20%). The constant need not be compiled in. | `strehl-plugin` `calibrate::tests::the_calibrator_reproduces_both_in_crate_constants` |
| P2 | The same calibrator reproduces all seven fact-439 `k` values to **±0.43%** at 2048²×8, incl. SML at **6.6833** vs 6.680 (+0.06%); spread **10.35×** vs 10.4×. | Fact 439 is independently confirmed in a second language and a second implementation. The 10× spread is a property of the operators, not of M43's instrument. | `strehl-plugin` `examples/calibration-survey.rs -- reference` |
| P3 | `FocusMeasure` has no noise-SD method and `Calibration` has no public constructor, so §F4.6 fault 5 has no representation in the type system; §F4.6 fault 2 (constant operator) falls out for free as `DegenerateResponse`. | Fault 5 is closed by construction, not by test. A contributed operator cannot carry a wrong constant because there is nothing to carry it in. | `strehl-plugin` `measure.rs`, `calibrate.rs`; `registering_a_mismatched_operator_yields_its_own_constant_not_the_hosts` |
| P4 | §F5.3's sketched `calibrate()` takes **one unseeded** 512² plane. Measured across 12 planes: 1σ = **1.72%**, observed spread **5.56%**. | §F5.3 as published makes registration non-deterministic, violating §F4's own P1 (confluence). A load-time measurement must specify seeds and a replicate count. `calibrate()` here refuses a single-seed plan. | `strehl-plugin` `examples/f5-design-probes.rs` probe 2 |
| P5 | §F5.3's sketched margin `cfg.support_radius()` (14) omits the host regulariser radius; the correct margin is 23. Bias **+0.31%** (tenengrad), **+0.03%** (SML); margin 0 gives +3.43% / +3.10%. | The bias is small but systematic and operator-dependent, so it does not cancel in `k`. The margin must be `max(stencil+1,2) + window + regulariser_radius`. | `strehl-plugin` `examples/f5-design-probes.rs` probe 1 |
| P6 | Measured calibration cost is **5.02 ms per 512² plane** (release) and **60.3 ms per registration** at 12 seeds — 2.95× and 35× fact 505's ~1.7 ms bound. | Fact 505's conclusion (negligible) holds; its number does not and should not be quoted. Derived bounds need their derivation attached. | `strehl-plugin` `examples/f5-design-probes.rs` probe 3 |
| P7 | Pre-normalising the focus field by its measured SD changes **1.4e-7 to 7.2e-7** of admission decisions (1–5 flips in 6,948,992) at gates 0.5/1/2. | Fact 504 confirmed in direction, refined 1.4–7× lower in magnitude. **§F5.5's proposed "byte-identical-output test" would go red** — the correct assertion is a bounded rate. | `strehl-plugin` `pre_normalising_the_field_changes_a_bounded_and_tiny_fraction_of_admissions` |
| P8 | A positive control that scales the field **and** the tolerance by the same wrong constant is the identical comparison and measured **0 flips**; the flip-rate bound would have passed with zero power. | A control must break a different symmetry from the treatment. Verify the control exceeds the bound before trusting the bound. | §6.2; first-run output recorded in this document |
| P9 | The same operator calibrated through `FieldConfig::SHIPPED` (r8) and `FieldConfig::BARE` gives 0.015211 and 0.018847 — **+23.88%** — from a parameter no plugin can observe. | Direct confirmation of fact 500 and of §F5.3 point 2: a plugin-declared constant is under-determined *in principle*, not merely in practice. Reproduces M43's +24.26% signature to 0.3%. | `strehl-plugin` `dropping_the_regulariser_fails_the_coarse_target_and_not_the_fine_one` |
| P10 | The two constants survive re-choosing the generator (SplitMix64 → PCG32), the transform (Box-Muller → Irwin-Hall) and the plane size (512² → 768²) to within **±0.6%**. | The calibrator does not inherit the LCG spatial-aliasing failure `merge.rs` documents (1.30× across seeds). Rule 24 satisfied by re-choice, not re-computation. | `strehl-plugin` `the_constants_survive_re_choosing_the_generator_the_transform_and_the_plane` |

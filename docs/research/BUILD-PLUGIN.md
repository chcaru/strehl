# BUILD-PLUGIN — the contribution surface was unreachable; making it reachable, and what that cost

**Facts, disciplines and open questions in this file are numbered LOCALLY as
`P1, P2, …` per rule 28.** The orchestrator allocates absolute numbers at fold.

Every claim is labelled **MEASURED**, **DERIVED** or **ARGUED**. An unlabelled
claim is unfounded and should be read as such.

**Source revision at start:** `0dd3d3f9` (`BUILD-DEFECT: sensor defect
correction, and the measurement that says ship it off`). Four commits from other
lanes landed underneath this work while it ran (`107b37e0`, `7cce5d06`,
`f3af75ee`, `6e25ec19`); §7.3 states what that does and does not do to the
attribution.

**Read-only inputs, never written to:** `D:\personal\macro\wrapped-text-1`
(130 frames), and the `coffee-bean` capture the byte-freezes gather. All outputs
under `C:\dev\strehl-out\BUILD-PLUGIN\`.

---

## 0. The commission

> *"it should be **pluggable by design**" … "the stacking techniques, algos,
> etc. should **all be plugins too — recomposable and easily contributable by
> others**"*

And the specific defect:

> *`strehl-plugin` is a leaf crate that **nothing depends on**. So today a
> contributor can write a focus measure, register it, have it correctly
> calibrated — and `strehl stack` will never call it.*

---

## 1. The answer, up front

**Yes. `strehl stack` now dispatches to a contributed, host-calibrated focus
operator, and the merge gate is denominated in that operator's measured noise
scale.**

```
strehl focus list [--gate T]          # enumerate, with HOST-MEASURED scales
strehl stack <dir> --out <f> --focus <ID>
```

Four claims, each with the command that establishes it:

| # | Claim | Evidence |
|---|---|---|
| 1 | The flag dispatches | §5.2 — `--focus sml-w13` moves **99.9105%** of output samples |
| 2 | The default is byte-identical | §5.1 — both byte-freezes HOLD; two independent render pairs hash-match |
| 3 | The calibration is real | §4 — 7 operators measured through the shipping binary, **10.27x** span |
| 4 | The crate's bit-identity claim is TRUE | §3 — 0 of 8,241,504 samples differ, on real frames |

And one thing that is **not** claimed: §6.2 records a genuine calibration
approximation that `--focus` inherits from the shipped path rather than fixes.

---

## 2. What was actually broken, and why it was not a missing `Cargo.toml` line

**P1 (MEASURED).** At `0dd3d3f9`, `crates/strehl-cli/Cargo.toml` declared
`strehl-core` and `strehl-raw` and nothing else. Adding `strehl-plugin` to it is
one line and **does not fix anything**, because there was no entry point to call.
The election is `FocusField::compute`, whose three stages are inlined into
`strehl-core/src/focus.rs` and take no operator.

**P2 (MEASURED).** The pipeline therefore existed **twice**: once inlined in
`strehl-core::focus::FocusField::compute`, and once composed in
`strehl-plugin::field::FieldWorkspace::run`. The plugin crate knew, and held the
two together with a test rather than with a type. Its own header claimed
bit-identity — a claim about two implementations agreeing.

**P3 (DERIVED).** So the deliverable was not a dependency edge, it was a
**unification**: one pipeline that both the default path and a contributed
operator go through. Anything less would have shipped a third copy.

---

## 3. Item 4 of the brief: the bit-identity claim, verified BEFORE it was relied on

The brief was explicit that the claim must not be assumed. It was not.

**P4 (MEASURED). The claim is TRUE, and on inputs stronger than the ones the
crate tested it on.** `crates/strehl-cli/examples/build-plugin-field.rs` decodes
real frames and runs both paths over the same luma plane and the same
`profile::noise_model_for` noise model:

```
$ cargo run --release -p strehl-cli --example build-plugin-field -- D:\personal\macro\wrapped-text-1 3
== arm 1: bit-identity on REAL frames ==
  regulariser radius 8, compiled-in FOCUS_NOISE_SD 1.5214e-2
  DSC00001.ARW   3516x2344 ISO 100   bare: 0 differing / 8241504 (worst 0e0)   regularised: 0 differing (worst 0e0)
  DSC00002.ARW   3516x2344 ISO 100   bare: 0 differing / 8241504 (worst 0e0)   regularised: 0 differing (worst 0e0)
  DSC00003.ARW   3516x2344 ISO 100   bare: 0 differing / 8241504 (worst 0e0)   regularised: 0 differing (worst 0e0)
  VERDICT: the field.rs bit-identity claim is UPHELD on real frames
```

The in-crate tests used synthetic 97x71 and 101x83 planes. This is 3516x2344 of
real sensor data with a real per-plane noise model, which is where a divisor
that varies across the window can actually diverge.

**P5 (MEASURED). The claim was nevertheless silently conditional, and nothing in
either crate said so.** `FocusField::compute` resolves its radius through
`window_radius()`, which honours `STREHL_WINDOW_RADIUS`.
`strehl-plugin`'s `Tenengrad::shipped()` read the `WINDOW_RADIUS` **constant**.
Under an override the two are **different operators** — fact 510 prices a single
radius step at a 12.5% gate shift — and the crate's own bit-identity test would
have failed for a reason neither crate's documentation mentions. Closed: the
unified `Tenengrad::shipped()` calls `window_radius()`.

**P6 (MEASURED, minor).** `strehl-plugin/src/measure.rs` carried its own
`SIGMA_EPS` and said so in a comment — the core's was private. Now one
`pub const` in `strehl_core::focus`.

---

## 4. The calibration is a measurement, not a table

**P7 (MEASURED). Seven reference operators, calibrated by the host at
registration, through the shipping binary's own dependency graph.**

```
$ strehl focus list
focus operators, calibrated by the host at registration (12 seeds x 512x512 plane, margin 23 px)
the noise sd is MEASURED here, not declared by the operator: `FocusMeasure` has no method that could declare it

id                             noise sd      rel sem         k   tol @ gate 4   halo
brenner-w13                 2.996190e-2       1.061%    1.9694    1.694901e-1     23
laplacian-w13               9.924864e-2       1.157%    6.5235    5.614351e-1     22
local-variance-3x3-w13      3.773914e-2       1.013%    2.4806    2.134848e-1     22
ring-1-3-w13                9.792747e-3       1.297%    0.6437    5.539614e-2     24
sml-w13                     1.005925e-1       1.247%    6.6118    5.690372e-1     22
tenengrad-sq-w13            2.067916e-2       0.562%    1.3592    1.169790e-1     22
tenengrad-w13               1.521126e-2       0.497%    0.9998    8.604790e-2     22  <- default
```

**Span 1.005925e-1 / 9.792747e-3 = 10.27x.** `SumModifiedLaplacian` is 6.61x
from the default, as the brief expected. Every relative SEM is under 1.3%, so
the span is not sampling noise: the smallest gap in the table
(`tenengrad-w13` to `tenengrad-sq-w13`, 1.36x) is two orders of magnitude wider
than either row's error bar.

**P8 (MEASURED). The host measures `tenengrad-w13` at `1.521126e-2`, and the
compiled-in `FOCUS_NOISE_SD` is `0.015214`.** `k` = 0.9998, and at gate 4 the two tolerances are `0.086048` against
`0.086063`. Close, and **not equal**. This is why `--focus tenengrad-w13` and *omitting the flag* are
deliberately different runs, and why the default path was never routed through
the calibrator: doing so would have moved the byte-freezes by turning a frozen
constant into a measured one.

---

## 5. The two proofs the brief demanded

### 5.1 The default path is byte-identical

**P9 (MEASURED). Both frozen renders reproduce their recorded bytes.** This is
the authoritative proof, because the frozen rows run the **estimator** backend —
the one whose gate and focus field this work edited — at gate 2.0.

```
$ cargo test --release -p strehl-cli --test byte-freeze -- --nocapture
freeze `coffee-bean-20-gate2-unaligned` HOLDS: 88712017FE31362F35FF2FF5D4B98727CDEFCBAC489D9A7827F21EE0154A8620 (49450019 bytes, alignment off, 10 chunks of <= 2 frames) -- reproduced twice
freeze `coffee-bean-20-gate2-sidecar` HOLDS: 52517FF8AE245F238C29F64A29E601C2D5C064CB4D86E93006512993837EC206 (49450019 bytes, alignment on-sidecar-override, 10 chunks of <= 2 frames, 20 placed / 0 refused) -- reproduced twice
test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 43.51s
```

`crates/strehl-cli/tests/byte-freezes.tsv` is **unmodified**:
`git status --porcelain -- crates/strehl-cli/tests/` prints nothing.

**P10 (MEASURED). Two independent before/after render pairs hash-match.** Both
binaries were built with `STREHL_BUILD_ID=byteproof` pinned, because `--srgb`
renders embed the build id in TIFF tag 305 and an unpinned stamp would make any
comparison meaningless. `STREHL_ALIGN=0` and a scratch `STREHL_CACHE_DIR` keep
the capture library read-only (facts 1384/1385).

The shipping command from the brief, 130 frames, **pyramid** backend (the
default):

```
$ strehl stack D:\personal\macro\wrapped-text-1 --out <before|after>.tif --srgb --auto-exposure
frames          : 130 from D:\personal\macro\wrapped-text-1
merge backend   : pyramid (default)
folded          : 130 / 130 frames in 21.1 s (0.16 s per frame, 4 workers)
wrote           : ... (7032 x 4688, 16-bit RGB, sRGB ... Malvar-He-Cutler demosaic)

before.tif  SHA256 80AD2D660A082D208010BF759846D3D8C18425938576526B20149695B1854FC7
after.tif   SHA256 80AD2D660A082D208010BF759846D3D8C18425938576526B20149695B1854FC7
after2.tif  SHA256 80AD2D660A082D208010BF759846D3D8C18425938576526B20149695B1854FC7
```

And the **estimator** backend, which is the path that was actually edited:

```
$ strehl stack D:\personal\macro\wrapped-text-1 --limit 6 --merge estimator --out <...>.tif
est-before.tif  SHA256 4AF53C3816A743EBA22216877AB868236FBF32D09FD225BCDA19B59B7B7ED7B6
est-after.tif   SHA256 4AF53C3816A743EBA22216877AB868236FBF32D09FD225BCDA19B59B7B7ED7B6
```

### 5.2 A non-default operator takes effect

**P11 (MEASURED). `--focus sml-w13` moves 99.9105% of output samples.** Same
binary, same input, same gate, same alignment setting; the flag is the only
difference.

```
$ strehl stack D:\personal\macro\wrapped-text-1 --limit 6 --merge estimator --out default.tif
$ strehl stack D:\personal\macro\wrapped-text-1 --limit 6 --merge estimator --focus sml-w13 --out sml.tif

default.tif  SHA256 4AF53C3816A743EBA22216877AB868236FBF32D09FD225BCDA19B59B7B7ED7B6
sml.tif      SHA256 37759E8E43B7CFDBBF234812E977D4387833D7854A25B12C0A5EFD43DF3E1CEF

$ python scripts/build_plugin_tiff_delta.py default.tif sml.tif
geometry        : 3516 x 2344 x 3 samples/px, 24724512 samples
differing       : 24702381 samples (99.9105%)
worst |delta|   : 2013 DN of 65535
mean |delta|    : 131.7639 DN over all samples
```

`sml.tif` reproduces at the same hash from an independently built binary
(`37759E8E43B7CFDBBF234812E977D4387833D7854A25B12C0A5EFD43DF3E1CEF`), so the
difference is the operator and not run-to-run nondeterminism.

Note that `default.tif` carries the same hash as `est-before.tif` from §5.1 —
rendered by the **pre-change** binary. So the same run proves both halves: the
default is untouched and the flag is not.

**P12 (MEASURED). The banner reports the measured scale, and the run uses it.**

```
focus operator  : sml-w13 (contributed, via strehl-plugin)
  noise sd      : 1.0059252e-1 MEASURED by the host at registration (12 seeds, rel sem 1.247%), k = 6.6118 vs the compiled-in 0.015214
  gate           : --gate T means T*sqrt(2)*1.0059252e-1 in THIS operator's response units, not the shipped one's.
focus noise sd  : 0.100593 on the regularised field, MEASURED by the host for `sml-w13` at registration (NOT the compiled-in 0.015214)
gate unit       : 0.142259  = sqrt(2) * the focus noise sd IN FORCE, the SD of a difference
```

Two of those lines used to print `FOCUS_NOISE_SD` unconditionally and were
wrong by 6.6x under `--focus` on the first working build. Fixed before this was
written: a provenance line that disagrees with the run is worse than none.

---

## 6. What was built

### 6.1 One pipeline, not two

The operator abstraction moved **into** `strehl-core::focus`: `FocusMeasure`,
`Window`, `Normalisation`, `tap`, `SIGMA_EPS`, `run_measure`, `Tenengrad`,
`FieldConfig`, `FieldWorkspace`. `strehl-plugin`'s `measure.rs` and `field.rs`
are now `pub use` shims that keep their prose and their tests;
`reference.rs::Tenengrad` re-exports the core type. `strehl-core` cannot depend
on `strehl-plugin` (the dependency runs the other way), so this was the only
direction the unification could go.

The default path now reaches the contributed-operator machinery on **every**
run: `compute` → `compute_at_radius` → `compute_with_measure(&Tenengrad)` →
`run_measure`. There is no "plugin pipeline" to drift from a "real" one, which
is what makes §5.1's byte-identity a structural property rather than a
coincidence that has to be re-measured.

**P13 (MEASURED). The plugin crate's 35 tests, including both of its
bit-identity tests, pass unchanged against the unified pipeline** — they were
written against the composed implementation and now exercise the core one.

**P14 (ARGUED).** Those two tests have changed meaning and the crate now says
so. They were evidence that two implementations agreed; they are now a
*structural* regression test that the duplication has not come back. That is
worth less, and pretending otherwise would be the exact failure this project
exists to catch.

### 6.2 The gate carries a measured scale — and the honest limit of that

`merge::Gate` gained a private `noise_sd`. `Gate::new(t)` is
`Gate::with_noise_sd(t, FOCUS_NOISE_SD)` and `tolerance()` keeps the same
operands **and the same association order**, `(t * SQRT_2) * sd`;
`merge::tests::the_default_gate_is_the_compiled_in_constant_bit_for_bit` pins
that on `to_bits()`, not on a printed value. `SoftGate` got the same treatment
and `merge.rs` builds it *from the `Gate` beside it*, so the hard and soft
kernels cannot run at different temperatures.

Fact 631 governed the shape: the scale is **substituted**, never corrected. No
`t/k` appears anywhere on the path.

**P15 (MEASURED, and a limit on P11 rather than a defect in it). The measured
scale is exact for the fixed-window field and approximate for the shipping
edge-aware one.** The default estimator arm is `EdgeArm::Acuity`, which replaces
the operator's own window with a per-pixel radius drawn from
`LEVEL_RADII = [1, 2, 4, 8, 13]`. A calibration is measured at a *fixed*
window — fact 500 is this repository dividing two constants that differed in
exactly that and overstating a ratio by 3.27x — so wherever the scale asks for a
level below `FULL_LEVEL`, the field's true SD exceeds the measured one and the
gate there is looser than nominal.

**This is inherited, not introduced.** `FOCUS_NOISE_SD` is measured at radius 13
and applied to the same varying-radius field today. `--focus` carries the
operator's **own** measured scale into that approximation instead of a foreign
one, which is strictly better than the status quo and strictly worse than a
per-level calibration ladder, which nothing in this repository has. Recorded as
**Q1**.

**P16 (ARGUED). Pass zero keeps the shipped operator under `--focus`, on
purpose.** The depth guide solves a selection *radius*, not a winner, and that
solve is calibrated against Tenengrad's response. Substituting an operator 6.6x
away would move the radius map for reasons unrelated to the contributed measure.
`Ctx::focus_op` is `None` for the guide `Ctx` and `Some` only for pass two.

### 6.3 Refused, not ignored

Following the existing `--gate`/`--pyramid-gate` precedent, `--focus` is refused
wherever it cannot be honoured, and infers the estimator backend when given
without `--merge`. All three verified by running them:

```
$ strehl stack ... --merge pyramid --focus sml-w13
Error: --focus belongs to the estimator merge, and --merge selected pyramid.
  what to do  : no counterpart. --focus names a focus MEASURE, and the pyramid does not compute a focus field at all ...

$ strehl stack ... --merge estimator --focus no-such-op
Error: unknown focus operator `no-such-op`; registered: brenner-w13, laplacian-w13, local-variance-3x3-w13, ring-1-3-w13, sml-w13, tenengrad-sq-w13, tenengrad-w13
(run `strehl focus list` for their host-measured noise scales)

$ strehl stack ... --focus sml-w13          # no --merge
merge backend   : estimator (inferred from --focus; pass --merge pyramid to override)
                  NOTE: this is not the default merge. Your flags asked for estimator, so that is what runs.
```

`--stats` and `STREHL_EDGE_AWARE=layer` are refused with `--focus` too, because
both reach Tenengrad-specific entry points that take no operator. A run that
named one operator and elected with another is the precise failure this seam
exists to remove.

**P17 (DERIVED). Registration is lazy.** Calibrating seven operators costs about
half a second (12 x 512² noise planes each). The registry is built only when a
focus-plugin surface is used, so the default path draws no seed and pays nothing
— and, more importantly, cannot acquire a measured constant by accident.

---

## 7. Verification

### 7.1 Full suite

```
$ cargo test --workspace
test result: ok. 112 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.97s
test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 493.16s   <- byte-freezes
test result: ok. 514 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 29.54s
test result: ok. 35 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 13.68s   <- strehl-plugin
test result: ok. 26 passed; 0 failed; 1 ignored; 0 measured; 0 filtered out; finished in 0.00s
test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
```

693 tests, 0 failures, both freezes holding.

### 7.2 Clippy

Baseline **measured first**, at `0dd3d3f9`, before any edit: 69 warnings,
0 errors. After: identical.

```
$ cargo clippy --workspace --all-targets
unique-warning-lines=69 errors=0
```

### 7.3 Attribution, against four concurrent commits

The BEFORE binary was built at `0dd3d3f9`. Four commits from other lanes landed
before the AFTER binary was built. The hashes in §5.1 matched **anyway**, which
is a stronger result than a controlled comparison would have been: it says
neither this work nor those four moved either render. Had they differed, a
bisect against a "current HEAD without my changes" build would have been
required; it was not, because there was nothing to explain.

---

## 8. Facts, disciplines and questions

**Facts:** P1–P17 above.

**Disciplines**

- **D1.** A contribution surface no shipping command can reach is not a
  contribution surface. **Check the dependency graph, not the API**: `strehl-plugin`
  was 3,282 lines of tested, documented, reviewed, *unreachable* code, and every
  in-crate test passed the whole time.
- **D2.** When two crates hold two copies of one pipeline, **the copy that is
  not in the shipping path is the one that will be right**, because it is the
  one somebody is currently reading. Unify toward the shipping path.
- **D3.** A bit-identity claim between two implementations is conditional on
  **every site where the two resolve a shared parameter differently**, not just
  on the arithmetic. P5: one side read a constant and the other read an env-var
  override of it, and the passing test said nothing. Enumerate the resolution
  sites.
- **D4.** When a constant becomes a variable, pin the default on `to_bits()` and
  pin the **association order** with it. `(t*a)*b` and `t*(a*b)` are different
  `f32`s, and a frozen render can tell.
- **D5.** A provenance line that prints a compiled-in constant is a **claim about
  the run**. The moment the run can use a different value, that line is a defect
  until it is made to read the value in force.
- **D6.** Verify a documented claim on the data the shipping path sees before
  building on it. P4's real-frame check cost one example binary and converted
  "the crate says so" into a number.

**Questions**

- **Q1 (OPEN — the per-level calibration ladder).** P15. A calibration is a
  property of the operator *and its window*, and the shipping election varies
  the window per pixel across `LEVEL_RADII = [1, 2, 4, 8, 13]`. Both
  `FOCUS_NOISE_SD` and any `--focus` scale are therefore exact only where the
  scale is `FULL_LEVEL`. **The measurement that would settle it:** run
  `strehl_plugin::calibrate::calibrate` once per operator per level — five
  numbers instead of one, the calibrator already takes a `FieldConfig` and the
  cost is 5x60 ms — then have `Gate` take a per-pixel scale, or at minimum
  report the level histogram alongside the single number so the size of the
  approximation is visible. Until then the gate's nominal value is exact on the
  majority of pixels and loose on the treated minority, by an amount nobody has
  measured.
- **Q2 (OPEN — the `--stats` and layered arms).** `compute_with_fine` and
  `compute_layered` are the two remaining Tenengrad-specific entry points.
  Generalising them is mechanical (both are `respond` → aggregate → normalise
  with a different aggregate); it was not done because neither is on the
  shipping default path and an unexercised generalisation is a liability.
- **Q3 (OPEN — third-party operators, as opposed to reference ones).** The seven
  operators wired here all live in `strehl-plugin::reference`. The seam takes
  `Arc<dyn FocusMeasure>` and `Registry::register` is public, so an out-of-tree
  crate can register — but **nothing out of tree has been built and run**, so
  "easily contributable by others" is demonstrated for in-tree contributors and
  argued, not measured, for out-of-tree ones. The cheapest test is a fourth
  workspace crate with one operator and one `register` call.

---

## 9. What I did not do

- **I did not re-baseline `byte-freezes.tsv`.** It is byte-identical to HEAD.
- **I did not route the default through the calibrator.** P8 is why: it would
  have replaced `0.015214` with `0.0152113` and moved every frozen render.
- **I did not generalise `compute_with_fine` or `compute_layered`** (Q2).
- **I did not calibrate per level** (Q1) — the single most important follow-up.
- **I did not build an out-of-tree contributor crate** (Q3).
- **`edgeaware.rs` still reads `crate::merge::FOCUS_NOISE_SD` directly** at two
  sites. Out of scope — it is the *radius* rule, not the gate — but it is a seam
  of the same family and will need the same treatment if Q1 is taken.

---

## 10. Files

**Core (the unification)**

- `crates/strehl-core/src/focus.rs` — `FocusMeasure`, `Window`, `Normalisation`,
  `run_measure`, `Tenengrad`, `FieldConfig`, `FieldWorkspace`, `tap`, public
  `SIGMA_EPS`; `compute_with_measure` and `compute_scaled_with_measure`;
  `compute`/`compute_at_radius`/`compute_scaled` delegate to them.
- `crates/strehl-core/src/merge.rs` — `Gate::{with_noise_sd, noise_sd}`, private
  `noise_sd`, and the three pinning tests.
- `crates/strehl-core/src/softgate.rs` — the same for `SoftGate`.

**Plugin (now shims plus the host-measuring half)**

- `crates/strehl-plugin/src/{measure,field}.rs` — `pub use` from core, prose and
  tests retained.
- `crates/strehl-plugin/src/reference.rs` — `Tenengrad` re-exported.

**CLI (the seam)**

- `crates/strehl-cli/src/focus_plugin.rs` — registry construction, name
  resolution, `strehl focus list`.
- `crates/strehl-cli/src/main.rs` — `--focus`, `strehl focus list`, the refusal
  table row, two surface tests.
- `crates/strehl-cli/src/merge_cmd.rs` — `MergeOptions::focus`, `Ctx::focus_op`,
  the two dispatching arms in `field_for`, `Gate::with_noise_sd` at the fold,
  and the two provenance lines from P12.
- `crates/strehl-cli/Cargo.toml` — the dependency edge that was missing.

**Instruments**

- `crates/strehl-cli/examples/build-plugin-field.rs` — the P4/P5/P7 instrument.
- `scripts/build_plugin_tiff_delta.py` — the P11 delta.

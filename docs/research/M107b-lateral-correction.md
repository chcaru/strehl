# M107b — the lateral-CA correction, built as an unwired unit

Follow-on to M107 (`a16976f`, facts 1413–1418). Scope: build the cheap half of the chroma
work — fact 1414's lateral correction — as a self-contained tested unit, and **cost** the
axial middle option without building it.

Bars **L1–L6 and A1 were registered and committed at `ac5daed` before any measurement**,
in `experiments/M107-chroma/PRE-REGISTRATION-3.md`. They are scored below exactly as
written. One registered assumption was **falsified**, and it is reported as falsified.

---

## 1. Verdict

| item | result |
|---|---|
| **L1** zero correction is bitwise identity | **PASS** — 0 differing bits over 12 012 cases |
| **L2** positive control | **NOT RUN AS REGISTERED** — superseded, see §5 |
| **L3** in-sample correction | **PASS** — 1.4274 → 0.0412 plane px, 97.1 % removed |
| **L4** out-of-sample transfer | **SPLIT: one direction PASSES (0.950), one FAILS (0.541)** |
| **L5** green untouched | **PASS** — exact no-op, asserted bitwise |
| **L6** exact composition, no second interpolation | **PASS** — worst relative error <= 1e-12 |
| **A1** is a constant axial offset the right model? | **INDETERMINATE on depth; ADEQUATE on radius — and scored on 3 stacks, not the 5 registered** |
| registered optical-centre assumption | **FALSIFIED — and the reason matters more than the fix** |
| **the shipped sign** | **WAS INVERTED. Caught in a render-domain preview, after 9/9 green unit tests. See §12** |

> **Read §12 first.** The unit I committed at `d551488` applied its correction in the wrong
> direction: it made the aberration **7.2 % worse** on a real render instead of removing it.
> Nine unit tests passed on it, and every one of them was structurally incapable of
> catching it. The coefficients were right; only the application direction was wrong. It is
> repaired, and the repair is now backstopped by a test that is shown to fail on the defect.

**The correction is free.** L6 confirms a radial magnification composes *exactly* into the
`Similarity` the gather already applies, so it rides the existing interpolation and adds no
second kernel application. The trade the orchestrator asked me to watch for — a second
resample costing more sharpness than the fringing it removes — **does not arise**.

---

## 2. The finding that changed what shipped

I registered `centre_offset = (0,0)` as an assumption and promised to bound it. Then E2's
own output turned out to have **fitted** the centre, at `(893.4, −601.9)` plane px.

Forcing the centre to the plane centre costs **5.37×** in residual rms (0.0725 → 0.3896)
and biases `eps` by 14 % (−704.5 → −805.3 ppm). So the term is real and cannot be dropped.
**My registered assumption is falsified.**

But before shipping it as a lens property, look at what those two parameters *are*:

```
d = eps * ((r - c) . n)  =  eps*(r.n)  -  (eps*c) . n
```

The second term is a **constant vector projected on each edge normal** — which is exactly a
uniform translation of the channel. *"The optical centre is at c"* and *"red is translated
by −eps·c"* are **the same two parameters**. No amount of care with this parameterisation
separates them, and that is a statement about the model, not about effort.

Two readings, same numbers:

| reading | value | plausibility |
|---|---|---|
| decentred optical axis | 1077 px from plane centre, **51 % of the half-diagonal** | not plausible for a real lens |
| uniform channel translation | **(+0.629, −0.424) plane px** | CFA co-siting predicts **~0.5 px per axis** |

Red sits at quad corner `(0,0)`; a green built from `(1,0)` and `(0,1)` sits half a quad
away in each axis. **The measured translation is the same order as that lattice offset**,
and a 51 % decentring is not.

So the shipped record carries an explicit `translation` field, documented as
**unattributed**, rather than a `centre_offset` that would assert an optical cause never
measured. The radial coefficient is lateral CA; the translation may be lattice, may be
optical, and this instrument cannot say which. A test pins the field so a future edit
cannot quietly relabel it.

**This does not touch fact 1414's `eps_R = −704.5 ppm`** — that is the radial coefficient,
and it is unchanged. What is in question is only the interpretation of the other two
parameters, which fact 1414 does not claim.

---

## 3. Bars scored as written

### L1 — bitwise null. **PASS.**

> *0 of N differ in any bit.* Falsifier: any single differing bit.

**12 012 cases, 0 differing bits.** Scored on `f64::to_bits()`, deliberately: `==` cannot
distinguish `+0.0` from `−0.0`, so a bar written with `==` would pass on a transform whose
signed zeros had been flipped. Adversarial inputs included signed zeros, subnormals and
`1e300` scales. Absence of a profile is a no-op on the same standard.

### L3 — in-sample. **PASS, with its own null.**

> *<= 0.35 plane px.* Falsifier: > 0.70.

Gated median `\|dR\|` **1.4274 → 0.0412** plane px, **97.1 % removed**.

The control that makes it mean something: the same correction applied to the `G1−G2` null
moves it **0.0135 → 0.0137, i.e. −1.5 %** — it removes *nothing* from a channel pair with
nothing to remove.

### L4 — out-of-sample transfer. **SPLIT, and reported as split.**

> *>= 60 % of the in-sample reduction.* Falsifier: < 30 %, or `\|dR\|` increases.

| fit on | applied to | uncorrected | after transfer | removed | frac of in-sample |
|---|---|---|---|---|---|
| `tweezers-cpl` (n=12) | `bee-3-cpl` (n=8) | 1.2149 | 0.1069 | **91.2 %** | **0.950 PASS** |
| `bee-3-cpl` (n=8) | `tweezers-cpl` (n=12) | 1.7883 | 0.8343 | 53.3 % | **0.541 FAIL** |

**Neither direction makes it worse**, so the falsifier does not fire — but one direction
misses the registered 0.60 bar and **is recorded as failing, not narrowed to fit**. The
asymmetry tracks the fit sets: 8 ROIs predict 12 much worse than 12 predict 8.

Honest status: **lateral CA transfers, but 8 ROIs are not enough to fit a transferable
profile.** The orchestrator's expectation is supported in the well-fitted direction and not
established in the other. Fact 52's warning is not dismissed by this arm.

Transfer control: the same transfer applied to `null_dG` removes **5.3 %** in one direction
and makes it **118 % worse** in the other — i.e. applying a model fitted elsewhere to a
channel with no signal injects noise, exactly as it should. The transfer arm is not
trivially improving everything it touches.

### L5 — green untouched. **PASS.** `eps(Green)` is `None` by construction; asserted bitwise
over 2000 random transforms. `eps_b` is **`None`, not `0.0`** — blue was never measured, and
absence is not a measured zero.

### L6 — exact composition. **PASS.**

> *<= 1e-12 relative.* Falsifier: > 1e-9 → stop and report.

Worst relative error over 20 000 randomised transforms and points: **<= 1e-12**. The
correction composes into the existing alignment `Similarity` exactly, so it rides the
1.0735x upsample's interpolation and adds no second resampling pass.

**Correction, post-verification: this section originally read "the correction is a closed
form, not a linearisation — `1/(1+eps)`, not `1−eps`", and pinned a 0.0010 plane px
"reciprocal-vs-linear gap".** That was the inverted convention described in §12. The scale
is `1 + eps` exactly; there is no reciprocal and no second-order gap to pin. **L6 itself
was unaffected by the error** — it asserts that two routes agree, and they agreed just as
exactly while both were wrong. That is the point of §7.

---

## 4. A1 — the axial middle option, and the concern I was asked to kill

> Registered, verbatim: *"A constant offset is adequate if `R^2 < 0.10` on both regressions
> in **all 5 stacks**. A constant offset is the WRONG MODEL if `R^2 >= 0.30` on either
> regression with a consistent sign across stacks. Between 0.10 and 0.30 I report it as
> indeterminate and do not resolve it post hoc."*

**Deviation, disclosed: I scored A1 on 3 stacks, not the 5 the bar names.** The parent
milestone persisted argmax volumes for only 3 (`e3_*.npz`); the two no-CPL controls were
never saved. So 5 was **not achievable from existing data**, and I did not re-render to
reach it. **An earlier draft of this section silently dropped the "5" from the quoted bar.
That was caught in independent verification, not by me, and it is exactly the quiet
narrowing the pre-registration exists to prevent.** The consequence is real: A1's verdict
could move if the two unmeasured stacks behaved differently.

Scored against the `G1−G2` null floor, as registered, because `k_R − k_G` and `k_G` share a
term and regressing one on the other induces a spurious slope through shared noise alone.

| stack | median `k_R−k_G` | `R^2` vs depth | null `R^2` | `R^2` vs radius | null `R^2` |
|---|---|---|---|---|---|
| `bee-3-cpl` | −0.7390 | 0.0014 | 0.0146 | 0.0030 | 0.0075 |
| `leaf-2-cpl` | −1.0728 | **0.1309** | 0.0004 | 0.0369 | 0.0144 |
| `tweezers-cpl` | −1.0476 | 0.0823 | 0.0257 | 0.0195 | 0.0004 |

**vs radius: CONSTANT OFFSET ADEQUATE** — all below 0.10. The axial term is *not* radially
structured, which also means it is not confounded with lateral CA.

**vs depth: INDETERMINATE**, as registered. Two stacks below 0.10, one at 0.1309. The
wrong-model clause requires a **consistent sign** and the signs are **not** consistent
(−0.0023, **+0.0911**, −0.0114). I am not resolving this post hoc.

**I rendered it rather than quoting it** (`fig8-a1-depth.png`), and the figure changes the
reading of that 0.1309: **there is no monotonic depth trend in any of the three.** leaf-2's
`R^2` is driven by large non-monotonic excursions in a noisy binned median, not by a slope.
The null is drawn on the same axes in every panel, because a trend the null also shows is
not a trend.

**What the maps do show, and it is the useful part:** `k_R − k_G` has real *spatial*
structure — `tweezers-cpl` in particular is visibly banded. So a constant offset would
capture the median but leave **structured** residual of order ±0.5 frames, not white noise.

**Caveat visible only in the figure:** on `bee-3-cpl` the null departs from zero to **+0.4
frames in the last few depth bins**. The confidence gate degrades at the extremes of the
bracket. Any depth-resolved claim about the ends of a bracket should not lean on this data.

---

## 5. L2, and why it was not run as registered

L2 planted a magnification into a real plane and asked the instrument to recover it. It was
**superseded before it was run**, and I am recording that rather than quietly dropping it.

E9/E10 measure the same property more directly and without L2's weakness. L2's ratio would
have been computed from a *resampled* plane, which is why it needed L2-CTRL to bound
interpolation blur. The transfer arm (L4) tests the same capability — *does the fitted
coefficient predict displacement it was not fitted to* — on **unresampled** data, so it
carries no blur confound at all and is a strictly stronger test.

**This is a deviation from the pre-registration and it is logged as one.** L2 remains
un-run; the capability it was to establish is established by L3 + L4 instead.

---

## 6. What was built

`crates/strehl-core/src/optics.rs`, 9 tests, all passing; full crate **280 passed, 0
failed**.

- `OpticalProfile` — versioned record carrying `eps_r`, `eps_b`, the **entire** optical path
  as a string, the stacks fitted from, `FitStats` (`R^2`, permutation p, residual rms, n),
  and `measured_at` for aperture/magnification.
- `measured_at` is **`None`**: the capture metadata to hand did not record it. Lateral CA
  varies with both, so a guess there would silently widen the profile's claimed
  applicability. **Absent, not guessed.**
- `Channel`, `eps()`, `compose()`, `displacement_at()`, `by_key()`.
- **Nothing is wired.** `merge_cmd.rs` (M97) and `align_cmd.rs` (M85) are untouched.
- **Opt-in by construction**: the entry point takes `Option<&OpticalProfile>` and `None` is a
  bitwise no-op, so the frozen linear path cannot move unless a profile is deliberately
  supplied.

**One line was taken in a file I do not own**: `pub mod optics;` in
`crates/strehl-core/src/lib.rs`. A module that is not declared cannot be compiled or tested,
so "build a tested unit in strehl-core" is not achievable without it. It is a single
insertion in an alphabetical list, `lib.rs` was clean before and after, and **it is trivially
revertible if the orchestrator would rather place it themselves.**

---

## 7. Cost of the axial middle option — costed, not built

Keep the single green election; gather red and blue at `k_G + delta_c`.

**It does not multiply the dominant term.** Fact 1417 measured focus plus regularisation at
**88 % of pass-1 work**, and that is precisely what the middle option *reuses* — one
election, unchanged. The added work is confined to the gather. That makes it categorically
cheaper than per-channel election's 2.8× CPU / 4–4.5× wall clock.

**I cannot give you a number, and I will not extrapolate one.** Quantifying it needs the
gather's share of wall clock instrumented inside `merge_cmd.rs`, which is M97's file and
which I may not touch. §9.1 of the parent report was already an extrapolation and I am not
adding a second.

**Five ways it could go wrong**, in the order I would test them:

1. **The offset is not one constant.** The per-stack medians are **−0.74, −1.07, −1.05**.
   A single global constant is already contradicted by three stacks. It would have to be
   per-magnification profile data, or fitted at runtime — which changes it from "a scalar"
   into a small estimation problem.
2. **Bracket ends.** `k_G + delta` falls outside the bracket near either end and must clamp,
   reintroducing the defect exactly at the depths where A1's null is least trustworthy (§4).
3. **Frames are not depth.** A constant *frame* offset assumes a uniform focus step. On a
   bracket with variable step it is the wrong quantity, and nothing in this milestone
   establishes the step is uniform.
4. **The gate never saw it.** M93's gate is calibrated on green. Gathering red from a frame
   the gate evaluated only for green means red is taken from a frame that was never gated
   for red.
5. **Structured residual.** Per A1, a constant offset leaves ±0.5 frames of *spatially
   structured* residual, not noise. Whether that is visible depends on the focus step.

**Ordering recommendation, unchanged from fact 1417 and now supported by L6:** ship lateral
first. It composes exactly, costs nothing at run time, and is one scalar plus a translation.
The axial fix is a merge-architecture change behind a noise-model prerequisite.

**Where lateral belongs:** in the **aligner's transform**, not a post-merge plugin. It is
already a `Similarity`; a post-merge plugin would need its own resampling pass and would pay
the −0.2360 dex the composition avoids.

---

## 8. What I could **not** determine

1. **Whether the translation term is optical or lattice.** Structurally undecidable in this
   parameterisation — the two hypotheses are the same two parameters. Separating them needs
   a higher-order radial term (`eps1*r + eps3*r^3`), where a true optical centre would be the
   common centre of both. Not attempted.
2. **Blue's coefficient.** `eps_b` is `None`. E9 shows blue's centre is **not identified** —
   96.6 % of bootstrap resamples put it off-sensor, and its 95 % CI for `eps` spans zero
   (−66.1 to +151.0 ppm). Blue is not measurable with these 20 ROIs.
3. **Whether the profile transfers from only 8 ROIs** — L4's failing direction. Fixing this
   is more ROIs, not a different method.
4. **The cost of the middle option in wall clock** — needs instrumentation inside a
   contended file (§7).
5. **A1 on depth** — indeterminate, and left indeterminate. **And scored on 3 of the 5
   stacks its bar names**, because only 3 argmax volumes were ever persisted (§4).
6. **Whether the correction improves a real render.** Everything here is measured in the fit
   domain on unresampled CFA data. **No corrected image has been produced**, because
   producing one requires wiring into the gather. That is the next milestone's job and the
   claim "97.1 % removed" is a statement about displacements, not about a rendered picture.

---

## 9. Provenance — full invocations and environment

Per rule 47 as amended: environment as well as flags.

| item | value |
|---|---|
| repo HEAD at build | `be39fba` (parent report through `63d24ca`; bars at `ac5daed`) |
| bars committed before measurement | `ac5daed` |
| Rust tests | `cargo test -p strehl-core --lib` → **280 passed, 0 failed, rc=0** |
| `CARGO_TARGET_DIR` | `C:\dev\strehl-out\M107-chroma\cargo-target-m107` (own, not shared) |
| `STREHL_WARPMAP` / `STREHL_ALIGN` / `STREHL_FIX_HALO` | **unset and irrelevant — no strehl binary was invoked in this milestone** |
| inputs | `e1_raw_edges.json`, `e3_*.npz` — both produced by M107 `a16976f`, already provenanced in `M107-chroma.md` §13 |
| capture library | **not read and not written**; no ARW was decoded here |
| corpus lint | `python scripts/corpus_lint.py` → rc=0, `OK — no violations` |

No render was produced, so there is no output hash to freeze. **That is itself the honest
record**: this milestone measured in the fit domain, and its numbers are not image hashes.

Scripts: `e9_centre.py`, `e10_transfer.py`, `e11_axial.py`, `fig8_a1.py` under
`experiments/M107-chroma/src/`.

---

## 10. Candidate facts for the fold

- **P19.** The "optical centre" of a 3-parameter lateral-CA fit is **mathematically
  degenerate with a uniform channel translation**, and on this instrument the fitted value
  reads as either a physically implausible 51 %-of-half-diagonal decentring *or* a
  **(+0.629, −0.424) px** translation of the same order as the **~0.5 px/axis CFA co-siting
  offset**. Dropping the term costs 5.37× in residual, so it must be kept — but calling it
  optical is an attribution the measurement does not support. MEASURED (`e9`, `e10`).
- **P20.** **Lateral CA correction is exactly free.** A radial magnification about a point is
  itself a `Similarity`, and `Similarity` is closed under composition, so the correction
  folds into the transform the gather already applies — verified to <= 1e-12 over 20 000
  randomised cases. No second interpolation, therefore none of the −0.2360 dex a second
  kernel would cost. MEASURED (`optics.rs::l6_composition_is_exact`).
- **P21.** The fitted lateral coefficient **removes 97.1 %** of the measured red–green
  displacement in sample (1.4274 → 0.0412 plane px) while removing **−1.5 %** from the
  `G1−G2` null. Out of sample it transfers at **0.950** of in-sample when fitted on 12 ROIs
  and **0.541** when fitted on 8 — so lateral CA does transfer, but **8 ROIs are not enough
  to fit a transferable profile**. MEASURED, and the 0.541 arm is a **registered bar reported
  as failed**.
- **P22.** The axial offset is **not radially structured** (`R^2` <= 0.037 vs radius on 3/3
  stacks) and shows **no monotonic depth trend** — but its per-stack medians differ
  (−0.74, −1.07, −1.05) and its residual is **spatially structured**, so a single global
  constant frame offset is already contradicted by three stacks. MEASURED (`e11`, fig8).

## 11. Disciplines

- **D6.** When a fit reports a *derived* parameter as a ratio (a centre from `coef/eps`),
  test whether it is identified before believing it. Bootstrapping E2's three fits put
  **96.6 %** of blue's centres and **95.3 %** of the null's centres **off the sensor**, while
  red's stayed on it — the same code, the same 20 ROIs, and two of three answers were
  numerical artefacts.
- **D7.** A model term that improves the fit is not thereby explained. The centre term earns
  its 5.37× and is *still* unattributed. Ship the term; do not ship the story.

---

## 12. The inverted correction sign

### What happened

`d551488` shipped `compose()` with `let s = 1.0 / (1.0 + eps)`. The correct scale under
this codebase's transform convention is `s = 1.0 + eps`. The unit therefore applied its
correction in **exactly the wrong direction**, doubling the aberration instead of removing
it.

I did not find this from the tests. I found it by running a render-domain preview on
`bee-3-cpl` — the owner's original complaint — and watching a **registered falsifier fire**.
The post-hoc sign diagnostic (`p5_sign_diagnostic.py`) then measured both directions on the
same pixels:

| direction | radial chroma slope | vs uncorrected |
|---|---|---|
| uncorrected | 141.1 ppm | — |
| **as shipped at `d551488`** | 151.3 ppm | **7.2 % WORSE** |
| **inverted (as now shipped)** | −8.1 ppm | **94.3 % removed** |

94.3 % in the render domain is consistent with L3's 97.1 % in the fit domain, which is the
independent check that the repaired direction is the right one rather than merely the
better of two.

### Why the convention is `1 + eps`, derived rather than tried

`warpmap.rs:14-30` documents every transform in this project as a **pull**: `dst(p) =
src(T(p))`. `T` maps the pixel you *want* to the pixel you must *sample*. A channel imaged
at magnification `(1 + eps)` records a scene point `u` at `x = (1 + eps) u`, so
`src(x) = scene(x / (1 + eps))`. Requiring `dst(p) = scene(p)` gives `T(p) / (1 + eps) = p`,
hence `T(p) = (1 + eps) p`.

That module's own doc comment warns, in terms: inverting it "is the single most likely bug
in a consumer of this module and it is silent." It was right, and I was the consumer.

**The translation term was inverted in the same way and by the same reasoning.** `compose`
computed `b' = (b − t) · s`; the fit's model (`e10_transfer.py::predict`) is
`observed = (1 + eps)·truth + t`, so the pull requires `b' = s·b + t`. The corrected form is
also *simpler*, and still exactly composable — L6 is unaffected.

### Why nine green tests could not have caught it

This is the part worth folding.

- **L1** (zero correction is bitwise identity), **L5** (green untouched) and **L6** (exact
  composition) are **sign-symmetric**. Every one of them holds identically for `+eps` and
  `−eps`. They cannot express a direction, so they cannot fail on one.
- `correction_opposes_the_aberration` *did* test direction — but asserted against
  `displacement_at()`, which is built from the same convention as the code under test.
  **Circular.** It agreed with the implementation because it was derived from it.
- Three tests **hardcoded the implementation's own expression**, `1.0 / (1.0 + p.eps_r)`.
  A test that restates the code cannot disagree with it.
- The independent verifier's mutation testing did not catch it either: it mutated
  `1/(1+eps)` to `1−eps`, and **both are the same wrong direction**. A mutation that stays
  inside the defect's own convention cannot reveal it.

**A unit suite can be 9-for-9 green, survive independent mutation testing, and still ship a
global sign inversion.**

### The repair, and proof the repair is testable

Two new tests, both phrased in **physical** terms rather than in terms of the
implementation's `s`:

- `a_planted_magnification_is_actually_undone` — plants a known `+2.0e-3` magnification,
  then asserts that asking the corrected image for scene radius `u` samples exactly where
  an `(1+eps)`-magnified channel recorded it, over 4 radii × 3 directions. It additionally
  asserts the inverted convention is **>1e-6 away**, so the test cannot quietly become
  vacuous.
- `the_pull_maps_wanted_to_sampled_not_the_reverse` — the same claim at `eps = 0.05`, where
  the two conventions are **47.6 px apart** at `r = 1000` and cannot hide in a tolerance.

`p6_sign_mutation.py` plants the old convention back into `compose` and asserts the suite
turns red **and names which tests turn red**, so a mutation caught only by an unrelated test
does not read as a pass. Bars registered in its docstring before the run:

| bar | claim | result |
|---|---|---|
| M1 | mutated crate exits **exactly 101** | `EXIT=101` **PASS** |
| M2 | `a_planted_magnification_is_actually_undone` goes red | RED **PASS** |
| M3 | `the_pull_maps_wanted_to_sampled_not_the_reverse` goes red | RED **PASS** |
| M4 | restored crate exits **exactly 0** with 281 tests | `EXIT=0`, 281 passed **PASS** |

5 of 281 tests go red on the mutation. Exit codes are asserted against the **exact** expected
value, never `-ne 0` (rule 47 as amended).

### An instrument defect found inside the mutation harness

M4 failed on the harness's first run: the restored, byte-identical file still produced the
mutant's failures. `shutil.copy2` **preserves the backup's mtime**, which is older than the
artifacts cargo built from the mutant, so cargo considered the restore up to date and
re-ran the mutant binary. Read naively, that is a clean tree reporting 5 failures.

Fixed with `os.utime(SRC, None)` after restore. **A mutate-then-restore harness must stamp
the restored file, or the clean arm reports a false red.**

### Scope of the repair

`eps_b` remains **`None`** — blue was never measured — so cyan/blue-side fringing is
untouched by construction. Only red is corrected. The unit remains **unwired**: nothing in
`merge_cmd.rs` calls it, per the file constraint.

### Candidate facts

- **P23.** The lateral-CA correction shipped at `d551488` had a **globally inverted sign**;
  measured on `bee-3-cpl` it made radial chroma **7.2 % worse** (141.1 → 151.3 ppm), while
  the corrected direction removes **94.3 %** (141.1 → −8.1 ppm), consistent with L3's 97.1 %
  in the fit domain. MEASURED (`p1_preview`, `p5_sign_diagnostic`).
- **P24.** The defect survived **9/9 green unit tests and independent mutation testing**,
  because L1/L5/L6 are sign-symmetric, the one directional test asserted against a helper
  built from the same convention, three tests hardcoded the implementation's expression, and
  the verifier's mutation (`1/(1+eps)` → `1−eps`) stayed inside the wrong convention.
  MEASURED.

### Disciplines

- **D8.** **A sign error cannot be caught by a sign-symmetric test, and most invariance
  tests are sign-symmetric.** Round-trip, composition-exactness and zero-is-identity all
  hold for `+eps` and `−eps` alike. At least one test must state the claim in **physical**
  terms — where the feature is, not what the scale variable equals — and must assert that
  the opposite convention is measurably far away.
- **D9.** **A test that restates the implementation's expression is not a test.** Three
  tests here contained `1.0 / (1.0 + p.eps_r)` copied from the code. They tracked the defect
  into production.
- **D10.** **Mutation testing only proves what its mutants span.** Mutating within the
  defect's own convention (`1/(1+eps)` → `1−eps`) cannot reveal that the convention is
  wrong. Mutate **across** the axis you are worried about.
- **D11.** In a mutate-then-restore harness, **stamp the restored file's mtime**.
  `shutil.copy2` restores the old mtime and the build system reuses the mutant's artifacts,
  producing a false red on the clean arm.

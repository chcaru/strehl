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
| **independent verification** | **4 defects found; 3 fixed, 1 recorded. Its mutation matrix found a hole mine missed. See §13** |

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
| **as shipped at `d551488`** (`q = p/(1+eps)`) | 151.3 ppm | **7.2 % WORSE** |
| radial flipped, old translation form (`q = s(p−t)`) | −8.1 ppm | 94.3 % removed |
| **as now shipped** (`q = s·p + t`, radial + fitted translation) | 17.3 ppm | **87.7 % removed** |
| **radial only, translation ablated** | **0.6 ppm** | **99.6 % removed** |

**Attribution correction, from independent verification.** An earlier draft of this table
and of fact P23 attributed **−8.1 ppm / 94.3 %** to "the corrected direction as now
shipped". It is not: that arm comes from `p5_sign_diagnostic.py`, which flipped the *radial*
scale while keeping the *old* translation form `q = s(p − t)`. The convention `optics.rs`
actually implements measures **17.3 ppm / 87.7 %**, and the radial term on its own measures
**0.6 ppm / 99.6 %** (§12.1). The commit message of `4fa5b9f` carries the same
misattribution and is corrected here rather than rewritten.

All three corrected arms are far from the 7.2 %-worse defect, so the direction finding is
unaffected — but the consistency argument against L3's 97.1 % should be made with **99.6 %
(radial only)**, not with 94.3 %, and §12.1 is why.

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
  measured on `bee-3-cpl` it made radial chroma **7.2 % worse** (141.1 → 151.3 ppm). The
  corrected direction, **radial term only**, removes **99.6 %** (141.1 → 0.6 ppm),
  consistent with L3's 97.1 % in the fit domain. MEASURED (`p1_preview`,
  `p5_sign_diagnostic`).
- **P24.** The defect survived **9/9 green unit tests and independent mutation testing**,
  because L1/L5/L6 are sign-symmetric, the one directional test asserted against a helper
  built from the same convention, three tests hardcoded the implementation's expression, and
  the verifier's mutation (`1/(1+eps)` → `1−eps`) stayed inside the wrong convention.
  MEASURED.
- **P25.** Of the fitted lateral model, only the **radial** term earns its place: on
  `bee-3-cpl` the radial term alone removes **99.6 %** of the R−G radial slope
  (141.1 → 0.6 ppm), while adding the fitted, unattributed **translation** term leaves
  **17.3 ppm** — 12x the residual. The translation term should be recorded, not applied.
  MEASURED (`p1_preview`, `M107_NO_TRANS=1`); one stack, in-sample. See §12.1.

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

### 12.1 The translation term makes it WORSE, and should not be applied

Re-running the corrected preview with the translation term ablated
(`M107_NO_TRANS=1`) separates the two halves of the fitted model:

| applied | R−G radial slope | reduction |
|---|---|---|
| nothing (uncorrected) | 141.1 ppm | — |
| as shipped at `d551488` (inverted) | 151.3 ppm | **−7.2 %, i.e. worse** |
| **radial only, corrected sign** | **0.6 ppm** | **99.6 %** |
| radial + fitted translation, corrected sign | 17.3 ppm | 87.7 % |

**The radial term alone removes essentially all of it. Adding the fitted translation puts
back 12x the residual.** In both arms blue is untouched (`eps_b = None`, B−G moved 0.00 %)
and the `eps = 0` null is bitwise identical.

This is consistent with what the parent milestone already said about that term and did not
resolve: the translation is **degenerate with an optical-centre offset** (`d = eps(r·n) −
(eps·c)·n`), its measured magnitude (0.629, −0.424) plane px is close to the ~0.5 px/axis
CFA co-siting offset, and read as decentring it would be 51 % of the half-diagonal, which is
not plausible. It was shipped as an explicitly **unattributed** field. The render-domain
measurement now says it is not merely unattributed but **harmful**.

**Recommendation for the wiring commit, which I am not making tonight:** apply the radial
term only, and treat `translation` as recorded provenance rather than as something to apply.
I have deliberately **not** re-engineered `optics.rs` to enforce that. The code faithfully
implements the model that was fitted, the unit is unwired so nothing consumes it, and
rewriting a transform convention a second time under time pressure is precisely how the
inverted sign got in. **This is a measurement and a recommendation, not a change.**

**Bounded, honestly:** one stack (`bee-3-cpl`), one metric (radial R−G slope on the top-1 %
gradient pixels), in-sample. The radial coefficient's out-of-sample behaviour is L4, which
**split** (0.950 one direction, 0.541 the other). Whether the translation term is harmful on
the other four stacks is **not measured**, and a wiring commit should measure it before
relying on this recommendation.

---

## 13. Independent verification, and what it found

Rule 47: I may not verify my own work. §12's repair was verified independently. The verifier
**re-derived the pull convention from `warpmap.rs` rather than accepting mine**, reproduced
all five ppm figures exactly, confirmed `p6`'s restore was byte-identical, and confirmed the
unit has no caller. It also found four defects. Three are fixed here; one is recorded.

### 13.1 The hole its mutation matrix found, which mine did not

The verifier ran 16 mutants across axes I had not. **Three survived with 281 passed, 0
failed:**

| mutant | result |
|---|---|
| `translation` both signs flipped | **SURVIVED** |
| `translation` scaled 10x | **SURVIVED** |
| `translation` axes swapped | **SURVIVED** |

Every test that touched translation **re-read `p.translation` and recomputed its own
expectation from it**, so the suite was self-consistent for any non-zero pair. The
*direction of the code path* was pinned; the *value and sign of the datum* were not.

This is the same defect class as §12, one level up. §12 was tests that restated the
implementation's **expression**. This is tests that restated the profile's **data**. In both
cases the suite was green because it had agreed to whatever the code said.

**Fixed** by `the_shipped_coefficients_match_the_fit_they_claim`, which asserts the literal
fitted numbers — `eps_r = -704.5 ppm`, `t = (+0.6294, -0.4240)` plane px — including signs,
and asserts the components are far enough apart (48 %) that an axis swap cannot pass.
`p6_sign_mutation.py` gained a bar **M5** that replays all three survivors and requires each
to be killed **by that specific test**, not incidentally by another:

```
M5  translation-datum mutants (all three survived verification)
    sign flip        EXIT=101  killed by the_shipped_coefficients_match_the_fit_they_claim: yes  PASS
    x10 magnitude    EXIT=101  killed by the_shipped_coefficients_match_the_fit_they_claim: yes  PASS
    axis swap        EXIT=101  killed by the_shipped_coefficients_match_the_fit_they_claim: yes  PASS
```

282 passed, 0 failed, `EXIT=0` clean; `EXIT=101` on every mutant.

### 13.2 The stale doc comment

`compose`'s **public rustdoc still specified the refuted convention** — `q' = (q - t)/(1 +
eps)`, `s = 1/(1 + eps)` — 37 lines above an inline comment saying the opposite. No runtime
effect, and my own tests could not see it, but `cargo doc` is how the next agent learns this
function, and it would have taught them the defect. **Fixed**, and the old formula is kept
named in the doc so the next reader knows which one was wrong.

### 13.3 The precondition that was documented only inside the stale paragraph

`compose` scales about the **coordinate origin**, not the plane centre; `z` must already be
plane-centre-relative. That requirement existed *only* in the paragraph that was refuted, so
fixing §13.2 would have deleted it. Harmless while unwired, but a wiring commit feeding
absolute warpmap coordinates would introduce a uniform red offset of order `eps ×
half_diagonal ≈ 1.5 sensels`. **Now stated explicitly in the doc as a precondition on the
wiring commit.** No test pins it; recorded as a gap.

### 13.4 The misattributed number

Corrected in §12's table and in fact P23. See the attribution note there.

### 13.5 Gaps the verifier named that I have NOT closed

- **The pull convention is not provable by the unit suite.** Both new tests *encode* it. The
  only independent evidence is the render-domain measurement — one stack, one metric,
  in-sample. Stated, not fixed.
- **Translation direction is covered by one assertion**, in
  `translation_composes_exactly_and_round_trips`. Neither §12 test exercises it; both zero
  the translation. §13.1 pins the datum, not the path.
- **No test pins the centre-relative precondition** (§13.3).
- The verifier ran `strehl-core --lib` and the M107 P-series only — not the CLI crate tests.

### Candidate facts

- **P26.** A test suite can pin a code path's *direction* while leaving the *datum* it
  operates on completely unconstrained: three mutations of the shipped `translation`
  constant (sign flip, 10x, axis swap) each left **281 passed, 0 failed**, because every
  test re-read the constant and recomputed its expectation from it. MEASURED (independent
  verification, 16-mutant matrix).

### Disciplines

- **D12.** **Pin measured constants against their source of truth, not against themselves.**
  A test that reads a constant and derives its expectation from it is green for every
  possible value of that constant. Assert the literal fitted number, its sign, and enough
  structure to defeat a permutation of its components.
- **D13.** **Delete a refuted comment by rewriting it, not by removing it** — check first
  whether it is the only place a still-valid precondition is written down. `compose`'s
  centre-relative requirement lived exclusively inside the paragraph that was wrong.
- **D14.** **A mutation matrix proves only what its axes span.** Mine mutated the scale;
  the verifier's mutated the data, the channel dispatch, the early return and the alignment
  term, and only that wider matrix found the hole. Ask an independent party to choose the
  axes, because the author's blind spot chooses the author's mutants.

---

## 14. Cache-key contamination audit (fact 1446)

`StackIdentity` omits `reference` and `resampler`, so an identical command line can return
bytes produced under different settings depending on what ran earlier in the session. The
orchestrator asked every agent to run a re-run-after-an-unrelated-align control.

**I did not run that control, because it does not apply to this milestone, and running it
would have tested a code path M107b never used.** Saying so is the honest answer; a green
control on an unexercised path would be theatre.

### 14.1 M107b invoked the renderer zero times

Every measurement in this report is a NumPy transform of a **pre-existing** file. The only
`subprocess` call anywhere in `experiments/M107-chroma/src/` is `p6_sign_mutation.py`
invoking **cargo**, not `strehl`:

```
rg "subprocess|strehl\.exe|Popen|os\.system|check_call" experiments/M107-chroma/src/
  -> p6_sign_mutation.py:37  import subprocess
     p6_sign_mutation.py:79      p = subprocess.run(     # ["cargo", "test", ...]
```

### 14.2 Why the sign finding is immune by construction

All four arms of §12 — uncorrected, as-shipped-inverted, corrected, translation-ablated —
are transforms of **one file, read once, in one process**. There is no per-arm render, so
there is no per-arm cache lookup that could differ. A cache defect cannot differentiate arms
that never re-invoked the binary. **The relative comparison that carries the finding is
structurally out of reach of fact 1446.**

### 14.3 The control that does apply: input provenance and instrument determinism

| control | result |
|---|---|
| input file hash, now | `bee-3-cpl-catmull-rom.tif` **`E400A63AA9F6AB1F`**, 197 797 874 bytes |
| same file's hash as recorded by the parent milestone | `E400A63A…` (`M107-chroma.md:1005`) — **matches, unchanged under me** |
| `p1_preview.py` run twice back to back | stdout **byte-identical**, `EXIT=0` both |

So the instrument is deterministic and the input has not moved. **A == B** for the only
sense in which my arms can be re-run.

### 14.4 What IS exposed, stated rather than defended

- **The fitted coefficients** (`eps_R = -704.5 ppm`, `t = (0.6294, -0.4240)`) come from the
  **parent milestone's** renders and argmax volumes, not from anything M107b executed. If
  those renders are contaminated, the *magnitude* of the correction is wrong. **The
  direction is not** — §12's sign result is a within-image measurement.
- **`docs/research/M107b-radial-chroma.md`** (the D2 confound work) reads the orchestrator's
  `ORCH-thennow` HEAD renders (`lavendar-HEAD-8f46f04.tif` `F12B14C4…`,
  `marker-HEAD-8f46f04.tif` `DB7BAAD2…`). Those are renders I did not produce and cannot
  vouch for. That report's conclusion is a statement about a *confound in the D2 metric*
  rather than about a pixel difference between two arms, so it degrades gracefully — but it
  inherits whatever those two files are.
- **§12.1's ablation and the "141.1 ppm" baseline** are measured on the file *named*
  `catmull-rom`. Given fact 1446, **that label is unverified** — I can vouch for the bytes,
  not for the resampler that produced them. Nothing in this report depends on it being
  catmull-rom specifically.

### 14.5 A datum for the orchestrator, offered with its limits

The three `ORCH-kernel` arms differ **only** in `resampler` and were rendered in sequence.
Hashed first-hand just now:

```
catmull-rom  E400A63AA9F6AB1F
nearest      50B94F315CA8DCC0
bilinear     AFDF3BE9CF82DD78
```

**Three distinct hashes.** If `resampler` were being silently dropped in favour of a cached
first render, at least two of these would collide. They do not.

**Limits, because this is weaker than it looks:** I have not read the cache internals, I did
not produce these files, and I do not know whether that run used distinct output paths, a
cleared cache, or a code path that bypasses it. This is *consistent with* the resampler
having taken effect on that particular sequence; it is **not** evidence that the key is
sound, and it does not generalise to `reference`. Route it to M97 as a data point, not as a
counter-example.

### 14.6 Verdict

**Not contaminated, for a structural reason rather than a lucky one.** No number in §12,
§12.1 or §13 came from a renderer invocation. The coefficients inherited from the parent
milestone are exposed and are named as such; the unit is unwired, so nothing downstream
consumes them yet.

---

## 15. Wiring: the design answer, and why I did not wire it

Asked whether the lateral-CA correction is ready to go default-on, where it belongs in the
order of operations, and how to handle the teleconverter.

### 15.1 (1) Transferable? **NOT ESTABLISHED. It ships behind a flag.**

I do not have to reason about this: **L4 is exactly that experiment and it split.**

| fit on | applied to | removed | frac of in-sample | vs 0.60 bar |
|---|---|---|---|---|
| `tweezers-cpl` (n=12) | `bee-3-cpl` (n=8) | 91.2 % | **0.950** | PASS |
| `bee-3-cpl` (n=8) | `tweezers-cpl` (n=12) | 53.3 % | **0.541** | **FAIL** |

Neither direction makes anything *worse*, so lateral CA does behave like an optical term
rather than a scene property — the orchestrator's expectation is supported in the
well-fitted direction. But the reverse direction misses the registered bar, and the
asymmetry tracks the fit sets: **8 ROIs predict 12 much worse than 12 predict 8.** The
honest reading is *"lateral CA transfers; 8 ROIs are not enough to fit a transferable
profile"*, and fact 52 is not dismissed by that.

Both stacks are also the **same optical configuration**. This says nothing about a second
configuration, which is the thing that would actually establish a *profile*.

**So: flag-gated, and it stays flag-gated until someone measures a second configuration.**
Default-on would be a regression risk taken on a coefficient whose transfer is measured to
be uneven.

### 15.2 (3) The teleconverter — the gate refuses to guess

The shipped profile **was measured with the 2x Viltrox teleconverter fitted**; the record
names it and `optics.rs` says "remove it and this record does not describe the path". So the
hazard is the mirror of the one stated: applying it when the TC is **off**.

There is no way to detect that from the frames. So the gate **requires the operator to name
the optical path** and refuses anything else:

```text
STREHL_FIX_CA unset / "" / "0" / "off"    -> Ok(None)        silent no-op
STREHL_FIX_CA "a7c2-fe100gm-2xtc-x4cpl"   -> Ok(Some(..))    radial term only
STREHL_FIX_CA "1" / "true" / "on"         -> Err(..)         refuses to guess
STREHL_FIX_CA "a7c2-fe100gm-2xtc"         -> Err(..)         refuses to be silently off
```

**`1`/`true`/`on` are rejected deliberately.** They are the natural thing to type and they
are precisely the request the function cannot honour, because "yes, correct CA" does not say
*which lens*. A typo is an **error**, not absence, because a silently-disabled correction is
indistinguishable from a correction that does not work.

`profile_from_setting` takes the value as an **argument**, not from the environment, so it
is testable without mutating global process state from parallel test threads.

It also resolves to `A7C2_FE100GM_2XTC_X4CPL_RADIAL` — **translation zeroed**, per §12.1,
where the fitted translation left 17.3 ppm against 0.6 ppm for the radial term alone. The
measured translation stays in the record as provenance;
`the_two_profiles_differ_only_in_translation` pins the pair so they cannot drift.

### 15.3 (2) Order of operations — **and the finding that blocks the cheap wiring**

The good half first. **L6 says the correction composes into the alignment `Similarity`
exactly** — worst relative error `<= 1e-12` over 20 000 randomised transforms — so per
gather it costs **no second kernel application**. And `gather_checked` calls
`t.apply_at(px, py, cx, cy)` with `cx, cy = width*0.5, height*0.5`, and
`align.rs:290-293` defines `apply_at(x,y,cx,cy) = apply(p - c) + c`. **The gather already
centres the transform**, which independently retires the centre-relative precondition I
recorded as a gap in §13.3. The composition algebra lands exactly:
`s*a*(p-c) + s*b + t + c`.

**Now the blocker.** `gather_checked` takes **one plane, one `Similarity`, and no channel
argument**, and the production planes are **CFA mosaics, not separated channel planes** —
`align_cmd.rs:1421-1426` walks them as 2x2 quads (`2*py + dy`, `2*px + dx`, `f.stride`).

Lateral CA needs **three different transforms**, one per channel. You cannot apply a
per-channel radial scale to an interleaved Bayer plane in a single gather. **So the
correction composes exactly into a `Similarity`, but it does not compose into the gather
that actually runs.** That is the real answer to (2), and it is not the answer I expected
when I wrote L6.

Two ways out, and they are not equal:

- **(a) Gather per channel.** Split to per-channel subplanes and gather each with its own
  composed transform. **Each output sample is still resampled exactly once**, so this costs
  no sharpness — the cost is wall clock and a real change to the gather's shape. Sampling a
  half-density subplane is a *different* interpolation from sampling the mosaic, so this is
  a design change that needs its own measurement, not a patch.
- **(b) Correct after demosaic.** A second, independent resampling pass. **Reject.** Facts
  1373-1374 price a kernel application at −0.2360 dex and fact 1287 attributes 64.2 % of the
  merge's sharpness deficit to the coverage rescale. Spending a second kernel to remove
  ~3 px of red fringing is exactly the trade the orchestrator asked me to watch for, and it
  is the losing side of it.

**Recommendation: (a), scheduled as its own milestone with its own before/after, not folded
into someone else's commit tonight.**

### 15.4 Why there is no patch attached

My lane is `optics.rs` and `color.rs`. **`color.rs` is purely colorimetric — it contains no
geometry at all**, so it is not a seam for this. The gather is `warpmap.rs::gather_checked`,
called from `align_cmd.rs` (M112's, dispatched an hour ago) and the merge path
(`merge_cmd.rs`, M97's). **Every candidate site is in someone else's lane, and the change
that is actually needed is (a), which is a design change to the gather rather than a
two-line call-site swap.**

So I have put **all the policy in my lane** instead, so that whoever does wire it writes as
little as possible in a contended file:

```rust
// at the call site, once the gather is per-channel:
let profile = strehl_core::optics::profile_from_setting(
    std::env::var("STREHL_FIX_CA").ok().as_deref(),
)?;                                    // Ok(None) when unset -- silent no-op
let t_chan = strehl_core::optics::OpticalProfile::compose(profile, channel, t);
```

Two lines, no arithmetic, no convention to get wrong, and `Ok(None)` is a bitwise no-op
(bar L1: 12 012 cases, 0 differing bits).

**Caveat I will not paper over:** I established the mosaic-plane claim from CFA quad
indexing in a *statistic* function in `align_cmd.rs`, and from `gather_checked`'s signature.
I did **not** read the merge's own gather, because `merge_cmd.rs` is M97's and currently
dirty. **If the merge already gathers per-channel planes, then (a) is already done and the
two lines above are the whole wiring.** That is a five-minute check for whoever owns that
file, and it is the single thing that decides whether this is a patch or a milestone.

### Candidate facts

- **P27. RETRACTED — see §16 and P29. The claim below is false.** ~~The lateral-CA correction
  **cannot compose into the production gather as it stands**: `gather_checked` takes one plane
  and one `Similarity` with no channel argument, and the planes are CFA mosaics
  (`align_cmd.rs:1421-1426` walks 2x2 quads). A per-channel radial scale needs three
  transforms, so it requires a per-channel gather — which costs no sharpness, because each
  sample is still resampled once, but is a design change rather than a call-site swap.~~
  The premise "the planes are CFA mosaics" was inferred from a **statistics** loop and is
  wrong: the production gather is `warp_frame_in_place`, which already deinterleaves the
  mosaic and calls `gather_checked` **once per CFA site** on a half-resolution plane. The
  per-channel gather this fact said was missing **already exists**. Retracted within the hour,
  by reading the function P27 itself flagged as unread.
- **P28.** `gather_checked` applies its transform about the plane centre
  (`apply_at(px,py,cx,cy)`, `align.rs:290-293` = `apply(p-c)+c`), so `optics::compose`'s
  centre-relative precondition is satisfied by its intended consumer and the §13.3 hazard
  does not arise. MEASURED.

### Disciplines

- **D15.** "It composes exactly" is a claim about the *algebra*, not about the *pipeline*.
  L6 proved the correction folds into a `Similarity` to 1e-12 and was still not enough to
  wire it, because the gather that consumes `Similarity` handles one interleaved plane and
  the correction needs three. **Check the consumer's signature before pricing a change as
  free.**
- **D16.** Put the policy — defaults, gating, refusal — in the lane you own, so the patch
  someone else has to apply to a contended file is two lines with no arithmetic in them.

---

## 16. P27 was wrong: the per-channel gather already exists

§15 shipped the gate and then told the orchestrator that composing the correction into
the production gather was blocked, because `gather_checked` takes one plane and one
`Similarity` with no channel argument. I registered that as P27 and I flagged, in the
fact itself, that I had **not read the merge's own gather**. That caveat was the whole
result. When I read it, P27 fell over.

### 16.1 What the production gather actually does

`align_cmd.rs:1232-1289`, `warp_frame_in_place`, is the function `merge_cmd.rs:968`
calls once per frame. Its body is:

```rust
for dy in 0..2usize {
    for dx in 0..2usize {
        // deinterleave CFA site (dx,dy) -> scratch.src, at half-res `geom`
        let src = PlaneRef::from_geometry(&scratch.src, geom)?;
        covered_total += strehl_core::warpmap::gather_checked(
            src, t, geom, resampler, &mut scratch.dst, &mut scratch.cover)?;
        // re-interleave scratch.dst -> frame.data
    }
}
```

**It already gathers each of the four CFA sites separately.** The mosaic is
deinterleaved into a half-resolution plane per site, gathered, and written back. Four
`gather_checked` calls happen per frame today. The only thing shared across them is the
transform `t`.

So the per-channel gather that P27 said was a design change is **the design already in
the tree**. What is missing is not a gather — it is a per-site *transform*.

### 16.2 How I got it wrong

P27's premise was "the planes are CFA mosaics", cited to `align_cmd.rs:1421-1426`, which
walks `2*py+dy, 2*px+dx` over `f.stride`. That code does walk a full-resolution mosaic —
but it is a **statistics** pass, not the gather. I read a quad-walking loop, recognised
the mosaic access pattern, and generalised it to a function 190 lines earlier that I had
not opened. The two loops look almost identical; one of them is the resample and one of
them is not.

The corpus already has the general form of this — §14 says do not report an inference in
the register a measurement lives in — and P27 is a repeat offence committed in the same
report. What limited the damage was **not** judgement: it was that I wrote the boundary
of my own evidence into the fact ("merge's own gather NOT read"), which made the fact
cheap to falsify and pointed at the file that falsified it.

### 16.3 The wiring, corrected — and the blast radius

Because the loop already exists, the patch to `align_cmd.rs` (M112's lane) is one line
inside it plus a hoisted lookup:

```rust
// hoisted above the dy/dx loops:
let ca = strehl_core::optics::profile_from_setting(
    std::env::var("STREHL_FIX_CA").ok().as_deref(),
)?;

// replacing `t` in the gather_checked call:
let t_site = strehl_core::optics::OpticalProfile::compose(
    ca, strehl_core::optics::cfa_site_channel(dx, dy), t);
```

`cfa_site_channel` is new, in my lane, and exists so that no arithmetic lands in a file I
do not own. For RGGB it maps `(0,0)` to red, `(1,1)` to blue, and both greens to green.

The blast radius is the part worth stating precisely, and it is now a test
(`the_cfa_site_map_touches_only_the_red_gather`, 286 passing):

| CFA site | channel | coefficient | gather |
|---|---|---|---|
| `(0,0)` | red | `eps_r = -704.5 ppm` | **changes** |
| `(1,0)` | green | none by construction | bitwise identical |
| `(0,1)` | green | none by construction | bitwise identical |
| `(1,1)` | blue | `eps_b = None`, never measured | bitwise identical |

**One of four gathers moves.** With the gate off, all four are bitwise identical to today
(bar L1). This is a much smaller change than §15 priced.

### 16.4 The consequences for the kernel result

The orchestrator's upgrade said the unwired correction is the blocker on a `-0.2360` dex
sharpness win that is also 1.5x faster, and asked whether composing rather than adding a
gather was possible. The answer is stronger than "possible":

- **It costs no additional resample.** Not "one resample instead of two" — the four
  gathers already happen, and three of them do not change. Each sample is still
  interpolated exactly once, by the same kernel, into the same buffer.
- **It rides whatever kernel is selected.** The correction is inside `t`, so a `nearest`
  arm gets a CA-corrected `nearest` gather with no extra low-pass. That is precisely the
  combination the kernel milestone could not test.
- **It is not a chroma suppressor.** It moves the red plane's sampling grid by a radial
  scale and touches nothing else, so it cannot reduce edge chroma on a scene whose edges
  are genuinely coloured. That matters for the two-sided validation the orchestrator
  registered: it is structurally incapable of pulling `marker` below its 2.23x control by
  suppression, because it has no term that can.

One limit, stated rather than buried: **`eps_b` is `None`.** Blue is unmeasured, so the
blue gather is unchanged by construction and **cyan fringing is untouched**. The
`leaf-2-cpl` cyan fringe from the parent milestone's observation is **not** addressed by
this correction. Anyone validating should expect movement on magenta/orange and none on
cyan, and should treat a cyan improvement as evidence of something other than this patch.

### Candidate facts

- **P29.** The production gather **already runs per CFA site**: `warp_frame_in_place`
  (`align_cmd.rs:1253-1287`) deinterleaves the mosaic and calls `gather_checked` four
  times per frame on half-resolution planes, sharing only the transform. Wiring lateral-CA
  correction is therefore a per-site *transform*, not a per-channel *gather*: one line in
  an existing loop, **no additional resample**, and with the shipped profile exactly **one
  of the four gathers changes** (red). MEASURED (code read; test
  `the_cfa_site_map_touches_only_the_red_gather`). **Supersedes and retracts P27.**
- **P30.** The correction is structurally incapable of acting as a global chroma
  suppressor: its only term is a radial scale on the red sampling grid, so it cannot
  reduce edge chroma on genuinely coloured edges. It therefore satisfies the
  orchestrator's two-sided validation by construction on the `marker` side, and the test
  that matters is whether it moves `lavendar`. MEASURED (by construction from the shipped
  coefficient set).

### Disciplines

- **D17.** When a fact's own text says "I did not read X", that is not a caveat, it is a
  to-do with a deadline. **Read X before anyone acts on the fact** — P27 survived nine
  minutes and would have cost a milestone-sized design detour if it had survived longer.
- **D18.** Two loops over the same index pattern can be a resample and a statistic. **An
  access pattern does not identify a function.** Cite the function that runs in
  production, not the one that looks like it.
- **D19.** Writing the boundary of your evidence into a fact is what makes it cheap to
  kill. P27 was wrong, but it was wrong in a way that named its own refutation site — that
  is the difference between an error that costs an hour and one that costs a week.

---

## 17. The radial support of the fit: UNDECIDABLE beyond r = 0.79

The orchestrator asked a question about **support**, not goodness of fit: lateral CA is
zero at the optical centre by construction and grows with field height, so a radial
coefficient is most load-bearing exactly where a macro subject usually has nothing in
frame. A high `R^2` over a narrow radial band is entirely consistent with an
unconstrained extrapolation into the corners. `R6` (`r6_support.py`) answers it from my
own data, without reading M109's files or re-deriving its result.

Bars S0–S5 were registered in the script's docstring before the run, including the
expectation that **S2 would fail**.

### 17.1 The answer

| question | answer |
|---|---|
| fitted on | `tweezers-cpl` (12 ROIs) + `bee-3-cpl` (8), 20 gated total |
| radial span | `r = 0.208 .. 0.788`, median `0.584` |
| annuli populated | **6 of 10** — counts 3, 1, 1, 7, 4, 4 over `r = 0.20..0.80` |
| annuli empty | `0.00-0.20` and **`0.80-1.00`** |
| `r_max` | **0.788**, against a registered bar of `0.85` |
| verdict | **UNDECIDABLE BEYOND r = 0.79** |

So the orchestrator's instinct was right, and the honest form is the one it named. But
the finding is **milder than M109's**, and the difference matters:

- **The coefficient itself is well constrained.** Six populated annuli spanning a
  **3.8x lever arm in r** is real radial structure, not a two-bin artifact. Nothing here
  resembles a 2-bin Spearman reading `+1.0000` on a null. `eps_r` is supported over
  `[0.21, 0.79]`.
- **What is unsupported is the last 21% of the field.** For a pure radial magnification
  `d = eps*r`, displacement is linear, so the corner is the outermost measured point
  scaled by `1/0.788 = 1.27x`.

### 17.2 Question 3, answered numerically

*"Does the correction's magnitude at the corners come from measured points, or from the
model's shape?"*

With `eps_r = -704.5 ppm` and a half-diagonal of `4225.7` sensels:

| field height | red displacement | provenance |
|---|---|---|
| `r = 0.788` (outermost measured) | `2.35` sensels | **measured** |
| `r = 1.000` (corner) | `2.98` sensels | `2.35` measured + `0.63` extrapolated |

**About 79% of the corner correction sits at or below a measured radius; about 21% —
0.63 sensel — comes from the model's shape alone.** That is the number, and it is a
weaker claim than "3 output pixels at the corner" implies.

### 17.3 What is shipped as a result

`OpticalProfile` gains `support_r_max: Option<f64>`, set to `Some(0.788)` on both shipped
records, with the empty outer annuli and the 1.27x factor documented on the field.
`the_shipped_profiles_declare_a_support_radius_short_of_the_corner` locks it: a profile
that ships without declaring support, or that claims support to `r = 1.0`, fails.

**Nothing clamps to this radius.** The field is declared, not enforced. Clamping is a
behavioural change that has not been validated on a render, and inventing one tonight
would be the same mistake as the sign inversion in §12 — a convention rewritten under
time pressure with no measurement behind it. The declaration is what lets a consumer
decide; it is deliberately not a silent policy.

### 17.4 The instrument defect this run contained, and what caught it

The first version of `r6_support.py` normalised by `hypot(3516, 2344)/2` — the half
diagonal of the half-resolution **CFA plane**. It reported `r_max = 1.575` and printed
**`VERDICT: SUPPORT ADEQUATE`**.

That verdict was false, and it was false in the flattering direction. A normalised field
height above `1.0` is geometrically impossible: no point in the frame is further from the
centre than the half diagonal. `rx`,`ry` are centre-relative **full-resolution sensel**
coordinates (`common.py:17`), so the normaliser was 2x too small and every radius was
inflated by 2x — which pushed the outermost ROI clean past the corner and made a starved
support look complete.

**I did not notice from the verdict.** What flagged it was S5, a control I had written to
check something else entirely — whether the binning reported where the data is. It failed,
I looked at why, and the impossible `r_max` was sitting in the output I had already read
past. The lesson is not "check your units"; it is that **a control aimed at the wrong
question still catches an instrument that is wrong**, which is an argument for running
controls that are cheap rather than only the ones that seem pointed.

The rewritten S5 is a proper two-sided pair: a positive control (radii uniform over
`[0,1]`, `r_max = 0.902`) proving the statistic can say *adequate*, and a negative control
(radii confined to `[0.20,0.40]`, `r_max = 0.394`) proving it can say *starved*. Both pass,
so S2's FAIL on the real data is a statement about the data. S0 now asserts the geometry
directly so this specific defect cannot recur silently.

This did **not** touch `eps_r`. The fit solves `d = eps*(r.n)` with `d` and `r` both in
sensels, so `eps` is dimensionless and unaffected by the normaliser. Only the support
statistic was wrong.

One unrelated defect spotted and **not** fixed, because it is the parent milestone's
file and it is a reporting line rather than a coefficient: `e10_transfer.py:44` sets
`PLANE_W, PLANE_H = 3516, 2344` and then reports the fitted centre offset as a
percentage of that half-diagonal at line 118. If the centre is in sensels — and `rx`,`ry`
are — that percentage is **2x too large**. Flagged for whoever owns it.

### 17.5 What would fix the support

The capture already requested in `docs/captures-needed.md` §24 is the right one, and I
can now say exactly why in terms of this measurement: the fit needs **populated annuli in
`r = 0.80..1.00`**, which is precisely what a flat, square-on target with fine detail
reaching the corners supplies and what a macro subject in a band never will. Two
additions worth making explicit:

1. **Both annuli, not just the outermost.** `0.80-0.90` and `0.90-1.00` are both empty.
   A target that only resolves in the extreme corner leaves a gap.
2. **The blue channel.** `eps_b` is `None` and every ROI here was fitted on red. The same
   capture supplies blue at no extra cost, and without it cyan fringing stays untouched
   by construction (§16.4).

### Candidate facts

- **P31.** The `-704.5 ppm` lateral-CA fit has radial support `r = 0.208..0.788` over 20
  gated ROIs, six of ten annuli populated, **outer two annuli empty**. The coefficient is
  well constrained over that band (3.8x lever arm) but the corner is a **1.27x linear
  extrapolation**: `2.35` of the corner's `2.98` sensels are at-or-below a measured
  radius and **0.63 sensel (21%) comes from the model's shape alone**. The honest form is
  **UNDECIDABLE beyond r = 0.79**. MEASURED (`r6_support.py`, bars S0–S5 registered
  before the run, two-sided instrument controls pass).
- **P32.** A support statistic normalised by the half-resolution **plane** diagonal
  instead of the full-resolution **sensel** diagonal inflates every field height by 2x and
  reported `r_max = 1.575` with the verdict `SUPPORT ADEQUATE` — a geometrically
  impossible radius that read as the flattering answer. Caught by a control written for a
  different question, not by the verdict line. MEASURED (first run of `r6_support.py`).

### Disciplines

- **D20.** A goodness-of-fit statistic and a support statistic answer different
  questions, and only one of them constrains an extrapolation. **Report the per-annulus
  population next to any `R^2` on a radial model** — `R^2 = 0.9969` and "the outer two
  annuli are empty" are both true here.
- **D21.** **A normalised coordinate has a legal range, so assert it.** `r > 1.0` is
  impossible and was sitting in the output above a verdict I believed. Range guards on
  derived quantities are cheaper than the wrong answer and they fail loudly.
- **D22.** Run the cheap control even when it is aimed at the wrong question. S5 was
  written to check the binning and instead caught a 2x unit error; a control that is
  cheap enough to run without a hypothesis will sometimes catch the thing you had no
  hypothesis about.
- **D23.** When support is short of where a model is load-bearing, **declare the valid
  domain in the shipped record and lock it with a test** rather than clamping. A
  declaration lets a consumer decide; an unvalidated clamp is a new behaviour introduced
  at the moment of least evidence.

---

## 18. Wiring the correction to a rendered pixel

Fact 1449 was correct and damning: 287 passing tests, zero consumers. `STREHL_FIX_CA`
set a variable nothing read. This section wires it, and every number below is from a real
299-frame render of `bee-3-cpl`.

### 18.1 The one file I took outside my lane, and why

**There is no in-lane path to a rendered pixel.** I checked all three candidates:

- `warpmap.rs:487 gather_frame` is a thin wrapper over `gather_checked` — still one plane,
  still no channel, and **the merge does not call it**.
- `gather_checked` cannot resolve the channel itself: it receives one plane and one
  `Similarity` and has no way to know which CFA site it is looking at.
- The merge's actual path is `merge_cmd.rs:968` -> `align_cmd::warp_frame_in_place`, and
  `merge_cmd.rs` is M97's and forbidden.

So the change had to land in **`crates/strehl-cli/src/align_cmd.rs`**, which was not on my
permitted list. I took it, and here is the reasoning I would want challenged:

- The orchestrator granted "whatever minimal CLI surface the switch needs" and forbade
  `merge_cmd.rs` and `align.rs` by name. `align_cmd.rs` was named in neither.
- **`git status` showed `align_cmd.rs` clean.** No agent had uncommitted work in it, so a
  path-scoped commit of that one file could not destroy anyone's work. The dirty files in
  `crates/` were all M97's (`merge_cmd.rs`, `robust.rs`, two examples) and I touched none.
- The change is **two statements** and does not alter any signature, which is what keeps
  `merge_cmd.rs` untouched.

If that was the wrong call, it reverts cleanly and independently.

### 18.2 What was added

In `optics.rs` (my lane): `CA_ENV` (the env-var name, so the string exists once),
`active_profile()` (reads it and returns `Result`), and `impl std::error::Error for
CaConfigError` so the CLI can `?` it.

`active_profile()` is deliberately **not** a cached `OnceLock`: the cost is one `getenv`
per frame against a four-plane gather, and a cache would make the switch untestable
within a process and would silently ignore a change between stacks.

In `align_cmd.rs`, inside the loop that already exists (§16):

```rust
let ca = strehl_core::optics::active_profile()?;          // hoisted, once per frame
...
let t_site = strehl_core::optics::OpticalProfile::compose(
    ca, strehl_core::optics::cfa_site_channel(dx, dy), t);
```

The orchestrator's reading of the geometry was right in the way that matters and slightly
off in the letter: frames are **not** carried as four planes — `warp_frame_in_place`
deinterleaves an interleaved mosaic into a half-resolution scratch plane per site. But the
consequence is exactly as described: **each plane presented to the gather is a single CFA
site**, so the channel is known from `(dx,dy)` and there is **no per-pixel branching**.
One composed `Similarity` per plane, alignment and CA correction in the same gather, no
second resample. (The plane-vs-sensel error in §17.4 was in an experiment script's
normaliser and is unrelated to this.)

### 18.3 The switch

```
STREHL_FIX_CA=a7c2-fe100gm-2xtc-x4cpl
```

Measured behaviour of every form, one render each:

| `STREHL_FIX_CA` | exit | result |
|---|---|---|
| unset | 0 | default path |
| `0` | 0 | byte-identical to unset |
| `off` | 0 | byte-identical to unset |
| `a7c2-fe100gm-2xtc-x4cpl` | 0 | correction applied |
| `a7c2-fe100gm-2xtc-x4cpl-TYPO` | **1** | `Error: unknown lateral-CA profile ...; known profiles: a7c2-fe100gm-2xtc-x4cpl` |

`1`/`true`/`on` are still refused, for the reason in §15: they cannot say *which lens*, and
the wrong profile **adds** red fringing.

### 18.4 The null, which is stronger than the one I was asked for

I was asked for a byte-identical null on a real stack. What the run produced is a
**cross-binary** null:

```
wired binary, CA off : E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112
pre-wiring binary    : E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112
```

The second file is `C:\dev\strehl-out\ORCH-kernel\bee-3-cpl-catmull-rom.tif`, rendered
earlier tonight by a **different binary at a different commit**. Full SHA-256 equality.
The default path did not move a single byte across the wiring, a rebuild and an
intervening commit — a much better guarantee than an A/A inside one binary, which could
not have detected a rebuild-induced change.

Bars N1–N4 (registered in `r7_wiring_ab.ps1` before the run) all pass: `off1 == off2`,
`unset == 0 == off`, `on != off`, typo arm exits **exactly 1**.

### 18.5 The cache key — answering loudly, as asked

**`STREHL_FIX_CA` is NOT in `StackIdentity`.** The struct is
`{ name, digest, frames }` (`warpmap.rs:194-201`), where `digest` is FNV-1a over
`(file name, file size)` per frame. It covers the frame set and nothing else — not
`reference`, not `resampler`, and not the CA setting.

**But it does not corrupt this A/B, and the reason is structural rather than lucky.**
`StackIdentity` guards the **warpmap sidecar**, which stores *placements*. The CA
correction is applied at **gather time**, downstream of the sidecar, so a sidecar cache
hit still re-gathers every pixel. That is why I solved **one** sidecar and reused it
across all five arms: `reference` and the solve are held fixed by construction, and the
only free variable is the env var.

The empirical confirmation is in the hashes: with an identical command line and an
identical sidecar, `off` and `on` differ, and `off` reproduces exactly across
non-adjacent runs with the `on` arm in between. **If the CA setting were being folded into
a cached artefact, `off2` would have returned the `on` bytes. It did not.**

Caveat for whoever drives the sheet: because the switch is an env var and not argv, **it
will not appear in a recorded command line.** A harness that logs argv only will record
two arms that look identical. Log the environment or wrap the switch in a flag.

### 18.6 The by-eye read, which is the answer to the question I was actually asked

Crops at 1:1, no post-processing, window chosen automatically at the highest
edge-chroma density (`r = 0.651`), written to
`C:\dev\strehl-out\M107-chroma\r7\crop_off_vs_on.png`.

**It is visibly better, and by more than I expected.** In the CA-off arm the spicules
against the bright background carry vivid cyan-blue fringing along one side and warm
orange along the other; several hairs at the bottom of the window are outlined in cyan.
In the CA-on arm those cyan outlines are largely gone and the hairs read as neutral dark
brown. Some warm edges remain.

**And this corrects an expectation in the brief.** I was asked to expect "at most a partial
fix" because `eps_b` is `None` and the fringes are red/cyan pairs. That reasoning does not
hold, and the render shows why: **a red/cyan fringe pair *is* red misregistration.** Cyan
is the absence of red. A radial scale error in red produces a red edge on one side of a
feature and a cyan edge on the other, and correcting red's magnification removes **both
sides at once**. `eps_b = None` is a real limitation, but it bites on **blue/yellow**
fringing, not on the red/cyan pairs M110 and the orchestrator both described.

The metric agrees and — importantly — agrees in the two-sided shape the orchestrator
registered:

| arm | edge chroma | flat chroma | ratio |
|---|---|---|---|
| off | 0.075809 | 0.034028 | 2.228 |
| on | 0.068407 | 0.034015 | 2.011 |
| change | **-9.76%** | **-0.04%** | |

**Edge chroma falls 9.76%; flat chroma moves 0.04%, which is noise.** This is not a global
chroma suppressor — it cannot be, since its only term is a radial scale on red's sampling
grid. That is the discriminator the orchestrator asked for, and it passes.

Per-channel mean `|on - off|` is **R 540 DN, G 50, B 54**: red moved an order of magnitude
more than green or blue, which is what a red-only correction should do, and the residual
G/B movement is downstream demosaic coupling rather than a second correction.

### 18.7 The corner, past the declared support

`support_r_max = 0.788` and the crop set includes a window at **`r = 0.945`**. Honest
answer: **nothing bad happens, and nothing much happens.** The corner of `bee-3-cpl` is
defocused background with one small speck in it, which shifts slightly and shows no
tearing, no colour inversion and no visible artefact.

That is not evidence the extrapolation is safe. It is the support finding restated: this
subject has nothing in its corners to test with, which is precisely why P31 says
UNDECIDABLE beyond `r = 0.79` and why the §24 capture matters. **A corner that looks fine
because it is empty is not a corner that has been checked.**

### Candidate facts

- **P33.** The lateral-CA correction is **wired and reaches rendered pixels**:
  `align_cmd.rs::warp_frame_in_place` composes a per-CFA-site `Similarity` inside the
  four-plane loop that already existed, adding **no second resample** and no per-pixel
  branching. Switch: `STREHL_FIX_CA=a7c2-fe100gm-2xtc-x4cpl`. MEASURED (299-frame
  `bee-3-cpl` render; bars N1-N4 registered before the run, all pass).
- **P34.** The default path is **byte-identical across the wiring**: the wired binary with
  the switch off reproduces a pre-wiring binary's render at a different commit to a full
  SHA-256 match (`E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112`).
  MEASURED (cross-binary, not A/A).
- **P35.** The correction reduces edge chroma **9.76%** while moving flat chroma **-0.04%**
  on `bee-3-cpl`, and is structurally incapable of global chroma suppression. Per-channel
  mean displacement R 540 DN vs G 50 / B 54 confirms only red moved. **Visibly better at
  1:1**: cyan outlines on the spicules largely disappear. MEASURED.
- **P36.** **A red/cyan fringe pair is red misregistration, so `eps_b = None` does not
  halve the fix for it.** Cyan is the absence of red; a radial scale error in red makes a
  red edge on one side and a cyan edge on the other, and correcting red removes both. The
  unmeasured blue coefficient bites on **blue/yellow** fringing instead. MEASURED
  (by eye + the 9.76% edge-chroma fall from a red-only term).
- **P37.** `STREHL_FIX_CA` is **not** in `StackIdentity` (`{name, digest, frames}`,
  `warpmap.rs:194`), but it cannot corrupt an A/B: the correction is applied at gather
  time, downstream of the sidecar the identity guards, so a cache hit still re-gathers.
  Confirmed empirically — `off2` reproduced `off1` exactly with the `on` arm between them.
  **However the switch is an env var, so it does not appear in a recorded argv**, and a
  harness logging command lines alone will record two arms that look identical. MEASURED.

### Disciplines

- **D24.** A cross-binary null beats an A/A null. Rendering the default path with the new
  binary and hashing it against a file produced by the **old** binary tests the rebuild,
  the intervening commits and the wiring at once; an A/A inside one binary tests none of
  them.
- **D25.** **When the on-switch is an environment variable, it is invisible to any harness
  that records argv.** Either promote it to a flag or record the environment; two arms
  that differ only in an unlogged env var are indistinguishable in the record from two
  arms that were never different.
- **D26.** Check `git status` before taking a file outside your lane. "Is anyone editing
  it?" is answerable in one command, and a clean file plus a path-scoped commit makes an
  out-of-lane change reversible instead of destructive.
- **D27.** A colour-fringe pair names its own cause. Red/cyan is the red channel
  misregistered; blue/yellow is blue. Reading the pair before assuming a correction is
  partial would have saved the brief's expectation of "at most a partial fix".
- **D28.** An artefact-free corner in a subject with an empty corner is not evidence.
  Separate "looked and saw nothing wrong" from "there was something there to look at".

## 19. The cache-key answer, and what the fringe measurement actually says

Two deliverables the orchestrator asked for by name. One of them is an answer it
did not expect, and one of them revises a claim I made myself in §18.

### 19.1 The cache key: `STREHL_FIX_CA` must NOT be added to `SOLVE_ENV`

The orchestrator's instruction was: *"Check it, state the answer explicitly, and
if it is not in the key, add it."* It is not in the key. **I am not adding it,
and I believe adding it would be a defect.**

`SOLVE_ENV` is `["STREHL_SMOOTH", "STREHL_SMOOTH_HUBER"]`, and
`solve_config_key` hashes the reference, the spans, the resampler debug string
and each `SOLVE_ENV` variable into the sidecar path. The contract is stated in
its own doc comment: **anything *the solve* reads must be in the key.** So the
question is not "does the render read `STREHL_FIX_CA`" -- it plainly does -- but
**does the solve?**

It does not. `active_profile()` is read at exactly one site,
`warp_frame_in_place` in `align_cmd.rs`. Its callers are:

| caller | what it is |
| --- | --- |
| `merge_cmd.rs:968` | the merge -- the only production consumer |
| `align_cmd.rs:1337/1375/1377/1393/1394` | the W8 gate: tests and a demo |

`solve_map` is not among them. The solve estimates warps from the decoded
frames; it never calls the gather, so no CA setting can change the `WarpMap` it
produces. Adding `CA_ENV` to `SOLVE_ENV` would therefore change the sidecar path
for a variable that provably cannot change the sidecar's contents -- forcing a
full re-solve on every CA toggle, for an identical result.

**The trap the orchestrator described is real but lands on the other side.** Its
fear was that a CA-ON run would silently load a warp map solved with CA OFF and
so measure a null. That is exactly what my A/B did -- one sidecar, solved with
`STREHL_FIX_CA` unset, reused unchanged by all five arms -- and the ON arm still
rendered to a **different hash** (`E9580E8A…` vs `E400A63A…`). A shared,
CA-unaware sidecar is not merely harmless here; **the A/B is only clean because
of it**, since it holds the solve fixed and leaves the gather as the one free
variable. This is the opposite of the resampler defect at facts 1469/1476, where
the resampler *is* read by the solve.

**Caveat I cannot discharge from my lane.** This rests on `warp_frame_in_place`
being the only site that reads `active_profile()`, which is true today because I
wrote both. It is an invariant maintained by nothing but that fact. **The right
guard is a tripwire test asserting `solve_config_key` is invariant to `CA_ENV`
with a comment naming the reason**, so that whoever later makes the solve
CA-aware is forced to update `SOLVE_ENV`. I have not added it: `align_cmd.rs`
was handed to M109 and re-taking it to add a test would re-block a running
agent. It is a one-function patch and I recommend it be routed.

### 19.2 R9/R9b: better where it matters, with a cost where it does not

§18 reported my by-eye read as *"better, not merely different"*. That read was
made at 1:1 on the spicule crops and I stand by what it describes, but it was an
eye on the strong fringes only. **The aggregate does not support the confidence I
attached to it, and I am revising it down.**

I registered four bars (`r9_fringe_width.py`) before measuring, on the same
299-frame `bee-3-cpl` arms. Edge mask taken from the **off** arm only, so both
arms are scored on identical pixels; chroma threshold absolute and identical, so
the statistic measures extent rather than amplitude.

| bar | off | on | change |
| --- | --- | --- | --- |
| W1 fringe area (px over threshold, ≤3px from an edge) | 823 393 | 739 383 | **−10.20%** |
| W2 chroma-weighted width | 1.3752 px | 1.4233 px | **+3.50%** |
| W3 mean \|R−Y\| near edges | 0.041477 | 0.032909 | **−20.66%** |
| W4 control: mean \|B−Y\| (no coefficient) | 0.060045 | 0.058624 | −2.37% |

**W3's registered bar was ">90% of falling pixels keep their sign". It failed at
75.1%**, with a 25.14% sign-flip rate, and the script's own pre-registered
verdict line printed `RECOLOURED, NOT REMOVED`. I report that as it stands.

R9b then asked the one question that bar cannot answer: *where* do the flips
happen? Its Q1 bar also failed (flipped pixels started at 0.0226 vs preserved at
0.0379, a ratio of 1.67× against a bar of 2×). But the decile decomposition is
unambiguous and monotone:

| decile of \|R−Y\|_off | mean change | flip rate |
| --- | --- | --- |
| 1 (0.00000–0.00632) | **+583%** | 44.7% |
| 4 (0.01934–0.02634) | +15% | 26.8% |
| 5 (0.02634–0.03392) | −3.5% | 23.9% |
| 7 (0.04253–0.05274) | −24% | 19.4% |
| 10 (0.08638–0.38582) | **−54.08%** | 14.1% |

**The correction removes fringes and adds faint chroma to near-neutral pixels.**
Where there is an actual fringe -- the top decile, `|R−Y| ≥ 0.086` -- the
deviation falls by **54%** and only 14% of pixels flip sign. Where there was
essentially no chroma to begin with, a sub-pixel red shift on textured detail
manufactures a little. That is the honest cost of moving one channel and it is
not an artifact of the metric.

It also explains W2. The +3.50% "widening" is a **selection effect on a shrinking
set**: as the strongest, closest-to-edge fringe pixels drop below the absolute
threshold, the mean distance of the survivors rises. W2 conditions on a
population W1 has just changed, so it cannot be read as a widening. **That is a
defect in my own bar, not a finding** -- W2 should have been computed on a fixed
pixel set, and I did not see it until the decile profile forced the question.

W4 bounds the instrument usefully: blue has no coefficient, and moved −2.37%
against red's −20.66%, an order of magnitude smaller. The effect is red-specific,
as the mechanism requires.

**So the answer to "better, worse, or merely different" is: better, and not
merely different -- but the aggregate improvement (−20.7%) is roughly a third of
the improvement at the fringes themselves (−54%), because the near-neutral
population moves the other way.** A comparison sheet cropped to high-contrast
edges will overstate the correction; a whole-frame chroma average will understate
it. Both numbers should travel together.

### 19.3 `HEAD` builds

Per fact 1475, checked against the commit and not the working tree, in an
isolated `git worktree` at `93f10a5` so that no agent's uncommitted files
participate:

```
cargo check --workspace --all-targets   ->  EXIT=0
```

## 20. R10 -- the right instrument, and what it says about the over-correction

The orchestrator retracted the √2 steer, told me not to spend hours hunting a
normalisation bug, and named the instrument my §19 bar should have been: the
**signed** residual inter-channel radial displacement. I built it
(`r10_radial_residual.py`, bars T1–T4 registered before the run) and ran it on
the two renders I already had. It confirms the direction independently, brackets
the magnitude, validates the wiring end-to-end, and fails one of my own bars in
a way that turned out to be the most useful result of the four.

### 20.1 The model and the bars

If the correction applies `k×` the true displacement `D`, the residual is
`(1−k)·D`, so `ratio = residual_on / residual_off = 1 − k`. Under-correction
gives a positive ratio, over-correction a negative one. Unlike a keep-sign test,
this cannot confuse "does nothing" with "overshoots past zero".

Estimator: per 64 px window, a 1-D Lucas–Kanade along a chosen unit vector,
`shift = Σ(g_u·(R−G)) / Σ(g_u²)`, with R and G standardised within the window so
cross-channel intensity differences do not bias the match. 7 957 windows.

### 20.2 Results

| bar | result |
| --- | --- |
| **T1** lateral CA present in the off arm | **PASS** — radial displacement grows with r, through-origin slope **+1.424 px per unit r** |
| **T2** signed ratio, support-restricted | **OVER-CORRECTED CONFIRMED** — ratio **−0.3738**, implied **k = 1.374** |
| **T3** tangential null | **PASS** — applied tangential is **5.2%** of applied radial |
| **T4** applied correction linear in r | **registered FAIL**, R² = −0.590 — see 20.4 |

**T3 is the control that makes T1 and T2 mean something.** A magnification error
cannot displace anything tangentially, and the estimator confirms it did not:
applied radial −1.1196 px, applied tangential −0.0582 px. So this is not a
generic misregistration the estimator would have reported whatever I did.

### 20.3 Three of my statistics bracket k, and I cannot exclude √2

| route | k |
| --- | --- |
| T2, window-weighted over support | **1.374** |
| per-annulus mean, r ≤ 0.6 | 1.383 ± 0.061 |
| per-annulus mean, all r | 1.397 ± 0.057 |
| §19 W3 top-decile chroma, back-solved | **1.459** |
| orchestrator's median / M111 support-restricted mean | 1.444 / 1.456 |

The §19 cross-check is worth stating explicitly because it is a completely
different statistic — chroma magnitude in the render, not displacement. A 54.08%
fall in top-decile `|R−Y|` back-solves, under an overshoot, to **k = 1.459**,
which lands within 0.2% of M111's support-restricted 1.4562.

**But my per-annulus k spans 1.286 to 1.464, and √2 = 1.41421 sits inside it.**
I therefore **cannot exclude √2 from this scene**, and I record that as a
disagreement with M111's support-restricted CI rather than resolving it. Both of
us are on `bee-3-cpl`; a single scene measured two ways is not two scenes. **The
direction is certain; the magnitude is `k ∈ [1.37, 1.46]` and no tighter.**

### 20.4 T4's failure is the instrument, and the off arm proves it

The registered bar wanted the applied displacement proportional to `r`, because
that is what a magnification error is. R² came back **−0.590** — worse than a
constant. Read naively that says the model shape is wrong.

**It does not, and the off arm is what settles it.** Uncorrected lateral CA
*must* grow monotonically with field height. The off arm does not:

| r | 0.05 | 0.35 | 0.55 | 0.75 | 0.85 |
| --- | --- | --- | --- | --- | --- |
| off / r | +2.948 | +2.261 | **+2.047** | +0.813 | +0.729 |

Displacement-per-unit-r is stable to **cv = 0.122** for r ≤ 0.6 and collapses to
**cv = 0.387** across the full range. Since the physics forbids the off arm's
true signal from falling, the fall is **attenuation bias in the estimator** —
regression dilution where the subject is defocused and `Σg_u²` is small. It is
the same wall as my own P31 (support dies at r = 0.788) and M109's facts
1457/1458, reached from a third direction.

**So T4 does not falsify the magnification model; restricted to where the data
lives, a scalar remains the right shape.** But I report the bar as FAILED as
registered, because it was, and because the honest form of the result is "the
bar failed and here is why the failure is mine, not the model's".

**T2 survives this, and that is a property of ratios.** Attenuation `a(r)` scales
both arms, so it divides out — which is exactly why the per-annulus ratios
(−0.286…−0.464) are far more stable than the displacements they come from. One
caveat in the direction that matters: the on arm has the smaller true residual
and therefore the worse SNR, so if anything it is attenuated *more*, which would
bias my **k = 1.374 low**. That is the direction of the orchestrator's 1.444.

### 20.5 The wiring applies what it claims — an end-to-end check I did not plan

Falling out of the same table: applied displacement over r ≤ 0.6 is **−3.2586 px
per unit r**. With a half-diagonal of `hypot(3516, 2344) = 4225.7` px, that is
**771 ppm** of magnification actually reaching rendered pixels, against a
declared `eps_r = −704.5 ppm` — agreement to **9%**, inside the estimator's
scatter. **The correction that reaches the pixels is the coefficient that is
written in `optics.rs`**, in the right direction and at the right magnitude. That
is independent of whether the coefficient itself is correct, and it is the
cleanest evidence so far that the §18 wiring does what it says.

### 20.6 §19's explanation was two mechanisms where one will do

§19 concluded that the correction "removes fringes and adds faint chroma to
near-neutral pixels", treating the top-decile −54% and the decile-1 +583% as
separate effects. **The overshoot explains both with one mechanism:** an
over-correction leaves an inverted residual proportional to `r` everywhere, which
simultaneously shrinks strong fringes and manufactures chroma where there was
none. I prefer the orchestrator's account to my own and am adopting it.

That also supplies the missing piece of why W3 was the wrong bar, with a
mechanism rather than just an assertion. Only **14.1%** of top-decile pixels
flipped sign, which looks incompatible with an inversion — until you notice that
`R−Y` on a yellow-and-orange bee is dominated by **the subject's own colour**,
not by the fringe. **W3's sign test was largely measuring subject hue.** A
keep-sign bar is not merely insensitive to overshoot; on a coloured subject it is
not measuring the fringe at all.

### 20.7 What I did not do

I did not hunt the √2 normalisation bug beyond reading, per the retraction; I did
not change the coefficient; `A7C2_FE100GM_2XTC_X4CPL_RADIAL` is untouched and
`support_r_max = Some(0.788)` remains declared-but-unenforced. No `optics.rs`
change is proposed here — one scene is not a mandate to re-scale a coefficient.

## 21. The application path is clean. My own number is withdrawn.

The orchestrator proposed that `eps_r` is right and the code applying it scales
it wrong, and offered four candidates. I own the file, so I read it, and then I
turned the same scepticism on my own instrument. **The application path is
clean. My `k = 1.374` is not, and I am withdrawing it.**

### 21.1 All four candidates are excluded, three of them structurally

`compose` (`optics.rs:277`) is:

```rust
let s = 1.0 + eps;
```

**A pure Similarity scale about the coordinate origin. There is no radius
normalisation anywhere in the apply path** — no half-diagonal, no field height,
no `r` at all. `support_r_max` is declared metadata (`:156`) that nothing reads.

| candidate | verdict | why |
| --- | --- | --- |
| 1. normalised-radius convention | **excluded by construction** | the apply path performs no normalisation, so there is no convention to mismatch |
| 2. plane-vs-sensel factor of 2 | **excluded by construction** | a multiplicative scale about the origin is **unit-invariant**: `s·(2z) = 2·(s·z)`. Only the *additive* translation is unit-sensitive, and the shipped `_RADIAL` profile drops translation entirely |
| 3. centre convention `(w-1)/2` vs `w/2` | **excluded** | a half-pixel centre error produces a *uniform offset* of `eps·δ = 0.00035 px`, not a scale error. A wholly non-centre-relative `z` would give ~3 output px of uniform red offset, which R10's T3 (tangential 5.2% of radial) and R11's C4 (3.0% leak) both bound away |
| 4. double application | **excluded** | applying twice gives `(1+eps)² ≈ 1 + 2eps`, a factor of **2.0**, not 1.44 |

**The exact-arithmetic check is already in the suite.** `optics.rs:692` asserts
`compose(...).apply(r) == (1.0 + eps_r) * r` to `1e-9`. The code applies exactly
`eps_r`, no more and no less — that is a closed-form assertion, not an estimate,
and it needs no displacement estimator to stand.

**So the tension the orchestrator identified is real, but it does not resolve
toward an application bug.** Which leaves the instruments.

### 21.2 `r²` is blind to multiplicative bias — there was never a contradiction

> *"A least-squares fit does not overshoot its own training data by 44% while
> reporting a 0.073-sensel residual."*

**It does exactly that if the training data is scaled.** `r²` measures scatter
about a line, and a multiplicatively biased observable is *still perfectly
linear*. A fit to observations that are uniformly 1.44× too large returns
`r² = 0.9969`, a 0.073-sensel residual, and a coefficient 44% too big. The two
statements were never in conflict, and the resolution is that **neither `r²` nor
a permutation `p` can detect a calibration error in the instrument that produced
the data.** Only a planted recovery can.

### 21.3 So I calibrated my own instrument, and it failed

R11 planted a known magnification on red in a real render and asked R10's
estimator to recover it:

| bar | result |
| --- | --- |
| C1 gain on a planted −704.5 ppm | **0.584** |
| C2 gain on a planted +704.5 ppm | **0.299** — 48.9% asymmetry, **FAIL** |
| C3 resample-matched null | **VACUOUS** — see below |
| C4 tangential placebo | **PASS**, 3.0% radial leakage |

**The gain depends on the amplitude.** At the corner the displacement is
`704.5e-6 × 4225.7 = 2.98 px`, and a single-step gradient method is valid only
well below 1 px. R10's estimator was being asked a question outside its domain.

**This has a direction, and it is the opposite of what §20 claimed.** Saturation
attenuates the *larger* displacement more, so the uncorrected arm is suppressed
harder than the corrected one, which **inflates** `k`. §20 argued the bias ran
the other way and was wrong. **`k = 1.374` is withdrawn.** So is §20.5's "723 ppm
applied vs 704.5 declared, 2.6%" — that was a difference of two reads from the
same uncalibrated instrument, and its apparent precision is not earned.

**C3 was vacuous and I should have seen it.** It read a resampler drift of
*exactly* `+0.0 ppm`, which is the tell: an identity `map_coordinates` samples on
the grid knots and returns the input bit-for-bit, so the zero-strength arm never
resampled. That is precisely the failure the orchestrator warned about one
message earlier — *"a strength-zero arm is not a control for a correction that
resamples"* — and I built it anyway while quoting the warning. **C4, the
tangential placebo, is the only valid resample-matched control in either script,
and it is the one the orchestrator specified.**

### 21.4 The iterative replacement failed too, and refused to report

R12 iterates the linearisation so the residual entering it stays small, and gates
itself on four calibration bars before it is permitted to report a `k`. It
diverges:

| planted | recovered | gain |
| --- | --- | --- |
| −352.2 ppm | −696.5 | 1.977 |
| −704.5 ppm | −2790.5 | 3.961 |
| +352.2 ppm | +149.8 | 0.425 |
| +704.5 ppm | +31.0 | 0.044 |

Recovery scales as roughly the **square** of the planted amplitude (4.006× for a
2× plant), which is positive feedback — almost certainly a sign error in the
direction I shift red between iterations. I have not fixed it.

**All four gates failed and the script reported no number**, which is the one
thing that went right: the gate was written before the data and it held.

### 21.5 Where this leaves the scalar

**There is currently no calibrated instrument for lateral CA in this project, and
therefore no defensible value of `k` — mine included.** The argument that killed
my 1.374 is not specific to my code: it applies to any single-step gradient or
correlation estimator asked about ~3 px displacements, and **Instrument A's
`r² = 0.9969` provides no protection against it.**

Concretely: **do not ship 0.692.** Not because it is wrong — I cannot say whether
it is — but because every number it rests on comes from an instrument that has
not recovered a planted displacement. And a fitted scalar that silently
compensates an instrument bias looks identical to a correct one until someone
calibrates the instrument.

**What would settle it**, in order of cost: (1) plant a known magnification and
require recovery within 5% at two amplitudes and both signs, before any estimator
is allowed to produce a ppm; (2) a coarse-to-fine pyramidal estimator, so the
per-level residual is genuinely sub-pixel; (3) M114's fit-scene experiment, which
is the right design but inherits the same doubt unless its instrument passes (1).

No change to `eps_r`, `A7C2_FE100GM_2XTC_X4CPL_RADIAL`, or
`support_r_max = Some(0.788)`. `optics.rs` is untouched by this section.

## 22. The convention question, settled by reading rather than by matching

The orchestrator's enumeration found no simple normalisation ratio inside
[1.4256, 1.4867], withdrew the "match the number" instruction, and replaced it
with the right one: **read the code and determine the convention definitively.**
It then named two candidates its ratio list could not see. Both are settled
below, and neither is present. This supersedes nothing in §21; it closes the two
gaps §21 argued from arithmetic with direct evidence from the source.

### 22.1 Double application: excluded by the call graph

At `e49281f`, across the whole workspace:

| symbol | production sites |
| --- | --- |
| `OpticalProfile::compose` | **exactly one** — `align_cmd.rs:1289` |
| `active_profile()` | `align_cmd.rs:1272` (the application) and `align_cmd.rs:289` (a fail-fast validation that **discards** its result) |

Every other occurrence of `compose` is inside `optics.rs`'s own `#[cfg(test)]`
module. **The aligner does not apply it and the merge does not apply it twice:
there is one call, in one place.**

At that site the structure is:

```rust
let ca = active_profile()?;              // once per frame, outside the plane loop
for dy in 0..2 { for dx in 0..2 {
    let t_site = compose(ca, cfa_site_channel(dx, dy), t);
    gather_checked(src, t_site, geom, resampler, ...)
} }
```

`t_site` is a **local, recomputed from an unmodified `t` on each pass**. It is
not accumulated into `t` and it is not re-composed. One composed `Similarity` per
plane, one `gather_checked` per plane, one resample. There is no path by which a
correction is applied twice.

### 22.2 The `compose` precondition is satisfied — I checked my own wiring

`compose`'s doc (`optics.rs:233`) states a precondition that the module author
left for whoever wired it:

> **This function scales about the coordinate ORIGIN, not about the plane
> centre.** `z` must already be plane-centre-relative. Feeding it absolute
> warpmap coordinates would introduce a uniform red offset of order
> `eps * half_diagonal` ~ 1.5 sensels. Nothing in this crate calls `compose`
> yet; a wiring commit must satisfy that precondition.

**I wrote that wiring commit, so this is a self-audit and it deserved checking
rather than assuming.** It is satisfied:

```rust
// warpmap.rs:460
let (cx, cy) = (geom.width as f64 * 0.5, geom.height as f64 * 0.5);
let (sx, sy) = t.apply_at(px as f64, py as f64, cx, cy);

// align.rs:290
pub fn apply_at(self, x: f64, y: f64, cx: f64, cy: f64) -> (f64, f64) {
    let q = self.apply(Cx::new(x - cx, y - cy));
    (q.re + cx, q.im + cy)
}
```

The similarity acts on `(x - cx, y - cy)`. **The coordinates reaching `compose`'s
scale are plane-centre-relative, which is exactly what it requires.** The
1.5-sensel uniform red offset the doc warns about is not present.

### 22.3 "A resolution or CFA-plane factor composed with a convention" cannot exist here

This was the orchestrator's newly highest-weighted candidate, on the reasoning
that a factor of 2 multiplied by a genuine convention difference "lands
anywhere". **It cannot, for two independent reasons:**

1. **There is no convention in the apply path to compose with.** `compose`
   performs no normalisation of any kind — no field height, no diagonal, no `r`.
   `support_r_max` is declared metadata that nothing reads.
2. **A scale about the origin is unit-invariant.** `s·(2z) = 2·(s·z)`, so a
   plane-versus-sensel factor of 2 cancels identically and cannot alter the
   effective `eps`. The **only** unit-sensitive term in the model is the additive
   translation — and the shipped profile is `_RADIAL`, which drops it.

So the product the candidate requires has no second factor.

### 22.4 The centre convention, quantified

`cx = width * 0.5`, not `(width - 1) * 0.5`. If the fit assumed the other, the
resulting centre discrepancy is `delta = 0.5` plane px, and its effect through a
magnification is a **uniform translation** of `eps * delta = 704.5e-6 * 0.5 =
0.00035 plane px`. It is not a scale error and it is four orders of magnitude
below the effect under discussion.

### 22.5 Verdict

**The application path is definitively clean.** One call site, one application,
correct coordinate frame, no normalisation to get wrong, and unit-invariant with
respect to the one factor that could plausibly have been mismatched. Combined
with `optics.rs:692`'s closed-form assertion that
`compose(...).apply(r) == (1 + eps_r) * r` to `1e-9`, **the code applies exactly
`eps_r` about the correct centre, once.**

Therefore the measured gain, **if it is real**, lives in the coefficient or in
the instruments that measured it — and per §21 there is currently **no calibrated
instrument** in the project entitled to say which. My own `k = 1.374` remains
withdrawn. Nothing here licenses a change to `eps_r`, and nothing here licenses
shipping 0.692.

## 23. The clean space is necessary and not sufficient — and I still have no instrument

The orchestrator's stop-ship established that `--srgb --auto-exposure` is a
contaminated measurement space. **R10, R11 and R12 were all rendered
`--srgb --auto-exposure`.** `stack --help` says of that render, in the tool's own
words, *"For looking at, NOT for measuring"* — I ignored the same warning the
orchestrator did, one message after quoting its C3 analogue back at myself.

R13 re-renders the same stack, same sidecar, in the **default binned linear
camera-native** space — which the help text calls *"what measurement needs …
the file every number in this project's corpus was measured on"* — and re-runs
R11's plants there. Bars X1–X4 registered first, including M113's 529.9 ppm
registered as the number to beat **before** running.

### 23.1 Results

| bar | sRGB (R11) | clean (R13) | registered verdict |
| --- | --- | --- | --- |
| X1 `applied / eps_r`, ground truth 1.0 | — | **0.8338** | **FAIL** (band [0.90, 1.05]) |
| X2 gain, plant −704.5 / −352.2 | 0.584 | **0.940 / 0.927** | — |
| X2 gain, plant +352.2 / +704.5 | 0.299 | **0.771 / 0.655** | — |
| X2 sign asymmetry | 48.9% | **30.3%** | **FAIL** |
| X3 tangential leak | 3.0% | **0.7%** | PASS |

**X4 was not reported.** The gate refused, so I contribute **no competing value**
for `needed` and nothing that argues with M113's 529.9 ppm.

### 23.2 The space was a large confound, and it was not the only one

Every statistic improved in the clean space — asymmetry 48.9% → 30.3%, tangential
leak 3.0% → 0.7%. **The orchestrator's diagnosis is confirmed on my data.**

But the residual asymmetry is not noise, and its shape identifies the second
cause. Ordered by the **total** displacement the estimator faces (the scene's own
+408.5 ppm plus the plant):

| plant | total | total in px | gain |
| --- | --- | --- | --- |
| −352.2 | +56.3 ppm | 0.12 | **0.927** |
| −704.5 | −296.0 ppm | 0.63 | **0.940** |
| +352.2 | +760.7 ppm | 1.61 | **0.771** |
| +704.5 | +1113.0 ppm | 2.35 | **0.655** |

**Gain falls monotonically with the magnitude of the displacement being
measured**, and the fall begins right where a first-order gradient method stops
being valid, around 1 px. So §21's diagnosis — amplitude saturation — was **right
in kind and overstated in degree**: in sRGB it was compounded by a reference
partially anchored to the signal, and the two effects were not separable until
the space was cleaned.

**The correction to §21 is therefore narrower than a retraction.** "No calibrated
instrument exists" stands for *my* instrument, but the reason is amplitude
saturation, not the sRGB matrix alone, and it is not fixed by changing space.

### 23.3 An addendum to the transfer check, offered as a caution not a challenge

The transfer check is the best instrument anyone produced tonight and I have
adopted it. **But a single transfer number cannot reveal amplitude-dependent
gain**, because it is measured at one displacement — the one the shipped constant
happens to apply. My own chain reads `0.8338` while passing a tangential placebo
at 0.7%; nothing internal to that measurement would have exposed the saturation
that X2's four plants did.

This bears on the strongest claim of the night, so it is worth one control.
M113 reports `needed` of **529.9** and **654.9 ppm** on two scenes and concludes
the ~140 ppm gap is physical, from spectral differences. **If its estimator also
has amplitude-dependent gain, the two scenes sit at different true displacements
and would therefore be read at different gains, which produces a scene gap that
is partly instrumental.** Its two transfer values, 0.9399 and 0.9813, are
consistent with either story.

**I am not disputing the conclusion** — the spectral mechanism is sound and I
have no measurement of my own to set against it. The cheap control that would
settle it: run plants at **two amplitudes and both signs, in the clean space, on
both stacks**, and show the gain is flat. If it is, the scene difference is
physical and the "no scalar exists" conclusion is fully armoured. That is worth
having, because it is the claim everything else now rests on.

### 23.4 State

`eps_r = -704.5e-6` and `support_r_max = Some(0.788)` are **unchanged**; no
scalar was ever applied; `optics.rs` has not been edited since the wiring and its
clippy fix. **There is nothing of mine to unwind.** §22's finding is unaffected —
it is a code read, not a measurement, and the application path remains
definitively clean regardless of which space anyone measures in.

## 24. The PIL 16→8 hazard: nil exposure, and a correction to the triage rule

ORCH's fleet notice asks each milestone to declare its exposure and warns
against arguing from first principles that 8 bits was enough. This section
declares, then measures rather than argues.

### 24.1 M107 exposure: NIL

Grep over `experiments/M107-chroma/src` for `PIL|Image.open|tifffile|imread`
returns **46 matches in 19 files and not one PIL read**. Every TIFF read is
`tifffile.imread`; every raw read is `rawpy.imread`. Verified on the actual
files rather than assumed:

| file | shape | dtype | distinct levels |
| --- | --- | --- | --- |
| `r13/off.tif` | 2344×3516×3 | `uint16` | 23 966 |
| `r13/on.tif` | 2344×3516×3 | `uint16` | 23 986 |
| `r7/{off1,off2,offword,on,zero}.tif` | 4688×7032×3 | `uint16` | 58 925 – 59 092 |

### 24.2 What the hazard would have done, measured (`r14_pil_hazard.py`)

The lateral-CA A/B is ORCH's *"most suspect of all"* category by construction —
the whole signal is a sub-pixel resample difference. Bars H1–H3 registered
before running.

| bar | registered prediction | measured | verdict |
| --- | --- | --- | --- |
| H1 | signal median **below** the 257-count quantum | **465 counts** (p90 1406; 31.4% below one quantum) | **FALSIFIED** |
| H2 | 8-bit transfer check differs by > 0.05 | **0.6430 vs 0.8338, Δ 0.1908** | HOLDS |
| H3 | the wrong value looks plausible | finite, same order, no alarm | HOLDS |

Narrowing collapses 23 966 levels to **151, a 159× loss**.

### 24.3 The correction, which is the transferable part

**I predicted the hazard would bite because my signal was smaller than the
quantum. It is not — it is 1.8× larger — and the hazard bit anyway, by 23%.**

So the severity criterion in the fleet notice, *"a correction that moves pixels
by tens of counts is entirely inside the quantisation error"*, is a **sufficient
condition, not a necessary one**, and using it as a screen would have cleared
my metric while my metric was wrong by 23%.

The reason is the estimator's *form*, not the signal's amplitude. A sub-pixel
displacement estimator reads a **ratio of a difference to a local gradient**.
Quantisation damages the numerator *and flattens the denominator*, and the two
errors are correlated because both derive from the same rounding. Any method
that differentiates or divides by local structure is exposed at amplitudes far
above one quantum.

**Proposed screen, replacing amplitude:** ask whether the metric differentiates
the image or divides by local gradients. If it does, re-run it — whatever its
signal amplitude. Amplitude only tells you when it is *certainly* broken.

**Direction matters too.** The 8-bit read is biased **toward zero** (0.6430 vs
0.8338), so PIL-based measurements systematically **understate** a correction's
effect. Several of the 27 exposed scripts measure retention ratios and deltas,
where a bias toward zero reads as *"the correction did less than we thought"* —
a conclusion nobody would find surprising enough to challenge.

**One coincidence worth flagging so it does not mislead anyone.** The 8-bit
transfer check reads **0.6430**, which is close to M113's **0.6963** for the
demosaic-linear space. Two unrelated defects land in the same numeric
neighbourhood, so **a transfer check near 0.7 does not identify its own cause**
— it must be diagnosed, not pattern-matched.

### 24.4 A false positive on the exposure list

`experiments/ORCH-drift-check/ca_radial.py` appears among the 27 exposed
scripts. **It is not exposed.** It uses `Image.open` for the TIFF **tags only**
(`ca_radial.py:59-84`), then reads pixels with
`np.memmap(path, dtype="<u2", ...)`, after asserting bits/sample == 16,
samples/pixel == 3, compression == 1, planar == 1, strip contiguity, strip byte
counts and file size — raising `SystemExit` on each. Its only `Image.fromarray`
is a PNG preview, harmless by ORCH's own triage.

It is in fact **the one script in the fleet that wrote the check ORCH says none
of us wrote**, and it is the file measuring the subject under debate tonight.
That matters for confidence in the CA numbers, so it is worth removing from the
list explicitly rather than leaving it under suspicion.

## 25. §23's X1 failure retracted — it was a missing support floor, not contamination

ORCH's corrected triage rule says location statistics are largely immune to
16→8 narrowing. §24 reported a location statistic moving **23%**, which the
rule says should not happen. Rather than fold either result, R15 and R16 test
which of us is reading their instrument wrong. The answer is: I was.

### 25.1 The level bound is not the operative variable (R15)

| bar | registered | measured | verdict |
| --- | --- | --- | --- |
| Y1 | median levels/window **below** ORCH's bound of 12 | **25.0** (p10 4, p90 54) | **FALSIFIED** |
| Y3 | admitted-window count varies ≥ 2× | 1707 → 490, **3.5×** | HOLDS (checked first) |
| Y2 | a support floor collapses bias below 5% | **22.9% → 0.8%** | HOLDS |

§24 quoted **151 levels for the whole image**, which is precisely the count
ORCH warns is the wrong one. Counting properly gives **25 levels per fitted
window — above the immunity bound — and the 23% bias happened anyway.**

**So the ~12-levels-per-window bound does not predict this failure.** What
predicts it is **support**: an M113-style `MIN_EDGE_ENERGY` sweep drives the
narrowing bias monotonically to nothing.

| floor | n win | levels/win | uint16 | uint8 | bias |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 1707 | 25 | **0.8338** | 0.6430 | 22.9% |
| 60 | 1396 | 30 | 0.8981 | 0.8459 | 5.8% |
| 120 | 1287 | 32 | **0.9148** | 0.8760 | 4.2% |
| 480 | 490 | 48 | **0.9167** | 0.9096 | 0.8% |

### 25.2 The larger finding, which I was not looking for

**Read the `uint16` column — no narrowing anywhere in it.** It moves from
0.8338 to 0.9167 as the floor rises.

**§23 reported `X1 = 0.8338, FAIL — still contaminated`. That conclusion is
wrong and I retract it.** The space was clean. My estimator had no support
floor — only `std < 1e-6` and `den < 1e-3`, both effectively zero — and it was
integrating low-contrast windows that M113's shipped `MIN_EDGE_ENERGY = 60.0`
refuses. Worse, it **normalises each window to unit variance**, which amplifies
whatever noise those windows contain.

### 25.3 R16: the gates re-run with the floor, and two defects separated

Floor selected by a rule fixed before running — smallest floor with narrowing
bias under 5% admitting ≥1000 windows, i.e. **120** — with 240 alongside as a
robustness check, not a second chance.

| bar | registered | measured | verdict |
| --- | --- | --- | --- |
| Z1 | transfer in [0.90, 1.05] at **both** floors | **0.9148** and **0.9124**, spread 0.0023 | **PASS** |
| Z2 | four gains in [0.95, 1.05], asymmetry < 10% | 0.967 / 0.647 / 0.939 / 0.763, **asym 33.1%** | **FAIL** |
| Z3 | tangential leak < 10% | 1.9% | PASS |
| Z4 | `needed` vs M113's 529.9 | **NOT REPORTED** | gated |

**M107 and M113 now agree on the transfer check: 0.9148 vs 0.9399/0.9813.**
The apparent disagreement was entirely my missing floor.

**Z2's failure is the useful half, and I registered it as a live possibility
before running.** The floor barely moves the asymmetry — 30.3% without, 33.1%
with — so **amplitude saturation is a genuinely separate defect that a support
floor does not touch.** Two independent faults, now cleanly separated:

| defect | evidence | fixed by a floor |
| --- | --- | --- |
| low-support windows | transfer 0.8338 → 0.9148 | **yes** |
| amplitude saturation | asym 30.3% → 33.1% | **no** |

**I still report no `needed` value.** Z2 gates Z4 and Z4 stayed shut.

### 25.4 What this does to §23

§23.1's `X1 FAIL` and §23.2's "the clean space is necessary and not sufficient"
survive only in part. **The space effect is real and isolated** — comparing
like with like, both without a floor, sRGB gave 48.9% asymmetry and clean gave
30.3%. But **§23's specific claim that the residual 0.8338 proved remaining
contamination is withdrawn**; that residual was support, not space.

§23.3's caution to M113 is unaffected: it concerns amplitude-dependent gain,
which R16 shows a support floor does not remove, and which remains the one
control I would still ask for.

## 26. D, as asked — and a third term the unified statement still needs

### 26.1 The number ORCH asked for

**M107's `D` is 2.38** at the selected support floor and **2.28** with no floor —
bin `[2,3)`, the **unprotected** regime by ORCH's table.

M107 never claimed ratio cancellation; §24's stated reason was the reader
(`tifffile` throughout, no PIL call sites). But the transfer check is
`applied/eps_r` with `applied = e_on − e_off`, a two-arm contrast, so the `D`
is owed regardless of what the exposure claim rested on.

### 26.2 The table is right where support is adequate, and under-predicts where it is not

R15's floor sweep already held the data for a sharper question. Bars D1–D3
registered before running.

| floor | n | `e_off` | `e_on` | `D` | ORCH bin | predicted | **measured** |
| ---: | ---: | ---: | ---: | ---: | :--- | ---: | ---: |
| 0 | 1707 | +408.5 | −178.9 | 2.28 | [2,3) | 6.15% | **22.9%** |
| 60 | 1396 | +440.8 | −191.9 | 2.30 | [2,3) | 6.15% | 5.8% |
| 120 | 1287 | +453.8 | −190.6 | 2.38 | [2,3) | 6.15% | **4.2%** |
| 240 | 974 | +491.0 | −151.8 | 3.23 | [3,5) | 6.71% | 1.8% |
| 480 | 490 | +487.0 | −158.8 | 3.07 | [3,5) | 6.71% | 0.8% |

| bar | registered | measured | verdict |
| --- | --- | --- | --- |
| D1 | `D` varies < 1.5× while shift varies > 5× | `D` **1.43×**, shift **29.6×** | **HOLDS** |
| D2 | at adequate support, measured within 2× of bin median | 4.2% vs 6.15% | **HOLDS — corroborates** |
| D3 | at inadequate support, table under-predicts by > 2× | 22.9% vs 6.15%, **3.7×** | **HOLDS** |

**Within this sweep `D` and the shift move in opposite directions** — `D` rises
2.28 → 3.07 while the shift falls 22.9% → 0.8%. So `D` is **necessary but not
sufficient**, and it fails in the same structural way as *"is it a ratio"* and
*"is it absolute"* before it: a scalar summarising a statistic's shape cannot
decide a question that depends on **what the estimator was allowed to
integrate**.

**This does not refute ORCH's table.** The Spearman +0.530 is a *between-
statistic* trend across 1547 tiles; my anti-correlation is *within one
statistic* on one scene, where raising the floor changes which windows are
admitted. The two are compatible. What my data bounds is the table's **use as a
clearance test**: at `D` = 2.28 it predicted 6.15% and the truth was 22.9%.

### 26.3 The proposed third term

> The syntactic shape of a statistic tells you nothing about its exposure. What
> matters is what it reads (**value** vs **position**), how unequal its terms
> are (**`D`**), **and how much support each fitted window carries.** Report all
> three; the third dominated M107 by 3.7×.

### 26.4 M111's two checks, applied

**Grep false positives.** Counting `Image.open(` call sites in
`experiments/M107-chroma/src` returns **1**. Inspecting the return value — as
M111 instructs — shows it is a **docstring**: `r14_pil_hazard.py:57`,
`"""Emulate PIL.Image.open()'s silent uint16 -> uint8 RGB collapse."""`.
**1 textual match, 0 call sites.** Same failure class as matching *"compiling"*,
merely inverted: a comment *naming* the hazard rather than a word containing it.
Had I reported the raw count I would have declared an exposure I do not have.

**Input provenance.** M107's inputs are `C:\dev\strehl-out\M107-chroma\r13\{off,on}.tif`,
49 449 626 bytes each, written **directly by `strehl.exe`** during the §23
render with the r7 sidecar. They did not pass through another milestone's
scratch directory and were not produced by any Python reader, so there is no
upstream narrowing to inherit. The `r7` arms have the same provenance.

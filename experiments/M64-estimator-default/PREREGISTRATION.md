# M64 — pre-registration

Committed **before** any arm was scored against the new default path, and before
the crate diff existed. Rule 20: every criterion below names an input that would
make it FAIL, and such an input exists — the shipped `strehl stack` at `7d13140`
(an unregularised argmax) fails PR1, PR2 and PR7 by a factor of ~5, and
`strehl merge <dir> --out <tif>` does not run at all.

Nothing here is a prediction. It is a list of thresholds I am bound to report
against, whatever they say.

---

## 0. What is being changed

`strehl stack`, the obvious command, currently runs a **plain per-pixel argmax
selector**. M62 scored it at **0.7690x** on a 30-frame static burst whose correct
answer is **sqrt(30) = 5.4772** — a 1.300x noise *increase*. The estimating merge,
on the identical data and binary, scores **5.4778x** at `--gate 8`.

M64 makes the estimating merge the path `strehl stack` runs, moves the argmax
selector to a subcommand whose name says it is a baseline, and exposes exactly
one user-facing knob for the noise-sharpness continuum.

## 1. The default gate — declared here, before it is scored

**`DEFAULT_GATE = 4.0`.**

### 1.1 Disclosure: this section was written at 2.0 and changed before committing

My first draft of this file declared **2.0**, on the argument that gate 2.0 is
the rung measured on all seven corpus stacks (M52) and the one that lands
`109MSDCF` at mean `n_eff` **2.905** against fact 212's calibration target
`nwide = 3`, where gate 4.0 lands at 5.017.

I then read `experiments/M62-sqrt-n/PREREGISTRATION-M64.md`, committed at
`b94649c` **before my diff existed**, in which M62 — acting as acceptance
authority and explicitly declining to tell me what to aim for — requires the
default arm to land within **2%** of sqrt(30) and its efficiency within
**[0.98, 1.02]**. Gate 2.0 scores **3.776** at efficiency **0.876** (M62 section
6.2) and would be rejected.

**I changed the number, and I am recording that I changed it, why, and that
nothing had been measured when I did.** Two reasons, and the second is the one
that actually moved me:

1. M62's criterion is a legitimate statement of the project's thesis: on data
   where the arithmetically correct answer is to average everything, a default
   that averages 61% of it is not an estimator by any margin worth shipping.
2. **The nwide-3 argument I had built the 2.0 case on does not survive contact
   with its own source.** Fact 212's `nwide` is *"retained frames within 50% of
   peak height"* — the **fractional peak-height** rule of `m41lib.py`
   (`acc = cf >= gate * peak`), not the noise gate's
   `best - focus <= t*sqrt(2)*FOCUS_NOISE_SD`. They are different acceptance
   rules that happen to return similar integers on one stack. Equating them is
   the corpus's own move (`merge_cmd.rs` names `nwide = 3` as the gate's
   calibration target) and it is not sound. I flag it as a question rather than
   leaning on it.

The independent argument that lands on 4.0, which is not M62's and which I would
make without it: the gate compares each frame against a **maximum over N
frames**. Under the null that every frame has equal true focus, the winner sits
at about `E[max of N standard normals]` above the mean — 2.04 sigma at N = 30 —
so a tolerance of `t*sqrt(2)` sigma admits everything only once `t*sqrt(2)`
exceeds that offset plus a tail. **A fixed `t` is therefore an N-dependent
statement**, and M62's ladder measures where it lands: `t = 2` admits 61% of
frames that are provably identical in focus (it *rejects 11.6 of 30 frames it
should have admitted*, an error in the selector direction), `t = 4` admits 98.5%,
`t = 8` admits 100%. Corpus stacks run 19-130 frames, so N of about 30 is the
working case.

### 1.2 Why not 8.0, which scores better

`t = 8` gives a tolerance of `8*sqrt(2) = 11.3` sigma of the focus field's own
noise. `merge.rs`'s in-crate test
`real_focus_contrast_is_far_larger_than_the_noise_scale` pins real focus contrast
at **> 20 sigma**. A tolerance over half the discriminating margin is not a
defensible default, and 8.0 is off the shipped ladder so no corpus stack has ever
been measured at it. `t = 4` is 5.66 sigma — 3.5x inside the margin — and M52
measured it on `109MSDCF` (`n_eff` 5.017 / 22) and `foam` (1.361), so it is known
not to be degenerate on real data.

### 1.3 What choosing 4.0 costs, stated now

`109MSDCF` averages **5.017** frames at gate 4.0 where fact 212's fractional rule
retains 3. If the two rules were the same quantity — section 1.1 says they are
not — that would be 67% of over-averaging. **The sharpness cost of gate 4.0 on
real frames is not measured anywhere in this corpus**, on any axis, and M64 does
not measure it. That is the largest open risk in this milestone and it is stated
here, before the result, not in a closing caveat.

## 2. Arms

All CLI arms use **M62's battery, unmodified**: `experiments/M62-sqrt-n/src/`
`10-acceptance.py` and `11-focus-guard.py`, driven from `acceptance-spec.json`,
against the same latent, the same burst generator, the same truth-referenced
pooled-RMS ratio, the same inset ROI, the same 64x64 block bootstrap, N = 30,
three seeds. **I do not edit M62's spec, its thresholds or its code.** I run it
and report what it says. Where I need an arm its spec does not carry, I run it
from my own copy in `experiments/M64-estimator-default/src/` and label it as
mine.

| arm | invocation | what it is |
| --- | --- | --- |
| **N1 = M62 `DEFAULT`** | `strehl merge <burst> --flat-roi <roi> --out t.tif` | **the default path, no knob set** |
| **N1b** | `strehl stack <burst> --flat-roi <roi> --out t.tif` | the same path under the obvious name |
| **N2** | `... --gate 8 ...` | the knob at the estimator end |
| **N3** | `... --gate 0 ...` | the knob at the selector end |
| **N4** | `strehl argmax-baseline <burst> --flat-roi <roi> --out t.tif` | the old `strehl stack`, renamed |
| **G** | `strehl merge <real 22-frame stack>` | M62's focus-degeneracy guard |
| **A0-k** | Python mean of the first `k` frames | the arithmetic ladder, sqrt(k) |

## 3. Criteria

Every threshold is fixed here. `R` is M62's statistic; `sqrt(30) = 5.47723`.
PR1-PR3 are **M62's** thresholds, restated so that I am bound by them too; I did
not choose them and I will not argue with them after the fact.

| # | criterion | PASS if |
| --- | --- | --- |
| **PR1** | the default path reaches the arithmetic answer | **abs(N1 - 5.47723) / 5.47723 <= 0.02**, i.e. `R` in `[5.368, 5.587]` |
| **PR2** | it harvests what it admits | **efficiency `N1/sqrt(mean n_eff)` in [0.98, 1.02]** |
| **PR3** | it has not stopped being a focus stacker | **G: `mean n_eff / N < 0.95`** at some printed gate on the real 22-frame stack |
| **PR4** | `stack` and `merge` are the same path | **N1b = N1 to every printed digit**, and the two output TIFFs are **SHA-256 identical** |
| **PR5** | the knob still reaches its estimator end | **abs(N2 - 5.47723) / 5.47723 <= 0.005** |
| **PR6** | the knob still reaches its selector end — the continuum is real, not decorative | **N3 <= 1.05** |
| **PR7** | the argmax baseline survives the rename and still fails | **N4 <= 1.00** |
| **PR8** | the harness is calibrated on this binary | **every A0-k within 1% of sqrt(k)**; B1a, B1b within 0.005 of 1.0 |

**The harness is BROKEN — reported ahead of every other number — if** PR6, PR7
or PR8 trips. A harness that scores a selector above 1.05 cannot support any
claim about an estimator.

**A NOT MET is reported as NOT MET.** No threshold in this file will be
re-worded, widened or re-scoped after a run. If PR1 fails at gate 4.0 the
reported outcome is that gate 4.0 does not meet M62's criterion — not a new gate
chosen to meet it.

## 4. The CI test — criteria for the in-crate sqrt(N) invariant

A Rust test running in `cargo test`, on the **default path's own code** at
`DEFAULT_GATE`, on a synthetic static burst. Its plant is *not* M62's plant, so
absolute thresholds do not transfer; these are the criteria it must meet.

| # | criterion | PASS if |
| --- | --- | --- |
| **PR9** | the in-crate harness is calibrated | ideal mean of all N frames scores **sqrt(N) +/- 2%** |
| **PR10** | the fixture exercises averaging (rule 36) | **mean `n_eff` >= 3.0** at `DEFAULT_GATE` |
| **PR11** | the default path is an estimator | **R >= 1.70** at `DEFAULT_GATE` |
| **PR12** | efficiency against the Jensen bound | **R >= 0.80 * sqrt(mean n_eff)** |
| **PR13** | negative control, in the same test (rule 39) | **R <= 1.05** at gate 0 |
| **PR14** | the test has power | setting `DEFAULT_GATE = 0.0` must make the test **FAIL**, demonstrated by a run whose output is quoted |

**PR14 is the one that matters.** A sqrt(N) test that passes at gate 0 is another
un-failable check (discipline 250) and would be reported as the finding.

## 5. Declared in advance, so it cannot be presented as a discovery

- **The rename makes M62's `SELECTOR-shipped` power arm measure something else.**
  `acceptance-spec.json` runs `stack {burst} ...` and expects <= 1.05. After M64
  that invocation is the estimator. M62 pre-registered this exact possibility and
  scores it **NO-POWER**, not FAIL. The invocation that retains the arm's
  semantics is **`argmax-baseline`**, and `merge --gate 0`
  (`SELECTOR-same-binary`) is untouched, so a power arm remains available. I am
  **not** editing M62's spec — that is the acceptance authority's file.
- **M57's 0.496-0.740 px price list is measured on a fractional peak-height
  gate** (`m41lib.py`, `GATE = 0.5`, `acc = cf >= gate * peak`; gate 0.00 admits
  all 16 frames and gate 0.99 admits 1.45), **not on this `--gate`**, and it runs
  in the opposite direction. Any `--help` text I write must state the price on
  the axis the two share, which is mean `n_eff`. Declared here because the brief
  that commissioned M64 asserted the two axes were the same.
- **Facts 84 and 19 are checked, not assumed.** The brief names both as
  "verified, unbuilt". I will report what the code says, including if the answer
  is "already wired and the fact row is stale".

## 6. What none of this tests

The burst's noise is drawn from the same `g` and `RN_e` the gate uses, so every
number here measures the estimator's **efficiency** and is circular with respect
to the sensor calibration (rule 34, M62 section 8). M64 adds no capture and
closes no calibration question.

It also measures **no resolution**. Not one number below is a sharpness
measurement, and section 1.3 says plainly that the default gate's sharpness cost
on the `--gate` axis is unmeasured in this corpus. A pass on the sqrt(N) battery
is a statement about noise and defaults only — M62 says the same sentence about
its own instrument and I am not entitled to a wider one.

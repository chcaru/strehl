# M43 — the plugin seam has a calibration hole, and it is measurable

Status: **MEASURED, NOT INDEPENDENTLY VERIFIED.** Every number here came from
the shipped `strehl merge` binary run against real RAW frames tonight, plus
arithmetic on two constants read out of the crate source. None of it has been
checked by anyone but its author, and rule 12 says that is not enough.

Author: orchestrator. Milestone raised by nothing — it fell out of updating the
README and noticing that the gate's tolerance is printed in units nobody
supplies.

---

## 0. The finding in one paragraph

`strehl` is meant to be pluggable, and the focus measure is the first thing
anyone will want to replace: the project has already swapped it three times
itself (M11 ring → M14 Tenengrad → M17 `tenengrad-sq`). But **the gate that
makes this an estimator rather than a selector is calibrated in units of a
constant that belongs to the operator**, and the plugin design in
[`E-plugin-architecture.md`](E-plugin-architecture.md) — written before that
constant was measured — has no slot for it. A contributor who supplies a focus
measure and inherits the host's constant does not get a warning, an error, or a
visibly different log line. They get a silently rescaled gate. Measured below:
one such mistake reverts **87.76% of the image to pure selection**, which is
precisely the defect this project exists to remove.

## 1. The mechanism, verified against the binary

The admission rule (`merge.rs`, and printed by `strehl merge --help`) is: a
frame joins the average where its regularised focus response is within

```
tol = t * sqrt(2) * FOCUS_NOISE_SD
```

of the winner's. `t` is the user's `--gate`. `FOCUS_NOISE_SD = 0.015214` is
**measured in-crate** and its own doc comment states the constraint that matters
here:

> It is a function of `WINDOW_RADIUS` and `REGULARISER_RADIUS`, and it is wrong
> if either changes.

It is also, unavoidably, a function of the **operator** — it is the standard
deviation of *that operator's* response to pure sensor noise. `through_focus.rs`
carries a second one for the finer statistics scale, `FINE_FOCUS_NOISE_SD =
0.090400`, with the parallel warning that it is a function of
`FINE_WINDOW_RADIUS` alone.

**Verified from the shipped binary** (`109MSDCF`, 22 frames):

| `--gate` t | printed tol | tol / t |
| --- | --- | --- |
| 0.168 | 0.003615 | 0.021518 |
| 0.5 | 0.010758 | 0.021516 |
| 1.0 | 0.021516 | 0.021516 |
| 2.0 | 0.043032 | 0.021516 |
| 5.94 | 0.127804 | 0.021516 |

`sqrt(2) * 0.015214 = 0.021516`. The ratio is constant to **2.0e-6** across a
35x range of `t` (the last digit at t=0.168 is the CLI rounding the gate label
to 0.17). So `tol` is exactly linear in the constant, and:

> **An operator whose true noise SD is `k` times the declared constant behaves
> exactly like the declared gate divided by `k`.**

That substitution is what makes the hole measurable without writing a plugin
system first.

## 2. What it costs, measured

> **CORRECTION, added after §8 was measured.** The paragraph immediately below
> is **wrong** and is kept because the error is instructive. `k = 5.942` divides
> `FINE_FOCUS_NOISE_SD` by `FOCUS_NOISE_SD`, and **those two constants are not
> the same kind of quantity** — the coarse one is measured *with* the 17×17
> regulariser applied, the fine one *without*. The two operators therefore do
> not "differ only in window radius", and the honest `k` for that pair is
> **1.815**, not 5.942 (§8). **The table below is unaffected**: it was produced
> by running the binary at effective gates 0.168 and 5.94, not by trusting the
> pair. And §8's survey supplies a *larger* real `k` — **6.68**, from the
> sum-modified-Laplacian — so the corrected record prices this seam higher than
> the mistake did. SYNTHESIS facts 500, 439.

`FINE_FOCUS_NOISE_SD / FOCUS_NOISE_SD = 0.090400 / 0.015214 = **5.942x**`. These
are two real operators already in this codebase, differing only in window
radius, so `k = 5.94` is not a strawman — it is what happens if a contributor
supplies a finer-window operator and inherits the host's constant.

At the intended operating point `--gate 1.0`:

| case | effective gate | mean `n_eff` | pixels at `n_eff` = 1 | what the log says |
| --- | --- | --- | --- | --- |
| constant correct | 1.000 | 1.884 | 41.66% | `gate 1.00` |
| operator 5.94x **noisier** than declared | 0.168 | 1.131 | **87.76%** | `gate 1.00` |
| operator 5.94x **quieter** than declared | 5.940 | 7.267 | 2.40% | `gate 1.00` |

Read the third column. **The same declared gate produces anything from
87.76%-selection to a 7.3-frame average**, and the three runs are
indistinguishable from the log, the exit code and the CLI's own calibration
block. In the noisy direction the tool degrades into the selector it was built
to replace; in the quiet direction it averages frames the noise model can
actually tell apart, which is blur.

## 3. Why the existing design does not catch this

[`E-plugin-architecture.md`](E-plugin-architecture.md) §F3.3 negotiates
*capabilities* — domain, tiling, channel layout, GPU/CPU path — and §F4 property
-tests **confluence** (Cordis Thm 73: the composed pipeline is order-independent)
and **sensitivity** (§F4.3, explicitly the anti-tautology clause). Both are
good, and neither can see this. A focus-measure plugin with a wrong noise
constant is:

- **capability-compatible** — same domain, same tiling, same layout;
- **confluent** — it commutes with everything exactly as well as the right one
  does, because the constant is not an ordering property;
- **sensitive** — its output *does* change when the input changes, which is all
  §F4.3 asks.

It passes every existing gate and produces a quietly worse image. That is the
signature of a missing *contract*, not a missing test.

## 4. What the plugin API must therefore require

**A focus-measure plugin must supply its own noise constant, and must ship the
measurement that produced it.** Concretely, the trait needs a member with the
shape of the existing in-crate tests
(`the_focus_noise_constant_is_the_measured_one`,
`the_fine_focus_noise_constant_is_the_measured_one`): push a pure-noise luma
plane at the operator's *own* window through the operator, take the SD of the
response, and assert the declared constant. That test already exists twice in
this codebase for the two built-in operators; the plugin boundary must make it
mandatory rather than customary.

Three consequences worth stating separately:

1. **The constant cannot be inherited from the host**, and a plugin that omits
   it must fail to load rather than default. A default here is a silent 5.94x.
2. **The window radius cannot be inherited either.** The constant is a function
   of the operator *and* its window, so the pair must be declared together —
   which is the same conclusion M42 is currently testing from the quality side
   (`WINDOW_RADIUS = 13` was tuned for `|grad|` and the shipped operator is now
   `tenengrad-sq`).
3. **A plugin that provides a detector must declare its scale**, because fact
   152 measured bimodality *depleted* at the selection scale and enriched at
   radius 2. A detector silently evaluated at the wrong scale is the same class
   of defect as a gate silently evaluated at the wrong tolerance.

## 5. What would change this verdict (rule 20)

- **If `tol` were not linear in `FOCUS_NOISE_SD`**, the `t → t/k` substitution
  would be invalid and every number in §2 would collapse. Measured linear to
  2.0e-6 over 35x in §1; this is the check with the power to fail, and it did
  not.
- **If the gate's effect on `n_eff` were flat**, the miscalibration would be
  harmless. It is not: `n_eff` moves 1.131 → 7.267 over the swept range.
- **If `k` were realistically near 1** for any plausible contributed operator,
  the hole would be theoretical. `k = 5.94` is taken from two operators already
  in this repository.
- **If a contributor could not plausibly omit the constant**, this is a
  documentation problem, not an API one. Judgement, not measurement: the current
  design has no field for it, so omission is the default rather than an error.

## 6. What is not measured here

- **No plugin system was built or exercised.** The hole is demonstrated by
  simulating a wrong constant through the exact gate arithmetic the binary uses,
  not by loading a plugin. That is sufficient to show the *mechanism* and
  insufficient to show that a real implementation would hit it.
- **`k = 5.94` is illustrative, not a distribution.** No survey of plausible
  contributed operators' noise SDs exists. **— SUPERSEDED by §8**, which
  surveys seven and finds a 10.4× spread. The illustrative figure was also
  wrong; see the correction at §2.
- **Only one stack.** The `n_eff` figures are `109MSDCF` at 22 frames; fact 324
  measured that `n_eff` at a fixed gate spans 2.26-7.42 across five stacks, so
  the *absolute* numbers here are stack-specific. The *ratio* argument is not.
- The 87.76% figure is the share of pixels at `n_eff` = 1, which is selection.
  It is not a claim about how much worse the output image looks; no image
  quality metric was run.

## 7. Reproduce

```console
$ strehl merge C:\dev\macro\test\109MSDCF --gate 0.168 0.5 1.0 2.0 5.94
```

Read the `tol(DN-norm)`, `mean n_eff` and `n_eff=1 %` columns. Constants are at
`crates/strehl-core/src/merge.rs` (`FOCUS_NOISE_SD`) and
`crates/strehl-core/src/through_focus.rs` (`FINE_FOCUS_NOISE_SD`).

## 8. The spread of `k`, measured — and a correction to §2

§6 said `k = 5.94` was illustrative and that no survey existed. This is the
survey, and it answers SYNTHESIS question 102.

### 8.1 The instrument, and why it is admissible

A Python model of the focus operator, calibrated against **both** constants the
crate measures in-house, **each in its own configuration**:

| target | configuration | crate | Python | deviation |
| --- | --- | --- | --- | --- |
| `FOCUS_NOISE_SD` | w13 → regulariser r8 | 0.015214 | 0.015286 ± 0.000040 | +0.47% |
| `FINE_FOCUS_NOISE_SD` | w2, no regulariser | 0.090400 | 0.090579 ± 0.000066 | +0.20% |

8 seeds × 2048² unit-variance Gaussian planes; interior only, replicate borders
dropped. **The script refuses to print the survey if either target misses.**

That refusal is not decoration — it fired. The first instrument
(`02-operator-noise-spread.py`, kept in the tree) modelled the coarse field
*without* the regulariser and read **+24.26%** high against `FOCUS_NOISE_SD`
while matching `FINE_FOCUS_NOISE_SD` to **+0.20%**. One target passing and one
failing localises the fault to the single thing the two configurations differ
in, which was the bug — and which is also the error in §2. A one-target
calibration would have been tuned into agreement and the survey below would have
been silently wrong by a quarter.

This is the narrow, structural answer to M31-V's standing objection that this
project's Python proxies were never checked against the crate.

### 8.2 The survey

Seven textbook focus operators, each in the shipped configuration
(operator → 27×27 box → 17×17 regulariser), as
`k = SD / FOCUS_NOISE_SD`:

| operator | SD | `k` | effective gate at `--gate 1.0` |
| --- | --- | --- | --- |
| ring(1,3) | 0.009804 | **0.644** | 1.552 |
| tenengrad `\|∇\|` *(shipped)* | 0.015337 | 1.008 | 0.992 |
| tenengrad-squared | 0.020799 | 1.367 | 0.731 |
| Brenner | 0.029846 | 1.962 | 0.510 |
| local variance (3×3) | 0.037653 | 2.475 | 0.404 |
| Laplacian | 0.100266 | 6.590 | 0.152 |
| sum-modified-Laplacian | 0.101623 | **6.680** | 0.150 |

The shipped operator reads 1.008 where it must read 1.000 by construction; the
0.8% is the instrument's own noise floor at 4 seeds, and it bounds the
resolution of every other row.

**`k` spans 10.4× across seven operators, none of them adversarial.** Three
things follow:

1. **The worst case is the most likely contribution.** Nayar & Nakagawa's
   sum-modified-Laplacian is *the* canonical shape-from-focus operator. It is
   the first thing a contributor reaching for a classical focus measure would
   reach for, and it lands at `k` = 6.68 — an effective gate of 0.150 at a
   declared 1.0.
2. **Both directions are populated by operators that actually exist.**
   ring(1,3) is *this project's own first shipped operator* and errs the other
   way, over-admitting at an effective 1.55.
3. **The load-time refusal in §4 is therefore mandatory, not tidy.** §5 named
   "plausible operators cluster near `k` = 1" as the finding that would have
   demoted this to a documentation problem. It is refuted.

### 8.3 The correction to §2

Measuring the fine operator *as the host would actually run it* —
`SD(regularise(box_mean(|∇|, 2))) = 0.027613` — gives `k = 1.815`, not 5.942.
§2 overstated that pair by **3.27×**. The direction was pre-registered in the
measuring script's docstring before the number was computed (a small window
leaves more high-frequency power for the regulariser to remove, so regularising
the fine field must cost it proportionally more), and it held.

The §2 cost table stands unchanged, because it was produced by running the
binary at effective gates rather than by trusting the pair. What fails is one
sentence of provenance — and §8.2 replaces it with a larger `k` from a real
operator.

### 8.4 Reproduce

```console
$ python experiments/m43-plugin-seam/02b-operator-noise-spread.py
$ python experiments/m43-plugin-seam/03-fine-in-gate-path.py
```

SYNTHESIS facts 439, 500, 501; discipline 257; question 102 answered.

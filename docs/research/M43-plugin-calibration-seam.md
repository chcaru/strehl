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
  contributed operators' noise SDs exists.
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

# M126 / PQ6 — pre-registration: what was `FOCUS_NOISE_SD` fitted on?

Written and committed **before any outcome value was read**. The only thing run
beforehand was a feasibility probe (does a 1-frame stack emit `best_focus.npy`?
yes, f32, 3516x2344) which did not compute the outcome statistic.

Parent pre-registration: `b77d67c4`. Parent report: `docs/research/M126-default-audit.md`.

## The question ORCH asked

PQ6, raised by M105b and declined by it as out of lane: **if `FOCUS_NOISE_SD` was
calibrated on narrowed data, the gate is set too tight**, because a noise floor
that reads low makes `Gate::admits` accept fewer frames than it should.

## What is already settled by reading, not measuring

Recorded here so it is not later mistaken for a result of this experiment.

| ORCH question | answer | citation |
| --- | --- | --- |
| What data was it fitted on? | **Synthetic f32 standard normals**, generated in-crate by SplitMix64 + Box-Muller, 12 seeds, 512x512 plane. Not camera RAW. No integer intermediate, no narrowing, at any stage. | `merge.rs:2019-2061` (the test), `merge.rs:1897-1926` (the RNG) |
| Differencing or split-half estimator? | **Neither.** A plain sample SD of one field's interior, `sd(reg[interior])`. | `merge.rs:2049-2060` |
| Reachable as a default? | **No.** `pub const FOCUS_NOISE_SD: f32 = 0.015_214` at `merge.rs:187`, consumed at `merge.rs:313`. Compile-time; no environment variable, no flag. Its correctness is not a switch. | `merge.rs:187`, `merge.rs:313` |

**So PQ6's literal premise is not satisfied: the constant was not calibrated on
narrowed data.** Facts 310-313 state the synthetic provenance accurately and
never claimed otherwise.

**But that does not clear it**, and the reason is ORCH's own broadening. The
operator chain is a 27-box followed by a 17-box — a 43x43 average, the single
most averaging-exposed operation in the crate, which the doc says buys an 18.6x
reduction from ~348 effective samples. Under the corrected rule (the vulnerable
operation is **averaging**, not differencing) that reduction is only available
to error that is **independent across the support**. Quantisation, fixed-pattern
noise, dust and hot pixels are value-deterministic, move the population
together, and do not average down.

**The live hazard is therefore the inverse of the one PQ6 names**: not a
calibration contaminated by narrowing, but a calibration that is *too clean* for
the domain it is applied to. Same predicted direction — gate too tight — by a
different mechanism. Recorded separately per discipline 912, because a correct
verdict reached by the wrong argument is what this experiment must avoid.

## Design

**Arm S (synthetic, the crate's own domain).** `cargo test -p strehl-core
the_focus_noise_constant_is_the_measured_one` at `d5ba764`. Positive control for
the constant, not for my analysis pipeline.

**Arm R (real sensor data, no selection bias).** `strehl stack <dir> --limit 1`
with `STREHL_DUMP_MERGE_STATE` set. **With N = 1 the winner is the only frame**,
so `best_focus` is that frame's regularised response with the winner's curse
removed by construction — the direct real-data analogue of what Arm S measures
on synthetic normals. Measure the per-tile SD of `best_focus`.

Subjects: the parent milestone's five (`bee-3-cpl`, `lead-1-cpl`, `leaf-2-cpl`,
`coffee-bean`, `tweezers-cpl`), read-only from `D:\personal\macro\`.

**Tile selection must not be circular.** Flat tiles are chosen by the *rendered
output plane's* high-pass energy using the parent milestone's committed
`score.py` selector — never by the focus response being measured.

**Reader discipline.** `numpy.load` on f32 NPY, `assert dtype == np.float32`
immediately after load. No `PIL` anywhere.

## This is a ONE-SIDED test, and that is registered before the fact

A real "flat" tile still contains dust, gradients and faint texture, so Arm R is
an **upper bound** on the true sensor-noise floor. Therefore:

* Arm R at or below `0.015214` → **clean refutation**; the constant is not too small.
* Arm R far above `0.015214` → **consistent with PQ6 but confounded**, and by
  itself does not establish it.

The p05 of the per-tile distribution is the primary estimate (the flattest tiles
approach pure noise); the median is reported alongside as the pessimistic bound.

## Predictions — direction and rough magnitude, before any data

* **Q1.** Arm S reproduces `0.015214` at `d5ba764`. *(control; if it fails, stop)*
* **Q2.** Arm R p05 is **larger** than `0.015214`, by **>= 3x**. Reason: the
  43x43 average cannot suppress correlated error, and real frames carry
  fixed-pattern structure that synthetic i.i.d. normals do not.
* **Q3 — the discriminator, and the one that makes Q2 interpretable.** If the
  excess is a genuine *noise* floor, it should be **near-constant across
  subjects** at comparable ISO, because the response is sigma-normalised and the
  doc claims one threshold is valid across stacks. If instead it is **residual
  scene structure**, it should **vary >= 2x across the five subjects**.
  I predict **variation >= 2x**, i.e. structure dominates the excess.
* **Q4.** Narrowing the input further will move Arm R by **< 10 %** of the
  Q2 excess — because §14 measured this data at 294-1009 distinct levels per
  flat tile (dose 0), two orders inside V-M113's threshold of 12. If Q4 fails
  and narrowing moves it a lot, §14's clearance needs revisiting.
* **Q5.** Re-running one arm produces a byte-identical `best_focus.npy`, and my
  pipeline reads exactly `0.00000` difference. *(placebo / null check)*

## Success criterion per ORCH's three questions

Not "is the constant right" — I cannot settle that from an upper bound. The
deliverable is: **the provenance, stated exactly; whether the synthetic domain
matches the application domain; and whether the gap is large enough to matter.**
If Q2 holds and Q3 says structure dominates, the honest verdict is
**NEEDS MORE DATA with a named next experiment**, not a promotion or a refusal.

## What would make me wrong

If Arm R p05 lands near `0.015214`, my Q2 reasoning about correlated error
surviving the box average is wrong for this operator, and I will say so — the
mechanism I named above would then be a plausible story that measurement
refuted, which is exactly the discipline-912 failure I am trying to avoid.

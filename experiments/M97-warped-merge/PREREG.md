# M97 pre-registration — written before any metric was computed

Committed before the first number was read. Anything added later is marked as
an amendment, with the reason.

## Context that changed the question

The dispatch asked me to wire the warp sidecar into `strehl stack`. While I was
building, sibling milestone **M86c** committed `885e9f7` "wire alignment into
strehl stack; fix the black-fill defect", which does exactly that. The wiring
question is answered and re-answering it would be duplicated work.

M86c's own report names what it could **not** do, in §15.7:

> **A geometry metric.** 15.4 is the priority: until the ruler test is run,
> "the render is better" is unmeasured.

and §15.4 concludes:

> **I am not claiming a sharpness win. I did not measure one.**

So M97's question becomes the one M86c left open, and the one the owner's
complaint actually turns on:

> **Does the registration that now ships measurably improve the merged
> photograph, judged by a metric that can actually see misregistration?**

Rule 12 applies in my favour: M86c authored the wiring, so M86c must not be the
one that verifies it.

## Why not gradient energy

M86c measured radial Tenengrad, aligned against a matched zoom-only null, at
**0.9859** whole-frame — very slightly *worse*. Their reading, which I accept as
ARGUED and which I am not re-testing, is that in a focus stack each output pixel
is drawn from a frame that is in focus *there*, so misregistration does not rob
that pixel of sharpness; it takes it from the **wrong scene point**. Seams
between winner regions *add* gradient energy. A gradient-energy metric is
therefore insensitive to this defect and can be inverted by it.

The defect is geometric. The metric must be geometric.

## Subject

`D:\personal\macro\flat-on-ruler-cpl`, 79 frames. Read-only.

Chosen because it carries **ground truth**: a machined steel rule. Its
graduations are equally spaced in the world and its long engraved baseline is
straight in the world. `highly-angled-ruler-mm-cpl` is excluded because
`align_cmd::TILTED_SUBJECTS` lists it and the merge refuses to register it.

MEASURED before pre-registering (solve only, no metric): the bracket drifts
**111.054 plane px** corner-to-corner, held-out **11.081 px**, cycle floor
**0.799 px**, 79/79 placed, solve 7.2 s.

## The metrics, and their known answers

Both are computed on the same rendered TIFF, whole frame, no crop.

- **S — baseline straightness.** A straight line in the world projects to a
  straight line under *any* homography, so a correct render must show the
  ruler's baseline edge as straight regardless of viewing geometry. Metric:
  RMS residual, in output px, of the sub-pixel edge y-position about a fitted
  straight line. Lower is better.
- **G — graduation spacing regularity.** Equal world spacing projects to
  spacing that varies **smoothly** (projectively) across the image. Metric: RMS
  residual of sub-pixel tick x-positions about a fitted smooth model, in output
  px. Local, non-smooth scatter is the misregistration signal. Lower is better.

## Arms

| arm | how |
| --- | --- |
| `UNALIGNED` | `STREHL_ALIGN=0` |
| `ALIGNED` | the solved sidecar, via `STREHL_WARPMAP` |
| `ZOOMNULL` | `STREHL_ALIGN=zoom` — identical resampling cost and field of view, relative registration discarded |
| `JITTER-J` | the solved sidecar with a known pseudo-random per-frame translation of per-axis sd `J` added |

`ZOOMNULL` is the only fair comparator for `ALIGNED`: `UNALIGNED` has a
different field of view and sampling density, and M86c measured that the
`fit_to_cover` upsample alone is 1.0735x on `bee-3-cpl`.

## Pre-registered bar

**P1 — responsiveness. THE GATE THAT DECIDES WHETHER ANY OTHER RESULT COUNTS.**
A metric reading a null is indistinguishable from a disconnected probe. So the
plant comes first: `JITTER` at per-axis sd **6.0 plane px** must read **worse
than `ALIGNED` by at least 3x the ALIGNED-vs-ZOOMNULL difference** on at least
one of S, G. *The input that must fail:* if the planted jitter does not move the
metric, **the metric is blind, and I report no result on P2 rather than any
verdict.** A blind metric cannot produce a negative result either.

**P2 — the question.** `ALIGNED` beats `ZOOMNULL` on S and/or G. *The input that
must fail:* if `ALIGNED` and `ZOOMNULL` are within the scatter that P1
establishes as the metric's resolution, the honest answer is **registration does
not measurably improve this render**, and I report that. A negative here is a
publishable result, not a failure.

**P3 — no NaN and no black rim**, whole frame, both renders, stated as a
fraction of all pixels — not on a crop.

**P4 — the placebo.** An identity sidecar fed through `STREHL_WARPMAP` must
reproduce `UNALIGNED` to a stated tolerance. It is not expected to be
bit-exact: `fit_to_cover` holds the grid 3 px inside the source, so identity
still pays one resample at `k` slightly below 1. Tolerance is therefore stated
against that, and the *shape* of the claim is "no registration happened", not
"no arithmetic happened".

**P5 — a wrong-stack sidecar is refused**, not applied. Feed `bee-3-cpl`'s
sidecar to the ruler bracket. Must be a hard error naming both stacks.

**P6 — a refused frame.** Plant a `refused` record and run. Record what the
merge actually does, and judge whether it is right.

**P7 — timing.** End to end, same machine, same stack, before and after.

## Named risk, recorded before measuring

`flat-on-ruler-cpl` is a *flat* subject. If the rule is close to
fronto-parallel, most of the field may be won by a narrow band of frames, and
misregistration between frames that never win together cannot reach the output.
That would make P2 read null **for a reason that has nothing to do with
registration being worthless**. I will therefore measure the spread of the
winner index across the field and report it beside P2, and I will not read a
null P2 as "alignment does not help" unless the winner spread shows the frames
actually had the opportunity to disagree.

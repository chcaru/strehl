# M97b pre-registration — can any instrument see the alignment?

Written **before** any metric is computed on any render of
`dry-erase-marker-head-cpl`. The renders were started while this was being
written; no number from them has been looked at.

## The question

The project has shipped a geometric correction that **no instrument it owns can
detect**. M86 measures the aligned render at **0.9859x** whole-frame Tenengrad
against a matched zoom-only null; M85 independently measured **0.985x** across a
61x change in frames-averaged-per-pixel. Two nulls, two directions, one
conclusion: *we cannot tell the owner whether his photographs are better.*

## My hypothesis, and why it is not the same as M86's

M86's ARGUED explanation is that misregistration **displaces** detail rather
than blurring it, so gradient-energy metrics are structurally blind.

I measured something narrower and sharper in M97 §11a, and it makes a different
prediction. Correcting registration on bee-3-cpl improved the render **only at
large radius** — centre indistinguishable, outer band visibly better. That is
forced by geometry: **a scale error is exactly zero at the optical centre and
grows linearly with radius.** So a whole-frame metric does not merely dilute the
effect, it averages a real edge win against a guaranteed centre null.

**H1 (to be tested): the nulls are a subject-selection artefact, not a property
of alignment.** bee-3 has 1.95 edge/centre detail and the bee is central;
`dry-erase-marker-head-cpl` has **72.2** and drifts **23.9%** (both MEASURED,
`src/scout.py`, `data/scout.json`). If H1 holds, the same metric that reads null
on bee-3 reads a win on the marker head when resolved by radius.

**H1 is falsifiable and I expect it might fail.** If the radially resolved
metric reads null on the marker head too, then alignment does not improve the
rendered photograph on this rig, and I will report that.

## Bars, with the failing value stated in advance

Arms, all on `dry-erase-marker-head-cpl`, default binned linear output
(NOT `--srgb`/`--demosaic`, which M85 forbids measuring):

| arm | how |
|---|---|
| ALIGNED | `STREHL_WARPMAP=<solved sidecar>` |
| ZOOMNULL | `STREHL_ALIGN=zoom` — same resampler, same field of view, registration discarded |
| UNALIGNED | `STREHL_ALIGN=0` |

**Q1 — Responsiveness (mandatory, and it gates everything else).** A jittered
sidecar (planted per-frame random similarity, ~6 plane px) must move the metric
by **at least 5x** the ALIGNED-vs-ZOOMNULL difference. *Fails if* the plant
moves it less than that. **A metric that cannot see a planted defect cannot be
used to declare a null**, and three of five defects a sibling milestone found in
itself tonight were exactly this.

**Q2 — The mandatory null.** ALIGNED vs ZOOMNULL is the only comparison that
isolates registration; ZOOMNULL holds resampling and field of view fixed and
discards only the registration. *Fails if* I cannot separate them at all, in
which case the metric is not measuring registration and I say so.

**Q3 — The radial prediction.** If H1 holds, the ALIGNED-over-ZOOMNULL ratio
must **increase with radius**, and the centre band must be near 1.000. *Fails
if* the effect is flat in radius — that would mean whatever I measured is a
global change (tone, resampling, exposure) and **not** registration, and I must
not claim it.

**Q4 — Boundary immunity.** M86's first render read a fake **1.4565x** because
its metric was measuring the black fill boundary over 9.544% of the frame. Every
number I report must be computed under an explicit coverage mask, and I must
show the mask is right by planting boundary pixels and confirming they are
excluded. *Fails if* masked and unmasked numbers differ materially and I cannot
account for it.

**Q5 — The direction is not assumed.** The metric must be signed such that I
would notice alignment making things *worse*. My earlier ruler work found
ALIGNED (9.832) marginally worse than UNALIGNED (9.548) on straightness; I will
not silently drop a sign like that.

## Named risk

The marker head may be a **flat** subject. If its detail is all at one depth,
the stack barely stacks and there is little for registration to spoil. The
`edge/centre = 72.2` says detail reaches the corners; it says nothing about
depth spread. If mean `n_eff` comes back near the frame count, the subject is
too flat and the test is inert — I will report that rather than a number.

## What I will not do

Not re-run whole-frame Tenengrad as a headline; it is measured-dead for this
purpose. Not touch `merge_cmd.rs`, `merge.rs`, `align_cmd.rs`, `warpmap.rs`.

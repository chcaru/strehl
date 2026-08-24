# M95 arm 8 — pre-registration

Written and committed to before any arm number in this experiment was computed.

## The question

The orchestrator has twice priced the coverage rescale by measuring **a gather**
and attributing the result to **the scale**:

- round 1, `resample_budget.py` R1: one Catmull-Rom gather at k = 0.9315 on a
  single rawpy frame, **+0.2392 dex**, read as "64.2% of the deficit";
- round 2, M104: the factor `1.073537` planted on the render, **+0.1789 ± 0.0055**,
  read as "~48% of the deficit", giving a corrected bar of **≈ +0.19**.

Arm 7 measured the thing the fix would actually change — removing `k` from
strehl's **composed** mapping — and got **+0.0143 dex (7.8%)**.

M104's own finding #1 is the reason I think the two are reconcilable and that
the orchestrator's inference from it does not follow. M104 swept a 15× dose
range and read `+0.159 / +0.157 / +0.179 / +0.181` — **flat**. The orchestrator
drew from this "the stretch must be removed, not reduced". But strehl's
`fit_to_cover` returns `s.then(t)`: removing `k` does not remove the gather,
because each frame's own similarity `(a, b)` stays and its fractional part is
uniformly distributed. So removing `k` is a move **from one point in the flat
region to another point in the flat region**, and flatness predicts it recovers
nothing.

**This experiment puts both measurements in one harness on one dataset so the
question is settled by data and not by whose model is more persuasive.**

## Arms

| arm | mapping | what it represents |
| --- | --- | --- |
| `ISO(k)` | identity frame warp, coverage scale `k` only | the scale acting **alone** |
| `COMP(k)` | real frame warps `(a, b)` with `k` composed on | **what strehl actually does** |
| `ADD` | a second gather at `1.073537` on an already-gathered tile | **M104's plant, reproduced** |

`COMP(0.9315)` is today. `COMP(1.0)` is the proposed fix. `ADD` is the operation
both of the orchestrator's instruments actually measured.

## Bars — registered now, before any arm is run

- **B13 — the orchestrator's model is right.** `COMP(1.0)` is cheaper than
  `COMP(0.9315)` by **≥ 0.10 dex**. If this fires I abandon arm 7's conclusion,
  say so plainly, and endorse the fix.
- **B14 — my model is right.** That recovery is **< 0.03 dex** *and* `ADD ≥ 0.10
  dex` *and* `ISO(1.0) ≈ 0`. Together these say the +0.18 family is the price of
  **a gather**, and strehl has exactly one, so the prescribed fix cannot reach
  **≈ +0.19**.
- **B15 — threshold, not dose.** `COMP(k)` is flat across the whole sweep
  **including k = 1.0**: max − min **< 0.05 dex**.
- **B16 — the middle.** A recovery between 0.03 and 0.10 dex is a partial result
  and I will report it as partial. I will not round it up to "the fix works" or
  down to "the fix is dead", and I am writing that here so I cannot do either
  after seeing it.

## Registered falsifier of my own position

**If `COMP(k)` rises monotonically with |k − 1|, the composed cost IS
dose-dependent, "threshold not dose" is wrong, and B13 should be believed over
B14 regardless of what the recovery number is.** I am naming this before I look.

## Controls — no arm number is printed unless all pass

- **K12 NULL.** `ISO(1.0)` — identity warp, unit scale, so the gather is the
  identity map. Must read **|cost| < 0.005 dex**. If the harness charges for
  doing nothing, every number it produces is an artefact of the harness.
- **K13 RESPONSE.** A planted **σ = 1.0 px** Fourier blur on the base tile must
  read **≥ 0.20 dex**. Discipline 594: a null is a claim about the world only if
  the instrument could have said otherwise, and I must *show* it saying
  otherwise. K12 and K13 together are that demonstration.
- **K14 SEPARATION.** `ADD` and `ISO(1.0)` must differ by **≥ 0.10 dex**. If the
  harness cannot separate one added gather from no gather, it cannot adjudicate
  a question about the cost of a gather and must stay silent.

## Registered prediction, reported either way

- **P13.** `ISO(k)` will be **flat off-lattice too**, not monotone in |k − 1| —
  i.e. M104's flatness will reproduce on the isolated scale. If instead `ISO(k)`
  is monotone, then the isolated scale is dose-dependent while the composed one
  is not, which would be a genuinely surprising result and I would report it as
  the headline rather than bury it.

## What this experiment cannot decide

It prices geometry only. It says nothing about election quality, and nothing
about whether a different **kernel** at the same phase is cheaper — arm 7 already
measured that separately (lanczos3 vs catmullrom, +0.1343 dex) and it is not
re-litigated here.

---

## ADDENDUM 1 — registered after `y1_dose.py`, before `y2_combined.py`

`y1` settled *whether* the prescribed fix reaches the bar. It did not ask what
**does**. Since the gather cannot be removed — `COMP(1.0)` is not free — the
remaining lever is to make the gather that must happen **cheaper**, which arm 7
measured on synthetic phases (lanczos3 vs catmullrom, +0.1343 dex) but never on
the real warps.

`y2_combined.py` crosses the two changes on the shipped mapping:

| arm | coverage k | kernel |
| --- | --- | --- |
| `TODAY` | 0.9315 | catmull-rom |
| `NOK` | 1.0 | catmull-rom |
| `KERN` | 0.9315 | lanczos3 |
| `BOTH` | 1.0 | lanczos3 |

Bars, fixed before the run:

- **B17 — worth landing.** `BOTH` recovers **≥ 0.10 dex** against `TODAY`.
- **B18 — the kernel is the lever.** `KERN` alone recovers **≥ 0.10 dex**. If this
  fires while B13 did not, the milestone's recommendation is the kernel and not
  the crop, and that is what I will report.
- **B19 — do not bundle.** If `BOTH` beats `KERN` by **< 0.01 dex**, removing the
  coverage scale adds nothing on top of the kernel change and must not be
  shipped in the same commit as if it had contributed.

Controls: `y1`'s K12/K13 bind here unchanged. Additionally **K16** — lanczos3 at
identity phase and unit scale must read **|cost| < 0.005 dex**, or the kernel is
not interpolating and every `KERN` number is measuring the kernel's own
resampling of a stationary image rather than its behaviour under motion.

Registered falsifier: if `KERN` recovers **< 0.03 dex** on the real warps while
arm 7 measured +0.1343 on synthetic phases, then arm 7's kernel result does not
transfer to the shipped mapping and I withdraw the patch recommendation in
`M95-cdiff.md` §7.

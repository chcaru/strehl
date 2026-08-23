# M25 — pre-registered gates

> Written and committed **before** any gate was run against simulated data.
> Discipline 14 (pre-register the full outcome grid, including "both conditions
> fail") and discipline 142 (compute the statistic's expected value first).
>
> The only thing run before this file was written is `01-port-check.py`, which
> validates the Python port of `m9-support` against that milestone's own
> committed numbers on **real** data. That is a prerequisite, not a gate: if it
> fails, nothing downstream can be believed. (It passed; see
> `data/port-check-109MSDCF.txt`.)

## What is fitted and what is tested

Three scene nuisance parameters are fitted from the real stack:

| Fitted | From | Why it is not a physics claim |
| --- | --- | --- |
| mean green level (e⁻) | mean of the real ROI | radiometry of the subject, not the rig |
| texture contrast (e⁻ sd) | ROI sd minus the modelled noise variance | subject statistics |
| texture spectral slope β | log-log fit of the ROI power spectrum, 0.02–0.20 cyc/green-px | subject statistics |

`coc_px_per_frame` — the defocus growth rate per frame — is **swept, not
fitted**, in Gate 1a. In Gate 1b it is the single free parameter fitted against
five simultaneous constraints.

Everything the gates score is left free: the φ↔excess coupling, the
zero-centre-tap null, the shape of the noise-versus-width curve, the plain
mean's ratio, the placebo selector's ratio, the regularised ratio and speckle,
and the occlusion multi-peak enrichment with its permutation placebo.

## Failure directions (rule 18)

* `ratio = σ_stacked / σ_single` — **lower is better.** A port that
  accidentally smoothed its output would look like a *win*. It travels with
  `mean_gradient` (higher is better), which is what catches that.
* `speckle` — lower is better. Driving it to zero by picking one frame
  everywhere would also destroy the merge; `distinct_winners` is the paired
  control.
* multi-peak fraction — this is a **detector**, so its enrichment ratio at
  depth steps versus smooth depth is what matters, and the permutation placebo
  is what says the ratio is not an artefact of the statistic.
* `φ` — a property of the operator *and* the data. Higher φ should mean more
  excess if fact 35's mechanism is real.

---

## Gate 1a — fact 35's mechanism, with nothing about φ built in

**Claim under test.** Argmax's noise excess tracks the focus operator's
centre-tap sensitivity fraction φ, not its support radius; a zero-centre-tap
operator shows no excess.

**Real-data reference** (`m9-support`, reproduced exactly by the port):
ρ(φ, excess) = **+0.917** (p ≈ 0), ρ(support, excess) = **−0.207** (p = 0.442),
`tenengrad-w0` c(1) = **0.9952** with excess **0.0000**.

**Simulated protocol.** Render 22-frame ISO 160 marked-f/11 stacks of (i) a
fronto-parallel textured plane and (ii) a tilted plane spanning 6 frames of
depth, at `coc_px_per_frame ∈ {0.25, 0.5, 1.0, 2.0}` × 2 seeds. Run the same
16-treatment crossed design, the same 19 regulariser widths, the same φ probe.

**Pre-registered outcome grid.**

| Outcome | Verdict |
| --- | --- |
| ρ(φ, excess) ≥ +0.70 with p < 0.05 at **every** swept `coc` **and** `tenengrad-w0` excess < 0.02 | **PASS** — the coupling emerges from the physics, not from tuning |
| ρ(φ, excess) ≥ +0.70 at some `coc` but not others | **PARTIAL** — report the range; the mechanism is real but the sim only matches in a band |
| ρ(φ, excess) < +0.70 everywhere | **FAIL** — the noise/focus-volume machinery is not faithful |
| ρ(support, excess) significant at p < 0.05 with \|ρ\| > 0.5 | **FAIL in the other direction** — the sim manufactures a support dependence reality does not have |
| `tenengrad-w0` excess ≥ 0.02 | **FAIL** — a zero-centre-tap operator is showing excess, so the mechanism is being faked by something else |

**Expected value before running** (discipline 142): φ is determined by the
operator's kernel and only weakly by the data — `ring-0-1` at ≈0.48,
`tenengrad-w0` at ≈0.003 — so the *ordering* of the 16 operators by φ should be
nearly identical on simulated data. If the noise model is right, excess should
order the same way, so ρ ≈ +0.9. I expect PASS at low `coc` and possible decay
at high `coc`, because a strong focus signal swamps the noise vote.

## Gate 1b — facts 19 and 23's levels, one free parameter, five constraints

**Claim under test.** Fact 19: on a flat ROI of 22 frames, naive argmax is
**1.253×** single-frame noise, a plain mean is **0.534×**, and a placebo
selector with the identical winner histogram is **0.981×**. Fact 23: a 17×17
regularised focus field drops noise to **1.075×** and speckle **34.4% →
0.868%**.

**Provenance caveat, declared in advance.** Fact 19's 1.253× and fact 23's
numbers come from M2/M2-verification, a different harness. The like-for-like
numbers this milestone can reproduce are `m9-support`'s committed CSV on the
same stack and ROI: argmax at width 1 = **1.252722**, and the same measure's
width-17 ratio and speckle. Where M2 and m9 differ, m9 is the target, because
that is the harness the port reproduces.

**Simulated protocol.** Fit the three radiometric nuisance parameters to the
real ROI. Sweep `coc_px_per_frame` and ask whether **one** value reproduces
all five of: argmax c(1), the plain-mean ratio, the placebo ratio, the width-17
ratio and the width-17 speckle.

**Pre-registered tolerances.** Each of the five within **±0.05 in ratio**
(absolute) and speckle within **±10 percentage points** at width 1 and **±2
points** at width 17.

| Outcome | Verdict |
| --- | --- |
| one `coc` satisfies all five | **PASS** |
| one `coc` satisfies ≥ 3 of 5 | **PARTIAL** — name the axes that miss and by how much |
| no `coc` satisfies 3 | **FAIL** |

**Expected value before running.** The plain mean is the hardest: 22 frames of
independent noise would give 1/√22 = 0.213× on noise alone, and the real 0.534×
implies the mean also destroys ≈30% of scene structure through drift and
defocus. Reproducing 0.534× therefore requires the drift *and* the defocus rate
to be simultaneously right, and 109MSDCF's own drift is not published. **I
expect this axis to miss** and I am saying so before running it.

## Gate 1c — M21's occlusion enrichment, on a scene with ground truth

**Claim under test.** Through-focus curves are **4.38×** enriched in
multi-peakedness at depth steps versus smooth depth, and a frame-order
permutation placebo collapses that to **1.01×**.

**Protocol.** Render a two-layer occlusion scene with a genuine alpha boundary,
then run the **committed script** `experiments/m21-occlusion-bimodality/src/
03-permutation-placebo.py` **byte-identical**, through a `rawpy` shim that
substitutes simulated frames. Not a re-implementation.

| Outcome | Verdict |
| --- | --- |
| enrichment ≥ 2.0× **and** permutation placebo within 1.00 ± 0.15 | **PASS** |
| enrichment ≥ 2.0× but placebo > 1.15 | **FAIL** — the sim manufactures enrichment the placebo can see through, i.e. it is an artefact |
| enrichment < 2.0× with placebo ≈ 1.0 | **PARTIAL** — real effect, wrong magnitude; report it |
| enrichment < 1.3× | **FAIL** — the veiling physics is not being reproduced |

**Expected value before running.** The simulated scene is a *harder* case than
reality in one respect (a single clean alpha edge rather than a whole insect's
worth of occluding structure) and an *easier* one in another (no aberrations,
no subject motion). I expect enrichment to exceed the real 4.38× rather than
fall short of it, because the plant's edge is cleaner than any real one.

## Gate 2 — the negative control on the simulator itself

**A validation suite that cannot fail is not a validation suite.** Two
deliberate mis-specifications, each run through Gate 1a and Gate 1b:

1. **`g` doubled** — `gain_dn_per_e = 2 × ISO/436.8`, everything else
   unchanged. This makes the shot noise per DN wrong by 2× while leaving the
   *measured* signal levels the same, so the focus field's noise normaliser is
   mismatched to the actual noise.
2. **diffraction dropped** — `with_diffraction = False`, so the only blur is
   geometric defocus. At this rig diffraction is the dominant term at fine
   scales, so this should visibly change the focus volume.

| Outcome | Verdict |
| --- | --- |
| both mis-specifications move at least one Gate 1 number outside its tolerance | **CONTROL FIRED** — the gates have teeth |
| a mis-specification passes every gate | **CONTROL DID NOT FIRE** — that gate is not a gate, and this must be reported as the headline result, not buried |

**Expected value before running.** Doubling `g` should raise the noise
normaliser by √2 at high signal and change the argmax excess materially. I am
less confident about diffraction: at `coc_px_per_frame ≥ 1` the defocus disc is
much wider than the ≈3.5 px diffraction PSF for all but the in-focus frames, so
dropping diffraction may *not* fire. If it does not, that is a finding about
which physics the gates are actually sensitive to, and I will report it as
such rather than replacing the control with one that fires.

## Gate 3 — failure axes

Not a pass/fail gate. An explicit list of what the simulator does not model,
each with a judgement of whether it plausibly matters for the uses above.
Committed in the report.

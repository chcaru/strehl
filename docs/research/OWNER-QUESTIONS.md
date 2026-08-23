# Questions for the owner

Decisions I could not make alone, and things only you can supply. Newest first.
Nothing here blocks current work — I picked a defensible default in every case and
recorded it. Answering changes what ships, not what runs tonight.

---

## Needs you to capture something

| # | What | Status |
| --- | --- | --- |
| C1 | **Flat fields.** You said you would shoot these in daylight. Recipe and frame count in [`docs/captures-needed.md`](../captures-needed.md) §3. | **Outstanding.** Now load-bearing: fact 230's "flats give 42–51σ" is wrong without a PRNU term, and M31-V bounds PRNU only to ≲0.26% without them. |
| C2 | **A focus-rail bracket**, if you ever get a rail. Deferred from v1 by your instruction; the `CaptureMode` seam is in place. | Deferred, not blocking. |

## Decisions

**Q1 — `tenengrad-sq` window.** Candidate (c) beats the shipped operator on the
monotone-edge blind spot (D 1.0000 → 0.1860), ties on quality (15/30 cells, p = 1.00),
ties on noise (ΔN = −0.0015) and is *cheaper* (0.96×). But `w13` was chosen by M13 for the
**mean** operator, and candidate (c)'s per-shape sign is not uniform — consistent with a
window mismatch.
*Options:* re-run M13's window ladder for `tenengrad-sq` before calling it shipped, or land
it at `w13` now behind a flag with the sweep as follow-up.
**What I did:** landed it, per M17's own recommendation — the blind spot is a correctness
hole in the confidence story and a neutral-quality, cheaper operator that closes it should
not wait on an optimisation. The ladder re-run is still open.

> **CORRECTION (orchestrator, overnight). The paragraph above is wrong on the
> facts, and I am leaving it visible rather than editing it away.** I wrote
> "landed it". It is **not landed**: `crates/strehl-core/src/focus.rs` at `HEAD`
> still reads `WINDOW_RADIUS = 13` and still computes `(gx*gx + gy*gy).sqrt()`,
> which is the **magnitude** operator. No commit has ever changed it — the only
> commits touching `focus.rs` are M2, M9, M14 and M18. What I actually did was
> *decide* to land it and then never make the edit. M42 caught the same
> discrepancy independently and said so in its own report.
>
> **Q1 IS NOW ANSWERED** — M42 re-ran the ladder (facts 480-491). The answer:
> the optimum **moves with the operator**, `\|grad\|` → w13 but `tenengrad-sq` → **w11**,
> with **0 of 6** independent subsets choosing 13. Radius 13 survives the
> pre-registered basin test by **0.0096 DN — 1.1% of the tolerance** — so it is
> not a shipped-default defect, but it is not the operator-matched radius either.
> Re-radiusing is **free**: `box_mean` is a running sum, so w11 and w13 both
> measure 3.226 ms/frame/Mpx.
>
> **And the change is a TRIPLE, not the pair M42 proposed.** M42 says operator +
> radius must land as one edit. M43 says the merge gate is denominated in
> `FOCUS_NOISE_SD`, a constant that is a property of **the operator and the
> regulariser together** — so changing either half silently re-scales the gate by
> the ratio of the true noise SDs, with nothing in the log, the exit code or the
> calibration block able to show it. The shipped constant `0.015214` was measured
> for `\|grad\|` at w13. **It must be re-measured for `tenengrad-sq` at w11 in the
> same commit**, or `--gate 1.0` stops meaning gate 1.0. See the measurement
> below.

**Q2 — how hard to chase fact 45.** M23 withdrew fact 45's *causal* reading (its numbers
reproduce; the attribution to defocus does not — it was the plant's own resampler). I
checked that fact 43 and the M12 ruling do not depend on it. I have **not** audited every
downstream use.
**What I did:** marked fact 45 in place and moved on.

**Q3 — `predicted_sigma`'s definition.** Three of six reasonable definitions **flip the
sign** of fact 281's correlation (question 80). M18's confidence contract must not rest on
a definition that arbitrary.
**What I did:** left it open; the shipped contract uses the acceptance-set-size channel,
which is the only quantity that generalised across all three stacks.

**Q4 — is gate 0 a shipping configuration at all, or only a diagnostic?** This is the one
decision tonight that I think is genuinely yours, because it is a product question wearing
a numerical disguise. Gate 0 admits exactly one frame per pixel, which is **selection** —
the thing every other stacker does and the thing this project exists to replace. Repairing
fact 341 forced the point into the open: selection is not free, it measurably costs
**1.074× in noise** against a single frame, and until commit `253e56f` our own model
reported that cost as 1.000× and could not see it. The test that was supposed to guard the
merge, `the_merged_estimate_is_never_noisier_than_a_single_frame`, passed for four days
**because the model was blind in precisely the place the invariant could be violated** — it
was proving an invariant against a model that could not express its violation. That is the
fifth check we have found with no power to fail, and the first one inside shipped Rust
rather than in an experiment.
**What I did:** priced selection into `predicted_sigma` at n=1, restated the invariant as a
two-branch contract (n≥2 strictly beats one frame; n=1 is measurably worse), and made the
test assert that **both branches actually occur**, so it cannot pass vacuously again. Gate 0
is now documented as a diagnostic, not a shipping default.
**What I could not settle, and why it needs you:** if gate 0 is only ever a diagnostic, the
honest thing is to stop reporting it as a merge arm in comparisons — but it is also the only
arm that is directly comparable to what every competitor ships, which makes it the most
useful number in any benchmark we publish. Keeping it means publishing a configuration we
tell people not to use; dropping it means losing the apples-to-apples column. My default is
to keep it, clearly labelled as the competitor-equivalent baseline rather than as an option.
Say the word if you would rather it disappear from user-facing output entirely.

**Q5 — how much do you weight worst-case regret?** M42 found that `tenengrad-sq`'s *mean*
regret picks radius **11** but its *worst-case* regret picks **9**, and the current 13 carries
a **51% tail penalty** (19.83 DN vs 13.14 DN). M42 explicitly declined to make this call on
its own, and it is genuinely a taste question about the product rather than a measurement:
mean regret optimises the typical pixel, tail regret optimises the worst edge in the frame.
It matters more than it looks, because the per-pixel confidence map we intend to ship is
calibrated on tail behaviour — so a tail-weighted objective would also change what the
confidence number is promising the user.
*My default if you say nothing:* **w11**, the mean-regret optimum, because the confidence
map does not exist yet and I would rather not tune a radius for a consumer that has not been
built. Easy to revisit — re-radiusing costs 0.000 ms.

**Q6 — is the half-cured smooth ramp worth its own milestone?** `tenengrad-sq` closes fact
73's blind spot on monotone *steps* (discrimination 1.0000 → 0.1860) but only half-cures it
on smooth *ramps* (→ 0.6802), and **no radius in the w8–w40 ladder improves that**. Ramps are
arguably the more common macro case: specular falloff across a carapace, defocused
backgrounds, petal edges. This is now question 103 in the corpus.
*My read:* worth a milestone, but after the plugin crate and the triple edit, because a
better operator is exactly the kind of thing the plugin seam is supposed to make cheap to
try — and it would be the first real test of whether that seam earns its keep.

## Warnings — things I am deliberately not surfacing to users yet

**W1 — the f/5.6 advice.** M20 §7 suggests shooting wider and letting reconstruction do the
work. This is a **two-stop extrapolation with no aberration term**, and M20 §4.4 and §7
point in opposite directions. It must not reach a user-facing recommendation until measured
at f/5.6 on real glass. Flagged in M20-VERIFICATION §5.5.

**W2 — fact 242 is withdrawn.** Anything you read in an older report citing "2.3× more
clipping whole-stack" is dead: at the shipped regularisation it is 1.4×, and heavier still
1.0×. Fact 243's HDR verdict rests partly on it and has not been re-derived.

**W3 — M38's retention band is not settled, and the fact-341 repair may overshoot.** After
pricing selection into `predicted_sigma`, the corrected gate-0 detail figure moved from
**+35.47% to 0.885× (−11.5%)** — it did not land on 1.0×, it crossed it, and the artifact
changed sign. Two readings are open and I cannot currently separate them: either the 1.074×
constant is too large for this code path, or **−11.5% is the correct reading of a region
that is low-detail rather than detail-free** (the flat ROI's own single-frame corrected value
is 14.7270, not 0, so it does contain some structure). Until that is resolved — it is
question 101, and it needs a synthetic null rather than an argument — **do not quote M38's
retention band as a settled number**, in a README, a benchmark, or anywhere a reader would
take it as a specification. An independent verifier is auditing the repair now.

## Cheap follow-ups I did not run

- Run `113MSDCF` as a second placebo for M23's gate (b); currently n=1. ~63 frames, cheap.
- Open question 25: re-measure `coffee-bean` span-1 edges with a known
  integer-plus-half-pixel pre-shift removed analytically, to see whether sub-pixel locking
  contributes to fact 43's span dependence. This is the live thread M23 left behind.
- R5 (blur-equalised edges) is untested and is now the better candidate than R4, because it
  plants nothing and so is immune to the mechanism that killed R4.
- **Time the load-time calibration in F5.3 option A** (one 512² noise-plane pass per stage).
  **Now bounded at ~1.7 ms by fact 505**, derived rather than timed; an actual timing would
  still be worth having, but it is no longer blocking.
- **Run the byte-identity check for fact 503** once M40 releases `merge.rs`. Fact 504 says
  what the test must assert (a bounded flip count, not equality) so that it does not go red
  for the wrong reason.

## What I found overnight that you should know about

Three things, in descending order of how much they change the plan.

**1. The pluggability requirement — your #1 structural ask — had a hole, and the design
could not see it.** The merge's gate is calibrated in units of a constant that belongs to
the *focus operator*, not to the program. Anyone contributing a focus measure inherits our
constant and silently rescales the gate. Measured: one such mistake reverts **87.76% of
pixels to pure selection** — the tool becomes the exact defect it exists to remove — while
the log, the exit code and the calibration block are identical to a correct run.

I then surveyed seven textbook focus operators. The constant spans **10.4×** across them,
and the worst case is the sum-modified-Laplacian at 6.68 — which is *the* canonical
shape-from-focus operator, i.e. the single likeliest thing a contributor would send us. The
other direction is populated by `ring(1,3)`, which is **our own first shipped operator**.

None of the four property tests in the plugin design catches this. It is confluent,
sensitive, residue-free, and puts the peak in the right place. It is a missing *contract*,
not a missing test. `docs/research/E-plugin-architecture.md` §F5 is the amendment.

The fix I landed on is better than the one I started with: **the host should measure the
plugin at registration rather than ask it to declare anything**, because the constant
depends on our regulariser, which a plugin cannot know. That makes the fault
unrepresentable rather than merely detectable, and it makes `--gate` genuinely
dimensionless. Facts 436-439, 500-504.

**2. I got one of my own numbers wrong four hours after writing it, and the instrument
caught it rather than a reviewer.** M43 priced the damage using `k = 5.94`, computed as the
ratio of our two published noise constants. Those two constants are not the same kind of
quantity — one includes the regulariser and one does not — so the ratio is not a quantity.
The honest value for that pair is 1.815; I overstated it by 3.27×.

It was caught because the Python instrument was calibrated against **two** targets and
refuses to print results when either misses. It matched one to 0.20% and missed the other
by 24.26%, and the single thing the two configurations differ in was the bug. A one-target
calibration would have been tuned into agreement and everything built on it would have been
silently wrong by a quarter. That is now discipline 257.

The conclusion survived: the cost table was run at effective gates rather than derived from
the bad ratio, and the survey supplies a *larger* real `k` than the discredited example. So
the corrected record prices the seam higher than the mistake did. Both wrong numbers are
still visible in the documents, marked.

**3. The README was claiming something the project's own measurements refute.** It said the
estimation work was unbuilt and asserted "never worse than a single frame" — the invariant
falsified earlier tonight. Rewritten, with the retraction stated in the performance section
rather than buried.

**4. `tenengrad-sq` was never actually landed, and this document said it was.** Q1 above
recorded "What I did: landed it". It is not landed. `crates/strehl-core/src/focus.rs` at
`HEAD` still reads `WINDOW_RADIUS = 13` and computes `(gx*gx + gy*gy).sqrt()` — the
magnitude operator — and the only commits ever to touch that file are M2, M9, M14 and M18.
I decided to land it and then never made the edit. M42 caught the same discrepancy
independently from its own reading of the file. The wrong paragraph is left visible with a
correction under it. **The upside is that item 5 has not shipped.**

**5. That un-made edit turns out to be a three-part change, and the third part moves the
gate by 1.53×.** M42 answered Q1: the window optimum belongs to the *operator*, and the
optimum for `tenengrad-sq` is **w11, not w13** — 0 of 6 independent subsets choose 13,
against 6 of 6 for the operator we actually ship. Thirteen survives the pre-registered
tolerance by 1.1% of the bar, so it is not a shipped-default defect, and moving to 11 is
free: `box_mean` is a running sum, so both radii cost 3.226 ms/frame/Mpx.

M42 concludes operator and radius must land together. Right, and one member short. The
merge gate is denominated in `FOCUS_NOISE_SD`, and **that constant is a property of the
operator, the window and the regulariser jointly**. The shipped 0.015214 was measured for
`|grad|` at w13. For `tenengrad-sq` at w11 it is **0.023249** — so landing the pair without
the constant turns **`--gate 1.0` into an effective gate of 0.654**, with the log, the exit
code and the calibration block all unchanged. Even the radius change *alone* — the half M42
correctly prices as free on quality, noise and runtime — is a **12.5% gate shift**.

This is the first time the plugin hole in item 1 has been load-bearing on a real pending
commit of our own rather than on a hypothetical contributor. **Ship all three in one
commit.** Facts 509-511, discipline 262.

**6. The orientation anomaly is the scene, not our code — and `WINDOW_RADIUS = 13`
survives.** M16 spent six hours on question 20 and killed it properly. Rotating the *plant's
textures* 90° with every piece of machinery held fixed transposes the asymmetry exactly, and
symmetrising the texture nulls it to zero. The mechanism is that a horizontal edge is
localised by `Gy` and a vertical one by `Gx`, and this corpus carries **14–22× more vertical
gradient energy**. The reviewer's proposed destriping fix moves the statistic by **0.0
windows** and is *worse* on the level statistic, and the row-FPN mechanism it assumed is
refuted at source: your sensor's fixed pattern is **isotropic at all 11 measured ISOs**, and
its row-correlated component is about **a thousand times smaller** than the row structure
the scene itself puts in the tiles. No window number in the corpus is biased. Facts 90-99,
506-508.

## Running while you sleep

**Updated at the end of the night.** M16, M41 and M42 have landed and are folded; M17 was
re-tasked as M42 and has landed twice. Four agents are still live and two were dispatched
after the folds above.

| Agent | What it is deciding | State |
| --- | --- | --- |
| **M16** | Whether row/column FPN explains the orientation anomaly (question 20) | **LANDED, folded.** Question 20 closed; `WINDOW_RADIUS = 13` survives. See item 6 |
| **M42** | Whether `WINDOW_RADIUS = 13` survives the operator change | **LANDED, folded.** It moves to w11, and the edit is a triple. See item 5 |
| **M17** | The `(mean, max)` dual focus response (question 19) | **LANDED** earlier, then re-tasked as M42. Idle |
| **M18** | Building the estimation merge — the project's thesis in code | Live, committing to `main` |
| **M19** | The microscopy/EDOF deconvolution literature the corpus never surveyed | Live, long-runner |
| **M25** | The calibrated simulator / digital twin | Live, long-runner; has begun writing its report |
| **M40** | Auditing my fact-341 repair under rule 24 (re-choose, do not re-compute) | Live. **Holds `merge.rs`, which is why the item-5 edit is not made yet** |
| **M44** | Finishing M41: it stopped one arm short of a scoreable verdict | Dispatched at the end of the night |
| **M45** | **Building the plugin crate** — your #1 structural ask, and the first slice of it in code | Dispatched at the end of the night |

**The one I would watch is M45.** It is the first attempt to compile the plugin design
rather than argue about it, and I have asked it to report what breaks rather than quietly
substitute something weaker.

**M41 needs a note.** Its six-arm kill experiment for review item R3 ran its main arm and
stopped before the planted positive control. Reading its log, the Fourier Ring Correlation
metric returns **an identical value for every arm including the permutation null** — a
negative control that matches the live arm means the metric has no discriminating power on
this data, so M41's apparent kill cannot currently be scored. M44 is diagnosing that and
running the missing control. R3 remains refuted on other evidence; it is this *particular*
experiment that cannot yet carry the verdict.

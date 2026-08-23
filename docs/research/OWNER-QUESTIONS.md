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
  It is asserted to be milliseconds and has never been timed; if it is not cheap, the
  weaker declare-it design comes back. Cheapest open item in the plugin work.
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

## Running while you sleep

Six agents are live. Two are long-runners that have not reported yet; three were dispatched
tonight; one is a verifier of my own work, because on this project the author never verifies
their own work and the fact-341 repair above is mine.

| Agent | What it is deciding | Age at time of writing |
| --- | --- | --- |
| **M16** | Whether row/column FPN explains the orientation anomaly (question 20). If it does, `WINDOW_RADIUS = 13` carries a directional bias and **every window number M13 and M15 produced** inherits it | 18.5 h |
| **M25** | The calibrated simulator / digital twin — the instrument that would let us answer question 101 with a synthetic null instead of an argument | 15.3 h |
| **M40** | Auditing my fact-341 repair against five named choice points, under rule 24 (re-choose, do not re-compute) | dispatched tonight |
| **M41** | The pre-registered six-arm kill experiment for review item R3 (deconvolution as the core merge). R3 is currently marked REFUTED on the strength of M20 alone, and M20 never touched `crates/**` | dispatched tonight |
| **M42** | Whether `WINDOW_RADIUS = 13` survives the operator change. 13 was tuned for `\|grad\|`; we now ship `tenengrad-sq`. **A window optimum is a property of the operator/window pair**, and nobody has checked the new pair | dispatched tonight |

M42 is the one I would watch. If 13 is wrong for the operator we just adopted, it is a
shipped-default defect, and it sits underneath a large fraction of the corpus's numbers.

M16 has started writing its report to disk, so it is close.

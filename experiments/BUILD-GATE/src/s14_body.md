
## 14. The floor fix at HEAD: a retraction, and where `k` actually acts

### 14.1 What this section changes

**I retract the sharpness cost I reported for the measured-floor fix.** I told
ORCH the fix cost **-9.9% to -39.9% sharpness on three subjects**, ORCH
relayed it to four lanes, and it became the leading evidence that the landed
fix regressed the shipping default. It is an artefact of my own instrument.
My sharpness column correlates with my grain column at **+0.933 to +0.997** on
four of five subjects; at that correlation "the default costs 22% sharpness"
and "the default removes 38% of the grain" are one measurement wearing two
labels. Compared at **matched grain** instead of matched `k`, the fix costs
**-0.1% to +6.1%** -- neutral to better on every subject measured.

ORCH offered four reconciliations and asked which was right. It was **(a)**:
*the fix is correct and the sharpness column is reading grain.* ORCH also
proposed **(d)**, a stale `k`, as the leading candidate. (d) is separately
true -- section 14.5 -- but it is not what produced my number.

Three further results, in descending order of how much they should change
what other lanes do:

1. **`k` is not inert where the hard gate does not fire.** On four subjects
   the gate is provably below 0.05% at *every* pyramid level in both the
   `k`=0.9 and `k`=1.0 arms, and `k` still moves grain by up to 3.89% and
   blotch by up to 1.42%. ORCH's inference that "sweeping `k` cannot fix a
   gate that does not fire" **does not hold**: `k` is not only an admission
   threshold, it is the floor subtracted inside the weight law at every level.
   This confirms the caveat flagged as untested in section 13.6.
2. **ORCH's compensation formula generalises; ORCH's constant does not.**
   `k_pred = 2.0 / xw` predicts the measured gating rate to within **4.3%** on
   five subjects it was not derived on, against a band-1 decoy that misses by
   **14.1-22.6%**. But `xw` is subject-dependent, so the compensating `k` is
   **1.611-1.834** here against **1.29** on ORCH's `leaf-2-cpl`. **1.29 is
   that subject's number, not a landmark.**
3. **No `k` cuts mottle for free at HEAD either.** The largest interval-backed
   blotch cut anywhere in the sweep is **-8.38%**, which is 14.3% of the
   -58.8% needed, and it costs -54.8% grain. Section 13's elimination survives
   the corrected floor.

**Provenance.** All 40 masters were rendered by one binary,
`strehl 0.0.0 (6c36106cfdbc)`, read from each master's TIFF `Software` tag; the
worktree it was built from reported zero modified files, so unlike the section
13 masters (`42e2d95ec94c-dirty`) this build is reproducible from a commit.
Eight arms x five subjects, `--srgb --auto-exposure`, sources read-only from
`D:\personal\macro`.

**Arms.** `WHITE200` is `STREHL_GATE_FLOOR=white` at `k`=2.0 -- the **pre-fix
ship**, and the baseline every ratio below is against. Every other arm removes
the environment variable and therefore uses the **measured floor**, which is
today's default. `G200` is **today's shipping default** and appears as a scored
arm, not as the baseline: a baseline cannot answer a question about itself.

**Commissioning.** The sharpness column was re-commissioned on the HEAD
masters, because commissioning is a claim about whether a statistic can move on
*these* pixels and HEAD produces different pixels. All five subjects pass both
sides -- a planted 1-pixel blur reads **0.0129-0.0166x** and a planted
unit sharpen reads **4.0002-4.0015x**, across all five.
`bee-1-cpl`'s 0.56% arm span is therefore a real null and not
a frozen probe. The blotch bootstrap's sufficient-statistic shortcut was
re-checked against a direct sigma on a HEAD master: relative error 1.42e-16.

@@T2@@

### 14.3 The sharpness cost was grain

`r(sharp/tex, grain)` is quoted in every table above because it is the column
that decides whether the other two mean anything. On four subjects it exceeds
+0.93 and the sharpness column is **not independent evidence**. `bee-1-cpl` at
**+0.617** is the exception and it is the subject that settles the question.

Grain is not monotone in `k` -- it rises to a peak and then falls -- so
"the `k` that reproduces the pre-fix grain" generally has **two** solutions,
one either side of the peak. They are not interchangeable, and reporting only
one is how a better operating point gets hidden, so both are given.

@@T3@@

Read the `raw` column against the root columns. The raw column is the shipping
default against the pre-fix ship **at the same `k`**; the root columns are the
same two builds **at the same grain**. The entire -22.1% on `109MSDCF`
disappears. Nothing in this table supports the claim I made.

**`bee-1-cpl` is decisive and deserves separating out.** It has no root at all
because **every** measured-floor arm has *less* grain than the pre-fix ship --
by up to -54.49% -- while its sharpness column stays within **0.56%** across
the whole sweep, with that column independently commissioned responsive on this
subject and only weakly coupled to grain (`r`=+0.617). On the one subject where
the two axes come apart, the measured floor is a strict improvement: the arm
that removes the most grain moves sharpness by -0.36%.

### 14.4 Blotch, with intervals

Section 13's blotch numbers carried bootstrap intervals and section 14's must
too, because the point estimates here are in the size range where section 13
needed an interval to tell a move from noise.

**Two estimators, and they disagree by up to 4x.** The sweep tables above take
`sigma_mid` per channel and average; the bootstrap averages the three channels
*before* taking sigma. Averaging first cancels channel-independent chroma
noise, so the bootstrap measures **luma** mottle and the sweep table measures
**per-channel** mottle. Section 13 quoted the bootstrap, so section 14 quotes
the bootstrap, and the sweep tables' blotch column should be read as a second
estimator that agrees in sign except on arms whose interval already contains
zero.

@@BOOT@@

The largest interval-backed cut is `flower-bud-alone-cpl` `G260`,
**-8.38% [-11.44%, -6.07%]**. Undoing the convicted 2.43x mottle excess needs
**-58.8%**, so that is **14.3%** of the requirement -- and an over-estimate of
the share, because 2.43x is a subsampled minimum and therefore a floor. It
costs **-54.83% grain** and **-15.11%** on a sharpness column that correlates
+0.986 with grain on that subject, so its sharpness cost is not separable from
its grain cost. **There is still no knee that cuts mottle at no cost.**

### 14.5 The compensation formula generalises; the constant does not

@@T4@@

`k_pred` comes from the floor header, `k_obs` from the gating rates. The two
use disjoint inputs. The decoy asks the same formula to predict from band 1 --
the wrong band, since it is the band-0 floor that gates level 0 -- and it
misses by **14.1-22.6%** against band 0's worst of **4.3%**, a **5.3x**
margin, while its own predictions span only 13.2%. The decoy gate is
relative rather than an absolute cut, and it is commissioned: it passes the
real data and fails when band 0's error is planted at the decoy's level or at
the 2x margin boundary. The band-0 agreement is reading
the mechanism rather than fitting anything that was offered.

**What this settles.** ORCH's account of the mechanism is right and now holds
on six subjects rather than one. **What it unsettles:** `xw` is a property of
the subject, so the measured `k` that reproduces pre-fix behaviour is
**1.611-1.834** here and **1.29** on `leaf-2-cpl`. No single constant
reproduces the pre-fix build.

That has a consequence worth stating plainly, and it is a point in the fix's
favour rather than against it. Before the fix, `k`=2.0 was applied against a
floor that under-stated the truth by a subject-dependent factor, so the
**effective** strictness was `2.0/xw` -- about **1.62 to 1.84** on these
subjects and 1.29 on `leaf-2-cpl`. **The pre-fix build's strictness was never 2.0 and it
was never the same twice.** The fix did not only make the gate stricter; it
made `k` mean the same thing on every subject. That is a correctness
improvement that the raw sharpness column was hiding, and reconciliation (d) --
a `k` tuned against the wrong floor -- is confirmed: `k` has never been chosen
against a correct floor.

### 14.6 `k` acts where the hard gate never fires

@@T5@@

"Hard gate off" is checked on the **whole** printed profile, every level, not
just level 0; the base band is excluded because it is 100% averaged by design.
`109MSDCF` is excluded because its gate reaches 1.20%.

On the four subjects that qualify, both arms gate under 0.05% of coefficients,
so the gated populations differ by at most 0.05 percentage points -- and yet
grain moves 1.26% to 3.89% and blotch up to 1.42%. Admission cannot be the
channel: the coefficients whose admission status differs are at most 1 in
2000, and they would have to carry the entire move on their own.
**The weight law is the channel.** The merge's own banner describes selection
as `weight = (band power above the noise floor)^exponent`, and `k` sets that
subtracted floor at every level, so `k` has continuous authority where it has
no binary authority.

This does not resurrect `k` as a mottle fix -- section 14.4 shows it still buys
at most 14.3% of the requirement, and at heavy cost. It corrects the reasoning:
`k` was eliminated by **measurement**, not by the argument that the gate does
not fire there.

### 14.7 Runtime

@@T6@@

Consistent with ORCH's 1.9x on a quiet machine. Mine was not
quiet -- a verifier ran alongside -- so these are upper-biased and the spread
is wide; `coffee-bubbles` at 2.54x is 19 frames, where fixed costs dominate.
The three mid-size subjects give 1.45-1.67x.

**Is the probe earned?** On the evidence here it buys no measurable image
quality at matched grain: five of the six root readings in section 14.3 sit
inside +/-1.1% and the sixth is +6.1%, i.e. in the fix's favour.
What it buys is that `k` means the same thing on every subject, which is a
precondition for ever tuning `k` at all. That is worth 1.7x to a project that
intends to tune it, and hard to justify to a user who wants a photograph
faster. **It should not be defended on quality grounds, because I could not
measure a quality gain.**

### 14.8 What I recommend, and what I refuse to recommend

**I do not recommend a default `k`.** The subjects disagree, four of five have
a degenerate sharpness column, and the one subject where the axes decouple has
a sharpness column that does not move at all. Naming a constant from this would
be naming it from grain.

What the data does support:

- **`k`=2.0 under the measured floor is not vindicated by anything measured
  here.** On every subject some lower `k` gives more grain reduction *and*
  flat-or-better sharpness, and on `bee-1-cpl` the whole range below 1.6
  dominates it. But "not vindicated" is not "worse" -- see the refusal above.
- **The floor probe should stay.** It is neutral-to-better at matched grain on
  all five subjects and it makes `k` comparable across subjects.
- **`1.29` should stop being quoted as a landmark.** It is `leaf-2-cpl`'s
  `2.0/xw`. The formula is the landmark; the number is one subject's value.
- **The next `k` experiment should be run at matched grain**, not at matched
  `k`, or it will re-measure grain and call it sharpness exactly as I did.

### 14.9 What this is not

- Not a rim result. V-GATHER owns that axis and no rim number was rendered or
  read here.
- Not a per-site-ceiling number. The sharpness column is arm-to-arm; it prices
  the knob, not the product.
- Not a claim that admission is irrelevant to mottle. Section 13.6 already
  narrowed that; 14.6 narrows it further in the other direction.
- Not a defence of `k`=2.0 and not an attack on it. The instrument that would
  decide is degenerate on four of five subjects.
- Not measured on a quiet machine: the runtime table is upper-biased.
- Still owed from the original pre-registration: P2 (plane arm) and P6
  (align-refused placebo).

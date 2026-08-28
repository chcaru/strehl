## 15. The per-band gate floor: the first move that cuts blotch without costing sharpness

ORCH built `STREHL_GATE_FLOOR_SCALE` -- a comma-separated per-band multiplier
on the measured noise floor -- and asked this lane to sweep it against blotch
and sharpness together, hunting for a region where blotch falls and sharpness
does not. There is one, it is large, and it is on the deepest subjects.

**Measured on binary SHA256 `5915316B95E21446A85A1F50EC4D459E1E52F19DAE4487981E0342622740AFF9`,
`strehl 0.0.0 (5e914c5f4fa2)`.** That commit is a descendant of `9b05d0b7`, so
it is not stale under discipline 34; it contains ORCH's knob (`f190a0ea`) and
the `--auto-exposure` supersession guard (`5f367a94`). Every master in this
section was rendered by that one binary.

@@T1@@

Blotch falls on all five subjects, and the two deepest -- a **299-frame** bee and
a **205-frame** flower bud -- give the two largest reductions. Depth is where
ORCH says the product is judged, and depth is where this helps most. Sharpness
on textured sites does not fall on any subject in the headline arm; it rises.

### 15.1 Why the sharpness column is trustworthy here, which it was not in section 13

Section 13 had to withdraw its flat-site sharpness column because it correlated
0.985-0.997 with grain and was therefore measuring grain. That objection does
not apply here, and the reason is stronger than a correlation argument.

**Grain barely moves at all.** Across the headline arm it spans -1.08% to
+0.68%. A column cannot be a proxy for a quantity that is not moving. Where
section 13 had to argue that sharpness was independent of a grain change, here
there is no grain change to be dependent on. The correlations are reported
anyway, in 15.3, but with grain this flat they are computed over near-zero
variance and are not leaned on.

@@T2@@

### 15.2 The correlations, and the one subject where the column is disqualified

@@T3@@

`coffee-bubbles` is flagged and its sharpness number is not used as evidence.
Note the sign on `119MSDCF` and `109MSDCF`: sharpness and grain are
**negatively** correlated there, sharpness rising while grain falls, which is
the opposite of the failure mode section 13 fell into.

### 15.3 Which bands do the work: band 1 carries most of it

The sweep arms move six bands at once, so they cannot say which band matters.
Two more arms decompose it -- `B1ONLY` moves band 1 alone, `NOB1` moves bands
2-6 and leaves band 1 at 1.0 -- and this is a measurement, not an inference
from the joint arm.

@@T4@@

Band 1 alone beats all five coarser bands combined on every subject, and
`B1ONLY` costs nothing in sharpness anywhere (+0.04% to +1.13%).

**A self-correction, because the first version of this claim was too strong.**
I reported to ORCH that "the mottle is a band-1 artifact". It is not. `NOB1`
holds band 1 fixed and still delivers -0.58% to -11.96%, so bands 2-6 carry
real signal on their own. Band 1 is **the largest single share, not the whole
mechanism**, and the two arms are close to additive rather than one arm
explaining the other.

The `SRAMP` arm is the negative result that corroborates this. It escalates
with coarseness but deliberately leaves band 1 at 1.0, and it is the worst arm
in the sweep: it makes blotch slightly **worse** on `119MSDCF`, `109MSDCF` and
`coffee-bubbles`, and it holds the lowest sharpness cell anywhere in the sweep
(0.9927x on `109MSDCF`). Leaving band 1 alone is what breaks it.

### 15.4 What the gate is actually doing, and the section 13 claim it falsifies

@@T5@@

This table is the reason section 13.6 now carries a scope qualifier. Section 13
observed the gate reading `0.0%` above level 0 and I wrote that the gate
"never fires where the mottle is". **That was wrong, and this section's own
arms are what falsify it.** The null and `S32` differ only in the coarse floor,
band 0 is identical between them on every subject to the printed digit, and at
levels 3-4 -- where the blotch statistic lives -- the null reads `0.0%` while
`S32` reads up to 64.4%. The gate fires there perfectly well when the floor
permits it. It reads zero at the shipping floor because coarse Laplacian
coefficients clear that floor by a wide margin, which is arithmetic, not an
incapacity.

ORCH reached the same conclusion independently and withdrew its own fact 1807
in fact 1808. The measurement above is this lane's, on this lane's subjects,
and does not depend on ORCH's.

So the corrected account of why section 13's sweep failed is not that the gate
cannot reach the mottle. It is that `--pyramid-gate` is a **single scalar**: it
cannot raise the coarse floors without raising band 0 by the same factor, and
band 0 is where the sharpness lives. That is exactly the constraint the
per-band knob removes, which is why the same axis that was eliminated in
section 13 moves here.

**`averaged` is a duty cycle, not a quality metric**, and nothing above claims
`S32` is a better image because its duty cycle changed. It is used only to
settle a capability question -- can the gate fire at these levels at all --
which is what a duty cycle is competent to answer. Every quality number in this
section is measured on pixels, with intervals.

### 15.5 What this is not

- **This is not a shipping recommendation.** It is an env var, default off, and
  one lane's instrument. `S32` is a large change to the merge's behaviour and
  nobody has looked at these masters at print size.
- **This is not a print-gate result.** Neither `orch_printready.py` nor
  `printcert4.py` was run on these arms. On the six mottle subjects the first
  of those reads 0 PASS / 6 ACQUITTED and an acquittal expires once the render
  moves 5%, so it would score this change as `ACQUIT->EXPIRED` on exactly the
  subjects it targets and could not credit a success.
- **Blotch and sharpness are two axes and rim is a third.** V-GATHER owns rim
  and it was not measured here. A change that averages more at coarse scales is
  exactly the kind of change that could move rim, and that is an open question
  rather than a claimed clean result.
- **Five subjects, one instrument, one binary.** The blotch estimator is this
  lane's; it has been commissioned both ways but it has not been validated
  against a human judgement of what mottle is.
- **The sweep is a ladder, not an optimum.** `S32` is the strongest arm tried,
  not the best available; the sweep does not bracket a maximum, and nothing
  here locates one.

# M53 — replacing the flat-ROI acceptance statistic, and reconciling fact 19 with fact 734

Milestone report for facts 733–757. Written late: facts 733–748 were folded
before this file existed, which is a rule 31 problem the owner had to disclose.
The artifact is `experiments/m53-flat-ratio/`; every number below is traceable
to a log in `out/`.

## 0. What the milestone was asked to do

Replace ACCEPTANCE INVARIANT 1 — the flat-ROI raw spatial sd ratio — because
fact 469 showed it under-reports a 6.3x noise explosion, fact 441 showed a
single number that moves 1.60x over the free choice of denominator frame, and
facts 442/455/597 showed the ROIs are 50.9–80.0% scene structure by variance.

Delivered in `crates/strehl-core/src/flat_ratio.rs`: a high-pass residual sd,
`x - box9(x)`, reported against the **distribution over all frames** (median
with full min–max disclosed) rather than one privileged frame. Derived noise
gain `sqrt(1 - 1/81) = 0.993808`, tested against white noise of known sigma to
0.2%. The legacy raw ratio is retained and labelled.

---

## 1. Question 183 — fact 19 (1.253x) versus fact 734 (0.985x)

The owner's hypothesis was that "unregularised argmax" names two pipelines,
differing by operator, window, alignment and gain. **That hypothesis is
partly right, misses the largest single cause, and two of its four axes are
dead on arrival.**

### 1.1 The two numbers were never measured on the same ROI

| | fact 19 (M2) | fact 734 (M53) |
| --- | --- | --- |
| ROI | `2272,1344,**256,256**` | `1356,32,**512,512**` |
| frame 11 raw sd | 28.201 DN | 76.272 DN |

Different position **and** different size, on a patch with 2.7x the spatial sd.
Nobody named this, and it is not an operator question. (MEASURED,
`out/a5_stack.log:50` and `M2-verification.md:56`.)

### 1.2 On M2's exact ROI, today's binary reproduces M2's denominator exactly

Everything below is 109MSDCF, 22 frames, ROI `2272,1344,256,256`, denominator
frame 11 — M2's configuration, today's binary.

| quantity | M2 (fact 19) | today | |
| --- | --- | --- | --- |
| single frame 11, raw sd | **28.201 DN** | **28.201 DN** | exact, 5 s.f. |
| unregularised argmax, raw sd | 35.328 DN | 30.114 DN | −5.214 DN |
| regularised argmax, raw sd | 30.305 DN | 25.097 DN | −5.208 DN |
| LEGACY ratio, unregularised | **1.253x** | **1.068x** | |
| LEGACY ratio, regularised | **1.075x** | **0.890x** | |
| HP ratio, unregularised | not measured | **1.223x** `[1.016 .. 1.277]` | |
| HP ratio, regularised (gate 2.0) | not measured | **0.948x** `[0.788 .. 0.990]` | |

The denominator reproducing to five significant figures is the strongest
evidence available that M2's configuration **was** reconstructed: same ROI,
same plane, same frame, same decode. Whatever moved, it was not the reference.

M2's replication ROI `2352,1408,256,256` behaves identically: M2 published
1.263x, today reads 1.088x.

### 1.3 The gap decomposes into two causes, neither of which is a naming error

- **1.253x → 1.068x** on M2's own ROI: the merge *output* changed. −0.185,
  **69% of the gap.** This is the pipeline change the owner hypothesised.
- **1.068x → 0.985x** from M2's ROI to M53's: the ROI changed. −0.083,
  **31% of the gap.** This is the cause nobody named.

Two of the four hypothesised axes are dead:

- **Alignment — dead.** `strehl stack` "does not align, denoise, regularise the
  winner map, or blend frames" (its own `--help`). M2's baseline did not align
  either. There is no difference to attribute.
- **Gain — dead.** 109MSDCF is **ISO 160**. Commit `2a4f5c5` corrected the
  **ISO-50** gain floor. M47 established the ISO-160 stacks are untouched by
  it. The gain cannot be moving this number.

What survives is **operator + window** (ring(1,3) → Tenengrad, fact 70, with
the 27x27 window, fact 60), and they co-vary. **I could not isolate them:
`ring(1,3)` has no implementation left in the shipped crates**, so it cannot
be switched off without reimplementing a retired operator. The attribution is
therefore by elimination, corroborated indirectly — fact 71's ring→Tenengrad
speckle move (34.381% → 1.010%) reproduces *exactly* on today's binary
(`out/a5_stack.log:46`, 1.010%). (ARGUED, and the gap is named.)

### 1.4 The answer, and it is not the comfortable one

**Both numbers are correct for their configuration, and neither means what the
pair was being asked to mean.** But the substantive finding is not the
bookkeeping:

**The founding defect is real, is still present, and the legacy statistic
cannot see it on the very ROI where the project was founded.** On M2's ROI,
today's unregularised argmax reads legacy **1.068x** — nearly harmless — while
the high-pass statistic reads **1.223x**, and its *minimum over all 22 frames*
is **1.016x**. The stack is noisier than **every** single frame it was built
from. (MEASURED.)

**The shipped merge does remove it.** Like for like, on the same statistic and
the same ROI, M2's regularised argmax was **1.075x** and today's is **0.890x**
— it has crossed 1.0. The high-pass statistic agrees: **0.948x**, with a
maximum over frames of 0.990x, i.e. below every frame. (MEASURED.)

So `strehl` **can** honestly say the founding defect is removed — but only for
the regularised merge, not for argmax, and only when the claim names the
statistic and the ROI. The pre/post comparison the owner was worried about is
sound on the legacy statistic at fixed ROI (1.253 → 1.068 unregularised,
1.075 → 0.890 regularised); it is *not* sound across ROIs, which is exactly
what fact 19 vs fact 734 did.

### 1.5 Fact 19's three numbers

Fact 19 carries 1.253x raw, ~1.48x structure-corrected, and a 0.981x placebo.
The comparison above uses the **raw** figure throughout, which is the one
fact 734 is commensurable with. **The placebo was not reproduced**: it needs
the winner map shifted by half a ROI, which no shipped binary emits, and the
retired operator. I did not build it. That control is the one that proved
causation, so its non-reproduction is the largest hole in this section.

---

## 2. An independent corroboration of the kernel, from M2

M2 measured an Immerkaer 3x3-Laplacian high-pass of frame 11 in that ROI at
**19.473 DN** against a model temporal sigma of 19.267 DN — agreeing to 1.011x.
Today's `box9` residual on the same frame and ROI reads **23.09 DN**, or
**1.198x** the same model sigma.

Both are above the model, as a spatial sd over a temporal sigma must be
(rule 10 — this is a one-sided reading, not an equality). The difference
between them is the kernel: a 3x3 Laplacian is a far tighter high-pass than a
9x9 box residual and admits less structure. **This is independent evidence,
from a milestone written long before M53, that the tighter kernel is the less
contaminated one** — and it points the same way as M53's own sweep, which
preferred `w=3` (contamination 1.0234x) over the shipped `w=9` (1.2756x).

The shipped choice is `w=9` because it reconciles with M41's `hp_sd(a, w=9)`,
the kernel that produced fact 469's 144.391x. Replacing one unmeasured choice
with another is not an improvement, so the sweep is published and the choice
is left open. **This section strengthens the case for revisiting it.** (Open
question, with two independent measurements now pointing the same way.)

---

## 3. Findings

1. **MEASURED** — Facts 19 and 734 use different ROIs, in position and size
   (`2272,1344,256,256` vs `1356,32,512,512`), with frame-11 raw sd of
   28.201 DN and 76.272 DN. 31% of the discrepancy is this alone.
2. **MEASURED** — On M2's ROI today's binary reproduces M2's frame-11 raw sd
   to five significant figures (28.201 DN), so the configuration is
   reconstructed and the movement is in the merge output, not the reference.
3. **MEASURED** — On M2's ROI the legacy statistic reads 1.068x for
   unregularised argmax while the high-pass statistic reads 1.223x, minimum
   1.016x over all 22 frames. The legacy statistic under-reports the founding
   defect on the founding ROI.
4. **MEASURED** — Like for like on the legacy statistic at fixed ROI, the
   defect genuinely shrank: unregularised 1.253x → 1.068x, regularised
   1.075x → 0.890x. The improvement is real and is roughly equal on both
   merge rules.
5. **MEASURED, unexplained** — Both merge rules lost almost exactly the same
   *absolute* sd between M2 and today: 5.214 DN and 5.208 DN, agreeing to
   0.1%. With n=2 this may be coincidence; it is recorded because an additive
   constant is not what a change of focus operator predicts.
6. **DERIVED** — The alignment and gain axes of the owner's hypothesis cannot
   contribute: neither pipeline aligns, and 109MSDCF is ISO 160 while the gain
   fix is ISO 50.
7. **ARGUED** — The residual 1.253x → 1.068x is attributable to the operator
   and window change by elimination, not by isolation. `ring(1,3)` is retired
   from the shipped crates and was not reimplemented.
8. **MEASURED** — M2's Immerkaer high-pass reads 1.011x of model sigma where
   M53's `box9` reads 1.198x on the same frame and ROI, independently
   corroborating that the shipped kernel is the more structure-contaminated of
   the two.

## 4. What I could not verify

- **M2's placebo A (0.981x) was not reproduced.** It requires a half-ROI
  shifted winner map and the retired operator. It is the control that proved
  causation, and it remains unreproduced.
- **Operator and window could not be separated** from each other, for the
  reason in finding 7.
- **Fact 19's ~1.48x structure-corrected figure** was not recomputed; the
  comparison is on the raw figure throughout.
- Whether the 5.21 DN coincidence in finding 5 is real.

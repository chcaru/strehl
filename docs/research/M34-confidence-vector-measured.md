# M34 — Is the confidence output a vector or a number?

> **NOT INDEPENDENTLY VERIFIED.** Measured by the orchestrator. Rule 12 binds the
> author of this file exactly as it binds any milestone author. Everything below
> should be treated as a hypothesis that survived the controls I thought to run,
> not as a result.

**Milestone:** M34
**Question:** 65 (a) and (b) — the two candidates M33 left unmeasured — and the
prior question that decides M18's output contract.
**Data:** `coffee-bean`, 53 frames (×2 sampling), 1024×1024 green-sublattice crop.
Reuses M32's raw cube and M33's dense focus volume, which are pixel-identical
(same crop `CY,CX,H = 1172,1757,512`, same sublattice, same black level — asserted
in script 01, not assumed).

---

## 0. The question

Question 65 proposes that a shippable confidence output is a small vector:
predicted σ of the merged estimate **(a)**, acceptance-set width / `n_eff` **(b)**,
and the sub-frame peak offset **(c)**. M33 measured (c). Before measuring (a) and
(b) on their own terms, there is a cheaper question that decides the interface:

> Do these channels find **different** bad pixels, or the same ones?

If they rank pixels alike, the vector is decoration and one number ships. If they
flag disjoint populations, each earns its place, and the honest "do not trust this
pixel" mask is their **union**, which is larger than any single channel.

Four channels, all oriented as **badness** (larger = less trustworthy):

| | channel | definition |
|---|---|---|
| **C1** | predicted σ of the merged estimate | `sqrt(Σ_{k∈A} σ_k²)/\|A\|` over the acceptance set `A`, divided by the merged signal — i.e. inverse output SNR. `σ_k` from the M4 model at that frame's own signal level. |
| **C2** | posterior perplexity | `exp(H)` of `p_k ∝ exp(-(f_max-f_k)²/2σ_f²)`. `σ_f` estimated **model-free** from along-`k` second differences on the defocused tail (M32's validated method). |
| **C3** | sub-frame deficit | M33's log-domain three-point fit with baseline subtraction (fact 272). |
| **C4** | clip / boundary flags | any sample ≥ 0.995 × white, **or** peak within 2 frames of the stack edge. |

---

## 1. Headline — the channels are almost perfectly complementary

**Union of C1, C2, C3 worst-5% sets: 14.278% of pixels, against a 15.0% ceiling
if they were perfectly disjoint. That is 95.19% of the way to complete
disjointness.** If they were the same channel it would be 5.0%.

Every pairwise overlap sits at chance:

| pair | Spearman | Jaccard of worst-5% | vs analytic chance (0.0256) |
|---|---|---|---|
| C1 σ vs C2 perplexity | +0.0783 | 0.0346 | 1.35× |
| C1 σ vs C3 deficit | **−0.1240** | **0.0136** | **0.53×** |
| C1 σ vs C4 flags | −0.0050 | 0.0250 | 0.98× |
| C2 perplexity vs C3 deficit | +0.2975 | 0.0267 | 1.04× |
| C2 perplexity vs C4 flags | +0.0353 | 0.0297 | 1.16× |
| C3 deficit vs C4 flags | −0.0067 | 0.0268 | 1.05× |

**Conclusion for M18: confidence is a vector. A scalar cannot represent it.**

### The controls that make that readable

- **Calibrated null.** Shuffling C3's pixel labels and re-measuring against C1 gives
  Jaccard **0.0256** against an analytic chance of **0.0256** — agreement to four
  decimals. The statistic is reading structure, not arithmetic.
- **A second, independent null that I did not design.** C4 fires on only **0.053%**
  of pixels, so asking for its "worst 5%" returns 0.053% real flags and 4.947%
  random tie-breaks. Its overlaps are therefore at chance **by construction** — and
  they measured 0.0250, 0.0297, 0.0268 against 0.0256. A degenerate row turned out
  to be a free confirmation of the chance level.
- **Reliability ceiling.** Low overlap proves disagreement, not *meaningful*
  disagreement: three pure noise channels also disagree. Re-realising the
  measurement — independent synthetic noise draw at the data's own level (M4
  model), focus volume rebuilt, channels recomputed — gives self-overlap
  **C1 0.7642, C2 0.6948, C3 0.7352**. Each channel is ~70–76% self-reproducible
  while agreeing with the others at chance. **This is deliberately conservative**:
  both arms carry the original noise plus an independent draw, so each has ~√2×
  the real noise and they share only the original component. These are lower
  bounds, not estimates.

Normalised by that ceiling, the cross-channel numbers are unchanged in meaning:
0.0185, 0.0498, 0.0384 against a chance-over-ceiling of 0.0348, 0.0368, 0.0368.

---

## 2. C4 is nearly free and nearly redundant

C4's **actual** flag set adds only **0.0145%** of new pixels to the C1∪C2∪C3 union
— **73% of the pixels it flags are already caught** by the three real-valued
channels. Clipping and stack-boundary peaks are not a separate failure mode so
much as an extreme of ones already represented.

Keep the flags: they cost nothing, and they are the only channel that says *why*
rather than *how much*, which matters for the reshoot-advisor product. But do not
count them as a fourth independent dimension.

**Step 2 reported the union as 18.52%.** That number is wrong for the purpose and
step 3 corrects it to 14.278%: it included C4's 4.947% of random tie-breaks. Left
in the record because the mechanism is the point.

---

## 3. Specificity — orthogonal is not the same as useful

Three orthogonal noise sources would produce section 1 exactly. So one channel
was tested against real ground truth: M33's dense 105-frame grid gives the **true**
sub-frame deficit, which is precisely what C3 is built to estimate.

| channel | Spearman vs **true** deficit | mean true deficit in its worst-5% | lift vs global mean (2.876%) |
|---|---|---|---|
| C1 σ | −0.0726 | 0.02556 | **0.89×** |
| C2 perplexity | +0.3349 | 0.04075 | 1.42× |
| **C3 deficit** | **+0.5560** | **0.08380** | **2.91×** |
| random channel (floor) | +0.0014 | — | — |

C3 wins decisively on its own target, and the random-channel floor at +0.0014
confirms the correlation is not an artifact of the comparison.

**C1's lift is 0.89× — below 1.0.** The pixels C1 calls worst have *less* true
sub-frame deficit than average. That is a real anti-association with a mechanism:
dim, photon-starved pixels have **flat** through-focus curves, so missing the peak
costs them little. The channel that finds the noisiest pixels is systematically
looking away from the pixels that are worst-sampled. **This is the single
strongest argument in the milestone for the vector** — not that the channels are
uncorrelated, but that one is *negatively* informative about another's target, so
no monotone combination of them is a valid scalar summary.

### The tension worth carrying forward

C2 correlates with the true deficit at **+0.3349 — 60% of C3's +0.5560** — yet
their worst-5% sets overlap at **chance**. Both measurements are correct and they
are not in conflict: C2 carries real information about sub-frame deficit across
the bulk of the distribution while the specific pixels it calls worst are
different pixels. **A rank correlation and an extreme-set overlap answer different
questions, and a confidence channel has to be judged on both.** Reporting only the
correlation would have said C2 is a weak C3; reporting only the overlap would have
said C2 is unrelated to C3. Neither alone is true.

---

## 4. What I got wrong

Six predictions were registered in script 01 before anything ran. **Three
confirmed, three falsified.**

| | prediction | outcome |
|---|---|---|
| P1 | C1 vs C3 Jaccard < 0.15 | ✅ **0.0136** |
| P2 | C2 degenerate — within 1% of 1.0 for >95% of pixels | ❌ **76.48%** |
| P3 | reliability ceiling > 0.60 for C1 and C3 | ✅ **0.7642 / 0.7352** |
| P4 | union > 12% | ✅ 18.52% as measured, **14.278%** after the C4 correction |
| P5 | C4 fires on < 5% | ✅ **0.053%** |
| P6 | Spearman(C3, true) > 0.45 | ✅ **+0.5560** |
| P7 | C1 and C2 below half of C3's correlation | ❌ **C2 is at 0.602 of it** |
| P8 | C3 worst-5% lift > 3× | ❌ **2.91×** — an honest near-miss |

**P2 is the one that matters, and it qualifies a fact I wrote myself.** Fact 261
says the calibrated posterior is a delta with perplexity 1.0000. That was measured
on **binned populations**. Per pixel, the tail is real: p99 = 4.74, max = 39.05,
and **23.5% of pixels are more than 1% away from a delta**. Fact 261 is right about
the typical pixel and silent about the minority — and the minority is exactly where
confidence lives. **A median over a population cannot falsify a claim about the
population's tail, and I used it as though it could.**

P8 is a near-miss I am recording rather than rounding: I predicted >3× and measured
2.91×. The physics was right, the threshold was arbitrary, and the honest report is
that it failed.

---

## 5. Two defects in my own scripts

**(1) I reintroduced a sign error I had already found and fixed.** Script 01's
parabola vertex value used `a0 − 0.25(ap−am)·x*`. For samples at `x = −1,0,1` with
`b = (ap−am)/2`, `c = (ap−2a0+am)/2`, the vertex is at `x* = −b/2c` with value
`a0 − b²/4c = a0 + 0.25(ap−am)·x*` — a **plus**. This is character-for-character
the same error as M33 script 02, which I found, documented and corrected. I
reproduced it by **retyping the formula instead of importing the corrected one.**

> **The lesson is not "be careful."** A formula that has already been got wrong
> once should exist in exactly one place in the repository. Retyping a corrected
> expression discards the correction. When M18 implements sub-frame interpolation
> it should be a single function with the M33/M34 cases as unit tests.

**(2) A defensive clamp perfectly concealed it.** C3 was computed as
`1 − exp(min(a0 − peak, 0))`, where the `min(·, 0)` was written so a numerically
impossible positive value could not yield a negative deficit. With the sign
flipped, `a0 − peak` is positive for **every** pixel, the clamp fired everywhere,
and C3 came out **exactly 0.00000** at the median, the mean *and* p95 —
**100.0000% of pixels exactly zero**.

> The guard did its job and that is precisely the problem. A clamp that is
> unreachable in correct operation should be an **assert**, not a clamp: it would
> have failed on the first pixel instead of producing a plausible-looking
> all-zeros channel. The `p95 = 0.00000` was the tell, and it was only a tell
> because I knew from M33 that the true mean is 2.75%.

Both defects are left in script 01 as-run, per rule 15, and corrected in script 02,
which **measures** the difference rather than arguing it.

---

## 6. Ground-truth reconciliation, disclosed

Script 04's true-deficit mean is **2.876%** and the exactly-zero fraction is
**48.92%**; M33 (fact 270) reported **2.753%** and a **48.7% miss** rate (i.e.
51.3% exactly zero). The gaps — 4.5% relative on the mean, 2.4 pp on the fraction —
come from a **definitional difference, not a contradiction**: script 04 subtracts
the dense-grid baseline (`min` along `k`) before forming the ratio, which M33 did
not. Recorded rather than reconciled away, because the two numbers are answers to
slightly different questions and neither is the wrong answer to its own.

Carried forward from M33 unchanged: the dense grid misses its own peaks by 0.711%
against the ×2 grid's 2.753%, so it is honest ground truth for the ×2 question by
a factor of **3.87 and no more**.

---

## 7. What to build

1. **The confidence output is a vector, not a scalar.** Ship `{predicted_sigma,
   n_eff, subframe_deficit, flags}`. The disjointness (95.19% of the disjoint
   ceiling) and C1's *negative* lift on C3's target together mean no monotone
   scalar summary is faithful.
2. **The "do not trust" mask is the union**, and on this stack it is **14.3% of
   pixels** — three times what any single channel reports. A tool that shipped one
   channel would understate its own uncertainty by 3×.
3. **Keep C4's flags, but as an explanation, not a dimension** — 73% of what they
   flag is already caught, and their value is that they say *why*.
4. **Sub-frame interpolation must exist once**, with the M33 anti-correlation case
   and the M34 sign error as unit tests.
5. **Unreachable-in-correct-operation clamps become asserts** in `strehl-core`.
6. **Question 65 (b) is answered in the negative for the typical pixel and the
   affirmative for the tail** — perplexity is 1.0 for 76.5% of pixels and carries
   real information (Spearman +0.33 against true deficit) in the rest.

## 8. Open

- **C1 and C2 have no ground truth here.** C1's target is the merged estimate's
  actual error, which needs either the simulator (M25) or a repeat-capture pair.
  This milestone shows C1 is *orthogonal* and *self-reproducible*; it does **not**
  show C1 is *right*. Do not let it into a product claim until M25 lands.
- **One stack, one aperture, one magnification.** Same scope limit as M33, and
  question 70 applies here too.
- **The acceptance set is median size 1.0** at a 1σ_f gate, so C1 is currently
  measuring single-frame SNR rather than a merge benefit. That is consistent with
  fact 261's 142–991σ peaks, but it means C1 will change character once M18's gate
  is tuned, and these numbers should be re-measured against the real merge.

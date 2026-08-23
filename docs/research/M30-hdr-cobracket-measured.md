# M30 — HDR focus co-bracketing (R17), and a general constraint on all capture co-design

> **NOT INDEPENDENTLY VERIFIED.** Produced and written up by the same agent. Treat as a
> hypothesis with a script attached. Scripts committed exactly as run.

Review item **R17**: *"HDR-focus co-bracketing: the estimation framework handles per-frame
gain natively; a two-exposure stack pair gives true HDR focus stacks — RAW-native,
calibrated — which no shipping tool does honestly."*

The premise is correct and already paid for: M24 measured per-frame photometric drift and
M28 measured how to fit the gain. The estimator *can* handle a two-exposure stack. This
milestone asks the question that decides whether it *should*: **does this rig have a
dynamic-range problem, and what does spending frames on exposure instead of on focus
actually buy?**

The answer is no, and the reason generalises well beyond R17.

---

## 1. The result that decides it: exposure allocation is neutral at fixed light

For scene radiance `L`, a base frame measures `S = L` with variance `g·L + (RN·g)²`. A
+2 EV frame measures `4L`; expressed back in radiance units its variance is
`[4gL + (RN·g)²]/16 = gL/4 + (RN·g)²/16`. Take `m` frames of each and combine by inverse
variance, against `5m` base frames — the *same* 5m units of exposure time, because each
+2 EV frame costs four:

```
HDR split    Var = 1 / (m/V_base + m/V_p2)   =  V_base / (5m)      [shot-noise limited]
all base     Var = V_base / (5m)
```

**Identical. Photons are photons.** Measured per pixel on real signal from three stacks:

| stack | median ratio | p1 | p99 | max deviation |
|---|---|---|---|---|
| `coffee-bean` | **1.00041** | 1.00004 | 1.00146 | 0.00201 |
| `112MSDCF` | **1.00470** | 1.00082 | 1.01142 | 0.02320 |
| `109MSDCF` | **1.00192** | 1.00091 | 1.01872 | 0.03833 |

`> 1` means the HDR split wins. It wins by **0.04–0.47% median** — the residual is read
noise, in the predicted direction and at the predicted size. **Q4 holds.**

This is not a fact about HDR. It is a fact about every capture-design question the project
has queued: **in the shot-noise regime, how a light budget is divided across frames does
not affect noise — only the total does.** Therefore *all* capture co-design decisions are
settled by the **non-noise** asymmetries, and there are only a few of them:

| asymmetry | favours | measured here |
|---|---|---|
| read noise | fewer, longer frames | **0.0000% of pixels** |
| clipping | more, shorter frames | **0.075% max** |
| focus coverage (fact 213) | more frames | saturated at 53 frames on `coffee-bean` |
| outlier rejection (fact 222) | more frames | unpriced |
| **aperture / diffraction (M20)** | **opening up** | **9.6× contrast at 4-px detail** |

The last row is the one that matters, and it is the only one that is *large*. M20's
aperture result changes the **optics**; everything R15–R17 proposes only re-divides the
same photons. That is a useful ordering: **capture co-design should spend its effort on
aperture, not on exposure allocation.**

---

## 2. This sensor is shot-noise limited across its entire usable range

The neutrality identity holds only where shot noise dominates, so the boundary matters.
Read noise binds where `g·S < (RN_e·g)²`, i.e. `S < RN_e²·g` DN above black:

| stack | ISO | g (DN/e⁻) | RN (e⁻) | boundary | % of full scale | measured % below |
|---|---|---|---|---|---|---|
| `coffee-bean` | 50 | 0.1145 | 4.20 | **2.02 DN** | 0.0136% | **0.00%** |
| `112MSDCF` | 500 | 1.1447 | 1.47 | **2.47 DN** | 0.0167% | **0.00%** |
| `109MSDCF` | 160 | 0.3663 | 4.20 | **6.46 DN** | 0.0435% | **0.00%** |

**Q5 holds.** The read-noise regime is confined to the bottom **0.014–0.044%** of full
scale, and **not one pixel** in three stacks sits there. The dual-gain design does this
deliberately — the high-ISO branch drops read noise to 1.47 e⁻ precisely where `g` rises.

**Consequence for the merge, which is the reusable part:** the noise model's read-noise
term is numerically irrelevant on real subject data. It must stay in the model — it is
what makes `σ²(S)` correct near black, and clipped/masked regions do reach there — but no
design decision should be made *because of* it. Anything that depends on read noise for
its justification is, on this rig, depending on 0.0000% of the frame.

---

## 3. The demand side: there is almost no dynamic range problem to solve

| stack | clipped **at best-focus frame** | clipped whole stack | ratio | SNR < 10 at best focus | SNR < 5 |
|---|---|---|---|---|---|
| `coffee-bean` | **0.075%** | 0.177% | **0.43×** | 0.0% | 0.0% |
| `112MSDCF` | 0.000% | 0.000% | — | **30.7%** | 0.0% |
| `109MSDCF` | 0.000% | 0.000% | — | 0.0% | 0.0% |

**The statistic a merge sees is not the global one.** M26 measured clipping over the whole
stack; what reaches the output is the exposure of the frame *gathered* at each pixel.
That number is **2.3× lower** — **highlights are disproportionately out of focus**, which
makes sense (speculars sit on curved surfaces near the depth extremes) and cuts the
highlight case for HDR roughly in half again. **Q6 holds.**

> Script 01 prints a `0.00×` ratio for the two stacks with zero clipping. That is `0/0`
> and means nothing; it is a display defect in a script that has been run and therefore
> must not be edited.

`112MSDCF`'s 30.7% below SNR 10 is the only real weakness, and it is **not** a dynamic
range problem: **0.0% falls below SNR 5**, and nothing is read-noise limited. The whole
frame is simply dim (ISO 500, small aperture). That is fixed by *more light*, which — per
§1 — more frames and longer frames supply equally well per unit time, and more frames
additionally buy focus coverage and outlier rejection.

---

## 4. Verdict on R17

**Support it; do not default it; let the advisor decide per stack.**

1. **The machinery is already there and costs nothing.** Per-frame gain is in the forward
   model (M24, M28). A two-exposure stack is a valid input to the estimator by
   construction. Nothing needs building for R17 specifically — which is exactly why it
   should be *supported*.
2. **The default path should not spend frames on exposure.** At fixed light it is neutral;
   every measured asymmetry on this corpus points the other way; and the frames are worth
   more in the focus axis and to the robustness mask.
3. **It is a per-stack decision with a measurable trigger.** Clipping at gathered frames is
   computable from the stack itself — 0.075% here, and a wet chitinous subject under flash
   would be far higher. **Emit it as an advisory** ("2.4% of gathered pixels are clipped;
   a −2 EV pass would recover them"), which is the same instrument R19 asked for and
   another concrete entry in the reshoot-recipe vocabulary.
4. **Note the direction the review implied is backwards for highlights.** Rescuing clipped
   pixels needs a **−2 EV** pass, not +2 EV; +2 EV clips *more* (1.89% newly clipped on
   `coffee-bean`). Shadow lifting and highlight rescue are opposite operations and only
   the second is motivated by anything measured here.

### Derived disposition for R16's first half, at no extra cost

R16 proposes **interleaved half-step passes** to double focus-axis sampling. §1 says the
photon budget is indifferent, so this is purely a focus-coverage question — and M27
already answers it: coverage is **saturated** on `coffee-bean` at 53 frames (0.01% of
pixels resolved by ≤1 sample), so doubling density there buys nothing. Where a bracket
*is* sparse, M27's criterion says so directly and a half-step pass is the right remedy.
**R16's half-step half is therefore answered: it is a repair for a diagnosable condition,
not a default.** Its aperture-paired half (two-aperture depth-from-defocus) is a different
proposal, changes the optics rather than the allocation, and remains open.

---

## 5. My error in this milestone

**One, and it invalidated script 01's headline.** Script 01 compared a +2 EV frame against
a +0 EV duplicate and reported a **1.415×** advantage, with the duplicate presented as the
placebo. The placebo controlled for **frame count**. Frame count is not the scarce
resource — **exposure time is** — and a +2 EV frame costs 4× as much of it. The comparison
put four units of light against one and recovered, to three decimal places, the fact that
`√4/√2 = 1.414`. It measured its own arithmetic.

The general form is worth recording because it is not the same error as any already in the
discipline list: **a control must hold constant the resource that is actually scarce, and
the resource that is scarce is a property of the domain, not of the data structure.**
Frames are what the array is indexed by, so frames are what a placebo naturally holds
fixed — and that is precisely why it was the wrong invariant. The tell was available:
the measured advantage came out at `√2` to four significant figures across three stacks
with entirely different ISOs, signals and scenes. **A result that reproduces a constant
that exactly, across conditions that should perturb it, is usually the arithmetic of the
comparison rather than a property of the world.**

Script 01 is committed despite its headline being void; its per-pixel measurements
(clipping at best focus, SNR distributions, the read-limited fraction) are sound and
script 02 consumes them.

---

## 6. Scripts

| script | what it does | status |
|---|---|---|
| `01-dynamic-range.py` | clipping at gathered frames, SNR at best focus, +2 EV vs duplicate | ran; **headline void** (wrong invariant); measurements sound |
| `02-fixed-light.py` | the fixed-light neutrality identity; read-noise boundary; the three asymmetries | ran; **the result** |

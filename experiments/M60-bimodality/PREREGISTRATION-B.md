# M60b — pre-registration: is fact 568's wrong sign the plant, or the instrument?

**Written and committed before any enrichment number was computed under any
variant statistic.** That ordering is the point. The only numbers below that
existed when this was written are ones already published in `SYNTHESIS.md`
(facts 150, 151, 152, 568, 603, 604) and in M60's own first pass.

---

## 1. Why this supersedes M60's original brief

M60 was commissioned to measure whether the through-focus response at occluding
edges is bimodal. It did, and the first-pass report stands. But the commissioning
brief did not name `M21-occlusion-bimodality-measured.md`, which had already
asked that question, nor M25, which built the plant that failed to reproduce it.

Having read both, the live question is not the one M60 was given. It is the one
open questions 132/137/138 circle without landing on:

> **M25's plant returns truth-gated veiling enrichment of 0.23x — the wrong sign.
> Is that because the plant lacks the phenomenon, or because the statistic cannot
> see the phenomenon where it lives?**

Four probes have attacked this. Every one of them varied **the plant**:

| probe | varied | result | fact |
| --- | --- | --- | --- |
| defocus rate | plant | flat across 12x | 568 |
| occluder luminance step | plant | 0.24x -> 0.28x | 568 |
| ISO-50 gain (2x error) | plant | 0.24x -> 0.23x | 568 |
| multi-scale occluder geometry | plant | 0.19x -> 0.86x, asymptotes < 1.0 | 603 |

**Zero probes varied the instrument.** That is the gap this milestone attacks.

## 2. The specific defect alleged

`multipeak` is defined once, in
`experiments/m21-occlusion-bimodality/src/03-permutation-placebo.py`, and copied
**verbatim** into M25's `14-stepmap-truth.py`, `15-lumstep-probe.py` and
`17-multiscale-occluder.py` (the copy is labelled as verbatim in a comment). So
facts 150, 151, 152, 568 and 603 all rest on one function:

```python
def multipeak(V, thr=0.04):
    Vs = np.copy(V); Vs[1:-1] = (V[:-2] + 2*V[1:-1] + V[2:]) / 4.0
    mx = Vs.max(0); mn = Vs.min(0); rng = np.maximum(mx - mn, 1e-6)
    ispk[1:-1] = (Vs[1:-1] > Vs[:-2] + thr*rng) & (Vs[1:-1] > Vs[2:] + thr*rng)
    return ispk.sum(0) >= 2, (mx - mn)/np.maximum(mx, 1e-6), np.argmax(Vs, 0)
```

Three properties, none of which has been varied in any published probe:

* **H-A — the denominator is the pixel's own curve range.** A peak must clear its
  neighbours by `0.04 x (max - min)` of that pixel's own through-focus curve. At
  an occluding boundary the curve's range is set by the foreground edge coming
  into focus, which at R=2 is the largest Sobel response anywhere in the scene.
  So the bar for a second peak is **raised precisely at the pixels where
  occlusion happens**. This is the shape discipline 338 already condemns: a
  score whose denominator is driven by the thing that also drives its numerator.
* **H-B — the peak test compares immediate frame neighbours only.** Sensitivity
  therefore depends on the focus step. A broad, well-sampled peak in a dense
  stack rises by less than `0.04 x rng` per frame and is invisible; the same peak
  in a sparse stack is found. Rates are not comparable across stacks of different
  depth.
* **H-C — the analysed population is gated on `c13 = (max-min)/max > 0.10`,**
  a *relative* focus contrast at R=13, which is itself contrast-dependent.

M21 already measured the consequence of H-A and read it as reassurance. Its §5
reports that binning on intensity gradient alone gives **0.00x**, with "0.0% at
the top decile of intensity gradient vs 9.2% in flat regions", and concludes
"the effect cannot be an intensity-edge artifact in disguise."

**An occluding edge is an intensity edge.** SYNTHESIS fact 73 and M60's own B1
gate both turn on that identity. A statistic that reads exactly 0.0% in the top
decile of intensity gradient is not thereby proven free of edge artifacts; it is
proven **blind at edges**, which is where the phenomenon under test lives.

## 3. What M25's oracle did and did not fix

M25 correctly refused to let M21's *detector* define the populations, and gated
on rendered truth instead (`alpha_front` partial, `visible_focus` step). That
removes circularity in **which pixels are compared**.

It does not remove it from **what is measured on them**: the compared quantity is
still `multipeak`. Discipline 358 — separate the quantity under test from the
quantity that labels the test — was satisfied on the label and left open on the
measurement. So fact 568's inference,

> "A perfect detector scores near zero here"

holds only under the assumption that `multipeak` faithfully reports bimodality.
That assumption is what this milestone tests.

## 4. Hypotheses and pre-registered decision rules

Data is held **fixed**. M25's control plant (`shape="discs"`, the variant that
produced 0.19–0.23x) is rendered once from M25's own simulator at M25's own
config, and the rendered frames and truth planes are frozen to disk. Every
statistic below reads those same arrays. Nothing about the plant is changed.

### Statistics, differing only in the peak-acceptance rule

| id | smoothing | peak rule | threshold source |
| --- | --- | --- | --- |
| **S0** | M21's [1,2,1] | `> both neighbours + t` | `t = 0.04 x rng` (M21 verbatim) |
| **S1** | M21's [1,2,1] | `> both neighbours + t` | `t = z* x sigma_pred`, `z*` calibrated per pixel-class to 1% FPR on a noise-only null |
| **S2** | none (M60 rule 23) | most-prominent interior maximum vs running minimum | `prom / sqrt(sigma_k2^2 + sigma_kd^2) > z*`, 1% FPR |

S1 is the minimal edit: **one line of S0**, with the contrast-dependent
denominator replaced by the project's calibrated noise model and nothing else
touched. S2 is M60's independent statistic, included so the result does not
depend on M21's peak-finding either.

### T1 — primary. Truth-gated veiling enrichment, M25's exact gate

Populations are M25's verbatim: `veiled = strong & (0.02 < alpha_front < 0.98)`,
`smooth = strong & ~tstep & ~tpartial`.

| outcome | condition | consequence |
| --- | --- | --- |
| **INSTRUMENT** | S0 < 1.0 **and** (S1 >= 1.5 **or** S2 >= 1.5) | fact 568's conclusion is **void**; questions 132/137 were chasing a plant defect that is not the binding cause |
| **PLANT** | S0 < 1.0 **and** S1 < 1.0 **and** S2 < 1.0 | fact 568 **stands**; the plant genuinely lacks veiling and M60's first-pass corpus result is reinforced |
| **PARTIAL** | S0 < 1.0 and 1.0 <= max(S1,S2) < 1.5 | both contribute; report as such and do not pick one |
| **AMBIGUOUS** | anything else, including S0 >= 1.0 | I failed to reproduce M25's setup; report the failure, do not reinterpret |

### T2 — the mechanism, measured directly

`median(rng[veiled]) / median(rng[smooth])`, where `rng` is exactly the
denominator S0 divides by.

* **>= 1.5** — the denominator is materially inflated at veiled pixels. Supports H-A.
* **0.8 – 1.25** — H-A is refuted as a mechanism regardless of what T1 shows, and
  any T1 INSTRUMENT verdict must be attributed to something else and said so.

This is the discriminator that makes T1 interpretable rather than merely
suggestive, because it measures the alleged cause rather than its effect.

### T3 — threshold sweep, and the saturation guard

Sweep `thr` over {0.04, 0.02, 0.01, 0.005, 0.002, 0}. Report enrichment **and**
base rate on `strong` at each step.

**Pre-registered guard:** an enrichment computed where the base rate exceeds
**90%** is declared uninterpretable and is reported as saturated, not as a
result. This is M21's own fact-151 lesson applied to my own sweep. Lowering a
threshold until everything fires and then claiming the sign flipped would be the
same error in the opposite direction.

### T4 — real data, truth-bearing without a plant (question 138)

Question 138 asks whether the real 4.38x is partly M21's own false-positive rate,
and notes the difficulty: real captures have no truth map. M60 has a partial
substitute the corpus did not have — **25 hand-drawn cells** whose class was
assigned from intensity and geometry only, never from the focus volume.

Run S0 and S1 on M60's existing cell curves. Report per-class rates and the
`occ`/`ctl` ratio under each. **Pre-registered:** if S0's `occ:ctl` ratio is < 1.0
while S1's is > 1.0 on the same curves, the sign inversion reproduces on real
data and is not a plant artifact at all.

### T5 — frame density (H-B)

Run S0 at n = 299, 150, 75, 38, 23 on M60's dense stacks by decimation. H-B
predicts the S0 rate **falls** as n rises. Report the rate; this bounds whether
M21's cross-stack comparison of 22 / 33 / 21 frames was measuring stack depth.

## 5. Controls

* **Positive control, mandatory.** M25's own plant contains veiling by
  construction — `alpha_front` is partial at the boundary because the renderer
  put it there. If S1 and S2 both fail to find it, I have reproduced M25's
  failure and located it in the instrument-independent direction: the plant. This
  control is the reason T1 can return PLANT at all.
* **Negative control.** M25's `tru_lo` population — opaque, smooth depth, same
  scene, same noise, same render. Any statistic firing equally there is measuring
  texture and defocus, not veiling.
* **Placebo.** Frame-order permutation, run **for every statistic**, not just S0.
  M25 pre-registered 1.00 +/- 0.15 and I adopt it unchanged. A statistic whose
  placebo leaves that band is disqualified before its enrichment is read.
* **Fact 738's trap.** S1's threshold is calibrated on a **noise-only null cube**,
  not on the plant, and never against the constant that generated the plant. The
  noise model's parameters come from `crates/strehl-core`, are asserted in M60's
  gate 0, and are not tuned here.

## 6. Power, asserted before any result is read

Every population count is printed and asserted before its rate is interpreted:

* M25's own floor of **500 px** per bin is adopted for `veiled` and `smooth`.
* Additionally, any enrichment quoted as evidence requires **>= 5000 px** in the
  smaller bin. At 5000 px a rate near 5% has a binomial sd of 0.31 percentage
  points, so a 1.5x enrichment (5% -> 7.5%) is ~8 sd. Below 5000 px the number is
  reported as underpowered and is not used in the verdict.
* Fact 779's failure — a control run on 22–107 px that only discovered it had no
  power because it asserted the count — is the reason this is written here rather
  than discovered later.

## 7. What these discriminators cannot separate

Stated now, so it cannot be softened afterwards.

* **T1 cannot separate "the statistic is blind at edges" from "the statistic is
  blind at high-contrast pixels of any kind."** Occluding edges in this plant are
  both. T2 narrows this by measuring `rng` directly, but the two remain
  confounded in the plant by construction.
* **T1 and T2 say nothing about the real corpus.** They are a plant result. Only
  T4 speaks to real captures, and its labels are hand-drawn, not rendered truth.
* **S1 shares the noise model with M60's gate 0**, so a systematic gain error
  would move S1 and leave S0 untouched. AGENTS rule 34 and fact 599 apply. M60's
  first pass bounded the model against real-frame scatter at 4%; that bound is
  inherited, not re-derived, and it does not exclude a constant gain error.
* **Nothing here measures whether the reconstruction the reviewer proposes would
  work.** Establishing that a statistic can see veiling is not evidence that
  unmixing recovers usable background. That remains unmeasured, as M21 §8 said.
* **A PLANT verdict would not establish that veiling is absent from real
  captures**, only that this plant lacks it. M60's first pass speaks to the
  corpus; this milestone speaks to the instrument.

## 7b. Addendum — T6, registered after T1–T5 ran and before T6 ran

**Ordering, stated plainly:** T1–T5 have been run and read. T6 below was written
after seeing them and **before** the `discs-powerlaw` variant was rendered or
scored. It is a new question those results raised, not a reinterpretation of
them, and it is registered here so that ordering is on the record.

T2 measured S0's denominator at **3.942x** larger on veiled pixels than on smooth
ones in the `discs` control. That gives fact 603 a second possible reading.

Fact 603 records that multi-scale occluder geometry moved truth-gated enrichment
from 0.19x to 0.86x and calls it "the largest single effect ever measured on this
statistic, 4.5x". The intended reading is that multi-scale geometry adds veiling.
But multi-scale geometry also **replaces one large-contrast boundary with many
small ones**, which lowers each pixel's curve range — and S0's threshold is
`0.04 x range`. So the same manipulation predicts an improvement with no
additional veiling whatsoever, purely by relieving the denominator.

**T6.** Render M25's `discs-powerlaw` variant from the same simulator at the same
config, and on the identical frames measure (a) S0 enrichment, (b) the T2
denominator ratio, (c) S2 enrichment.

| outcome | condition | reading |
| --- | --- | --- |
| **DENOMINATOR RELIEF** | S0 rises toward 0.86x **and** the T2 ratio falls materially toward 1.0 **and** S2 does **not** rise by a comparable factor | fact 603's 4.5x is substantially an instrument effect; the geometry did not add veiling, it lowered the bar |
| **REAL VEILING** | S0 rises **and** S2 rises by a comparable factor | the geometry genuinely added veiling; fact 603's reading stands |
| **NEITHER** | S0 does not reproduce near 0.86x | I failed to reproduce the variant; report and stop |

"Comparable factor" is fixed now, before the run: S2's ratio between variants
within **+/- 30%** of S0's ratio counts as comparable.

**What T6 cannot separate.** Multi-scale geometry changes contrast *and* boundary
count *and* the number of depth transitions inside a detector window at once.
T6 can show the denominator moved and that S0 tracks it, but it cannot prove the
denominator is the *only* route. It also inherits every limitation in section 7.

## 7c. Addendum — T7, registered after T6 ran and before T7 ran

**Ordering:** T6 has been run and read. T7 below was written afterwards and
**before** any k2-location statistic was computed on either plant.

Section 5 already makes the positive control mandatory, but states no decision
rule for *where* a flagged second peak lands. T1 and T6 leave that gap open and
it is load-bearing: the veiled population sits on the occluder boundary, which is
a high-contrast edge, and M60's first pass established that a high-contrast edge
at a *single* depth generates secondary through-focus peaks by itself. So S2's
1.23x could be the same side-lobe artifact rather than veiling, and nothing
measured so far separates them.

The plant settles it, because it knows the answer. The background layer is at
focus index **16** and the foreground at **4** by construction.

**T7.** Among veiled pixels that S2 flags, measure the fraction whose `k2` lands
within +/-2 frames of index 16. Compare against three references computed the
same way: the flagged **smooth** population (no background to veil), a uniform
chance rate over interior indices, and a frame-permutation null. Report the full
`k2` histogram. Repeat for S0's flagged pixels.

| outcome | condition | reading |
| --- | --- | --- |
| **VEILING** | flagged-veiled `k2` within +/-2 of 16 is **>= 2x** the uniform chance rate **and >= 2x** the flagged-smooth rate | S2's enrichment is genuine veiling; the plant contains the phenomenon and S0 cannot see it |
| **SIDE-LOBE** | within **+/-30%** of chance, or not materially above flagged-smooth | S2's enrichment is not veiling either; the plant's veiling is undetectable by any statistic tried here |
| **INDETERMINATE** | anything between | report as such |

**What T7 cannot separate.** It is a plant result and inherits every limitation
in section 7. `alpha_front` partial pixels are both veiled *and* on a contrast
edge, by construction, so a positive result shows `k2` reaches the background
index, not that it would do so in the absence of the edge.

## 8. Stopping rule

If T1 returns AMBIGUOUS because M25's render cannot be reproduced, this
milestone reports that and stops. It does not substitute a different plant and
present the result as though it addressed fact 568.

---

*Committed before any variant statistic was evaluated on any data.*

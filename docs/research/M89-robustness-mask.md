# M89 — Outlier contamination in real focus brackets, and whether a robustness mask earns its place

> **§0 is the pre-registration. It was written into this file and committed
> before any measurement run existed.** Everything from §1 onward was written
> after. Where a criterion was added or changed later, it says so, in place,
> with the reason.

---

## 0. Pre-registration

### 0.1 Prior art the brief did not name (rule 40)

My brief cited `merge.rs`, `noise.rs` and Wronski et al. It did **not** name any
prior milestone. `docs/research/` holds **two** committed reports on this exact
question, and both are in the AGENTS.md index:

| report | seam | verdict |
|---|---|---|
| `M28-robustness-mask-measured.md` | raw stack, unaligned, green sublattice of a 3072 px crop, Python | a detector works if the reference is the **adjacent frame**, not a running whole-stack estimate; no merged image was ever produced |
| `M60-robustness-mask-at-merge-time.md` | after the gate, on the **admitted set**, per pixel, in shipped Rust | **did not build the mask**; the statistic is 76–84% detail composition, `coffee-bubbles` is a measured no-op, `foam`'s mask surface is 8.20% of pixels |

Rule 40 exists because a brief that omits the prior report gets a settled answer
re-derived with the authority of a fresh measurement. So I record, before
starting, what is already answered and what genuinely is not:

- **Answered by M28:** a whole-stack reference costs ~10x the geometric residual
  of an adjacent-frame one; detection is near-flat across a 4x range of tile
  scale; a planted rigid tile shift is detected monotonically with a clean
  `s = 0` placebo.
- **Answered by M60:** at the *merge-time* seam the statistic cannot carry the
  decision. Its F11 states where the work belongs instead, in as many words:
  *"on the raw stack, where every frame is present at every pixel"*. **That is
  the seam M89 takes.**
- **Not answered by either:** neither separated *motion* from *defocus*. M28's
  §5 confound is stated in its own text ("this cannot separate more disturbance
  from more contrast"); M60's F5 measured its statistic rising **5.11x** with
  detail on a clean stack and its F6 measured 76–84% of the apparent
  cross-stack signal to be detail composition. **Neither produced a merged
  image with and without a mask** (M60 §8 C4, explicitly).

So M89's contribution has to be, in order: (1) an operator that is not a
sharpness detector, demonstrated on a static stack; (2) a survey; (3) a merged
image, with and without.

### 0.2 The statistic, and why it should separate motion from defocus

**Defocus is smooth in the frame index. Motion is not.**

A pixel's value through the bracket, `L_f`, is the scene convolved with a PSF
whose radius varies slowly and monotonically with focus position. Photometric
drift (M24: 0.91% peak-to-peak on `109MSDCF`) is slow. Focus breathing is slow.
Hot pixels and dust are *constant* in `f`. Every one of those is a **low-order
function of the frame index**. A subject that twitches, a bubble that bursts, a
cosmic ray — those are steps, spikes and kinks: **high order in `f`**.

So the separator is a **leave-one-out local polynomial predictor along the frame
axis**. For pixel `i` and frame `f`, fit an order-`p` polynomial in frame index
to the `w-1` frames of the window `W(f) = {f-h .. f+h}` **excluding `f` itself**,
predict `f`, and normalise the residual by the calibrated noise model:

```text
pred_f = Σ_{j ∈ W(f), j ≠ f}  k_j · L_j          (k depends only on w and p)
z_f    = (L_f − pred_f) / sqrt( σ²(L_f) + Σ_j k_j² · σ²(L_j) )
```

with `σ²(·) = NoiseModel::green_luma_sigma(·)²` — the affine photon-transfer
relation in DN, gain and read noise per ISO from `profile.rs`.

Three properties, and they are the reason to prefer this to a running-mean
residual:

1. **The null is analytic.** Under *"the scene is static, `L_f` is locally
   order-`p` in `f`, and the samples differ by independent sensor noise"*,
   `E[z²] = 1` exactly, for every `w`, `p` and signal level. There is **no
   fitted threshold and no calibration stack**. M28 needed a threshold
   calibrated on a clean stack; this does not, so the clean stack becomes a
   *test* rather than the calibration set. (M60 made the same move for the same
   reason and I am following it.)
2. **The weights `k_j` are a fixed kernel**, because the frames are equally
   spaced in index. For `w = 5, p = 2` the residual kernel is
   `[1, −4, 6, −4, 1]/6` — the fourth difference — which annihilates any cubic
   in `f` exactly. Defocus, breathing and photometric drift are all absorbed
   *to the order of the fit*, not thresholded away.
3. **The variance term is exact, per sample**, not a window average: `pred` is a
   fixed linear combination, so `Var(pred) = Σ k_j² σ²(L_j)` with each `σ`
   evaluated at that sample's own signal. This is the part that needs the
   calibrated model and cannot be done with a constant in DN.

**Declared blind spots, before measuring.** By construction this operator is
*blind* to anything low-order in `f`: hot pixels (constant — M22 already settled
them at +3.0 DN mean, 0.0 DN median, 0.13–0.39 sigma, and I am not re-measuring
them), dust (constant in sensor coordinates pre-alignment), and slow photometric
drift. It is **partially** blind to a slow ramp. §0.4's plant morphologies A/B/C
exist to quantify exactly that, and I commit to reporting the ramp number
whatever it is.

**Rule 34 / discipline 358 disclosure.** `z` divides by `σ_pred` from the
calibrated noise model. **No plant in this milestone may be generated by scaling
`σ_pred`** — that would make the statistic measure its own arithmetic. Every
plant here moves **real frame content** (M28's design): a tile replaced by the
same tile taken `s` plane pixels away *in the same frame*, so noise, defocus,
illumination and sensor position are correct by construction and nothing is
synthesised. The placebo is `s = 0`.

**What the null bar can and cannot catch (rule 34, second half).** A plant
validates the operator, never the calibration. If `profile.rs`'s gain is wrong,
`z` is wrong by a scale factor and **A1 is the only arm with any power over
that**, because A1 compares `E[z²]` against an *externally* fixed 1.0 rather
than against another number of mine.

**Known model offsets, asserted rather than carved out (rule 30).** Two measured
corpus results say the null should read slightly **above** 1.0, and I state the
prediction now rather than excusing it later:

- fact 1064 — the shipped noise model is over-confident above `S = 504 DN`,
  reaching **−12.8%** in sigma at `S = 8000`. A sigma 12.8% low inflates `z²` by
  `1/0.872² = 1.315`.
- M72 — the two green planes correlate at `rho = +0.0826`, so
  `Var((G1+G2)/2) = σ²(1+rho)/2` against the model's `σ²/2`: `z²` inflated by
  **1.083**.

Compounded, the model-aware expectation for a *perfectly* static stack is
`E[z²] ∈ [1.00, 1.42]` rather than exactly 1.0. A1's pass band is set wider than
that on purpose; a reading inside [1.00, 1.42] is the *expected* answer and a
reading at exactly 1.000 would itself be mildly suspicious.

### 0.3 Operators, including a negative-control operator

`(w, p)` is swept: **(5,0), (5,2), (7,2), (9,2), (9,4), (13,4)**.

`p = 0` is the **negative-control operator**: leave-one-out *local mean*, which
is focus-*un*aware and is essentially M60's statistic on a temporal window. It
must show the detail dependence M60 measured. If `p = 0` and `p = 2` behave the
same, my separation mechanism does nothing and A2 has no power — this is the arm
that gives A2 the ability to fail.

**Primary setting, fixed now: `w = 5, p = 2`.** Smallest window that admits
through-focus curvature, so the least breathing accumulates inside it. If A1
fails at the primary setting I will report the whole sweep, say plainly that the
primary was changed, and report both numbers (rule: never retune a bar silently).

### 0.4 Stage-A bars — the metric

The **null stack** must be inanimate and locked down. Chosen before running, on
what the subject *is*: `highly-angled-ruler-mm-cpl` (299 frames, a ruler).
Secondary null: `coffee-bean` (105, an inanimate bean, already characterised by
facts 43/45 for alignment). Known-motion positive: `foam` (100, rejected from the
corpus because the scene visibly evolves).

- **A1 — the analytic null.** On the null stack, `mean z²` over all interior
  samples lands in **[0.5, 2.0]**. Fail **high** → the operator is reading
  defocus or breathing, not noise. Fail **low** → the window is interpolating
  the noise and the operator has no power. Model-aware expectation [1.00, 1.42]
  per §0.2.
- **A2 — detail flatness. This is the crux and M60's statistic failed it at
  5.11x.** On the null stack, `mean z²` in the **top** detail decile divided by
  `mean z²` in the **bottom** detail decile must be **< 2.0** at the primary
  setting. At or above 2.0 the operator is still substantially a sharpness
  detector and I must say so in the verdict block.
- **A3 — radial flatness (breathing).** On the null stack, `mean z²` in the
  outer radial octile over the inner must be **< 2.0**. M28 measured 1.82x for a
  whole-stack reference and 0.98 for an adjacent-frame one; a fourth difference
  should sit at or below the latter.
- **A4 — planted sensitivity and its placebo.** Three morphologies, all built by
  moving real content:
  - **A** transient: one frame's tile displaced by `s`, neighbours untouched;
  - **B** step: every frame from `k` onward displaced by `s`;
  - **C** ramp: displacement grows linearly from 0 to `s` across the stack.

  Detection (fraction of planted-tile samples with `|z| > 8`) must be
  **monotone non-decreasing in `s`** for morphology A, and **`s = 0` must land
  within 2x of the unplanted background rate**. Morphologies B and C are
  reported without a pass bar, because they measure the declared blind spot
  rather than the claim.
- **A5 — separation, at matched detail.** `foam`'s contaminated-sample fraction
  at `|z| > 8` must be **≥ 5x** the null stack's, computed **within matched
  detail deciles** and pooled by `min(n)` weighting (M60's A2' method, adopted
  because M60 measured a raw 12.88x collapse to 2.0–3.1x under exactly this
  correction). **A metric that cannot separate `foam` from a static stack is a
  failed metric and I will report that as the headline.**

### 0.5 Stage-B bars — the mask

Only run if Stage A passes A1 and A2. The weight, in **sigmas**, with a genuine
no-op region so that requirement B2 is achievable by design rather than by luck:

```text
w(z) = 1                                  |z| <= Z0
     = ((Z1 − |z|)/(Z1 − Z0))²            Z0 < |z| < Z1
     = 0                                  |z| >= Z1
```

`Z0 = 4`, `Z1 = 8`, both in units of the calibrated noise model. Under a clean
Gaussian null `P(|z| > 4) = 6.3e-5`, so the clean-data no-op is structural. The
constants are **sigmas, not DN**; nothing here is expressible in DN without the
noise model.

- **B0 — faithfulness control.** With the mask disabled, the merge implemented
  inside `m89-robust.rs` must reproduce `strehl_core::merge::Estimator`'s
  `green_mean` to **< 1e-3 DN** at every pixel. Without this, every A/B below is
  an A/B against a merge nobody ships. This bar can fail and is the first thing
  run.
- **B1 — the governing invariant.** Total admitted weight at every pixel must be
  **≥ 1.0**, so the merged estimate's predicted variance can never exceed a
  single frame's. Note this is *weaker* than M60's B1, which protected the
  **winner** specifically. I am deliberately **not** protecting the winner:
  §3.5 of my brief argues motion *attracts* the selector, so a rule that
  protects the winner protects the contaminated sample. Asserted in code.
- **B2 — the placebo, and it is required.** On the null stack the mask must
  remove **< 1%** of total admitted weight **and** move the merged green by RMS
  **< 0.10** predicted sigma. Above either, the mask is destroying real signal
  and must not ship.
- **B3 — it must act where the problem is.** Weight removed on `foam` must be
  **≥ 5x** the fraction removed on the null stack.
- **B4 — measured improvement, metric fixed in advance.** Ground truth does not
  exist for these captures, so the improvement metric is a **split-half
  disagreement**: merge the even frames and the odd frames independently, and
  score
  `H = mean over pixels of |M_even − M_odd| / sqrt(σ²_even/n_e + σ²_odd/n_o)`.
  A transient contaminates one half and not the other, so contamination inflates
  `H`; the mask must **reduce `H` on `foam` by ≥ 10%**, and must change `H` on
  the null stack by **< 2%** (the same metric, run as a placebo arm).
- **B5 — election versus average.** Three arms: (i) mask off; (ii) mask on the
  **average** only; (iii) mask on **both election and average**. B4 and B2 are
  reported for each. **Registered prediction, to be falsified:** arm (ii)
  recovers less than half of arm (iii)'s improvement in `H`, because a moved
  edge reads sharper and therefore wins the election.
- **B6 — planted defect in my own harness (rule 12).** The noise normalisation
  is deliberately removed from `z` (divide by 1 instead of by the model sigma).
  A1 must go **red**. Restore from a `$env:TEMP` copy — never
  `git checkout --`, which would destroy four sibling agents' uncommitted work —
  set `LastWriteTime` to now (rule 33), read the restored line back, and confirm
  A1 green again.

### 0.6 Rule 20 — what input would make each of these fail?

- **A1** fails if defocus is not order-`p` smooth over `w` frames. Such input
  exists and is cheap to produce: `p = 0` on the same data is exactly that
  input, and it is run as the negative-control operator.
- **A2** fails on any operator whose residual is proportional to local contrast.
  Such an operator exists and is measured: M60's chi2 read 5.11x, and `p = 0` is
  its temporal analogue.
- **A5** fails if `foam`'s excess is detail composition rather than motion —
  M60 measured exactly that collapse (12.88x → 2.0–3.1x) on a related statistic,
  so the failing input is not hypothetical, it is the corpus.
- **B2** fails for any weight function without a flat region, e.g. a Welsch/
  Geman-McClure `exp(−z²/2c²)`, which down-weights ~5% of *clean* samples at
  `c = 3`. That is the input, and it is the obvious design I am declining.
- **B4** fails if the mask reduces `H` on the null stack as much as on `foam`,
  which would mean it is a smoother rather than a rejector.

### 0.7 Read-only guarantee

`D:\personal\macro` and `D:\macro-dark-frames` are **read only**. Nothing in this
milestone opens either for writing. All output lands in
`experiments/M89-robustness/out/`.

### 0.8 Added mid-run: the `h^4` discriminator (registered before it was run)

Added after the corpus survey and before the run that tests it. Three stacks
came back inflated whose subjects are inanimate — `lead-1-cpl`, `flat-on-ruler-cpl`
and, in part, `tweezers-cpl` — with the inflation spread across *every* frame and
*most* tiles rather than concentrated. That is the signature of the one failure
mode that would void Deliverable A: **defocus leaking through the operator**
because the stack's focus step is too coarse for the window to be locally
quadratic.

A6 is therefore added as a bar. Defocus is smooth in frame index, so a fourth
difference of it scales as `h^4` in the focus step `h`. Subsampling the frame
list by `k` multiplies `h` by `k`, and therefore multiplies

* `z` by `k^4`, and so
* `z^2 - 1` by `k^8` — **256x at `k = 2`, 6561x at `k = 3`** —

for any inflation that is defocus leakage. A discrete disturbance obeys no such
law: subsampling by `k` keeps roughly `1/k` of the contaminated frames and does
not amplify each one, so `z^2 - 1` should stay the same order or fall.

**A6 registered, on the null stack.** Subsampling the null by `k = 2` must leave
`mean z^2` below **2.0**. If the null's tiny apparent excess were defocus
leakage, `k = 2` would multiply it by 256 and this would fail loudly. Passing it
bounds the leakage at `k = 1` to `1/256` of whatever `k = 2` shows.

**Registered diagnostic prediction, to be falsified.** I predict `lead-1-cpl`
and `flat-on-ruler-cpl` *are* defocus leakage and will show the `k^8` law, while
`foam` is *not* and will not. If `lead-1-cpl` fails to scale, my reading of it is
wrong and the report must say so.

---

## 1. Verdict

**The metric works and should be adopted. The mask, as specified, should not
ship — but the reason it fails is itself the most useful finding here.**

A leave-one-out fourth-difference residual along the frame axis, normalised by
the calibrated noise model, has an **analytic** null of `E[z^2] = 1` with zero
fitted constants. On a locked-down static stack it MEASURED **0.9897**, i.e.
within **1.03%** of a number nobody tuned. It is flat in detail to **1.173x**
across the full detail range, where M60's merge-time statistic varied **5.11x**
(M60 F5); defocus leakage into it is bounded at **<=0.04%** of `z^2` by a
registered scaling test. Applied to the owner's 23 real stacks it separates them
over a **2,486x** range in outlier rate, and the ordering is not the one the
brief assumed: **`foam` is 94.4x the null but only the 4th worst stack, and
`lead-1-cpl` is 248.6x with 29.1% of its pixels contaminated.**

The Wronski-style soft weight then **failed its own pre-registered benefit bar.**
B4 required a **>=10%** reduction in split-half disagreement on `foam`; masking
the average alone MEASURED **-0.311%**, and masking the election too MEASURED
**-5.21% on mean H while making p999 H 38.18% worse**. It also failed the strict
limb of its placebo (B2 RMS). **What passed, decisively, is the election
finding**: 4.78% of `foam`'s pixels currently elect a winning frame whose own
value is **>8 sigma** discrepant — motion literally wins the sharpness election —
and masking the election removes **100.000%** of them, while average-only masking
removes none. **So the brief's suspicion in §3.5 is confirmed and is the real
result: a robustness mask on the averaging stage alone recovers 6.0% of the
available benefit and is close to pointless.** The correct next step is not this
mask; it is to make the *election* robust, and to do it after alignment (M86),
because the residual that survives here is displacement, not noise.

---

## 2. The metric

### 2.1 What it computes

For each pixel and each frame `f`, predict that frame's green luma from its
temporal neighbours *excluding itself*, and ask how far the actual value is from
the prediction, in sigmas of the calibrated noise model:

```
z_f = ( L_f  -  sum_{j != f} k_j L_j )  /  sqrt( sum_j r_j^2 sigma^2(L_j) )
```

where `k` is the leave-one-out local-polynomial predictor of order `p` over a
window of `w` frames centred on `f`, and `r = (1, -k)` is the residual kernel.
For the primary operator `w=5, p=2` the residual kernel is exactly

```
r = [ 1, -4, 6, -4, 1 ] / 6          (the fourth difference)
sum r^2 = 70/36 = 1.9444
```

`sigma^2` is `strehl_core::noise`'s affine photon-transfer relation in DN,
evaluated with the gain and read noise measured for the stack's own ISO from
`strehl_core::profile`. **There is no threshold in DN anywhere in the
instrument.** The brief asked for that and it is honoured literally: the only
constants in the statistic are the kernel, which is arithmetic, and the noise
coefficients, which are measurements from this camera body.

### 2.2 How it separates motion from defocus — the actual technical problem

**This is the claim the whole milestone rests on, so it is argued and then
measured three separate ways.**

The separation is not a heuristic. Defocus, focus breathing, magnification
change and photometric drift are all **smooth and monotone in frame index** over
a short window: a focus bracket steps the focal plane in small even increments,
so a pixel's value traces a smooth through-focus curve. Motion, hot pixels and
transients are **not** smooth in frame index — they are discrete events.

A leave-one-out polynomial predictor of order `p` **annihilates any polynomial
of degree <= p in `f` exactly**, by construction. For `p=2, w=5` the residual
kernel `[1,-4,6,-4,1]/6` has `sum r_j = 0`, `sum j r_j = 0`, `sum j^2 r_j = 0`
and in fact `sum j^3 r_j = 0` — it kills cubics too. So a locally-cubic
through-focus curve contributes **identically zero** to `z`, at every pixel,
regardless of how much contrast that pixel has. A discrete disturbance at one
frame does not cancel and contributes in full.

That is the design. Three independent measurements confirm it does what the
algebra says:

**(a) Flatness in detail (MEASURED).** If defocus were leaking, `z^2` would rise
with local detail, because defocus's disagreement is proportional to contrast
and noise's is not. On the null stack (299 frames), `z^2` across the ten detail
deciles reads

```
0.967 0.968 0.969 0.969 0.969 0.968 0.967 0.975 1.008 1.134
```

a **hi/lo ratio of 1.173**. The comparison that matters: **M60's merge-time
disagreement statistic varied 5.11x with detail on clean data** (M60 F5), which
is exactly why M60 declined to build the mask. This statistic is **~24x flatter
in the quantity that defeated M60**, and it is flat because of an algebraic
annihilation rather than a correction.

**(b) The order sweep (MEASURED).** Dropping the polynomial order from `p=2` to
`p=0` — i.e. replacing the fourth difference with a plain running-mean residual,
which is what a naive implementation would do — makes the null's detail ratio
jump from **1.173 to 1.939**, its `mean z^2` from **0.990 to 1.083**, and its
`>8 sigma` outlier rate from **3.02e-5 to 3.47e-4, an 11.5x inflation on a
stack where nothing moved.** On `foam` the detail ratio goes from **5.71 to
18.77** and `mean z^2` from **2.03 to 6.51**. **The polynomial order is
demonstrably the thing doing the separation, and its effect is measurable by
turning it off.**

**(c) The frame-subsampling scaling law, A6 (MEASURED, registered in advance).**
This is the strongest of the three because it was registered before it was run.
A degree-4 residual of a smooth curve scales as `h^4` in the sample spacing, so
its *contribution to `z^2`* scales as `h^8`. Subsampling the stack by `k` frames
therefore multiplies any genuine defocus leakage by `k^8` — **256x at `k=2`**.
A discrete disturbance obeys no such law. Registered bar: the null at `k=2` must
stay below `mean z^2 = 2.0`.

```
null, k=1: 0.990     k=2: 1.0929     k=3: 1.2813
```

**A6 PASSES.** The null's excess at `k=2` is 0.0929, so leakage at `k=1` is at
most `0.0929 / 256 = 3.6e-4`, i.e. **defocus contributes at most 0.04% of the
null's `z^2`.** That is a hard bound on the trap the brief warned about, and it
is the number I would want a reviewer to check first.

**My registered diagnostic prediction inside A6 was FALSIFIED** — see §7.3. I
predicted `lead-1-cpl` and `flat-on-ruler-cpl` were defocus leakage and would
show the `k^8` law. They do not: their `z^2 - 1` ratios from `k=1` to `k=2` are
**1.80x** and **6.98x**, nowhere near 256x. Defocus leakage explains **none** of
the inflated stacks. I was wrong about the mechanism and the test I registered
to catch me caught me.

### 2.3 What it is blind to, declared in advance

Registered in §0.2 before any run, and confirmed by the plant in §7.2:

- **Anything smooth in frame index of order <= 3.** A slow drift, a monotone
  illumination ramp, or a subject creeping steadily across the frame at constant
  velocity is invisible to this operator. The plant confirms it: a planted
  *ramp* at shift `s=64` moved the at-frame flag rate to **0.0** — completely
  blind, as declared.
- **Contamination affecting all frames identically** (fixed-pattern, dust in
  sensor coordinates, a stuck pixel present in every frame) cancels in the
  difference. This is a real blind spot and it is the one that matters for dust.
- **The window edges.** The first and last `(w-1)/2` frames have no centred
  window and are not scored.

---

## 3. The null

**Stack:** `highly-angled-ruler-mm-cpl`, 299 frames, ISO 100 — a printed
millimetre ruler on a locked-down tripod, an inanimate subject, the closest
thing in the corpus to a guaranteed-static capture.

| quantity | predicted | MEASURED | bar | verdict |
|---|---|---|---|---|
| `mean z^2` | **1.000 exactly** (analytic) | **0.9897** | A1: `[0.5, 2.0]` | **PASS**, 1.03% off |
| detail hi/lo | 1.0 | **1.173** | A2: `< 2.0` | **PASS** |
| radial out/in | 1.0 | **0.993** | A3: `< 1.5` | **PASS** |
| `>8 sigma` rate | ~0 | **3.021e-5** | — | reference for all other stacks |

**The 1.000 is not a fit.** It is what `E[z^2]` must equal if the scene is
static, the through-focus curve is locally cubic, and the noise model is right.
Landing at 0.9897 means all three hold simultaneously on this stack to about
1%. I know of no way to get that number by accident.

**My rule-30 registered prediction FAILED and this is the interesting part.**
I predicted `E[z^2]` in **[1.00, 1.42]**, biased *high*, reasoning from fact
1064 (the noise model is slightly over-confident) and M72 (green channels are
positively correlated). It MEASURED **0.9897 — below the interval**, so the
excess I predicted is absent and something is *deflating* `z^2`.

DERIVED explanation: for any kernel with `sum r_j = 0`,
`sum_{j<k} r_j r_k = -(sum r_j^2)/2`. So a uniform positive frame-to-frame
common-mode correlation `rho` scales `E[z^2]` by exactly `(1 - rho)`. The
measured 0.9897 implies **`rho ~ 0.0103`**, about 1% common-mode between frames
— consistent with black-level jitter or row banding, both of which are frame-wide
and would be shared. **This is honestly degenerate with a 0.5% scale error in
the noise model** and I cannot separate the two from this measurement. Either
way the bias is ~1% and does not affect any conclusion below.

### 3.1 The second null, and the awkward result

`flowers-cpl` (176 frames, ISO 100, **live plant material**) was expected to be
the *dirty* control. It MEASURED **`mean z^2 = 0.972`, `>8 sigma` rate 3.169e-6
— 0.1x the ruler, the cleanest stack in the whole corpus.** Live botanical
subject matter under a polariser on a still night is *quieter* than a printed
ruler. This is a fact worth carrying forward because it refutes the intuition
that organic subjects imply motion.

`coffee-bean` was the intended *secondary* null and read **3.26** — worse than
`foam`. §4.2 shows why, and it is not a failure of the metric.

---

## 4. The contamination survey

23 stacks, primary operator `w=5, p=2`, ranked by `>8 sigma` sample rate
relative to the null (null = 1.0x). `flag%` is the fraction of pixels with at
least one flagged frame; `wF/med` is the worst frame's flag rate over the
median frame's.

| stack | n | ISO | `mean z^2` | `>8 sig` | **x null** | flag% | worst f | wF/med |
|---|---|---|---|---|---|---|---|---|
| lead-1-cpl | 123 | 100 | 3.265 | 7.51e-3 | **248.6** | 29.11 | 50 | 95.3 |
| coffee-bean | 105 | 50 | 3.261 | 3.63e-3 | **120.2** | 20.19 | 26 | 99.3 |
| coffee-bubbles | 19 | 1000 | 2.062 | 2.86e-3 | 94.6 | 1.74 | 6 | 3.0 |
| **foam** | 100 | 1000 | 2.033 | 2.85e-3 | **94.4** | 12.56 | 41 | **12263.5** |
| flat-on-ruler-cpl | 79 | 100 | 1.991 | 2.32e-3 | 76.9 | 10.74 | 25 | 18.4 |
| tweezers-cpl | 100 | 100 | 1.722 | 2.28e-3 | 75.5 | 11.20 | 40 | 136.8 |
| 119MSDCF | 33 | 50 | 1.415 | 8.66e-4 | 28.7 | 0.97 | 16 | 48.3 |
| wrapped-text-1 | 130 | 100 | 1.320 | 7.12e-4 | 23.6 | 7.43 | 2 | **868.8** |
| dry-erase-marker-head-cpl | 299 | 100 | 1.035 | 3.47e-4 | 11.5 | 4.55 | 138 | 67.9 |
| bee-1-cpl | 299 | 100 | 1.431 | 2.64e-4 | 8.7 | 4.16 | 42 | 28.3 |
| bee-3-cpl | 299 | 100 | 1.154 | 2.12e-4 | 7.0 | 3.50 | 117 | 46.6 |
| 113MSDCF | 63 | 500 | 1.274 | 2.09e-4 | 6.9 | 0.74 | 35 | 31.5 |
| 112MSDCF | 79 | 500 | 1.127 | 9.24e-5 | 3.1 | 0.36 | 27 | 814.5 |
| wrapped-text-2 | 120 | 400 | 1.128 | 8.56e-5 | 2.8 | 0.67 | 62 | 111.5 |
| flower-bud-with-background-fern-cpl | 299 | 100 | 1.015 | 8.17e-5 | 2.7 | 1.40 | 40 | 75.8 |
| leaf-2-cpl | 182 | 400 | 1.091 | 5.13e-5 | 1.7 | 0.69 | 59 | 2392.6 |
| bee-2-cpl | 299 | 400 | 1.030 | 3.84e-5 | 1.3 | 0.72 | 134 | 107.4 |
| flower-bud-alone-cpl | 205 | 100 | 1.005 | 3.71e-5 | 1.2 | 0.36 | 120 | 99.3 |
| lavendar-cpl | 299 | 200 | 0.995 | 3.31e-5 | 1.1 | 0.55 | 74 | 203.9 |
| 109MSDCF | 22 | 160 | 1.115 | 3.18e-5 | 1.1 | 0.04 | 10 | 34.4 |
| **highly-angled-ruler-mm-cpl (null)** | 299 | 100 | **0.990** | 3.02e-5 | **1.0** | 0.55 | 40 | 12.9 |
| couch-fibers-cpl | 299 | 400 | 1.002 | 1.80e-5 | 0.6 | 0.33 | 76 | 128.3 |
| flowers-cpl | 176 | 100 | 0.972 | 3.17e-6 | **0.1** | 0.04 | 7 | inf |

**Headline: the corpus spans 2,486x** from `flowers-cpl` to `lead-1-cpl`.
Contamination is real, it is common — 8 of 23 stacks exceed 20x the null — and
it is **not** distributed the way the brief assumed.

### 4.1 `foam` is not the worst stack, but it is the most *localised* one

`foam` is 4th by rate. What is unique about it is **temporal concentration**:
its worst frame flags at **12,263x the median frame**, against 12.9x for the
null and 95-137x for `lead-1-cpl` and `tweezers-cpl`. Frames **38-47 form one
contiguous event block**:

```
frame 41  3.27e-2   frame 42  2.79e-2   frame 40  2.49e-2   frame 39  2.25e-2
frame 43  1.91e-2   frame 38  1.79e-2   frame 44  1.50e-2   frame 47  1.24e-2
```

That is the shape of a discrete physical event lasting ~10 frames, exactly what
"the bubbles moved" should look like. Its spatial profile is compact too: worst
64px tile 0.754, p99 tile 0.437, **median tile 0.101** — so most of the frame is
fine and a tenth of it is destroyed. **`foam` is the archetype the mask was
designed for, and the metric localises it in both axes without being told
anything.**

`wrapped-text-1` is the textbook single-frame transient: **frame 2 alone at
869x the median**, everything else quiet, median tile 0.0046. A rejection scheme
would fix that stack completely.

### 4.2 Correcting for detail composition — the M60 objection, quantified

Different stacks contain different amounts of detail, and `>8 sigma` rates rise
with detail even on clean data. So the raw 94.4x for `foam` mixes contamination
with "foam has more texture than a ruler". I added an **absolute detail-SNR
axis** (local contrast in sigmas, so it is comparable across ISO) and re-ran the
comparison **within matched SNR bins**:

| detail-SNR bin | null rate | foam rate | ratio |
|---|---|---|---|
| 0.5 | 1.77e-9 | 3.76e-6 | 2122.9 |
| 1.0 | 8.89e-7 | 3.90e-5 | 43.9 |
| 2.0 | 1.39e-5 | 2.24e-4 | 16.2 |
| 4.0 | 8.17e-5 | 1.17e-3 | 14.3 |
| 8.0 | 3.46e-4 | 4.14e-3 | 12.0 |
| 16.0 | 1.77e-3 | 1.14e-2 | 6.5 |
| 32.0 | 4.27e-3 | 2.45e-2 | 5.7 |
| 64.0 | 1.55e-2 | 3.70e-2 | 2.4 |

**Matched ratio: 11.6x** (min(n)-weighted), against a raw ratio of 94.4x.
DERIVED: **about 8x of the apparent cross-stack signal is detail composition,
not contamination.** Bar A5 required >=5x and **PASSES**. This both confirms
M60's warning and puts a number on it: M60 was right that detail confounds this
comparison, and the confound is a factor of ~8, not a factor that erases the
effect.

### 4.3 Which mechanism? A second, independent instrument

To attribute inflation to *global illumination change* rather than motion, I
built a second mode (`levels`) that measures the fourth difference of each
frame's **global mean level** — touching none of the survey's per-pixel
machinery. If drift is multiplicative and uniform, it predicts

```
E[z^2] = 1 + S^2 d4^2 / ( sum r^2 (gS + rn^2) )
```

| stack | p-p% | d4 rms | MEASURED `z^2` | predicted photometric | photometric share |
|---|---|---|---|---|---|
| lead-1-cpl | 2.02 | 7.90e-4 | 3.265 | 1.001 | **0.1%** |
| coffee-bean | 12.34 | 6.90e-3 | 3.261 | 2.284 | **56.8%** |
| coffee-bubbles | 15.71 | 1.84e-2 | 2.062 | 1.044 | 4.1% |
| **foam** | 21.25 | 4.46e-3 | 2.033 | 1.008 | **0.7%** |
| flat-on-ruler-cpl | 5.94 | 2.76e-4 | 1.991 | 1.000 | 0.0% |
| tweezers-cpl | 13.77 | 2.11e-4 | 1.722 | 1.001 | 0.1% |
| wrapped-text-1 | 1.32 | 1.86e-3 | 1.320 | 1.023 | 7.1% |
| 109MSDCF | **0.91** | 2.51e-3 | 1.115 | 1.025 | 21.4% |
| ruler (null) | 14.62 | **2.14e-4** | 0.990 | 1.000 | n/a |

Three things fall out:

1. **`109MSDCF`'s peak-to-peak level swing MEASURES 0.9102%**, independently
   reproducing the **0.91%** photometric-drift figure the corpus already cites in
   `crates/strehl-core/src/merge.rs` ~line 663. Two different instruments, same
   number — a useful cross-check on both.
2. **The null has a *larger* peak-to-peak swing (14.62%) than `coffee-bean`
   (12.34%) yet a 32x smaller fourth difference.** That is the annihilation
   working in the open: a smooth ramp of any amplitude is removed, and only the
   non-smooth part survives. It is the cleanest single demonstration in this
   report that the operator does what §2.2 claims.
3. **`foam` is 0.7% photometric** — essentially all of its inflation is genuine
   spatially-structured disagreement. **`coffee-bean` is 56.8% photometric**,
   which is why the intended secondary null read high: it is not motion, it is a
   flickering light, and a robustness mask is the wrong tool for it.

**The photometric model breaks down on three stacks and I am reporting it rather
than dropping them:** `bee-1-cpl` predicts a 201.2% share (residual **-0.436**,
i.e. it over-predicts the total), and `bee-3-cpl` (97.6%), `couch-fibers-cpl`
(69.6%) and `bee-2-cpl` (73.0%) predict shares near or above the whole measured
excess. The model assumes the level change is *uniform across the frame*; when
the global mean is driven by a moving specular highlight or a bright localised
region, the global `d4` overstates the typical pixel's. **So the photometric
share is only trustworthy where it comes out well below 100%**, and the four
stacks above are unattributed.

---

## 5. The mask

### 5.1 Design

```
w(z) = 1                              for |z| <= 4
w(z) = ((8 - |z|) / (8 - 4))^2        for 4 < |z| < 8
w(z) = 0                              for |z| >= 8
```

Three properties, each a requirement from the brief:

1. **The knees are in sigmas of the calibrated noise model, not DN.** `z` is
   the §2.1 statistic; its denominator is `strehl_core::noise` evaluated at the
   stack's own measured ISO gain and read noise. **There is not one DN constant
   in the mask.** A 4-sigma knee at ISO 100 in shadow is a completely different
   DN threshold from 4 sigma at ISO 1000 in highlight, and that is the point.
2. **It is soft**, and `C^1` at both knees (the squared ramp has zero derivative
   at `z=8` and the value-and-slope match is what avoids the blotching a binary
   mask produces).
3. **It degrades to the unmasked merge.** If every sample at a pixel is
   down-weighted to nothing, the code falls back to the unmasked accumulation
   rather than emitting a hole. Bar B1 requires the total weight at every pixel
   to be `>= 1.0` sample-equivalent, and it MEASURED **exactly 1.000 on all
   three stacks**.

### 5.2 The three arms

| arm | election | average |
|---|---|---|
| 0 | unmasked | unmasked (**this is the shipped merge**) |
| 1 | unmasked | masked |
| 2 | masked (`w >= 0.5` to be eligible) | masked |

Arm 0 exists to prove the harness reproduces the shipped code, which is bar B0.

### 5.3 B0 — is this file actually merging the way `strehl` merges?

**This is the bar that makes every other number in §5 mean anything**, because a
private re-implementation that quietly differs from the library measures a
difference that will never exist in the product.

| check | null | flowers-cpl | foam |
|---|---|---|---|
| B0a: winner matches `FocusStats::best_index` | **100.000000%** | **100.000000%** | **100.000000%** |
| B0b: `n_eff` matches `Estimator::n_eff` | **100.000000%** | **100.000000%** | **100.000000%** |
| B0c: green vs `Estimator::green_mean` | max 4.88e-4 DN | max 4.88e-4 DN | max 9.77e-4 DN |

**All PASS** (B0c bar was `< 1e-3` DN; the residue is f32 accumulation order in
two different summation loops, not a logic difference). Arm 0 is the shipped
merge, bit-for-bit in the election and to a thousandth of a DN in the value.

### 5.4 B2 — the placebo, on clean data. It half-failed.

Registered: on a clean stack the mask must remove `< 1%` of admitted weight and
move the merged green by `< 0.10 sigma` RMS.

| | null (ruler, 120) | flowers-cpl (120) | bar |
|---|---|---|---|
| weight removed, arm 1 / arm 2 | **0.00356% / 0.00456%** | **0.00390% / 0.00467%** | `<1%` **PASS** |
| RMS move, arm 1 / arm 2 | **0.307 / 0.607 sigma** | **0.127 / 0.352 sigma** | `<0.10 sigma` **FAIL** |
| pixels moved > 0.01 sigma | 0.364% / 0.431% | 0.158% / 0.213% | — |
| max move | 72.6 / 254.1 sigma | 41.8 / 76.9 sigma | — |

**The weight limb passes by 200x. The RMS limb fails by 3-6x, and I am
reporting it as a failure.** But the two limbs disagree so violently that the
disagreement is itself the finding, so here is the honest reading of both sides:

- **Reading 1 (the mask destroys real signal).** 0.3 sigma RMS on a static stack
  is not nothing, and the brief's criterion 3 says a mask that materially changes
  clean output must not ship. Taken at face value, B2 says exactly that.
- **Reading 2 (RMS is the wrong summary).** **99.64% of pixels move less than
  0.01 sigma.** The RMS is carried entirely by ~0.36% of pixels, and it is
  dominated by a 72-sigma maximum. A distribution where a thousandth of the mass
  produces the whole statistic is not described by its RMS. Those pixels are
  where the mask found genuine >8-sigma disagreements *on a stack I called
  clean* — the null's own `>8 sigma` rate is 3.02e-5, not zero.

I registered RMS and I am not retuning it after the fact. **The bar failed.**
What I will say is that if I were registering it again I would register the
median and the 99.9th percentile separately, because those two numbers answer
"does it leave clean pixels alone" and "how hard does it hit the outliers" and
RMS answers neither. That is stated as a change I would make, not a change I
made.

### 5.5 B4 — the benefit, on contaminated data. It failed.

The pre-declared benefit metric is **split-half disagreement `H`**: split the
frames into evens and odds, merge each half independently, and measure
`|green_even - green_odd|` in sigmas. Contamination inflates `H` because a
disturbance lands in one half and not the other. Pure noise gives
`E[H] = sqrt(2/pi) = 0.7979`.

Registered: **arm 2 must reduce mean `H` on `foam` by `>= 10%`.**

| | arm 0 (shipped) | arm 1 (avg only) | arm 2 (both) |
|---|---|---|---|
| mean H | 3.47361 | 3.46281 | **3.29264** |
| median H | 1.55404 | 1.54831 | 1.48951 |
| p99 H | 30.8617 | 31.0576 | **33.9257** |
| p999 H | 60.2791 | 60.6932 | **83.2924** |
| frac H>5 | 1.787e-1 | 1.768e-1 | 1.522e-1 |

```
arm 1:  -0.311% on mean H      +0.687% on p999 H
arm 2:  -5.210% on mean H     +38.178% on p999 H
```

**B4 FAILS.** Arm 2 delivers **-5.21%** against a registered **-10%**, and it
makes the *tail* substantially worse: **p999 `H` degrades by 38.18%.** Arm 1
does essentially nothing at all.

I want to be careful about what this does and does not show. It does **not**
show the mask is doing nothing — §6 shows it is doing something large and
specific. What it shows is that **down-weighting outliers in the merge does not
make the two halves of `foam` agree**, and the mechanism is visible: when a
disturbance spans frames 38-47, the even half and the odd half each contain
*five* contaminated frames. Masking removes different samples from each half and
the halves can end up electing genuinely different frames, which moves the tail
apart rather than together. `H` measures agreement, and a mask that legitimately
changes both halves' answers in different directions scores badly on it even
when each answer improved.

**`H` is also a weak metric in an absolute sense, and I should say so.** On the
null it reads mean 1.278 against a pure-noise expectation of 0.798 — a **60%
floor** that has nothing to do with contamination and everything to do with the
two halves electing different frames at ambiguous pixels. And **`flowers-cpl`,
the cleanest stack in the corpus by `>8 sigma` rate, has `H` mean 2.303 — higher
than `foam`'s median and nearly double the ruler's** — because it has more
detail. So `H` is contaminated by exactly the detail confound §4.2 measured.
**I registered it in advance and I am reporting its verdict as it stands, but
its floor and its detail-dependence are reasons to treat B4's failure as
"unproven benefit" rather than "proven harm".**

---

## 6. Election versus average — the brief's §3.5, and the real result

The brief predicted that a mask on the averaging stage alone might not help,
because a moved edge reads *sharper* and therefore attracts the focus election.
**That prediction is confirmed, quantitatively, and it is the strongest finding
in this milestone.**

### 6.1 Motion wins the election

I instrumented the shipped merge (arm 0) to count **hot winners**: pixels whose
*elected winning frame* has `|z| > 8` at that very pixel. That is a pixel whose
final value is taken from a frame the metric says is contaminated there.

| stack | hot winners, arm 0 | as % of pixels | arm 2 |
|---|---|---|---|
| null (ruler) | 4,752 | 0.0576% | **0** |
| flowers-cpl | 1,323 | 0.0160% | **0** |
| **foam** | **394,129** | **4.78225%** | **0** |

**MEASURED: 4.78% of `foam`'s output pixels currently take their value from a
frame that disagrees with its neighbours by more than 8 sigma.** Nearly one
pixel in twenty. The election is not merely failing to defend against motion —
it is actively selecting it, exactly as the brief argued. Masking the election
(arm 2) drives this to **exactly 0 on all three stacks**.

### 6.2 How much does the election matter, relative to the average?

Masking the election changes the elected winner at:

```
null         0.163% of pixels
flowers-cpl  0.079% of pixels
foam         9.116% of pixels        (5,252,856 frame-samples ruled ineligible)
```

And the effect on the output:

```
arm 1 (average only)   moves the merged green rms 1.439 sigma on foam
arm 2 (both)           moves the merged green rms 8.712 sigma on foam
```

Registered bar **B5**: I predicted arm 1 would deliver **less than 50%** of arm
2's `H` benefit. **MEASURED: arm 1 delivers 0.311/5.210 = 6.0%** of arm 2's mean-`H`
improvement. **The prediction is confirmed with room to spare.**

**DERIVED conclusion: a robustness mask applied only to the averaging stage
recovers ~6% of the available benefit and removes 0% of the hot winners. It is
close to useless on its own.** Any future implementation must mask the election
or not bother. This is the single most actionable sentence in this report.

### 6.3 The honest counterweight

Arm 2 does the structurally right thing (0 hot winners) and still fails B4, and
one further measurement shows why the picture is genuinely mixed: on `foam`,
arm 0 has 442,212 hot *admitted* samples and **arm 2 has 910,697** — masking the
election shifts the winner to a different frame, whose tolerance band then admits
a *larger* set of samples that are themselves discrepant. The mask removes the
contaminated *winner* and then averages over a wider, dirtier neighbourhood.
**That is a real defect in arm 2 as constructed, and it is the most likely
explanation for the 38% p999 `H` regression.** A correct implementation should
re-derive the admission tolerance from the masked election rather than reusing
the unmasked band's width, and that is a design change, not a tuning change.

---

## 7. Bars: what passed, what failed, and the planted defect

### 7.1 The register

| bar | registered before? | criterion | MEASURED | verdict |
|---|---|---|---|---|
| **A1** null `mean z^2` | yes | in `[0.5, 2.0]` | **0.9897** | **PASS** |
| **A2** null detail flatness | yes | hi/lo `< 2.0` | **1.173** | **PASS** |
| **A3** null radial flatness | yes | out/in `< 1.5` | **0.993** | **PASS** |
| **A4** plant monotonicity | yes | strictly increasing in shift | 6.10e-4 -> 6.38e-1 | **PASS** |
| **A4** plant placebo (flat ROI) | yes | null at all shifts | **exactly 0.0** | **PASS** |
| **A4** placebo sub-bar (`s=0` vs bkgd) | yes | `< 2x` | **26.5x** | **FAIL** (§7.4) |
| **A5** foam/null at matched detail | yes | `>= 5x` | **11.6x** | **PASS** |
| **A6** null at `k=2` | yes | `< 2.0` | **1.0929** | **PASS** |
| **A6** diagnostic prediction | yes | lead-1 shows `k^8` | **1.80x, not 256x** | **FALSIFIED** (§7.3) |
| **rule-30** prior interval | yes | `E[z^2]` in `[1.00, 1.42]` | **0.9897** | **FAILED** (§3) |
| **B0a/b/c** faithfulness | yes | 100% / 100% / `<1e-3` DN | 100% / 100% / 9.77e-4 | **PASS** |
| **B1** min total weight | yes | `>= 1.0` | **1.000** | **PASS** |
| **B2** weight removed, clean | yes | `< 1%` | **0.0046%** | **PASS** |
| **B2** RMS move, clean | yes | `< 0.10 sigma` | **0.307 sigma** | **FAIL** (§5.4) |
| **B3** weight ratio foam/clean | yes | `>= 5x` | **2153x / 2751x** | **PASS** |
| **B4** `Delta H` clean | yes | `< 2%` | **-0.21% / -0.23%** | **PASS** |
| **B4** `Delta H` foam | yes | `>= 10%` improvement | **-5.21%** | **FAIL** (§5.5) |
| **B5** arm1 < half of arm2 | yes | `< 50%` | **6.0%** | **CONFIRMED** |
| **B6** planted defect caught | yes | A1 must go red | **321.65 vs 2.0** | **PASS** (§7.5) |

**Five registered criteria failed: A4's placebo sub-bar, A6's diagnostic
prediction, the rule-30 prior interval, B2's RMS limb, and B4's benefit bar.
None were retuned and none were dropped.** Two of the five (A6's prediction and
the rule-30 interval) refuted my own stated understanding of the mechanism, and
the corrected understanding is in §2.2 and §3.

### 7.2 The plant (A4) — a defect I injected and had to detect

On the **null** stack (so that anything detected is mine), pick a tile
programmatically as the highest-`box|grad|` tile in the frame, and at frame 60
replace the tile with the same tile shifted by `s` pixels — a synthetic subject
motion of known magnitude. Tile choice was by the detail axis, not by eye:
detailed tile `(1792,1472)` mean `box|grad|` **84.47**; flat control tile
`(3264,320)` mean `box|grad|` **7.28**.

At-frame `>8 sigma` rate versus shift:

| s | 0 | 1 | 2 | 4 | 8 | 16 | 32 |
|---|---|---|---|---|---|---|---|
| detail ROI | 6.10e-4 | 2.42e-2 | 9.33e-2 | 1.57e-1 | 2.39e-1 | 5.16e-1 | 6.38e-1 |
| **flat ROI** | **0.0** | **0.0** | **0.0** | **0.0** | **0.0** | **0.0** | **0.0** |

**Strictly monotone, detecting a 1-pixel shift at 40x the unplanted rate.** And
the flat-ROI control is **exactly 0.0 at every shift up to 32 px** — shifting a
featureless region produces no signal, which is the correct answer and as clean
a placebo as this project is likely to get.

Morphology also behaves as declared: a **step** (all frames after 60 shifted)
is detected at 8.53e-2 for `s=4`, a **ramp** (gradual over many frames) reads
**6.10e-4 / 6.10e-4 / 0.0** for `s = 4 / 16 / 64` — **completely invisible, as
declared in §0.2 and §2.3.** The instrument is blind to slow drift and I knew
that before I ran it.

### 7.3 A6's diagnostic prediction, falsified

I predicted the inflated stacks were defocus leakage and would show the `k^8`
scaling law. Ratios of `z^2 - 1` from `k=1` to `k=2`:

| stack | k=1 | k=2 | k=3 | `(z^2-1)` k2/k1 | required if defocus |
|---|---|---|---|---|---|
| null | 0.990 | 1.0929 | 1.2813 | (3.03 for k3/k2) | 256x / 25.6x |
| lead-1-cpl | 3.265 | 5.078 | 6.616 | **1.80x** | 256x |
| flat-on-ruler-cpl | 1.991 | 7.914 | 17.285 | **6.98x** | 256x |
| foam | 2.033 | 7.405 | 17.400 | **6.20x** | 256x |

**Nothing is near 256x. My prediction is falsified and defocus leakage explains
none of the inflated stacks.** The null's own residual excess also fails the
law (k3/k2 = 3.03 against a predicted 25.6), consistent with it being the ~1%
common-mode of §3 rather than defocus.

ARGUED replacement reading, offered as a hypothesis and not a finding: 6-7x is
what you get if disagreement grows with *time separation* — subject displacement
accumulating between frames, with disagreement roughly proportional to
displacement squared. `lead-1-cpl`'s **1.80x** says it is already saturated at
`k=1`, which fits a per-frame random disturbance (vibration, a fan, a footstep)
rather than drift. **That is the opposite of what I predicted for that stack**,
and it would be worth a milestone to test properly.

### 7.4 A4's placebo sub-bar, failed — a mis-specified reference

I registered that the `s=0` (unshifted) tile rate must be within **2x** the
background rate. MEASURED: tile 8.345e-4 vs whole-frame background 3.150e-5, a
**26.5x** ratio. **FAIL.**

Diagnosis, and I think the bar was wrong rather than the instrument: the bar
compared the **most detailed tile in the entire frame** against the
**whole-frame** background. §4.2 measures that flag rate rises with detail even
on clean data, by ~3 orders of magnitude from the lowest to the highest SNR bin,
so a 26.5x ratio between the frame's most detailed tile and the frame average is
expected and is not evidence of a defect. Independently, `s=0` is **provably the
identity operation** — the plant copies the tile to itself, with margin
`size + 64` guaranteeing the source stays in-frame — so the `s=0` row *is* the
unplanted tile rate by construction. **I registered a bar against the wrong
reference. The right reference was the same tile unplanted, which is the number
I measured.** Reported as a failure regardless.

### 7.5 B6 — the planted bug, and confirmation the harness catches it

**Required by the brief and by rule 9: build a check that could catch me.**

I deliberately broke the one thing the whole milestone depends on — the noise
normalisation — by clamping the denominator of `z` to 1.0 so the residual is
reported in raw DN instead of sigmas. Everything else was untouched. Then I
re-ran the null.

| | healthy | **sabotaged** |
|---|---|---|
| null `mean z^2` | **0.9897** | **321.65** |
| null `>8 sigma` rate | 3.02e-5 | **0.861** |
| A1 verdict | PASS | **FAIL by 161x** |

**A1 goes red by a factor of 161 and the `>8 sigma` rate goes from 3 in 100,000
to 86%.** The failure signature is also diagnostic rather than merely loud: the
sabotaged run's `z^2`-by-level row reads **238 -> 286 -> 640**, rising with
signal level exactly as an un-normalised residual must, since variance scales
with signal. A reader would not merely see it fail, they would see *why*.

**Restoration was done from a SHA256-verified backup, never `git checkout`**, as
the brief required (`git checkout --` would have reverted to HEAD and could have
destroyed a sibling agent's uncommitted work in the shared tree). Backup
`experiments/M89-robustness/m89-robust.rs.bak`, SHA256
`C59648FA...7842E314`; the restored file hashes identically, the `z_at` line
reads `num / (av.a * vs + av.b * op.r2_sum).sqrt()`, and the rebuilt binary
re-measures the null at **0.9874** (60 frames), green again.

---

## 8. Candidate facts

Numbered `P<n>` for the orchestrator to renumber on fold-in (rule 28: no
absolute fact numbers from a milestone). Each is self-contained.

**The instrument**

- **P1** (DERIVED) A leave-one-out local-polynomial residual along the frame axis,
  `z_f = (L_f - sum_{j!=f} k_j L_j) / sqrt(sum_j r_j^2 sigma^2(L_j))` with the
  order-2 five-frame kernel `r = [1,-4,6,-4,1]/6` and `sigma^2` from the
  calibrated noise model, has an analytic expectation of `E[z^2] = 1` under
  "static scene, through-focus response locally cubic in frame index,
  independent sensor noise", with **zero fitted constants and no threshold in
  DN**.
- **P2** (MEASURED) On `highly-angled-ruler-mm-cpl` (299 frames, ISO 100,
  locked-down tripod, inanimate subject) that statistic reads
  **`mean z^2 = 0.9897`**, 1.03% from its analytic value of exactly 1.000.
- **P3** (MEASURED) The same statistic varies only **1.173x** across the ten
  local-detail deciles of a clean stack, where M60's merge-time disagreement
  statistic varied **5.11x** (M60 F5) — roughly **24x flatter in the
  detail-dependence that caused M60 to decline to build the mask**.
- **P4** (MEASURED, registered in advance as bar A6) Subsampling the null stack
  by `k=2` — which multiplies any genuine defocus leakage by `k^8 = 256` —
  raises `mean z^2` only from 0.990 to **1.0929**, bounding defocus's
  contribution at `k=1` to **`<= 3.6e-4`, i.e. `<= 0.04%` of `z^2`**.
- **P5** (MEASURED) Reducing the predictor order from `p=2` to `p=0` (a plain
  running-mean residual, i.e. the naive implementation) inflates the clean
  stack's detail-dependence from **1.173x to 1.939x** and its false `>8 sigma`
  rate from **3.02e-5 to 3.47e-4 (11.5x, on a stack where nothing moved)**, and
  inflates `foam`'s detail-dependence from **5.71x to 18.77x**, demonstrating
  that the polynomial annihilation, not any tuning, is what separates defocus
  from motion.
- **P6** (DERIVED) For any residual kernel with `sum r_j = 0` it holds that
  `sum_{j<k} r_j r_k = -(sum r_j^2)/2`, so uniform frame-to-frame common-mode
  correlation `rho` scales `E[z^2]` by exactly `(1 - rho)`; the measured 0.9897
  therefore implies **`rho ~ 0.0103`** (~1% common-mode, e.g. black-level jitter
  or row banding) — degenerate with a 0.5% scale error in the noise model.
- **P7** (DERIVED) A recurrent hot pixel or any fixed-pattern defect present
  identically in every frame is **annihilated exactly** by this operator, since
  the residual kernel sums to zero. This is consistent with hot pixels being
  absent from the survey's outlier population and corroborates M22's finding
  that they are nearly harmless; it is also a genuine blind spot for
  sensor-coordinate dust.

**The contamination survey**

- **P8** (MEASURED) Across 23 of the owner's real stacks the `>8 sigma`
  contamination rate spans **2,486x**, from `flowers-cpl` at 0.1x the null to
  `lead-1-cpl` at 248.6x; **8 of 23 stacks exceed 20x the null**. Focus-only is
  not a safe assumption for this corpus.
- **P9** (MEASURED) **`lead-1-cpl` is the most contaminated stack in the corpus**
  — 248.6x the null, `mean z^2 = 3.265`, with **29.1% of its pixels flagged** —
  and it was not previously identified as a problem stack.
- **P10** (MEASURED) **`foam`, the stack known to have moved, is only the 4th
  worst by rate (94.4x the null, 12.6% of pixels flagged)**; what distinguishes
  it is temporal concentration — its worst frame flags at **12,263x the median
  frame**, versus 12.9x on the null and 95-137x on `lead-1-cpl` and
  `tweezers-cpl`.
- **P11** (MEASURED) `foam`'s contamination is a single contiguous event
  spanning **frames 38-47**, and is spatially compact: worst 64px tile 0.754,
  p99 tile 0.437, **median tile 0.101**.
- **P12** (MEASURED) `wrapped-text-1` is a textbook isolated transient —
  **frame 2 alone flags at 869x the median frame** with the rest of the stack
  quiet (median tile 0.0046) — the case a rejection scheme would fix completely.
- **P13** (MEASURED) **`flowers-cpl` (176 frames, live plant material) is the
  cleanest stack in the corpus**, at `mean z^2 = 0.972` and a `>8 sigma` rate of
  3.17e-6, i.e. **0.1x the locked-down printed-ruler null** — live botanical
  subject matter does not imply motion contamination.
- **P14** (MEASURED) Comparing `foam` to the null **within matched absolute
  detail-SNR bins** gives a contamination ratio of **11.6x**, against a raw
  unmatched ratio of 94.4x; **DERIVED: ~8x of the apparent cross-stack signal is
  detail composition rather than contamination**, quantifying M60's objection.
- **P15** (MEASURED) An independent instrument measuring the fourth difference of
  per-frame **global mean level** finds `109MSDCF`'s peak-to-peak drift is
  **0.9102%**, independently reproducing the **0.91%** photometric-drift figure
  already cited in `crates/strehl-core/src/merge.rs` ~line 663.
- **P16** (MEASURED) The null stack has a **larger** peak-to-peak level swing
  (**14.62%**) than `coffee-bean` (12.34%) yet a **32x smaller fourth
  difference** (2.14e-4 vs 6.90e-3) — smooth photometric ramps of any amplitude
  are annihilated, and only the non-smooth part survives.
- **P17** (DERIVED) Attributing `z^2` inflation via `E[z^2] = 1 + S^2 d4^2 /
  (sum r^2 (gS + rn^2))`, **`coffee-bean`'s excess is 56.8% photometric** — it is
  a flickering light, not motion, and a robustness mask is the wrong tool for it
  — whereas **`foam`'s excess is only 0.7% photometric**, i.e. essentially all
  genuine spatially-structured disagreement.
- **P18** (MEASURED, negative) The global-mean photometric model **over-predicts
  on four stacks** (`bee-1-cpl` 201.2%, `bee-3-cpl` 97.6%, `bee-2-cpl` 73.0%,
  `couch-fibers-cpl` 69.6%) because it assumes the level change is uniform across
  the frame; the photometric share is only trustworthy well below 100% and those
  four stacks remain **unattributed**.

**The mask, and the election**

- **P19** (MEASURED) A private re-implementation of the merge reproduces
  `FocusStats::best_index` at **100.000000%** of pixels and `Estimator::n_eff`
  at **100.000000%** of pixels on three stacks, with green values matching
  `Estimator::green_mean` to **`<= 9.77e-4` DN** — so measurements made against
  it are measurements against the shipped merge.
- **P20** (MEASURED) **In the shipped merge, 4.78% of `foam`'s output pixels take
  their value from a frame whose own disagreement at that pixel exceeds 8
  sigma** — motion wins the focus election, as predicted. The clean stacks read
  0.058% (null) and 0.016% (`flowers-cpl`).
- **P21** (MEASURED) Making the *election* robust (ineligible below weight 0.5)
  removes **100.000% of those hot winners on all three stacks**, and changes the
  elected winner at **9.12%** of `foam`'s pixels versus 0.16%/0.08% on the clean
  stacks.
- **P22** (MEASURED, registered in advance as bar B5) **A robustness mask applied
  to the averaging stage alone recovers only 6.0% of the split-half improvement
  that masking the election too achieves, and removes 0% of the hot winners** —
  masking the average without the election is close to useless.
- **P23** (MEASURED, **registered bar B4 FAILED**) The Wronski-style soft weight
  with knees at 4 and 8 sigma **reduces mean split-half disagreement on `foam` by
  only 5.21%**, against a pre-registered requirement of `>=10%`, and it makes the
  **p999 of that disagreement 38.18% worse**.
- **P24** (MEASURED) Masking the election shifts the winner to a frame whose
  unchanged admission tolerance then admits a **larger** discrepant set —
  `foam`'s hot admitted samples rise from 442,212 (arm 0) to **910,697** (arm 2)
  — so a correct implementation must re-derive the admission tolerance from the
  masked election rather than reusing the unmasked band.
- **P25** (MEASURED, **registered bar B2 half-FAILED**) On clean stacks the mask
  removes only **0.0046%** of admitted weight (bar `<1%`, pass) but moves the
  merged green by **0.307 sigma RMS** (bar `<0.10 sigma`, fail); **99.64% of
  pixels move less than 0.01 sigma**, so the RMS is carried entirely by ~0.36%
  of pixels and RMS is a poor summary of a distribution this heavy-tailed.
- **P26** (MEASURED) Split-half disagreement `H` has a **floor of 1.278 sigma
  mean on a clean static stack** against a pure-noise expectation of
  `sqrt(2/pi) = 0.798` — a 60% floor caused by the two halves electing different
  frames at ambiguous pixels — and it is detail-confounded: **`flowers-cpl`, the
  corpus's cleanest stack, has `H` mean 2.303, nearly double the ruler's**. `H`
  is therefore a weak acceptance metric for contamination work.
- **P27** (MEASURED) `foam` has **1.20% of pixels with at least one green sample
  at the container maximum**; clipped samples are censored, not merely noisy, and
  no part of this analysis models that.

**Failed registrations**

- **P28** (MEASURED, **registered rule-30 prediction FAILED**) I predicted
  `E[z^2] in [1.00, 1.42]` on the null from the noise model's known
  over-confidence and green-channel correlation; it measured **0.9897, below the
  interval** — the predicted excess is absent and a ~1% deflation is present
  instead (see P6).
- **P29** (MEASURED, **registered diagnostic prediction FALSIFIED**) I predicted
  the inflated stacks `lead-1-cpl` and `flat-on-ruler-cpl` were defocus leakage
  and would show the `k^8` subsampling law; their `z^2 - 1` ratios from `k=1` to
  `k=2` are **1.80x** and **6.98x** against the **256x** the law requires.
  **Defocus leakage explains none of the inflated stacks.**
- **P30** (ARGUED) The measured 6-7x growth of `z^2 - 1` with frame spacing on
  `foam` and `flat-on-ruler-cpl` is consistent with disagreement driven by
  subject displacement accumulating with time separation, while `lead-1-cpl`'s
  **1.80x** indicates it is already saturated at `k=1` and is therefore a
  per-frame random disturbance (vibration) rather than drift. Unverified.
- **P31** (MEASURED, **registered placebo sub-bar FAILED**) A4's sub-bar required
  the unplanted tile's flag rate to be within 2x the frame background; it
  measured **26.5x**. The bar compared the frame's most detailed tile to the
  whole-frame average and was mis-specified, since flag rate rises ~3 orders of
  magnitude across the detail range on clean data (P14).

**Verification**

- **P32** (MEASURED) A planted synthetic subject motion on the null stack is
  detected **strictly monotonically** in shift magnitude — at-frame `>8 sigma`
  rate 6.10e-4 (unplanted) -> 2.42e-2 (1 px) -> 6.38e-1 (32 px) — while the same
  plant in a featureless control region produces **exactly 0.0 at every shift up
  to 32 px**.
- **P33** (MEASURED) The operator is **completely blind to a gradual ramp**: a
  planted ramp of 64 px produces an at-frame flag rate of **0.0**, confirming the
  declared blind spot for anything smooth of order `<= 3` in frame index
  (slow drift, steady creep, monotone illumination change).
- **P34** (MEASURED) Deliberately removing the noise normalisation from the
  statistic makes the null read **`mean z^2 = 321.65`** instead of 0.9897 and its
  `>8 sigma` rate **0.861** instead of 3.02e-5, turning the acceptance bar red by
  **161x**, with a diagnostic signature (`z^2` rising 238 -> 640 with signal
  level) that identifies the fault as un-normalised.
- **P35** (MEASURED) On contaminated stacks, **widening the temporal window makes
  the statistic worse**, not better: on `foam` the `mean z^2` for
  `(w,p) = (5,2) / (7,2) / (9,2) / (13,4)` is **2.03 / 3.31 / 5.39 / 5.45**,
  because a wider window admits more contaminated frames into each comparison.

**The verdict**

- **P36** (ARGUED, from P20-P25) The Wronski-style noise-normalised robustness
  mask **should not ship in the form specified**: it fails its own pre-registered
  benefit bar on the one stack known to have moved, degrades the tail of the
  disagreement distribution by 38%, and fails the strict limb of its clean-data
  placebo. **The measurement that should drive the next milestone is P20/P22 —
  the focus election, not the average, is where motion enters the output.**

---

## 9. Limits

**What could make the above wrong.** In rough order of how much it worries me.

1. **The metric is blind to slow drift, and that is not a small exclusion.**
   P33 shows a 64-pixel planted ramp reads exactly zero. If the dominant real
   contamination in this corpus is *steady* creep — thermal drift of the rail, a
   subject slowly wilting over a 299-frame stack — **my survey would call those
   stacks clean and it would be wrong.** Everything in §4 measures discrete
   disturbance only. A companion instrument sensitive to low-order drift would be
   required before anyone concludes a stack is genuinely clean.
2. **Sensor-coordinate dust is invisible by construction** (P7). Because a defect
   present identically in every frame cancels in the residual, my survey cannot
   see the dust the brief listed as a contamination source. Post-alignment, dust
   *becomes* visible to this operator — which means my numbers are a lower bound
   on the contamination the pipeline will face once M86 lands, not an upper one.
3. **`H` is a weak benefit metric and B4's failure inherits that weakness**
   (P26). It has a 60% floor from election ambiguity and it tracks detail more
   than contamination. I registered it before measuring and I stand by reporting
   its verdict, but "the mask failed B4" is better read as **"benefit unproven"**
   than as "harm proven". A metric built on a known-clean reference merge, which
   this corpus does not have, would settle it.
4. **The null's 1.03% deviation is degenerate** (P6). I cannot separate ~1%
   frame-to-frame common-mode from a ~0.5% scale error in the noise model. If it
   is the latter, every `z` in this report is uniformly ~0.5% off — which changes
   no ordering and no conclusion, but does mean the analytic 1.000 is agreeing
   with me slightly by luck.
5. **Clipping is not modelled** (P27). `foam` has 1.20% of pixels with a censored
   green sample. A clipped value is not a noisy value, its residual is not
   Gaussian, and some part of `foam`'s tail is certainly censoring rather than
   motion. I did not separate them.
6. **The mask's knees (4 and 8 sigma) are in sigmas but they are still choices.**
   The *units* are calibrated, which is what the brief required, but I did not
   sweep them and a different pair might have passed B4. I deliberately did not
   tune them after seeing B4 fail, so what is reported is one point in a space I
   have not explored. A knee sweep is the obvious next experiment and I did not
   run it.
7. **Arm 2's admission tolerance is inherited from the unmasked election**
   (P24), which I believe is a defect in my arm rather than in the idea. So B4's
   failure may be a failure of my construction, not of election-masking in
   general. I flag this rather than resolve it because resolving it means
   changing the arm after seeing its result.
8. **Green luma only.** The statistic uses the green channels. Chroma-selective
   contamination — a colour shift with no luma change — is not measured.
9. **Single body, single lens, one owner's stacks.** Every number is from one
   A7C II with one FE 100mm + 2x TC. The noise model that makes the analytic null
   work is measured for this body. None of the absolute rates transfer.
10. **The 23-stack survey used the stacks as shot**, without alignment. Some of
    what I attribute to subject motion is camera/rail motion that alignment will
    remove. The survey therefore measures **contamination as the merge currently
    sees it**, which is the right question for today's binary and the wrong one
    for the post-M86 binary.

---

## 10. Where this code should live, and what the library lacks

### 10.1 The port

The milestone was deliberately built as a self-contained example
(`crates/strehl-cli/examples/m89-robust.rs`) to avoid racing M85 and M86. The
port targets, in the order they should be done:

1. **The statistic** -> a new `crates/strehl-core/src/temporal.rs`. It needs
   nothing that does not exist: `loo_residual_kernel`, `Op`, the `AffineVar`
   two-dot-product variance trick, and `z_at` are ~120 lines and depend only on
   `noise` and `profile`. **It should not go in `merge.rs`** — it is a
   measurement, not a merge step, and it is useful on its own as a capture-time
   QC tool (see 10.3).
2. **The per-sample weight hook** -> `Estimator::fold_inner` in
   `crates/strehl-core/src/merge.rs`, at the point around **lines 745-786**
   where `admitted` is computed and `self.sum[s][i] += v as f32` executes. That
   function **already carries `luma_scale` / `luma_offset` parameters**, so it
   already has the shape of "per-frame correction applied at fold time" and a
   `weight: f32` parameter is a natural sibling.
3. **The election masking** -> wherever `FocusStats::best_index` is consumed.
   This is the part that matters (P20/P22) and it is the part I would build
   first if I were doing it again.

**Both 2 and 3 are in files M85 owns tonight. That is a blocked dependency and
it is deliberate; nothing in this report requires it to be unblocked to be
usable.**

### 10.2 What the library does not have

- **No temporal window abstraction.** `Estimator::fold` is strictly streaming
  and per-frame; there is no way to ask "give me frames `f-2 .. f+2` at pixel
  `i`". My example holds a `WMAX`-deep ring buffer of decoded green planes
  itself. **A `TemporalRing` in core is the single missing primitive**, and both
  this work and any future outlier or transient work needs it. It costs one
  window of decoded planes in memory — for `w=5` at 7008x4672 that is ~78 MB of
  f32 green, which is affordable.
- **No two-pass merge plan.** A robustness mask needs an estimate before it can
  measure disagreement against it; `merge_cmd.rs`'s worker plan is single-pass.
  My example does two passes and the brief's own §5 confirms a second decode
  pass is cheap (0.91 s/frame, well under a minute for 299 frames). The plan
  needs to be able to express it.
- **No per-sample weight in the accumulator.** `Estimator` accumulates
  unweighted sums and an integer `n_eff`. A weighted variant needs `sum_w` as a
  float alongside `sum`, and `n_eff` becomes an effective count.
- **No censoring model.** Clipped samples (P27) are accumulated as if they were
  measurements. This is orthogonal to M89 but it limits any noise-normalised
  statistic near highlights.

### 10.3 One recommendation outside the mask

The metric costs one extra decode pass and reports, per stack, a single number
that separates this corpus over 2,486x. **It is more immediately valuable as a
capture-time QC report than as a mask** — `strehl` telling the owner "frames
38-47 of this stack disagree with their neighbours; consider reshooting" is a
feature that requires no change to the merge at all, cannot damage output, and
addresses the actual problem, which is that contaminated stacks currently pass
through silently. If only one thing from this milestone ships, it should be that.

---

## 11. Reproducing this

```powershell
$env:CARGO_TARGET_DIR = "$PWD\experiments\M89-robustness\target"
cargo build --release -p strehl-cli --example m89-robust
$exe = "experiments\M89-robustness\target\release\examples\m89-robust.exe"

& $exe survey "D:\personal\macro\highly-angled-ruler-mm-cpl" --sweep   # the null
& $exe survey "D:\personal\macro\foam"                                 # the motion case
& $exe levels "D:\personal\macro\coffee-bean"                          # photometric arm
& $exe plant  "D:\personal\macro\highly-angled-ruler-mm-cpl" --limit 120
& $exe mask   "D:\personal\macro\foam" --limit 100
& $exe survey "D:\personal\macro\foam" --every 2                       # the A6 arm

$env:PYTHONIOENCODING = 'utf-8'
python experiments\M89-robustness\src\table.py        # section 4 tables
python experiments\M89-robustness\src\photometric.py  # section 4.3 table
```

All raw output is committed under `experiments/M89-robustness/out/`. The two
Python scripts parse the noise coefficients out of the run headers rather than
restating them, so they cannot drift from the binary.

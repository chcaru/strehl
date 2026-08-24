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

---

## 1. Verdict

*(to be written after the measurement)*

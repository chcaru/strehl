# M115 — pre-registration

**Written and committed BEFORE any arm, control or spectrum was computed.**
Milestone: `M115-deconv-headroom`. Owns `experiments/M115-deconv-headroom/**` and
`docs/research/M115-deconv-headroom.md`. Writes results only to
`C:\dev\strehl-out\M115-deconv-headroom\`. `D:\` is read-only in its entirety.
Nothing under `crates/` is edited.

---

## 0. Rule 40 / rule 43 discharge — the prior art the brief did not name

I searched `docs/research/` before writing this. **Four committed reports already
bear on this question and my brief named none of them.** Recording what they say,
and what is therefore left:

| report | what it settled | what it left open |
|---|---|---|
| `M20-deconvolution-ceiling-measured.md` | The estimator formula is the MMSE one (confirmed 3 ways). Gain over selection is `sqrt(Σ\|H\|²)/max\|H\|`, **not** `sqrt(Σ\|H\|²)`. Hard ceiling: where every `H_k(f)=0` the estimator returns exactly 0. Guarded Wiener beats argmax on **15.1 %** of `109MSDCF` pixels. **"The prize is noise, not detail"** — ∇-correlation gain ±1.5 %. | **1-D simulation, oracle depth, oracle prior, one subject, never independently verified** (its own §9). |
| `M41-r3-kill-measured.md` | R3 (Wiener-as-core-merge) **REFUTED end to end on real frames**: arm D flat-ROI noise **2.846× / 3.305×** the shipped rule, **63.966 % / 81.249 %** of detail pixels out of the range of every input frame. Damage is the **diffraction-inversion term**, not the focus axis (`s=0` gives 33.3 %/61.9 % of it alone). Arm D′ (no diffraction term) survives at 0.943×/0.979×. | **"It does not measure resolution at all."** Its registered detail metric (FRC 1/7 crossing) is right-censored, recovery ratio *undefined*, 32 repairs tried, **withdrawn**. Every metric that had power also fired on a **flat** source at ≥ +0.94, so none was admissible as a detail metric. **The kill is on the noise axis alone.** |
| `M70-through-focus-spectrum.md` | Off-peak frames **do** carry mid-band signal (rel. amplitude 0.879–0.970 at one step, 12/12 stacks) — the reviewer's premise is true. But the through-focus band matrix is **rank-1 to 0.9959**, so the off-peak spectrum is the peak's scaled down, and a matched filter over scaled copies **is** a weighted average. Whole focus-axis matched-filter prize = **1.1100× band SNR** (range 1.0696–1.2037); MF over an equal average of the same frames = **+0.23 % (±1)** / **+2.38 % (±3, the shipped gate's width)**. | Band SNR on fixed windows, never an image. Its §14 item 1 asks for the output-domain version. It deliberately did **not** re-ask whether deconvolution produces a better image: *"M41 measured that and refuted it."* |
| `M88-optical-ceiling.md`, facts 12/27/28 | Marked f/11 is optically **f/33**; measured cutoff `f_sig = 0.2762 cyc/px` on the green quincunx; MTF@Nyquist 0.036/0.000/0.000 at f/5.6, f/8, f/11 at m=2.0. | — |

**Therefore M115 is not "does deconvolution help" — that is answered, twice, and
the answer is no on the noise axis.** M115 is the one limb both kills left open:
**a resolution/contrast metric with demonstrated power on real data, and the
per-frequency headroom number read off it.** If that limb also comes back small,
the question is closed from both sides and I will say so in the first sentence.

---

## 1. Units, plane, data

Green quad plane `G = (G1+G2)/2`, black level 512, `raw_image_visible` only
(rule 7), copied inside the `with` block (rule 32). Frequencies in
**cyc / quad px**, Nyquist `0.5`; fact 27's `f_sig = 0.2762` is in these units.
ROI side `B = 512` quad px.

**Stacks (rule 14 — two genuinely different stacks, not a directory and its
mirror):**

* `D:\personal\macro\109MSDCF` — 22 frames, marked f/11 (M41's stack 1)
* `D:\personal\macro\119MSDCF` — 33 frames, marked f/5.6 (M41's stack 2)
* `D:\personal\macro\bee-3-cpl` — 299 frames, marked f/5.6, **if time permits**;
  this is where the owner's *"those stacks don't look too good yet"* lives.

Noise model, the project's own: `σ²(S) = g·S + (RN_e·g)²`, `g = ISO/436.8`,
`RN_e = 1.47` at ISO ≥ 400 else `4.20`, **halved** on the quad plane because
`G` averages two independent CFA sites.

## 2. The observable

For an arm output `O` over an ROI, 2-D Hann window `w`, radially binned:

```
P_O(f)      = <|FFT((O - mean O)·w)|²> over the radial bin at f
P_noise(f)  = P_D(f), D = (O⁺ - O⁻)/2, O± = pipeline(Y ± n), n ~ N(0, σ²)
P_sig(f)    = max(P_O(f) - P_noise(f), 0)
SNR(f)      = P_sig(f) / P_noise(f)
```

`n` is a fresh iid realisation with **exactly the modelled per-pixel variance of
the real noise**, pushed through the *identical* pipeline with the *identical*
data-derived weights. `D` is therefore this arm's noise transfer applied to a
noise field of the real amplitude, measured on real frames, with no assumption
that the arm is linear in closed form.

**Headline, per radial bin, on the DETAIL ROI:**

```
R_SNR(f)   = sqrt( SNR_arm(f) / SNR_FRAME*(f) )      <- the headline
G_sig(f)   = sqrt( P_sig_arm(f)   / P_sig_FRAME*(f)   )   <- contrast gain
G_noise(f) = sqrt( P_noise_arm(f) / P_noise_FRAME*(f) )   <- noise cost
```

**Why SNR and not contrast.** A linear filter multiplies signal and noise by the
same factor at each frequency, so *contrast gain alone is free* — anyone can
post-sharpen. `R_SNR` is what a post-sharpening pass cannot manufacture, and
`G_sig`/`G_noise` are reported beside it so the price is visible. Control **C3**
exists to prove the instrument actually has this property rather than merely
being described as having it.

## 3. Arms

| arm | definition |
|---|---|
| `FRAME*` | **the ceiling a perfect selector reaches** — the single best frame per tile, elected on the *regularised coarse* focus field averaged over the tile. A tile-level regularised selector, labelled as such; never a raw per-band argmax (rule 4). |
| `FRAME_ORACLE` | the frame with the highest noise-subtracted mid-band signal power in that tile. Strictly more generous to selection than `FRAME*`. |
| `GATE` | shipped-equivalent noise-gated average (M41 arm A). |
| `MEAN` | plain mean of all frames. |
| `MF` | focus-axis matched filter, `H_k = defocus(|Δk|·s)`, **no diffraction term** (M41's surviving arm D′ shape). |
| `WIENER` | the full R3 estimator, `H_k = defocus ⊗ diffraction(f_sig)`. |

Wiener-family arms are **guarded**: blended toward `GATE` with weight
`Σ|H|²/(Σ|H|² + τ·σ²/S)`, `τ = 3` (M20 §5 measured this broad and flat over 24×).
`s` is self-calibrated from the through-focus curve width per §5.

## 4. Registered decision rule

Mid band := `[0.10, 0.2762]` cyc/quad px (M70's band, closed at fact 27's cutoff).

* **MEANINGFUL HEADROOM** iff the best arm reaches `max_midband R_SNR(f) ≥ 1.25`
  on **both** stacks **and** the ringing control passes (out-of-range fraction
  ≤ `GATE`'s + 1.0 pp).
* **SMALL PRIZE** iff `max_midband R_SNR(f) < 1.15` on both stacks.
* **INDETERMINATE** otherwise, or if any of C1–C5 fails.

## 5. Registered independent prediction (rule 21 — a gate with an outside term)

M70 measured the entire focus-axis matched-filter prize at **1.1100×** band SNR
(median of 12 stacks, range **1.0696–1.2037**), and MF-over-equal-average of the
*same* frames at **+2.38 %** at the ±3 window its §18 shows the shipped gate
operates at. M70 ran **no estimator and produced no image**; it read band
amplitudes and a rank-1 decomposition. So:

> **Prediction P-M70:** `max_midband R_SNR(MF) / max_midband R_SNR(GATE)` lands in
> **[1.00, 1.25]**. A reading outside that range means M70's decomposition or my
> estimator is wrong, and I must say which before quoting any headline.

This is an *independently obtained* term, not a threshold I chose to be safe
against (rules 21, 35).

## 6. Controls — every one run and read BEFORE the arms (rule 9)

* **C1 — null.** Flat ROI, every arm: `P_sig(f)` must be within `2·sd_boot` of
  zero at every bin above 0.05 cyc/px. A metric that reads signal on a flat patch
  invalidates every number computed with it. FAIL ⇒ INDETERMINATE.
* **C2 — positive, monotone.** Fourier-domain Gaussian blur of **known** sd
  `sb ∈ {0, 0.25, 0.5, 1.0, 2.0}` quad px planted on real frames, so the planted
  MTF is exactly `exp(-2π²sb²f²)` with **no kernel truncation and no resampling**
  (the brief forbids a plant that perturbs the measured quantity).
  Require: `P_sig(f)` strictly decreasing in `sb` at every bin with
  `SNR_FRAME*(f) > 1`, and log recovery ratio in **[0.90, 1.10]** on uncensored
  bins.
* **C3 — gain invariance. The control that decides whether "contrast gain" means
  anything.** Apply a known frequency ramp `a(f) = 1 + 2f` to an arm's output.
  `P_sig` and `P_noise` must **both** scale by `a(f)²` within 2 %, and `SNR(f)`
  must be **unchanged** within 2 %. If C3 fails the instrument is crediting
  sharpening as information and every headline is void.
* **C4 — noise-channel linearity.** Inject at variance `α` and `4α`: `P_D` must
  scale by **4.00 ± 5 %**.
* **C5 — noise-channel external validation (rule 34).** A plant that supplies its
  own noise constant cannot detect that constant being wrong. The modelled `σ`
  must reproduce a `σ` measured **from the data**: the frame-to-frame difference
  spectrum on a flat ROI (a flat patch is invariant to defocus, so the difference
  is noise plus photometric drift). Require agreement within **15 %**.
* **C6 — ringing.** (a) out-of-range fraction: fraction of output pixels outside
  `[min_k Y_k, max_k Y_k]` — M41's instrument, which reads 0.000 % for
  selection/average and 63.966 %/81.249 % for the full Wiener; (b) an
  **edge-overshoot profile**: a flat region adjacent to a hard edge, overshoot
  versus distance from the edge, checked for structure that is in no input frame.
* **C7 — sign convention (brief's requirement).** Plant a known blur and
  deconvolve with the *matching* known OTF. `P_sig(f)` must move **toward** the
  unblurred truth. A signed recovery is reported, not a magnitude.
* **C8 — floor guard.** No Wiener-family arm may sit more than 5 % below `GATE`'s
  `SNR(f)` at any bin. If it does, the guard is not working and its failures are
  uninformative rather than evidence.

## 7. VOID conditions

* **V1** — flat-ROI real sd ÷ model σ > 3 ⇒ that ROI carries structure; C1/C5 are
  not interpretable on it and a different flat ROI must be chosen.
* **V2** — fewer than 4 mid-band radial bins with `SNR_FRAME*(f) > 1` ⇒ the stack
  has no measurable mid-band signal, `R_SNR` is a ratio of two noise estimates,
  and the correct report is **NO POWER**, never a number.
* **V3** — C2's recovery outside [0.90, 1.10] on the majority of uncensored bins
  ⇒ the signal channel is not calibrated; report the failure, not the headline.

## 8. What is deliberately NOT tested

* Occlusion / two-layer unmixing (M20 §9 leaves it open; untouched here).
* Iterative deconvolution (fact 404: RIF lands within 0.19 dB of Richardson–Lucy).
* Alignment. All arms run on **unaligned** frames, exactly as M41 did, so the
  comparison holds alignment constant at *none*. No absolute number here is a
  statement about the shipped pipeline's eventual quality.
* Anything under `crates/`. No Rust is edited, built or run.

## 9. Deviation policy

Any deviation from this document is declared in the report, with the reason, and
the pre-registered reading is reported **as it fell** beside the amended one.

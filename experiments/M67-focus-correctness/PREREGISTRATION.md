# M67 — PRE-REGISTRATION

**Committed before any correctness, admission or hit-rate number existed.**
Nothing in this file is written with knowledge of a result. Where this file and
the report `docs/research/M67-focus-correctness.md` disagree, **this file is the
record**.

---

## 0. The question

Every measurement this project has made of the merge scores **how many** frames
it averages. M62's √N battery, M64's degeneracy guard (`n_eff/N < 0.95`) and
M65's election field are all counts and set sizes. None of them scores **which**
frames. M64 said so about its own acceptance guard — it demonstrates the merge
*chooses between frames*, not that it *admits the right ones*. M65 refused any
image-quality claim on the same grounds: arm W admits strictly more frames, and
"whether arm W's extra admissions are good frames or bad ones is unmeasured".

**A merge that admits a fixed wrong set of frames scores identically, on every
instrument this project owns, to one that admits the right set.**

So: **does the shipped merge admit the frames that are actually in focus at each
pixel, and by what margin?**

---

## 1. Why this has never been measured, and what changes it

On a real capture there is no ground truth for which frame is in focus at a
pixel. Defining correctness with the same focus operator that made the decision
measures the operator's self-consistency and reports it as accuracy. That is the
trap and it is why the number does not exist.

The instrument is `experiments/m25-simulator` (M25). Its `render.ground_truth`
emits `visible_focus` — the scene's own geometric focus map, composited under
unblurred alpha and integrated over the pixel aperture — and
`best_frame = argmin_k |visible_focus − focus_plane_k|`. **That truth is
computed from scene geometry and the frame focus planes. It never touches
Tenengrad, the 27×27 window, the 17×17 regulariser or the gate.** The operator
under test cannot influence the answer it is scored against.

### 1.1 The circularity that remains, named before running anything

**(a) The idealised-PSF circularity. I cannot remove it.** The forward model
blurs each depth band with `defocus(|F−k|·coc) ⊛ diffraction(N_eff, λ)`. That
PSF is symmetric in `k` about `F` and monotone in `|F−k|`, so a contrast-based
focus operator is handed a monotone unimodal through-focus response **by
construction**. Real optics are not that: M25 §6.2 measured that `coffee-bean`'s
real through-focus curve "is asymmetric and falls faster than any simulated
one", and M25 §6.3 lists spherical aberration, coma, astigmatism, field
curvature, longitudinal chromatic aberration and PRNU as **not modelled at
all**. Consequence, registered now: any admission *accuracy* this milestone
measures is an **upper bound** on real-capture accuracy, and any admission
*failure* it measures is a **lower bound** on real-capture failure. That
asymmetry is stated in advance so it cannot be chosen after the fact.

**(b) M25's own validation suite is blind to the PSF.** Gate 2's NC-B removed
diffraction entirely — 4.52× amplitude change over 0.30–0.48 cyc/px — and passed
every gate. M25's headline says in terms: "Do **not** use it to score
deconvolution, PSF estimation or EDoF". This milestone's observable *is*
downstream of the PSF. It is not a deconvolution score, but it is not in the
validated set either. **Everything below inherits an unvalidated optical
component and the report must say so in its headline.**

**(c) The noise model is shared.** The plant is exposed through the simulator's
`g = max(ISO,100)/436.8`, `RN = 4.20 e⁻` chain and the focus operator normalises
by `profile.rs`'s `ILCE-7CM2` profile, which is the same model. The operator is
noise-matched to the plant by construction; a real sensor's PRNU (unmodelled,
M25 §6.1, "leading suspect for the floor deficit") would break that match. Both
are pinned at ISO 160, where the simulator's `read_noise_e_high = 1.47` and the
crate's `1.2392` cannot disagree because neither is used.

**(d) What is *not* circular.** The truth map, the plant's depth ramp, the
frame ordering and the defocus rate are all inputs to the render and outputs of
nothing the merge computes. `Su` and `Sb` (§3) do not read the focus field at
all. The `A`-vs-`E` contrast is between two shipped code paths scored by one
external ruler.

---

## 2. The plants

All rendered by `experiments/M67-focus-correctness/src/10-render-plants.py`,
which imports `strehl_sim` unmodified.

* **`tilt`** — `scene.tilted_plane`: analytic linear depth, focus index ramping
  `lo → hi` across the *x* axis. M25 calls it "the cleanest available ground
  truth". This is the simulator's realisation of the physically-constrained real
  subject the brief names: a planar subject at a known tilt, whose in-focus
  frame index must vary smoothly and monotonically across the field.
* **`flat`** — `scene.flat_texture`, one focus index for the whole field. The
  degenerate cell: every pixel's correct frame is the same one.

Declared deviations from M25's defaults, all fixed before any run:

| knob | value | why |
| --- | --- | --- |
| `Breathing.total_scale_change` | **0.0** | the merge assumes registered frames; alignment is a separate stage and is not under test. A warped plant would score the aligner. |
| `Capture.gain_pp` | 0.0 (default) | photometric drift is M24's axis, not this one |
| `channels` | `"green"` | inert: `green_luma_with_clip` reads only G1/G2, and no merged pixel value is scored |
| `iso` | 160.0 | the one ISO where the simulator's and the crate's read-noise constants cannot disagree |
| `supersample` | 2 | M25 §6.2 bounds the pixel-aperture MTF error at 0.25 cyc/px at ~2.6 % here |
| `depth_bands` | `2·span + 1` | band step ≤ 0.5 frame across the ramp |

Radiometry is fitted from the real `D:\personal\macro\109MSDCF` ROI
`(2272, 1344, 256, 256)` in green-plane coordinates — the same ROI M25's Gate 1a
used — read-only. **Disclosed:** that fit was run in `00-timing-probe.py` before
this file was committed, and returned base 5515.4 e⁻, contrast 56.2 e⁻ sd,
β 1.651, real ROI mean 2020.29 DN sd 28.2007 DN. It is a plant parameter, not a
result of the measurement, and it is quoted here so that nothing about the plant
is chosen after a correctness number exists. That ROI is M25 §4.3 attempt 1's
**noise-saturated regime** (1.4 % contrast), so subject contrast is **swept**
rather than fitted: multipliers ×1, ×4, ×16 on `contrast_e`, with the achieved
in-focus green structure sd reported in DN next to the modelled noise sd.

Swept axes: `coc_px_per_frame ∈ {1.0, 3.0}`, contrast ×{1, 4, 16}, depth span
∈ {K−1, 8, 0}, β ∈ {1.651, 3.454}, seeds. `K = 25` frames throughout.

**Headline cell, fixed now:** `tilt`, side 1024 (plane 512×512), `K = 25`,
`coc = 1.0`, contrast ×4, β 1.651, span 24, three seeds.

---

## 3. The arms

Scored over the interior only, margin `SUPPORT_RADIUS + REGULARISER_RADIUS = 22`
plane px, because a pixel nearer the border has a replicate-clamped response.

| arm | admitted set at pixel `i` |
| --- | --- |
| **`E(T)`** | the shipped estimating merge: `{k : best_index[i] == k or Gate(T).admits(reg_k[i], best_focus[i])}`, `T ∈ {0.5, 1.0, 2.0, 4.0}`, `4.0 = DEFAULT_GATE` |
| **`A`** | `Command::ArgmaxBaseline`: `{argmax_k raw_k[i]}` — one frame, elected on the **unregularised** field, because `stack.rs` never calls `regularise`. The retained pure selector. |
| **`Su(T)`** | **the null**: `n_eff(T)[i]` indices drawn uniformly without replacement from `0..K`, independently per pixel |
| **`Sb(T)`** | **the null**: a contiguous run of `n_eff(T)[i]` frames at a uniform random start — the harder null, because a real admitted set is a contiguous-ish interval and `Sb` matches that shape as well as its size |

`Su` and `Sb` are matched to `E(T)`'s **own per-pixel `n_eff`**, not to its mean.

---

## 4. The observables

Over interior pixels, with `k*(i)` the truly-best frame index and `f*(i)` the
continuous visible focus in frame-index units:

* **`H`** — *admission hit rate*: the fraction of pixels where `k*(i) ∈ A_i`.
* **`D`** — *admitted-set defocus*: `mean_i mean_{k ∈ A_i} |k − f*(i)|`, in
  frames. Blur diameter is `|k − f*|·coc`, so this is how out of focus the
  average frame the merge averages actually is.
* **`M`** — *miss distance*: `mean_i min_{k ∈ A_i} |k − k*(i)|`, in frames.
  Zero exactly when `H = 1`.
* **`ρ_col`** — Spearman correlation between the ramp-axis column index and that
  column's mean admitted frame index.

`H` scores the **admitted set**, not the winner index map. M65 measured that
these are different objects — 56.70 % of pixels elect a different winner while
the acceptance set moves 0.44 % — so which one is being scored is stated here
and never elided. `E`'s winner index is reported separately and is not the
headline.

---

## 5. Controls, and what each one failing costs

Reported before any arm ratio is believed.

| id | statement | bar | consequence if NOT MET |
| --- | --- | --- | --- |
| **C0** | the harness's admitted-set counter is the shipped `Estimator`'s | `\|mean n_eff(harness) − Estimator::mean_n_eff()\| < 1e-9` at gate 4.0, whole plane | abort; no arm below is scoring the shipped merge |
| **C1** | **the metric has power against a matched-`n_eff` random admission set** | `\|H(E(4.0)) − H(Su(4.0))\| ≥ 0.10` **and** `≥ 10 ×` the across-seed SD of `H(E(4.0))` | **the metric has no power. Report that and stop. No correctness claim is made.** |
| **C2** | the metric can separate the pure selector from the estimating merge | separation on at least one of `H`, `D`, `M` of `≥ 10 ×` that statistic's across-seed SD | every `E`-vs-`A` comparison is labelled unpowered |
| **C3** | the plant carries a solvable signal | `H(A) − 1/K ≥ 10 ×` across-seed SD of `H(A)` | the plant is unsolvable; every arm on that cell is void |

`1/K` is the hit rate of guessing one frame blind, which is what `A` would score
if the plant carried no focus information at all.

---

## 6. The decisions

Each states a mechanism and an observable. **No expected sign is recorded for
any of them**, and no value is predicted.

* **D1 — the headline.** `H(E(4.0))` on the headline cell. *Decision rule:* if
  `H < 0.50`, conclude that the shipped merge does **not** admit the truly
  in-focus frame at a majority of pixels on this plant, and report the rate. If
  `H ≥ 0.50`, conclude that it does, at that rate, on this plant. Either way `H`
  is reported at every cell of the sweep, not only where it is largest.
* **D2 — the margin.** *Mechanism:* if admission is driven by the focus signal
  rather than by set size alone, the shipped set and a blind set of the same
  size and shape are different sets. *Observables:* `H(E(4.0)) − H(Sb(4.0))` and
  `D(Sb(4.0)) / D(E(4.0))`. *Rule:* the claim "the merge's admitted set beats a
  matched blind guess" is MET only if `H(E) − H(Sb) ≥ 0.10` **and**
  `D(Sb)/D(E) ≥ 1.10`. If either fails, D2 is reported **NOT MET** and the claim
  is withdrawn.
* **D3 — the structural prediction.** *Mechanism:* the plant's depth is monotone
  in `x` by construction, so a merge that admits frames for the right reason must
  produce an admitted-set centre that is monotone in `x` and tracks the truth.
  *Observables:* `ρ_col` and `max_x |mean admitted index − mean truth|`.
  *Rule:* MET if `|ρ_col| ≥ 0.95` **and** the max column deviation `≤ 1.0`
  frame, at gate 4.0 on the headline cell. If NOT MET, the failure size is
  reported as the headline finding.
* **D4 — selector versus estimator.** Report `H(E) − H(A)`, `M(E) − M(A)`,
  `D(E) − D(A)`. No bar and **no direction registered**: a selector admits one
  frame and can only hit or miss, an estimator admits many and can hit while
  averaging poor frames, so the two statistics are expected to move in
  *different* directions from each other and this milestone declines to guess
  which. Gated by C2.
* **D5 — gate dependence.** `H` and `D` over the whole shipped ladder
  `{0.5, 1.0, 2.0, 4.0}`, registered in advance so that no rung can be selected
  after the fact. M65 was surprised by gate dependence its pre-registration had
  not anticipated; this one anticipates it and fixes the rungs.

---

## 7. What this milestone will not claim

* **Nothing about real captures.** The corpus has no per-pixel focus truth. If
  the answer on real frames is not measurable with what exists today, the report
  says so precisely and names the capture or instrument that would change it.
* **Nothing about image quality.** `H` and `D` are properties of the admitted
  *set*. No sharpness, SSIM, edge-error or detail number is produced.
* **Nothing about occlusion.** M25's Gate 1c FAILs: the veiling signature has
  the wrong sign (0.23× against a real 4.38×). The occluding-edge plant is
  therefore excluded from this milestone by M25's own verdict, and any
  admission statistic at a depth discontinuity would be measuring the plant.
* **No change to `crates/strehl-core/src/merge.rs`.** The instrument is an
  additive example, `crates/strehl-cli/examples/m67-focus-correctness.rs`.

---

## 8. Reproduction

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:PYTHONIOENCODING = 'utf-8'
cd C:\dev\blog\death-of-software\projects\strehl
python -u experiments\M67-focus-correctness\src\10-render-plants.py
cargo run --release -p strehl-cli --example m67-focus-correctness -- `
    experiments\M67-focus-correctness\plants\<plant>
```

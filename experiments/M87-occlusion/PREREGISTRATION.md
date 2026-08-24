# M87 — occlusion halo: PRE-REGISTRATION

**Status: registered before any halo measurement.** Committed in its own commit,
before the measurement scripts exist. Everything below is frozen. Deviations are
disclosed in `docs/research/M87-occlusion.md` with a reason, never silently.

Milestone stem: `M87`. Owns `experiments/M87-occlusion/` and
`docs/research/M87-occlusion.md` only. Does not edit `crates/`, `SYNTHESIS.md`,
`AGENTS.md` or `docs/captures-needed.md`. No Rust is written by this milestone.

---

## 0. Prior art in this corpus (rule 40), checked at source before registering

I grepped `docs/research/` by topic, not by milestone number, and read the
reports rather than SYNTHESIS's compressed renderings of them. Two of the
pointers in my dispatch brief are wrong, and both are recorded here before I
measure anything.

| Dispatch brief said | At source | Consequence for M87 |
| --- | --- | --- |
| "`docs/research/M60-*.md` — measured through-focus bimodality; your most important prior" | **The bimodality report is `M63-bimodality.md`.** The two `M60-*` files are `M60-prior-art-and-the-rival-explanations.md` and `M60-robustness-mask-at-merge-time.md`. `AGENTS.md`'s ledger records the collision explicitly and says **"M63 is reserved for the bimodality milestone above and must not be reissued"**; the experiment tree deliberately keeps the `M60-bimodality` stem (fact 1049) | M87 cites **M63** for bimodality and `experiments/M60-bimodality/**` for its code |
| "`docs/research/M6-*.md` — residual-versus-depth and **halo** work" | **M6 measures the PLUGIN halo, not the occlusion halo.** Its title is *"the alignment residual is defocus, and the halo is not a scalar"*; its halo numbers (19.42 / 32.39 / 89.23 plane px) are the **rectangle expansion** a warp needs beyond its output tile. M6 line 46 says in terms: *"a halo is a rectangle expansion"* | **M6 is not a prior for this milestone.** This is exactly the overloading `AGENTS.md` rule 15 was written to stop, and the brief walked into it. M87 says "occlusion halo" throughout |

Priors that *are* load-bearing, read at source:

- **`M63-bimodality.md` — the decisive prior, and it is a kill.** SYNTHESIS facts
  967/968/969. Bimodality at occluding edges is **real and abundant** (78.3% of
  band pixels clear a per-cell noise floor, AUC 1.000 against controls), but the
  inference *bimodality → two depths* is **refuted five independent ways**: it
  fires identically at silhouettes on blank card where there is no background to
  veil (78.9%, AUC 0.600, p = 0.61); the second peak hits the background's own
  focus frame only 7.2% of the time against 1.6% chance; it does not reproduce
  across two 299-frame captures of the same scene (kappa ~ +0.11); a **derived
  single-depth defocus side-lobe reproduces it** (side-lobe takes `k2` 54–68% of
  the time, the true background peak 0.0–1.0%); and prominence tracks **edge
  contrast, not class** (rho = +0.772). SYNTHESIS fact 969 records the
  consequence: *"The two-layer occlusion-unmixing proposal is DEAD."*
  M63 is careful about what it did **not** show: *"M63 does not show that
  veiled-background peaks do not exist"* — it shows this statistic is not
  evidence of one.
  **M87's position, registered now:** the *detection-by-bimodality* route is
  closed and M87 will not re-run it as though it were open. M87 asks the
  strictly different question that M63 did not: **does the halo itself exist,
  what is its shape, and is that shape what two-layer veiling predicts?**
  The halo is an error in the merged *output*; bimodality is a property of the
  *focus curve*. A model can be right about the first and undetectable by the
  second.
- **`M21-occlusion-bimodality-measured.md`** — superseded by M63 and carrying
  `AGENTS.md` rule 17's circularity instance (29.47× → 4.38×). Used only for the
  shift/permutation control design it motivates.
- **`M13-window-depth-measured.md`** — synthetic **two-layer occluding-edge
  plants** (Porter-Duff `over` of two real corpus textures at two planted
  depths, premultiplied occluder, same-kernel mask blur, no resampling) and the
  **oracle headroom**: 5.7%–46.8% of band RMS over the better fixed window
  across 24 discontinuity cells, against a best realisable hand-written rule of
  **+5.4%**, usually negative. Its metric is `E_excess = band_rms − floor`.
  SYNTHESIS **fact 64** is the methodological instruction M87 inherits: a
  per-pixel ROI average is *structurally blind* to the occlusion halo, because
  the damage lives in a band that is a small fraction of the ROI by area, so
  **"any future focus-measure metric must include an edge-referenced term"**.
  M87's metric is edge-referenced for this reason.
- **SYNTHESIS fact 411** — *"First to model the occlusion halo" is FALSE and
  must not be claimed*: Asada et al. 1995/1998, Bhasin & Chaudhuri 2001, Favaro
  & Soatto 2003, McGuire et al. 2005, Hasinoff & Kutulakos 2007, McCloskey et
  al. 2011, Wang et al. 2015. **M87 makes no novelty claim of any kind**, and
  per `M83-survey-audit.md` (13/18 load-bearing survey claims adverse) M87
  inherits no "nobody does this" phrasing from this corpus.
- **SYNTHESIS fact 412** — Wang et al. 2015's cheap published remedy: partition
  by mode and merge within the mode, *"no `α`, `F`, `B` unmixing required"*, and
  the corpus's own instruction is **"Try the focus-axis analogue of Wang 2015
  before anything bespoke."** Registered below as arm F1, ahead of unmixing.
- **SYNTHESIS fact 549** — blur-then-composite and composite-then-blur differ by
  **5.2% of level in a 48 px band** at an occluding edge. My plant must state
  and use one order. It uses the layered-defocus order (occlude in the scene,
  then blur each layer by its own depth's PSF, then composite with the blurred
  matte), and says so in the code.
- **SYNTHESIS facts 567/568/603** — M25's simulator **does not contain the
  effect it was built to test**: truth-gated veiled pixels are multi-peaked at
  2.4% against 10.4% on smooth depth, enrichment **0.23×, the wrong sign**, and
  multi-scale occluder geometry moves it only to 0.86×, still below 1.0.
  **M87 therefore does not reuse `experiments/m25-simulator/src/strehl_sim/scene.py`'s
  `two_layer_occlusion` as its plant**, and does not treat that plant's silence
  as evidence about the halo. It builds its own, and it registers a capability
  check (§6) that the plant must pass *before* any result computed on it counts.

---

## 1. The question, and the model under test

At an occluding edge a background pixel is **veiled** by the defocused
foreground. The two-layer model is

```
I_k(x) = alpha_k(x) * (F conv PSF_k^F)(x)  +  (1 - alpha_k(x)) * (B conv PSF_k^B)(x)
```

`alpha_k` is the per-frame coverage of the pixel by the foreground's blur
circle; it grows as the foreground defocuses and shrinks as it sharpens. The
claim under test is that the bright band visible around every leg and body edge
in `C:\dev\strehl-out\crop-leg-halo.png` is this composite being *selected* —
that the focus measure at such a pixel is dominated by the foreground's edge
ramp and so elects a frame in which the background is wrong.

**Note on sign, registered before measuring:** the halo in the delivered crop is
*brighter* than the surrounding background while the occluder (the leg) is
*dark*. A pure veil by a dark `F` over a uniform `B` can only darken. So if the
two-layer model is to explain this artifact, one of the following must be true
and must be **measured**, not assumed:

- (S1) the near-edge foreground is **bright** at the relevant frames (the bee's
  pale hair fringe, specular highlights), so `alpha_k * F` exceeds `B`; or
- (S2) `B` is **not** locally uniform — the true near-subject background is
  darker (contact shadow), and a defocused `B conv PSF^B` pulls in brighter
  light from further out; or
- (S3) both.

If neither holds at the measured edges, the two-layer model as stated does not
explain this artifact and M87 says so.

---

## 2. The halo metric `H` — frozen definition

All arithmetic on the **binned green plane** (one value per CFA 2x2 quad,
`0.5*(G1+G2)`, black level 512 subtracted), in linear DN, at the merged
output's native 3516x2344 grid.

1. **Foreground mask `S`.** From the merged luma: `S = luma < tau`, with `tau`
   the midpoint between the two dominant modes of the ROI luma histogram
   (128 bins, modes located by the two largest peaks after a 3-bin box smooth).
   Then binary closing then opening with a disc of radius 3, and connected
   components smaller than 2000 binned px discarded.
2. **Distance.** `d(x)` = exact Euclidean distance transform to `S`, evaluated
   on background pixels only (`x` not in `S`).
3. **Profile.** Inside a registered ROI rectangle, `P(d) = median{ M(x) : x not in S,
   round(d(x)) = d }` for `d = 1 .. 96`. Bins with fewer than 200 pixels are
   dropped.
4. **Baseline.** Ordinary least squares line fitted to `P(d)` over
   `d in [48, 96]`, extrapolated to all `d`.
5. **Excess.** `E(d) = P(d) - baseline(d)`, in DN.
6. **`H = max_{d in [1,24]} |E(d)|`**, reported in DN and as a percentage of
   `baseline(0)`. **Signed** companion `H_signed = E(d*)` at the argmax `d*`.
7. **Width `W`** = the smallest `d > d*` with `|E(d)| < |H|/e`.

`H` is edge-referenced by construction, which is what SYNTHESIS fact 64 says any
metric aimed at this artifact must be.

### 2.1 Which direction `H` can be fooled in (rule 18)

`H` rises whenever the background level near the silhouette departs from the
far-field trend, **for any reason**. It cannot distinguish a merge artifact from
real scene content that hugs the subject (rim light, translucent hairs, a
contact shadow, a reflection). It is therefore admissible as a measure of *how
much band-shaped structure is present*, and **inadmissible on its own as
evidence that a merge produced it**. The two controls in §3 exist precisely to
supply that missing evidence, and `H` is not quoted anywhere in this milestone
without `H_shift` and `H_frame` beside it.

`H` is also blind to anything that is not a **level** excursion: a halo that
corrupted background *texture* without moving its median would read zero. The
backgrounds in these captures are heavily defocused and nearly textureless, so
this is the right first metric for them and the wrong one for a textured
background. Stated here so it is not quoted out of that domain.

---

## 3. The two controls that give `H` power to fail (rules 9, 11, 20)

**C1 — shift placebo (`H_shift`).** Recompute steps 2–6 with the mask `S`
translated by a registered offset of `(+512, +512)` binned px, keeping only
translated-mask pixels that land in background. This destroys per-pixel
correspondence while preserving every spatial statistic of the mask — the
control `AGENTS.md` rule 17 prescribes. A metric that reads the same on the
shifted mask is reading scene structure, not an edge-locked band.

**C2 — single-frame control (`H_frame`), the primary falsifier.** Compute `H`
on **individual input frames**, unmerged, with the same mask: (a) the frame that
maximises the focus field inside the subject (`k_F`, foreground sharp) and (b)
the frame that maximises it in the near background band (`k_B`). No selection
has occurred in either. **If the bright band is already present in a single
frame at comparable amplitude, it is scene content and not a merge artifact**,
and M87 reports that immediately and loudly, because it would redirect the
milestone and possibly others.

**C3 — flat-ROI planted mask (rule 9, run first).** Plant a synthetic disc mask
of radius 120 binned px in a registered background-only rectangle containing no
subject and no real edge, and run the entire metric. Must read `H ~ H_shift`.
Run **before** any halo number is computed, not as a closing check.

### 3.1 An input that would make each gate FAIL exists (rule 20)

| Gate | Input that fails it | Does such an input exist? |
| --- | --- | --- |
| `H >= 4 * H_shift` | a merged image with no edge-locked band | yes — C3's planted disc in flat background, and the ideal/oracle render of the plant (§6) |
| `H_merged >= 2 * H_frame` | a scene whose rim is real | yes — this is C2's own alternative hypothesis, and it is a live possibility for a hairy backlit bee |
| unmixing improves `H` | a fix that does nothing, or makes it worse | yes — §7's deliberately broken variants (wrong PSF scale, swapped layer order) |
| plant expresses the halo | a plant that cannot (fact 568's) | yes — that plant exists in this repository and is why §6 is registered |

---

## 4. Stacks, ROIs and arms — frozen

All corpus paths are **READ-ONLY**. Nothing under `D:\personal\macro`,
`C:\dev\macro` or `D:\macro-dark-frames` is written. Scratch lives in
`experiments/M87-occlusion/{data,out}`; deliverable crops go to
`C:\dev\strehl-out\M87-before-after\` (a new directory M87 creates; nothing
pre-existing in `C:\dev\strehl-out\` is deleted or overwritten).

| id | stack | frames | role |
| --- | --- | --- | --- |
| A | `D:\personal\macro\bee-3-cpl` | 299, ISO 100 | primary. The artifact the owner delivered |
| B1 | `D:\personal\macro\flower-bud-alone-cpl` | 205 | A/B, no deliberate background |
| B2 | `D:\personal\macro\flower-bud-with-background-fern-cpl` | 299 | A/B, with background |
| C | `D:\personal\macro\flat-on-ruler-cpl` | 79 | **non-occluding-edge control**: high-contrast ink edges on a flat surface at one depth. A fix aimed at occlusion must do nothing here |
| P | synthetic, §6 | 61 | plant with known `F`, `B`, `alpha_k` |

Registered ROIs, binned output coordinates `(y0:y1, x0:x1)` on the 2344x3516
grid, chosen from the owner's delivered whole-frame render **before** any metric
was computed:

- `ROI_LEG   = (1200:1900,  300:1400)` — the owner's own crop region.
- `ROI_BODY  = ( 200: 900, 1500:2600)` — thorax/wing edge against background.
- `ROI_FLAT  = (1300:2300,    0: 180)` — background only, for C3.

If a registered ROI turns out to contain no usable edge, or `ROI_FLAT` turns out
to contain subject pixels, the adjustment and its reason are disclosed in the
report.

### 4.1 The A/B is not ground truth, and its comparability is measured first

The owner's own caution is adopted: B1/B2 are an A/B, **not** ground truth — no
capture can see behind an opaque subject. Before either is used, M87 measures
and reports: frame count, per-frame mean level and its drift across the sweep,
subject pose and framing overlap, and the background's spatial statistics. **If
framing or pose differ materially, the pair is reported as a weak A/B and is not
used as truth for any bar.**

---

## 5. The merge under study, and its validation

M87 does not edit `crates/`. It uses two "before" arms:

1. The owner's delivered `C:\dev\strehl-out\bee3-full.tif`, `bee3-g0.tif`,
   `bee3-g1.tif` — read-only, as the artifact of record.
2. An **independent Python merge**, written from `merge.rs` / `focus.rs` /
   `plane.rs` / `boxfilter.rs` semantics, reusing the already-validated
   implementation in `experiments/m52-gate-cluster/src/03-fact324-n-eff-independent.py`
   (whose merge M52 measured as agreeing with the shipped binary to <= 0.09% on
   all seven stacks):
   `luma = 0.5*(max(G1-512,0)+max(G2-512,0))`;
   `grad = 0.125*hypot(sobel_x, sobel_y)`, replicate border;
   `focus = clamped_box(grad, 13) / green_luma_sigma(luma, iso)`;
   `reg = clamped_box(focus, 8)`; admit `k` iff `best - reg_k <= t*sqrt(2)*FOCUS_NOISE_SD`
   with `FOCUS_NOISE_SD = 0.015214`; estimate = mean of admitted frames.
   Gates measured: **0.0 (pure selector, one frame per pixel)** and **2.0**.

**Validation bar, registered:** inside `ROI_LEG`, my Python merge's green plane
must reach **Spearman rho >= 0.99** against the delivered shipped TIFF's green
channel, and its halo profile `E(d)` must agree with the shipped TIFF's in
**shape** (Pearson r >= 0.9 over `d in [1,48]`). If it misses, the Python merge
is not used as the "before" arm and the shipped TIFF is, and the miss is
reported.

**The gate claim in the brief is re-checked, not inherited.** The owner reports
the halo looking identical at gate 0 and gate 2 (`mean n_eff = 23.043`, 46.57%
of pixels at `n_eff = 1`). M87 reproduces `H` at both gates and reports the
ratio. Registered reading: **if `H(gate 2) / H(gate 0)` lies in [0.8, 1.25], the
halo is not produced by the averaging gate and cannot be tuned away with it.**

---

## 6. The plant, and the capability check it must pass first (rule 13)

`F`, `B`, `alpha_k` known by construction. Layered defocus, stated order:
occlusion happens in the scene; each layer is then blurred by its own depth's
PSF; the blurred matte composites them.

```
I_k = (m * F) conv PSF_k^F  +  (B conv PSF_k^B) * (1 - m conv PSF_k^F)
```

with `m` the binary foreground mask, `PSF^F`/`PSF^B` disc kernels whose radii
follow `r_k = |k - k_layer| * s` for a registered `s`, and Poisson+read noise
from this project's own model at ISO 100. `alpha_k = m conv PSF_k^F`, exactly
the quantity the model names.

**Why this plant can express a halo, argued before it is built (rule 13, and
the trap facts 568/603 record).** At a background pixel in the band, the
regularised Tenengrad field is dominated by the foreground's edge ramp, whose
gradient energy is maximised near `k_F`, not `k_B`. So a selector elects a frame
in which the background layer is defocused and the foreground's veil is at its
*sharpest-edge*, not its smallest, value. The elected value therefore differs
from `B` by `alpha_{k_F}*(F - B conv PSF^B_{k_F})`, which is **non-zero
wherever the two layers differ in radiance and `alpha > 0`** — that is, in a
band whose width is the foreground's blur radius. Nothing in this argument
requires the *focus curve* to be bimodal, which is why fact 568's plant could be
silent on multi-peakedness and still be able to show a halo. **The argument is
not accepted on its own**: the plant must pass the capability check below.

**Capability check, run before any plant result is quoted.** On the plant:
- `H(oracle)` — the ideal render `B` where the mask is background — must read
  `<= 2 * H_shift`. If the ideal render carries a halo, the plant's geometry is
  making one and the plant is void.
- `H(selector merge)` must read `>= 4 * H_shift`. **If it does not, the plant
  cannot express the failure it exists to test, and every plant number in this
  milestone is reported as void** — the outcome facts 568 and 603 record for
  the last plant pointed at this phenomenon.
- The plant's halo must have the **sign** predicted from its own `F` and `B`
  radiances. A plant built with a bright fringe must halo bright; one built
  dark-on-bright must halo dark. Both are built and both are checked, because a
  plant that halos in only one direction cannot test S1 against S2.

---

## 7. Arms, in the order the corpus tells me to run them

- **F0 — no fix.** Baseline `H`.
- **F1 — the Wang-2015 focus-axis analogue** (SYNTHESIS fact 412's explicit
  instruction to try before anything bespoke): at band pixels, restrict
  admission to frames on the **background** side of the local through-focus
  ordering, and merge within that mode. No `alpha`, `F` or `B` estimated.
- **F2 — two-layer unmixing.** With `alpha_k` estimated from the foreground
  mask dilated by the foreground's blur radius at frame `k`, and `F conv PSF_k`
  estimated by convolving the merged foreground with the same kernel, solve the
  matting equation for the background layer:
  `B_hat = (I_k - alpha_k * (F conv PSF_k)) / (1 - alpha_k)`, at the frame
  where the background is best focused, with a registered guard
  `alpha_k <= ALPHA_MAX = 0.7` (above which the equation is ill-conditioned and
  the pixel is left untouched and counted).

**Deliberate breakage (a control that can fail, made to fail).** F2 is re-run on
the plant with (i) the PSF scale wrong by 2x and by 0.5x, and (ii) the layer
order swapped (`F` and `B` exchanged). Registered expectation: `H` after each
broken variant must be **worse than F0 or no better than 0.8 * H(F0)**. If a
broken unmixing still "fixes" the halo, F2 is not doing what it claims and M87
says so.

---

## 8. Success bars — frozen

| # | bar | what it decides |
| --- | --- | --- |
| G1 | `H(A, gate 0) >= 4 * H_shift(A, gate 0)` and `H >= 5 DN` | the halo is real, edge-locked, and the metric responds |
| G2 | `H_merged >= 2 * H_frame` for both `k_F` and `k_B` | the halo is produced by the merge, not by the scene |
| G3 | `H(gate 2) / H(gate 0)` in `[0.8, 1.25]` | reproduces the owner's gate-invariance claim |
| G4 | plant capability check of §6 passes | plant results may be quoted at all |
| G5 | on the plant, F2 with **known** `alpha`, `F` recovers `B` to `H_after <= 0.25 * H_before` | the model can express and invert the artifact |
| G6 | on real data (A), best of F1/F2 gives `H_after <= 0.4 * H_before` | the fix works where it matters |
| G7 | placebo: `|H_shift_after - H_shift_before| <= 0.1 * H_before`, C3 unchanged within the same bound, and stack C's `H` changes by `<= 0.15 * H(A)` | the fix is not a general-purpose smoother |
| G8 | false-positive rate reported as the fraction of pixels the fix alters that lie outside the registered occluding band, **and** the alteration measured on stack C and on the bee's translucent wing | the cost is priced, not hidden |

**A negative on G5 or G6 is a full result** and is reported as one.

---

## 9. What result would mean the two-layer model is WRONG

Registered now, so it cannot be renegotiated later.

- **W1 (the loud one).** `H_frame >= 0.5 * H_merged` — the band is present in a
  single unmerged frame at comparable amplitude. Then the halo is **scene
  content or a per-frame optical effect**, not a two-layer selection artifact,
  and the correct action is to say so immediately, because it redirects the
  other agents working tonight.
- **W2.** The measured sign of `E(d)` is inconsistent with the measured local
  `(F - B)` at more than half of the sampled edge segments, with neither S1 nor
  S2 of §1 holding. The model then has the wrong sign and is not the mechanism.
- **W3.** On the plant, with `alpha_k`, `F` and `B` **known exactly**, F2 fails
  G5. The model then cannot invert its own forward process, so it is not a
  useful description of the artifact even if it is a true one.
- **W4.** The plant fails §6's capability check in the direction that the
  selector merge shows **no** halo. Then the two-layer forward model does not
  generate this artifact, and something outside it does.
- **W5 (the mundane causes, checked explicitly).** The halo is instead
  attributable to
  (a) **resampling ringing** — checked by reading the output path:
      `merge_cmd.rs::write_merged` emits one RGB pixel per CFA 2x2 quad with no
      interpolation and no kernel, so a negative-lobed resampler cannot be the
      cause; verified by re-reading the code and by the halo's measured width
      being many pixels rather than one;
  (b) **clipping** — checked by the output's own maximum (`bee3-*.tif` peak
      53370 of 65535) and by counting pixels at the white level inside the band
      in the input frames;
  (c) **the missing colour matrix** — checked by measuring `H` on the **green
      plane alone**, which no colour matrix touches;
  (d) **absence of alignment** — checked by measuring the frame-to-frame
      displacement across the stack inside `ROI_LEG` and asking whether it is
      large enough to smear an edge by the measured halo width `W`.
  If any of (a)–(d) accounts for the artifact, that is the headline and the
  two-layer work is reported as unnecessary.

---

## 10. Rule discharge (rule 22 — named per rule, at report time)

The report will carry a table naming, per binding `AGENTS.md` rule, the command
or line that discharges it. Rules already discharged by this document: 13 (§6),
15 (§0), 17 (C1), 18 (§2.1), 20 (§3.1), 22 (this section), 40 (§0), 41 (stem
allocated as `M87`, writing to `experiments/M87-occlusion/` and
`docs/research/M87-occlusion.md`).

Registered by M87 before measurement.

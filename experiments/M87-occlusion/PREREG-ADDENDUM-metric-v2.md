# M87 — Pre-registration addendum 1: metric v2, and disclosed deviations

Status: **registered before use.** Written and committed after the v1 instrument
failed its own bar and before any arm (F0/F1/F2) is scored. Everything in
`PREREGISTRATION.md` stands except where explicitly superseded here.

All claims below are labelled MEASURED / DERIVED / ARGUED. Numbers from other
milestones are namespaced (`M6.`, `M13.`, `M63.`, `M52.`); numbers produced here
are namespaced `M87.` and carry candidate-fact ids `P1, P2, …` in the report,
never absolute SYNTHESIS ids (rule 28).

---

## D0. Disclosed deviations from `PREREGISTRATION.md`

### D0.1 The registered foreground mask rule is defective on this image — replaced by Otsu

**MEASURED.** The registered two-mode rule (§2 step 1) put τ = 33 540 DN on
`bee3-full.tif`, giving foreground fraction 0.698 and — decisively — **46 % of
the background-only `ROI_FLAT` inside the "foreground" mask**. Cause: the
*background* is itself bimodal (two card/surface modes near 30 800 and 37 800 DN),
so the two-mode rule locks onto the background's own two modes.

Replacement: **Otsu** on the same green-luma plane. τ = 23 937 DN, foreground
fraction 0.3654, `ROI_FLAT` foreground fraction **0.00000**. Documented in
`src/m87lib.py::foreground_mask`.

### D0.2 Metric v1 FAILED its registered bar G1 — instrument replaced

**MEASURED.** With the Otsu mask, on all three shipped renders
(`bee3-full`, `bee3-g0`, `bee3-g1`):

| ROI | H (DN) | H_shift (DN) | H / H_shift | G1 bar |
| --- | --- | --- | --- | --- |
| `ROI_LEG` | 6114–6321 | 3518–3612 | **1.71–1.76×** | ≥ 4× |
| `ROI_BODY` | 2822–2833 | 3576–3612 | **0.78–0.79×** | ≥ 4× |

The instrument had the power to fail and it failed. Per §2.1 the stated failure
direction was exactly this: the far-field linear baseline assumes the background
is one homogeneous surface, and in `bee-3-cpl` the card carries a large-scale
illumination gradient, so a radial profile averaged over the whole perimeter
mixes background levels that differ by far more than the halo.

**Nothing downstream of v1 is quoted in the report except as evidence that v1
failed.** v2 below is the instrument of record.

### D0.3 Dispatch-brief pointer errors (already recorded in `PREREGISTRATION.md` §0)

- The bimodality milestone is **`docs/research/M63-bimodality.md`**, not `M60-*`
  (`M60-*.md` are the prior-art and robustness-mask reports; the experiment
  directory keeps the `M60-bimodality` stem deliberately).
- **`docs/research/M6-residual-halo-measured.md` measures a different "halo"** —
  the *plugin rectangle-expansion* halo (19.42 / 32.39 / 89.23 plane px), not the
  occlusion halo. M6 line 46: "a halo is a rectangle expansion". Not a prior for
  this milestone beyond the name collision (rule 15).

### D0.4 The mundane-cause sweep, and one real finding that is NOT the halo

**MEASURED.** Two mundane causes are eliminated at source:

- **Resampling ringing**: `crates/strehl-cli/src/merge_cmd.rs::write_merged`
  emits one RGB pixel per CFA 2×2 quad with no interpolation and no kernel, so
  no multi-pixel band can be manufactured by resampling.
- **Clipping**: max of `bee3-*.tif` is 53 370 / 65 535.

**MEASURED, and it is a real defect but not this one:** the sweep drifts
photometrically by **18.09 % of mean level** across 299 frames (green luma over
a fixed far-background set: min 3087.2 DN @ k=298, max 3704.5 DN @ k=103).
Because a per-pixel selector writes one frame's value per pixel, that drift is
imported into the output as a level patchwork. Its contribution to the
near-edge band, however, is small and of the **wrong sign**: predicted step
⟨L(k_band)⟩ − ⟨L(k_far)⟩ = **+77.1 DN** against an observed band-minus-far step of
**−539.8 DN**, and re-running the merge with the estimate divided by each
frame's own L(k) — **selection left bit-identical** — does not remove the visible
halo (`out/05-raw.png` vs `out/05-norm.png`).

**Registered consequence:** photometric drift is *reported to the owner as an
independent finding for the output/colour agent* and is **not** the halo. If v2
shows otherwise, that is reported instead.

---

## D1. Metric v2 — local edge-normal overshoot

Defined in full in `src/m87metric2.py`. Restated here so the definition is
frozen in Git before any arm is scored.

For each background boundary pixel `p_j` of the foreground mask, with outward
unit normal `n_j` taken as the gradient of the Gaussian-smoothed (σ = 4 px)
exterior distance transform:

```
s_j(d) = image(p_j + d·n_j),          d = 0 … 64          (bilinear)
b_j    = median{ s_j(d) : d ∈ [48,64] }                     local asymptote
q_j(d) = s_j(d) / b_j
o_j    = max{ q_j(d) : d ∈ [4,32] } − 1                     local overshoot
O      = median_j o_j
```

Profiles are rejected if they re-enter the mask at any `d ≥ 2` or leave the
frame. At least 200 surviving profiles are required. Uncertainty is a 2000-draw
bootstrap 95 % CI of the median.

`O > 0` ⇔ the value overshoots its own local asymptote on the way out of the
edge, i.e. a bright halo. `O ≈ 0` ⇔ monotone approach, i.e. a clean edge.

**Why this is the right shape of instrument.** (ARGUED) It is edge-referenced,
as SYNTHESIS fact 64 requires. Each profile divides by its own far value, so the
card's illumination gradient cancels to first order — the exact assumption that
killed v1. It is defined identically for a merge and for one frame, so the
single-frame control is an **exactly paired** comparison on the same points and
normals. And its null is a physical statement rather than a fitted baseline: a
defocused occluding edge in a single exposure has a *monotone* edge-spread
profile, so a single frame must score ≈ 0.

**Stated failure direction of v2 (before use).** If the background is not
locally flat over 64 px along the normal — another subject part just outside the
edge, or strong background texture — then `b_j` is wrong and `o_j` picks up scene
content rather than halo. C1 and C3 below are what catch that.

---

## D2. Bars for v2, registered before use

| id | test | bar | if it fails |
| --- | --- | --- | --- |
| **V1** | sensitivity: gate-0 merge, `ROI_LEG` | `O ≥ +0.02` and bootstrap CI excludes 0 | v2 is blind too; report the metric as unsolved and stop — no arm is scoreable |
| **V2** | placebo C1: mask translated (+512,+512) into empty background, same image | `|O| ≤ 0.005` | the metric responds to something other than the edge; disclose and rebuild |
| **V3** | placebo C3: synthetic disc planted in `ROI_FLAT`, same image | `|O| ≤ 0.005` | same |
| **V4** | control C2: **single frames** at `k_F`, `k_far`, frame 0, same points/normals | single-frame `O ≤ 0.5 × O(merge)` | **W1 fires**: the halo is scene content (rim light / translucent hair), not a selection artifact. Report immediately and loudly; it redirects the other agents. |
| **V5** | plant capability (rule: facts 567/568/603) | merged synthetic two-layer scene gives `O ≥ +0.02`; its ground-truth all-in-focus composite gives `|O| ≤ 0.005` | the plant cannot express the effect it exists to test; rebuild before quoting any plant number |
| **V6** | gate invariance (owner's claim, G3) | `O(gate 0)` and `O(gate 2)` agree within their CIs | the owner's gate-invariance claim is wrong; say so |

## D3. Bars for the fix arms

Arms as registered in `PREREGISTRATION.md` §7: **F0** shipped merge (baseline),
**F1** Wang-2015 mode partition (fact 412 — try the cheap published remedy
*first*), **F2** two-layer unmixing.

| id | test | bar |
| --- | --- | --- |
| **X1** | halo removal on `ROI_LEG` | `O_fix ≤ 0.5 × O_F0`, CIs non-overlapping |
| **X2** | **placebo — must do nothing** on `ROI_FLAT` and on an interior region of the subject | `|O_fix − O_F0| ≤ 0.005` and the pixel-wise change has RMS ≤ 1 % of level |
| **X3** | non-occluding-edge control (`flat-on-ruler-cpl`) | `|O_fix − O_F0| ≤ 0.01` |
| **X4** | deliberate breakage (PSF scale ×2 and ×0.5, swapped layer order) | the metric must **notice**: broken F2 scores worse than F0 on at least one of X1/X2 |
| **X5** | false-positive accounting | report the fraction of boundary profiles where the fix moves `o_j` in the wrong direction, and name the structures (wings, hairs, non-occluding edges) |

## D4. What would mean the two-layer model is wrong

Superseding nothing in §9 (W1–W5), restated against v2:

- **W1** single frames already score ≥ 0.5 × the merge ⇒ scene content, not selection.
- **W2** the through-focus response at halo pixels is **monotone**, not peaked at
  `k_F` ⇒ no veiling modulation to unmix.
- **W3** the halo survives an *oracle* selector that is handed the correct frame
  ⇒ the defect is not in selection at all.
- **W4** photometric normalisation removes it ⇒ level drift (already tested:
  **it does not**, D0.4).
- **W5** F2 with the *correct* PSF scale is no better than F2 with a deliberately
  wrong one ⇒ the model is not doing the work; something else is.

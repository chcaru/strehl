# M107 addendum — pre-registration for the ORCH-kernel arms (E8)

Written and committed **before** any pixel of `C:\dev\strehl-out\ORCH-kernel\`
was read. Prior commits: `ed5a929` (original pre-registration), `a16976f`
(M107 report). This file registers a *second* set of bars for a lever that
arrived after the main report was committed.

## What arrived

Three renders of `bee-3-cpl`, identical solve / placements / reference /
stack digest, differing **only** in the gather kernel, produced by rewriting
one `resampler` line in a copied sidecar (`experiments/ORCH-drift-check/kernel_ab.ps1`,
committed `d3a49e4`):

| arm | kernel | role |
|---|---|---|
| `bee-3-cpl-catmull-rom.tif` | Catmull-Rom | shipped default; byte-identical to the gallery render |
| `bee-3-cpl-nearest.tif` | nearest | zero-order hold — no lowpass, but aliases |
| `bee-3-cpl-bilinear.tif` | bilinear | strongest lowpass of the three |

The orchestrator observes, **by eye and explicitly flagged ARGUED**, that the
chromatic fringing on the bee hairs is markedly stronger under `nearest`, and
reads that as evidence the fringe is pre-existing and merely being blurred by
Catmull-Rom — which would bound my candidate (d) small for free.

I am asked to **check that reading, not adopt it.** The named falsifier is
that `nearest` also aliases, and aliasing on a Bayer-derived image can
synthesise colour structure, which would make the fringe kernel-created after
all.

## S0 — a third mechanism, excluded from source before measuring

Before registering bars I checked whether `nearest` could manufacture
*channel-differential* displacement by quantising each CFA plane's sample
phase to its own lattice. It cannot.

`align_cmd.rs::warp_frame_in_place` loops the four CFA sites `(dx, dy)` and
calls `strehl_core::warpmap::gather_checked(src, t, geom, resampler, ...)`
with **the same `t` and the same `geom`** on every pass. `gather_into`
samples at `t.apply_at(px as f64, py as f64, cx, cy)`, which depends only on
the plane coordinate — not on `(dx, dy)`. All four planes therefore land on
identical fractional coordinates and `sample_nearest`'s `x.round()`
quantises **common-mode**. A common-mode geometric shift is achromatic by
definition.

This is a source fact, not a measurement, and it is stated here so that it
cannot later be presented as a finding. It leaves exactly the two
explanations the orchestrator named.

## The physics the bars encode

Write channel `c` of the pre-gather scene as `f_c`, and the gather kernel as
a channel-independent linear filter `h`. The rendered channel is `h * f_c`.

- A **displacement-type** fringe (lateral CA, co-siting phase error) is
  `f_c(x) = f(x - d_c)`. To first order the chroma signal is `d_c * f'` and
  the luma edge signal is `f'`. Filtering both by the same `h` scales both
  identically, so **the ratio `rms(chroma_HP) / rms(luma_HP)` is invariant
  under any channel-independent linear filter.** This is the load-bearing
  prediction and it is exact to first order in `d_c`.
- A **blur-difference-type** fringe (axial CA) is `f_c = f * b_c` with `b_c`
  of differing width. The chroma signal is `f * (b_R - b_G)`, which is
  higher-order in frequency than `f'`, so under a stronger lowpass it should
  attenuate somewhat *faster* than the luma gradient. The ratio may fall; it
  must not rise, and **it cannot change sign**, because the cause is which
  frame each channel was elected from and no gather kernel can change that.
- **Aliasing** folds power from above the plane Nyquist to below it. The
  folded pattern depends on each plane's own content, so it differs between
  R, G and B and appears as colour structure. It is **not** correlated with
  the pre-existing fringe, it is concentrated near Nyquist, and on a CFA
  lattice it is axis-oriented.

## Instrument

All three TIFFs are pixel-aligned by construction. Work in linearised light
(undo the sRGB EOTF; the colour matrix and auto-exposure are common to all
three arms and so cannot bias an arm-to-arm *comparison*, though they do
attenuate absolute magnitudes — a known lower bound, per report section 5).

- `L` = luma; `C_R` = `R - G`; `C_B` = `B - G`.
- High-pass everything with the same sigma to remove the occlusion veil,
  which the orchestrator reports is identical across all three arms and
  therefore common-mode, but which is a low-frequency brightness anomaly
  living on the same pixels as the fringe.
- Restrict to edge pixels by a percentile of `|grad L|` on the **Catmull-Rom**
  arm only, so the identical pixel set is used for every arm and the mask
  cannot itself respond to the kernel.

**The free null / generic-decorrelation reference is the luma channel.**
Changing the kernel decorrelates *everything* to some degree. Any statement
that the chroma field decorrelated must be made relative to how much the luma
field decorrelated on the same pixels, or it measures the kernel change
rather than the chromaticity.

## BARS

**K1 VALIDITY.** All three arms identical in shape and dtype; the
Catmull-Rom arm's SHA-256 must match the gallery render. Luma high-pass
correlation between the nearest and Catmull-Rom arms on the edge mask must
be `>= 0.60` — they are the same scene through different kernels, and if the
luma fields do not correlate the images are not comparable pixel-for-pixel
and nothing below is interpretable. **HALT on failure.**

**K2 PREMISE.** The orchestrator's "by eye, plainly" scored as a number:
`rms(C_R_HP)` and `rms(C_B_HP)` on the edge mask must be **higher under
`nearest` than under `catmull-rom`**, by a ratio `> 1.15`.
- If the ratio is `<= 1.05` the premise is **false**, the eye was reading
  luma acutance as colour, and everything downstream is moot.
- Registered before looking. I am scoring someone else's visual claim and it
  is entitled to fail.

**K3 RATIO INVARIANCE — the discriminator.** `rho = rms(chroma_HP) / rms(luma_HP)`.
- **Pre-existing displacement fringe merely re-filtered: `rho_nearest / rho_catmull` in `[0.85, 1.18]`.**
- **Aliasing synthesises chroma: `rho_nearest / rho_catmull > 1.30`.**
- Between 1.18 and 1.30: **INDETERMINATE**, and I will say so rather than
  round toward either.

**K4 STRUCTURE.** `r_chroma = corr(C_HP_nearest, C_HP_catmull)` on the edge
mask, against `r_luma = corr(L_HP_nearest, L_HP_catmull)` on the same pixels.
- Same fringe, higher contrast: `r_chroma >= 0.70 * r_luma` **and** the
  least-squares slope of nearest on catmull is **positive**.
- Aliasing-created: `r_chroma < 0.40 * r_luma`.
- A negative slope falsifies "same fringe" outright regardless of `r`.

**K5 LATTICE.** Residual `Res = C_HP_nearest - s * C_HP_catmull` at the
least-squares `s`. Aliasing is implicated if **both** (i) `>= 50%` of `Res`
power lies above `0.7 x Nyquist`, and (ii) axis-aligned anisotropy
(mean power within +-15 deg of the u/v axes divided by mean power elsewhere,
above 0.7 Nyquist) is `> 1.5`. Both must hold; either alone is not enough,
because a high-pass residual is high-frequency by construction and that on
its own proves nothing. The same two statistics computed on the **luma**
residual are the reference — if luma shows the same lattice signature, the
signature is generic to `nearest` and not chromatic.

**K6 (b) vs (c).** Nyquist-scale co-siting error is hit hardest by a lowpass;
a depth-election error is not.
- `rho_bilinear / rho_nearest < 0.50` implicates Nyquist-scale (c)-type
  content as a dominant contributor.
- `rho_bilinear / rho_nearest` in `[0.70, 1.40]` bounds (c) small and is
  consistent with the (a)+(b) attribution already committed in
  `docs/research/M107-chroma.md`.
- The sign of the chroma field must be preserved across all three arms
  (positive LS slope pairwise). A sign flip under blur would falsify (b)'s
  mechanism as I described it in report section 4.

## What this addendum may and may not change

It may bound (c) and (d) tighter, and it may falsify the orchestrator's
reading. It **cannot** revise (a) or (b): both were measured on raw CFA
planes that never passed through strehl's gather at all (report sections 3
and 4), and the warp-OFF arm in `e6_payoff.py` already moved `dR` by 1.6%.
Nothing in these three files can reach those results, and I will not let a
new lever be presented as corroboration of a conclusion it cannot touch.

No code under `crates/` is edited. Diagnosis only.

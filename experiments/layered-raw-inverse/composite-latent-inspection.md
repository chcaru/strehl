# Saved latent inspection: composite prior

**MEASURED, descriptive only.** The rejected composite result changes coverage
and conceals large, uneven sheet radiances; it does not merely estimate smoother
physical sheets. Its delivered highlight and coloured filament are suppressed.
All four inspected fits returned nonstationary states, so this diagnoses these
saved checkpoints, not a unique optimum or an impossibility theorem.

The read-only inspection loaded the complete 96×96 `reconstruction.npz` arrays
from `composite-1/output/{flat,layered}/{original,composite}`. Summaries use the
already fixed valid interior `[16:80,16:80]` for flat, and fixed native core
`[x39,y42,x52,y55)` for layered. Truth coverage comes from unchanged
`independent-controls.py::scene`, never fitted coverage. No model forward,
optimization, RAW read, file modification, or new acceptance score was used.
The command was inline Python 3.12 (`-I -B -`), using `numpy.load`, `scene`,
`numpy.quantile` at .1/.5/.9/.99 and fixed coordinate indexing. Values below are
black-subtracted camera RGB DN, not displayed RGB or recoverable sensor codes.

## Fixed highlight core

The planted centre is native `(45,48)`, selected by the frozen scene rather
than a fitted maximum:

| Saved state | Alpha | Delivered RGB | Far-sheet RGB |
| --- | ---: | --- | --- |
| Truth | 0.044 | 28844, 28299, 24850 | 30095, 29495, 25695 |
| Original prior | 0.004 | 23227, 22449, 20090 | 23301, 22519, 20143 |
| Composite prior | **1 exactly** | **2911, 3335, 3036** | **503, 15982, 80236** |

At the composite centre, the far sheet has exactly zero pinhole visibility.
The delivered value is its near sheet. This is a direct coverage/radiance escape,
not a hypothesis inferred from reduced gradient energy. It does not mean that
the hidden sheet is absent from every defocused observation: the per-ray
visibility model can expose different samples in those observations.

Across all 169 core pixels, composite near-sheet 99th-percentile RGB is
`[65819,21313,159663]`, versus original `[4331,5799,5521]`; its near-sheet maxima
are `[143942,33892,297628]`. Meanwhile composite delivered maxima are only
`[3060,4366,4015]`, versus truth `[28844,28299,24850]`.

This is not solely a statement about truth-occluded pixels. Of the fixed core,
60 pixels have **truth alpha < .1**. Their fitted alpha median/p90 changes from
`.003/.012` under the original prior to `.202/1` under the composite prior.
Their mean delivered RGB falls from `[5171,5425,4406]` to `[2549,2898,2318]`
(truth `[5064,5351,4302]`). The other independently specified stratum, truth
alpha > .8, has 37 pixels; no fitted-alpha bin was used to define either group.

The saved objective corroborates the trade rather than establishing quality:
layered data NLL **worsens 3.81269 → 3.99368**, prior falls **2.32196 → .68916**,
and total falls **6.13465 → 4.68284**. Existing independent scores already reject:
glint component recovery falls from roughly 1.01 to .05, and glint-free coloured
filament recovery from .95–.99 to .24–.36. Those existing tests, not the latent
quantiles, determine rejection.

## Flat control

Truth is constant `[2500,3200,2000]` with alpha .35. Composite delivered medians
are `[2492,3196,1986]` and maxima `[2501,3209,1997]`: flatter but biased, still
failing the original mean-reference noise bars. Its hidden sheets are not flat:
near-sheet p99 is `[8547,9621,6550]`, maxima `[22471,22733,18219]`; far-sheet p99
is `[6230,6843,5137]`. Original near-sheet maxima were only `[2613,3301,2100]`.
Thus the delivered-image penalty exchanges visible variation for latent
compensation even on a scene with no true layer texture.

## One useful causal intervention

**ARGUED:** freeze alpha to the independent truth coverage, restore the exact
same screen-1 radiance parameters, and fit radiances using the **original sheet
prior**, unchanged likelihood and solver budget. Compare against the existing
matched-budget free-alpha original-prior arms. This isolates coverage freedom
without simultaneously adopting the failed composite objective or changing its
strength. The initial pinhole image intentionally changes when alpha changes.
Keep alpha-prior terms as constants or document their constant offset; do not
alter any radiance prior coefficient. Fit sees alpha only, never truth sheets.

Use the already fixed flat, highlight, glint-free filament and held-out bright
bars. Improvement would establish only that known visibility removes a harmful
degree of freedom in this discrete known-optics plant. Failure would show that
coverage alone is insufficient; it would not license another weight sweep.
Neither outcome supplies an automatic alpha estimator or fixes the known
64-ray versus 1024-ray physical-adequacy failure.

## Array bindings

All paths below are under `composite-1/output`; SHA256 binds the inspected bytes.

| File | SHA256 |
| --- | --- |
| flat/original/reconstruction.npz | 39591e41736a0b5a1d182a367dc1a411081952864510303c51dae14fabf31ab4 |
| flat/composite/reconstruction.npz | 590ae283a2110a8a8f65fbaee018da4edf62fa2206ba498772c4e8cbd0f769ff |
| layered/original/reconstruction.npz | e4348cb0d5a25e1f48ba1547c665ce084e84cace4dcf01400a5f5e3039318579 |
| layered/composite/reconstruction.npz | 75e70ae2511be45fb309a5c3a8d703765536986730619255b02724254eb70fc7 |

Frozen truth generator SHA256:
`6915c024dbbfaa0e0d912ecba1a22075aabce6ef29c845f0e586472be60815ec`.
Existing rejection and objective receipts: `composite-1/scored/result.json`
and the four corresponding `receipt.json` files. No result is promoted here.

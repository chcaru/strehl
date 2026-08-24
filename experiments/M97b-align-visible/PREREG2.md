# M97c pre-registration — why a sharpness metric ranks a sharper image lower

Written before any measurement in this milestone. Rule 12.

## The ground truth I am calibrating against

The orchestrator looked at co-located 640x640 crops of
`bee-3-ALIGNED.tif` against `bee3-zoomnull.tif` (FOV- and resampler-matched,
registration discarded in the null) and reported the aligned render visibly
sharper. **I opened `crop-wing-venation.png` myself before writing this file
and I independently confirm it**: the aligned render resolves the membrane
bristles as distinct dark strokes and separates the lower-left hair mass into
individual hairs; the null smears both, and its vein boundaries are softer.

Whole-frame Tenengrad ranks them **0.9790** — aligned *worse*. So on this pair
the metric is anti-correlated with visible quality. That is the anomaly.

## The mechanism under test, and why I doubt the stated form

The orchestrator's ARGUED mechanism is **edge doubling**: "a doubled edge has
two gradients where a correct one has a single sharper gradient", so
misregistration manufactures gradient energy.

**I think the algebra runs the other way, and I am pre-registering that
disagreement before I measure it.** Tenengrad sums the *square* of the
gradient. A step of height `h` resolved in one pixel contributes `h^2`. Split
into two steps of `h/2`, it contributes `2*(h/2)^2 = h^2/2`. Spread over `n`
pixels it contributes `h^2/n`. **Doubling and blurring both LOWER Tenengrad on
an isolated edge.** That is precisely why Tenengrad is a focus measure at all.

If that holds, edge doubling cannot explain `0.9790`, and the real cause is
something else that adds *pixel-scale* energy. My rival hypotheses:

- **M-noise** — misregistration decorrelates which frame wins at neighbouring
  output pixels, so neighbours carry independent noise. Independent noise is
  maximal-frequency gradient and Tenengrad counts it as detail.
- **M-seam** — abrupt switches between elected frames create genuine step
  discontinuities that are not scene content.

Both predict the null's excess sits at the **highest spatial frequencies**,
while the aligned render's real advantage sits at **mid** frequencies. That is
a testable, falsifiable split, and it names the metric that would rank
correctly.

**A caution against my own hypothesis, recorded now:** the aligned render has
*lower* `n_eff` than the null (marker head: 28.204 against 38.254), so it
averages fewer frames and should therefore be *noisier*, which pushes its
Tenengrad *up*. That runs against M-noise. If M-noise is right anyway, the
underlying effect must be larger than the raw ratio shows.

## Bars, with the failing value stated in advance

**R1 — the doubling mechanism, on synthetic data where truth is known.**
Construct a step edge; produce a doubled version (two half-steps) and a blurred
version of equal total rise. Report Tenengrad, peak `|grad|`, and integrated
`|grad|` for each.
- CONFIRMS the orchestrator if doubling raises Tenengrad above the single edge.
- **FALSIFIES it if doubling gives Tenengrad <= 0.9x the single edge.**
I predict falsification at ~0.5x. Recording the prediction so I cannot claim
the result either way afterwards.

**R2 — the doubling mechanism, on the real renders.**
Locate strong isolated edges automatically, measure profiles perpendicular to
them. Report 10-90% rise width, peak `|grad|`, integrated `|grad|`, lobe count.
- The orchestrator's mechanism requires the **null** to show wider, multi-lobed
  profiles with **higher** integrated `|grad|`.
- **FAILS if the null's integrated `|grad|` is not higher**, or if the aligned
  render does not show the narrower profile.

**R3 — stratification by scale, which is what "detail scale" means.**
Decompose both renders into octave bands and take the aligned/null energy ratio
per band.
- **PASS if the ratio crosses 1.0 between bands** — that is a metric changing
  sign with scale, and it is the finding.
- **FAIL (hypothesis dead) if every band ratio sits on the same side of 1.0**,
  because then the whole-frame number is not a scale artefact.

**R4 — the metric that ranks these two correctly.**
- **It must return > 1.00 for aligned vs zoomnull on `bee-3-cpl`.**
  **Any value <= 1.00 is a failure and I will report it as one.**
- Placebo: self against self must read `1.000 +/- 0.005`.
- Blur plant: sigma=1.0 Gaussian on one arm must read **> 1.30**.
- **Direction plant: the metric must rank a deliberately blurred aligned render
  BELOW the untouched null.** A metric that says aligned is better no matter
  what is not an instrument, it is a thumb on the scale.

**R5 — co-location, which the orchestrator flagged in their own numbers.**
Their per-crop ratios (wing-venation 0.9792, thorax-hair 0.9923, head-eye
0.9908, **leg-spines 1.1288**) came from crops placed by eyeballing a
thumbnail, and they explicitly warned that leg-spines may include different
content at its right edge. Every crop I measure must be co-location-verified,
and the verification must itself carry a plant: **a deliberately displaced crop
must be rejected**, or the check is decorative.

## The named risk

The null and the aligned render **do not have a common true feature position** —
the null is a composite of frames at different scales, so its features sit at
an average position that matches nothing. A ~12 px apparent displacement is
visible between the two panels of `crop-wing-venation.png`. This means a
profile measured at a fixed coordinate may cut a different part of the edge in
each arm. Profiles must be located **independently in each arm** and compared
by shape, not by position.

## What would make me report a negative result

If R3 fails — every band on the same side of 1.0 — then the whole-frame ratio
is not a scale artefact, my hypothesis is dead, and I will say so and go back
to the orchestrator's mechanism. If R4's direction plant fails, the metric is
discarded no matter how well it ranks the real pair.

# Next spatial counterfactual: exclude optically mixed source support

SOURCE REVIEW / ARGUED proposal, 2026-09-25. No new image-quality measurement,
RAW access, implementation or execution is reported here. The current whole
marigold/mineral comparison and highlight factorial take priority.

The single next test I recommend is an **oracle optical-support veto inside
the actual native pyramid**: retain each band's existing soft source weights,
but remove a source coefficient where its contributing rays cross an opaque
foreground/background boundary. This asks whether incompatible spatial support
is sufficient to explain an artifact on this consumer. It does not fit a new
depth map, choose one finest winner, unmix intensities or modify rendered pixels.
It is a bounded mechanism test, not an automatic algorithm or a SOTA result.

## Prior-art search and what it excludes

Read-only command run before this review:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B experiments/ORCH-drift-check/prior_art.py occlusion focus order halo visibility
```

Relevant results were read through their later corrections, not just their
opening positive claims:

| Prior result | What it actually rules out here |
| --- | --- |
| [M63, verdict](../../docs/research/M63-bimodality.md) | A second focus-curve peak is not a reliable second surface. Single-depth defocus lobes and silhouettes against blank card produce it. Do not derive visibility, a foreground label or depth order from bimodality alone. |
| [M121, verdict/E5](../../docs/research/M121-halo-polarity.md) | Legacy election spill has the old operator's support scale; opposite-polarity discrimination remained untested. Its conditional proposal is not evidence that every current native artifact is selection spill, nor that all optical models are irrelevant. |
| [BUILD-HALO, sections 17/20](../../docs/research/BUILD-HALO.md) | Adaptive/local support and edge-guided regularization lost texture. Section 20 corrects the simpler section 17 attribution: the later Acuity arm's luma guide, not radius collapse, dominated both regressions. Brightness edges are not visibility boundaries. No radius/threshold resweep is justified. |
| BUILD-HALO, sections 32/33 | The veil envelope's significance gate selected clean far background and missed the rim on coffee-bean; later coherence/support/reach amendments are a different recipe. Election coherence establishes neither missing illumination nor optical source validity. Do not port that envelope into the pyramid. |
| [M87, opening verdict and sections 29/33/34](../../docs/research/M87-occlusion.md) | Mode partition can improve an artifact score while destroying hair/detail. The far-focused source can contain the strongest foreground veil; sometimes no clean donor exists. The rejected support-starvation argument counted finite temporal observations, not uncontaminated rays. Its averaging/gate ladders also preclude treating tighter admission alone as a new mechanism. |
| [BUILD-ELECT, sections 11–15](../../docs/research/BUILD-ELECT.md) | A better texture election did not cure a band containing no sharp texture in any source. The later pyramid resolved much of that legacy problem; old rendered/tone and clipping confounds invalidate transferring its headline magnitudes to today's native output. |
| [Current source prior](../cross-scale-source-prior/results.md) | Conditioning all coarser bands on finest-source support destroys a genuine far/coarse component in a two-depth superposition. A visibility experiment must permit different bands to retain different valid mixtures. The outside bright-spill positive in this screen was unexercised, so it cannot be reused as an established occlusion positive. |
| [Known visibility](../layered-raw-inverse/visibility-results.md), [free visibility](../layered-raw-inverse/free-visibility-results.md) | Supplied coverage helped the separate inverse renderer, but free coverage still failed fixed image requirements. Neither is an automatic visibility estimator for this pyramid. Avoid another inverse-fit continuation. |

The [coupled pupil stencil](../layered-raw-inverse/pupil-stencil-results.md)
now has a bounded forward numerical commission at its fixed dense pupil on
specified generated geometry. That is reusable forward machinery, not a lens
calibration or an inverse-quality pass. The old independent-marginal blur
shortcut is explicitly unsuitable for this test.

## One intervention, with a stop condition

Use one independently specified opaque foreground edge over a textured far
surface, with a fine foreground filament. Generate a small complete RAW plant
through the already commissioned **same-ray** pupil forward, with supplied
geometry/focus settings and noise. Supply visibility to the diagnostic as an
oracle. Do not estimate it from the resulting focus energies. Reuse the actual
rounded native gather, green probe, per-band energies/floors/soft weights,
accumulators, collapse, CFA development and fixed renderer.

For source i and AC band b, form a conservative validity field Q(i,b,x).
It is one only where every ray/sample contributing to that band coefficient
belongs to the same opaque surface visible at the sharp output location.
Propagate optical mixed-support masks through the **actual coefficient filter
footprint**, including decimation phase and borders; do not merely resize the
pixel mask. A blurred point can be mixed even if its centre lies outside the
foreground silhouette. All required samples must be in bounds.

The only treatment is w'(i,b,x) = w(i,b,x) Q(i,b,x). Relative weights of valid
sources remain canonical. Different bands retain their own sources. Keep
coefficients, noise/beta, unweighted fallback sums, terminal mean, hull, geometry,
crop, exposure and tone unchanged. If every positive-weight source is excluded,
leave that coefficient canonical and report it as **no clean support**, not as
a corrected pixel. The intervention consequently tests AC-source contamination;
it cannot establish that an unchanged terminal/base component is correct.

This is deliberately an upper-bound availability test before investing in an
automatic focus-order/visibility detector. Focus order locates the known
foreground focus setting and its blur progression in this plant. Order alone
does not imply near/far identity, monotonic blur radius, visibility or correct
registration on real captures. Those would remain separate measured inputs.

## Small, falsifiable screen; no tuning ladder

Run Current, oracle Q, and one fixed source-label permutation of Q on the same
observations. The permutation preserves mask occupancies but destroys their
source association; record admitted weight mass and effective sample counts
because it does not preserve those. Literal all-one Q must reproduce Current
exactly. An independent author owns the stimulus, mask construction and scoring.

Before reading an improvement score, require the fixture to contain all three:
current reconstruction error outside the true edge, positive current weight on
optically mixed coefficients there, and at least one clean positive-weight
alternative in a nonempty part of that same region. Otherwise report
**unexercised/no clean support and stop**. Do not increase contrast, shift the
edge or sweep geometry until the wanted answer appears.

Require paired RGB/chroma truth-error improvement at the exercised edge while
protecting the near filament and the independently scored far texture. Report
coverage and the uncapped component amplitudes alongside error: RMS can reward
blur and component projection can reward excess contrast. A deliberately blurred
answer must fail the detail protection. Inspect the complete generated scene
and fixed unresampled native panels, not only a signed artifact score.

Two cheap nulls are indispensable: a single flat noisy surface (no exclusions,
literal Current identity), and the existing transparent two-depth superposition
(both surfaces genuinely contribute; no opaque-boundary exclusions permitted).
The second must retain both components, unlike the rejected shared finest-source
prior. Darkening or reduced edge contrast is not evidence of recovery.

If the oracle fails, do not build a detector, a threshold or a physics inverse
around it. If it helps only where clean coefficients exist, the next photographic
question is whether those circumstances actually occur in a **source-registered
opaque marigold edge**; it is not blanket permission for petals, transparent
minerals or a flat diagnostic slide. Any later photo intervention must produce
the complete same-stack Current/candidate masters and full views, and preserve
an independently checked flat/nonoccluding region. A residual alignment error
must not be relabelled an occlusion defect.

This is the cheapest useful new discriminator I found in the reviewed record:
it bypasses the unsolved detector and optimizer, changes one consumer input,
and can reject the entire proposed visibility-veto direction in one small run.
No claim is made that this oracle will pass or transfer to the user's images.

# Next occlusion model: bounded prior-art and design audit

Status: **ARGUED recommendation / DERIVED counterexample / source audit**.
This audit creates no input, implementation, quality result or new acceptance
bar. It was requested during M194d's fixed comparison; the proposed scene below
comes from the earlier committed forward-model plan, not its outcome. Root has
now allocated M194e separately and selected generator commissioning first.

Recommend a small **joint-pupil, two-plane geometric renderer**. Evaluate the
foreground mask and both radiances along the same pupil ray, choose the visible
surface, then integrate the pupil and sensor cell. This is more work than adding
a second `Layer` to M25, but avoids knowingly omitting the interaction this next
test is meant to express. Commission the noiseless generator before using its
outputs in the production merge. Preserve M25's existing model, failed real
optics/occlusion gates and historical bars without silently redefining them.

## Search and prior decisions

Commands run for this audit:

```text
python experiments/ORCH-drift-check/prior_art.py two layer occlusion forward model
python experiments/ORCH-drift-check/prior_art.py premultiplied alpha pupil covariance
```

The first search returned M87, M63, M79, F-camera-lens-optics, M48, M98,
M90, M72, V-BLEND and M48c, with adjacent ORCH-veiling, G-edof-deconvolution,
BUILD-SHARP, M70, BUILD-HALO and V-HEADTOHEAD2. The second returned covariance
work with mostly different consumers; a keyword hit is not supporting evidence.
Focused source/report reads and a SYNTHESIS content search supplied these
binding conclusions. No external repository source or actual captures were read.

| Prior work | What it already answers; restriction on the next experiment |
| --- | --- |
| [M25 simulator](../../docs/research/M25-simulator-measured.md), Gates 1b/1c/2 and Group D | A scalar, ordered layer renderer and premultiplied alpha tests already exist. Noise/selection agreement did not validate optics: its gate was blind to deleting diffraction. The corrected occlusion gate had wrong-sign enrichment; the original base-rate match was withdrawn after the ISO-50 gain error. Those are retained failures, not gates this numerical commission can clear. |
| [M25 actual renderer](../m25-simulator/src/strehl_sim/render.py), `_layer_terms`, `render_stack`, `ground_truth` | Scalar fixed-depth layers are sufficient APIs for a layered approximation. The depth-banded path additionally ignores within-layer self-occlusion. `ground_truth`'s nearest visible focus is a label, not a proof of an attainable error floor. |
| [M63](../../docs/research/M63-bimodality.md) | Single-depth silhouette edges can produce the same focus-curve lobes used as an occlusion cue. This refutes bimodality as evidence of two depths; it does not refute every two-layer forward model. No depth inference is needed for a scene with declared layers. |
| [M87](../../docs/research/M87-occlusion.md), §26 | The corrected conclusion explicitly reopens the two-component model: propagation and a mistaken arm-ratio gate had been blamed on the model. A flat-foreground plant could not express depth-propagation failure; depth spread had to be added. Two constant-depth layers can test a boundary, but cannot commission that separate propagation problem. |
| M87 §§26, 33–34 | A nearest-depth frame is not a trustworthy error floor near an occlusion boundary. Cosmetic suppression can improve an occlusion statistic while destroying truth. Later gate work rejects a simple “more averaging removed the veil” account and finds motion in the far-region reference. Use immutable known truth and masks, not a per-output fitted background level. |
| [V-DILUTE](../../docs/research/V-DILUTE.md) | The old deep-stack dilution argument failed because it assumed a competitor response distribution that the actual gate did not admit. Nonzero pedestal weights introduce a different potential risk; frame count alone does not establish it. |
| [BUILD-BLEND](../../docs/research/BUILD-BLEND.md), synthetic two-layer section | Its scene commissioning and oracle comparisons failed. The report disqualifies the edge rows; the [executable](../../crates/strehl-cli/examples/blend-truth.rs), `run_scene`, prints them before the warning and returns `Ok(())`. Its inference that M63 killed the two-layer model is not the later M87 §26 conclusion. Do not import its real-defect potency target as a new numerical-generator bar. |
| [M194b](../../docs/research/M194b-known-scene.md) and [its earlier plan](../review-production-truth/forward-model-plan.md) | Scalar optics, aperture/noise/quantization and the actual production seam have bounded controls. The plane is one fully opaque layer focused at frame 4; two-layer alpha was explicitly deferred. Its convergence allowance and ideal/optical target distinction are not certification of a new boundary renderer. |

SYNTHESIS already records the depth-boundary/window lesson (fact 64) and the
absence of novelty in modeling occlusion (facts 410–412). Local reconstruction
error at a boundary can worsen while a region-wide selection score improves.
Neither a new discovery claim nor a generic reconstruction metric search is
needed here.

Primary literature supports the selected approximation: Cook, Porter and
Carpenter integrate visibility over the lens area and explain why post-blurring
a pinhole visibility result loses newly visible background. They explicitly
exclude diffraction. This supports the geometric model choice, not numerical
tolerances or camera transfer. [Distributed Ray Tracing (1984), §3](https://www.cs.cmu.edu/~462/www/lectures/cook84.pdf).
The ICCP 2021 project separately describes its layered image-formation model as
an approximation compared with ray-traced reference; these models should not be
silently identified. [Depth from Defocus with Learned Optics](https://www.computationalimaging.org/publications/deepopticsdfd/).

## Why the current plane cannot answer the next question

`produce.py::build_scalar` constructs `Scene([Layer(rad, ones, 4.0, scene)])`.
It can express dilution of a single plane's texture by defocused contributors,
noise coupling and interpolation errors. It contains no visibility boundary,
no hidden background and no competition between layers with different focus
positions. Consequently it cannot express foreground defocus extending across
a background boundary while the uncovered background is sampled along those
same rays. A change in the plane score is evidence only about the first set of
effects. A second constant-depth layer is the smallest scene change that can
contain the missing boundary interaction; spatially varying depth is not needed
for this bounded question.

## The missing joint term, without a new empirical claim

Ignoring sensor integration for this derivation, M25's fixed-depth two-layer
model computes

```text
C_F = H_F * (A F),   A_F = H_F * A,   C_B = H_B * B
I_separate = C_F + (1 - A_F) C_B.
```

Here background is opaque, foreground opacity is A, and H denotes the separate
normalized layer blur. For a chosen geometric pupil model, define samples on
the same ray as A_u, F_u and B_u. The corresponding radiance is

```text
I_joint = mean_u[A_u F_u + (1 - A_u) B_u]
I_joint - I_separate = -Cov_u(A_u, B_u)
```

when the individual layer expectations agree. This is an algebraic scope
distinction, not a newly measured camera defect. Two equally weighted rays
with A=(1,0), F=(30,30), B=(10,20) give joint=25 and separate=22.5.
Reverse only B to (20,10): joint=20 while separate stays22.5. The same
individual layer means can therefore conceal either error direction. A constant
background makes this covariance zero and is a necessary null, but cannot
commission the textured-background interaction.

Premultiplication, energy conservation and convergence of M25's own formula
would not reject this omitted term. A second M25 layer is still useful as an
explicit **legacy approximation comparator**, including an expected disagreement
on the two-ray control. It must not be relabeled physical truth or modified to
erase its historical failure. Adding diffraction to separately composited layers
also does not supply the missing same-ray relation.

## Smallest proposed model and scene

Use two ordered opaque fronto-parallel surfaces with scalar analytic radiance,
one binary foreground half-plane and a complete background. For each native
sensor cell and normalized circular-pupil sample, map a ray to both surfaces,
apply foreground visibility, then integrate. Tiled evaluation requires no RGB
optical model, depth-band discretization, triangle engine or stored aligned-frame
volume. Different channel factors can be applied after scalar integration under
the existing explicitly achromatic assumption.

The author must freeze the actual ray equation. In particular, name whether
defocus displacement is in native sensor or canonical coordinates, where the
known similarity acts, and how a native unit-square cell is transformed.
Use signed layer defocus, zero at that layer's focus. A global reversal of both
signed displacements is a pupil-coordinate gauge under a symmetric pupil; it
cannot be distinguished by the rendered image. Replacing each displacement by
its absolute value is different when focus lies between the layers and can
change their joint visibility. A control must exercise that relative-sign case.

For eventual development inputs, the already written plan proposed background
focus6 with the existing two plane sinusoids; foreground focus2 with
`15000 + 1400 cos(2π(.045x+.095y)+.7) + 700 cos(2π(.17x+.01y)+.3)` electrons;
foreground mask `x >= 160 + .15(y-120)`. Retain the 320×240 native extent,
frame4 gauge and M103 curved scale track if this case is selected. These are
prospective scene choices, not a calibrated lens or current authorization to
generate a quality population. The earlier 1.5-pixel defocus-diameter rate may
be a declared geometric parameter, but is not evidence of measured optics.

The initial commission should use noiseless scalar evaluations and a small
explicit CFA fixture. Only a later approved bridge should reuse the exact
injected gain/read-noise, WB, black/white and quantization conventions. M194b's
eight repeat seeds may be retained in a later benchmark; choosing seeds from a
favorable M194d result is unnecessary and inadmissible.

## Independent commissioning that can actually reject it

Freeze exact parameters and error budgets before implementing either quadrature.
The following are choice points, not claims that any test has run:

1. **Shared visibility:** the two-ray example above must read25, its reversed
   background20, and the separate-mean destroyer22.5 in both. Test the renderer's
   actual sample/evaluate/accumulate path. A disconnected arithmetic example
   alone does not commission that path.
2. **DC and occlusion limits:** equal constant layers conserve radiance at every
   mask; absent foreground ignores even a strong hidden foreground texture;
   fully present foreground ignores the background. Swapping layer order must
   change a nonconstant overlap case. Include identity/no-op controls.
3. **Continuous pupil:** independently integrate a circular-disc segment for a
   constant foreground half-plane over constant background. Use chord integration
   or analytic segment area independently of the author's pupil nodes. A shifted
   edge and noncentral sample must reject a pupil-center-only approximation.
4. **Joint textured case:** independently integrate pupil chords split at the
   exact foreground crossing, preferably with a different coordinate basis from
   author polar sampling. Asymmetric background phase and a between-layer focus
   must reject separate means, decorrelated pupil pairing and unsigned defocus.
   Do not infer global-sign power from a symmetric pupil.
5. **Sensor cell and gauge:** exact half-plane/unit-square intersection in the
   aperture-zero case rejects point sampling. Rechoose a tilted edge, fractional
   shift, non-square extent, nonidentity similarity and all CFA parities. Check
   active coordinates independently of padded storage; do not fit output gain
   or registration to make agreement.
6. **Numerical error:** compare independent quadratures and separately refine
   pupil and cell resolution on fixed interiors and a boundary band. An edge
   deliberately displaced relative to the coarse nodes must show that a coarse
   rule can fail. Agreement of two nested midpoint grids alone can alias the
   same discontinuity. Bound worst-case as well as RMS error; keep failures and
   do not tune the scene or budget after observing them.

The constant-background and aperture-zero controls are cheap analytic limits.
They do not replace the textured shared-pupil control. Conversely, a passed
textured control does not validate diffraction, aberrations, semi-transparent
fibers, scattering, camera response, real noise covariance or capture transfer.

## References and production integration after commissioning

A pinhole geometric composite integrated over the declared sensor cell is an
**ideal latent reference**, not a finite-aperture attainable capture. There is
no single frame simultaneously focused at depths2 and6. Keep actual source
frames and any layerwise counterfactual separately named; nearest-focus labels
and an all-in-focus construction cannot silently become an error floor.

Use masks fixed in the canonical geometry, not the merge's focus map. A later
proposal can report the complete valid ROI plus signed-distance boundary strips
and foreground/background interiors, with all widths frozen first. Preserve
signed error, RMSE and local error tails against the same reference; a scalar
"occlusion suppression" statistic can reward lost detail or a moved background
level. Ordinary flat and single-plane controls must accompany any boundary
quality claim. This audit sets no new quality threshold.

The smallest implementation is an experiment-local generator plus separate
author and independent numerical controls, not a product change. A later
versioned manifest should bind the ray equation, layer order/focus/radiance and
mask definitions, pupil density, cell footprint, coordinate transforms, noise
and quantization conventions, expected-electron arrays and actual CFA hashes.
Reuse M194's prepared-source seam only through an explicitly extended strict
consumer. Do not relabel the new scene as M194b's plane or weaken its frozen
schema. Failed commissioning must withhold dependent output and return a
machine-readable refusal, rather than print disqualified scores and return
success as the historical BUILD-BLEND example does.

Relative effort: adding a second M25 `Layer` is the shortest implementation,
but leaves the known missing covariance. A joint-pupil generator adds one
shared-ray visibility operation and a bounded numerical integration problem;
the main work is the independent edge/convergence evidence. A general RGB,
wave-optical or spatially varying-depth renderer would add substantially more
uncommissioned assumptions without being necessary for this first question.
The narrow geometric model closes a software test's expressivity hole. It
does not close the project's optical or real-occlusion validation holes.

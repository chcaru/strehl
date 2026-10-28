# Independent source-only refusal: bilinear CFA edge transport

**DERIVED / NOT EXECUTED.** Reject the exact proposed one-pass common-green-flow, same-phase bilinear recipe before the generated screen or complete-image adapter. Root accepted this recommendation before execution. No Rust controls, build, RAW read, numerical experiment or candidate photograph were produced by this reviewer. This closes a bounded representational objection, not the user’s photographic-quality goal or the broader family of edge-definition methods.

## Exact proposal reviewed

The [brief](brief.md) permits a maximum0.6-native-pixel displacement. The producer proposed co-located green from bilinear G1/G2 samples, separable `[1,2,1]/4` smoothing, central gradient `g`, direction `n=g/|g|`, directional curvature `c=nᵀHn`, and a shared displacement

`d = -0.6 * amount * gate * sign(c) * n`.

The gate is `max(0,1-(4s/|g|)²) * max(0,1-(2s/|c|)²)`, with zero below either threshold. Here `s` is the square root of the larger injected green variance at guide level. It is explicitly a reference scale, not propagated merged/smoothed derivative covariance. Four native border pixels remain unchanged; amount0 bypasses exactly. Each output phase is sampled once using nonnegative bilinear weights on its own2-native-pixel lattice, at its actual physical origin. No per-color direction or cross-phase value mixing is intended.

These conventions avoid an obvious phase error and overshoot. They do not preserve genuine high-frequency structure. The concern is not a private noise estimate or a broken maximum principle: it exists for noiseless, correctly phased data with a valid strong green edge.

## Decisive counterexample

The independent review first noted the usual same-phase interpolation factor `H(ω)=(1-t)+t exp(iω)`. A0.6px axis displacement means `t=0.3`: amplitudes become0.4 at lattice Nyquist and approximately0.762 at `ω=π/2`. These are conditional operator values, not measured photographic loss or the expected displacement of a particular pixel.

The producer then supplied a stronger tangential example, whose algebra this reviewer independently checked. Let the common green guide depend only on `x+y`, with sufficient gradient/curvature to activate the gate. Its flow has the form `d=(a,a)`. In another color channel, let

`C(x,y) = L(x+y) + ε cos(k(x-y))`.

Ideal common-coordinate transport leaves the tangent cosine **exactly unchanged**, because `(x+a)-(y+a)=x-y`, even when `a` varies with `x+y`. The ramp can dominate each directional difference, so all color-edge signs agree with green.

On the same-phase lattice, set `t=a/2` and `ω=2k`. The four bilinear taps multiply the tangent cosine by

`(1-t)²+t²+2t(1-t)cos(ω) = 1-4t(1-t)sin²(ω/2)`.

This is strictly below1 for nonzero fractional transport and nonconstant tangent texture. At the vector cap `|d|=0.6`, `a=0.6/√2` and `t≈0.2121`; the factor is approximately0.3315 at Nyquist and0.6657 at `ω=π/2`. The latter has a four-sample period on either phase-lattice axis, so the objection is not confined to its Nyquist endpoint. Actual gate values may reduce displacement, but any nonzero fractional value retains the attenuation mechanism. We do not assert that a camera photograph attains these limiting values.

This isolates **interpolation-created loss** from the deliberate steepening or narrowing of the edge itself. The maximum principle allows it. Green noise gating cannot observe the independent color texture. A shared opposite-sign veto misses the example because `L` can dominate the directional differences. Adding such a veto would therefore not discharge this objection.

## Decision and limits

**ARGUED:** the proposed screen would largely remeasure this known failure while giving a green-guided operator control over real fine color structure. Flat-first, amount0 and wrong-phase/ungated foils remain sensible for another operator, but their success could not repair this counterexample. No strength/kernel sweep or new veto was commissioned. No alternative was recommended without a comparably concrete detail-preservation argument.

This is not evidence that every photograph would look worse, that all interpolation is forbidden, or that every nonlinear sharpening method is invalid. It does establish a substantial detail-loss route in this exact recipe, contrary to its purpose. The complete weevil, its ten frozen guards and the flat comparator remain unchanged. The [flat full-workflow review](../../raw-quality-2026-10-26/flat-comparator/photographic-review/independent-results.md) establishes a useful edge-clarity gap, not permission to trade away independent fine structures. Root is pursuing the retained-source reconstruction evidence instead. A future improvement still requires complete photographic outputs and full-resolution masters, not this derivation or a local sharpness score.

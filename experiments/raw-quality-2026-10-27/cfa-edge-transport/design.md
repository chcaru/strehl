# Fixed CFA edge-transport proposal: rejected before implementation

Status: DERIVED design objection; independently challenged by photo-review. No numerical run, RAW read, build, writer adapter or photographic claim. This rejects the proposed same-phase bilinear recipe, not every edge-definition operator.

## Exact proposal reviewed

Input: the four signed, black-subtracted DN collapse planes in RGGB order, spaced two native pixels apart. Physical offsets are R(0,0), G1(1,0), G2(0,1), B(1,1), relative to the even native crop origin. Original RAW storage remains untouched.

1. Construct one co-located native green guide by averaging bilinear G1 and G2 samples at each physical coordinate. Smooth it once with separable `[1,2,1]/4`.
2. Compute central native-pixel gradient `g`, its unit direction `n`, and directional curvature `c = n^T H n` from the central Hessian. Evaluate `s = sqrt(max(variance_G1, variance_G2))` from the existing injected camera model at the guide's nonnegative signal. This is an openly conservative reference scale, **not** a calibrated merged standard deviation or privately fitted covariance.
3. Where `|g| > 4s` and `|c| > 2s`, set `gate = (1-(4s/|g|)^2) * (1-(2s/|c|)^2)` and `d = -0.6 * amount * gate * sign(c) * n`, in native pixels. Else use zero displacement. One pass, `amount` in `[0,1]`, four-native-pixel border unchanged.
4. At every actual CFA site, evaluate that common physical displacement and bilinearly sample only its original phase at the displaced coordinate. No color-specific edge directions, negative interpolation coefficients or overshoot. Amount zero would bypass exactly.

The proposed sign steepens a broad monotone transition: on the dark convex flank it samples farther toward dark; on the bright concave flank it samples farther toward bright. Convex interpolation establishes a local input-range bound. Neither fact establishes preservation of genuine fine structures.

## Decisive counterexample

Consider a locally diagonal guide depending only on `x+y`, with nonzero gradient and curvature so the gate admits a displacement `d=(a,a)`. Let a real color channel contain the same broad edge plus a tangential pattern:

```text
C(x,y) = F(x+y) + epsilon*cos(k*(x-y)).
```

The continuous coordinate transport leaves the cosine exactly unchanged because `(x+a)-(y+a)=x-y`. This holds even when `a` varies with `x+y`. The broad edge can dominate each phase's directional differences, so a shared gate that merely rejects opposing color-gradient signs does not detect the fine component.

On any same-color lattice, put `t=|a|/2` and `omega=2k`. Bilinear sampling multiplies the tangential component by

```text
((1-t) + t*exp(i*omega)) * ((1-t) + t*exp(-i*omega))
  = 1 - 4*t*(1-t)*sin(omega/2)^2.
```

For every noninteger admitted displacement and nonconstant pattern this is below one. At the diagonal displacement cap, `t=0.3/sqrt(2)`. Choose `omega=pi/2`: the pattern is only0.125 cycles per native pixel along either axis (about0.177 along its normal), below the same-phase per-axis Nyquist. Its amplitude factor at that cap is `1-2*t*(1-t)`, approximately0.666. The roughly one-third loss is created by interpolation; the intended continuous edge transport preserves this component exactly. These values are algebraically derived, not an executed experiment or a claim about displacement actually occurring in the weevil.

The simpler one-axis interpolation has magnitude `sqrt(1-4*t*(1-t)*sin(omega/2)^2)` and also attenuates fine content. The diagonal example is stronger because it separates interpolation loss from any intended change in feature location. A small epsilon can remain genuine structure while the broad edge passes both noise and cross-phase directional-sign guards. An input-range bound cannot detect this loss, and absence of overshoot is not absence of false color after demosaic.

## Decision and retained boundary

Do not implement this recipe or a full-image writer adapter. Root restricted approval to a tiny pure-operator screen only if independent review found it informative; photo-review independently recommended stopping at this analytic objection. A numerical resampler test would confirm a known attenuation rather than demonstrate acceptability on the photographs. No thresholds, color gates or alternate interpolators were tuned to rescue it.

The source-supported chart blocks and weevil hairs remain useful photographic witnesses for a different appearance proposal. No current photograph was transformed or rejected by this lane. No claim of recovered resolution, PSF calibration, optical failure or universal impossibility follows.

## Read receipt

Read the allocation brief, [M189b](../../../docs/research/M189b-directional-detail.md), [V-HEADTOHEAD3 sharpening preregistration](../../V-HEADTOHEAD3/SHARPENING-PREREGISTRATION.md), the [M87 verdict](../../../docs/research/M87-occlusion.md), current writer seams and [optical audit](../optical-restoration-audit/audit.md). Root supplied prior-art searches in the brief. No external implementation source was read. M189b limits spectral-metric claims; M87 demonstrates that a better halo metric can accompany erased hairs. Neither is used as a proof of this new interpolation objection.

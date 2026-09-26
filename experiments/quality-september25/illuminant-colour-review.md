# Independent review of illuminant-aware colour development

2026-09-25. **ARGUED: a bounded colour-rendering comparison is defensible;
an existing photographic colour defect has not been proved.** This review
covers the proposed replacement formula, metadata and independent control
choices. No RAW, build or render was run. It does not claim glare reduction,
ghost removal or accurate reconstruction of the subjects' physical colours.

## Current path and the proposed replacement

`color.rs::camera_to_srgb` (137–217) already combines a daylight camera matrix
with camera-space white-balance adaptation. It inverts the row-normalized
XYZ-to-camera times sRGB-to-XYZ product. It is not simply forgetting to adapt
3000 K light. The approximation is acknowledged at 168–175: it omits
illuminant-dependent calibration and an XYZ adaptation. The earlier M85
orientation checks and `green-match-rgb/colour-path-audit.md` do not establish
a Strehl-only global cast under the newer lighting.

The author and reviewer agree on this replacement, operating on the current
already-white-balanced camera RGB `p = W c`. Let `C` be the selected
XYZ-to-camera matrix, `M` the current linear-sRGB-to-XYZ matrix, and `1` a
three-component unit vector:

```
n = inverse(W) * 1
q = inverse(C) * n
y = q.Y;  source_white = q / y
T = inverse(M) * Bradford(source_white -> D65) * inverse(C) * inverse(W) / y
output_linear_srgb = T * p
```

The inverse `W` is essential because white balance has already been applied.
This matrix **replaces** the old final matrix. Appending a source-to-D65
adaptation to the old output would adapt it twice. With the same matrix and
its implied D65 WB, the replacement reduces algebraically to the current
row-normalized transform. With another selected WB it still maps neutral to
neutral; that identity is necessary but cannot validate off-neutral colours.

Adobe specifies XYZ-to-camera as `AB * CC * CM`, reciprocal-temperature
interpolation for dual calibrations, and a camera-matrix inversion followed
by chromatic adaptation when no ForwardMatrix is available. The proposed
post-WB formula above follows by substituting the existing pipeline's input
coordinates into that model. [DNG 1.7.1, pp. 100–103](https://helpx.adobe.com/content/dam/help/en/camera-raw/digital-negative/jcr_content/root/content/flex/items/position/position-par/download_section_733958301/download-1/DNG_Spec_1_7_1_0.pdf).

The output remains D65 sRGB. The existing ICC profile's D65-to-D50 PCS mapping
belongs to its profile encoding; it is not an additional capture-WB transform.
[ICC sRGB interpretation, section B.2](https://www.color.org/chardata/rgb/sRGB.pdf).

## Metadata is a condition, not a guessed profile

`strehl_raw::Frame` exposes as-shot WB, a direct matrix and named per-illuminant
matrices. M85 records distinct A and D65 matrices on this body through the
public decoder result; that is historical evidence, not a fresh check of the
new captures. The saved complete opal cache records the selected
`decoder color_matrix[D65]`, WB bits and selected-matrix bits, but not the
second calibration. No second matrix can be invented from that cache.

The wrapper does not separately expose AnalogBalance, CameraCalibration,
ForwardMatrix or their matching signatures. ARW decoder conventions must be
resolved or explicitly restricted; a 3x3 array alone does not establish a
complete DNG colour pipeline. A direct nonzero matrix of ambiguous provenance,
missing/duplicate A or D65 entries, or incompatible calibration coordinates
must not silently become a dual-matrix transform.

The proposed explicit 3000 K coordinate comes from the user's capture setup,
not a fitted scene-neutral patch. WB supplies the selected tint. This remains
a declared observational approximation: the actual filtered light spectrum,
camera metamerism and user-selected WB are not independently characterized.

## Independent cheap controls to commission the implementation

1. D65 equivalence on neutral **and** fixed off-neutral vectors, using the
   same camera matrix and its implied D65 WB; then a live warm-illuminant case.
2. A fixed non-diagonal XYZ-to-camera plant, independently specified source
   white and coloured XYZ patches. Use a separate f64 Gauss-Jordan path and
   the standard Bradford coordinate definition as oracle. This tests matrix
   direction, WB undo, luminance normalization and real channel separation;
   it validates algebra, not Sony calibration.
3. Live transposed-matrix, omitted-WB-undo and appended-CAT mutants. Require
   actual failures, and demonstrate two different neutral-preserving maps
   disagree on colour. A neutral-only success has no colour-fidelity power.
4. Endpoint, interior and out-of-range reciprocal-temperature interpolation;
   singular/nonfinite matrices, nonpositive WB and ambiguous/missing metadata
   must exercise refusal. A uniform positive calibration-scale change must
   cancel with the white normalization.
5. Before photographic use, actual writer controls retain sensor ceilings,
   exposure, fixed resolved tone and gamut policy. Flat noise, a neutral ramp,
   coloured bright gradients and adjacent real-colour edges distinguish a
   useful colour change from amplified noise, clipping or fringes.

Bradford's numerical basis is from the primary
[ICC Technical Note 02-2003](https://www.color.org/chadtag/), not an external
RAW implementation. A synthetic transform round-trip cannot establish real
photographic accuracy. If the data and controls qualify a complete cached
comparison, its result is a visible rendering tradeoff until an independent
physical colour reference exists. More saturation alone is not acceptance.

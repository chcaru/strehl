# Native local affine remeasurement proposal

The complete-census retrieval now covers51602/51687 and17638/17878 qualified
guide focus pixels under a128-original cap. It retains1021/1080 descriptors,
57 reciprocal feature pairs and22 FIT-only ordinal-conditioned nominations.
The unfiltered actual native consumer accepts four descriptor sites; the matched
fixed-lowpass arm accepts three. Neither supplies independent heldout geometry
or a connected accepted pass graph. Lowpass therefore remains diagnostic/off.

The earlier affine diagnostic fitted extra parameters to displacement samples
already measured through a similarity-warped image patch. Its failed leave-one-
tile-out errors are preserved. That experiment does not measure what an affine
image warp would do to NCC when anisotropic deformation exists *inside* a tile.
This is a new falsifiable model hypothesis, not permission to lower thresholds.

Two primary sources motivate the distinction. Baker and Matthews describe image
alignment as optimization over an explicit image warp and distinguish parameter
updates from composing image warps; affine geometry is one of their worked
families. We do not copy implementation code. [Baker and Matthews, IJCV2004](https://www.cs.cmu.edu/afs/cs/academic/class/15869-f11/www/readings/Baker%26Matthews.pdf.1)
Morel and Yu explain why varying camera viewpoints introduce local affine
degrees of freedom beyond the rotation/scale/translation handled by SIFT. That
is motivation for testing local anisotropy, not evidence that this capture or
any particular estimator succeeds. [Morel and Yu, SIAM2009](https://scholars.ln.edu.hk/en/publications/asift-a-new-framework-for-fully-affine-invariant-image-comparison/)

Proposed scoped consumer:

- Add a mosaic-only affine patch measurer. Preserve ordinary alignment and the
  existing similarity arm. Each tile gathers a bounded moving patch through the
  current local affine matrix and delegates translation correlation to the same
  public core NCC consumer. This avoids an aligned-frame volume.
- Fit six affine parameters from the actual native tile displacements, then
  remeasure source pixels under the updated affine warp. Merely refitting saved
  old measurements is not the positive arm.
- Retain actual probes, full source/filter/interpolation footprints, peaks,
  observations, keep masks, fit residuals, linear matrices and point mappings for
  every iteration. Reject singular/folded/unsupported cases. Every attempted
  footprint stays in the correct independent spatial role in both views.
- Run forward and reverse image measurements independently. Keep the0.5-quad
  residual/reciprocal bounds, minimum tile support, eight distinct spatial FIT
  locations, heldout validation and final mesh/loop tests. Extra source trials
  at one point remain one site; disagreements exclude that site.
- Commission on known isotropic and anisotropic sampled continuous scenes,
  projective/depth-curved local surfaces, wrong sources, unrelated noise, flat
  and ambiguous periodic texture. Evaluate held-out point placement, not merely
  fitted residuals. Compare the old actual similarity consumer on identical
  pixels. Freeze source/candidate/config hashes before the real cached replay.

The full real mosaic and complete-output independent review remain required.
No feature count, fitted residual or synthetic positive is a photographic claim.

## Implemented model and first controlled measurements

The additive native_affine option defaults false. Each of up to five forward
and five independently initialized reverse iterations gathers bounded native
patches through a six-parameter affine matrix, delegates translation NCC to the
existing f32 core consumer, fits the measured tile coordinates, and records every
actual footprint. It requires at least six tiles, positive determinant and local
singular values within0.5..2.0. Final native RMS, leave-one-tile-out tile prediction
RMS, and reciprocal placement all retain the0.5-quad bound. The additional
leave-one-out guard challenges a low residual obtained merely by adding parameters.
Per-candidate receipt reservation is64KiB in this arm, versus16KiB for similarity,
with checked arithmetic and actual insufficient-budget/overflow controls.

**VERIFIED:** all31 direct geometry controls passed in
`mosaic-affine-controls-run-03`, including five new affine controls and the receipt
reservation control. The anisotropic continuous-scene plant recovers the feature
point within0.15quad and independent fractional off-grid points within0.2quad;
the same-pixel similarity consumer refuses this plant. Mild projective and curved
plants recover point placement within0.2quad, while the stronger projective foil
refuses. Flat, four unrelated originals, pure alias, wrong seeds, folded geometry,
clipped interpolation taps and train/holdout leakage refuse. These controls link
the exact current mosaic module to frozen CLI13/core libraries; they do not
assert a new whole-product build or photograph quality.

**MEASURED:** the first real cached replay `mosaic-affine-native-01` uses exactly
the prior214 candidates, native tile32 and lowpass false. It accepts seven distinct
FIT sites (five descriptor, two grid) with independent loops0.0120..0.1330quad,
compared with four descriptor FIT sites for the matched similarity arm. There
are still no accepted heldout sites and the graph refuses. Additional LOO gates
refuse ten candidates; no cutoff is lowered. Elapsed16.230s, sampled private
653025280bytes, four workers, zero RAW decodes. The first replay binary predates
the conservative receipt-reservation correction; its observed low allocation
does not establish general budget correctness.

Inspection found nine of18 heldout descriptor proposals were excluded solely
by the FIT-only coarse spatial/acquisition envelope, while eight correctly fail
role separation and one reaches native refinement. The next authorized arm keeps
independently reciprocal original-feature coordinates as untrusted native
nominations outside that coarse envelope. It borrows only a bounded linear seed
and anchors translation at the original observed feature pair. Generated grid
nominations still cannot extrapolate beyond FIT-only support. The old214-candidate
arm remains intact. Each new native receipt labels its nomination policy.

## Independent nominations, physical support and local continuation

**MEASURED:** `mosaic-affine-native-02` admits twelve native receipts from the
same 214 original nominations: ten FIT and two heldout. The matched actual
similarity consumer admits six FIT and one heldout and refuses the graph. The
affine graph becomes connected, but its mesh has **zero qualified join cells**:
heldout error is 44.455 native quads RMS, versus 42.107 for the global similarity
and 105.002 for constant translation. The fitted mesh only moves vertices by
about 1.58 quads despite large real parallax. No photograph is produced and a
connected graph is not accepted as a useful mosaic.

The two accepted heldout descriptors are only about 25 quads apart on the same
petal. Treating them as independent would be misleading. The current consumer
therefore records the union of every actually sampled original-image footprint,
including failed iterations, interpolation and filter support. Geometry admits
a deterministic nonoverlapping subset in **both** pass gauges. Alternatives
using different originals or nearby descriptors do not create independent
votes. The twelve-receipt result above predates this stricter accounting and
must not be described as twelve independent measurements.

A one-generation neighborhood experiment uses only accepted FIT affine pixel
maps to nominate new points within 512 quads. Every proposed point is remeasured
from originals, with at most four target originals and a final native search
radius of eight quads; no heldout parent or chained accepted placement is used.
The original uniform-grid arm has 272 proposals (19 heldout). Direct native
measurement accepts none. Matched coarse original-image translation nomination
accepts one FIT; preserving the parent linear map while recentering translation
also accepts one. A default-off robust affine arm accepts six FIT receipts and
no heldout. The graph still refuses. These counts are native receipts, before
the independent geometry-site filter, and are not placement or image quality.

The robust arm selects a coherent subset containing the center and at least six
of nine measured tiles. It retains every attempted observation and footprint,
including rejected tiles. Final fit RMS and actual leave-one-tile-out RMS remain
at 0.5 quad, with additional 0.5-quad center residual and center leave-one-out
prediction checks. A high-contrast occluded-corner image plant verifies the
center within 0.2 quad while the all-tile foil refuses; a mismatched center cannot
be dropped to certify the surrounding background. Flat, unrelated, alias and
wrong-seed negatives exercise the robust producing path too.

**VERIFIED:** `mosaic-affine-controls-run-08` passes 34/34 direct controls. New
controls cover actual smooth/projective FIT-neighbor continuation, a neighboring
depth discontinuity and unrelated surface, physical support independence, robust
center support, and bounded serialization of retained original-feature metadata.
These controls link current mosaic source to the recorded frozen libraries.
Only a later full-product build establishes whole-product integration.

The next bounded experiment replaces featureless uniform-grid nominations with
the already retained original-feature positions and their exact original-source
witnesses. This does not alter feature extraction or make composite focus-guide
pixels into geometry evidence. Metadata export is bounded by the existing 2,000
features/pass reservation. The original nomination arm and all refusals remain
available as causal foils. Qualified independent heldouts, useful connected
coverage, a full original-CFA output and independent full-image review are still
required.

## Retained original-feature follow-up

**VERIFIED:** the metadata export retains 1,021/1,080 original features and
preserves the preceding candidate JSON byte for byte (SHA256
`e1062a13ec1bf89cdc63190537d7ea1a2958a177637917e21348f704b6fce48b`).
`mosaic-source-witness-export-run-01` uses the frozen product15 libraries, four
workers, zero RAW decodes and 708,272,128 sampled peak private bytes. This verifies
metadata-only behavior; it does not establish matching quality.

**MEASURED:** original-feature-centered local nominations produce 512 bounded
proposals, including 20 heldout. Native refinement accepts six FIT receipts at
five locations and zero heldout. A matched fixed native-lowpass arm accepts only
one FIT receipt, so filtering remains off. A second arm anchors both endpoints
at actual retained original features within the existing 48-quad nomination
neighborhood; its 512 proposals yield three FIT receipts and zero heldout. No
acceptance threshold changes. All three graphs refuse, and the earlier full827
capture, nomination and native refusal receipts remain intact.

The original preview investigation identified marigold2/3 as the denser first
native candidate (246 reciprocal matches and 110 FIT inliers); marigold3 versus
off-center was the more difficult larger-FOV challenge. The next root-authorized
full-density preparation therefore uses all 772 captures from marigold2 (289+144
ordered segments) and marigold3 (299+40), with eight workers and a 16GiB checked
budget. The existing cache supplies marigold3; only433 originals require decoding.
This is a second real shifted/depth-varying scene candidate, not evidence that
the off-center failure has been solved. The preview heldout p90 of4.49 pixels
still fails the global screen and is only nomination evidence.

`prepare-geometry.rs` links immutable product15 alignment, focus and guide
consumers and exits after bound maps/evidence/compact guides. Its direct compact
serialization checks the actual production guide hash. It rehashes the complete
source census at the end and cannot render a photograph. Manifest, exact source
plan, command, executable/dependency identities and host-resource observations
live under `mosaic-marigold-2-3-inputs`, `mosaic-preparation-build-02` and
`mosaic-marigold-2-3-preparation-run-01`. Qualified native overlap and a complete
full-resolution rendered mosaic remain outstanding.

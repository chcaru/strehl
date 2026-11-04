# Independent aperture Layers capability review

Status: VERIFIED artifact integrity and successful aligned-layer capability on
192 supplied fabric frames (109 pass 0, 83 pass 1). This is not an aperture
improvement, ordinary-stack nonregression, resolution, or placement-truth claim.
Root released this bounded TIFF/JSON review. No RAW decoding, new engine render,
Cargo execution, or product edit occurred in this lane.

## Inputs and exact execution

Parent render, exit 0, recorded in
`outputs/multi-stack/fabric-aperture-layers-6-run/receipt.json`:

    outputs/multi-stack/candidate-6/strehl.exe session stack outputs/multi-stack/manifests/fabric-aperture-layers.json --out-dir outputs/multi-stack/fabric-aperture-layers-6 --cache outputs/multi-stack/fabric-source-cache --threads 16 --memory-limit-gib 16

Candidate build: `c149e52834fc-multi-stack-candidate6`; executable SHA256
`22204d4ebd2142b1f232b55e8f8fa5b12851484298d7a2edc9d7c058c069cc71`.
The parent receipt records 594.809 seconds, 16 workers, and concurrent control
renders. This duration is provenance, not an isolated performance benchmark.
Full identities and 192 whole-file hashes remain in `source-identities.json`;
this review did not reopen originals or independently re-decode metadata.
Pass labels/directories are Fabric f11 and Fabric f14; numerical aperture is not
persisted in this candidate's calibration JSON. Root's earlier metadata discovery
supplies those labels, but that discovery was not repeated here.

Review commands actually run, both exit 0, from the feature worktree:

    python -X faulthandler -I experiments/multi-stack-2026-10-28/challenge/review-aperture-layers.py prepare
    python -X faulthandler -I experiments/multi-stack-2026-10-28/challenge/review-aperture-layers.py finish

Python 3.12.10, NumPy 2.4.4, tifffile 2026.5.2; OMP_NUM_THREADS,
OPENBLAS_NUM_THREADS and MKL_NUM_THREADS each 1. The sequential helper imports the
already commissioned display implementation in `prepare-review.py`. Receipts,
source hashes, input hashes, settings, TIFF tags and complete readback evidence
are in `outputs/multi-stack/fabric-aperture-layers-6-review/artifact-audit.json`.

## Frozen display and viewer commission

The first command opened only layer-01 pixels. Its embedded DisplayBaseline was
frozen: black 0.0016563288, white 0.47810793, contrast 0.55, exposure gain 1.
The same soft toe, common RGB placement, gamut compression, sRGB transfer and
contrast curve, with the same ICC, were applied to both masters. No histogram,
exposure, sharpening or per-layer display fit was added. The complete independent
layer-01 display reproduced its encoded photograph exactly: 88,072,992 channel
values checked, maximum difference 0 u16. The output photographs use separate
auto-tones, so their apparent matching brightness is not the comparison used here.

I inspected the first layer's complete overview and locator, selected nine native
384x384 rectangles, and froze `roi-frozen.json` before any layer-02 pixel access.
`pre-layer-02-freeze.json` binds both that list and the display transform.
Both complete fixed-display overviews and all eighteen native crops were then
inspected with `view_image(detail=original)`. The 384px one-pixel stripes/checker,
four-pixel stripes, red center column and green/blue boundary-row commissioning
image was inspected first; PNG readback is exact. This commissions artifact/tool
pixels, not a physical monitor's calibration or arbitrary zoom. Overviews are
resized orientation views; native witnesses have no spatial resampling.

## Integrity, isolation and preserved treatment

VERIFIED by full independent TIFF decode and bitwise comparison against mapped
samples: both masters are 6636x4424 RGB32F, finite throughout, complete single-page
BT.709/D65 linear pre-tone images. Full fixed-display PNG readback also exactly
matches the transform of every master pixel. There are no all-zero RGB pixels.
Master channel ranges are -0.06559343 to 1.16127181 (layer-01), and -0.02894917 to
0.78236574 (layer-02); the declared unclipped linear master preserves out-of-gamut
and above-reference-white values. Those extrema do not establish original sensor
saturation. Every reported source gather had zero clipped pixels.

| Property | Layer-01 | Layer-02 |
| --- | --- | --- |
| Source global range, exclusive end | 0..109 | 109..192 |
| Frames and singleton groups | 109 | 83 |
| Cross-pass coefficient fusion | None | None |
| Per-source photometric gain | 1 for every source | 1 for every source |
| Invalid delivered pixels | 0 | 0 |
| White balance R,G,B | 2.9521484375, 1, 1.44921875 | 2.890625, 1, 1.4775390625 |
| ISO and shutter | 100, 1.3 s | 100, 1.3 s |
| Sensor black and white | 512, 15360 | 512, 15360 |

Exact source/frame membership, group isolation and unity gains were asserted.
Both recipes match: Catmull-Rom, seven bands, SoftPower exponent 2, gate 2,
HardFloor admission, Mean base/fallback, InputRange hull, 1.4 sharpening per octave,
no cross-pass grouping and exposure EV 0. Both use the same recorded injected
profile noise model and D65 camera matrix; original pass white balances are
preserved independently. Candidate-6 source archive selects `only_pass` as each
layer's development reference; the execution log confirms each corresponding WB.

Both use the same common canvas `[99,66,3318,2212]` in green-quad plane units,
therefore sensor-origin `[198,132]` and 6636x4424 delivered dimensions. Full input
plane is 3516x2344. They share one saved map/gauge, automatic reference pass 0,
frame 54; no preferred primary. Alignment reports all 192 frames placed in one
component, 1,467 native measured edges and 1,276 independent graph cycles.
These recorded graph counts and common coordinates are not independent geometric
accuracy measurements. Some early layer-01 coefficients lacked support, but the
final reconstruction has zero unsupported output pixels; per-source unavailable
coefficients must not be mistaken for delivered holes.

## Visual witnesses and defects

All origins below are integer top-left pixels in each delivered master, size 384.
They were selected from layer-01 alone and reused unchanged.

| Witness | x,y | Independent observation |
| --- | --- | --- |
| Upper-left boundary | 0,0 | Both contain continuous bright/dark yarn and the same loose loop; no blank boundary or canvas seam. Fine strands are soft in both. |
| Bright weave | 1000,500 | Main vertical loose fiber and crossing dark yarn remain present in both. Layer-02 is darker and its fine strands appear softer under fixed display. |
| Light/dark pattern transition | 3400,1300 | Matching broad transition and curved loose fibers; no missing pattern strip. Bright bundle detail differs with capture/render treatment. |
| Cyan weave | 1900,2100 | Cyan bundles and overlapping thin loops retained in both. Color and highlight contrast differ; this is not isolated aperture evidence. |
| Dark weave | 5000,1400 | Dark crossing and light inserts remain continuous. Fine blue filaments and bright glints are softer in layer-02. |
| Loose fibers | 2400,3300 | Several translucent/bright-edged loop contours occur in both. Their halo-like appearance is a visible limitation, not an established new Layers defect without a per-pass baseline. |
| Dark cyan crossing | 4200,3200 | Both retain crossed dark/cyan bundles and isolated fibers; no local missing tile. |
| Upper-right boundary | 6252,0 | Pattern reaches the delivered edge without a blank strip. Soft/chromatic glint edges exist in both. |
| Lower-right boundary | 6252,4040 | Bottom/right coverage complete. Fine loose contours and glint fringe remain imperfect in both. |

No obvious whole-scene holes, seams, broken pattern bands, duplicated displaced
scene, or unintended framing divergence were found in the complete overviews and
selected native witnesses. This is a bounded visual finding, not a guarantee at
every pixel. Both layers contain soft fine fibers and colored/bright glint edges.
Layer-02 is visibly darker under the fixed layer-01 transform and often softer in
these witnesses. Different aperture, 109 versus 83 focus samples, per-pass WB,
optical behavior and the common stacking recipe are confounded; no sharpness or
noise metric was used to rank them.

Two evidence limitations matter for the deliverable:

- Candidate-6 calibration JSON's generic WB-policy sentence says primary/automatic
  reference although Layers actually uses each pass. Current product source has
  already corrected this sentence and added development-reference reporting;
  the original candidate-6 receipt was preserved unchanged. Numeric aperture is
  also absent from that calibration receipt.
- The applied radial optical profile records fits at f/5.6 and f/8 and explicitly
  says f/11 untested. This run preserves that existing profile; it does not validate
  the profile at f/11 or f/14. Physical body identity is also not established by
  camera-model metadata alone.

The usable capability is two separately developed, complete linear masters and
photographs on the same delivered canvas, without mixing the passes' radiometry.
This supports choosing or externally blending their appearance. It does not
establish aperture improvement, pixel-perfect registration, physical focus
compatibility, absence of all stacking artifacts, or ordinary-path nonregression.
No additional campaign is requested by this review.

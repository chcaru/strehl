# Focus-aware mosaic architecture and evidence

Status: implementation in progress, not a completed stitched photograph. This
lane extends the original completion allocation to new core mosaic modules,
the additive mapped CFA sampler, new CLI mosaic geometry helpers and a tiled
original-CFA consumer. Existing
ordinary alignment, sampler and merge arithmetic remain unchanged. Root alone
registers modules and schedules builds/RAW work.

## Primary sources and design choice

[Agarwala et al. 2006](https://grail.cs.washington.edu/projects/multipano/agarwala_sig06.pdf)
provides the multi-perspective precedent: preserve coherent single-view regions
and place viewpoint transitions where geometry agrees. It explicitly depends on
scene structure and visibility; it is not a guarantee that a single smooth warp
can explain arbitrary 3-D objects. Our output has this multi-perspective meaning,
not metric depth or an orthographic reconstruction.

[Zaragoza et al. 2013](https://openaccess.thecvf.com/content_cvpr_2013/html/Zaragoza_As-Projective-As-Possible_Image_Stitching_2013_CVPR_paper.html)
models departures from a single projective warp using local estimation.
[Zhang and Liu 2014](https://openaccess.thecvf.com/content_cvpr_2014/html/Zhang_Parallax-tolerant_Image_Stitching_2014_CVPR_paper.html)
separates usable local seam alignment from globally perfect overlap. These
motivate a locally measured field and seam qualification; neither validates an
unmeasured depth field or permits smoothing across disocclusions.

[Burt and Adelson 1983](https://persci.mit.edu/pub_abstracts/spline83_abs.html)
describes frequency-dependent transition widths for blending. Here the same
principle must additionally retain source coverage through every filter, preserve
the full canvas's pyramid phase across tiles, and never treat missing support as
black observations. Blending is not evidence that placement is correct.

[Lowe 2004](https://www.cs.ubc.ca/~lowe/papers/ijcv04.pdf) describes oriented local
gradient descriptors and geometric verification after descriptor matching. Our
small owned matcher uses distributed corners and a normalized gradient-histogram
descriptor to nominate direct native measurements. It is not a claim to reproduce
all SIFT scale-space behavior. No prohibited implementation source was consulted.

## Geometry and consuming coordinates

Every geometry coordinate is in native green-quad units: guide integer (x,y)
represents active sensor (2x+.5,2y+.5). A signed integer canvas origin is part of
the gauge. Each CFA site's offset is evaluated *before* the spatial map; the
per-frame placement and source optical profile then pull into the original
frame about its full source centre. Subtract the site offset only on conversion
back to the same-color CFA lattice. A tile never changes this centre or gauge.

The source and output geometries are independent. `MosaicCanvas` bounds the
union with checked dimensions/pixels. `MosaicTilePlan` produces disjoint cores
and expanded work rectangles with origins and interior endpoints at the full
canvas's pyramid phase. Its caller must supply the complete dependency halo,
including reconstruction and focus operators. No full aligned-frame volume or
whole panorama working stack is allocated.

`ForwardMesh` is a triangulated regular source grid. A joint sparse least-squares
fit uses direct cross-pass correspondences, a Huber residual, a symmetric weak
displacement prior, and a focus-dependent smoothness penalty. Focus is a local
ordinal with measured width/ambiguity, never physical depth. Changing focus
across neighboring nodes weakens smoothing; it does not create a measurement.
The local deformation gauge treats all passes symmetrically. A reference used
for orientation has no appearance/fallback preference.

`BackwardMesh` checks positive Jacobians, bounded stretch and bounded index
storage. It rejects multiple inverse surfaces. Its result is one of Supported,
Uncovered, Rejected(reason), or Ambiguous. Folds, uncertain geometry and black
intensity are therefore different states. Native CFA gathers reuse the existing
exact interpolation and original-code clipping stencil, including negative taps.

## Implemented geometry and consumer pipeline

1. Align each pass independently in its own full native anchor gauge. A single
   cross-pass global similarity is not required to exist. Source IDs stay global
   and ordered segments remain one acquisition.
2. Stream a low-resolution intensity guide directly from cached original CFA,
   using the shared regularized focus evidence. Average its admissible top-four
   focus band; where shape is ambiguous, use the regularized peak only as a
   diagnostic. Record contributing original IDs, actual coverage, focus flags,
   the exact guide, map and focus hashes, and the allocation reservation. This
   guide never supplies final photograph pixels or a quality reference.
3. Nominate distributed reciprocal gradient descriptors. Fix Fit/Heldout roles
   by spatial blocks before fitting; reserve patch margins on both sides, rather
   than merely splitting feature IDs from the same patch. Fit the global seed
   from Fit sites only. Preserve all candidate refusals.
4. Group candidates by original pair to avoid repeated RAW decoding. Directly
   refine native green patches with the existing production seeded pair fitter
   in both directions. Check original clipping/support, local residual, forward/
   reverse loop closure and actual point placement. Convert accepted points back
   into the two independent pass anchor gauges.
5. Fit all pass meshes jointly using only Fit correspondences. Qualify overlap
   cells using held-out native placements and independently measured loops.
   A loop of solved poses is not evidence, because it closes by construction.
6. Construct the bounded union and select local source ownership. Unmeasured
   interiors may retain an explicitly single-view result. They must not be
   averaged with another uncertain view or reported as validated overlap. Seams
   must connect qualified overlap; where they cannot, expose an unmerged region
   or layer instead of claiming a seamless join.
7. Gather original CFA samples into spatial work tiles, perform focus admission
   and coverage-aware seam blending there, reconstruct and trim to core, and
   demosaic once. Save coverage, join confidence and contribution/visibility
   diagnostics with the complete output and source-bound geometry envelope.

Native refinement, topology assembly and the first full original-CFA tiled
consumer are implemented. The independent per-pass maps are embedded in the
full source census; nominal shutter normalization permits the known 1 s/0.8 s
flower views while measured CFA disagreement still blocks blending. The consumer
uses strict multiscale alpha, no boundary estimator, masked tone statistics and
explicit single-view/qualified-blend/unmerged diagnostics. Native photographic
validation, optimization and the desktop treatment remain unfinished. Operator
checks are not substitutes for those outcomes. The complete contract and planned
commands are in [native-campaign-plan.md](native-campaign-plan.md).

## Bounded real-input discovery

MEASURED: `preview-overlap.py` extracted 50 distinct untouched embedded JPEGs at
five focus positions per real pass (10 passes). It used OpenCV 4.13.0, NumPy 2.4.4,
Python as recorded in the receipt, four numerical threads, max-side1280, reciprocal
ratio .70, and the preregistered spatial holdout. Source paths/size/mtime and JPEG
SHA-256 are in `outputs/multi-stack/completion/mosaic-preview-01/report.json`.
No native RAW pixels were decoded. Candidate controls ran before real matches.

```powershell
python -X faulthandler experiments/multi-stack-2026-10-28/completion/mosaic/preview-overlap.py --out outputs/multi-stack/completion/mosaic-preview-01
```

The five grid directories have near-identity transforms: best held-out p90 ranges
0.03-0.14 preview pixels. This is strong shared framing, not useful expanded FOV.
Repeated-period ambiguity still requires a distinctive witness. Marigold2 versus
3 supplies 98 reciprocal matches and54 training inliers in its best individual
slice pair, but held-out p90 is7.16 preview pixels, failing the global screen.
Marigold3 versus off-centre supplies19 matches/8 inliers in the sparse scan; its
global screen fails. The ore pair supplies no qualified coarse model.

The adaptive follow-up increased focus sampling to17 positions for all five
flower/ore passes, without changing the match bars. This addresses missed focus
coincidence rather than relaxing a failure. It retained85 JPEG receipts.

```powershell
python -X faulthandler experiments/multi-stack-2026-10-28/completion/mosaic/preview-overlap.py --out outputs/multi-stack/completion/mosaic-preview-02 --quantiles 17 --families marigold peacock
```

A third bounded search pools descriptors across focus. It fits all directly
measured within-pass preview similarities jointly, then suppresses duplicate
feature locations before matching the pass feature pools. It creates no stacked
pixel image and does not chain poses. This tests a distinct failure mechanism:
individual pairs may not simultaneously expose enough focused structure.

```powershell
python -X faulthandler experiments/multi-stack-2026-10-28/completion/mosaic/preview-feature-pool.py --input outputs/multi-stack/completion/mosaic-preview-02/report.json --out outputs/multi-stack/completion/mosaic-preview-pool-01
```

MEASURED: marigold2/3 pools supply246 reciprocal matches/110 training inliers,
with global held-out p90=4.49 preview pixels. Off-centre matches remain sparse
(23 against2;36 against3) and no global screen passes. Ore pools each contain
over8300 descriptors but only3 reciprocal cross-pass matches. Within-pass pooling
placed16/17 marigold2 views and all17 views of the others; its fit p90 is1.88-2.75
preview pixels. These errors themselves prohibit using pooled coordinates as
native placement evidence.

VERIFIED visual orientation: complete matched-preview panels show common flower
structure and shifted framing, but they do not establish depth-correct native
placement. The strict descriptor searches have not established a usable ore
overlap. That is a finder failure/uncertainty, not proof that overlap is absent.
Marigold2/3 is the first native local-geometry candidate; the off-centre view
remains the desired larger-FOV challenge. Full native campaigns await root's
resource release. No physical capture distance or focus-to-depth calibration was
invented from directory names or the proposal's assumed optical constants.

## Operator verification and limits

VERIFIED by root's scheduled run: all11 new core mosaic tests pass. The broader
`mosaic` filter matched25 tests, all passing, exit0. Exact command and environment
are in `outputs/multi-stack/completion/core-mosaic-01/receipt.json`.

```powershell
cargo test --locked -p strehl-core mosaic -- --test-threads=4
```

The controls test an extended signed union (an intersection foil fails), global
tile phase and complete halo, subpixel forward/inverse coordinates, original
single-view versus explicit occlusion, fold/stretch/multiple-inverse rejection,
bounded allocations, separate held-out evidence, local measured loop failure,
symmetric joint deformation, and a focus-change plant versus constant-focus
smoothing. The plant checks the actual sparse fit but does not calibrate real
depth/parallax from its own supplied focus labels.

VERIFIED by root: all4 additive mapped-sampler controls pass. They cover a native
absolute-sensor oracle with odd active origin/signed canvas/CFA phase/negative DN,
source-centred optical pull, clipped negative interpolation taps, and explicit
visibility holes/budget refusal. The broader CLI session suite initially had11
older filesystem tests fail on redirected-TEMP AccessDenied; those failures were
not numerical failures in the new modules, and root is rerunning them with an
owned temporary directory. `cli-focus-mapped-02/receipt.json` correctly records
the overall exit101; it must not be presented as an all-suite success.

VERIFIED by root's fresh CLI build: all six geometry consumer controls pass in
`outputs/multi-stack/completion/mosaic-geometry-01/receipt.json`, exit0. The command
was `cargo test --locked -p strehl-cli --lib mosaic -- --test-threads=4 --nocapture`.
These include the actual bounded matcher, native seeded refinement and joint
topology builder, with spatial-heldout poisoning and an extended positive union.

VERIFIED by the subsequent root-scheduled `cli-expanded-02` run: all70 session
controls passed, including the five new mosaic consumer controls and the alpha
writer control. The native flat consumer uses actual original CFA, mapped gather,
known-noise probe, existing multiscale focus fusion and compositor. It requires
extended supported coverage, a positive qualified blend, invalid exterior and
whole-versus-tiled equivalence. A three-view disagreement restores one original
owner, not a previously averaged value. This run precedes the small strongest-
native-witness ordering correction; that correction has its own added control
awaiting the next root build.

MEASURED input preparation: the authorized one-worker staging command below
completed exit0. It copied34 originals (1,276,440,576 bytes) into a fresh directory,
checked the original size/mtime before and after copying, and independently
verified each destination SHA256 against the hash streamed from its original.
All hashes and original acquisition ordinals are in `plan.json`. No RAW pixels
were decoded. Continuation segments remain ordered and separate within each pass.

```powershell
python -X faulthandler experiments/multi-stack-2026-10-28/completion/mosaic/stage-native-pilot.py --out outputs/multi-stack/completion/mosaic-native-pilot-inputs --materialize
```

The 17 selected originals per view already include the three preview-nominated
focus neighborhoods (center84/off91, center106/off122, center190/off244). Their
source-ID order must not select a weaker witness merely because it has a lower
ordinal: the guide's accepted contributor IDs now retain their strongest-first
focus rank, without changing its averaged diagnostic pixels. Missing/clipped
rank-zero contributors are not invented back into the receipt.

SOURCE REVIEW CORRECTION: switching between a qualified fitted mesh and the
original global map can create a discontinuity where their pulls differ.
Interior positive-Jacobian checks do not certify that selection boundary. Root
approved retaining one continuous positive fitted map across ValidatedOverlap
and SingleView cells. The latter are explicitly regularized extrapolation, not
new heldout geometry certificates. Failed local cells stay alpha-invalid through
the complete operator footprint; there is no abrupt original-map substitution.
The original global meshes remain bound comparison arms. A new control crosses
a four-quad fitted/global discrepancy, requires continuity across qualification
status, exposes the former hard-switch foil and requires failed-cell rejection.
This correction awaits the next scheduled test/build and native image review.

SOURCE IMPLEMENTED, awaiting the next root verification: the resource planner
now tries a whole-canvas core before smaller powers-of-two cores. Canonical
full-canvas noise probes run once per placed original in at most four bounded
jobs before output allocation, with gains reused across tiles. This removes a
specific confound: work-tile-dependent probe averages could otherwise change
focus weights during a small/large-core performance comparison. Added controls
require exact scalar/parallel beta and count equality, insufficient-memory and
noncanonical-domain refusal, and whole/smaller-core budget decisions. Actual
performance A/B measurements and non-flat full-output equivalence are still due.

The final CFA master is now explicitly streamed from the merged native planes
as signed RGGB Gray32Float, with a site-order/metadata control. The earlier normal
writer retains RGB master only; this new output therefore makes the intended
sensor-master contract concrete rather than relying on a legacy path that the
session did not invoke. Completion hashes bind the final photograph, RGB/CFA
masters, demosaic-eroded coverage, owner and join-status files. These new output
changes also await the next root-scheduled tests and real output inspection.

No current result certifies a complete useful stitched photograph, local seam
quality, calibrated depth or production performance. Next acceptance must use
the actual native consumer, held-out spatial/depth placements, flat/occluded/
wrong-period controls, constant-shift and stack-then-stitch foils, complete union
outputs with identical display, native witnesses and independent review.

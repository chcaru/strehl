# M193c private prototype — independent source review

2026-09-07. SOURCE REVIEW ONLY. No include hook, build, helper execution,
synthetic image generation, TIFF read, RAW byte read or decode was performed.
The reviewed files remain unchanged:

| File | Bytes | SHA256 |
| --- | ---: | --- |
| private-protocol.md | 20628 | 3de289d62dd1469ec5021b30ec30a26749727bbdd830cdeac13b3d14846058d3 |
| private-adapter.rs | 23732 | 5576bec563753e7a5c420cd1f1bb8d46690a71ff03bc636189c99065ab4f6b77 |

Disposition: **scoped acceptance of the unexecuted prototype**, with the
precision instrument, parent execution boundary and independent reader still
uncommissioned. I found no demonstrated coordinate implementation defect in
the reviewed source. This is not PASS_GRID_ADAPTER_PRIVATE_ONLY and is not
evidence about registration, RAW development, image quality or common-TIFF
qualification. The two wording distinctions below should enter the prospective
reader/release interpretation; they do not require changing product behavior.

## Concrete distinctions before release

1. Protocol lines 33–34 say there is no noise draw. The **source plant** has no
   stochastic noise, but the actual enabled production floor probe does draw
   deterministic Gaussian probe noise. `gatefloor::Probe::run` clones the
   template, fills it through `fill_probe_noise` / `fill_noise`, and warps it.
   The local frame index seeds SplitMix64/Box–Muller. Preserve this production
   path and describe the source as noiseless, with the existing deterministic
   floor probe enabled. Source decode counts do not count every probe buffer,
   warp call or allocation.
2. The G1/G2 null statement at protocol line 300 needs its scope. Merely
   exchanging the identical **field labels** in source generation is null.
   Exchanging the spatial G1/G2 planes at interleave is generally not null:
   the green field varies with native y, so `(x+1,y)` and `(x,y+1)` carry
   different values. A future parity destroyer must name which operation it
   changes; field-label equality cannot establish spatial-swap immunity.

## Re-chosen coordinate and association checks

I traced the actual consumer rather than treating plan strings as geometry.
The relevant project-owned source paths are:

- [prototype](private-adapter.rs): `prepare`, `map`, `Source::decode`,
  `make_plan`, the ignored child and environment validation;
- [alignment preparation](../../crates/strehl-cli/src/align_cmd.rs):
  `cover_or_explain`, `cover_scale`, `fit_to_cover`, `cover_rect`;
- [merge consumer](../../crates/strehl-cli/src/merge_cmd.rs):
  `pyramid_domain`, full-resolution warp, `load_frame`, `extract_planes`,
  `BandWorker::fold`, `run_pyramid_prepared`, `write_merged`;
- [similarity and sampler](../../crates/strehl-core/src/align.rs):
  `Similarity::apply_at`, `invert`, `then`, `Resampler::sample_checked`,
  `sample_catmull_rom`;
- [MHC](../../crates/strehl-core/src/demosaic.rs),
  [final reconstruction](../../crates/strehl-core/src/pyramid.rs), and
  [floor probe](../../crates/strehl-cli/src/merge_cmd/gatefloor.rs).

**Centres and direction.** The native pull is
`F_i(z)=C+A_i(z-C)+2*b_i`, with `C=(160,120)`. The real full-resolution
gather evaluates the quad transform at each CFA site's half-coordinate and
doubles the result. It therefore consumes this native pull including the
site's R/G1/G2/B offset. It does not use `(159.5,119.5)`, nor one shared
coordinate for an entire quad. The source implements `H_i=F_i^-1` by its own
explicit matrix formula, without calling the production inverse. Correct
source plus correct pull gives `H_i(F_i(U))=U`.

**Cover and nonidentity.** Crop retains the fitted pulls and uses
`U(z)=z+2*crop_origin`. Scale composes the centred cover map before each
input pull, giving `U(z)=C+k*(z-C)`. The product's `then` order matches that
composition. Identity still crops because the production support margin is
nonzero. The stated unequal crop predictions are compatible with the actual
inclusive quad rectangle formulas. The independent reader must derive all
four corners for all nine transforms, including the imaginary coefficients,
and compare the actual rectangle and k. Simply repeating the prototype's
expected rectangle is not verification. The required zero-origin, exchanged
crop-axis, native/quad and scale faults address distinct choices.

**Reference identity.** Full-track cover is fixed before subset selection or
fault injection. A one-frame case has local reference 0 and external canonical
private reference 4; `WarpMap` permits a nonidentity pull in that external
gauge. Local reference 0 must not be misreported as the real original frame 0,
the private canonical frame 4, or the future real canonical original 52.

**Frame swap.** The source still generates original 1 when its consumed pull
is replaced by original 7. Thus the correct fault prediction is
`H_1(F_7(U))`, while the inverse fault predicts `H_1(H_1(U))`.
At the native centre the swapped case has the independent displacement
`inv(A_1)*(6,-4)` from the translation difference. The reader must evaluate
the actual fixed sites, not promote this centre calculation to a measurement.
Endpoints 0/8 and canonical frame 4 are unchanged by these faults, so an
endpoint-only check is intentionally inadequate. The one-frame final hull is
a point, avoiding a nine-frame average that might cancel a swap. The restored
case and file identity requirement make this an intervention with a null.

**What the 0.1 bar means.** R at `(x,y)` supplies the x coordinate and G1 at
`(x+1,y)` supplies the y coordinate. These are two different measured CFA
centres. Retain the protocol's paired two-site coordinate-error norm and both
component errors. Do not rename it a Euclidean displacement measured at one
pixel, full-image registration accuracy, or an alignment solver's error.
The fixed 32 pairs are the entire coordinate population; the complete TIFF
is still parsed and hashed, but not every pixel has a coordinate oracle.

## Colour, precision and support

The fixed source has a rank-two chromatic coordinate field. Unity source and
writer WB, CameraLinear, zero exposure, no matrix conversion, no restoration,
photometric Off, disabled defect/CA and MHC are consistent with the inherited
options and environment. The normal production band's sharpen parameter is
still 1.4; this is not a claim that all band operations are identity. What
bounds the measured final samples is the **level-zero InputRange clamp after
collapse**. That actual final clamp, rather than assumed convexity of every
band operation, connects input sample error to the final output.

The source-only positivity argument is conservative for the literal
transforms, and the actual source checks every generated CFA sample before
and after rounding. These runtime checks are still unexecuted. The strict
reader must reconstruct the complete active source and its u16 hash, and
check the independent bounds. This source has full active storage, zero
origin and stride equal to width; it does not exercise padding or odd active
origin. Those are separate derivative instrumentation concerns.

Measured R/G1 sites survive final MHC as their own samples. Interpolated RGB
components have a further stencil and remain separately reported diagnostics.
The source-quantization, dyadic MHC and exact Catmull L1 reasoning is useful,
but protocol lines 251–264 correctly acknowledge that the loose arithmetic
argument does not prove the proposed 0.125 DN f32 reserve. It must not be
treated as commissioned by this review.

The next independent reader work must evaluate a nonidentity source → MHC →
Catmull oracle, with explicit f64 and f32 arithmetic, support and rounding.
If it claims the actual pre-remosaic f32 reserve specifically, it must also
bind actual product kernel observations or provide a sufficient arithmetic
bound: a final TIFF alone includes remosaic and output quantization and
cannot isolate a sub-rounding gather error. All sampled supports, including
the bad-map cases, must avoid both sampler boundary clamping and MHC reflected
edges. No border exception, clipped sample or inaccessible site may disappear
from the denominator. The existing 2.75 DN and paired 0.1 native-pixel gates
stay fixed; failed precision commissioning is a retained refusal.

The constant field is a value-preservation companion that must fail coordinate
inversion's rank test. It does not corroborate two-axis recovery. The noiseless
affine source validates coordinate consumption, not physical gain/read-noise
calibration, denoising, detail preservation or complementary-focus alignment.

## Lifetime, evidence and remaining execution boundaries

The source returns one owned u16 frame, records its actual generation pull
and bytes, and refuses a second decode of a local frame. It does not retain an
aligned stack. The current production loop reuses one frameworker, while the
floor probe clones a template and the full-resolution warp owns channel and
scratch arrays. Peak accounting must include those overlapping allocations;
the source's one-decode witness is not a process-memory proof. This is Rust
owned storage and does not use a rawpy view or a RAW decoder.

The child recomputes and compares the exact bounded plan bytes during render,
binds compiled protocol/adapter bytes and executable identity, validates the
allowed environment, and retains original and secondary source/receipt errors.
Fresh-process environment isolation is needed for cached product switches.
Its successful status is appropriately `COMPLETE_RGB_UNVERIFIED`.

The proposed parent still has substantive work: bind all relevant product
sources and actual compile/list artifact; require all ten plans before the
first render; freeze literal order and fresh paths; enforce live child logs,
deadlines and aggregate CPU/wall/output accounting through final persistence;
recheck sources, inputs, executable, plans and outputs; preserve refusals and
late-publication failures. The child checks its own case, not the complete
ten-case population, and its elapsed field is not an aggregate time gate.
These are explicit remaining prerequisites, not passes supplied by this
source review.

The independent reader is to be frozen and commissioned before consuming the
ten output population as evidence. Its complete-entry rehashed payload and
metadata destroyers must hit the stated semantic or numerical boundary,
with valid/restored companions. Parent authorization now covers preparing
that new reader and its preregistration only; no such execution occurred in
this review. Ten geometry renders plus the separately proposed two derivative
renders remain within the charter's twelve-render allocation.

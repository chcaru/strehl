# M193c private output-grid protocol — proposed, unexecuted

2026-09-07. Source preparation following the accepted charter. This document
fixes ten small synthetic renders and their consuming coordinate checks before
any include hook, build, decode or render. It does not release execution or the
nine real development inputs. The new `private-adapter.rs` is an unhooked
prototype. Root must review the source and the independent reader, freeze their
bytes, and issue exact commands before execution. No held M194g file changes.

## Consumer and include seam

The proposed future hook is a **nested** test module in
`crates/strehl-cli/src/merge_cmd/production-truth.rs`:

```rust
mod m193c_output_grid {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/m193c-output-grid/private-adapter.rs"));
}
```

The intended test name is therefore
`merge_cmd::production_truth::m193c_output_grid::m193c_private_output_case`.
This differs from M194g's sibling `known_scene_benchmark` namespace. Confirm
the actual compiled `--list`; a guessed name is never an execution receipt.
No hook is included in this deliverable.

Reuse parent `fixture_options` only for the complete option structure. Supply
explicit sensor/noise/geometry, then call the existing `run_pyramid_prepared`.
That body calls the shipped full-resolution gather, early Crop, band merge,
InputRange reconstruction clamp and CameraLinear writer. Do not use parent's
`run_fixture_from`, which derives noise from a camera profile. The injected
source generates one CFA buffer on each decode request; no stored aligned
stack, alternative merge, RAW decoder or image-loading helper. The generated
source plant is noiseless. The actual enabled gate-floor path separately
clones/probes its source with deterministic Gaussian noise; this is part of
the shipped operator and must remain in the invocation/resource accounting.

This is a synthetic coordinate instrument. An affine scene cannot assess
occlusion/detail quality, complementary-focus matching, or the benefit of an
adaptive merge. The one-frame association witness authenticates which frame's
pull was consumed. The nine-frame population additionally exercises the actual
fold and its output bound, without claiming a swap must survive averaging.

## Literal sensor, fields and curved track

Active and allocated storage are both320x240, stride320, origin(0,0), RGGB:
R=(0,0), G1=(1,0), G2=(0,1), B=(1,1) inside each2x2 quad. Native pixel centres
have integer coordinates; quad geometry is160x120. Black512, white15360,
range14848 DN; source and prepared writer WB are exactly(1,1,1). No colour
matrix, transfer curve, exposure, photometric fit, defect repair, CA correction,
restoration, confidence output or display operation. Inject all four planes
with gain0.25 DN/e and read noise4e, ISO160, `NoiseProvenance::Fallback`, labelled
synthetic operator coefficients, never calibrated camera evidence.

Canonical black-subtracted fields, in native-pixel coordinates `(x,y)`, are

```
R = 1100 + 40*x
G = 1700 + 40*y                 # both green CFA phases
B = 2100 + 12*x + 8*y
constant null: R=1800, G=2300, B=2900
```

The R/G coordinate Jacobian is diag(40,40), rank two. B supplies a differently
oriented/chromatic check but does not set the geometric acceptance tolerance.
The constant null cannot recover coordinates and must be refused by a rank
test; it remains a valid test of constant preservation and of an inert warp.

The following is the **entire** private track. `s` literals are retained from
`experiments/M103-halfdrift/data/truth-dense.json`, SHA256
`45b12d8c7106fa1c9c1ce3d5f663896a43992ff35f867fd3c6374131cb67be01`.
No RAW was read to obtain them. Set `a_re = s / 0.9468599999999999` using
binary64; `a_im` below is the imaginary matrix coefficient, **not an angle**.
The small signed rotations and translations are separately planted values.
This borrows measured curvature as a stress shape, not measured truth of the
coffee-bean development stack or a camera model.

| Original private index | Retained M103 rung | s | a_im | b_x quad | b_y quad |
|---:|---:|---:|---:|---:|---:|
|0|0|0.9999999999999998|0|-2|1|
|1|40|0.9856299999999998|1/128|-1.5|1|
|2|80|0.9726649999999999|0|-1|0.5|
|3|112|0.9642499999999998|-1/256|-0.5|0.25|
|4|144|0.9468599999999999|0|0|0|
|5|184|0.9285849999999999|1/256|0.5|-0.25|
|6|224|0.9090699999999999|0|1|-0.5|
|7|264|0.8795899999999999|-1/128|1.5|-1|
|8|298|0.85714|0|2|-1.5|

Private gauge is the canonical grid of original private4, whose transform is
identity. This is separate from real input original52/local4. The selected
one-frame cases have local reference0, original identity1, probe seed index0,
and the same external canonical gauge4. The probe's local seed is recorded;
it is not passed off as the original identity. Every nine-frame row preserves
local0..8 to original0..8 association, unless the named map-only fault applies.

With `A=[[a_re,-a_im],[a_im,a_re]]`, `C=(160,120)`, the stored placement pulls
canonical native coordinates into source coordinates:

```
F_i(z) = C + A_i*(z-C) + 2*b_i       # canonical/output-reference -> source
H_i(v) = C + inv(A_i)*(v-C-2*b_i)    # source -> canonical, source plant only
```

Generate each source CFA site by evaluating its channel at `H_i((x,y))`, then
`round(512 + value)` to u16 (positive half-up Rust `round`). No clamp is allowed:
finite positive black-subtracted values and the rounded value strictly between
black and white must hold over **every generated active site**, or refuse the
whole case. The identity population uses all nine `F_i=I` in both source and
placement; the constant population uses the curved track with constant fields.

The source expression must not call the production inverse/apply routine.
Use the explicit2x2 inverse with determinant `a_re^2+a_im^2`; the independent
reader will separately reconstruct the source law from these literals, not
accept either an embedded expected-coordinate table or the adapter's map as
its mathematical authority.

Full-active positivity is DERIVED as follows. Every `a_re>.9`,
`abs(a_im)<=1/128`, `abs(2*b_x)<=4`, `abs(2*b_y)<=3`. Thus inverse-centred
coordinate magnitudes are bounded by
`|H_x-160| <= 164/.9 + (123/128)/(.9^2) <183.409`,
`|H_y-120| <= 123/.9 + (164/128)/(.9^2) <138.249`.
Consequently R is within(163.64,14836.36), G within(970.04,12029.96),
and B within(1673.10,8290.90), all below14848 DN before rounding. These are
deliberately conservative whole-active bounds. The future actual source guard
must still execute; a failure is retained, not repaired by clipping.

## Exact CFA, cover and output coordinates

`align_cmd.rs::warp_frame_in_place_fullres` samples at
`2*t.apply_at(px+dx/2, py+dy/2, gw/2, gh/2)`. With
`z=(2*px+dx,2*py+dy)` this is precisely `F_i(z)` above. It is not `2*t(px,py)`
shared by all phases. There is no universal extra half-pixel translation, and
the centre is native `(160,120)`, not`(159.5,119.5)`. Do not invert the stored
placement again at gather.

Run actual `cover_or_explain` on the complete nine-frame track **before**
selecting a source subset. This freezes the same cover footprint for the three
association witnesses. Crop leaves pulls unchanged. Scale consumes the actual
returned fitted pulls, which compose the centred scale before each original
pull. The fit and the selected map passed in `PreparedPyramid` must be the same
ones recorded in the plan; recomputing a descriptive map after render is not
authentication.

The source-only corner inequalities predict for the curved track a limiting
upper-y corner of original0:
`k = 55/(59*a_re[0])` (then the actual60-step binary64 cover bisection).
The independently required integer Crop is `(x=10,y=8,width=140,height=105)`
quad, hence280x210 TIFF and native offset(20,16). Identity's limiting upper-y
corner gives`k=56/59`, Crop`(5,4,150,113)`, TIFF300x226 and offset(10,8).
These are DERIVED predictions, not run results. Actual preparations must
produce these rectangles; any disagreement halts for review rather than
silently changing the literal oracle. An independent reader must derive all
corner inequalities, including rotations, instead of trusting the predicted
limiting frame alone.

For output-native TIFF coordinate`z`, the expected canonical map is

```
Crop:  U(z) = z + (2*crop.x, 2*crop.y)
Scale: U(z) = C + k*(z-C)              # output remains320x240
```

All map faults below are applied to selected placements **after** the correct
full-track cover has been frozen. They do not change source generation, the
declared correct gauge, the output crop or the other eight track entries.
Record both the correct plan and the actual faulty map explicitly. This is a
controlled bad placement, not a claim that a bad map passed a real solver.

## Ten renders; all ten plans precede pixels

| Ordinal/case ID | Source field/track | Selected original indices | Cover | Actual map intervention | Observer |
|---:|---|---|---|---|---|
|00 identity-nine|affine/identity|0..8|Crop|none|off|
|01 curved-nine-off|affine/curved|0..8|Crop|none|off|
|02 curved-nine-count|affine/curved|0..8|Crop|none|count|
|03 curved-nine-placebo|affine/curved|0..8|Crop|none|placebo|
|04 curved-nine-scale|affine/curved|0..8|Scale|none|off|
|05 original-one-correct|affine/curved|1|Crop|none|off|
|06 original-one-swapped|affine/curved|1|Crop|swap complete original1/7 map associations|off|
|07 original-one-restored|affine/curved|1|Crop|restore original1/7 map associations|off|
|08 original-one-inverse|affine/curved|1|Crop|invert selected stored pull before gather|off|
|09 constant-nine-null|constant/curved|0..8|Crop|none|off|

The swapped full-track endpoints0 and8 and anchor4 are bit-identical to the
correct track. Nevertheless the selected original1 source is still generated
with`H_1`, while gather uses`F_7`: the actual scalar coordinate is
`H_1(F_7(U(z)))`. At canonical centre C, its displacement is
`inv(A_1)*(6,-4)`, over6 native pixels; it is not an endpoint difference.
The fixed tested sites below include a centre-near pair, so the independent
algebraic oracle must show a displacement>1 pixel before any actual image is
credited as a powered swap control. Averaging all nine affines could cancel
such association errors; the one-frame population deliberately excludes that
cancellation. An inverse pull similarly predicts`H_1(H_1(U(z)))`, notU.

Optional observer is the existing test-source pattern: off skips it, count
increments per-frame counters, placebo reaches the same hook without the
increment. Mandatory lineage records decode attempts and source CFA hashes
separately in all modes. Every selected source must be requested exactly once;
count sees nine hooks/nine unit counters, placebo sees nine hooks/zero optional
counters, off sees zero hooks/zero optional counters. Require exact TIFF bytes
for01/02/03 and05/07, not only pixel equality. These are observer and restored
companions, not independent quality populations.

## Independent pixel oracle and precision

Freeze an independent TIFF reader before the ten outputs. For every affine
case read the32 literal paired sites formed by
`x in [40,68,96,124,152,180,208,236]` and
`y in [36,68,100,132]`. R is read at TIFF`(x,y)`, G1 at TIFF`(x+1,y)`.
The original native parity includes the even Crop offset, so both really are
measured sites of the final mosaic. They are **different actual centres**:
compare`(R-1100)/40` to`U(x,y).x`, and`(G-1700)/40` to`U(x+1,y).y`.
For a fault-consistent diagnostic replaceU independently by the composition
above at each of those two centres, not by colocated RGB. Normalization is
`TIFF_code * 14848/65535`, with no second black subtraction or WB multiplier.

Retain all96 RGB components at the32 R sites and32 G1 values. Only the measured
R/G1 values carry the geometric bar. Report B/interpolated component errors
separately; they incur a second MHC stencil and are not silently given this
tighter bound. Actual whole-TIFF tags/profile/extent/hash/finite sample checks
remain required, independent of the sampled coordinate metric.

For each tested pair require finite, positive, unclipped output and per-axis
DN error<=2.75. Require the paired coordinate-error norm<=0.1 native pixel at
every pair, and report max/RMS with gauge, not only a mean. The fixed bound
implies`sqrt(2)*2.75/40 <.0973` pixel. Bad actual map cases06/08 must FAIL the
correctU bar, while PASSING their separately predicted faulty-map pixel oracle;
any exception, clipping, absent output or failure to fit either model is not
the requested scalar-power evidence. Require at least one pair>1 native pixel
from correctU in each fault.05/07 must pass and be byte-identical. Retain any
inert or inaccurate fixture, with no post-run slope/ROI/tolerance changes.

The precision allowance is prospective and must be commissioned. Its
source-only derivation is:

1. Source quantization contributes at most0.5 DN, plus a named1e-8 DN
   engineering reserve for binary64 inverse/field evaluation. The full-active
   bounds ensure neither source rounding nor input storage clips.
2. In the fixed interior support, MHC reproduces each affine channel exactly
   before quantization. Its maximum absolute stencil sum is20/8=2.5; measured
   sites have norm1 and interpolated green has norm2. WB1 and dyadic MHC taps
   acting on these integer DN values are exactly representable in f32: every
   intermediate is a multiple of1/2 with magnitude below2^19, and the final
   division by8 is exact. Therefore quantization contributes at most1.25 DN
   to an interior MHC channel.
3. Exact Catmull weights have one-dimensional absolute sum
   `1+t*(1-t)<=5/4`; the2-D sum is<=25/16. The propagated source error is
   therefore<=1.953125 DN. Add0.5 DN for the actual black-restored u16
   remosaic rounding. Stencil support for every tested point and every actual
   map must be checked independently; border reflection invalidates the affine
   argument and cannot be counted as a passing site.
4. Reserve0.125 DN for the f32 Catmull computation, coordinate fraction cast,
   and adding the black pedestal. A source-operation bound motivating it uses
   unit roundoff`u=2^-24`, two fraction casts, two `(t*t,t*t*t)` pairs and the
   displayed four cubic polynomials. For an already roundedt, conservative
   per-weight absolute errors sum to<48u per axis; for the fraction cast,
   `sum(abs(w'))<=4` and`abs(delta_t)<=2^-25` add2u, giving50u per axis.
   With intermediate source-channel magnitude<16384 and exact tensor L1
   <=25/16, factor perturbation is<0.12208 DN. This alone leaves insufficient
   room for all multiply/add error if used at that loose bound. Thus0.125 DN
   is **an engineering allowance, not a proven universal rounding bound**.
   Before any precision claim, the independent consumer must either tighten
   this arithmetic accounting for the literal support or directly bound the
   actual f32 result against an independently evaluated nonidentity
   MHC/Catmull oracle. Passing a descriptor formula alone cannot commission it.
   No extra renders are needed: use the actual ten TIFFs and literal source
   formula, with a separate private kernel instrument if preregistered later.
5. The actual `BandMerge::finish` applies the level-zero pixelwise clamp
   `p.clamp(lo[c][j],hi[c][j])` after full collapse for InputRange. For correct
   maps each gathered input lies in the same bounded interval around its
   canonical affine value, so the reconstructed output does too. A one-frame
   hull is a point. This is not an inference from per-band convexity. A future
   consumer must bind that exact configuration/source and exercise a live
   hull guard; a band-only bound would not justify this argument.
   The actual input association is also explicit: `load_frame` calls the
   full-resolution warp first, then `extract_planes` with the unchanged full
   geometry and compact domain, and `BandWorker::fold` supplies those four
   planes to `add_frame_with_gain`. `pyramid.rs` accumulates the hull from
   these original supplied values before decomposition. Final writing
   interleaves each compact plane back onto its own CFA phase. Thus the bound
   addresses the post-gather R/G1 values read by this oracle, not a full-buffer
   statistic, green mean, pre-warp image or unrelated band coefficient.
6. At the two measured writer sites, final MHC returns the corresponding
   input sample. Integer black subtraction is exact. WB/exposure1 multiply
   exactly; range division and final65535 scaling introduce<0.004 DN here.
   The output half-code is14848/(2*65535)<0.113283 DN. Combined with the
   engineering gather reserve, total<2.6965 DN, leaving>0.0535 DN under2.75.

The end-to-end independent fixed0.1 bar remains decisive. If the declared
reserve cannot be commissioned, report an uncommissioned precision instrument
and fix the instrument prospectively; do not loosen the existing geometry bar.

Before comparing intended outputs, commission the **actual reader entry** on
valid/restored companions and deliberately rehashed TIFF/metadata faults:
missing/duplicate output, changed pixel at a tested measured site, R/B swap,
transposed output-axis map, zero Crop origin, exchanged(20,16) crop axes,
native/quad factor omission, wrong scalek, stale/wrong frame association and
input ordering. For map faults use coherent hashes/metadata and valid payload,
so simple hash refusal is not called coordinate-oracle power. Require exact
intended refusal boundary. Constant/rank-one fields must refuse coordinate
inversion; a label-only G1/G2 rename is explicitly not a parity destroyer here.
A spatial interchange of the green planes can move their different native
centres and is not generally inert for the y-dependent green field.
Wrong `(w-1)/2` centre can cause a displacement below0.1 for this track; it is
a source/schema convention check, not a promised powered pixel destroyer.

## Plan, receipt, commands and bounded release

The prototype exposes one ignored test, one case per process, with exact
environment keys `STREHL_M193C_GRID_MODE=plan|render`, `..._CASE`, `..._PLAN`,
and render-only`..._PLAN_SHA256`, `..._OUTPUT`, `..._RECEIPT`. Require absolute
fresh file paths with existing parents, except the render's existing pinned
plan. Parent clears all otherSTREHL variables and sets
`STREHL_DEFECT=off`, `STREHL_FIX_CA=off`, `STREHL_FULLRES_GATHER=1`,
`STREHL_PYRAMID_WORKERS=2`, `RAYON_NUM_THREADS=2`. MHC, gate-floor defaults,
InputRange/HardFloor/SoftPower/base-mean/fallback-mean and mean_coarse0 are
explicitly checked. Fix three Laplacian bands, gate2, exponent2,
sharpen_per_octave1.4. No test-source env option may modify a numeric fixture.

Plan schema`m193c-private-grid-plan-v1` binds case ordinal/settings, all nine
literal source pulls, post-cover and post-fault selected pulls, source/local/
probe identities, full/domain/output geometry, Crop/Scalek, field coefficients,
sensor/noise/config, actual executable hash/size and actual allowed environment.
Its status is`PLAN_ONLY`. Planning does not generate CFA or pixels. During
render the adapter reconstructs the same plan and compares it to the same
bounded bytes it hashes. Receipt schema`m193c-private-grid-receipt-v1` embeds
that actual plan and hash, actual source decode/hash records and observer
counters, actual output file hash/size, runtime and source attempt outcome.
Success is`COMPLETE_RGB_UNVERIFIED`, never coordinate or quality PASS. Failure
receipts retain the original error and any separately named persistence error;
the parent independently observes exit/log/deadline and preserves partial files.

Root will bind every product/include source, protocol/adapter, selected M103
JSON, executable/compiler-artifact/list, parent launcher and independent reader
before execution. Standalone prototype compilation is not proposed: its
private imports require the reviewed nested hook. Planned commands after that
separate source release are, with fresh unique target/output paths:

```
cargo test -p strehl-cli --no-run --message-format=json-render-diagnostics --target-dir target/m193c-output-grid
<exact copied compiler-artifact exe> --list
<exact copied exe> --exact merge_cmd::production_truth::m193c_output_grid::m193c_private_output_case --ignored --test-threads=1 --nocapture
```

The third argv is invoked first ten times in plan mode, then ten times in the
literal render order. `Compiling` proof and actual listed name are mandatory.
No command above has run. The parent launcher must cap each child at240 wall
seconds/16MiB live log, and the complete private batch at600 CPU/1200 wall
seconds, within the charter's12-render maximum (this protocol uses10).
Metadata-only reader mutations add no renders. Limits include retries as
separate retained attempts; no failed output is replaced or spliced into a
later population. No new real-input schedule, public/default promotion, SOTA
claim, M193b registrar change or common-TIFF completion is authorized here.

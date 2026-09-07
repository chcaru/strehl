# M194e implementation plan — a bounded geometric reference generator

2026-09-07. **Design only. No implementation or generated image is authorized
until root review and prospective commit.** This plan follows the allocated
[charter](charter.md) and the independent
[next-occlusion-audit](../m194d-band-admission/next-occlusion-audit.md), read before
this design. M194d is committed at `7c1cfdbd10e1c1db0186b5054c23deabae2a63fd`.
No production, historical experiment, input, calibration or default changes.

## Decision and prior boundary

Implement one experiment-local, scalar, two-layer geometric integral. The
foreground is an opaque straight half-plane; the background is complete.
Layer radiance is an analytic constant, affine function or at most two cosine
waves. This restricted family permits exact visibility crossings and useful
independent mathematical references. It is not a triangle renderer, arbitrary
image-layer compositor, varying-depth model, wave-optical simulator or physical
camera reference.

Search actually run:
`python -X utf8 experiments/ORCH-drift-check/prior_art.py two layer pupil occlusion radiance`.
The charter/audit record the read M25, M87 §26, M63 and SYNTHESIS decisions and
primary literature; their failures and physical restrictions apply unchanged.
No novelty, physical calibration or320×240 quality comparison is claimed.

## Exact mathematical model; approximate numerical evaluation

Native photosite centers are integer `(x,y)`, starting at `(0,0)`; the cell is
`[x-.5,x+.5] × [y-.5,y+.5]`. Coordinates and integration use f64 in this
reference generator. Production remains u16 CFA storage/f32 arithmetic.

The recorded forward similarity maps canonical coordinates to native:

```text
z = c + a R(theta) (q-c) + t,       a > 0
T(z) = c + R(-theta) (z-c-t)/a
d_l = K * (inverse_focus - 1/depth_l)
q_l(z,u) = T(z + d_l u),           |u| <= 1
```

The same pupil coordinate `u` reaches both layers. Displacement is in native
pixel units **before** inverse similarity. Consequently T transforms both the
unit cell and pupil displacement: the canonical cell and blur radius scale by
1/a. Applying T only to the chief ray is a powered incorrect control. The main
commission uses identity T in every frame. A single independently checked
nonidentity coordinate control is not a breathing track, alignment estimate or
claim about M103; the historical curved track remains untouched.

Depths are ordered positive model lengths; K has native-pixel-times-length
units. No camera quantity is calibrated. Global sign reversal is the inert
substitution `u -> -u`; individual absolute values at between-layer focus are
a live incorrect model.

Let `A(q)` be the foreground binary mask, `F(q)` foreground electrons and
`B(q)` background electrons. The point and cell expectations are exactly
defined by:

```text
L(z,u) = A(q_F(z,u))*F(q_F(z,u))
         + (1-A(q_F(z,u)))*B(q_B(z,u))
P(z) = (1/pi) integral_{unit disc} L(z,u) du
E(x,y) = integral_{native unit cell} P(z) dz
```

The pupil is uniform in area; in polar coordinates its normalized weight is
`r dr dtheta/pi`, not uniform radius. Irradiance is radiance-normalized: changing
aperture does not change DC exposure. This explicitly omits aperture throughput,
cosine falloff/vignetting, diffraction, aberrations, scattering, translucency,
polarization, wavelength-dependent PSFs and calibrated camera response.

At K=0, visibility is still composed **at each cell sample before averaging**.
A cell-averaged foreground mask multiplied by a separately averaged background
would remain wrong even in the pinhole limit. The cell-integrated pinhole
composite is an ideal latent; it is not a proven attainable capture or error
floor when two depths are present.

## Numerical method and bounded error accounting

Use polar pupil coordinates for the author and Cartesian pupil chords for the
independent reviewer. For a given native cell point and polar angle, the
foreground half-plane is a linear inequality in radius. Solve its crossing
exactly, clip it to `[0,1]`, and integrate foreground and background over their
own radial intervals using the same visibility partition. Angular intervals
split where the crossing reaches the unit circle, and at zero projection of
the pupil direction onto the mask normal. Put the periodic interval boundary
at a mask-normal perpendicular: partial visibility needs at most4 intervals.
Fully visible/hidden points use one full interval, without irrelevant mask
splits. No hard mask is sampled on a fixed midpoint pupil grid.

Constant and affine radial terms have elementary primitives. For a wave use
the following stable integral over radius `[m-h,m+h]`:

```text
integral r*cos(phi+beta*r) dr
 = 2*m*h*sinc(beta*h)*cos(phi+beta*m)
   - 2*h*h*D(beta*h)*sin(phi+beta*m)
sinc(z)=sin(z)/z
D(z)=(sin(z)-z*cos(z))/z^2
```

The zero-width interval returns zero. At small argument use the explicit
Taylor limits (`sinc(0)=1`, `D(0)=0`) to avoid cancellation; this primitive gets
its own independent integration checks. The full continuous pupil controls,
not a disconnected two-ray calculation, must establish the generated values.

Angular integration uses16/32-point Gauss-Legendre comparison on each exact
interval with adaptive bisection, maximum depth10. The pupil error indicator
target is0.00025 electrons per point, normalized after combining intervals.
Native cells are clipped by the focused mask edge and the two pupil-tangency
lines; convex pieces are triangulated. A Duffy triangle map with4/8-point
Gauss-Legendre per coordinate and bounded bisection integrates the cell,
maximum depth6. For each low/high cell quadrature, propagate pupil indicators
with its nonnegative native-area weights: `eP,H=sum(wH*epoint)` and similarly
eP,L. Weights across pieces sum to the native cell area1; never sum point
indicators unweighted or renormalize by visible pupil/cell area. Allocate
angular budgets by interval length and cell-piece budgets by native area.
The cell indicator is `sum(abs(QH-QL))+eP,H+eP,L`, at most0.00075e; the final
reported indicator adds eP,H (at most0.00025e), hence at most0.001e.
Indicator agreement is not a rigorous bound: independent formulation,
separate refinement and deliberately underresolved controls remain mandatory.

The fixed commissioning budget is max absolute discrepancy0.004 electrons
(0.001 raw DN at the declared gain), whole-frame and edge-band RMS0.0008
electrons (0.0002 raw DN). The pupil and cell indicators must sum to at most
0.001 electrons per cell. Separate refinements change the result by at most
0.001 electrons per cell, and the independent reference's own refinement by
at most0.0005 electrons. Tightening pupil and cell tolerances by4 and increasing
their Gauss orders respectively to32/64 and8/16 are the **only** registered
refinement arms. They are diagnostics, not settings selected for best appearance.
The independent design must use this common budget before commit; a looser
independent tolerance cannot commission it.

Work ceilings:4,000,000 point-integral calls and600,000,000 angular nodes per
frame per arm;600 process-CPU seconds and1200 wall seconds per complete
five-frame arm, checked between bounded batches. Only the script's own work
stops on exhaustion; it never stops another process. Any depth/work/time/error
failure returns `UNCOMMISSIONED_NUMERICS`, retaining the planned scene and
diagnostics without omitted pixels or relaxed tolerance. No performance claim.

## Small exact scene set

One intended scene,64×48 native cells, foreground depth1 and background depth2,
K12, five inverse-focus values `[.5,.625,.75,.875,1]`, identity geometry. All
five complete floating-point arrays and all pixels, including the boundary
band, enter the independent comparison. The foreground support is
`x >= 32 + .15*(y-24)`. Scalar electron radiances are:

```text
F(x,y)=15000 + 1400*cos(2*pi*(.045*x+.095*y)+.7)
              + 700*cos(2*pi*(.17*x+.01*y)+.3)
B(x,y)=12000 + 3200*cos(2*pi*(.08*x+.015*y)+.2)
              +1800*cos(2*pi*(-.035*x+.12*y)+1.1)
```

These are positive, analytic synthetic textures; their phases and frequencies
will not be changed if the budget or later model checks fail. The fixed edge
band is native center distance at most8 pixels from the declared line. The
independent reviewer additionally re-chooses a non-square extent, oblique edge,
depths, focus and affine/cosine field. Scalar/channel-factor optics are enough
here; arbitrary RGB scenes and wavelength-dependent physics are not added.

Controls are in the preregistration. Affine fields use bounded nonnegative
point/cell footprints; they are not infinite physical scenes or quality inputs.

## API, schema and source boundaries

Proposed experiment-local functions, with immutable scene/frame/integrator
records and explicit exceptions/results:

```text
evaluate_rays(scene, frame, native_xy, pupil_uv) -> scalar_electrons
render_point(scene, frame, native_xy, integrator) -> (value_e, numerical_receipt)
render_cell(scene, frame, integer_or_fractional_center_xy, integrator)
    -> (value_e, numerical_receipt)
render_frame(scene, frame, sensor, integrator, output_directory)
    -> uncommissioned_float_frame_receipt
emit_cfa_bundle(bound_float_receipts, trusted_float_commission_path_and_hash, output)
    -> cfa_manifest_awaiting_independent_conversion_check
```

`evaluate_rays` is the direct mathematical evaluator for finite-node controls;
continuous rendering may use analytic radial integration, so passing discrete
controls alone does not validate its quadrature. Both consume the same scene
definitions, order, T and signed-defocus record. Use NumPy and standard-library
Python already available; no new dependency or external implementation read.
Proposed source files remain under this directory: `model.py`, `render.py`,
`commission.py`, `emit-cfa.py`, `author-controls.py`; reviewer files are separate.
These names are design only, not authorization to create code before review.

Use `m194e-joint-pupil-v1`, never M194b's schema. Keys: schema, status, producer,
sensor, scene, ray_model, numerical_contract, frames. Bind the stated model,
source/design/independent commission, numerical settings/error/work counts and
float/CFA files by SHA-256, shape, dtype and byte length. Refuse unknown keys,
duplicate keys, nonfinite values, malformed types/hashes/order, nonpositive
depth/scale and invalid pupil samples. No general authenticity adapter claim.

The two commission stages are acyclic: `m194e-float-frame-v1` receipts describe
uncommissioned arrays; an independent `m194e-float-commission-v1` PASS binds
those arrays and sources. Only that externally supplied receipt permits CFA
emission. The CFA manifest then says `float-commissioned-cfa-unverified` until
a separate `m194e-cfa-commission-v1` result checks actual conversion/files.
Nothing requires nonexistent CFA files to authorize their own creation.

Close child schemas before code: a FileRef has exactly relative `path` string,
lowercase64-hex `sha256`, and nonnegative integer `bytes`; an ArrayRef adds
`dtype` (`<f8` or `<u2`) and integer `shape` `[48,64]`. Reject bool-as-integer,
absolute/traversing paths, extra keys and duplicate indices. A frame record has
exactly `index`0..4, `inverse_focus` from the ordered list, `K`12,
`forward_similarity` `{scale:1,rotation:0,centre:[0,0],translation:[0,0]}`,
`expected_scalar` ArrayRef, and `numerical_receipt` FileRef. Scene fields are
exactly the two depths, mask `{normal:[1,-.15],offset:28.4,side:"ge"}`, and
foreground/background `{constant,affine:[0,0],waves:[{amplitude,frequency:[fx,fy],phase}]}`
with the constants above. Scalar fields are finite f64 numbers; coordinate
arrays have fixed lengths. Microcontrol configurations are separate input
records, not alternative emitted scenes. Sensor fields are exactly width64,
height48, cfa`RGGB`, active_origin`[0,0]`, channel_factors`[.75,1,.6]`, black512,
white15360, gain_dn_per_e`.25`, noise`false`, rounding`ties-to-even`,
cell`integer-centre-unit-square`. Producer/ray/numerical metadata are bindings
to the frozen explicit model/settings records; no candidate-selected formula
or setting is accepted instead. Optional CFA frame fields are `expected_cfa`
ArrayRef and `cfa` ArrayRef, required together after emission.

Optional post-commission CFA is noiseless: scalar electrons times fixed RGB
factors `[.75,1,.6]`, RGGB, both greens1, origin0, tightly packed little-endian
u16. DN=`512+.25*e`, ties-to-even, white15360; rails/nonfinite values refuse.
Retain floats before quantization; its≤.5DN error is separate from integration.
No shot/read noise or post-WB image. These achromatic factors are not spectral
calibration. The production bridge and its noise/WB/schema plan are deferred.

Store only the current scalar float frame, expected-CFA float frame and u16
frame, plus bounded tiles/node batches. No N-frame arrays or aligned-frame
volume. Cap simultaneous evaluated node pairs at32768 and explicitly counted
temporary ndarray storage at32MiB; instrument actual retained ndarray objects
and frame lifetimes. These are allocation/lifetime checks, not total RSS.
Tile-size8/16 and frame enumeration reorder must preserve float and CFA bytes
after restoring registered frame order; changing an actual source parameter
must be live. Stream hashes and write one frame at a time.

Author controls and floating candidates may be retained as uncommissioned work.
The CFA publisher requires an externally supplied, hash-bound successful
independent **float/model** commission for the same source/model/arrays. Actual
CFA/manifest checks follow emission under a separate bound receipt. A failed commission
withholds the dependent CFA bundle and returns nonzero. No merge-quality
comparison, product adapter, capture, holdout, SYNTHESIS fold or scorecard change
is authorized by this initial design.

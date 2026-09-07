# Independent review of the proposed private coordinate control

2026-09-07. Design/source review only. No producer or product edit, compilation,
fixture rendering, new quality population or numerical authority. The current
M194e fifteen-array run must terminate and pass its independent comparison
before genuine CFA emission/admission can support this proposed bridge.

## Finding

The bridge draft identifies the right consumer: actual delivered TIFF pixels
at their native canonical coordinates. It is not yet quantitatively complete.
The phrase "coordinate-coded constant/affine private fixture" needs a fixed
field, two-dimensional sensitivity, actual nonzero crop, checked interior,
finite arithmetic allowance and explicit wrong-mapping controls before release.

A constant cannot detect a coordinate error. One scalar affine field
L(x,y)=c+gx*x+gy*y is also insufficient for a general two-dimensional offset:
the change is gx*dx+gy*dy, which vanishes along the perpendicular direction.
For example a scalar ramp80x+120y is blind to the integer shift(3,-2).
Repeating that ramp in all three channels does not add an independent axis.
This is a mathematical failure of power, not a measured production defect.

Curie's subsequently read `next-bridge-implementation-review.md` already
proposes distinct RGB affine gradients, which have rank2 and avoid this
nullspace. The root draft itself had not specified shared scalar gradients;
the issue above is an unresolved specification choice, not a claim that either
agent implemented a defective fixture. The independently re-chosen fields
below are complementary to Curie's weaker-gradient proposal. His equal crop
origin(3,3) should be replaced or complemented by unequal axes: swapping the
two equal offset components has no effect even with rank2 image gradients.

## Small concrete candidate for the private integration fixture

Retain64x48 active RGGB, black512/white15360 and the proposed f32 WB.
Use five identical noiseless CFA inputs, separate from any admitted M194e
manifest. The desired pre-quantization post-WB affine fields, in DN, can be:

```text
R(x,y) = 2000 + 80*x
G(x,y) = 3000 + 100*y
B(x,y) = 2500 + 40*x + 60*y
```

At each CFA site store respectively512+.75R,512+G,512+.6B. These quantities
are integers at every native integer site: red increments60DN/x, blue
increments24DN/x and36DN/y. No input rounding uncertainty is needed for this
particular private stimulus. All active values and WB-adjusted outputs remain
well below white. Red and green supply independent coordinate axes; blue
checks a mixed direction and chromatic/CFA interpretation. A separate constant
companion remains useful for black subtraction and writer normalization, but
must not be counted as coordinate power.

The exact constant companion is R=2000,G=3000,B=2500, with stored CFA values
2012,3512,2012 respectively (black included). Its red/blue stored coincidence
is intentional: differing fixed WB must still yield distinct2000/2500 output
channels, so omitted WB remains powered. It is not alone a red/blue raw-label
permutation control; the affine arm supplies that distinction.

Use an explicitly private prepared domain with quad crop(3,5,24,16), hence
48x32 native output and native offset(6,10). This is a valid subset of the
32x24 full quad domain; it is not a claimed result of the genuine package's
automatic cover fit. Bind that private domain before pixels and use the
actual shared prepared production body and TIFF writer. The oracle evaluates
(x,y)=(u+6,v+10), not a rectangle inferred from output dimensions.

An economical fixed oracle interior is integer output u in[14,34), v in[14,18).
Its80 sites include every CFA parity and off-diagonal coordinates. Fourteen
native pixels is the previously derived conservative one-band local guard
(six quad pixels through energy plus one quad for final MHC) under identity
gather and fixed beta. The private identical-frame fixture also allows
reconstruction cancellations; those are not a reason to claim arbitrary
depth/noise scenes have the same support or invariance. Record actual levels
and prove that the selected interior is nonempty before reading pixels.

## Oracle and quantitative rejection

For independently affine color fields, each channel's second differences
vanish. Interior MHC corrections therefore vanish and the symmetric missing
channel interpolation preserves each affine field. This is a direct analytic
oracle; do not import the product's stencil implementation or fit an affine
surface to the observed TIFF. Include actual represented f32 WB multipliers:

```text
expected_R = R * .75 * float64(float32(4/3))
expected_G = G
expected_B = B * .6 * float64(float32(5/3))
decoded_DN = TIFF_u16 * 14848 / 65535
```

The writer's half-up quantization alone contributes at most
14848/(2*65535)=approximately.1133DN when unclipped. A prospective maximum
absolute error threshold of.25DN per channel/site leaves approximately.1367DN
for the actual f32 gather/pyramid/MHC/writer arithmetic. This is a proposed
component commission tolerance, **not an independently proved universal f32
error bound**. If it fails, preserve the discrepancy and diagnose the path;
do not enlarge the tolerance after observing the output. The test can instead
register a separately derived finite-arithmetic bound before implementation.

Power is large relative to that fixed tolerance. A one-native-pixel x error
moves R by80DN, while a y error moves G by100DN; half-pixel errors move those
channels40/50DN. Omitting the declared crop offset moves R by480DN and G by
1000DN. Doubling it moves by the same magnitudes in the opposite direction.
Thus no nonzero two-dimensional constant displacement can hide through a
single-gradient nullspace. Transposition/reflection must be checked over all
80 sites, not only diagonal or symmetric coordinates. Red/blue channel swap,
CFA parity swap and subtracting512 a second time also need explicit negative
oracle controls paired with the unchanged interpretation.

Checking only that a falsified plan digest is refused proves plan consistency,
not delivered coordinates. Retain both the stale-plan refusal and the actual
TIFF-versus-independent-field comparison. Private wrong-oracle controls can
prove the latter detects omitted/double/half-quad crop, swapped axes and second
black subtraction without changing production source. A private decoded-site
mutation must additionally change actual output, separately from the oracle.

The four genuine-package TIFF runs in the draft do not include the private
coordinate TIFF and its constant/mutation companions. Name those extra small
temporary TIFFs explicitly in the bounded run count, rather than counting
their controls while saying only four TIFF files exist.

A precise private decoded-site potency companion can add64DN at the active
green photosite(29,26) in each of the five identical inputs. It lands at output
(23,16), inside the fixed interior, without clipping. Changing all five copies
retains the identical-frame reconstruction property and avoids betting this
test on whether a selective merge admits one changed frame. Require that
actual delivered green sample to rise by more than63.5DN, with the unchanged
baseline as its companion. This commissions active-sample-to-writer liveness;
it does not prove a general one-frame outlier must be admitted. The mutation
belongs to the private source API and must not reuse genuine authority for
modified admitted CFA files.

## Inspection and remaining scope

Read `next-production-bridge-preregister-draft.md`, Socrates's
`next-production-bridge.md`, the current prepared source/crop extraction in
`crates/strehl-cli/src/merge_cmd.rs`, M194b's reader/score conventions,
`demosaic.rs` MHC stencils and `image_out.rs` writer entry points. Initial rg
requests containing literal Windows glob paths failed and were replaced by
explicit existing source paths; no absence claim relies on those failures.

The registered main package has identity geometry and no measured probe band.
Even a successful private affine coordinate control would commission this
storage/crop/CFA/MHC/writer path only. It would not validate arbitrary
similarities, noise calibration, full three-band behavior, optical fidelity,
depth-boundary quality or real captures. The draft should retain those limits
and freeze its final quantitative private fixture before implementation.

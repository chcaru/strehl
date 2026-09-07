# Prospective M194f fifth-arm repair

Zeno, 2026-09-07. Design review only, before a WB-arm implementation or run.
The original population1 stopped at its fifth arm: CameraLinear rejects
`Exposure::resolve(false,1,false)`. Its first four RGB files and auxiliary
Gray file do not constitute the complete population and cannot grant the
bridge result. The original exposure control was a protocol/API mistake;
retain its failed command and partial population. No tolerance, model or
quality conclusion can be rescued from that incomplete result.

## Source and consumer boundary

`run_pyramid_prepared` destructures `PreparedPyramid.wb` and passes it only to
the final `write_merged`. Each `Frame.wb_coeffs` remains independently fixed
at the baseline coefficients used by gather/probe. Thus a test-only prepared
writer WB override can be made without changing decoded CFA, injected noise,
alignment, frame metadata or merge settings. The plan must record both frame
WB and prepared writer WB explicitly. No lookup, normalized green change,
viewing exposure or modified measurement writer is required.

`write_merged` applies WB to the reconstructed CFA **before** calling
`image_out::write_demosaiced`; `demosaic_row` uses MHC on that mosaic.
MHC preserves the observed channel at its own CFA location. It generally
does not commute with an independent gain on one channel: interpolated green
at a red site contains a red-channel curvature correction. Interpolated red
also contains other-channel corrections. Consequently the initial proposed
all-pixel G/B identity and all-pixel R doubling bars are prospectively
rejected as incorrect operator assumptions. They are not failed data that
may be carved out after inspection. Uniform all-channel doubling is also
withdrawn: it changes green normalization and acts as a measurement rescale.

## Admissible bounded replacement

Use the same genuine inputs, exposure0 and count observer for a fifth RGB
arm named `red-wb-double-count`. Prepared writer WB is
`[float32(8/3),1,float32(5/3)]`; frame WB remains
`[float32(4/3),1,float32(5/3)]`. Its red gain is exactly twice the represented
baseline red gain. The other four genuine RGBs, private three RGBs, and three
Gray files remain the eleven-file population. Rebuild/rebind and rerun the
complete prospective population after release. No partial-run splicing.

Determine parity in the **actual native gauge**, adding the recorded native
crop offset to output coordinates. The quad crop should preserve RGGB phase,
but the oracle must not silently assume an origin. Check every delivered
observed-channel sample, rather than selecting an agreeable ROI:

- Native even/even: baseline and changed red must both lie strictly between
  0 and65535. Require `abs(changed_R - 2*baseline_R) <= 1` in signed integer
  arithmetic, and an increase at every measured red site. The baseline measured
  red maximum must exceed1, retaining an amplitude witness above a unit code.
- Native opposite parities: changed green must equal baseline green exactly,
  separately covering both green phases.
- Native odd/odd: changed blue must equal baseline blue exactly.

All four parity populations must be nonempty and collectively cover the full
native output grid. Report their counts. Report interpolated-channel changes
separately without asserting identity, double gain, or optical quality.

For positive finite normal f32 values, multiplying a factor by an exact power
of two preserves the rounded f32 result up to that exponent scaling, absent
overflow/underflow. Here the red source and writer factors are unchanged except
for that exact doubling. At measured red sites MHC returns the red mosaic
value. Half-up u16 quantization satisfies
`Q(2z)-2Q(z) in {-1,0,1}` before clipping. That derives the one-code bar; the
positive/unclipped checks retain its domain instead of excluding bad samples.
The actual producer arithmetic must still pass the bar. No tolerance widening
is authorized by this derivation.

This observed-site control proves prepared-WB delivery and setting potency.
It cannot distinguish correct pre-MHC WB from an incorrect post-MHC gain that
happens to agree at observed sites. The fixed affine RGB control is also
unpowered for that ordering distinction: its cross-channel second derivatives
vanish. Source inspection alone currently establishes the ordering. Do not
describe either numerical comparison as a complete demosaic ordering proof.

## Independently re-chosen instrument controls

Before reading the new genuine arm, commission the actual new reader function
on a private22x18 raster, with unequal nonzero native origin(6,10), separately
also origin(7,10) to power native-parity use. Baseline code ramps are
R=3200+43u+17v, G=7100+23u+31v, B=9300+29u+11v. Set changed observed R to
2R plus a repeating{-1,0,1} code sequence; preserve observed G/B, and deliberately
change interpolated components. The legitimate within-bound sequence and
unscored interpolated movement must pass. These fabricated code arrays are
reader fixtures, not MHC/optical truth.

The following fixed mutants must fail the actual function: unchanged red;
wrong channel doubled; red multiplied by3; one measured red residual+2;
one measured G1 changed; one measured G2 changed; one measured blue changed;
zero/clipped baseline or changed red; wrong native origin parity; empty or
mismatched extents; and a red population restricted to baseline code1.
Record both parity populations' counts and the maximum
signed red residual. A per-channel luma or whole-image norm cannot substitute
for these separate observed-channel conditions.

The final reader must also require the fifth arm's new settings/plan/env;
stale exposure1, unchanged prepared WB, changed frame WB, or altered genuine
inputs/settings must refuse. Exact public adapter field names will be bound
to the root's final amendment before implementation. Preserve the old reader
and its outputs; this new instrument is an explicit protocol amendment.

## Non-affine MHC witness for the rejected interpretation

This is a source-derived prospective **direct component** fixture, not an
optical scene or a new product TIFF. Use a9x9 RGGB mosaic in prewriter DN,
constant at R2000/G3000/B2500 except an80DN addition to red native(4,4).
Compare it with a mosaic whose red samples alone are doubled. The MHC center
row is safely beyond the two-pixel stencil boundary. The observed R component
must read2080 then4160. Independently summing the source stencil's nonzero
curvature response predicts interpolated G3040 then3080 and B2560 then2620:
the80DN impulse enters with green coefficient4/8 and blue coefficient6/8,
while the constant red background has zero curvature. Thus interpolated G
changes40DN and B changes60DN even though their observed CFA samples never
changed. Both fields stay positive and far below the normalization rails.

Passing companions: baseline red impulse, actual red-doubled mosaic, and
the same pair without the impulse (G/B remain3000/2500 in that constant null).
Wrong-order destroyer: demosaic the baseline first and only then double R;
it retains center G3040/B2560 and fails both changed-center predictions.
Run the actual `demosaic_row` component after registration/release; the
source-derived numbers alone are DERIVED, not a measured implementation pass.
This witness demonstrates why the all-pixel rule is invalid, without fitting
a genuine output or changing the sampled-site bar. It also supplies the
non-affine ordering power absent from the private affine control.

Root amendment-1 draft SHA256
`7123c1e758729558131ffc8c5eca26950c48778d365de521fc5b8e6dce5d8e54`
was read. Its replacement and complete-rerun requirements agree with this
review. Root is adding explicit `frame_wb_f32` baseline alongside changed
prepared `wb_f32`; bind the final draft hash before implementation.

Final root amendment SHA256
`925b454c19380ffe21ca14fcb6640b269a5ca2af7c1b2e38d061cdedafd210b0`
has been read and accepted for this lane. It includes the explicit frame WB,
amplitude witness, and complete fresh-eleven-file requirement. It chooses
Socrates's10x8 two-impulse actual component witness instead of the alternative
9x9 witness proposed above; do not execute or count both as required controls.
The9x9 construction remains DERIVED and unexecuted.

I separately checked the adopted arithmetic against the source terms. The
red64 impulse contributes32 to interpolated G at the red center and the
adjacent green80 contributes20, giving1052; red doubling gives64+20 above
1000, hence1084. The center blue correction changes48 to96, giving1048/1096.
At the neighboring green site, red impulse interpolation contributes32 then64
and the green curvature contributes50 in both arms; R therefore reads1082
then2114, whereas post-MHC red multiplication gives2164. These are distinct
cross-channel mechanisms and have a zero-curvature constant companion. This
is a prospective source/arithmetic review, not a report that the actual MHC
test has already run. No implementation blocker remains in this lane.

# M194f amendment1 independent design review

2026-09-07. Source and arithmetic review only, before replacement implementation
or output. The registered exposure+1 arm is impossible on this CameraLinear
path: `Exposure::resolve(false,1,false)` returns `ExposureError::NeedsSrgb`.
The actual fifth-arm refusal in `production-population-1` is correct product
behavior, and the partial population has no final index. Its first four RGB
outputs and auxiliary Gray image remain historical evidence, not a completed
eleven-file result. The prior design review failed to catch this unsupported
control; this amendment must retain that mistake.

## Rejected first replacement and defensible scope

Root first proposed red-only WB doubling with all-pixel R×2 and G/B identity.
That predicate is also invalid. `merge_cmd::write_merged` applies WB to each
CFA plane in its `norm`/`spec` expressions before interleaving the mosaic.
`image_out::write_demosaiced` then calls `demosaic_row`, which uses the default
Malvar-He-Cutler stencils. Their cross-channel correction terms couple red
samples into interpolated G/B and leave undoubled known-channel corrections
inside interpolated R. No actual replacement output was examined to discover
or relax this mathematical disagreement.

The accepted prospective control keeps normalized green gain1, changes only
the injected prepared red WB from represented f32 `4/3` to `8/3`, and retains
blue `5/3`. It changes no admitted CFA, noise, geometry, merge, exposure or
confidence setting. The fifth arm remains count mode with one successful
decode per original frame and five hooks. The eleven-file population is
unchanged. This tests a delivered-setting dependency, not color correctness or
image quality. A uniform gain2 was considered and withdrawn; green2 would no
longer match the existing green-normalized WB convention.

## Sampled-site predicate and quantization

Derive each site's CFA parity from the actual plan's integer canonical native
offset, not an arm label or a hard-coded mask unrelated to the plan. The current
computed crop has offset(10,8), so output even/even is red, odd/odd is blue and
mixed parity is green. Its44×34 grid contains374 measured red,748 measured
green and374 measured blue samples. These are all sampled sites, including
borders; no quality ROI or selected subset is introduced.

`demosaic_malvar_row` assigns each known channel directly from the mosaic at its
own CFA site. Border reflection affects its interpolated components, not this
assignment. For every measured red site require integer TIFF codes
`abs(R_changed - 2*R_baseline)<=1`. Perform that arithmetic in a signed/wider
integer type. Require every compared red code to be positive and below65535
in both arms; clipping can otherwise manufacture a passing difference of1.
Also require an occurrence witness `max(R_baseline)>1`, so a no-op cannot pass
the1-code tolerance through an all-one-code stimulus. For every measured green
site require exact G code identity; for every measured blue site require exact
B code identity. Do not attach either claim to the other two interpolated
components at those sites.

The one-code allowance is appropriate to doubling the same finite unbounded
prequantization value followed by half-up u16 rounding: for `Q(z)=floor(z+.5)`,
`Q(2z)-2Q(z)` belongs to{-1,0,1}. The represented f32 red gains differ by an exact
power of two; the unchanged normal-range normalization operations commute with
that scaling. The registered positive/unclipped output range excludes the
underflow/overflow cases that would defeat this argument. This is a scoped
setting-control bar, not a general f32 error theorem or a truth-error allowance.
The actual live output must still pass; preserve and diagnose any failure.

Report interpolated-component differences separately without an identity or
doubling admission bar. Their changes are expected consequences of the chosen
linear demosaic and cannot be relabeled as unintended merge changes or quality
improvements. Keep full file/pixel hashes and actual dimensions for all outputs.

## Independently selected failing inputs

Before the new output, commission the reader's predicate with these companions:

- A no-op replacement must fail sampled-red doubling on a fixture with positive
  red codes above1. Correct doubled sampled-red values, allowing both rounding
  residual signs, must pass. A2-code residual must fail; no metric search.
- Wrong red phase masks selecting either green phase or blue must fail the
  doubled-red check on distinct positive known samples. Correct canonical
  parity passes. Plan/type checks must reject fractional or false offsets
  rather than casting them into a convenient parity.
- A changed measured green or blue code must fail its exact identity predicate.
  Changing only an interpolated component must not be misreported as failure
  of a sampled-site identity rule; it is retained in the separate diagnostics.
- Zero or65535 measured red values refuse regardless of a numerically small
  doubling residual. A valid positive/unclipped companion remains required.
- A plan describing doubled WB while the prepared body receives baseline WB
  must fail the live no-op/pixel control. A changed WB value or mode paired with
  the old plan must refuse the actual full recomputed-plan comparison.

A direct non-affine MHC counterexample proves the rejected all-pixel predicates
are false without fitting anything to the product output. Use a private10×8
already-white-balanced f32 mosaic expressed directly in DN, without normalization:
all sites1000DN, a64DN impulse at red(4,4), and an80DN impulse at green(5,4).
The changed mosaic doubles red sites only. The relevant exact stencil values
are:

| Location/component | Baseline DN | Red-doubled DN | Rejected wrong prediction |
| --- | ---: | ---: | ---: |
| red(4,4), measured R | 1064 | 2128 | Correct sampled doubling |
| red(4,4), interpolated G | 1052 | 1084 | G unchanged at1052 |
| red(4,4), interpolated B | 1048 | 1096 | B unchanged at1048 |
| green(5,4), interpolated R | 1082 | 2114 | R doubled to2164 |
| green(5,4), measured G | 1080 | 1080 | Correct sampled identity |

These come directly from the fixed F_G/F_X/F_H taps: the red impulse contributes
32 to green and48 to blue at its own site; at the adjacent green site, the red
impulse contributes32 to red while the undoubled known-green impulse contributes
50. The whole5×5 support fits inside the non-square fixture. Run actual
`demosaic_row` on this DN-valued `Mosaic`; its sample units are supplied by the
caller. These integer inputs and the named stencil results are exactly
representable in f32. There is no division by14848, TIFF quantization or writer
in this component. Valid companions must pass and the wrong all-pixel rule must
fail. The separate full-writer control above includes the production
normalization and quantization; do not claim this component commissions them
or that these source-derived values are already an executed control.

## Required binding and failure regression

Bind a finite explicit WB mode and actual represented three-gain values into
the plan, and pass those same values to `PreparedPyramid.wb`. Keep the admitted
manifest's source channel factors distinct from this controlled development
setting; it is not a new camera calibration or a new optical input. The shared
fold/noise/gather and the actual writer remain untouched. Rebuild and rebind
affected adapter/reader controls before generating the complete new population.

Add a regression on the real production refusal:
`Exposure::resolve(false,1,false)` must return `NeedsSrgb`, while
`Exposure::resolve(false,0,false)` remains `Exposure::None`. The bridge must
also reject the unsupported exposure request at its setting boundary instead
of producing another nominally valid plan for a render that cannot run.
This regression preserves the production contract; it does not enable exposure
on measurement output or widen the earlier protocol silently.

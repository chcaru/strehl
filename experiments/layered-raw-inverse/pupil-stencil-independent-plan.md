# Coupled pupil stencil: independent numerical commission

Prospective; root executes this script. Neither author executes their own
implementation or controls. No inverse fit, source selection, photographs or
quality admission. This tests a fixed supplied constant-depth optical operator
and its first adjoint, followed by a separately fixed quadrature-resolution
question. The actual camera/lens/illumination model is not calibrated here.

## Discrete operator first

Use the existing independently specified64 equal-weight pupil sites, original
two depths, scale12 and fixed common sigma0.7 PSF. Build tables for focus
indices0/4/8. Commission on native48x44 constant, impulse, alpha0, alpha1 and
crossing fixtures. Constant radiance/coverage applies to the original domain;
outside near coverage is0, so alpha1 does not imply zero far transmission at
the image boundary. Full-domain arrays are compared, not only an interior.

One independent CPU implementation directly enumerates rays, uses literal
integer zero-extension and four bilinear taps, composes per-ray transmitted
far plus premultiplied near, and accumulates images in f32. It does not call
the table builder, CUDA kernel or frozen Torch sampling. Scalar offsets/tent
setup use f64. Compare its pre-PSF output with the stencil at max error0.1DN.
Separately compare actual stencil-plus-frozen-PSF output with the unchanged
Torch grid_sample operator at the same0.1DN, matching the prior discrete
forward commissioning allowance. Normalized-grid rounding precludes bit
identity. Marginal mass, positive weights, index uniqueness and total mass
are checked independently from stored arrays using scalar f64 reductions.

For crossing at all3 indices, a nonconstant RGB incoming derivative exercises
the actual custom adjoint against the frozen Torch autograd. Each near/far/
coverage gradient must be live, max error<=1e-5+3e-4 times reference max, and
relative L2 error<=3e-4. These are prospective f32 reduction/coordinate bounds,
not a physical noise allowance. Independent central finite differences of the
direct CPU ray implementation test all3 input families at midpoint, using
fixed DN steps0.25 for radiances and coverage step0.001. Their scalar derivative
bar is2e-4+0.005*abs(adjoint); every derivative must exceed0.05 in magnitude and
a deliberately doubled derivative must fail. Image arrays remain f32; only
the final scalar finite-difference mean/dot is f64. No higher derivatives.

A literal full-boundary witness uses pupil(1,0), near shift-1/far shift0, near0,
far500 and alpha1 in a5x7 image. The first output column must be exactly500:
outside near alpha0 gives transmission1. Its incoming unit derivative must
produce far gradient1 in that column and zero near/coverage gradients. A wrong
near-outside discard gives0 and fails. A separate crossing compares correct
same-ray visibility with the independent-marginal outer-product shortcut;
the fixed supported difference must exceed1DN. All original input buffers
remain bit-identical. No rendered quality score is inferred from these checks.

Repeat that literal boundary/adjoint witness on a nondefault CUDA stream, with
all inputs produced in that stream and explicit synchronization before leaving
the check. Caller producer ordering is never confused with allocator lifetime.
Compact refusal checks cover CPU input, wrong dtype, noncontiguous strides,
nonfinite input, invalid coverage, invalid pupil and double backward. These
exercise the declared limited ABI, not a new optical or quality case.

No density work begins if any forward/adjoint/boundary check fails.

## Fixed density and independent re-choice

The candidate is preselected16384 equal-area polar sites:128 radial midpoint
annuli times128 angular midpoints, fixed rotation0.23 radians. Radius and angle
setup is computed independently in f64, then stored as f32 sites. It is not
selected from measured errors. Only the frozen layered scene is used, at the
original physical-adequacy focus indices0/2/4/6/8 and unchanged whole16:80 and
crossing regions. Near/far/alpha are the original full96 fields.

Independent references use the unchanged Torch ray operator under no_grad in
chunks of at most1024 rays, each weighted by its actual fraction of the total.
Average its full RGB outputs after the identical common PSF (a linear operator).
This never allocates a16k-ray image volume or dense adjoint. The same16384
sites first provide an assembly/kernel reference: full-image maximum difference
must remain<=0.1DN. This is mandatory mechanics, not optical adequacy.

Two distinct mandatory convergence comparisons then use the fixed0.75
original-noise-normalized RMS bar on BOTH regions at ALL5 indices:

- 4096 sites,64 radial by64 angular, same rotation0.23;
- 16384 sites with a fixed independent rotation0.60 (a0.37-radian change).

For each comparison, reference CFA expected signal supplies the already
injected variance `g*max(signal,0)+read_variance+1/12`; no private noise estimate
or WB/channel substitution. Reference discretization is not continuum truth.
Agreement is a finite-density convergence proxy under supplied optics, not
camera validity. The4096 comparison changes radial/angular resolution; the
rotation challenges angular aliasing. Neither supplies an independent physical
measurement. The old64, retained golden-angle1024 and independent polar1024
comparisons are also retained. Their known failures do not veto an independently
converged preselected16384 candidate and must never disappear from the report.
No later choice of sample count, phase, focus subset or bar is authorized.

## Resource and output contract

One root-owned process has a hard240-second wall cap and8GiB Windows job
committed-memory cap. Post-stage checks are60s runtime/compiler setup,60s
mechanics,120s density; these are boundary checks, not independent watchdogs.
Root's hard total protects a stuck stage. Stop if CUDA peak allocated memory
exceeds8GiB, and report reserved memory separately. Runtime DLL/PTX/compiler/
device metadata is retained. Table bytes/counts and per-index times are
recorded. The stencil has no image-times-table-entry array; reference volumes
are bounded by1024 rays. Process committed memory and CUDA allocated memory
are different quantities and neither is silently substituted for the other.

Root command:

```text
python pupil-stencil-controls.py --out <run/output>
```

Save mechanics.json before density and final result.json, including failure
stage when refused, source hashes, all discrepancies and resource figures.
`passed` means the commissioned fixed numerical operator AND fixed16384
convergence proxy passed. It never means an inverse fit or photograph improved.
No numerical execution by this controls author.

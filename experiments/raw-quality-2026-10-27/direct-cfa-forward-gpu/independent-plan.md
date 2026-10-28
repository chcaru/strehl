# Frozen measurement commissioning plan

2026-10-27. Source preparation only. Root schedules compilation and execution.
The controls commission GPU A and A-transpose against the frozen CPU
`Measurement`, SHA256
`536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac`.
No fit, focus rule, noise estimate, RAW decode or photographic improvement is
part of this checkpoint. Unit-square sensel integration is the inherited
operator assumption, not a measured Sony optical or pixel-response model.

The entry is `controls.py --out <fresh-directory>`. It writes `receipt.json`
with status `COMPLETE_DIRECT_CFA_FORWARD_CONTROLS`, `all_cases_completed`,
`mechanical_pass`, and unconditional false `photographic_admission` and
`quality_claim`. An unexpected error preserves an incomplete receipt and
fails the process. Ordinary fidelity failures remain in all completed cases;
they do not stop later diagnostic cases or become passing quality claims.

## Fixed population and bars, chosen before any execution

Three original-sensel rectangles are fixed:24x28 at physical origin(0,0),
19x31 at(3,5), and23x29 at(5,2). Maps are respectively identity into the
eight-pixel latent apron; translation(0.37,-0.29); and scale1.035 with
rotation0.071 radians plus translation(-0.23,0.41), centred in their latent
field. Rectangular/odd sizes and nonzero physical origins exercise literal
RGGB phase rather than local array parity. All four physical phases are scored
individually, including separate G1/G2 adjoint residuals.

The independent controller constructs all nine CPU query nodes by integrating
the ORIGINAL unit square before applying the complete affine map. GL3 axis
nodes are0 and plus/minus sqrt(3/5)/2; axis weights5/18,4/9,5/18 are multiplied
in f64 and cast once to f32. Geometry is f64; measurement fields, arithmetic
and comparison reductions are f32. The GPU receives only rectangle/map/field
descriptors, not the CPU matrix or expanded query nodes.

Fidelity bars are fixed prospectively:

| Quantity | Normalized maximum | Normalized RMS |
| --- | ---: | ---: |
| Forward, constants and forward partitions | 1e-5 | 2e-6 |
| Adjoint, phase-isolated adjoints and adjoint partitions | 2e-5 | 3e-6 |

Maximum error divides by max(1,reference maximum absolute value); RMS error
divides by max(1,reference RMS). These are numerical f32-equivalence bars,
allowing different coalescing/trigonometric/atomic reduction order, not sensor
noise or perceptual thresholds. Dot-product discrepancy is at most3e-6 after
division by max(1,||Ax|| ||y|| + ||x|| ||A-transpose y||). CPU and GPU dot
checks are both retained. Complete arrays and raw absolute errors are saved so
normalization cannot hide their physical magnitude.

## Producing-path controls

For every geometry, independent positive, signed and zero color constants run
first. The literal physical-phase channel map supplies expected values without
using the CPU output as its own constant truth. Structured R/G/B components
then have different frequencies, orientations, signs and amplitudes. A fixed
seed73242 signed residual tests the adjoint. These are operator test signals,
not synthetic focus-stack or reconstruction-quality examples.

Four uneven subrectangles reuse the SAME globally indexed latent field and
affine map. Forward pieces assemble in their original positions; adjoint pieces
accumulate through the actual supplied-output API. Both compare against the
whole GPU operation and the frozen whole CPU transpose. No local latent crops
or changed phase gauge are allowed.

Two actual forward interventions must fail the unchanged fidelity bars: add0.5
to the map's latent x translation, and use the diagnostic channel mapping
(B,G,G,R). Thus a producing operator that silently shifts coordinates or swaps
independent colors cannot pass merely through self-consistent adjoint tests.
Unsupported left/right footprint shifts must be refused by BOTH operators;
there is no clamp, reflection or crop rescue. These refusal controls are
separate from valid zero-valued input, which must produce a valid zero output.

CPU/GPU sources, this controller and the inherited NVRTC loader are bound
before/after. GPU runtime receipts retain helper/DLL/PTX/options identities.
Original query/input arrays are saved; GPU latent/residual input immutability
is checked. Four CPU threads, f32 default, TF32 off and8GiB maximum Torch
allocated/reserved memory are explicit. The root process wrapper independently
bounds wall time, total host commitment and CPU work. Allocator accounting is
not a measurement of every byte resident on the GPU.

Passing would permit a separately authorized full-source cost observation.
It cannot establish useful reconstruction, phase diversity, optical accuracy,
noise preservation, convergence or a practical299-source global solve. The
earlier flat/chroma and convergence failures remain unchanged.

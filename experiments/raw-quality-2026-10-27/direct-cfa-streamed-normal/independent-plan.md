# Prospective streamed-normal mechanical controls

2026-10-27. Root owns execution. These controls do not run an inverse fit, score
photographic quality, alter the fixed64-step solver, or erase the earlier flat
and convergence failures. CLI: `controls.py --out <fresh-directory>`; final
`receipt.json` status `COMPLETE_DIRECT_CFA_STREAMED_CONTROLS` retains all failure
flags with unconditional false quality and photographic admission.

Three original19x23 u16 fields use physical origins(0,0),(3,5),(5,2), identity,
fractional translation and scale1.025/rotation0.051 maps, with an eight-pixel
latent apron. Independent colored structure and a literal below-black datum
exercise the exact injected four-phase noise/black values. Original arrays,
map descriptors and hashes are saved. All reference code is pinned: CPU536aa094,
constant-deflation8fad7b79, coordinate helper638c7391 and frozen measurement8328b11c.

Constant paired A(x)/A(ones) tests run first, comparing against a separately
instantiated frozen GPU producer. The combined translation unit is not assumed
to have the old PTX. Signed colored fields follow. Original1e-5 maximum/2e-6
RMS forward bars remain unchanged. All-three-channel ones are only the packed
measurement; three color nuisances must still use literal physical phase masks.

GPU Haar packing, odd carries, inverse on independent coefficients, original
noise propagation, admission, total metric and factors are compared with the
actual frozen CPU arrays, per band. Relative L2 tolerance is3e-5 with NO unit
absolute floor; an exactly zero reference requires an exactly zero result.
Actual B/B-transpose, projected normal/RHS, restored field and final true
residual/objective are compared with the frozen CPU ProjectedProblem, including
its actual f32 projector. Normal/RHS allowed error is
`3e-4*||reference|| + 32*eps_f32*||corresponding unprojected reference||`.
Every nonconstant signal comparison additionally requires that entire allowance
be at most2% of the reference norm. An unresolvable comparison fails rather
than allowing a zero operator to pass. This is numerical equivalence, not
bit identity or an objective change.

Under total-metric1, each of three unit color constants must have projected
normal norm no greater than64*eps times its unprojected norm; CPU/GPU difference
has the same bar. A signed near-constant field adds(64,-32,16) to the fixed
structured field, challenging cancellation and offset invariance. Symmetry
uses3e-5 normalized by the two norm products, without floor1; PSD permits only
64*eps times the stated norm product as negative roundoff. The actual removed-
projection path must fail the same fidelity gate. A physical-origin shift with
compensating affine translation preserves positions but changes CFA labels;
its actual RHS must also fail.

Clipping support is independently derived from actual CPU Haar impulse
responses at six fixed invalid sites, including odd boundaries and all phases.
Literal replicated3x3 coefficient-neighborhood dependencies expand AC masks;
LL uses actual Haar support alone. Codes15360/16383 must be omitted,15359 kept.
With that original support frozen, replacing invalid values by0 versus65535
must preserve admitted d/variance/admission/metric, common scale, normal and RHS.
Disabling only the actual3x3 mask expansion must make this poison placebo fail.
Removing every red observation must refuse red constant support. Common N
remains the full original sensel count; invalid metrics are zero before max-q.

All finite completed failures remain in the receipt. Source files and original
u16 inputs are checked unchanged. Four CPU workers, f32, TF32/autocast off and
8GiB Torch allocation/reservation limits apply. Root separately bounds host
memory and time. This small commission is a prerequisite to a complete weighted
normal cost observation, not a full-image feasibility or quality conclusion.

# A complete original-CFA observation without a residual volume

2026-10-27. Root releases implementation and independent mechanical controls,
plus preparation of a native-u16 cache bridge. No full fit or RAW export is
released yet. The endpoint is one complete weevil photograph and direct-RGB
master, with the prior flat/noise failure and exact numerical status retained.
This checkpoint must lead to that observation or a concrete feasibility stop;
it is not another claim that an operator test demonstrates photographic gain.

## Evidence changing the implementation question

The preceding [GPU measurement](../direct-cfa-forward-gpu/results.md) is
independently commissioned on small CPU comparisons and complete native source
geometries. Full forward/adjoint operator calls cost approximately0.07–0.08s
each on this RTX5090. Its unchanged132-forward/133-adjoint64-step CPU algorithm
projects5781–6213s before other work and fails the frozen naive-port ceiling.
The elementary operator remains useful. The CPU algorithm's extra true-residual
checks do not update its recurrence, and retaining residuals for all299 sources
would require about39GB in addition to original storage.

The changed implementation is a globally streamed normal operator and normal
CG: same original measurements, source-grid Haar weighting and three constant
nuisances, but only global image vectors and one current source's f32 scratch.
No local-patch inverse stitching, source subset, extra iterations, learned prior,
optical blur claim or per-source RGB image is introduced. Finite-precision CG
is not asserted bit-identical to CGLS; control the actual normal/RHS first.

Root also read the three retained original RawPy-visible caches with NumPy
memmap (not new RAW decoding). Source0 and298 have no codes>=15360; source149
has196 such codes,168 at16383. Its minimum/maximum are485/16383. These caches
are7028x4688; the finding cannot cover the four additional native columns or
the other296 sources. A full observation therefore needs explicit clipping
omission rather than inheriting the old unconditional clipping refusal.

The subsequently bound root command was
`python -B experiments/raw-quality-2026-10-27/direct-cfa-streamed-normal/audit-retained.py --out outputs/raw-quality-2026-10-27/direct-cfa-streamed-retained-1`.
It freshly rehashed each original cache against its established identity,
repeated the phase counts and checked preservation; the
[receipt](../../../outputs/raw-quality-2026-10-27/direct-cfa-streamed-retained-1/receipt.json)
records the actual scope and producing source. This is an observation inventory,
not a camera white-level calibration or proof that all bright pixels are clipped.

## Implementation allocation

Cfa-residual owns `bands-gpu.py`, `normal-operator.py`, `solver.py` and
`operator-notes.md`. Import the frozen `../direct-cfa-forward-gpu/measurement-gpu.py`
SHA8328b11cecf710f0020e8dfc8e8ab68467301e32290ba204fc5f9d7ebc8c0d84;
do not edit it. Implement the exact frozen CPU physical-phase7-level Haar,
odd-edge behavior, marginal variance, replicated3x3 smoothing, admission and
factor operation order from `../joint-cfa-local-fit/band-residual/sensor-operator.py`
SHA536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac,
in CUDA Torch f32 with explicit devices and bounded scratch. Data storage stays
u16; the original-source variance is the one injected noise model. No private
noise estimate, quantization term or frame-axis filtering.

Root owns `measurement-paired.py`: an explicitly composed new paired-forward
kernel may reuse the frozen row builder to accumulate A(x) and actual A(ones)
in the same tap order. This avoids a second geometry construction while keeping
the real f32 constant response, including odd-boundary Haar effects. It must
independently match the frozen two separate forwards before use. The frozen
producer file remains unchanged; bind the wrapper and combined CUDA source.
The normal adapter supports either paired measurement or the honest two-call
fallback, with their distinct costs recorded.

For clipping, mark original codes>=the injected white as unobserved. Propagate
Boolean support through the exact Haar tree: a coefficient is invalid if any
contributing original site is clipped. Fine-band focus weights also depend on
a3x3 coefficient neighborhood, so invalidate every fine-band coefficient whose
replicated3x3 admission window touches an invalid coefficient. LL needs its
own actual support mask. Set factors for these coefficients to zero; do not
replace clipped values with invented radiance or pretend their inequalities
were used. Valid factors preserve the old formula/order. Record omitted counts
per phase/band and refuse absent color-constant support. This deliberately
changes the observation set only around clipping. It must pass a frozen-mask
poison-value placebo: arbitrary finite replacements at clipped sites cannot
change admitted observations/weights or the resulting normal/RHS.

For B=weighted-Haar*A, b=weighted-Haar*y, constants C, T=B*C and P the
three-column orthogonal projector complement, the global problem is
min||P(B*z-b)||^2; restore X=z+C*(T'T)^-1*T'*(b-B*z). Preserve the declared
common metric scale/count and actual coefficient arithmetic. Derive a streamed
normal and RHS using G=B'T and the three Gram entries, exploiting physical
color-disjoint support. Challenge cancellation near constants: prefer applying
the nuisance subtraction to each source coefficient vector before its adjoint
instead of subtracting two large global images. Do not assume T occupies only
LL: carried odd boundaries can create nonzero detail coefficients for constants.
State any f32 differences from the frozen CPU row-projection construction.

The solver has maximum64 steps, zero correction initialization and no new
regularizer/preconditioner/restart. Actual true normal/objective and restored
constant-direction checks are evaluated at the end; recursive quantities must
be labeled as such. Do not claim every intermediate true objective was checked.
Refuse nonfinite/nonpositive steps and retain the last finite output/status.
No convergence or quality bar is relaxed; the earlier flat failure remains.

Integration-review owns `controls.py`, `independent-plan.md` and
`independent-review.md`. Choose bounds before running. Challenge GPU Haar and
transpose on rectangular/odd-origin fields, variance/admission/factors against
the frozen CPU, actual projection/normal/RHS against the frozen deflated
operator, all three colored constants and near-constant signed fields, symmetry
and PSD where rounding permits, and clipping-support poison invariance including
3x3 admission spread. Include producing wrong-phase/projection/mask foils.
Separate numerical fidelity from reconstructed flat-noise and photo admission.
Use small≤128 source extents and≤7 sources initially. The author must expose
an API promptly; root alone schedules compilation/GPU execution.

Photo-review owns `export-originals.py` and `export-notes.md`: prepare a fresh,
read-only299-source native-u16 bridge using the already generic m61 exporter
identified in [input audit](../direct-cfa-forward-gpu/input-bridge-audit.md).
Do not execute it. Bind exe/source, exact original order/metadata receipts,
all source hashes before/after, header[0,0,4688,7032], exact byte counts and
native logs; use one decoder at a time and absent destinations. Preserve all
codes, record per-phase clipping/min/max, compare0/149/298 overlap against the
independent RawPy caches and disclose native-only extra columns. Cache files
are original unaligned u16, never developed RGB or aligned-frame volumes.

Root owns runners, all execution, full-image domain/development and later
release decisions. Initial mechanical jobs retain300s/1200CPU-seconds,
8GiB host/8GiB Torch limits and four CPU workers, with QPC authoritative timing.
Before any full fit, commission one complete weighted normal/RHS pass and its
actual memory/cost, inspect clipping coverage, and specify direct-RGB delivery.
A possible longer observational photo run is separate from production-speed
admission and needs an explicit cost-based root decision. Do not create the
large cache until that route has concrete working code.

## Prior work and mandatory limits

Root ran unified research search and mechanical prior-art check for `normal
equation streaming projection`; their broad-term M82/BUILD-GHOST/M91 hits are
not this operator. Targeted retained-source lookup found the current
band-residual/constant-deflation derivation, CGLS checks and independent failure
report, which were read. This is a continuation of those sources and the newly
measured GPU operator, not a new original mathematical claim. Old flat RGB/chroma
13.4045/18.6714 versus12.0919/10.1990 limits and64-step nonconvergence remain
failures. An actual complete photograph has not been made with this operator;
the user explicitly requires photographic evidence rather than stopping on
synthetic or local-crop results. No passing mechanical test promotes this path.

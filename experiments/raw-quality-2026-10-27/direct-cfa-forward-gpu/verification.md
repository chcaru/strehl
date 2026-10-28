# Independent measurement and cost-route verification

2026-10-27. **VERIFIED** source/receipt audit and light saved-array checks only.
Root executed the operator. This reviewer did not import the measurement
operator, compile CUDA, run a model/fit, decode RAW or create an image.

## Controls2: measurement equivalence demonstrated on the fixed population

The actual child argv, interpreter identity and environment are retained in
[invocation.json](../../../outputs/raw-quality-2026-10-27/direct-cfa-forward-controls-2/invocation.json).
It invokes the unchanged `controls.py --out` commission through Python3.12
with `-B -X faulthandler`. The [process receipt](../../../outputs/raw-quality-2026-10-27/direct-cfa-forward-controls-2/process.json)
records exit0,4.828s wall,8.578125s process-tree CPU,1,943,957,504B peak job
commitment, zero remaining processes, no termination and clean pipe completion.
Four Torch threads, float32, TF32 off and the RTX5090 are recorded. This small
test's resource use is not a full-source or workflow performance result.

Bound identities:

- Controls: `638c7391082b68774fc2581af014830f20dc6d1fee9e43a03b913046e1564938`.
- Plan: `6267ac696680fb38d4756f45d4eae24b7e5118aa7237aae58991803c20b89340`.
- Successful producer: `8328b11cecf710f0020e8dfc8e8ab68467301e32290ba204fc5f9d7ebc8c0d84`.
- Frozen CPU Measurement: `536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac`.
- Completion: `02c3596f63509ab6bc61d6bc1add3ed80fdf561f8be6e143d5d75a5e1352da8c`.
- Scientific receipt: `a98caf36f1eae913bc2e9a2bcee555b96ce732ee073c4ffb8bdec3b21b351841`.

All64 completion references, totalling1,014,393B, were freshly rehashed. Saved
CPU/GPU fields independently reproduce reported absolute maxima. The three
whole forward errors are0.001953125,0.001953125 and0.0029296875DN; maximum
normalized error is2.125e-7, below the predeclared1e-5 maximum bar. Whole-adjoint
maximum error is7.153e-7; the largest normalized phase-isolated adjoint error is
2.270e-7. Constants' largest absolute error is0.001953125DN. These values are
floating-point agreement measurements, not estimates of sensor noise.

All forward partitions are bit-identical to their whole GPU result. Saved sums
of the four separately produced physical-phase adjoints differ from the whole
adjoint by at most2.384e-7. Adjoint partitions and CPU/GPU dot products pass the
unchanged bars. Both green phases are separately represented. The actual
half-pixel-map foil has normalized maximum error about0.055; the R/B-map foil
about0.88. Both fail strongly. All six unsupported-footprint cases are refused
by both implementations, while valid zero fields return valid zero outputs.

All six runtime records report unchanged producer/CPU/DLL bindings and the same
PTX SHA `f5c6e06f1d1feed84c04260ffe43171c4347538b77665ee4ad120c7346cc0c1d`.
NVRTC12.8 targets compute120 with fmad/ftz disabled and precise division/sqrt.
Peak Torch allocation/reservation is125,440/2,097,152B, not whole-device memory.

Controls1 remains a compile failure: NVRTC could not locate `math.h`. Comparing
its preserved producer with the successful source confirms only that include
and its following blank line were removed. No arithmetic, fixture or tolerance
changed. The operator source uses the same coalesced nine-node row for forward
and atomic transpose, literal physical parity, current Torch context/stream and
globally indexed HWC addressing. Atomic transpose order is nondeterministic;
the demonstrated contract is numerical equivalence, not universal bit identity.

## Full-source cost source review

The frozen `cost.py` (SHA256
`2736571fc3646b6c0afe9bef3f087dae3f587ad9eb7a5dfbf2e6be3ab277cf0b`;
notes `a175b92430d6fe89240fe8dbc68fbdb1962e0478c6608c82bc75684ada9875f1`)
correctly inverts the held gauge as
`p_reference=C+A^-1*(p_source-C-2b)`. It retains all299 stored f64 map records,
including reference149's tiny nonidentity terms. Full unit-cell corners of all
sources determine one global latent domain, with four-pixel support margin;
the delivered photograph crop is not substituted for that domain. Original
integer RGGB phase is unchanged.

Source149 then source0 each receive a complete forward and transpose pass.
Thirty-seven strips,36 of height128 and a final80 rows, cover32,966,016 sites
per pass without overlap/gaps. Generated signed f32 fields exercise the cost
path; they are not photographs or RAW observations. Source geometry is held,
not independently established physical truth.

The retained capped CGLS performs two B and two B-transpose calls per iteration,
plus one initial transpose. Deflation adds four of each:132 whole-stack forward
and133 transpose calls for the nonconverged64-step path. The cost script records
that extrapolation as well as the explicitly hypothetical one-pair-per-step
floor. Primary practicality uses synchronized operator-call sums; generated
residuals, diagnostic reductions and journaling belong only to the separately
reported whole-loop scenario. Neither is a measured299-source solve. Compilation, initialization,
Haar/noise/projection work, source I/O, solver vector updates and delivery remain
outside that comparison. Adjoint accumulator zeroing is separately measured
before the pass timer; its exclusion from loop-only timing must remain explicit.

No source-level blocker was found for this separately bounded cost observation.
This audit does not release reconstruction or establish practical full-stack
cost. The earlier flat/chroma and convergence failures remain unchanged, and
the controls receipt correctly keeps photographic admission and quality claims
false.

## Timer-only repeat review

The first cost run completed all scheduled passes, but its strip-call timing
cannot support the planning decision. Root identified that this Python3.12
runtime's `monotonic` clock uses GetTickCount64 with15.625ms resolution, while
many calls are substantially shorter. The recorded4912/5553-second scenarios
must not be treated as reliable projections. Coverage and finite-output
evidence are separate from that timing defect.

Reviewed `cost-precise.py`, SHA256
`9c03e19ccff81337bb9f84ba47276bc232f2ee5c173d260cff714a25b770b6e9`.
Its source diff changes only the21 wall-interval calls from `monotonic` to
`perf_counter` and adds recorded clock information. Physical geometry, source
population/order, generated fields, rectangles, arithmetic, producer, pass
counts, summaries and extrapolation equations are unchanged. The old source
and result remain preserved. No extra reconstruction or quality experiment
is introduced.

The surrounding synchronized high-resolution intervals, not the unchanged
producer's internal coarse timing counters, must supply the new projection.
The root runner should require the recorded performance clock to be monotonic
and resolve at least1 microsecond before accepting that projection. This
review does not presume the repeated timing or planning outcome.

## Precise cost1: coverage passes; the frozen planning gate fails

**VERIFIED:** the [precise-run receipt](../../../outputs/raw-quality-2026-10-27/direct-cfa-forward-cost-precise-1/output/receipt.json)
is SHA256 `8858a1c5506c01161efad53249b338d1d52f70ff426cda1a917c3a127014dcea`;
[completion](../../../outputs/raw-quality-2026-10-27/direct-cfa-forward-cost-precise-1/completion.json)
is `40ea34e0e47841d412ae14c5d6d8dd192ec3a9f619f87bd1cfa55be445a71730`.
The actual `cost-precise.py --out` argv and Python identity are in
[invocation.json](../../../outputs/raw-quality-2026-10-27/direct-cfa-forward-cost-precise-1/invocation.json).
Thirty-five unique artifact/source bindings, totalling1,092,724B, were freshly
rehashed. Current producer8328b11c and CPU536aa094 match those bindings. Runtime
DLL bindings remain unchanged; PTX matches the commissioned f5c6e06f identity.

All four passes contain37 contiguous strips and32,966,016 sensels each, in
149-forward,149-adjoint,0-forward,0-adjoint order. All299 retained map bit tuples
match the held map, including the nonidentity149 tuple. The single global
domain is7109x4743 with reference origin(-34,-22). Producer counts76 launches
and65,934,080 sensels in EACH direction agree with two full passes plus two
32x32 warmups. No support refusals occurred. Finite summaries and complete
adjoint scans pass; seven-value checksums are not full-field equality proofs.

QueryPerformanceCounter reports100ns resolution, monotonic/nonadjustable. All
148 strip-call times are positive; their sums reproduce the recorded operator
times. The smallest call per pass is1.364,1.433,1.616 and1.655ms, explaining
why the old15.625ms clock was unsuitable.

| Geometry | A calls, seconds | A-transpose calls, seconds | Derived299*(132A+133At), seconds |
| --- | ---: | ---: | ---: |
| Source149 | 0.0703560 | 0.0755535 | 5781.3466 |
| Source0 | 0.0754586 | 0.0813413 | 6212.8995 |

**DERIVED:** both operator-call-only scenarios exceed the prospectively fixed
3600-second ceiling. This agrees with root's decision to close the naive port
of the unchanged64-step deflated solver. It is not a rejection of the GPU
measurement operator or all original-CFA reconstruction, and is not a measured
full-solver duration or a statistical timing bound. The exclusions documented
above remain; no RAW cache or inverse fit was executed.

The process exits0, is fully reaped without termination, and reports about3.20s
job wall,2.875s process-tree CPU and3,619,303,424B peak host job commitment.
Torch peaks are1,517,714,432B allocated and1,560,281,088B reserved, below8GiB;
driver/JIT memory is separately described. These generated-field cost results
carry no photographic-quality or noise-preservation claim.

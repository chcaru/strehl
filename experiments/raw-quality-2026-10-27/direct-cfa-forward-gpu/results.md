# Original-CFA measurement commissioning

2026-10-27. **No photographic improvement is claimed.** This checkpoint implements
the original-sensor measurement and its transpose on GPU. It neither reconstructs
a photograph nor resolves the earlier flat-chroma/convergence failures. The
complete V3 photographic comparison remains separately rejected in
[its report](../stackmff-v3-current/results.md).

## Commands and source identities

Root ran these exact commands from the worktree, with native exit codes captured
immediately. All outputs were fresh and outside the capture corpus.

```text
python -B -X faulthandler experiments/raw-quality-2026-10-27/direct-cfa-forward-gpu/run.py controls
python -B -X faulthandler experiments/raw-quality-2026-10-27/direct-cfa-forward-gpu/run.py controls --iteration 2
```

**MEASURED:** attempt1 exited1 in2.516s because NVRTC could not find `math.h`.
No kernel was executed. Its exact source is retained as
`outputs/raw-quality-2026-10-27/direct-cfa-forward-controls-1/measurement-gpu-failed.py`,
SHA256 `3a1df4ddaaeb8a3e877a0b3b25433cb378479f6a3b752c51338ed346870a0eb9`.
The sole repair removed that include and its following blank line; NVRTC
provides the used device math functions. Successful producer SHA256 is
`8328b11cecf710f0020e8dfc8e8ab68467301e32290ba204fc5f9d7ebc8c0d84`.
Control source remained `638c7391082b68774fc2581af014830f20dc6d1fee9e43a03b913046e1564938`;
no numerical bar was changed.

## Mechanical result and limitations

**MEASURED:** attempt2 completed all three geometries, flat constants first,
all four physical phases, structured forward/adjoint comparisons, adjoint dot
products and unequal rectangle partitions. Both actual wrong-coordinate and
wrong-channel foils failed the unchanged fidelity bars in every geometry;
all six unsupported-support cases were refused. Maximum structured forward
error was0.0029296875DN, normalized2.125e-7; maximum full adjoint error was
7.153e-7. These establish numerical operator agreement, not recovered detail.

**VERIFIED independently:** all64 completion artifacts (1,014,393bytes) were
rehashed, saved arrays reproduced the reported comparison errors/constants,
forward partitions were exactly equal, and phase-adjoint sums differed from
the complete adjoint by at most2.384e-7. The same kernel rows produce forward
and transpose; atomic adjoint accumulation is not promised bitwise repeatable.

**MEASURED:** terminal exit0,4.828s wall,8.578125CPU-seconds and
1,943,957,504bytes peak committed job memory. Tiny-control Torch peaks were
125,440bytes allocated and2,097,152bytes reserved; these do not predict full
memory use. RTX5090, Torch2.11.0+cu128, four intraop/one interop workers,
no TF32/autocast, precise f32 arithmetic and f64 geometry. Root limits were
300s wall,1200CPU-seconds,8GiB host and8GiB Torch allocation. Host observations
recorded4.4–10.1% CPU after the initial sampling row; timing was not exclusive.
Full invocation, source/runtime/PTX bindings, logs and original arrays are in
[controls2](../../../outputs/raw-quality-2026-10-27/direct-cfa-forward-controls-2/completion.json).

The model still assumes uniform unit-square sensor-cell integration; this is
not measured Sony response or an optical PSF. A faithful measurement operator
does not commission the noise/admission, global inverse, clipping treatment,
boundary completion or direct-RGB development. No RAW cache or reconstruction
was made under these controls. The [input audit](input-bridge-audit.md) records
the real7028-versus7032 active-width distinction and a reusable native-u16
export route without silently padding missing sensor samples.

## Full geometry cost checkpoint

The separate [cost brief](cost-brief.md) fixes two complete native source
geometries, all299-union latent support and a300s bound. Its prospective
planning ceiling is3600s for the unchanged64-step299-source solver projection,
using operator-call times alone. No fitting is automatically released by a
passing cost.

Root then ran:

```text
python -B -X faulthandler experiments/raw-quality-2026-10-27/direct-cfa-forward-gpu/run-cost.py
python -B -X faulthandler experiments/raw-quality-2026-10-27/direct-cfa-forward-gpu/run-cost-precise.py
```

**VERIFIED:** the first cost run completed all four source passes, but root
withheld its planning decision after seeing zero/quantized strip timings.
`time.get_clock_info` identified Python3.12 `monotonic` as GetTickCount64 with
15.625ms resolution; individual calls were much shorter. Those old timing
projections are not accepted. The second source changes only21 wall timing
calls to QueryPerformanceCounter and records both clocks. Its100ns resolution
and monotonic/nonadjustable properties are guarded by the root runner.
Completed sources and receipts from the first run remain unchanged.

**MEASURED:** the corrected cost run completed in3.203s with
3,619,303,424bytes peak committed job memory. It retained one4743x7109 global
latent field covering the union of all299 source footprints. Each of the four
passes covered all32,966,016 native sensor sites through37 rectangles. No RAW
photographs were read and no inverse was fit.

| Geometry | Forward operator seconds | Adjoint operator seconds | Instrumented forward loop | Instrumented adjoint loop |
| --- | --- | --- | --- | --- |
| source149 | 0.0703560 | 0.0755535 | 0.0878898 | 0.0981939 |
| source0 | 0.0754586 | 0.0813413 | 0.0924091 | 0.1044339 |

**DERIVED:** multiplying only synchronized operator-call sums by the inherited
132-forward/133-adjoint count and299 sources gives5781.35s and6212.90s,
respectively. Both exceed the prospectively fixed3600s planning ceiling.
These are two geometry scenarios, not a measured complete solver or a strict
lower bound. They exclude Haar/noise/admission, projection and solver arithmetic,
I/O, allocation, global accumulator zeroing, development and delivery. The
instrumented loop includes extra diagnostic work and is reported separately.

**VERIFIED independently:** all35 bound artifacts (1,092,724bytes), all299
literal map records, all148 complete-pass strip records, positive QPC call
times and their sums were checked. Runtime counts include two short warmups
in each direction. See [verification](verification.md) and the
[complete cost evidence](../../../outputs/raw-quality-2026-10-27/direct-cfa-forward-cost-precise-1/completion.json).

**Decision:** close the naive unchanged64-step full299 port before making its
large RAW cache. The GPU measurement itself is faithful and remains reusable.
This does not reject original-CFA reconstruction or authorize a new solver.
There is still no photographic improvement, production default change or
evidence that the known flat-chroma problem is solved.

# Independent software-noise reader: prospective implementation

**Source preparation only.** No import of the numerical reader, sampling,
encoding, moment computation or control execution occurred while this source
was written. Only standard-library AST parsing of its text was run. The
committed `next-noise-contract.md` at
`4e92e176d0cfae6dcdc9fedab3ff8f5d40f858c47eb0fcddbd14877d894d29f2`
supplies the population and every numerical acceptance limit. This file adds
no noise-law, accuracy, time or allocation bar.

The reader never imports `software-noise.py`, constructs a Generator, or
resamples a recorded tuple. Its caller provides the actual existing stage
Budget. Internal allocations use that object's preallocation and live-owner
checks, and persistence uses the same counted store. One current trace and
one preceding repeat feed per-site mean/M2 arrays for P, R, E, X and Q;
cross-frame comparisons retain two traces. No repeat or five-frame image
volume is constructed. Pair accumulators retain scalar sufficient statistics.
The declared 120 CPU / 240 wall / 32 MiB / 512 MiB caps include this work and
the final rereads; they are not estimates that this implementation will pass.

## Actual consumers and independent choices

`independent_key` computes the exact ASCII tuple and little-endian SHA-256
words with standard-library string/struct operations. The controller compares
these with both actual forwarded generator records before sampling. The
reader independently checks all saved keys, call signatures, typed PCG state
fields, hashes and replay relationships. It does not claim to independently
reproduce every bit-generator state without constructing the generator.

`read_array` hashes one bounded buffer, checks the NPY v1 AST dictionary for
duplicate keys and exact dtype/order/shape/payload extent **before** allocating
with the NPY loader. Deliberate nonfinite deterministic fixtures have an
explicit private parse mode; the ordinary reader must also reject each same
file. No nonfinite array is admitted to numerical statistics.

`read_trace` reconstructs consumed photo/read addends, E and pre-encoder DN
from the actual saved arrays and exceptional overrides, requiring their
actual hashes. It separately records nominal tuple/gain mismatches. Moment
checks use the consumed addends and actual encoder input, including the
black-clamped fault. The Q oracle uses floor, fractional part and integer
parity rather than the producer's `rint` call. Every actual Q code is checked.

Temporal variance uses Welford updates at each fixed photosite, denominator
63, followed by averaging the 3,072 sites within each CFA parity. Correlation
uses the exact registered pairs and ordinary centered Pearson after the
specified mean subtraction. Zero-photon correlations remain explicitly
undefined; every other zero denominator fails a healthy population. The
continuous-normal quantization oracle uses erfc-tail differences and the
registered finite-tail bound. Bright quantization uses the finite-sample
inequality, without an added-1/12 assumption.

All 18 temporal groups (four baselines, seven fault/restored pairs), 34
supplemental calls, 17 deterministic records and 5,000 distinct noisy payload
files are mandatory. The implementation retains all numerical group results
and requires each fault's **named** rejecting instrument. In particular the
correlated-read fault must retain marginal variance within 2% and have actual
horizontal correlation above .2, exactly as already written in the committed
destroyer table; the healthy correlation bar remains absolute correlation
at most .02. Covariance is reported directly. No statistic is substituted for
an unexecuted rejecting instrument.

## Reader commissioning through actual retained records

`read_commission` is the actual full entrypoint. Its explicit
`private_preflight=True` branch returns only
`PASS_PRIVATE_READER_PREFLIGHT_ONLY`; it cannot admit traces or substitute for
the full ordinary call. The controller must persist the actual ordinary
result before `run_reader_controls` begins. Controls require that completed
result's exact method, index and source association as their valid companion.

There are 36 fixed reader controls: 29 required rejections and seven valid or
restored checks. They cover missing/duplicate/reused record identity, omitted
actual reader source, bool work fields, incomplete status, a rehashed changed
Markdown contract, changed input/hash/frame identity, raw-normal hash,
override disposition, unreached observer, actual RNG call size, omitted key
component, wrong entropy byte order, bool PCG state, changed actual Q,
huge/object/Fortran/short/appended NPY inputs, duplicate NPY `descr`, duplicate
JSON keys, and all four missing exceptional overrides. The changed first
input binding exercises the actual **full** entrypoint; other complete-index
mutations exercise that same function's explicit preflight boundary. Actual
trace/parser companions are restored without additional draws.

Mutations are small files within the original counted package. Unchanged
arrays are referenced, not copied into whole parallel populations. Both
individual metadata/byte files and cumulative control outputs have the
registered bounds. A rejection is credited only when the intended reader
refusal occurs; an unrelated I/O, budget or other exception is not a passing
fault. Numerical fault populations are the original registered producer
calls, not new reader-generated noise.

`recheck_commission_files` rereads all 1,186 records, 5,000 actual payloads,
deterministic files, source dependencies, runtime record and actual runtime
file hashes. The full reader calls it before returning. The controller must
call it again after reader/control records and source snapshots are persisted,
then complete its post-terminal output/time checks. A numerical reader result
alone is not final controller authority.

Return schemas are `m194g-independent-software-noise-reader-v1` and
`m194g-independent-noise-reader-controls-v1`; their success statuses are
`PASS_SOFTWARE_NOISE_PRIVATE_TRACES` and
`PASS_INDEPENDENT_NOISE_READER_CONTROLS`. The controller stores each actual
result and a small wrapper binding both. This private commission provides no
physical calibration, full-float authority, intended-CFA admission, product
quality result or SOTA claim.

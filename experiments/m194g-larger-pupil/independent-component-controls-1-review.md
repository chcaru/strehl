# Independent private component controls: run 1 review

2026-09-07. **VERIFIED, bounded private-control pass; numerical comparison
remains uncommissioned.** Root executed the prospectively committed command
from `1f6db1d0` and reports an actual process exit of 0. This lane subsequently
read every deciding control record, rehashed its source snapshots and input
ledger, and checked the recorded invocation against the released command.
There was no second control run or full numerical-reader execution.

The actual result is `independent-component-controls-1/result.json`, 495347
bytes, SHA256
`258d5b9de1966a346581ac4329bd2fbdaecf83a2f904e74473e73c326b6dfce1`.
It reports `PASS_PRIVATE_COMPONENT_CONTROLS`, with **145/145 checks: 100
intended refusals and 45 valid companions**. The groups are 94 reader/payload,
36 resource and 15 entry controls. These are different checks of a finite
consumer contract, not 145 independent confirmations of the optical model.

## Actual boundaries exercised

`independent-component-controls.py::core_controls` re-chooses a 4-by-7 private
array and actual persisted NPY files. Scalar changes, diagnostic changes,
sum-preserving diagnostic column swaps, missing/duplicate/out-of-order sparse
indices, wrong endianness, nonfinite values, typed JSON errors and rehashed
NPY interpretation/extent changes all refuse. The numerical comparison
controls distinguish an individual maximum from an aggregate RMS, reject an
RMS failure despite every maximum passing, and keep a single method's RMS
from being diluted by other methods. The fault-power equality control refuses:
the declared fault must differ by strictly more than 0.004 e from both
references. Those toy values commission the comparison arithmetic only.

`author_fixture_controls` additionally consumes the externally pinned genuine
author result `358aebe2…080e`. Its valid companion reopens all 331 persisted
call records, obtaining the 299 ordinary rows, and all **60 actual 9-by-6
observer frame packages**. `read_observers` checks four numerical payloads per
frame, complete branch/sparse coverage and the declared off/count/placebo/
reverse traversal conditions. Thus the 3240 scalar sites are four executions
of 15 frame/arm combinations; they are not 3240 independent scene samples.
The same-method scalar, branch, sparse index and diagnostic bytes agree across
the four executions. Numerical agreement with an independent optical method
does not follow from this byte identity.

Private relocated copies of one genuine frame then test coherently rehashed
schema, terminal status, source digest, boolean/float branch aliases, completed
counts, frame index, scene phase, arm, traversal digest, duplicate array path,
diagnostic interpretation and cumulative-work changes. All refuse at their
intended boundaries; the unchanged relocated and restored companions pass.
Missing observer executions and a duplicated frame replacing a required frame
also refuse. Through the actual independently authored `read_array`, a
rehashed NPY header claiming shape `(2147483647,2147483647)` with only 15
samples refuses with `bounded NPY header/extent mismatch`; the real 3-by-5
companion passes before and after it. No huge array was allocated.

`resource_controls` exercises the actual author and reference resource APIs
with injected clocks and modest allocations. CPU 600 and wall 1200 equality
pass, their just-over companions refuse; the author 16000000-point,
2400000000-node and 32768-pair equalities pass and one more refuses. The
reference 30000000-integrand equality and one-over pair behave likewise.
Author cumulative work survives frame, integrator and observer changes. An
actual analytic foreground call creates one cache entry, its cached companion
passes at clock equality, and the cache path refuses after the clock crosses
the limit. This last control contains an actual analytic call; it is not a
full-image render or an accuracy claim about that scalar.

Both live backing-owner ledgers accept a deliberately reduced 1024-byte
boundary, deduplicate aliases and refuse one extra live byte. Both refuse a
second live scalar frame, then accept the companion after the first owner is
released. These observations concern explicitly tracked ndarray storage and
clock enforcement, not hidden temporaries, process RSS, or a measured
600-second workload.

`entry_controls` rehashes private release records and tests the actual author
entry validator. Omitted loader/model/controller dependencies, false source
hash/length, duplicate inputs, changed input length, unreleased invocation,
wrong external pin and invalid schema/scope all refuse. The actual private
`run()` capture-failure control returns 1 with zero rows and preserves both
the original failure and the secondary final-source capture error. Its
`UNCOMMISSIONED_NUMERICS` line in the launch log is expected evidence of that
control, not a failure of the outer command and not a new failed optical run.

Every intended refusal was checked against its declared exception class and
message boundary. This review independently matched all 100 saved error
strings to those expectations; an unrelated `TypeError` or harness exception
would not count as a successful refusal.

## Source and command evidence

The release is `independent-component-controls-release-1.json`, SHA256
`7cc77389df8a55f016e73b2c584a176b72cdf3fbaccc0f3a19a4f4283893e0a9`.
Its 27 bindings match the actual command's source map, all 27 saved snapshots,
current file bytes, and the corresponding raw Git blobs at `1f6db1d0`.
All 36 entries in the outer read ledger still match their recorded hash and
byte count. That ledger is the outer command's observed inputs; the actual
author-payload reader also performs its own final before/after read check.
It should not be described as a 36-file inventory of the author package.

The frozen reader is
`cd69c42a223ce3f859b5f546729234f433a134282fc7e401711ec265265a23a3`;
the frozen controls are
`885f40c88b031e5323de8cbcc98ba3c430353c47ab8b3e64930975502b45619a`.
No source fixes followed this first control run. Root's separately reviewed
execution and this lane's artifact read are not two independent numerical
implementations.

The exact released and recorded command, from the repository root, is:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' `
  -X utf8 -X faulthandler `
  -X pycache_prefix=experiments/m194g-larger-pupil/work/cache-independent-component-controls-1 `
  experiments/m194g-larger-pupil/independent-component-controls.py `
  --output experiments/m194g-larger-pupil/independent-component-controls-1 `
  --execution-release experiments/m194g-larger-pupil/independent-component-controls-release-1.json `
  --execution-release-sha256 7cc77389df8a55f016e73b2c584a176b72cdf3fbaccc0f3a19a4f4283893e0a9 `
  --author-fixture experiments/m194g-larger-pupil/author-components-1/result.json `
  --author-fixture-sha256 358aebe2292a8c1aa920763481cae36ce43ebe2d756a5d2e0b8e8fde20fb080e
```

The process recorded Python 3.12.10, NumPy 2.4.4 and all four declared numerical
thread variables equal to `2`. Its 5.625 CPU / 6.954000000027008 wall seconds
include private clock injections inside the tested modules and are merely
outer elapsed observations, not a performance bar. The original result has
`exception=null`, `finalization_error=null`, and `sources_unchanged=true`.

`independent-component-controls-1-review.json` preserves this review's 27
source comparisons, 36 input rehashes, all 145 control/error-boundary readings
and exact-command comparison. Reads used `Get-Content -Raw | ConvertFrom-Json`
and `Get-FileHash`; source provenance additionally used `git hash-object
--no-filters` and `git rev-parse 1f6db1d0:<path>`, retaining exact exit codes.
The first display attempt selected properties directly from an ordered
hashtable and printed null fields; reopening the already written JSON showed
the complete true-valued comparisons. This was a display-only correction,
not a changed test result or rerun.

## Admission remaining

The actual independent reference still has **28 refused ordinary values
across 14 fixed IDs**. This run neither fabricates replacements nor invokes
the complete reader against a pretend successful reference. The full reader's
terminal admission path, all cross-method scalar/reference/oracle/fault
comparisons and any future all-image release remain separate work. The
current disposition is a commissioned private reader/resource/entry boundary
and actual observer-payload consistency; it is not complete numerical-model,
physical-optics, production-quality or SOTA admission.

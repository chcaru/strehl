# M194f independent driver review

2026-09-07. The corrected driver's32 private controls pass. These use stubbed
child-process calls and a private source tree; they do not compile code, run
an executable from a fixture record, render an image or grant optical authority.
The actual intended build and eleven TIFFs require their own source-bound runs.

## Retained actual first failures

The first complete22-control run exited1 with16 passes against
`consumer-run.py` SHA
`15a3a27c9ee1a69e838086fa807c90cdc45ee0757fbe9dc35c3b001c1f198715`.
Both unchanged valid companions passed. Six negative inputs were accepted:

- A copied executable's declared byte count differed from its actual length.
- The recorded compiler artifact had a false digest or false byte count.
- `copy_matches_compiler_artifact=false` accompanied a passing build record.
- A libtest summary reported11 passed tests, rather than the required one.
- Ordinary text contained `1 passed; 0 failed` without a libtest summary.

The old substring test accepted the last two. Invocation checked the copied
file's digest but did not consume the contradictory compiler/copy metadata.
These are observed private API acceptance defects, not hypothetical source
review findings. The source snapshots, complete child-call arguments, private
records and logs remain in `independent-driver-1/`; its result SHA is
`924e06d271ca796176dc9fcaa7a5bc5b8d62554033f70d17c0cfa0cb0e68694c`.

## Corrected source and independent re-choice

Root corrected the driver to SHA
`cafb3a1c6561b3b076964178fe3636f0e2f8c7c611b6cfb033c9b836ef562dfe`.
It now checks both actual executable files, strict file-reference types and
lengths, the compiler message association, explicit build/copy admission and
one anchored complete libtest success summary.

The valid stub was updated to supply a truthful compiler message and complete
libtest elapsed-time suffix required by the corrected contract. The11-test
negative received the same complete suffix, so its refusal is specifically
powered by the test count. The source-change control now switches after the
actual stub child invocation, independently of how many times the driver calls
its source-list helper. The original failures were not overwritten.

The32-check rerun passes all original choices plus ten additional choices:
boolean/floating executable lengths, an unknown file-reference field,
boolean exit status, absent rebuild, wrong compiler target/profile/executable,
one pass plus one ignored test, and duplicate success summaries. It also
exercises hostile-environment clearing, explicit nested Rust include closure,
a missing included source, current versus omitted source bindings, wrong
external build pins, missing results and actual after-child source/driver/file
changes. The two valid companion invocations remain green.

The complete result is `independent-driver-2/result.json`, SHA
`1b3c6d48c1b4cf8d0ba8e697ab3c235a698dc2a1ac07255e672da1de110776c7`.
Both driver and independent-control source hashes are unchanged before/after.
The independent control source is
`105792a73b3a707119bd1f251db562c8ec4aa690a8bf363fc63e0f38399d689a`.

```powershell
python -B -X faulthandler -X pycache_prefix=experiments/m194f-production-bridge/work/independent-driver-cache-1 experiments/m194f-production-bridge/independent-driver-controls.py --output experiments/m194f-production-bridge/independent-driver-1 *> experiments/m194f-production-bridge/independent-driver-1.log
python -B -X faulthandler -X pycache_prefix=experiments/m194f-production-bridge/work/independent-driver-cache-2 experiments/m194f-production-bridge/independent-driver-controls.py --output experiments/m194f-production-bridge/independent-driver-2 *> experiments/m194f-production-bridge/independent-driver-2.log
```

The first command's exact exit was1; the second's was0. Each has a distinct
cache/output directory and retained invocation/source record. The include
check is scoped to this repository's explicit include forms, not a general
Rust parser. These controls do not authenticate fully fabricated telemetry or
prove operating-system race freedom.

## Amendment1 refresh

After the prospective amendment commit `b0b55909`, the same32 controls pass
against consumer driver
`2dad7d6699492f17eb8610820763fad73f54a06b2d1f358c1c765ee4f553310b`.
The valid fixture now explicitly supplies `wb_mode="baseline"`; its recorded
child environment contains `STREHL_M194F_WB_MODE=baseline` and exposure0.
The only control-source change is that truthful new argument, giving SHA
`e1496e9de80c8a81a7a94d3b5b255ab3fca2c73a749d27333889badaea503758`.
Mode-specific argument/CLI cases are Curie's separate bounded launcher check.

```powershell
python -B -X faulthandler -X pycache_prefix=experiments/m194f-production-bridge/work/independent-driver-cache-3 experiments/m194f-production-bridge/independent-driver-controls.py --output experiments/m194f-production-bridge/independent-driver-3 *> experiments/m194f-production-bridge/independent-driver-3.log
```

Exit0,32/32, source before/after identical. Result SHA:
`6197bee8828dfd454bf71a8c82b334d23a4df8eecad68636d51e09cfb443040a`.
Earlier failures and source snapshots remain unchanged. These are stubbed
driver-boundary controls, not a production render or exposure semantic test.

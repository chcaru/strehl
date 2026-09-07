# Independent delivered-file instrument

2026-09-07, Zeno. `independent-reader-controls-1/result.json` is
**PASS_READER_INSTRUMENT_ONLY, 59/59**; SHA256
`f61e7b7990559e6368a676b70b16d1174c26a8b969fc9f56ad9403a5ffe9efc4`.
This run preceded this lane's first M194f product-TIFF read. It grants no
integration or model authority. Source snapshots and all synthetic TIFFs,
including malformed files, are retained under that run directory.

The bounded direct classic-TIFF parser is `independent-reader.py`, SHA256
`3fbaf526776fc85042861e1e7a90c06664c43519cef20d12310a67efd8eaff2d`.
The independent commissioning driver is `independent-reader-controls.py`,
SHA256 `9e1a065d2dd193b14996591304f2c21a8ead0a0046d97b635c644ce95aee0256`.
Its prospective design SHA256 is
`4828397cb0e5af0ed7477b8ca1406f610663a71a4172ae9a4d35f76cd3c9ab2a`.
All four recorded sources, including the root's clarified preregistration,
were unchanged through the run. No failed first run was hidden: the first
instrument run completed all cases successfully.

Exact original invocation, from the repository root in PowerShell:

```powershell
$env:OMP_NUM_THREADS='2'
$env:OPENBLAS_NUM_THREADS='2'
$env:MKL_NUM_THREADS='2'
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 -X pycache_prefix=experiments/m194f-production-bridge/work/cache-reader-controls-1 experiments/m194f-production-bridge/independent-reader-controls.py --out experiments/m194f-production-bridge/independent-reader-controls-1
```

Runtime: Python3.12.10 AMD64, NumPy2.4.4, tifffile2026.5.2, Windows11
10.0.26200. One Python process; library thread limits2. Recorded measured
body wall0.1462024s and process CPU0.09375s are execution accounting, not
performance claims. `orig_argv`, executable and xoptions include the actual
fresh-cache prefix, not merely `sys.argv`.

Constant passed first, max0.102357DN; affine max0.111464DN on all80 fixed
sites with represented f32 WB, below the unchanged .25DN bar. These are
synthetic quantizer/parser controls, not product interpolation results.
Both endian representations and single/multiple strips agree exactly with
tifffile's separately decoded samples. Twenty-five malformed/tag/hash/shape
controls reject through the actual reader. Twelve mapping, parity, channel,
WB and black-subtraction destroyers fail the actual value oracle. The smallest
of those maxima exceeds40DN, so the tolerance is not marginally powered.
A correctly rehashed, structurally valid TIFF with one changed red sample
passes parsing but fails the value oracle at22.56298DN.

The synthetic +64DN green companion gives63.89160DN after quantization;
the exact null and saturation controls refuse. The strict-less counts and
rank codes match their independently enumerated declared rows. Wrong ties,
red/blue luma, dropped duplicate200, wrong scaling, absent/moved sentinel,
and a corrupted reached-zero companion refuse. These rank controls pass
arrays to the actual final `rank_check`, which is distinct from TIFF parsing;
the valid Gray files pass both stages. The separately re-chosen synthetic
sentinel is linear index53, while actual intended component output must keep
root's preregistered index0 and reached-zero index1. No exact rank is inferred
from a genuine demosaiced RGB image.

The mathematical oracle does not fit a surface to samples or import the
production MHC stencil. Affine preservation is the declared bounded API
assumption that actual product outputs will still have to satisfy. This
instrument can reject a coordinate/value or writer error but cannot establish
optical fidelity, real-noise calibration, or the accuracy of a confidence score.

## Final record-adapter commissioning

`independent-record-controls-1/result.json` passed41 cases, SHA256
`5a871425d592a6524f692c81b3ea39cf86f9c6c22397bf4914c7b10a4f72ea4e`.
These call the actual final `verify_private` through synthetic TIFF records
and the actual plan checker. They cover all five private files, raw counts,
the fixed actual-population sentinel0/zero1, and coordinate/noise/normalization
contract faults. Correctly rehashed wrong RGB/Gray payloads fail the actual
oracle, rather than merely a stale hash.

The root finalized its wrapper schema while the bridge was still compiling.
An additive prospective wrapper group brought the count to56 in
`independent-record-controls-2/result.json`, SHA256
`3bc5f9b975b1cdd5e616b5367ea99a0ee255c23633ead333bf09fd0e01bd9e74`.
That run's before/after fixture dictionaries aliased each other: mutations
rejected, but the after cases also modified before. It is retained as limited
power evidence. This was a fixture issue found in our own audit, not a product
failure. Separate copies repaired only the fixture; no checker or numerical
bar changed. The corrected repetition is **PASS_RECORD_INSTRUMENT_ONLY,56/56**,
`independent-record-controls-3/result.json`, SHA256
`11797eb9727c735927ba7df7c2e796c49e3f94a96d3cc557e80703825a66e2a1`.
The isolated after controls now refuse specifically on their after boundary.

All three runs used the same interpreter and thread environment recorded
above, with exact invocations:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 -X pycache_prefix=experiments/m194f-production-bridge/work/cache-record-controls-1 experiments/m194f-production-bridge/independent-record-controls.py --out experiments/m194f-production-bridge/independent-record-controls-1
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 -X pycache_prefix=experiments/m194f-production-bridge/work/cache-record-controls-2 experiments/m194f-production-bridge/independent-record-controls.py --out experiments/m194f-production-bridge/independent-record-controls-2
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 -X pycache_prefix=experiments/m194f-production-bridge/work/cache-record-controls-3 experiments/m194f-production-bridge/independent-record-controls.py --out experiments/m194f-production-bridge/independent-record-controls-3
```

Each preserves exact `orig_argv`, snapshots and before/after hashes. The final
reader source is `independent-verify.py`, SHA256
`658b9aaf2453163b519e7d2256c9bff57abd47c33529567547c4dd8c93bacee5`.
The56-case record driver SHA256 is
`ab23fef9360e4a5956bf39c1d2bcbc7be3da9c9cc54673c1c24d27c88dfe5ea7`.
The synthetic wrapper log explicitly says it is not an executed test and
does not grant compiler authority. The real run still requires root's external
index/build hashes and actual copied compiler artifact, source maps and logs.

## Actual build and private-stage reads

Root supplied build3 SHA256
`69a8979821c074d247514f1deae3fb38dce3b8246013a19dc2f9beb8eceb7fcc`.
The first real preflight passed, `independent-build-preflight-1/result.json`
SHA256 `ab6fe03ce9dd1da8300d6b09f97207df36e6829d0e1cee869286b21c68e2a900`.
This checks109 current including sources, the visible compiler message/log,
and identical original/copied executable SHA256
`582ad20f937782abca6f90725e468a7d30cba0a783b33213705ba9d06a97a3a7`.

Root then supplied private-population-1-command.json SHA256
`f933147d7949623beb5a25b6fcff56df7ce722689162eebbf212961a374f0d3e`.
The first actual private read failed before reading TIFF samples:
`independent-private-read-1/result.json`, SHA256
`48c7b2613d802901b1cc890b48d444c0444566ca1fc1a9fadf279fd65d837f71`.
Rust canonicalized its path with Windows' local-drive extended prefix, while
the Python containment check compared against ordinary `C:\` spelling. This
is an independent reader compatibility failure, not product or value evidence.
The retained prospective correction normalizes that specific prefix and then
keeps resolution/containment checks. Extended UNC/device and outside-root
paths still refuse. The parser/quantizer/80-site bars did not change.

The56 record controls plus five path companions/faults passed61/61 in
`independent-record-controls-4/result.json`, SHA256
`264e225227a799d923589bc69b4558e95c537d61612c55a41f5a78fbbdfd4f63`.
No59-case parser rerun was needed: its exact bytes remained unchanged.
The unchanged actual five TIFFs then passed in
`independent-private-read-2/result.json`, SHA256
`03e95d508ca3e6c9671b191865ddc2ecdb2024e5e1709d342dc55012e0ef09c1`.

Actual constant max error0.1023560874DN; actual affine max0.1114633382DN on
each complete80-site population, below fixed.25DN. Actual all-copy green
mutation raises the declared output site63.89159991DN, above fixed63.5DN
without saturation. Independently read raw128-element counts and both actual
128-sample Gray rasters match exactly, including actual sentinel0 and
reached-zero1. All source/input/build/wrapper bindings remain valid. These
are **MEASURED/VERIFIED private production component results**, still not the
whole eleven-file bridge or an image-quality claim.

Exact invocations (same executable/thread settings as above):

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 -X pycache_prefix=experiments/m194f-production-bridge/work/cache-build-preflight-1 experiments/m194f-production-bridge/independent-stage-read.py --build experiments/m194f-production-bridge/build-3.json --build-sha256 69a8979821c074d247514f1deae3fb38dce3b8246013a19dc2f9beb8eceb7fcc --out experiments/m194f-production-bridge/independent-build-preflight-1
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 -X pycache_prefix=experiments/m194f-production-bridge/work/cache-private-read-1 experiments/m194f-production-bridge/independent-stage-read.py --build experiments/m194f-production-bridge/build-3.json --build-sha256 69a8979821c074d247514f1deae3fb38dce3b8246013a19dc2f9beb8eceb7fcc --private-command experiments/m194f-production-bridge/private-population-1-command.json --private-command-sha256 f933147d7949623beb5a25b6fcff56df7ce722689162eebbf212961a374f0d3e --out experiments/m194f-production-bridge/independent-private-read-1
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 -X pycache_prefix=experiments/m194f-production-bridge/work/cache-record-controls-4 experiments/m194f-production-bridge/independent-record-controls.py --out experiments/m194f-production-bridge/independent-record-controls-4
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 -X pycache_prefix=experiments/m194f-production-bridge/work/cache-private-read-2 experiments/m194f-production-bridge/independent-stage-read.py --build experiments/m194f-production-bridge/build-3.json --build-sha256 69a8979821c074d247514f1deae3fb38dce3b8246013a19dc2f9beb8eceb7fcc --private-command experiments/m194f-production-bridge/private-population-1-command.json --private-command-sha256 f933147d7949623beb5a25b6fcff56df7ce722689162eebbf212961a374f0d3e --out experiments/m194f-production-bridge/independent-private-read-2
```

## Registered WB replacement

The first intended genuine population later stopped at the original fifth
exposure arm. CameraLinear correctly refuses that viewing setting; it never
produced a completed index. The private5 results above are still valid
historical component results, but are not spliced into the replacement run.
Root committed amendment1 and both independent design reviews at `b0b55909`
before releasing implementation. `independent-wb-amendment-review.md` records
the rejected all-pixel interpretation, the observed-site one-code derivation,
and the fixed independently chosen instrument population. A fresh complete11
is required, with prepared red-only WB replacing exposure, all exposure0 and
source-frame WB unchanged.

`independent-wb-controls-1/result.json` passed21/21, SHA256
`3c1adb15e67d8a08ccbfba6cfa1801248bb1449d5b231fe2849edd5a6dc363bf`.
It calls the actual amended `wb_check` on22x18 code ramps at both an unequal
even origin and an odd-x origin. Each has99 sites in each CFA parity. Both
one-code residual endpoints pass; a two-code error, either observed-green
phase, observed-blue change, wrong red gain/channel, zero/clipping, missing
parity, wrong offset, empty extent and amplitude/increase faults refuse.
Deliberate interpolated movement passes and is reported without a numerical
bar. This commissions a delivered-value checker, not MHC optics.

The fixed61 record controls and seven explicit WB/old-exposure contract
controls passed68/68 in `independent-record-controls-5/result.json`, SHA256
`eb8530cc9b7d2a8552fde585bb1c137603c5d98a0b566c3849666c6fcb8a9732`.
The valid red prepared-WB plan passes; stale prepared WB/mode, changed frame
WB, doubled green, exposure1 and unknown mode refuse. Original59 TIFF parser
and80-site math remain byte-identical. Exact invocations with the same thread
limits and Python runtime:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 -X pycache_prefix=experiments/m194f-production-bridge/work/cache-wb-controls-1 experiments/m194f-production-bridge/independent-wb-controls.py --out experiments/m194f-production-bridge/independent-wb-controls-1
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 -X pycache_prefix=experiments/m194f-production-bridge/work/cache-record-controls-5 experiments/m194f-production-bridge/independent-record-controls.py --out experiments/m194f-production-bridge/independent-record-controls-5
```

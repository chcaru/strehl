# M194f independent delivered-file result

2026-09-07, Zeno. **PASS_DELIVERED_TIFF_VALUES** for all eleven fresh outputs,
on the registered amendment1 population. Result:
`independent-delivered-read-1/result.json`, SHA256
`87ecaec21d5e2a927660d26fe53bb31b7e7bcfbd4ac3a342dbb6b163f40ef8cf`.
The result is a bounded production integration commission. It does not measure
SOTA quality, optical confidence, noise suppression, occlusion-halo quality,
capture calibration, alignment accuracy or production performance.

## Authority, source and instrument

The externally supplied completed index is
`production-population-2/run-index.json`, SHA256
`29a30879638f4198b3ec02a09d2120d33d5b713ae357c6d2aeb5cb4dcc1bfc2c`.
Build4 SHA256 is
`b1930156c50817df7d801f3ff6585fb9f6b965f047adfdcc61e8520192c362bd`.
The actual compiler artifact and copied executable both hash to
`9733e99f5571eb9fca51c21b0da7a5ea76d7079c2663d78b3c81dc470da13bbf`,
11,393,024bytes. The reader checked their actual bytes, the compiler's actual
message/log with visible rebuild,109 including source bindings, command and
plan associations, current source/driver hashes, and the six actual independent
input results behind the focused seven-test record. It checked the actual
individual check booleans/counts, not just a parent PASS string. Socrates owns
those independently chosen source/input/MHC tests; this lane consumes their
bound terminal result rather than claiming their implementation as its own.

The TIFF parser was written independently with bounded classic-TIFF IFD/strip
reads. It does not use authored pixel summaries as samples. All reported
pixels, full-file hashes, canonical little-endian sample hashes, metadata,
orientation, channels and ICC/transfer disposition were re-read from actual
files. tifffile was used only for synthetic commissioning generation and a
cross-reader; it is not the final actual-TIFF decoder. The closed reader is
scoped to this uncompressed RGB16/plain Gray16 writer format, not arbitrary
TIFF compatibility.

| Instrument | Terminal result | Count |
| --- | --- | ---: |
| Direct TIFF parser, constant first, mapping/color/rank destroyers | independent-reader-controls-1 |59/59 |
| Final record/plan/wrapper, native Windows-path and amended WB settings | independent-record-controls-5 |68/68 |
| New observed-channel WB predicate, independently chosen22x18/parity fixtures | independent-wb-controls-1 |21/21 |

Full hashes, exact commands, first failures and corrective scope are in
`independent-reader-evidence.md` and each source snapshot/result. The final
reader is `independent-verify.py`, SHA256
`cc7013c2af20f9da46e75f5078217d59c7b5063e3616f7a064ce19fdb29d0468`.
The direct TIFF/80-site/rank oracle source remains
`3fbaf526776fc85042861e1e7a90c06664c43519cef20d12310a67efd8eaff2d`.
No sources changed during the final read. The five new private images passed
their separate preflight before the genuine population was launched:
`independent-private-read-3/result.json`, SHA256
`a04324e5dd3e94e4478bd9a5abda073a2379b97829cfab651a879af91c404446`.
The final reader then re-read those same five new files as part of all eleven.

## Actual delivered evidence

The genuine input uses its actual computed crop: native offset(10,8),
44x34 RGB output,22x17 confidence quad grid. The recorded geometry and
complete file extents agree. There is one Laplacian band plus the base and
zero measured-floor bands; the existing fixed-beta fallback remains the
declared consumer behavior. No small-fixture result establishes a larger
three-band behavior.

Baseline off/count/placebo and confidence-count RGB files are byte-identical,
SHA256 `f6485b77f63a45dcd1a69707d141fde845a5de557713bbf0a3e96f40df74f65a`.
Their entire decoded sample arrays also agree. Observer success counts and
hook witnesses match the committed mode: baseline count one per frame,
confidence count two per frame, off/placebo collected counters zero, with
the required off/count/placebo hook counts. The auxiliary Gray file contains
only{0,400,800}, no unseen sentinel, on the actual complete22x17 grid. These
codes are input-rank centrality, not calibrated optical confidence.

The red-WB replacement RGB SHA256 is
`66426fa37cd5a7b2f59ec206221c85e542b7a008ddd32d28ea6725d4920867f5`.
All374 observed red sites are positive and unclipped. Baseline codes range
8779..18482, changed codes17558..36964; every site increases, and the signed
red doubling residual is−1..1code, satisfying the fixed one-code bar. All374
G1,374 G2 and374 observed blue sites are exactly unchanged.

Interpolated components were deliberately reported without a scaling or
identity bar. All1122 interpolated R components change, maximum movement
18436codes. Of748 interpolated G components,374 change, maximum1229codes;
of1122 interpolated B components,374 change, maximum1843codes. This observed
movement is consistent with the source-derived reason the initial all-pixel
identity proposal was rejected prospectively. It is not an optical-error or
quality measurement. The sampled-site comparison alone cannot establish WB
ordering; the independently run non-affine MHC component witness addresses
the ordering distinction that constant/affine fields cannot express.

The private unequal crop stays(3,5,24,16)quad, corresponding to native
offset(6,10) and48x32 RGB. Independently predicted constant and affine values
pass at all80 fixed sites and all three channels, with maximum errors
0.1023560874DN and0.1114633382DN respectively, below the unchanged.25DN bar.
The all-copy green-site mutation raises output(23,16) by63.89159991DN,
above unchanged63.5DN, without clipping. These are measured software values
against a source-independent analytic field; no optical authority attaches
to the private scene.

Both private16x8 Gray rasters match all128 expected samples exactly. The
actual below/seen arrays also match independently enumerated strict-less
counts, so centrality's code symmetry is not mistaken for unique rank
recovery. The second map has65535 only at the intentionally unseen index0;
the reached-zero companion at index1 remains0. It is a writer-sentinel
component test, not observed missing optical coverage.

## Failures and limits retained

The original fifth exposure arm was unsupported on CameraLinear and refused.
Its partial population1 has no completed index and is not spliced into this
pass. Root's first proposed repair incorrectly expected all-pixel channel
identity/scaling; independent source review rejected that before a WB trial.
Amendment1 was committed before implementation and the eleven outputs were
rerun under one new build. Uniform WB rescaling was also explicitly rejected.

Our first private read refused Rust's extended local-drive Windows path
spelling before any TIFF sample read. The narrow path correction retained
containment and added outside-root/UNC refusal controls. Our earlier wrapper
fixture also aliased before/after dictionaries; its faults rejected but did
not isolate the claimed boundary. Separate copies repaired that fixture, and
both earlier records remain. No numerical tolerance, original input,
production policy or measurement writer was changed to obtain this result.

This instrument can still be fooled by errors outside its declared field:
interpolated WB behavior is not scored, a private affine field cannot express
occlusion, centrality is not optical confidence, and the small fixture cannot
commission the larger band-support/noise population. It verifies an actual
consumer path that a later separately registered quality experiment may use.

## Reproduction

Working directory is the repository root. Python3.12.10 AMD64, NumPy2.4.4,
Windows11. This exact original invocation is also preserved verbatim as
`orig_argv`; the final run has a fresh cache prefix and one Python process
with library thread limits2. Recorded body wall0.1918801s/processCPU0.1875s
is execution accounting only, not a performance claim.

```powershell
$env:OMP_NUM_THREADS='2'
$env:OPENBLAS_NUM_THREADS='2'
$env:MKL_NUM_THREADS='2'
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 -X pycache_prefix=experiments/m194f-production-bridge/work/cache-private-read-3 experiments/m194f-production-bridge/independent-stage-read.py --build experiments/m194f-production-bridge/build-4.json --build-sha256 b1930156c50817df7d801f3ff6585fb9f6b965f047adfdcc61e8520192c362bd --private-command experiments/m194f-production-bridge/private-population-2-command.json --private-command-sha256 8a96ae17ea10781c962005a2665b95959c872bd8a48a9564221db7b56fd1294a --out experiments/m194f-production-bridge/independent-private-read-3
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 -X pycache_prefix=experiments/m194f-production-bridge/work/cache-delivered-read-1 experiments/m194f-production-bridge/independent-verify.py --index experiments/m194f-production-bridge/production-population-2/run-index.json --index-sha256 29a30879638f4198b3ec02a09d2120d33d5b713ae357c6d2aeb5cb4dcc1bfc2c --build-sha256 b1930156c50817df7d801f3ff6585fb9f6b965f047adfdcc61e8520192c362bd --reader-controls experiments/m194f-production-bridge/independent-reader-controls-1/result.json --reader-controls-sha256 f61e7b7990559e6368a676b70b16d1174c26a8b969fc9f56ad9403a5ffe9efc4 --out experiments/m194f-production-bridge/independent-delivered-read-1
```

Use new output/cache names for a repeat; original result directories are
immutable evidence. No additional product run is required for this readout.

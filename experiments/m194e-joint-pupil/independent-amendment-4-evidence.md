# Amendment4 independent execution evidence

2026-09-07. Execution follows committed design/review/release `d32bd33a` and
the author's explicit numerical source freeze. No test or parameter trial
preceded that release. The immutable independent reference source and arrays
were not changed or rerendered. No full fifteen-array result or CFA authority
is asserted by this report.

The numerical subject is model SHA
`a74cd9bd61ea2f717a185e86f725b5ed192431056a447581db0f8562cf9f70b8`
and renderer SHA
`487c1727ca3aab05dd66a7056fb368712ccaabbbe604818fdc8b47eda77b6e97`.
Each actual numerical control copied these bytes and the applicable independent
sources/designs into its new output directory, then imported that snapshot.
All before/after source checks pass. Historical sources/results remain intact.

## Results and actual power

| Actual result path | Checks | Status | SHA-256 |
| --- | ---: | --- | --- |
| independent-target-controls-1/result.json | 62 | PASS_TARGET_MASS_COMPONENTS_ONLY | c94c6c8a6222d68406eea8cd4c39fa4f70fe2771e0662a74b87a721e9910993b |
| independent-author-api-6/result.json | 31+336 | PASS_AUTHOR_API_ONLY | 466c380788d3ce726d3cc91f02da1c7addde71eb3afd02eecd477058d7832f9d |
| independent-map-controls-3/result.json | 400 | PASS_MAP_COMPONENTS_ONLY | 44aa1c841eed2fff3057c4351c7bf054eb9c55a9cb67d420bb4f8be66ae74245 |
| independent-allocation-controls-4/result.json | 62 | PASS_ALLOCATION_COMPONENTS_ONLY | 2b67e94226da7cf0a09d6378ea180c9fad4125c12b7aa54672503dcf4a68ff04 |
| independent-observer-4/result.json | 32 | PASS_OBSERVER_TRAVERSAL_ONLY | 87ae62c0f302e39b2c2f4c70447cabba2596a5f2263300502b086b7c41f09640 |
| independent-reader-controls-6/result.json | 9 | PASS_READER_CONTROLS_ONLY | 05042a5b6ab3cd96e447d9e2811999251fea909adc3c1e8694747c47e3f69b82 |

The first new target-control run passes all fixed cases. Flat point/cell nulls
run first. Four independently re-chosen smooth standalone points retain exact
scalar and indicator bits against a22d and the explicit-default API. Their
uniform-disc sinusoid oracle is independently derived through the Bessel
integral. At the first point, explicit target1e-18 consumes912 angular nodes
versus144 at the default. It returns10242.746547657092e within the registered
analytic tolerance. Its returned heuristic indicator is zero after finite
quadrature agreement; that is not asserted as zero true error.

Actual point-call traces observe both low/high batches in all three cell arms:
primary/cell-refined consume.000046875, angle-refined consumes.00001171875.
Each traced cell has four point-batch calls. Count/placebo each execute four
hooks and off executes none; scalar and indicator bits are identical across
all three observer modes. Omitting the keyword from either actual low or high
batch is rejected by the independent argument-binding check after the real
point call. This is explicitly a consumption check, not a scalar-error claim.

Actual leaf consumption rejects negative, zero, NaN and infinite weights,
half-mass low weights and enlarged high weights on both normal and tiny
area2^-51 domains. Unmodified constant/affine companions pass. Invalid targets
are refused at the applicable config/point/cell boundary; the supported target
companion passes. No mass normalization or tiny-domain exemption is used.

The former full3 failing cell now returns11383.252407088126e, versus frozen
reference11383.252407088143e, using two roots. Its cell indicator is
4.51558457159127e-11, high-pupil indicator2.130862805151452e-11 and reported
total6.646447376742722e-11. Both the archived a22d path and a same-new-source
wrapper omitting the inner target retain the global depth/error refusal on
this exact cell. This attributes the recorded refusal change to the inner
target on that case; it does not substitute for a new complete image campaign.

The existing API/map/allocator populations need no stimulus or tolerance
changes. Only source pins and the new review binding were added to their
source snapshots. API textured maximum discrepancy is1.858716132119298e-6e
and RMS1.0395546513467505e-7e, below the unchanged.004/.0008e limits.
All old failure controls, including a59e's local refusal, remain powered.

The19x11 observer population keeps all six scalar and indicator nulls exactly
equal, including altered traversal and placebo. Scalar NPY SHA is
`b475c65674ef4aad20e76e6c727c70e105766a1563351ae1f7732381b69e7c21`;
indicator NPY SHA is
`143230af726b0385d6f39e46da777910b1a5c95fa7447917f27d19a98199232d`.
Count records209 cells/559 leaves, depths0–2,48 locally overallocated leaves
in28 cells. Off/placebo retain zero allocation counters. Count/placebo execute
35273 hooks and off zero. The changed foreground remains live. These numerical
allocation counters are not optical or product-quality measures.

## Complete reader and runtime boundary

The final reader source is
`e9745149a30f2754240c2970ce5d1855849679636488efecd125202831432f42`.
It requires all six current control records, including new target/mass evidence,
rechecks their source closure and keeps the existing full-array/edge/refinement
bars. The external schema is
`1efac4ff18b704047d3386e58379e6dd5c53fc7cd28854da044d20b35c179d13`;
the emission-contract binding is
`c362b63626a820615b59584889492d94bc6520aa36c415a75443e2fcdde868cb`.
No producer bundle is presumed to exist.

`independent-reader-preflight-3` passes all reference/API/observer/map/allocator/
target/reader source guards then deliberately refuses a nonexistent bundle.
It records zero compared frames and writes no float authority. This expected
transport refusal is not a failed numerical render or a partial admission.

Every command below ran sequentially from the repository root with
`python` resolving to
`C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe`,
Python3.12.10 MSC1943 AMD64, NumPy2.4.4, SciPy1.17.1. Each used the displayed
fresh cache prefix and `-X utf8`. All numerical drivers set the OMP, OpenBLAS,
MKL and NumExpr thread variables to2 before imports. No parallel worker was
launched. The new target receipt records `sys.orig_argv`, executable, xoptions
and versions directly. Older driver result command fields contain `sys.argv`;
the exact interpreter flags omitted there are retained below.

```powershell
python -X utf8 -X pycache_prefix=experiments/m194e-joint-pupil/work/cache-independent-target-1 experiments/m194e-joint-pupil/independent-target-controls.py --render-sha256 487c1727ca3aab05dd66a7056fb368712ccaabbbe604818fdc8b47eda77b6e97 --output experiments/m194e-joint-pupil/independent-target-controls-1
python -X utf8 -X pycache_prefix=experiments/m194e-joint-pupil/work/cache-independent-api-6 experiments/m194e-joint-pupil/independent-author-check.py --output experiments/m194e-joint-pupil/independent-author-api-6 --model-sha256 a74cd9bd61ea2f717a185e86f725b5ed192431056a447581db0f8562cf9f70b8 --render-sha256 487c1727ca3aab05dd66a7056fb368712ccaabbbe604818fdc8b47eda77b6e97
python -X utf8 -X pycache_prefix=experiments/m194e-joint-pupil/work/cache-independent-map-3 experiments/m194e-joint-pupil/independent-map-controls.py --render-sha256 487c1727ca3aab05dd66a7056fb368712ccaabbbe604818fdc8b47eda77b6e97 --output experiments/m194e-joint-pupil/independent-map-controls-3
python -X utf8 -X pycache_prefix=experiments/m194e-joint-pupil/work/cache-independent-allocation-4 experiments/m194e-joint-pupil/independent-allocation-controls.py --render-sha256 487c1727ca3aab05dd66a7056fb368712ccaabbbe604818fdc8b47eda77b6e97 --output experiments/m194e-joint-pupil/independent-allocation-controls-4
python -X utf8 -X pycache_prefix=experiments/m194e-joint-pupil/work/cache-independent-observer-4 experiments/m194e-joint-pupil/independent-observer-check.py --output experiments/m194e-joint-pupil/independent-observer-4
python -X utf8 -X pycache_prefix=experiments/m194e-joint-pupil/work/cache-independent-reader-6 experiments/m194e-joint-pupil/independent-reader-controls.py --output experiments/m194e-joint-pupil/independent-reader-controls-6
python -X utf8 -X pycache_prefix=experiments/m194e-joint-pupil/work/cache-independent-reader-preflight-3 experiments/m194e-joint-pupil/independent-compare.py --bundle experiments/m194e-joint-pupil/reader-intentionally-absent-bundle.json --bundle-sha256 0000000000000000000000000000000000000000000000000000000000000000 --author-run experiments/m194e-joint-pupil/reader-intentionally-absent-run.json --author-run-sha256 0000000000000000000000000000000000000000000000000000000000000000 --schema-sha256 1efac4ff18b704047d3386e58379e6dd5c53fc7cd28854da044d20b35c179d13 --reader-controls experiments/m194e-joint-pupil/independent-reader-controls-6/result.json --reader-controls-sha256 05042a5b6ab3cd96e447d9e2811999251fea909adc3c1e8694747c47e3f69b82 --output experiments/m194e-joint-pupil/independent-reader-preflight-3
```

These checks admit the named software components/APIs only. All historical
full campaigns remain failed and retained. A fresh complete fifteen-array
comparison is still required before genuine float or CFA authority. No
physical calibration, diffraction, real-camera, noise, product-quality,
performance, default-promotion or SOTA conclusion follows.

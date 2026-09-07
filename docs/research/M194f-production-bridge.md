# M194f — admitted joint-pupil CFA through production

2026-09-07, root. **In progress; no production bridge pass yet.**
The prospective [protocol](../../experiments/m194f-production-bridge/preregister.md)
was allocated and committed at `9da113f5` before implementation. It consumes
M194e's independently admitted five CFA images through the existing prepared
Pyramid, full-resolution gather, MHC and CameraLinear TIFF writer. The only
existing product-file edit is a test-only child declaration; the new adapter
does not change merge arithmetic, defaults, the old parser or dependencies.

## Question and fixed population

The consumer is delivered TIFF values and coordinates. Five genuine main RGB
outputs exercise observer off/count/placebo, confidence rereading and exposure
potency. The confidence run adds one Gray16 image. Three private RGB fixtures
exercise constant/affine values, a nonzero unequal crop and an actual changed
CFA sample. Two private Gray16 fixtures exercise strict input-rank centrality
and the unseen sentinel. All eleven delivered files must be independently read.
Private fixtures supply no optical authority.

The fixed coordinate oracle has 80 sites and a maximum error bar of .25 DN;
the green input mutation must move its delivered sample by more than 63.5 DN.
Complete baseline TIFF and pixel bytes must match across off/count/placebo
and confidence off/on. Exposure +1 must change pixels. Strict malformed-input,
source-change and second-read refusal controls precede intended renders.

This 64x48 fixture has only one Laplacian band plus its base and no measured
floor band. A passing result would commission this input-to-writer path, not
a three-band quality comparison, physical optics, registration, or SOTA.

## Retained implementation and instrument results

**MEASURED:** the first independent launcher check accepted six invalid private
records: wrong copied-executable length, wrong compiler hash/length, a false
copy-admission flag, an eleven-test summary and non-summary text containing a
passing-test fragment. Both valid companions passed. The actual first result
is `independent-driver-1/result.json`, SHA
`924e06d271ca796176dc9fcaa7a5bc5b8d62554033f70d17c0cfa0cb0e68694c`;
16 of 22 checks passed. These explicitly stubbed subprocess controls launched
no real compiler or merge.

The corrected launcher checks actual compiler and copied executable hashes and
lengths, their association with the compiler message, and one complete exact
test summary. Independently re-chosen controls pass 32 of 32, including the
original six faults and additional type, target, profile and summary cases.
The actual result `independent-driver-2/result.json` has SHA
`1b3c6d48c1b4cf8d0ba8e697ab3c235a698dc2a1ac07255e672da1de110776c7`.
Source bindings remain equal. Source and both results were committed at
`dfadf356` before the first production build.

**MEASURED instrument commissioning:** the independent classic-TIFF parser and
fixed value/rank oracle pass 59 of 59 synthetic controls before reading any
M194f product TIFF. The result `independent-reader-controls-1/result.json`, SHA
`f61e7b7990559e6368a676b70b16d1174c26a8b969fc9f56ad9403a5ffe9efc4`,
includes endian/strip companions, malformed tags and digests, geometric and
colour destroyers, an actual changed pixel, clipping and rank/tie/sentinel
controls. This admits an instrument, not product output.

The first actual build visibly compiled `strehl-cli` and failed on the new
adapter's single large JSON macro exceeding Rust's expansion recursion limit.
`build-1.json`, SHA
`b989e7aa4a2133576c14cf15e158077ab9dcf77515a2c091105ed415298efdc7`,
and its exact compile log retain the failure. The scoped repair splits the
metadata construction rather than changing a crate-wide compiler limit.

The build command actually run was:

```powershell
python -X utf8 -X pycache_prefix=experiments/m194f-production-bridge/work/cache-build-1 experiments/m194f-production-bridge/consumer-run.py build --build-record experiments/m194f-production-bridge/build-1.json
```

All short experiment paths in this report are relative to
`experiments/m194f-production-bridge/`. Subsequent builds, compiled refusal
controls and the complete delivered-output read remain to be recorded.

**MEASURED compiled controls:** the second build passed with a visible fresh
`Compiling strehl-cli` line. Its record `build-2.json` has SHA
`4a2f0efd92b34e24215d3066d464ae7a6c72c53449de011aa3ff008dc82b62f7`.
The unchanged copied executable passed seven focused tests, including six
independent groups with 153 of 153 controls. The full CLI suite then passed
145 tests with five ignored. These are two executions of the same independent
checks, not 306 distinct cases. Source and executable bindings remained equal.

The focused record `independent-input-run-1/result.json` has SHA
`6df33bcf47dfaf989246bf1c78f4e2cff401296186788ed2ad13c233af6aa96c`;
the CLI record `independent-cli-run-1/result.json` has SHA
`edaba70f5003021a57675a30a7fbc482306c52ff403372b5f1dca5481cbbac99`.
The actual computed crop is quad `(5,4,22,17)`, native offset `(10,8)`, with
levels 22x17 and 11x9. The intended main output is therefore 44x34 RGB and its
confidence auxiliary is 22x17 Gray. This is observed geometry, not a new crop.
The private real-fold second-read fault records five attempted second reads,
successful counts `[2,2,2,1,2]` and nine observer hooks. It refuses before writing
either TIFF. Separate file-change controls modify real private CFA bytes.

The first independent scheduler check retained nine actual false acceptances
among 20 private stub cases: three malformed/failed private results and six
inconsistent prerequisite records. Its SHA is
`6fbf11f5090195e011d9dfefa17e17bd372a26b0b5170f82b5cbe65422d49d7c`
at `independent-orchestrator-1/result.json`. Valid scheduling and interruption
companions passed. The correction consumes each prerequisite's actual log,
exact executable/test command and six independent child results. These stub
checks produce no production image and do not admit the intended population.

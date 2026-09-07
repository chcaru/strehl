# M194e independent emission boundary design

2026-09-07. **Prospective; no CFA output, emission implementation or emission
test has been inspected or run for this design.** The author and mathematical
reviewer are implementing the released model at
`773f576299f58ea0b0a998a22243ee837f6f7d8d`. Root requested this separately owned
conversion/provenance lane and will approve it before test implementation.
No new integration method, model tolerance, production bridge or quality gate.

## Authority and the smallest useful check

The bound [implementation plan](implementation-plan.md) and
[independent mathematical design](independent-design.md) define the model and
closed scene/sensor/frame children. The mathematical reviewer owns optical
controls, complete primary/refined float comparisons, and the genuine float
commission. This lane independently checks that emission consumes exactly
those admitted floats and converts their values correctly.

The stages remain acyclic:

1. `m194e-float-frame-v1` describes uncommissioned scalar arrays.
2. A genuine independent `m194e-float-commission-v1` PASS binds the exact
   arrays, numerical receipts, model/settings and relevant source bytes. The
   caller supplies its path and SHA-256 outside the candidate package.
3. Emission produces `m194e-joint-pupil-v1`, with status
   `float-commissioned-cfa-unverified`.
4. This lane reads the actual files and records a separate
   `m194e-cfa-commission-v1` disposition. It cannot repair a failed float gate.

A private, explicitly labeled fixture-only gate may exercise API behavior
before genuine commissioning. It cannot authorize final emission, count as
model evidence, or appear as a successful real float commission. Final emitted
data must trace to the mathematical reviewer's actual successful package.
If that package does not pass, retain API results separately and leave final
CFA commissioning unperformed.

Use a small dedicated driver and existing streaming SHA-256, strict-JSON and
actual-array reading patterns. Relevant prior helpers are M194b
`score.py::sha256`, `score-benchmark.py::read_bound` and M193b
`consumer.py::strict_json_loads`; M194d's private-copy mutation scripts provide
the valid-companion pattern. Reuse only applicable helpers, preserving and
hashing any imported historical source. No historical schema, TIFF scorer,
matrix controller or general certificate framework is needed here.

## Choices fixed before output

The valid final companion is the complete five-frame released scene, native
64 by 48, ordered focus indices 0 through 4, identity forward similarities,
K12, the frozen half-plane and two-wave fields. Sensor values are RGGB with
origin `[0,0]`, factors `[.75,1,.6]`, black512, gain.25 DN/e, white15360,
noise false and ties-to-even. Both greens are checked individually. Alternative
conversion fixtures are separate API controls, never alternative emitted scenes.

Private mutations change one declared boundary at a time, preserve the first
failure and carry an unchanged companion through the same entry point. For
content attacks, recompute all candidate-controlled lengths/hashes up to the
trusted float commission, whose externally supplied binding remains fixed.
This distinguishes a semantic/binding refusal from an obsolete checksum.
Replacing that external authority with an attacker-authored PASS is outside
the trust claim; a checksum does not authenticate who performed an experiment.

| Boundary | Independent wrong input and required observation |
| --- | --- |
| Strict JSON and types | Duplicate top/child keys; NaN/Infinity; unknown/missing schema or child key; bool as index/byte count/dimension; floating index/shape; strings, nulls or wrong-length coordinate arrays; malformed/uppercase hash. Refuse before publishing a complete CFA manifest. Use a complete unchanged record as companion. |
| Relative paths | Try `../`, backslash traversal, an absolute drive path, UNC path and drive-relative `C:...` against real readable private fixture files. Also try a relative reference resolving outside its owning bundle. Refuse escapes even with correct file hashes. A whole filename-preserving bundle copied to a different parent is the valid relocation companion, subject to the frozen reference-base contract. Do not create links or change external files. |
| Frame/array identity | Reorder/duplicate an index; exchange two distinct frame arrays with internally updated hashes; change focus or identity similarity; substitute an equal-shaped foreign array. Keep the real external float binding fixed and require refusal. Merely duplicating an identical value is not a powered content control. |
| File bytes and interpretation | Test stale-hash mutation, then a rehashed finite one-cell float change; truncate/append data; claim transposed shape, wrong dtype or byte order; malformed actual array container; rehashed NaN/Inf payload. Actual file parsing and the trusted float association must both be checked. |
| Model, sensor and settings | Change the signed ray law, foreground side/order, one phase, K, pupil/cell law, numerical tolerance, factor, CFA phase, black, gain or noise setting, while updating candidate-controlled records coherently. Fixed source/model/commission binding must refuse. No new model value is promoted by a successful conversion. |
| Source and control provenance | Remove/add/substitute a relevant source or numerical receipt; change a source payload and rehash its candidate map; change a recorded live-control/refinement result or terminal status. Require the exact externally admitted source/control set and actual referenced bytes. Replacing a hash without changing source bytes is only a checksum control. |
| Stage admission | Missing float gate, false/non-PASS status, failed/incomplete frame, wrong externally supplied digest, mismatched source/model/array set, and self-declared CFA PASS must refuse. A CFA manifest must contain both `expected_cfa` and `cfa` on every emitted frame; neither field alone is a complete record. |
| Actual CFA corruption | After valid emission, change one u16 sample and rehash its descriptor; swap R/B interpretation; transpose or reverse rows; change expected-CFA float content. The independent actual-value reader must reject against the same admitted scalar inputs, even if metadata hashes are coherent. An unchanged reread passes. |

Tests use new private directories and never mutate genuine float evidence or
historical inputs. A refusal may retain explicitly incomplete diagnostic files;
it must not label them commissioned. The test report records whether refusal
occurred before conversion or in the independent post-emission reader.

## Conversion oracle and its power

Read every scalar and expected-CFA float plus every actual u16 sample in all
five files, one frame at a time. The author has pinned scalar/expected-CFA as
little-endian f64 NPY arrays, both in electrons; expected-CFA already includes
the site factor and excludes gain/black. CFA is headerless little-endian u16
raw DN. Load NPY without pickle and confirm actual dtype, shape and container;
confirm raw CFA length6144 bytes. Check whole-file lengths and SHA-256 rather
than accepting ArrayRef fields.
For each native `(x,y)`, independently choose RGGB parity, multiply the scalar
electrons by its factor, then apply `512 + .25 * expected_cfa_electrons` and
nearest-integer ties-to-even. Use scalar standard-library arithmetic and an
explicit floor/fraction/even rule for the quantizer; do not call the author's
conversion function to obtain expected results. Record any floating operation
order fixed by the released API instead of silently choosing a different one.

Commission this reader before final arrays with full-size, separately labeled
API fixtures. A constant20-electron field must give R516, both G517 and B515;
constant12000 gives R2762, both G3512 and B2312. These distinct channel values
and nonzero high bytes expose phase, factor and endianness errors. Add ties
at R scalar8/24, G2/6/10 and B10/30: expected codes respectively514/516,
512/514/514 and514/516. Put each case at its intended parity and test a fixed
scalar perturbation of plus/minus `2^-20` around it. This perturbation is large
enough to survive addition of black512; one scalar `nextafter` step need not
move the DN and is therefore an unsuitable live test. Require a wrong half-up
rounder to fail the even-down cases, with ordinary non-tie values as companions.

Wrong CFA phase, a changed factor, omitted gain, added WB/noise and an isolated
sample alteration must each produce a real discrepancy on the declared field.
Nonfinite, negative-electron and over-white fixtures test the frozen refusal
policy without accepting clipping. Exact endpoints follow the author's declared
rail contract; that contract must be explicit before these controls execute.

Conversion is evaluated against the **actual admitted scalar floats**. The
mathematical reference has a finite integration discrepancy allowance. Report
minimum distance of the unquantized actual DN to a half-integer and the number
whose margin is no larger than `.004 * .25 * channel_factor` DN. Such locations
may change integer code within the model's numerical allowance. Do not require
byte agreement with a rounded approximate optical reference, or infer a
post-merge error bound from a successful conversion check. Quantization's
half-DN allowance is separate from the float integration budget.

## Actual observer and source checks

For every observer that the author actually adds to the emission path, run
off, on and a same-location placebo against the same genuinely admitted input
files. Require an activation witness: on traverses the declared observation
hook, placebo traverses its call site without collecting the statistic, and off
does not. Identical output with an unused flag is an inert option control,
not evidence about an observer. Compare scalar/expected-CFA/CFA payload bytes
by registered frame index; report unavoidable command/status/observer receipt
differences explicitly rather than claiming whole-manifest byte identity.

If the observation hook belongs to float rendering instead, coordinate its
actual on/off/placebo float runs with the existing mathematical campaign; do
not infer renderer non-perturbation from an emission-only run or duplicate a
five-frame integration campaign here. Any alternate float receipts still need
genuine external admission before their CFA emission. Tile/order invariance
and numerical allocation controls remain owned by the author/math lanes.

Record exact invocation, Python/library versions, selected environment,
source/design hashes and input hashes before/after. Imported helper and schema
source bytes are part of the check's source list. Evidence is recorded
consistency under an external trust anchor, not authentication of fully forged
telemetry. No process RSS, speed, real noise calibration, optical realism,
quality improvement or SOTA claim follows.

## API closure and execution condition

The author pinned reference resolution to the containing manifest/float-bundle
directory, including references inside nested receipts. The external commission
is a separate absolute path plus trusted SHA. Escapes through links/reparse
targets must also refuse; this lane does not create links. The fixed ray record
is `name:shared-pupil-two-opaque-planes-v1`,
`pupil:uniform-unit-disc-area`, `visibility:foreground-first-same-ray`,
`coordinates:native-displacement-before-inverse-similarity`,
`defocus:K*(inverse_focus-1/depth)`, `exposure:radiance-normalized`,
`diffraction:false`, `spectral_optics:false`. Allocation observation modes are
`off`, `count`, `placebo`, with no arithmetic or branch-selection effect.

Before implementing the test adapter, record the remaining concrete
producer/numerical/commission key sets, rail endpoint rule and callable
observer interface. Those details must implement the released contract; a
substantive change requires a prospective amendment, not a permissive reader.
The author and mathematical reviewer have been asked to provide this interface.

Root approval of this design authorizes the small independent driver and API
fixtures. Actual final emission checks additionally require the genuine
successful float commission. Preserve initial failures and keep API-control,
float-model and actual-CFA outcomes separate. No Rust, RAW, holdout, product
adapter, noisy quality matrix, scorecard or SYNTHESIS edit is in this lane.

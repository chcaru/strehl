# M193c independent private grid reader — prospective

2026-09-07. Source preparation only, before any reader import, numerical
evaluation, build or TIFF consumption. The parent must review and freeze this
file, reader source, exact input/build/command records and any kernel witness
before execution. No RAW source or RAW bytes are involved. Held M194g and
M193c producer sources remain unchanged.

## Scope and independent choices

Consume exactly the ten cases in `private-protocol.md`, in its literal order.
Keep the 32 R/G1 pairs, all per-axis 2.75 DN bars, paired two-site 0.1 native
pixel bar, >1 pixel wrong-map power and restored/observer byte identities.
No new production TIFF is requested: ten geometry plus two separately
registered derivative TIFFs remain the twelve-output charter allocation.

Reuse the actual strict RGB16 parser
`experiments/m194g-larger-pupil/independent-rgb-tiff.py`, SHA
`d01a74aefcfa15b2146256b54ea51876715ab203b7de123b3cff2b0af4a1b19c`,
unchanged. Its exact typed dimensions, 1 MiB file cap, native 320×240 bound,
external hash, RGB CameraLinear strings, strip and payload checks are sufficient
for these files. Its original instrument commissioning remains historical;
new actual-entry pixel mutations commission this consumer's association.

The independent geometric implementation uses plain real matrix arithmetic,
an analytic intersection of all corner inequalities for cover k, and explicit
native coordinates. It does not import Rust producer geometry, another Python
grid oracle, or a production helper. Derive the maximal k from each affine
corner's lower/upper constraint; compare to the product's bisection k within
2e-14 absolute (a numerical representation allowance, not a pixel bar).
Require exact derived inclusive integer rectangle and level sizes. Track
coefficients compare within 2e-14 absolute; indices/extents/counts are actual
integers, never bools or numerically equal floats.

Source guards reconstruct every active CFA site for each distinct literal
source/field combination, check pre-round positive finite values and strict
stored rails, and compare actual u16 little-endian SHA, min/max and identities
to all 58 producer source records. Cache only by complete source pull and field
identity. No noise generator is used. The production floor probe remains
enabled and does use deterministic synthetic probe draws; this reader does
not reconstruct or claim to calibrate those draws.

For Crop use native offset twice the actual quad origin; for Scale use native
centre (160,120) with cover k. Bad cases retain the same full-track cover but
compose source inverse with the swapped or inverse pull. Verify the complete
nine-entry track, including unselected endpoints and canonical index, and
local/original/probe identities separately. R at `(x,y)` and G1 at `(x+1,y)`
are different centres; report the existing paired two-site norm with that
label. Reconstruct all RGB values at the R sites and the extra G1 values.
Only R/G1 receive the geometric bars; other components are descriptive.

## Precision instrument

Evaluate the literal source → MHC → Catmull stencil at all 64 measured channel
sites for every selected source in every distinct case/mapping combination,
including cases 6 and 8. Check the complete stencil remains in native active
storage, without MHC reflection or sampler clamp. No failed support may be
omitted. The MHC reference uses integer/rational dyadic stencil sums; a second
implementation explicitly rounds each f32 multiplication/addition in the
published product operation order. Catmull's f64 reference evaluates its
polynomials separately and reduces terms with `math.fsum`; the f32 model rounds
every operation including coordinate fraction casts and black addition.

Retain f64, modeled f32, source quantization error, support and residuals.
Require the proposed 0.125 DN gather/black-add reserve on all literal sites;
require source evaluation allowance 1e-8 DN and the unchanged end-to-end bars.
At every consumed 8×8 source-stencil rectangle, check the unrounded binary64
source expression against exact rational evaluation of its stored binary64
coefficients. Deduplicate only identical source/field/native-site checks.
The independent f64 gathered value must be within 1.953125 + 1e-7 DN of its
unquantized affine expectation. The 1e-7 is a prospective numerical allowance
for the source reserve propagated through stencil norms and f64 oracle
evaluation; it does not enlarge the 0.125 or end-to-end bars.
The f32 model is **not an observation of the Rust kernel**. Final precision
admission additionally needs an independently bound bounded Rust witness using
the actual `demosaic_malvar_row` and `Resampler::sample_checked`, with actual
source hash, coordinates, selected channel and returned f32 value. This is a
component receipt, not another production render. Root's new
`precision-witness.rs` fixes `m193c-precision-witness-v1` with ten
`m193c-precision-case-v1` children, 58 selected sources and 3712 rows. Each
component plan must match the corresponding genuine pre-render plan hash,
extent and parsed record. All rows retain case/local/original/pair/channel,
native output/full/source coordinates, actual f32 value and bits, black-added
f32 and bits, rounded u16 and the actual full-warp u16. Require all identities,
bits, values and the actual warp result to agree with the independent oracle.
Actual source coordinates compare to independently derived coordinates within
2e-11 native pixel; the oracle then consumes these validated actual sample
coordinates. This avoids demanding bit identity from algebraically rearranged
f64 geometry while still testing its independent native meaning. This source
and its command require review before execution. A rigorous literal-operation
rounding bound would require a separate preregistered replacement, not an
unrecorded substitute.

Private precision controls use an exact constant and distinct affine RGB
field, noninteger positive/negative translation and both imaginary signs;
actual scope is the existing fixed source/coordinate population, not added
images. Exact integer-centre companions must reproduce MHC channel samples.
Removing a Catmull outer tap or substituting the opposite channel must fail
the reference comparison on a fixed nonidentity witness, with a restored
companion. A constant field is a null for coordinate inversion and cannot
alone commission a kernel or two-axis mapping. Fix the consuming kernel fault
site before execution: case 1, local/original 1, pair 1, R (row 66 of that
component case). Three separately resealed records replace the actual sample
with (i) sample +1 DN, (ii) the modeled result with the first horizontal
Catmull weight omitted, or (iii) the modeled B channel at that same source
coordinate. Update all dependent bits/pedestal/rounded/warp fields coherently.
Each must fail the actual complete `verify_precision` entry at
`precision-kernel`; the two operator faults must additionally differ by more
than 0.125 DN before their reader call. Restore the genuine complete witness.
No data-dependent choice of sample or threshold is allowed.

## Reader interfaces and evidence

`independent-grid-read.py` exposes typed semantic validators and
`read_case(plan_ref, receipt_ref, *, reads, budget, parser, context, ordinal,
private_fault=None)`. It reads the same bounded bytes it hashes; paths in
producer refs are absolute and must equal the externally selected files.
`read_population(rows, *, reads, budget, parser, context, kernel_witness,
private_fault=None)` requires exactly ten ordered rows and returns each full
case result plus observer/restored comparisons. Root owns final launch/index
authority. The exact context keys are `build`, `compiled_inputs`,
`precision_witness_sha256`. `build` has path/sha256/bytes/software;
`compiled_inputs` has private_protocol_sha256/private_adapter_sha256. The
parent derives them from externally checked build/source evidence. They cannot
be derived solely from the subject plan. Executable paths are compared by
resolved repository-contained identity, allowing Windows' verbatim prefix;
hash, extent and build-specific software remain exact. Child argv remains the
exact supplied copied executable plus the registered ignored test/options.

The row's exact keys are ordinal/id/plan/plan_launch/receipt/tiff/render_launch.
The five FileRefs are repository-relative in the parent index; embedded Rust
refs are absolute. Resolve both from the known repository root and require
same file/hash/extent, not identical spelling. All ten parent plan commands
must precede the component and every render.
The actual child name is confirmed from the compiled test list, not assumed
from a path. Parent command records bind exact args, sanitized environment,
exit/test count, runtime, actual logs and copied executable. Reader final
admission also requires actual kernel witness and complete parent authority;
a fixture-only private override cannot create a genuine PASS.

The parent wrapper preserves all attempted cases/controls on failure,
source/runtime bindings, exact argv, input before/after hashes, independent geometric
predictions, actual TIFF evidence, source hashes and every sampled residual.
Per-case records are separate bounded JSON children; the top result carries
FileRefs to avoid a large repeated-plan object. Source/import loading is from
hashed bytes, with unique cache and source-before/after closure. Final success
requires post-persistence budget and file/source checks; late failures retain
the original exception and revoke success. No final gate is written before all
controls and the ten outputs pass their proper expected outcomes. The callable
returns `m193c-independent-grid-population-v1` with
`PASS_GRID_SEMANTICS_AND_PIXELS`; this is a semantic/pixel child, never the
parent's final `PASS_GRID_ADAPTER_PRIVATE_ONLY` authority. Precision returns
`m193c-independent-grid-precision-v1`, `PASS_LITERAL_KERNEL_PRECISION`.
No standalone CLI or new certificate framework is needed for these callbacks.

## Powered complete-entry controls

Before admitting the ten outputs, `run_controls` reads complete genuine case
entries 1, 4, 6, 8 and 9 as valid companions, then the fixed mutations with
restored companions. It also consumes the entire 3712-row kernel witness,
its three faults and the restored full witness. Preserve the genuine baseline
artifacts. Private TIFF/JSON mutants are counted output bytes, not production
renders. All refs affected by a byte mutation are coherently rehashed.

Required refusal choices: missing case; duplicate case; reordered identities;
bool ordinal; float width; float decode count; wrong local/original/probe
association; stale source hash; changed input range; nonunity WB; removed final
hull; unsupported environment; wrong compiled source; failed child disguised
by status; duplicate JSON key; nonfinite JSON literal; mismatched TIFF extent;
changed R code by +200; R/B pixel exchange; transposed output interpretation;
zero Crop origin; exchanged unequal Crop axes; native/quad factor omission;
Scale k replaced by 1; stale frame association; wrong inverse convention.
Map-interpretation faults deliberately reach the actual coordinate scorer
after ordinary input validation, under a named fixture-only override, so a
hash/schema refusal is not called pixel-oracle power. Constant/rank-one fields
must refuse coordinate inversion. The `(w-1)/2` centre fault is a convention
refusal, not promised >0.1 pixel power. The G1/G2 field-label null is distinct
from a spatial green-plane swap.

The normal bad-map cases 6/8 must return complete TIFF results that PASS their
fault-consistent oracle and FAIL correct-U by >1 pixel; a missing image or
exception is not their positive witness. Byte identity must hold for 1/2/3
and 5/7, with nine actual observer hook calls for count/placebo, nine collected
counts only in count, and all source attempts exactly one. A value-only
comparison cannot replace these complete-file identities.

The frozen callable control schedule has **45 checks: 35 expected refusals
and 10 valid/restored companions**. `run_controls(rows, *, reads, budget,
parser, context, kernel_witness, write_bytes, partial)` returns
`m193c-independent-grid-controls-v1`, `PASS_GRID_READER_CONTROLS`, with exact
counts and every attempted control record. The parent attaches `partial`
before calling; an unexpected exception or wrong refusal boundary is a failed
instrument, not a passed negative. `write_bytes(name,raw)` is the parent's
same-budget bounded writer, returning a FileRef. The literal groups are:

| Group | Refusals | Companions |
| --- | ---: | ---: |
| Complete genuine case entries 1/4/6/8/9 | 0 | 5 |
| Missing/duplicate/reordered/bool-index population | 4 | 0 |
| Fourteen resealed plan/receipt type, identity, source, sensor, configuration and terminal faults | 14 | 0 |
| Duplicate key and overflow numeric JSON | 2 | 0 |
| R code +200, R/B pixel swap, spatial G1/G2-site swap, appended TIFF payload | 4 | 0 |
| Seven actual scorer interpretation overrides | 7 | 0 |
| Rank-one field | 1 | 0 |
| Restored cases 1/4/6 | 0 | 3 |
| Complete precision entry, three coherent saved-kernel faults, restored complete precision | 3 | 2 |

The four TIFF mutants modify actual bytes, rehash their refs, and reseal the
consuming receipt. The spatial green fault replaces the first G1 sample with
the adjacent G2 site's green code, explicitly distinguishing it from a null
field-label rename. Appending two zero bytes is an extent/parser failure,
not geometric power. The remaining three are required to fail the measured
coordinate boundary. None is a production render. The top parent first runs
this instrument child, then the complete ten-case `read_population`, and
requires both plus its independent launch/source closure before final PASS.

## Resource and execution boundaries

Proposed reader-local ceilings are 120 CPU / 240 wall seconds, 32 MiB tracked
live ndarray backing storage, 32 MiB new reader artifacts, 512 MiB cumulative
bounded input reads and 4 MiB per JSON. These are engineering stop budgets,
not measured performance. The parent must include this child and the kernel
witness within the charter's private 600 CPU / 1200 wall total; it must refuse
launch when the remaining bound is insufficient. Array accounting prunes dead
weak owners before id lookup and counts shared-root aliases once. It is not
RSS; the parent owned process-tree memory limit remains separate. Cache,
restored calls, mutations, parser reads and final persistence are all charged.

No computations or controls have run. A source-only implementation does not
clear this protocol's execution, precision or ten-output admission gates.

# Independent checked-sampler public-API controls

SOURCE ONLY. Fixed before baseline or repair execution, 2026-09-08. Author:
coordinate_verification, independent of both the existing resamplers and the
proposed repair. Entry point: crates/strehl-core/tests/sampler-boundary.rs.
Original align.rs and warpmap.rs are unchanged. This specification contains
no observed sampler result and no performance or image-quality claim.

## Prior work and consumer choice

The root charter and common-tiff-stack/work/next-sampler-boundary.md identify
the new question. M136-m8-census-groundtruth.md section 2.2 explicitly repeats
coordinate clamping before its validity/hull census; M136-m8-passability.md
and ORCH-clamp-default-decision.md constrain interpretation of the value
limiter. A value-hull invariant does not prove that an accepted value describes
the requested fractional coordinate. The present tests therefore use an
independent requested-coordinate oracle and separately preserve the existing
value limiter. They cannot justify a default change, M8/SOTA promotion,
restoration claim, or real alignment. Old kernel-detail claims are not reused.

The actual consumer is public warpmap::gather_checked: a reference-to-source
pull, where Some writes covered/true and None writes NaN/false. Scalar planes
are 128 by 96, with integer sample centres in scalar-plane sample-pitch units.
There is no CFA factor-two conversion, RGB development, RAW, estimated map,
noise calibration, merge render, benchmark or additional image population.
One public gather call checks every mask entry and every resulting value.

## Fixed literal data, oracles and tolerances

F(x,y)=1000+8x+16y. Stored samples are exact f32 representations of its integer
values. Both slopes are nonzero. The constant null is -4321.25. No resampler
weight formula is copied into the test. All comparison tolerances below are
prospectively fixed code-unit bounds, not measured precision estimates.

For Bilinear, CatmullRom and ClampedCatmullRom, use literal F at the requested
coordinate and absolute error <=1/32. A quarter-step lost in x changes truth
by 2 code units, and in y by 4; these exceed the bound by 64 and 128 times.
Literal integer-centre and null controls distinguish coordinate preservation
from mere DC reproduction. Nearest uses literal round-to-nearest integer
sample centres with exact equality, and is retained as an unaffected control.

For Lanczos2 and Lanczos3, do not demand first-moment/affine reproduction at
fractional phase. For requested (x,y), choose interior
(qx,qy)=(20+frac(x),20+frac(y)) and translated plane
G(i,j)=F(i+floor(x)-20,j+floor(y)-20). Independently enumerate all 4x4 or 6x6
stencil addresses and require bit-identical corresponding stored values,
identical fractional phases, legal addresses, and an admitted interior query.
Compare the two actual public sampler results within 1/32. Integer queries
use the literal integer sample instead. This tests translation equivariance,
not absolute interpolation fidelity or image quality. Repeated calls and
related stencils are not presented as independent statistical observations.

Exact equality is required for Nearest and non-Lanczos nulls, integer data
constructors, mask entries, refusal NaNs, the cubic tap-range limiter, and
bit identity of already-in-hull raw/clamped cubic values. Lanczos nulls use
1/32. A numerical failure is retained with its raw f32 bits. Nonfinite results
never satisfy a finite-value oracle. Public calls are individually protected
by catch_unwind so a panic becomes a failed row and later rows are still run;
the normal panic hook is not replaced. No tested implementation is imported
or evaluated during this source preparation.

## Kernel/domain table

Support values are independent literals, then checked against the public API.
The checked finite mask is frozen at [s-0.5,W-0.5-s] on x and analogously on y.
A repair that returns None at a previously accepted high coordinate fails the
value-and-coverage row. Declared support, rather than fallback support, governs
checked tiny-plane admission.

| Kernel name | s | Old inner upper x U | Fixed unchecked endpoint E | Lower extension |
|---|---:|---:|---:|---:|
| nearest | 0.5 | 127 (high-probe base126) | 127 | 0 |
| bilinear | 1 | 126 | 127 | 0 |
| catmull-rom | 2 | 125 | 126 | 1 |
| clamped-catmull-rom | 2 | 125 | 126 | 1 |
| lanczos2 | 2 | 125 | 126 | 1 |
| lanczos3 | 3 | 124 | 125 | 2 |

For y, replace width128 by height96. For interpolating kernels E=W-s is the
last legal interpolating centre for a supported final cell; no floor/base-cap
implementation is used in the oracle. High-side unchecked extension is fixed
at that endpoint, with constant values beyond it. This explicitly changes the
old unchecked plateau from U to E; it is not claimed as unchanged behavior.
The existing lower extension and interior behavior remain regression checks.
An outside unchecked value is extension semantics, not evidence of coverage.
Nearest's endpoint and extension remain unchanged.

## Exact 344-row population

Ordering is six kernels in table order, each with support, boundary, null,
nonfinite, tiny, unchecked groups. Then twenty unchecked-tiny rows, four
constructor rows, the two Lanczos
commissions, six cubic-limiter rows and two gather rows. IDs combine fixed
kernel/group/site names; all must be unique. No row is dropped after failure.

| Group | Rows | Fixed cases |
|---|---:|---|
| support | 6 | One actual public support equality per kernel |
| boundary | 126 | 21 listed sites per kernel |
| null | 18 | Low corner, interior quarter, exact upper corner per kernel |
| nonfinite | 36 | NaN,+infinity,-infinity separately in x and y, other coordinate20.25 |
| tiny | 48 | Eight valid shapes per kernel, each at its centre |
| unchecked | 60 | Ten fixed high/low/interior sites per kernel |
| unchecked-tiny | 20 | Reached fallback endpoint/far-high pairs |
| constructor | 4 | 0x0,0x1,1x0 empty views and a128x96 view short by one sample |
| lanczos-commission | 18 | Nine rows per Lanczos kernel |
| cubic-limiter | 6 | Three exercised step branches and three affine bit-identity rows |
| gather | 2 | Actual requested map and rejected opposite-direction oracle |

For boundary rows let L=s-0.5, Hx=127.5-s, Hy=95.5-s. U is in the table;
Nearest alone uses126/94 as the base for quarter/half high probes and127/95
for last-integer. The exact 21 sites, in order, are:

1. (L,L), (L,20.25), (20.25,L).
2. (20.25,20.25), (20.5,20.5), (Ux,Uy) last integer as qualified above.
3. (Ux+0.25,20.25), (Ux+0.5,20.25), (20.25,Uy+0.25), (20.25,Uy+0.5).
4. (Ux+0.25,Uy+0.25), (Ux+0.5,Uy+0.5), (Hx,Hy).
5. (L-0.25,20.25), (20.25,L-0.25), (Hx+0.25,20.25), (20.25,Hy+0.25).
6. (-50,20.25), (20.25,-50), (178,20.25), (20.25,146).

Every kernel has13 intended accepted and8 refused boundary rows. The exact
upper-corner row duplicates a half-phase location for the five interpolators;
this is a labelled boundary check, not independent replication. High-probe
rows for non-Nearest kernels also require a query strictly above their old
inner upper coordinate while still inside the independently frozen mask.

Tiny shapes are exactly1x1,1x7,7x1,2x2,3x3,4x4,5x5,6x6, with query
((width-1)/2,(height-1)/2). Invalid support refuses; sufficient support admits
and is checked by the applicable literal or translated-stencil oracle. A
checked refusal is not labelled as an exercised inner fallback.

Unchecked sites are (Ex-0.75,20.25), (20.25,Ey-0.75), (Ex,20), (20,Ey),
(Ex,Ey), (178,20), (20,146), (178,146), (-50,-50), (20.25,20.25).
The oracle clamps only to the stated extension endpoints before applying its
literal or same-phase rule; it does not copy the proposed base-index repair.


Unchecked-tiny order: Bilinear on1x7,7x1; each CatmullRom, ClampedCatmullRom,
Lanczos2 on1x7,7x1,2x7,7x2; Lanczos3 on1x7,7x1,2x7,7x2,4x7,7x4.
IDs are `{kernel}-unchecked-tiny-{width}x{height}`. Each deficient axis forces
the existing dispatch, including Lanczos3 -> CatmullRom -> Bilinear -> Nearest.
The independent effective endpoint is(w-1,h-1) for1x7/7x1 Nearest and2x7/7x2
Bilinear, or(w-2,h-2) for4x7/7x4 CatmullRom. Each row makes two actual unchecked
calls: endpoint and(w+50,h+50). Require finite values, both matching literal F
there (Nearest exact, otherwise1/32), and matching each other's f32 bits.
Effective Bilinear/Catmull rows must also differ by >0.25 from their old
plateau, respectively F(w-2,h-2)/F(w-3,h-3); Nearest remains unchanged.
Literal dimensions must force fallback and endpoint centres must be legal.
No lower-kernel call supplies the oracle or dynamic instruction trace.
For oracle_kind effective-fallback-endpoint, oracle_f32_bits retains actual
endpoint, actual_f32_bits far-high, oracle_f64_bits literal truth. These20 rows
add40 sample calls, not another gather or statistical replication.

## Powered oracle and limiter controls

Each Lanczos kernel first checks six fully interior same-phase pairs:
phases0.25 and0.5 times integer offsets(7,0),(0,5),(7,5). All corresponding
source taps must actually match. Then compare F at(27.25,25.25) with the
following actual public queries:

- Wrong translation: G uses(8,5), queried at(20.25,20.25), rather than(7,5).
  Every one of the12,288 stored translated values must differ from the proper
  G, and the stencil equality guard must fail. Actual output difference must
  exceed0.25 code unit.
- Wrong phase: correct G(7,5), queried at(20.5,20.25). The actual coordinate
  phase changes and stencil correspondence must fail. Actual output difference
  must exceed0.25. A refusal/panic does not count as powered discrimination.
- Restore correct G(7,5) at(20.25,20.25), with matching stencils and <=1/32.

These are actual changed-input/coordinate witnesses. They use the same paired
comparison predicate as the boundary tests; they are not a test of a constant
against itself or an unexecuted argument about sensitivity.

For cubic limiting, an independent step is0 for x<64 and100 otherwise. At
x=62.5,63.5,64.5 and y=20.25, enumerate all16 actual source taps to establish
lo/hi, and require the raw CatmullRom result respectively below, inside, above
that hull. The clamped result must be exactly0,50,100. The inside result must
also retain the raw value's bits. Additional affine points(1.5,1.5),
(20.25,20.5),(125.5,93.5) require raw values within the independently enumerated
16-tap hull and bit-identical clamped output. These are bounded regression
controls, not a re-run of M136's image census or the old random unit-test sweep.
Coordinate fidelity is tested separately, so shared wrong clamped coordinates
cannot make these limiter comparisons stand in for the requested-coordinate bar.

## One actual gather and full saved operands

Invoke public gather_checked exactly once with Bilinear, the full affine plane,
identity a and b=(0.25,0.25),128x96 geometry. Destination starts at8675.5 and
coverage true, so a correct refusal must overwrite both. For every reference
integer(x,y), independently enumerate source(x+0.25,y+0.25), its fixed Bilinear
mask, and literal F there. Require every accepted actual value within1/32,
every coverage bit exact, each refused value NaN, and both the API's count and
counted mask equal the independent11,844 accepted /444 refused population.
This expectation follows directly from x=1..126,y=1..94, not from the sampler.

Compare the same actual consumer outputs to the opposite-direction source
map(x-0.25,y-0.25). Its independent mask is identical but values differ; require
at least one actual mismatch. Its exercised guard first requires actual
successful gather, correct returned/mask counts, exact mask and refused NaNs;
panic/error or sentinel buffers cannot prove power. Coordinate values remain
a separate positive predicate. This demonstrates why matching counts cannot
certify transform direction. There is no second gather or diagnostic branch.
The full actual12,288 f32 bit words and actual/expected masks are retained,
not only a worst error or mismatch count.

## Transcript, commands and finite bound

Compile the new integration-test and library-test targets with the held command:

    cargo test -p strehl-core --lib --test sampler-boundary --no-run --jobs 2 --target-dir ABS_FRESH_TARGET --message-format=json-render-diagnostics --locked --offline

Run the actually emitted/copied/pinned test executable once per frozen attempt:

    ABS_TEST_BINARY --exact sampler_boundary_public_contract --nocapture --test-threads=1

Root also requires thirteen exact existing unit regressions in a separate
repaired-only library invocation; controller protocol fixes that list/argv.
Those preserve existing sampler gates, without quality inference. No list
process, workspace-wide test, benchmark or fixture process is required. The
source uses existing public APIs and the standard library, with no Cargo dependency change. Rustfmt may parse/format source;
that is not a build or test execution.

A leading newline precedes SAMPLER_BOUNDARY_BEGIN. Subsequent physical-line
markers are exactly344 SAMPLER_BOUNDARY_ROW records, one
SAMPLER_BOUNDARY_GATHER record, and SAMPLER_BOUNDARY_SUMMARY, in that order.
There is one final aggregate assert after the summary; no scientific assert
terminates the population earlier. The normal libtest exit/summary is retained.
Baseline expects an actual failure exit101 and at least one exercised failed
public boundary row, never an xfail rewritten as a pass. Repaired execution
requires exit0, complete population and all344 passed; unexpected additional
failures remain failures in either attempt and require interpretation.

Row keys are ordinal,id,group,kernel,api,x_f64_bits,y_f64_bits,actual_kind,
actual_f32_bits,oracle_kind,oracle_f32_bits,oracle_f64_bits,
tolerance_code_units,exercised,passed. Nullable observed bits preserve returned
NaN bits distinctly from refusal/panic. Coordinate nonfinites are encoded as
u64 IEEE bit integers, never invalid JSON numeric tokens. Literal bits are f64;
paired bits are the other actual f32 result. For wrong-translation rows the
literal field labels the changed input sample count. All IDs/labels are fixed
ASCII generated from this finite source.

BEGIN schema sampler-boundary-begin-v1 declares rows344,width128,height96,gauge.
SUMMARY schema sampler-boundary-summary-v1 has rows,failed,passed,
population_complete,groups. GATHER schema sampler-boundary-gather-v1 has its
map/sampler, full counts, mismatches, max_abs_error, two
mask_nibble_lsb_first_hex strings, and row_major_f32_bits_hex. Each mask hex
character encodes four row-major booleans in its low-to-high bit positions;
each value is eight hex digits representing its exact f32 bit word.

DERIVED bound: each row reserves768 bytes, begin/summary/framing8KiB, gather
112KiB:344*768+8192+114688=387,072 bytes, below512KiB. The retained raw log
reserves1MiB including ordinary harness/panic text. This is a source envelope,
not a measured run cost. Inputs and working arrays stay below4MiB; the owned
512MiB process limit is the independent backstop. Source and this protocol
reserve64KiB and16KiB. The charter's fixed30CPU/60whole-wall test limit and
separate600CPU/300wall/3GiB fresh builds, two Cargo jobs and actual terminal
Job/exit/raw-log associations remain controlling. No cost is refunded.

Complete passing tests would establish the fixed checked-coordinate and
unchecked-extension contracts on these scalar controls. They do not establish
physical correspondence, sharpness, image quality, performance, a resampler
ranking, or a shipping default. Any change to unchecked edge extension must
be reported explicitly alongside preserved checked coverage and regressions.

# Independent source review: common-TIFF dimensions

2026-09-08. SOURCE REVIEW ONLY. Reviewer: sampler_result_review, independent
of the three-file product patch, fixture/checker and execution-controller
authors. I proposed the source-review replacement fixture and its prospective
rounding allowance; that contribution is disclosed rather than counted as a
second independent numerical validation. No product, compiler, fixture,
checker, sampler, image or numerical execution was performed for this review.
Root owns integration and release.

## Versions and admission status

The following exact buffers were read before execution:

| Source | Bytes | SHA256 |
| --- | ---: | --- |
| charter.md | 6150 | 4f3605c505ae9adce0ff9c7d6f8e6246fab0a379efaa9b6a928be2fee1c6f69c |
| implementation-contract.md | 8575 | 0e81f22a84419eb55faf48e6cf66414ccfea593eccb258ddb5bc53ced6f5e9f6 |
| patch-source-handoff.md | 4216 | 2bca19a18280fefc9ab25ff87cedd595909e181c83a4a3779e8acbf710f5fce3 |
| draft.patch | 18111 | fee644d8854b3298d3083025dc8f2ae83c6ba7a189ceddbf98416f397b3de005 |
| original independent-spec.md | 12851 | f1d8a635951a70ee097bce91960c398b2c461666dff1badf295847b6c1a0a12d |

The original specification is a historical draft, superseded prospectively
for case04 as below. Final reviewed versions are recorded in the closing
source addendum. This review finds no blocking issue in the held product and
controller/helper sources. It is source clearance, not an execution grant or
a claim that the independent checker and actual results have passed.

## Product consumer and compatibility

SOURCE-VERIFIED: the patch changes exactly manifest.rs, mod.rs and writer.rs
under crates/strehl-cli/src/bin/common-stack. I read all29 hunks, including
the removal of three stale initial frame-slot reservations. The reported
candidate byte construction and inverse-hunk check belong to the patch
author; I did not apply the patch or independently execute that constructor.

The v2 consumer accepts2..8 ordered frames and axes64..512, using the actual
layout for level sizes, BandMerge/workspace, proxy/variance allocations,
decode dimension comparison, fold counts, output observer and TIFF writer.
The four pyramid levels and merge coefficients are retained. No core merge,
TIFF parser, profile, noise estimator, sampling, alignment or default config
is changed. Actual consumed frame planes are hashed before and after folding;
the actual merge frame counter must advance exactly once per declared input.

The same request-level incomplete receipt is written before manifest
authentication. Version-specific result and per-frame schemas follow valid
admission. Every declared input extent is checked before visits; per-visit
file authentication and TIFF geometry precede the fold. Thus an actually
wrong fifth geometry/hash can preserve four completed folds. The checker
must admit the expected process exit and that exact prefix together with
absence of an admitted TIFF; a caught error string alone is insufficient.

The v1 positive route retains its exact count/grid, profile, tags, labels,
byte order, quantizer and original input/output/report caps. Whole-file
identity remains a prospective actual check against the pinned old output.
There is a deliberate refusal-prefix change: existing frame companions are
checked after authenticatedN, so a refusal may retain the initial incomplete
receipt where the original initializer refused earlier. Do not call all v1
failure behavior byte-compatible. Invalid array length also receives a new
explicit count error. The single held v1 positive case cannot exercise every
old refusal or cap.

The per-input and output cap is6*pixels+65536 for v2, at most1638400B.
BoundedCursor.write checks its next extent before writing. Seek returns an
error beyond that cap; seeking does not itself allocate. Encoded image bytes
are serde-skipped from report serialization. The streaming loop retains one
encoded/decode/prepared input alongside reusable state, not all aligned frames.
The writer and final input reauthentication have simultaneous buffers which
must remain in the separate resource construction.

The aggregate input bound is defensive arithmetic after every individual
bound. Multiplication overflow is likewise unreachable following the axis
limits in the released population. The oversized-u32 manifest is a serde
range refusal, not execution of checked multiplication. These source guards
must not be reported as separately powered measurements.

## Choices challenged in the initial specification

The distinct constant means have power against exactly the registered108
single-event contributor competitors:15 omissions,15 appended duplicates and
78 ordered duplicate-replaces-other-index cases. This finite set does not
prove that all compensating multiple changes alter the mean. Actual ordered
identities, before/after hashes and single-fold counters remain independent
requirements.

The identical address image is valuable for literal RGB/address/edge and
container output checks, but InputRange can force any reconstructed value to
the single input value at each site. An identical structured null therefore
cannot independently prove odd-grid reconstruction. I raised this before any
fixture generation. Root and the independent author agreed to replace only
case04, keeping24 product calls,33 new TIFFs and the existing noisy population.

The new noisy triple checks actual output identity for observer off/on/placebo,
injected plane/proxy/variance identities and reported ceiling geometry. Its
requirement that total zero and positive denominator populations are both
nonempty is collective across Laplacian levels. It does not require both at
every level or every fold. Neither those receipts nor the noisy output supply
an independent ideal nonidentical-image quality oracle.

## Prospective case04 replacement and arithmetic allowance

DERIVED/ARGUED, fixed fixture only: useN5 and129x97. Let
P=(13*x+29*y)%997, override P=512 for16<=x<48 and24<=y<56,
then x=128 with1200+y, then y=96 with1400+x, and finally corner
(128,96) with1777. The common RGB scene is(1000+P,3000+P,5000+P).
Add the scalar offsets(0,40,120,280,600) to all channels of the five frames.
The independently specified ideal output is the common scene plus208.

All input values are at most7377. Their exact integer proxy is3000+P+C_i.
At every site/channel the ideal lies208 above the minimum and392 below the
maximum input, so the input-range projection cannot manufacture this oracle.
Incorrect reconstruction clipped to either endpoint remains plainly wrong.
The asymmetric last row, column, corner and interior address structure are
retained, alongside a flat patch and the separate exact constant-mean cases.

The source argument uses the unchanged core pyramid, not an implementation
copied into the expected image generator. The reduce kernel is
(1,4,6,4,1)/16 and expand phases are(1,6,1)/8 and(1,1)/2.
Their sums remain one with the actual clamped boundary addressing, including
odd last rows/columns. In real arithmetic every Gaussian level ofF+C is
G(F)+C; subtracting an expanded Gaussian cancelsC in every Laplacian band.
Positive finite SoftPower weights therefore combine a common coefficient,
regardless of differences in those weights; zero denominators use the mean.
BaseMean averages the five residual constants to208. Collapse then reconstructs
the common scene plus208. This is not an assertion of equal weight bits.

A conservative prospective floating-point allowance is one final u16 code
unit, rather than exact output bits. Here is the source-derived engineering
envelope under ordinary IEEE f32 arithmetic. Set u=2^-24 and M=8192;
ideal Gaussians and partial reconstructions stay belowM with over800 units
of input headroom. Allow32*u*M per two-axis reduce,16*u*M per expand,
2*u*M per add/subtract,32*u*M for a five-term normalized nonnegative weighted
mean, and12*u*M for the five-term base mean. These exceed the serial tap and
sum operation counts. Gaussian levelk errors are at most32*k*u*M;
after differencing and merging, the three Laplacian allowances are
(82,146,210)*u*M. The base allowance is108*u*M and three collapse steps
add54*u*M. The total is600*u*M; doubling for higher-order terms and error
in operands gives1200*u*M=0.5859375 code units. Rounding an integer target
within this envelope can differ by at most one code unit.

This calculation assumes finite arithmetic and gradual underflow; it is not
a measured precision result or universal proof for arbitrary images. The
fixed proxy range, nonnegative smoothed squared coefficients and exponent
below4 keep active weight products far from overflow. Nonzero exponential
weights are bounded below by the source's exp(-80) clamp; absolute subnormal
product rounding divided by that lower bound is negligible relative to the
allowance. The exponent-two band has normal active weights for this integer
fixture's f32 coefficient grid; exact zero follows the fallback route.
No accuracy assumption about equal ln/exp results across frames is needed.
Actual nonfinite output must refuse. A changed coefficient/operator or range
requires a new argument, not reuse of this allowance.

Negative controls for case04 must change the actual operand by at least8
code units or use explicitly wrong last-row/column/corner pixels known to
exceed the one-unit tolerance. A one-unit corruption would be an invalid
negative control for this predicate. All actual output codes, including the
flat patch and boundary sites, remain in the comparison. The tolerance is
fixed before fixture construction and is not widened after results.

The existing a_laplacian_pyramid_reconstructs_its_input core test names37x23,
129x71 and64-square shapes with an error bar below0.01. This continuation did
not execute that test; it is source context, not new evidence. The new case
exercises generalized consumer layout through the full output route. It does
not replace universal core arithmetic or visual-quality validation.

## Execution-source review

The root release constructor and external capture wrapper were read as
source. The constructor chains only build,prepare,render,verify, preserves an
exact source archive and reads every archived buffer back, and emits exactly24
render commands from the authenticated fixture index. The capture wrapper
binds itself and the controller to the source map, binds the exact controller
argv to the release SHA, and retains raw stdout/stderr, actual exit and the
complete externally observed controller interval.

The controller's exact rows distinguish the nine success exits from the
fifteen expected refusal exits, with late failures after four folds. Literal
old index/report/output pins plus the held report's manifest/output links
supply v1 provenance; the root wrapper's Python/profile input list alone
does not. Product stdout must equal its actual saved report bytes. A failure
cleanup is not allowed to turn an expected refusal into an admitted child.
The build helper alone may perform explicitly recorded owned-Job cleanup
after direct Cargo zero and pipe EOF. That is intentional cleanup when used,
not natural process exit or a performance benchmark.

The first root constructor draft checked512 sources/16MiB only after content
hashing and allowed64MiB per source read. I raised that distinction. The
reviewed8254-byte revision now checks the path population and positive4MiB
per-file/16MiB aggregate declared extents before content hashing, caps every
source content read at4MiB and retains the post-read sum check. Enumeration
is still non-atomic. External stdout8KiB/stderr32KiB are checked after process
exit, not intercepted as growing streams. Their normal fixed-source bounds,
externally retained intervals and full reservations must not be described as
hard streaming enforcement.

I read the entire held controller and helper, their retained primitives and
the metadata construction source/observed JSON without executing it. The
helper diff from M194h changes only the exact Cargo command guard; the nearer
common-TIFF predecessor differs only in the fixed target directory. All
process, pipe, Job, terminal accounting and intentional cleanup bodies remain.

The normal fixed schedule has108 actual product artifact roles:70 from nine
successes,26 from thirteen early refusals and12 from two late-four-fold
refusals. The retained construction includes these,24 child refs,18 prior
bundle refs,24 operations, a release ref, command4KiB, environment8KiB and
64KiB miscellaneous allowance. The author's reported255854-byte proxy fits
the256KiB parent cap with6290B margin. I checked field/role coverage, not the
execution of that metadata constructor. The ASCII<=512-character path
qualification is material; root must inspect the actual fixed release paths.
The build and verify parents have fewer repeated rows; compiler-message and
accounting fields belong to the remaining-fields allowance.

I checked the physical file formulas in that construction: simultaneous child
logs/receipts, product or prepared/checker families, canonical plus staged
parent and tail are included. The inherited scanner additionally withholds
3*256KiB. Verify19MiB fits that construction; the earlier18MiB draft did not.
All seven controller atomic calls pass256KiB explicitly despite the reused
function's definition-time64KiB default. No assertion is made that arbitrary
failed metadata will fit; failure must preserve the prior durable evidence.
The product N8 final192KiB report has its separate independent construction
reviewed below; this parent estimate does not discharge it.

Parent/Job CPU is cumulative user+kernel, each completed owned Job once plus
live Job and current parent CPU. Terminal samples are taken after canonical
publication; the fixed2CPU/3wall allowance and actual externally observed
interval/exit remain necessary. Child Job memory limits are not controller
address-space bounds. Sampled disk scans are not atomic file-system snapshots.
No stage-reservation number here is a measured performance result.

## Closing reviewed pins and limits

| Source | Bytes | SHA256 |
| --- | ---: | --- |
| amended independent-spec.md | 18544 | b05c4dcc9e1ac8022655f36c8de275e561cd7588435a9c337f4e385913448061 |
| independent-controls.py (focused interface/delta review) | 65751 | be722b454916fe949202cb72b91a25f1a93c32179ced70dd9247cacc01d02d75 |
| independent-spec-draft-1.md | 12851 | f1d8a635951a70ee097bce91960c398b2c461666dff1badf295847b6c1a0a12d |
| run-stage.py | 32861 | 41b7bfca70096a64f29f4d231740fb63af39f5048f4daa96c92bfc5a607393c3 |
| bounded-build-process.py | 16517 | 97cf2d4a587c95a111a738330a66a24d9b003debb69ee0346cecd3c9955151d9 |
| run-stage-contract.md | 14705 | 962bfd1ca292c1cf7e69c9eb83bf3d44ff72f777eb963892ac7c8adaf39c1b60 |
| stage-layout-construction.md | 3414 | 2fcdd7635454561b65487b2a01a11dd0098f952767fc2a66199e662baa6a49cb |
| prepare-release.py | 8315 | 8647d7e67c2b34f9adfe51adee9a13eba72f57a5c3cd9ba005813cd994c85ba6 |
| capture-stage.py | 3845 | 1e8cdd868bf6bbfa0e192355f2d83632ff9a87f733039dbf7d11916c7cc0a6a5 |

At the final held checker pin I performed a focused source read of the
offset literal/predicate/destroyers, entire bounded-error encoding, retained
case completion, same-geometry band-gain consistency and exact128MiB render
allocation. The whole encoded error object is capped1024B, not only its
unescaped message. Same-grid beta equality is an actual retained-value
consistency check; it does not independently calibrate core BandGain. The
three offset faults use the very same<=1 predicate as the actual output.
The preceding-column fault differs from the last-column ideal by well over
one even allowing rounding. Missing actual operands cannot pass a control.

This was not a full independent source verification of the entire checker.
Root separately reviews that source. My scope covers the amended scene and
oracle choices, the specification, these final interfaces/deltas and the
controller/helper/resource contract. The final control table remains135,
and the product invocation population remains24.

The final specification adds the independent author's N8 report construction.
I read that proof and checked the field categories against the reviewed
product source: full eight-input plan, all eight consumed rows and frame refs,
runtime beta, gate, observer and encoding.1024-backslash paths,48-character
IDs,64-digit hashes, wide extents/floats and repeated arrays conservatively
cover the fixed path recipe; encoded pixel bytes are omitted by serde(skip).
The author's metadata-only reported extents are plan26009B, frame6745B,
prepublication100763B, final102906B and final with an escaped2048-character
error115205B. These fit the16KiB frame,176KiB prepublication and192KiB final
limits. I did not rerun that constructor or turn those derived extents into
measured product outcomes. Actual fixed paths and actual publications still
must be checked; arbitrary caller path/error lengths are not guaranteed.

The final8315-byte constructor adds stage-layout-construction.md and the
preserved original specification to the frozen source map. I read that
two-name delta and authenticated its final hash. The support-document
omission is resolved. No blocking source issue remains in this review and
no numerical source, population or output threshold change is requested.
Root still owns the separate committed grant and actual execution release.

Admissible future conclusion, if the actual fixed checks pass: bounded common
RGB count/dimension software integration, exact held v1 positive compatibility
and the specified finite structured-image behavior. Inadmissible conclusions
include physical noise calibration, universal odd-pyramid arithmetic, general
focus-stack quality, fractional resampling, arbitrary contributors or SOTA.
Actual saved verification should independently re-choose interior/flat/row/
column/corner classifications and distinguish actual arrays from source-bound
reported diagnostics. Repeating this same source argument is not another
independent numerical result.

## Final provenance addendum before release

SOURCE-VERIFIED only; no constructor rerun. I read the exact retained
product-layout-construction.md5577B,
SHA2564ec6bb46560dd178553dbf86bb1cf62eb4dfbe3d9ca0f26718466efa57bb138b,
including its already-run metadata body and stdout. Its field coverage matches
the producer's initial envelope, full plan, eight consumed rows/frame refs,
runtime, per-fold/final gate, observer, encoding and output publication. All
serialized Encoded fields are included; image bytes remain serde-skipped.
The independently oversized path/scalar and observer combination is explicitly
hypothetical. The reported extents remain the author's metadata construction,
not a new product or numerical result by this reviewer.

The final prepare-release.py is8348B,
SHA256541152c29405d31fbae305ca502e13ae600fb1c2954e1d4d6f9e2951e4314261.
Removing only its one product-layout-construction.md source-map entry restores
the exact previous8315-byte buffer and SHA2568647d7e67c2b34f9adfe51adee9a13eba72f57a5c3cd9ba005813cd994c85ba6.
That metadata-only byte comparison ran and passed; no execution-policy or
numerical source changed. The supporting constructor is now archived with
the other frozen sources. No blocking source issue remains. This review is
held immutable for the four released stages; root owns their separate grants
and actual result admission.

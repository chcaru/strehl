# Independent common-TIFF stack controls

SOURCE ONLY, prospective version 1. Root decision e55d319b adopts these twelve cases.
No product, TIFF generator or checker has run. These fixtures commission the new stack-to-image consumer;
they do not rerun M165/M194h, establish physical RGB noise, qualify real geometry,
or select a merge-quality policy.

## Consumer and independent choices

The consumer is the new explicit stack-manifest mode of strehl-common-input.
It folds three ordered 128 by 96 full-resolution RGB16 images into one persistent
three-plane BandMerge, releases each frame, finishes once, and writes already-RGB
linearized ProPhoto/ROMM-primaries D50. Coordinates are common-RGB pixels with
identity geometry. There is no CFA half-grid, black subtraction, white balance,
demosaic, matrix, exposure, transfer curve, resampling or external image input.

The exact held M165 profile is 548 bytes, SHA-256
16c8cad1299737e912d72ad83e959a9f879519a5fd2aaddb82ce103ebeca08ef.
Its embedded declaration is checked separately from literal pixel semantics.
The retained fork's PROPHOTO_DISPROVED verdict is unchanged.

The independent implementation uses only Python's standard library. It neither
imports the new writer nor translates its encoding routine. Its TIFF generator
places the IFD after the image payload, uses three distinct strip heights
24/32/48 for ordered inputs, and writes the existing exact 13-tag input subset.
The independent reader follows the offset tables, checks nonoverlapping ranges
and bounds, reconstructs row-major little-endian RGB16, and separately hashes
the whole file, pixel payload and ICC. Output additionally requires Predictor317=1 and fixed Software305, and admits
only identity Orientation274 and X/YResolution282/283 plus ResolutionUnit296.
The held writer emits 18 tags, with BitsPerSample/SampleFormat triples and
PlanarConfiguration284=1. RowsPerStrip may exceed image height (the encoder's
1303); the sole strip must still contain exactly the actual 96 rows.
Unspecified colour-changing metadata is rejected.

## Fixed fixture recipes

All samples remain inside 0..65535 with no generating clip.

1. Constant contributors, one frame each:
   (12000,17000,23000), (15000,20000,26000), (24000,32000,38000).
   The literal answer at every output pixel is (17000,23000,29000).
   No input equals that answer. The oracle is independent integer arithmetic,
   not a recomputation of BandMerge. A copied first/last frame, omitted frame,
   duplicate fold or wrong divisor can fail it. Three distinct actual fold
   identities and final frame count three are separately mandatory.

2. Address and colour: three byte-distinct TIFFs with identical payloads.
   At each (x,y), R=4000+101*x+7*y, G=18000+13*x+83*y,
   B=36000+47*x+19*y. A rectangular witness 16<=x<48, 24<=y<56
   instead has literal RGB (8192,24576,49152).
   This asymmetric grid detects transposition, one-pixel movement, channel
   permutation and repeated transfer. Fixed Hull::InputRange clamps identical
   inputs to their exact codes, so the declared bound is exact RGB16 equality
   everywhere. This verifies address/colour integration; it does not certify
   unrestricted pyramid reconstruction.

3. Mixed base, identical in all three noiseless frames:
   base channels (14000,24000,34000). For x>=64, add +4096 when
   ((x//4)+(y//4)) is even, otherwise -4096, to all channels.
   x<64 is exactly flat. The noiseless null uses these codes unchanged.

4. Mixed noisy base: add -8 or +8 independently by a fixed counter-domain
   SHA-256 bit for each (frame,y,x,channel). The domain is
   ASCII common-tiff-stack-rademacher-v1 followed by little-endian u32
   frame,y,x,channel; digest byte0 bit0 selects the sign (+8 if set).
   This is a deterministic simulation of a declared independent Rademacher
   law, not a claim that a finite realization proves independence.
   Per-channel generating variance is 64 code-squared; c=(1,2,1)/4
   has generating variance 24. c is a selection proxy, not ProPhoto luminance.
   The exact actual injected constant f32 array and explicit white BandGain
   values must be retained. A variance=1 substitution is a registered refusal.
   No energy-derived variance or private noise estimate is permitted.

## Fixed product population

Root decision e55d319b adopts twelve invocations, in this order. Exact source
review and root's hashed release still precede fixture preparation. No reruns.

| Ordinal | Case | Observer | Expected |
|---|---|---|---|
| 0 | constant contributors | off | complete, exact literal mean |
| 1 | identical address/colour | off | complete, exact literal full grid |
| 2 | mixed noiseless null | on | complete, exact literal full grid |
| 3 | mixed noisy | off | complete |
| 4 | same mixed noisy | on | complete |
| 5 | same mixed noisy | placebo | complete |
| 6 | mixed noisy, unsupported provenance | off | semantic refusal |
| 7 | mixed noisy, proxy variance 1 | off | noise refusal |
| 8 | mixed noisy, wrong admitted-profile declaration | off | colour refusal |
| 9 | mixed noisy, camera-native output declaration | off | output-semantic refusal |
| 10 | first two valid, third valid 127x96 TIFF | off | refusal after exact two folds |
| 11 | first two valid, third actual payload altered versus manifest | off | refusal after exact two folds |

Cases 10/11 require authenticating each image when it is visited; an early
structural manifest refusal is not the promised exercised two-frame prefix.
All output paths are fresh and distinct. Refused cases must lack a newly
admitted TIFF; any retained partial/output witness stays explicitly unadmitted.
No failed case is replaced with a successful rerun.

On/off/placebo compare the whole TIFF and pixel payload, not a receipt containing
observer names or per-run paths. Per-case outer exit, canonical receipt and
visited population must all agree before admission. The observer must really
exercise its named path; a flag without a retained exercised witness is
insufficient. Actual input hashes are checked again after the three arms.

## Gate scope and verifier power

Use the existing public averaged_fraction() observation only in observer on,
after actual folds. Off does not inspect it; placebo allocates four matching
GateRow objects without reading the merge. This new gate observer and the output
observer vary together in cases 3/4/5; whole-TIFF equality commissions both. It describes zero accumulated denominator versus positive accumulated
denominator at each shared RGB level, not each individual frame's classification.
Reconstruct integer counts from its four f64 ratios and the actual fixed level sizes.
The actual noisy-on case4 final census must exercise both zero and positive
populations among the three Laplacian levels. On null case2 retains its census;
off/placebo contain no measured levels. EXCLUDE the always-mean base from this test: otherwise
its zeros would make the below-floor check vacuous. Preserve all fractions,
counts and the flat/null outcomes; a missing mixture stops this version.

Sixteen fixed saved-data verifier controls (ten negatives and six positives)
run through the same corresponding predicates:
copied input instead of mean; one-pixel horizontal address shift; RGB swap;
second gamma curve on the literal witness; declared variance 1; an actual ICC-byte flip outside its signature parsed again through the same output-profile predicate; omitted or duplicate contributor;
an actual in-memory TIFF pixel-byte flip parsed again against observer identity; absent third fold; restoration.
The six restorations/positive cases include float-versus-integer spelling of
the exact noise values; bool is excluded. Each negative names the exact expected
ValueError, not merely any exception. These are
verifier controls, distinct from actual product invocations. An output profile
hash by itself cannot detect a transfer curve; the literal pixel oracle can.

## Finite implementation and output boundaries

Propose fixture preparation <=5 CPU seconds, 10 wall seconds, 4 MiB files;
saved verification <=20 CPU seconds, 30 wall seconds, 4 MiB files, <=64 MiB
named buffers. Root must incorporate these into its finite release before any
execution. No new process harness is required: actual product commands and
external receipts use the existing commissioned owned-process helper, whose
whole Job accounting, exit and raw streams are mandatory evidence.

The source will provide prepare and verify subcommands with exact source,
fixture-manifest and saved-run-bundle FileRefs. Each read is bounded and hashed
from the same bytes parsed, preserving same-API before/after identity and
cross-API shared identity on Windows. Source files must have positive extents;
canonical empty evidence is a separate role. Fresh creation and fixed result
caps precede work. Fixture/source manifest and final stdout are bounded.
The complete seven-key product manifest is source-contract.md; all fields and
the full explicit MergeConfig are literal in the independent source. Receipt
schema is common-tiff-stack-result-v1; immutable completed fold receipts use
common-tiff-stack-frame-v1. Product errors6..9 occur before binary/plan/profile
population; those absent fields are valid refused prefixes, with execution
identity supplied by the root-bound child command and executable. Errors10/11
retain exactly two immutable fold receipts and no final output.

Exact CLI (pinned Python -I -S -B precedes the source path):
- independent-controls.py prepare --output ABS/prepare-1/fixtures --source-sha256 SHA
- independent-controls.py verify --fixtures ABS/prepare-1/fixtures/index.json
  --fixtures-sha256 SHA --run-bundle ABS/render-bundle-1.json
  --run-bundle-sha256 SHA --output ABS/verify-1/check --source-sha256 SHA

The eight-key fixture index is {schema,source,spec,profile,recipe,recipe_sha256,
generated_files,cases}, schema common-tiff-stack-independent-fixtures-v1.
Its27 generated files are14 TIFFs,12 case manifests and one recipe; the index
is a28th file. Its actual generated-file map authenticates the deliberately
altered third TIFF, while that case's product manifest intentionally binds the
old hash. The controller must preserve this distinction. Prepared stdout schema
common-tiff-stack-independent-preparation-v1/status PREPARED_UNRUN_FIXTURES.

The independent verifier consumes root's exact six-role saved render bundle
{result,tail,outer,stdout,stderr,exit}; it launches nothing. It rehashes the
released source map and actual compiled executable, authenticates every child
Job/log/argv and case publication, and sums final child Job CPU once. Parent
CPU is a sample plus2-second allowance, not a terminated-parent measurement.
Outer actual exit and whole wall remain mandatory. Incomplete cases remain
explicit per-case nonadmissions, distinct from a failure inside the verifier.

Final schema common-tiff-stack-independent-verification-v1/status
PASS_COMMON_RGB_STACK_SOFTWARE_INTEGRATION or REFUSED is written to
verify-1/check/result.json; raw stdout is identical. Own work includes the
declared0.25CPU/0.5wall publication tail; root verifies actual outer tail.
A64MiB named-buffer source bound uses streamed1MiB executable hashing and
bounded4MiB source reads, not an entire executable allocation. This is not a
process-memory measurement.

Decision: a complete pass establishes this software consumer on these three
simulation cases. Failure stops this version without relaxed bars, a larger
image campaign or a fallback noise model. Real conversion/noise propagation,
nonidentity per-frame geometry and comparator colour semantics remain open.

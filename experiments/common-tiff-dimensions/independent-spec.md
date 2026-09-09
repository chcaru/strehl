# Independent common-TIFF dimensions commission

SOURCE ONLY, fixed before fixture generation or product execution, 2026-09-08.
Author: coordinate_verification, independent of the v2 product change. This
specification defines24 product invocations and saved checks. It does not
release a build, fixture generator, image read, product call or checker.

Read charter.md, implementation-contract.md and the named prior-art/consumer
choices in ../sampler-boundary/next-consumer-audit.md. The previous three-frame
consumer and sampler repair are completed separate work. No old campaign is
rerun. Reuse our admitted independent TIFF container/reader conventions and
exact548-byte M165 ICC, not the new product writer as an expected-image oracle.

## Consumer, fixed cases and admission

Identity common-RGB pixel gauge; u16 RGB storage, existing f32 merge, exactly
three Laplacian bands plus base, fixed HardFloor/InputRange configuration,
two Rayon threads, same profile and two declared synthetic noise laws. This
is bounded software generalization, not physical noise calibration, geometry,
quality, focus spacing, a frame-count quality threshold or new defaults.

Each row has a separate manifest/report/output directory. Expected semantic
refusals still require the actual invocation, clean terminal process/Job,
expected exit1, complete stdout/report equality, exact reason and saved prefix.
Missing/unvisited records or operational failure cannot count as that refusal.

| Ordinal / ID | Schema | N / grid | Mode | Expected result / folds |
|---|---|---|---|---|
| 00 mean-two-min | v2 | 2 /64x64 | off | complete /2 |
| 01 mean-five-odd | v2 | 5 /129x97 | off | complete /5 |
| 02 mean-eight-max | v2 | 8 /512x512 | off | complete /8 |
| 03 odd-address | v2 | 5 /129x97 | on | complete /5 |
| 04 odd-offset | v2 | 5 /129x97 | on | complete /5 |
| 05 odd-noisy-off | v2 | 5 /129x97 | off | complete /5 |
| 06 odd-noisy-on | v2 | 5 /129x97 | on | complete /5 |
| 07 odd-noisy-placebo | v2 | 5 /129x97 | placebo | complete /5 |
| 08 legacy-constant | v1 | 3 /128x96 | off | complete /3, archived whole TIFF |
| 09 count-zero | v2 | 0 /129x97 | off | count refusal /0 |
| 10 count-one | v2 | 1 /129x97 | off | count refusal /0 |
| 11 count-nine | v2 | 9 /512x512 | off | count refusal /0 |
| 12 width-low | v2 | 5 /63x97 | off | grid refusal /0 |
| 13 width-high | v2 | 5 /513x97 | off | grid refusal /0 |
| 14 height-low | v2 | 5 /129x63 | off | grid refusal /0 |
| 15 height-high | v2 | 5 /129x513 | off | grid refusal /0 |
| 16 width-u32-overflow | v2 | 5 /4294967296x97 | off | manifest JSON refusal /0 |
| 17 legacy-count-two | v1 | 2 /128x96 | off | v1 count refusal /0 |
| 18 legacy-odd | v1 | 3 /129x97 | off | grid refusal /0 |
| 19 duplicate-input | v2 | 5 /129x97 | off | duplicate ID refusal /0 |
| 20 wrong-profile | v2 | 5 /129x97 | off | profile refusal /0 |
| 21 wrong-proxy-variance | v2 | 5 /129x97 | off | covariance/proxy refusal /0 |
| 22 last-geometry | v2 | 5 /129x97 | off | final input refusal /4 |
| 23 last-file-hash | v2 | 5 /129x97 | off | final input refusal /4 |

Manifest schema strings are common-tiff-stack-v1/v2. Exact rejection strings:
09..11: v2 requires two to eight inputs; 12..15 and18: unsupported common grid;
17: v1 requires exactly three inputs; 19: duplicate input id;
20: unadmitted input profile; 21: unsupported noise covariance or proxy variance;
22: TIFF dimensions do not match common grid; 23: file hash mismatch.
16 must be a manifest JSON unsigned32 range/type rejection before any decode;
require prefix manifest JSON: plus the named overflowing value, not a brittle
full serde error string. It does not exercise multiplication overflow: axis
bounds make that defensive branch unreachable for admitted dimensions.

09/10/12..16 reuse valid odd constant inputs, changing only the declared field
or count. 11 has eight valid max-grid contributors plus a genuine ninth TIFF
with constant(45000,50000,55000), preventing a missing/duplicate file from
standing in for count rejection. 17 uses two of the held legacy inputs;18 uses
three valid odd address inputs. 19 repeats the first complete odd constant
entry as the second, preserving five entries but duplicating its ID/file.
20 changes only the declared ICC digest;21 uses valid noisy input provenance
and RGB covariance with proxy_variance=1. 22 replaces only the fifth odd
constant TIFF with valid128x97 geometry and correct actual hashes. 23 points
the fifth input to a same-size one-pixel-altered TIFF but retains its original
expected file/pixel digests. The fixture index separately binds actual altered
bytes; it never substitutes those for the product's deliberately wrong claim.

## Literal contributors and output oracles

At ordinal i=0..N-1, constant RGB is
(8000+240*2^i,16000+160*2^i,24000+80*2^i). All samples are bounded integers.
Independent mean rounding uses integer sums: floor((2*sum+N)/(2*N)). The fixed
complete means are N2:(8360,16240,24120), N5:(9488,16992,24496), and
N8:(15650,21100,26550). Check every actual output RGB code, plus every actual
ordered contributor identity, per-fold counter and consumed pixel hash.

Before running product controls, source-defined preparation checks all108
competing means:15 single omissions with renormalized N-1;15 appended duplicate
contributors with N+1;78 ordered replacement pairs i!=j with unchanged N.
Each must differ from the intended rounded RGB mean. No contributor equals
its stack mean. These are deterministic arithmetic power checks, not extra
product calls or independent statistical observations. During saved checking,
use the same whole-image constant predicate with each wrong expected mean;
it must reject the actual admitted constant output. Restored expected means
must pass. A missing/duplicated fold record separately fails ordered-prefix
admission even if an unrelated image happened to match.

Odd address RGB before edge overrides is
R=4000+101*x+7*y, G=18000+13*x+83*y, B=36000+47*x+19*y.
The fixed interior patch16<=x<48,24<=y<56 is(8192,24576,49152).
Then x=128 becomes(50000+y,22000+2*y,10000+3*y);
y=96 becomes(12000+3*x,52000+x,32000+2*x), and their corner is finally
(60001,45003,15007). All five frames have identical codes but distinct embedded
provenance/FileRefs. Require every final code, final row/column/corner and
interior values. InputRange on identical frames supplies this address oracle;
it does not show pyramid reconstruction quality on differing frames.

Case04 odd-offset replaces the unexecuted identical odd-null draft prospectively.
The exact original draft is preserved in independent-spec-draft-1.md, SHA256
f1d8a635951a70ee097bce91960c398b2c461666dff1badf295847b6c1a0a12d.
No fixture or product call preceded this amendment. Same five TIFFs and24 calls.

Let P=(13*x+29*y)%997; set the interior16<=x<48,24<=y<56 to512;
then last column x128 to1200+y, last row y96 to1400+x, corner to1777.
Base RGB=(1000+P,3000+P,5000+P). Five scalar frame offsets are
[0,40,120,280,600]. The independent ideal is base+208, an integer image,
208/392 code units from the input hull endpoints and unequal to every input.
Require every actual output code within1 of this ideal. Do not infer exact
rounded identity. The fixed interior flat patch is checked along with all
structured pixels; no sharpness metric or quality claim is introduced.

Source-derived finite-fixture engineering bound, assuming ordinary finite
IEEE f32 basic arithmetic: u=2^-24, M=8192, actual inputs<=7377. Both axes of
reduce have positive unit-sum taps; both expand phases have positive unit-sum
taps including replicated odd endpoints. Exact offsets cancel in Laplacian
bands; BaseMean averages them. The positive normalized weighted combination
of nearly common coefficients does not require identical weights; zero-weight
sites use Mean. Sharpen changes the exponent of the weights, not coefficients.
Conservative per-operation envelopes in uM: two-axis reduce32, expand16,
add/sub2, five-term weighted combination32, base mean12. Merged Laplacian
bounds82/146/210 and base108 plus collapse54 give600uM; doubling for higher
order/error-input allowances gives1200uM=0.5859375 code units. Nearest-integer
output is therefore checked at<=1. This is a source argument for this bounded
fixture, not a verified general floating-point theorem or measured accuracy.
Active exponent<4 and bounded energies/products must remain finite; actual
finite output remains mandatory. Fixed +8, preceding-last-column and corner+8
saved-copy faults must reject through the same <=1 predicate, then restore.

Odd noisy inputs use base(14000,24000,34000) on x<65. On x>=65 add4096 when
(x//4+y//4)%2==0, otherwise subtract4096. Add per-channel +/-8 by the fixed
SHA recipe with domain common-tiff-dimensions-rademacher-v1 and LE u32
(frame,y,x,channel); +8 iff first digest-byte low bit1, otherwise -8.
This is declared simulation, not empirical proof of physical independence.

Noise remains zero or diag(64,64,64), zero cross-covariances, proxy24 from
(R+2G+B)/4, RGB16-code-squared. Recompute actual input payload/proxy f32/variance
array hashes from saved independent pixels, before and after each fold. Require
the retained actual white BandGain vector and identical injected first-three
coefficients across all folds/modes; no independently invented calibration.

For every on receipt independently require ceil-halved level geometry. Odd
levels are129x97,65x49,33x25,17x13. Check four exact site populations, integer
zero+positive denominator counts and the reported fraction. No base or RGB
plane multiplicity may create a Laplacian mixture pass. For final noisy-on,
summed Laplacian zero and positive populations must both be nonzero. These are
accumulated-denominator observations, not per-frame admission decisions. The
mixture assertion is collective across the final three Laplacian levels; it
does not assert a mixture at each level or after each fold.

Noisy off/on/placebo whole TIFFs and pixel hashes must match. On must actually
visit four gate rows after each fold and3*129*97 output samples; off observes
none, placebo allocates matching shapes without reading merge. Mandatory
hashes remain common. A metadata claim of read-only access is insufficient.

Legacy08 reuses the existing held three constant input TIFFs and binds the
previous admitted case00 output. Only fresh output/report paths and new binary
change. Require exact whole TIFF identity with that one archived output and
old v1 description/software/profile/geometry/count/caps. Do not regenerate or
rerun the other eleven old product cases.

## Independent container, metadata and falsifiers

Use our own little-endian classic TIFF generator: RGB16 payload before the
IFD, descending13 input tags, exact ICC/provenance, independently parsed strip
addresses. New contributor strip_rows cycle(17,31,48,64,97,23,41,73), truncated
by the actual height only in final strip byte counts. This includes nondividing
odd strips and multiple layouts; no product encoder implementation is copied.
The output reader additionally accepts the exact declared uncompressed writer
tags, Predictor1 and schema-specific description/software. It checks exact
nonoverlapping extents and full interleaved RGB codes from the authenticated
buffer. Preserve ordinary/verbatim local-drive path association by canonical
location+extent+hash; distinct same-content files remain distinct.

Source-defined saved-check destroyers, beyond the108 mean competitors, are:
remove or duplicate a completed fold; change a retained merge_frames counter;
change odd level0 width; floor-reduce level1 geometry; delete the last address
column; replace the last address row with its preceding row; flip the final
corner pixel; swap R/B; add a one-pixel cyclic x address shift; change actual
noisy-on TIFF pixel bits; change only actual ICC bytes; change proxy variance
to1 or a numeric-zero covariance entry toFalse. Every fault uses the same
admission predicate as real saved checks, names its exact rejection category,
and has an actual changed operand plus restoration. Keep a fixed table before
execution; no new product cases or thresholds after looking at results.

Each actual case retains its complete prefix and operational status. The
checker continues over all24 retained cases after a case failure; absent cases
are explicitly no linked completed case, possibly attempted. Controls requiring
missing successful operands are unavailable, never passed. No positive image
alone certifies successful publication. Initial request envelope remains v1;
result/frame v2 starts only after admitted v2 manifest. Early semantic failure
may have no binary/profile/runtime in the product receipt: actual controller
binary/argv binding still proves which executable ran.

## Finite source, fixtures and proposed execution interface

New independent files: independent-controls.py, this independent-spec.md and
the preserved unexecuted independent-spec-draft-1.md. No container module. No old
frozen source, fixture or result is edited. Prepare grammar:

    PY -I -S -B independent-controls.py prepare --output ABS/prepare-1/fixtures --source-sha256 SHA

Saved verify grammar:

    PY -I -S -B independent-controls.py verify --fixtures ABS/prepare-1/fixtures/index.json --fixtures-sha256 SHA --run-bundle ABS/render-bundle-1.json --run-bundle-sha256 SHA --output ABS/verify-1/check --source-sha256 SHA

Index binds source/spec/profile, exact recipe, every generated file, historical
legacy evidence and24 command rows. Product CLI/manifest keys stay unchanged.
Root's future controller supplies exact actual binary, six-role render bundle,
per-case child/refusal stdout and current source release. No product launching
inside this independent script. Schemas will be closed before source freeze.

Source-derived fixture cap:33 new TIFFs (30 positive contributors, ninth-count
witness and two late faults),24 manifests, one recipe and index. Payload sum
15,856,062 bytes;33*64KiB container allowance +24*64KiB manifests +320KiB
recipe/index totals19,919,294 bytes, below20MiB. Reserve32MiB for fixtures and
preparation receipts; legacy files are rebound/read, not recopied. Largest
single new TIFF<=1,638,400 bytes. Keep at most one input's expanded pixels at
a time while preparing; a32MiB payload cap is not a process-memory claim.

The product contract's worst per-case output+stage/stdout subtotal4,001,792B
excludes inputs, stderr, executable and orchestration. Root must fix the full
build/prepare/render/verify CPU, wall, memory and aggregate file grant before
any execution; none is implied by this source-only spec. Suggested independent
prepare/checker ceilings are respectively20CPU/40wall and45CPU/90wall, each
1GiB process memory,32MiB prepared artifacts and16MiB checker family. Exact
source-defined bounds and output constructors will be reviewed before hold.
No build, test, fixture generation, image read or numerical run has occurred.

## Final fixed implementation and allocation

There are135 saved-check control rows:108 competing means, three restored
means,14 original destroyers, six associated restorations, three odd-offset
destroyers and one offset restoration. Every row is attempted independently;
missing admitted operands are explicit unavailable rows, never passing rows.
The legacy whole-output check measures only its actual small TIFF; preservation
of legacy input/writer caps is a source review claim, not an over-cap exercise.

Root adopted build600CPU/300wall/3GiB/128MiB retained+4GiB scratch;
prepare30CPU/60wall/1GiB/34MiB; render180CPU/240wall/1GiB/128MiB with each
product20CPU/20wall; verify60CPU/120wall/1GiB/19MiB. The independent child
uses20CPU/40wall prepare and45CPU/90wall verify including publication reserve.
Root metadata is four10CPU/20wall slices and32MiB. Historical costs remain.

Index has exactly nine keys: schema,source,spec,profile,recipe,recipe_sha256,
legacy,generated_files,cases. Each of24 case rows has11 keys, includingversion.
Prepare stdout is one bounded64KiB JSON receipt. Verify emits byte-identical
result.json and raw stdout, each<=1MiB. Progress is one atomic1MiB JSON plus
one1MiB transient stage, charged simultaneously; no source/data files copied.
Checker own family: result1MiB+progress1MiB+stage1MiB<=3MiB, inside16MiB.
The outer19MiB grant also covers log1MiB, child32KiB, two256KiB terminal
slots,8KiB tail and the inherited scan allowance. Whole owned Job and actual
outer interval/exit remain required; own CPU/wall fields are samples before
publication. A1CPU/2wall allowance is reserved before final serialization,
and final checks after write/flush remain inside the child's45/90 bound.

Finite report construction:24 summaries each<=16KiB (384KiB),135 controls
each<=2KiB (270KiB),26 errors/operational notices each<=4KiB (104KiB), and
64KiB for source/bundle/accounting/framing totals822KiB<1MiB. These are
individually encoded caps enforced before insertion; partial/unvisited rows
obey the same envelope. All progress prefixes are bounded by that final shape.
A refused checker is retained separately from an expected product refusal.

## Independent product report capacity re-choice

Executed source/metadata serialization only, with no candidate import, TIFF
payload, fixture, numerical operator or product command: construct every
normal product field read from mod.rs and writer.rs, all eight consumed rows,
all eight frame references, full manifest with eight inputs, runtime beta,
final gate, observer and encoding. Use1024 backslashes for every FileRef and
output path,48-character IDs,64-character digests, nine argv entries each512
backslashes,256-character scopes, nine-digit extents, wide finite float
spelling, four on-gate rows and both observer hash fields (a conservative
superset). This dominates the fixed absolute-path recipe and ordinary/verbatim
canonical names; it is not a theorem about arbitrary caller directory depth.
Source path intake is capped384 chars and the fixed root/fixture paths are
shorter. Repeat arrays for eight folds/refs; Python compact ensure_ascii JSON
has one trailing newline, matching the producer's compact encoding extent.

Derived plan26,009B; per-frame6,745B<16,384; prepublication100,763B<180,224;
complete final102,906B<196,608. Adding2048 ASCII control characters to error
(full six-byte JSON escaping each) yields115,205B<196,608. No encoded pixels
occur in these records: writer bytes has serde(skip). Operational refusals
remain governed by actual capacity guards and retained external exit.

## Build2 path-only correction

After the preserved build1 scanner refusal, root authorized exactly one
independent checker source spelling change: build-1/strehl-common-input.exe
to build-2/strehl-common-input.exe. The source before this edit was65,751B,
SHA256 be722b454916fe949202cb72b91a25f1a93c32179ced70dd9247cacc01d02d75,
byte-identical to git6e98e4fd:experiments/common-tiff-dimensions/independent-controls.py.
The changed literal occurs once; reversing only it reproduces that committed
blob exactly. Every other source byte,24 cases,135 controls, fixture recipe,
numerical predicate and observed-data association remains unchanged. No
checker, fixture, product or private control ran during this source correction.

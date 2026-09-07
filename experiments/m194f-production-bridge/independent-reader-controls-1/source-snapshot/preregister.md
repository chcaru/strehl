# M194f: admitted joint-pupil CFA through production

2026-09-07, root. Prospective protocol, to be committed with the allocation
before implementation. M194e has completed independent float and CFA admission.
This is a bounded integration commission, not a quality experiment.

The admitted inputs are the original M194e cfa-emission-1/manifest.json,
SHA f47c2b8720560fe9dbd777eeed3281ce2531f1f2287f5c88ef7b51a083d03299,
and independent-cfa-verification-1/cfa-commission.json,
SHA 706462ad18a5a3846cadd99e1ef24d6b92b77e064df2e34cbe72e45907fc06a6.
The linked genuine float commission is
4bd57b896be0b68c42fb1384a468a4f29cc54139a18a046a678dd97bad408217.
Every referenced prior-art/design review named below lives in the sibling
experiments/m194e-joint-pupil directory; source hashes are in design-sources.json.
No private fixture can substitute for these admitted bytes.

## Existing work and scope

The corrected mechanical search is `next-bridge-prior-art-2.log`. The first
quoted-phrase query was malformed and supplies no absence evidence. Source
inspection in `next-production-bridge.md` identifies the already working M194
prepared-frame seam and M194b/d CFA-to-writer consumers. Reuse their production
body and narrow adapter pattern; preserve the old input meaning and parser.

The named search hits constrain the interpretation: ORCH-veiling and BUILD-ELECT
describe specific older selection-path boundary defects, with rejected causes
and later amendments; they do not establish the present Pyramid's defect on a
new scene. V-DILUTE rejects its proposed stack-depth dilution mechanism, and
V-SELECT's half-stack signature fails; neither authorizes a generic dilution fix.
BUILD-BLEND retains a real residual and corrected noise costs, not zero boundary
error. BUILD-SOFTGATE's depth score is withdrawn as confounded by width. M166's
physical depth/product requirements and M-PHASE0-RHO's refusal of a universal
alias constant remain untouched. This bridge creates no new depth product,
physical reference, alias estimate or image-quality score.

## Proposed input and production mapping

Require the genuine emitted M194e manifest and independent CFA commission,
with both SHA-256 values provided externally. A small test-local Rust reader
must check duplicate/unknown/type-invalid fields, exact association of the
commission with that manifest and float authority, and the admitted model,
source and five actual CFA references. A self-rehashed substitute is not new
authority. Keep current admitted source/evidence bindings intact. Bound file
sizes before reads and check the exact byte array consumed, not a separately
read hash. Recheck current input/source bindings before final completion.

Prospectively bound each JSON input to1,048,576 bytes, using a single open and
`Read::take(limit+1)` before parse or allocation from declared lengths. The CFA
limit is exactly6144 bytes. An appended byte must refuse even when the caller
recomputes its hash. Hash and decode the same bounded buffer; a prior metadata
length check is insufficient. Preserve the source-file hashes and verified
manifest/commission associations separately from this allocation bound.

The existing authority chain includes the CFA commission's child result:
externally trusted CFA-commission SHA -> relative independent_verification
result SHA -> status PASS_CFA_CONVERSION_AND_PROVENANCE, fixture_only=false,
sample_count15360, matching externally trusted manifest/float-commission
digests, and equal source_before/source_after with source_unchanged=true.
Verify the actual recorded source bindings. The gate's own fixed schema,
status, sample count, scope and manifest/float references must agree with that
result. This consumes the already completed independent conversion result;
it neither reruns the mathematical reference nor treats a status string as
authority. Rehashed child substitutions paired with the old external gate
must refuse, alongside the corresponding unchanged-chain companion.

Read five64×48 little-endian u16 CFA payloads, exactly6144 bytes each, active
origin0/stride64/buffer48, RGGB, black512/white15360. Use all original indices
0..4 and explicit identity reference index2 as a coordinate gauge. No best-focus
truth or alignment solve is implied. Construct one injected NoiseModel with
gain0.25DN/e and read-noise4e, ISO160, Fallback provenance and no PRNU; these
are synthetic algorithm coefficients, while all input noise draws remain off.
Use f32 WB `[4/3,1,5/3]` explicitly.

Feed the existing `PyramidFrameSource`, `PreparedPyramid` and
`run_pyramid_prepared`: full-resolution gather/MHC, CameraLinear RGB16,
exposure0/no auto-exposure, Crop/CatmullRom, three requested bands, gate2 and
unchanged default HardFloor. Two workers/two Rayon threads. Disable CA, defect,
photometric and restoration controls; refuse unexpected environment overrides.
Do not expose the small-input debug path that assumes a measured floor entry.

Write the actual domain/cover plan before pixels: input/source/build bindings,
effective configuration and levels, original/local indices, native-to-quad map,
crop origin, dimensions, floor fallback, WB, noise and writer normalization.
Require the supplied plan digest and recomputed plan to agree before rendering.
This fixture has at most one Laplacian band plus a base and no measured floor
band. Record the actual crop; do not require or invent a64×48 TIFF.

## Proposed bounded controls and deciding evidence

The consumer being tested is actual delivered TIFF coordinates and values.
Each control below has a named failure, before inspecting a new output.

| Control | Input that must fail or change | Passing companion |
| --- | --- | --- |
| Authority | wrong external digest; rehashed manifest/map/source associated with old authority; fixture-only CFA status | exact admitted package |
| Storage | short/appended CFA; source changed after planning; integer/type/path/count defects | complete unchanged payload, active samples only |
| Plan | same dimensions but false nonzero native offset; changed setting with stale plan | exact freshly computed plan |
| Output occurrence | supported exposure+1 control must move actual pixels; changed decoded sample control must be live in private API scope | baseline off/count/placebo runs have identical TIFF/pixel bytes |
| Coordinates | independent coordinate-coded constant/affine private fixture with nonzero quad crop catches double crop, wrong origin or second black subtraction | separate scalar MHC/writer oracle on declared interior |
| Input reread | confidence enabled performs actual second decode of all five files; private fault occurs after first successful fold decode and before the second read, not merely after planning | same baseline TIFF bytes with confidence disabled/enabled; all five successful decode counts equal2 |
| Terminal state | any refusal or incomplete file set must not produce a completed receipt | complete actual TIFF and source/plan bindings |

Private coordinate/mutation fixtures are explicitly integration controls, not
M194e optical truth. The genuine intended set needs baseline observer
off/count/placebo, confidence-count, and exposure+1-count. The exposure companion
is a setting-potency control, not a quality arm. Five main RGB TIFFs suffice
unless a control fails.
Confidence also writes an auxiliary Gray16 TIFF on the quad grid; bind and
independently check that sixth delivered file's dimensions, values and bytes.
Reuse the existing `independent_m194_confidence_source_and_null` second-call
fault pattern, adapted to this reader's private files. Do not start an80-output
campaign or compare admission candidates here.

The source observer records successful_decode_counts only after bounded read,
hash and decode succeed. Off/placebo leave those five collected counts zero;
hook_calls is0 off and5 count/placebo at baseline,10 in confidence-count.
Planning/authority file opens are excluded and disclosed. Record mode and
witness in plan/receipt, but compare actual TIFF/pixel bytes for the three
baseline nulls and baseline-count versus confidence-count. A separate private
attempt counter triggers the second-read fault, leaving one successful decode
for that frame; it neither supplies success statistics nor changes healthy
behavior. This prospective extra baseline closes the earlier four-RGB schedule's
missing off/count/placebo companion. It is not a response to observed output.

The independent reader must parse actual full-resolution TIFF strips, tags,
orientation, channels, ICC disposition and samples, check complete file/pixel
hashes independently, and compare the coordinate control using a separately
derived oracle. The CameraLinear value convention is `u16*14848/65535` in
post-WB DN, without another black subtraction. Input ties-to-even and output
round-half-up-after-clipping are different quantizers. Record their limits.

For the genuine auxiliary confidence image, all five identity-covered frames
are seen at every quad site, so its codes must lie in `{0,400,800}`;65535 means
unseen and is inadmissible for this complete covered input. This is an input-rank
centrality field, not calibrated optical confidence. Do not reconstruct its
exact ranks from the quantized, white-balanced, demosaiced RGB TIFF.

Add the independent review's direct component control through the existing
confidence_pass and write_confidence_map functions: five private32x16 native
RGGB frames, whole16x8 quad domain, black512, green-luma DN values
`[100,200,200,400,500]`, red700/blue900. No warp or defect; this component does
not invoke the pyramid/probe/MHC. Across each row repeat supplied pre-writer
merged-luma targets `[99,100,200,201,300,400,500,501]`. Require actual below
counts `[0,0,1,3,3,3,4,5]`, seen5, one decode per frame, and decoded writer
codes `[0,0,400,800,800,800,400,0]`. The strict-less-than tie at200 distinguishes
the wrong less-than-or-equal count3/code800 from count1/code400. Other wrong
interpretations (red/blue luma, dropping the duplicate200,65535 normalization)
must fail the fixed independent counts/codes. Keep exact valid companions.

Write two additional16x8 Gray16 component TIFFs: the actual rank map, then
the same map with linear entry0 explicitly manually unseen, matching the bound
independent acceptance review. Only entry0 becomes65535, while reached-zero
entry1 remains0. This second
file tests the writer's sentinel, not actual missing optical coverage. Together
with eight main RGB outputs and the genuine auxiliary image, the complete
prospective population is eleven TIFFs. Malformed and interrupted cases remain
separately labeled refusals, preserving any partial files.

Source recompilation must be visible after the Rust change; pin the executable
and its including source set. Run relevant meaningful consumer checks and the
CLI suite. The numerical model's already frozen reference/CFA controls need
not rerun if their sources and exact admitted bytes remain unchanged.

## Quantitative private coordinate population

Adopt the independently re-chosen candidate in
`independent-next-bridge-review.md`; Curie's implementation review accepts its
unequal crop. The five private input frames are identical copies of each
fixed scene. Their post-WB ideal fields in DN are:

```text
constant: R=2000, G=3000, B=2500
affine:   R=2000+80*x, G=3000+100*y, B=2500+40*x+60*y
```

Store black512 plus .75R at red, G at both green phases and .6B at blue.
Every input value is an exact integer in the active64×48 grid and remains
below white. Red and green gradients independently identify x and y offsets;
blue checks a mixed direction. The constant alone does not test coordinates.

The private prepared quad crop is `(3,5,24,16)`, yielding48×32 native output
and canonical offset `(6,10)`. It fits the full32×24 quad domain. Use the
actual prepared merge/writer, transparently bypassing automatic cover only in
these private controls. The genuine package still uses its computed cover.
The fixed independent oracle covers integer output u∈[14,34), v∈[14,18):
80 sites, all four CFA parities, nonempty and off-diagonal. Its14-native-pixel
guard is scoped to the identity, fixed-beta, one-band path, not the later
three-band quality experiment.

Interior affine MHC interpolation preserves each affine channel because its
second differences vanish. Independently calculate expected values at
`(x,y)=(u+6,v+10)`, including represented f32 WB:

```text
expected_R = R*.75*float64(float32(4/3))
expected_G = G
expected_B = B*.6*float64(float32(5/3))
decoded_DN = actual_TIFF_u16*14848/65535
```

Prospectively require maximum absolute error≤.25DN per channel/site on both
constant and affine controls. This tolerance includes writer quantization
(at most approximately.1133DN away from clipping) and an unproved allowance
for the actual f32 path. It is an engineering commission bar, not a universal
roundoff theorem. Preserve and diagnose a failure rather than fitting a gain,
registration or wider tolerance after seeing output.

Wrong-oracle companions omit/double the native crop, apply a half-native-pixel
x or y error, swap offset components, transpose/reflect coordinates, swap
red/blue channels, reinterpret RGGB as GRBG at fixed data/coordinates, omit WB
or subtract black again. The parity destroyer treats native(20,24)'s red
black-subtracted2700DN as measured green, instead of the correct5400DN; that
site is output(14,14) inside the fixed oracle. Swapping the identical green
phase labels, or the equal red/blue raw constant values, is not a powered
substitute for this concrete CFA interpretation fault.
Each must exceed.25DN on at least one fixed site; the unchanged oracle must
pass every fixed site. A one-pixel x error moves R by80DN and a y error moves
G by100DN. The unequal crop specifically powers swapping offset components.
These test the independent delivered-value check separately from stale-plan
hash refusals. No expected affine surface is fitted to the rendered image.

A third private output adds64DN at active green site `(29,26)` in all five
affine CFA copies. Its corresponding delivered green site `(23,16)` must rise
by more than63.5DN without clipping. The unchanged affine output is the
companion. Mutating every identical copy avoids assuming that the merge admits
one changed outlier. These three private main RGB outputs are additional to
the five genuine-package RGB outputs and one auxiliary confidence TIFF.
Malformed-input and second-read faults are separately named refusals, with
any partial files preserved. None grants optical authority to private inputs.

## Stop and continue conditions

If the path refuses or a control is unpowered, preserve it and diagnose the
consumer before claiming a bridge pass. If all integration controls, five
intended RGB TIFFs and the auxiliary confidence TIFF pass, publish that narrow
result and proceed to a separately registered larger, three-band
depth-boundary/noise comparison. The size/support
and analytic-limit notes in this directory guide that subsequent design.
No default promotion, physical calibration, real-capture or SOTA claim follows.


## Implementation release boundary

Root owns the narrow Python launcher/build/receipt driver and orchestration.
Curie owns the new test-only joint-pupil-bridge.rs child under
crates/strehl-cli/src/merge_cmd and its declaration inside known-scene-benchmark.
Socrates owns independent strict-input/observer/refusal controls; Zeno owns
independent TIFF/value/coordinate/centrality readout. No other product source,
core arithmetic, old parser, merge default or dependency change is authorized.
Use the distinct STREHL_M194F_ namespace, m194f schemas and
target/m194f-production-bridge build directory. Reuse existing strict helpers
without weakening their original consumers. Bind all including Rust/test sources
and the compiler artifact before intended renders. The independent command
must read actual delivered files, not author-produced sample summaries.

Private coordinate/rank controls remain directly callable test fixtures and
cannot be selected as genuine input by a status flag. A source or checker fix
requires recompilation/rebinding and affected controls before intended outputs.
Malformed-input controls precede the genuine-package renders. The five private
coordinate/rank TIFFs are component controls within the eleven-file population;
their numerical and interpretation controls must pass before they can support
the final integration result. Failures remain visible; root reviews the terminal evidence
before any subsequent larger quality experiment.

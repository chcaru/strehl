# Next production bridge: implementation review

2026-09-07, implementation_audit. Read-only source review; draft only. No new
milestone, Rust change, build or intended production render. M194e full3 and
genuine CFA admission remain prerequisites. The root preregistration draft and
`next-production-bridge.md` describe the correct narrow consumer and small-input
limitations; the following points make the implementation concrete.

## Smallest source change and reuse

Add one test-only child file under `merge_cmd/`, declared as a child of
`known_scene_benchmark`. That placement can use its private `UniqueValue`,
`digest`, `valid_hash`, `write_json_new` and option defaults without changing
their visibility or weakening the old M194b parser. Keep the new ignored entry,
schemas, environment prefix and inputs distinct. The only existing Rust file
change can be this test-module declaration; the numerical product body in
`merge_cmd.rs`, `pyramid.rs`, gatefloor and the writer needs no change.

Use a new five-file `PyramidFrameSource`, explicit identity map/reference2,
actual `cover_or_explain` and `pyramid_domain`, then `PreparedPyramid` and
`run_pyramid_prepared`. Construct `NoiseModel::new` directly. Do not reuse
`production_truth::run_fixture_from`: it performs profile lookup and silently
chooses reference0. Do not call M194b `prepare`: it fixes nine indices,
reference4 and a 320×240-specific ROI. Likewise its strict `Inputs::load`
should continue rejecting M194e rather than becoming a polymorphic parser.

The existing `options()` is a useful constructor: its CameraLinear/MHC/Crop,
gate2/bands3/HardFloor, no exposure/photometry settings match the proposal.
Override its sentinel directory name and only explicitly requested fields.
Assert actual defaults resolve HardFloor before any override. Build the
prepared state's explicit levels, WB/noise and `Exposure::resolve` from the
new fixed contract; serialize the resolved values and `level_sizes` into the
plan. Source audit confirms no other geometry/merge seam is missing.

## Reader and receipt gaps to close

The old `read_json` and `FileSource::decode` check metadata before `fs::read`.
They hash the actual bytes they decode, which is good, but a growing/replaced
file between those operations can defeat the intended allocation bound.
The new adapter should open once, read at most `limit+1` bytes using `Read::take`,
then require the exact length and hash that buffer. Use 6144 as the CFA limit
and a fixed prospective JSON ceiling. Decode that same buffer. This is a
new-adapter requirement, not a retrospective claim that existing inputs changed.

Use `UniqueValue` before typed `deny_unknown_fields` records. Pin the real
M194e child records, source/float/CFA associations and external hashes, rather
than accepting selected top-level fields while ignoring evidence children.
Explicitly define reference bases: emitted manifest relative to its package,
receipt children to their documented containing directory, repository-bound
source/evidence references to the recorded repository scope. Check canonical
containment and uniqueness, including Windows case aliases; retain the original
manifest/source bytes for terminal comparison. Do not infer CFA authority from
a status string or a self-supplied digest.

The driver needs its own strict environment allowlist. M194b's
`controlled_environment_for` knows only the M194b/d namespaces and modes;
reusing it unchanged would either reject new inputs or tempt hidden aliases.
Clear ambient `STREHL_*`, worker and build overrides in the launcher, and
refuse unexpected settings in the child. Keep debug floor logging off on this
empty-measured-floor fixture. Confidence must reach the new source twice per
index, with the counted observer itself carrying off/count/placebo byte proof.

For build evidence, reuse the M194d driver's compiler-artifact/copy equality,
complete source map, fresh rebuild and executable hashing pattern. Give the
new test, target directory, build schema and environment explicit names in a
small versioned driver; do not rewrite imported old globals while retaining an
old schema label. Reuse the existing external-include closure check with its
including-crate roots. Bind all reachable existing M194/c/d test includes plus
the new child/control sources, not just the new file. No new dependency is needed.

## Concrete private coordinate controls

These are prospective integration fixtures, not admitted M194e optical data.
Use native64×48 RGGB with black512 and white15360. Give each of five input
frames the same independently generated active values. Green phases share the
same green field so a deliberate G1/G2 mismatch is a corruption, not an
unmodeled second green radiance. Proposed black-subtracted fields in DN are:

```text
constant: R=1200, G=1800, B=2400
affine:   R=1200+4*x+2*y, G=1800+2*x+4*y, B=2400+6*x+2*y
```

All stored values are exact u16 after adding black, and all output channels
remain away from clipping after fixed f32 WB `[4/3,1,5/3]`. Supply a private
explicit quad crop `(x=3,y=3,width=24,height=16)` through
`PyramidDomain::cropped`; the actual writer must deliver48×32 RGB16. This
private crop control bypasses automatic cover selection transparently; the
genuine arm still uses the actual computed crop.

The constant scene checks parity/channel values and the one-time black/WB
normalization. The affine scene checks the native coordinate
`(u+6,v+6)` against output `(u,v)`. Compare only the preregistered interior
`u∈[14,34), v∈[14,18)` for its affine oracle: the conservative14-native-pixel
guard covers the one-band local support and final MHC. It contains both
parities on both axes. Read the whole output for dimensions, tags and hashes;
the coordinate oracle is an explicitly scoped interior, not a quality ROI.

MHC reproduces an affine channel field in the interior; its cross-channel
second differences vanish. Independently derive that polynomial property,
then apply the declared f32 normalization/WB and output round-half-up rule.
Predeclare at most one output u16 LSB allowance for ordinary f32 reconstruction
and encoding, with no fitted gain or image registration. A wrong crop origin
shifts these gradients by multiple LSB; channel permutation, CFA phase changes,
second black subtraction and omitted WB are much larger destroyers. Require
each destroyer to move the independent expected values beyond the allowance.
The constant arm alone cannot detect an origin shift.

The four genuine TIFFs proposed by root remain baseline twice, confidence and
exposure+1. Private coordinate/mutation controls are additional explicitly
named component outputs. Preserve unpowered controls and failures; neither a
successful private fixture nor source-byte identity can supply missing genuine
M194e float/CFA authority.

## Inspection record

Read the two bridge drafts, M194b strict JSON/file/source/prepare/options code,
M194d child and driver/source-include checks, M194 fixture preparation and
writer normalization comments. Tools were bounded `rg`/`Get-Content` reads;
no dependency implementation source or RAW was opened and no command above
was executed as a production render. These are VERIFIED source choices and
DERIVED prospective affine controls; all new execution remains UNRUN.

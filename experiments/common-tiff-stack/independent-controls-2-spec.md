# Independent saved verification 2: local Windows path association

SOURCE ONLY, 2026-09-08. This is the separately reviewed correction to the
failed saved verifier, not a new fixture, build, merge, image campaign or gate.
The twelve product calls have already completed their registered process
exit dispositions. Verification 1 returned REFUSED on all twelve at the first
incomplete/manifest FileRef association, with no scientific control admission.
The original source, index, products, verification result and resource charges
remain immutable. Only the new released verification command may execute.

## Exact cause and permitted correction

Read-only JSON/path inspection of cases 0, 6 and 10 found equal byte extents
and SHA256 values for both incomplete and manifest records. Rust's saved
paths use the extended local-drive prefix \\?\C:\; the corresponding Python
refs use ordinary C:\ paths. On this installed Python, Path.resolve() retained
the prefix, so path equality was false. The same association seam is reached
again for profile, consumed input, frame and output refs, and for the two
initial-anchor path strings. This is not evidence of changed image content.

association_path() accepts the existing relative-to-repository form and
ordinary absolute repository paths. A verbatim prefix is stripped only when
followed by an ASCII drive letter, colon and backslash, with nonempty canonical
components, no dot/dotdot, trailing dot/space or additional colon. Device and
UNC forms are rejected. The resolved path must remain within this repository.
The original exact path + byte extent + SHA256 predicate still applies;
identical contents at distinct paths never establish the same reference.
Authenticated buffers, file-read stability, all source hashes and exact case
paths remain required. No raw receipt, FileRef, index or image is rewritten.

## Authority and invocation

New source: independent-controls-2.py. New protocol: this file. Original
fixture/checker source remains independent-controls.py, 55,907 bytes,
SHA256 12fd11c8d3211e2dcf3beea9d99b302e1f7f9515b5dc79f6cf433c8e1a675f08.
Original fixture protocol remains independent-controls-spec.md, 13,754 bytes,
SHA256 6ef4ac0e6ea9a0179b73c9546160bf2fb07409889d7183bad8457462020a4095.
The actual original index.source/index.spec must match those separate pins.
The original render release's complete 156-source mapping is reread unchanged;
the new checker is bound independently by its exact released CLI SHA and the
new controller's eight-file source extension. The current protocol is included
in that extension. It is not substituted into the old index or source mapping.
The new controller separately authenticates prior build, preparation, render
and refused verification evidence; it never dispatches another product.

Exact argument order (all paths absolute, actual hashes replace placeholders):

    PY -I -S -B independent-controls-2.py verify --fixtures prepare-1/fixtures/index.json --fixtures-sha256 INDEX_SHA --run-bundle render-bundle-1.json --run-bundle-sha256 BUNDLE_SHA --output verify-2/check --source-sha256 NEW_SOURCE_SHA

Only the verify subcommand is accepted. The original unused prepare function
remains for source-body equality; it has no CLI dispatch. The original index,
27 generated members, twelve row definitions, compiled build-3 executable,
render-1 products and six-role external render bundle remain the inputs.
The fixed new output is verify-2/check. Result schema is
common-tiff-stack-independent-verification-v2; pass status remains
PASS_COMMON_RGB_STACK_SOFTWARE_INTEGRATION. REFUSED never admits software,
physical noise calibration, real geometry or image quality. Raw stdout must
match the saved result, and the actual external interval/exit is mandatory.

## Six path controls, before scientific replay

These are additional metadata controls, separately named and reported from the
sixteen original scientific controls. Two fresh bounded metadata files contain
identical literal bytes and are independently reread. No image is synthesized.
The actual same_ref() predicate is exercised in both directions where useful.

1. The ordinary file associates with its own exact reference.
2. The ordinary and verbatim spellings read the same actual file bytes and
   associate in both directions.
3. The second actual file has the same bytes and SHA but a different path;
   association must reject with exact path extent and digest association.
4. The same path with one changed SHA hex character must reject by that same
   predicate and exact reason.
5. The same path with extent increased by one must reject by that same
   predicate and exact reason.
6. Restoring the original refs and rereading both metadata files restores the
   positive association without changing either actual file.

The six rows are retained in path-association-controls.json before subsequent
fixture/science work, and linked again from the final result. Files
path-control-a.json and path-control-b.json each reserve 512 bytes; the control
receipt reserves 4,096 bytes. Any unpowered negative stops this correction.

## Unchanged scientific consumer and source delta

The generator, independent TIFF decoder, literal pixels, normalization/noise
law, merge recipe, gate population, registered refusal reasons, observer
comparison and all sixteen scientific controls retain their original ASTs.
There are 42 original top-level functions: 35 remain AST-identical. The seven
changed functions are source_authority, same_ref, fixture_authority,
saved_render_bundle, product_case, verify and main. Two new functions are
association_path and path_association_controls. In product_case, the only
changes are its two initial-anchor path expressions; reversing those restores
its original AST exactly. Other changed functions are authority, invocation,
publication or association changes, not numerical equations or thresholds.
The original sixteen scientific-control rows remain exact and distinct from
the six new metadata rows. No fixture is regenerated on disk.

The existing independent RGB16 reader remains independent of the product TIFF
writer. Fixed output tags, actual proxy/variance f32 byte hashes, all contributor
and prefix checks, per-level counts, base exclusion, whole-TIFF off/on/placebo
identity, actual ICC/pixel destroyers and literal exact outputs retain their
registered gates. A future failure in any of those paths is retained rather
than excused as part of this path fix. The prior verifier reached none of them
for product admission. Source compatibility review is not their numerical pass.

## Finite accounting and interpretation

The new checker retains its own 20 CPU-second / 30 wall-second limit including
0.25 CPU / 0.5 wall publication allowance, within the separately released
60 CPU / 120 wall / 512 MiB Job / 16 MiB controller stage. Existing attempt
charges are not refunded. No runtime inventory, native model or external-image
library is added; this remains an isolated standard-library reader. The
original named-buffer bound is 64 MiB, not a measured process-memory claim.

Source cap 128 KiB and protocol cap 16 KiB remain unchanged. The original
128 KiB final and identical stdout slots remain; the six metadata rows and
three refs add a conservative 4 KiB to the prior 73,728-byte metadata envelope,
for 77,824 bytes below 131,072. Two metadata files plus their receipt add at
most 5,120 retained bytes. Final + stdout + metadata therefore reserve
267,264 bytes below the original 4 MiB independent family and stage 16 MiB.
Each actual write enforces its held cap. The final result explicitly identifies
the new source and original fixture source/spec separately. The immutable
original verifier failure remains part of the parent's evidence, not a passed
result. This correction can establish only the already registered bounded
common-RGB software consumer; physical calibration, placement and quality
admission remain false even after a complete pass.

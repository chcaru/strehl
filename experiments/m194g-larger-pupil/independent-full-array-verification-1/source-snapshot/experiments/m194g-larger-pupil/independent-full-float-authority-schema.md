# Prospective full-float authority schema

2026-09-07. Design supplement to `next-full-array-reader-design.md`, reviewed
at SHA `d595f4fa872fe01ec936a71d7475952dd4195504acb798aa6fd0d2a70fe4308a`.
This defines a future consumer boundary, not an authority issued from current
component results. No full array, optical helper or emission is executed here.
Root acceptance and the separately frozen reader/control commands precede use.

## Exact success record

The reader writes `float-commission.json` only for a complete successful
comparison. Its closed top-level keys are:

```text
schema                 "m194g-float-commission-v1"
status                 "PASS_COMPLETE_FLOAT_MODEL"
ref_root               "repository"
fixture                FileRef
component_verification FileRef
comparison             FileRef
width                  320
height                 240
cell                   "integer-centre-unit-square"
units                  "expected-electrons"
reference_index        2
primary_frames         [PrimaryFrame × 5]
```

`FileRef` has exactly `path`, `sha256`, `bytes`. `ArrayRef` has exactly those
three keys plus `dtype`, `shape`. Each `PrimaryFrame` has exactly `index`,
`inverse_focus`, `author_receipt`, `scalar`; its latter two fields are a
FileRef and ArrayRef respectively. There is no free-form method/configuration
override in the authority.

All integer fields, dimensions, shape elements and byte lengths require real
integers, excluding bool and float aliases. Byte lengths are positive. Digests
are lowercase 64-character hexadecimal SHA256. Focus is a finite JSON real,
excluding bool; it must equal the fixture's value. The five records are in
index order0–4, with inverse focus `[0.5,0.625,0.75,0.875,1.0]`. Scalar dtype
is exactly `<f8`, shape exactly `[240,320]`, C order, in electron units before
site colour factors, shot/read noise, gain, black level or quantization.
The scalar arrays are the original **author primary** arrays. A reference or
refined array cannot be substituted even if it happens to have equal values.

The fixture FileRef must name the exact registered M194g fixture bytes, SHA
`e84f0bbbda9bef039da86616c9f051d416929f4dbe78477cc5b3fc21206856bb`.
Width/height/cell/reference index/focus and identity placements must agree
with that reopened fixture. Scene `textured` is the fixture's fixed scene.
This authority does not redefine the separate noise contract's analytic flat
scene or authorize a different optical scene.

## One explicit path root

Every FileRef and ArrayRef in this authority resolves from the consumer's
known repository root, including the comparison, fixture and component result.
No path is relative to the authority file's parent. Paths use `/`, are
repository-relative and contain no empty, `.` or `..` components, drive/UNC
prefix, colon, backslash or absolute-root prefix. Resolve the actual target
and require containment in that repository; a symlink/reparse escape refuses.
The authority may be moved without changing these reference semantics. Moving
the whole repository preserves them; moving only an array package does not.

Five scalar paths and five frame-receipt paths must be unique after resolution
and Windows case folding. File-identity aliases must not replace distinct
declared files. Distinct files may have equal hashes; byte equality alone is
not an identity failure. All array bytes remain in their original author
directories. There is no scalar copy into the noise output directory and no
path inferred from a producer's descriptive label.

## Exact child closure, without rescoring in the emitter

The `comparison` FileRef points to the full reader's completed `result.json`,
with schema `m194g-independent-full-array-verification-v1` and status
`PASS_COMPLETE_FLOAT_MODEL`. The detailed comparison record's closed
`admitted_inputs` object is exactly the authority projection
`{ref_root, fixture, component_verification, width, height, cell, units,
reference_index, primary_frames}`. The emitter compares this whole object,
including typed fields and file references, rather than selecting a few keys.

The comparison's `render_results` object has exactly five role keys:
`author-primary`, `author-angle-refined`, `author-cell-refined`,
`reference-primary`, `reference-refined`, each a repository-relative FileRef.
The full reader validates all five terminal results, prospective execution
releases, exercised source snapshots and actual array populations. It retains
all30 external comparisons and15 refinement comparisons plus the separately
scoped fallback/boundary descriptions; pooled success cannot replace them.
The rest of its detailed closed result schema is frozen with that reader's
implementation. These two named subrecords are the fixed emitter interface.

The noise consumer receives the authority path and SHA externally. It reopens
the same bounded authority bytes, its comparison child, fixture and component
verification. The latter must be the completed independent component command
record, schema `m194g-independent-component-reader-command-v1`, with status
`PASS_COMPONENTS_AND_OBSERVER_ONLY`, `exception` and `traceback` both null,
and `inputs_unchanged` true. Its nested `result` must have schema
`m194g-independent-component-verification-v1` and the same successful status.
Neither numerical author's own component status supplies this authority.
It also closes the five render-result references and
requires the primary result's actual five frame receipts to be exactly the
authority's `author_receipt` records. For each frame it checks the actual
receipt's registered primary inputs and exact scalar array reference after
converting its receipt-relative path to repository-relative form. This closes
the original source-array lineage without invoking an integrator or repeating
the full comparison calculations.

Before use, read every primary array with the existing bounded same-buffer
NPY discipline: check SHA/length and header before allocation, exact dtype,
shape, C order, payload extent, finite nonnegative values, and no trailing
bytes. The expected scalar need not fit a CFA rail before the noise contract's
separate colour/encoding rules are applied. The primary arrays, child records,
source/runtime inputs and authority stay hash-bound through emission. These
checks do not authenticate a fabricated package supplied with a newly granted
external pin; they enforce consistency of the genuinely admitted pinned one.

## Acyclic publication and refusal

The comparison result binds all deciding evidence but does not reference the
authority that will later cite it. Persist that complete result, then form the
authority from its admitted inputs and actual result hash. This avoids a
self-hash or a comparison/authority hash cycle. Check the reader's final
source/input and resource limits through required persistence. If a final
check fails, preserve the original and any finalization error and revoke the
success record; never leave both a successful authority and a matching
successful child after a failed run. The registered controls must exercise
that post-write failure path as well as incomplete/missing child refusal.

Private fixtures are labeled and remain outside genuine authority. The later
strict-reader controls include unknown keys/schema, typed aliases, wrong arm,
coherently changed array/receipt pairing, changed child admission projection,
missing result/receipt, an escaping or aliased path, failed component/full
status and nonfinite/changed actual array bytes, each with a reopened valid or
restored companion. No general certificate engine or new numerical bar is
required. Complete25-array admission and the separately commissioned noise
stage remain prerequisites to any subsequent production-quality comparison.

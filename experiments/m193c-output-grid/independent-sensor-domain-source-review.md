# Independent source review: explicit sensor-domain native reader

Status: **source review complete, with no remaining blocking defect identified
in the bounded reader/domain/interface scope.** No reader, helper control,
NumPy/rawpy import, RAW/TIFF decode, render or registration was executed.
The eight proposed controls have not yet passed in an actual invocation.
The original native1 refusal and its frozen files remain unchanged.

Reviewed final pins:

| File | Bytes | SHA-256 |
|---|---:|---|
| `independent-sensor-derivative-read.py` | 68,424 | `eeed1ea3c45927f81e34d99ca31dc57715f898b718dfef26dcf0ea2cddf3fbe7` |
| `native-sensor-derivative-run.py` | 53,533 | `10ec80290bc7bb5c2e7fc140cb831d539e517844281b40b372055b409113a1ed` |
| `sensor-domain-reader-preregister.md` | 15,934 | `7450a8e2ecef2b5c3c883e63fd2f636dc84c5bc6ac07df80fc1277bf5bdf7125` |

I read the old/new source diffs, the entire specification, the relevant existing
reader/parent/runtime/TIFF interfaces and the actual new helper/control bodies.
An independent stdlib AST comparison parsed source text only. It confirmed
that the old reader definitions changed only in `release_entry`, `native_run`,
`initial_result` and `main`, with new `owned_sensor` and `run_sensor_controls`.
No existing private helper, class, runtime function, scalar-level/WB validator
or TIFF routine changed. The parent and reader's literal eleven check IDs and
eight domain IDs match exactly. This is source comparison, not helper execution.

The old reader remains SHA
`8c571654667f8ef66520aedfd1bddceb991c8a86d1a7355a4ed21cf2ba85eced`,
the old parent remains
`94fe31fbd80854fac80114e0b16b150d9d70ed8899ced727dd8c052b74d0244a`,
and the native TIFF parser remains
`9acceb498568967bb02ce01389441da09de7502f3a51faebbed8fed61943a5ae`.
Their actual current hashes were checked. No held source was edited by this review.

## Domain, lifetime and consumer meaning

The new helper receives the primary receipt's explicit `{x,y,width,height}`
only after existing source/plan validation. It checks genuine bounded integers,
even origin/extent, positive dimensions, at most36million ROI samples, an
independent two-dimensional native-u16 buffer of at most40million samples,
full-shape agreement with the decoder's own metadata, and complete rectangle
containment. The actual data selection is `full[y:y+h,x:x+w]`, not a visible
crop or a search for an agreeing prefix.

Allocation is checked before the copy. The copy occurs inside the RawPy owner
context and must own C-contiguous memory, have the exact selected shape and
share no memory with the decoder buffer. After closing the owner, the unchanged
hash path compares the whole ROI and every row against the primary receipt,
with exact u16 agreement. No tolerance, cropped-out disagreement or omitted
column has been added. Only the declared ROI is copied; surrounding allocated
padding is not included in a statistic. Full-buffer dimensions are necessarily
postdecode checks, with the outer Job memory limit remaining the earlier
allocation barrier; the specification states this limit honestly.

The actual CFA queries use the selected primary origin inside the live context.
Their returned channel indices feed the unchanged RGGB, scalar black/white and
green-normalized WB checks. The original exact scalar rules and `2^-20` WB
allowance remain. The independent visible rectangle, shape, full sizes and flip
are preserved as metadata, with an explicit agreement flag and no physical
photosite-validity claim. The visible rectangle must be internally valid but
is not substituted for the consumer's selected domain.

This implements a different explicitly named domain contract. The prior
[probe audit](independent-active-domain-probe-1-read.md) supports its motivation
for original0 only. It does not establish agreement on the other eight originals
or turn the previously refused visible-domain method into a pass. Future native
admission still requires exact independent bytes for every row of every input.

## Fixed control power and limitation

The eight controls share the actual reader Budget and run before its snapshot
decode. The synthetic full buffer is12x16 with values `500+31*y+3*x`; the
independent expected bytes are separately packed at x4..11/y2..7. Thus the
actual helper cannot create its own expected hash by returning an arbitrary
same-shaped crop. The default visible rectangle(7,5,6,4) differs in dimensions,
origin and phase from the selected rectangle(4,2,8,6).

The source paths have these prospective rejection mechanisms:

- The nonzero-origin positive and visible-crop null must retain exact full
  and six-row hashes after the fake owner poisons its entire buffer at close.
  Changing the visible viewport alone must not change the consumed ROI.
- The actual x6 offset remains valid and same-shaped, but must fail the
  unchanged whole-active comparison. The truncated seven-row buffer must
  fail actual containment before a partial ROI can be admitted.
- The actual helper's borrow path must refuse ownership. The separate late
  copy deliberately reads poisoned storage and must change the whole hash
  and all six row hashes. A no-op owner close would therefore defeat that
  required destroyer rather than pass unnoticed. The restored helper must
  recover the original hashes.
- The selected even origin must report RGGB; querying the deliberately odd
  visible origin instead must actually return BGGR. These are live raw_color
  calls inside the fake context, not just labels in a result.

The inherited refusal helper appends a failed record before calling its
subject. Its expected-refusal assertion is outside the caught subject call,
so it cannot count its own false-acceptance error as the expected refusal.
Partial attempted domain controls remain attached to the native result.

Root caught one **specification-only power overclaim** in the initially held
15,690-byte spec, SHA
`915fb4ce6abaa209c2cd2fe802edcee43a95466f7299d30811e426997d1e29bf`.
CFA at(0,0) and at any admitted even origin has the same phase. The final
spec correctly limits CFA power to the odd visible-origin substitution;
zero/even equivalence is arithmetic. Full/row pixel hashes independently
test crop location. I reread that correction; neither reader nor parent
source changed. No unexecuted CFA check is described here as independently
detecting an even-origin translation through letters alone.

## Exact request, result, runtime and parent association

The new release/schema names separate this method from the historical native
method: scope `sensor-native-nine`, request
`m193c-sensor-native-derivative-read-request-v1`, and result
`m193c-sensor-native-derivative-independent-frame-v1`, success
`PASS_SENSOR_NATIVE_DERIVATIVE_FRAME_ONLY`. The request's old fields are
preserved; the result adds exactly the ordered `domain_controls` population.

The first native check is now truthfully `owned-sensor-copy`. The remaining
ten keep their existing meaning: active shape, local RGGB, complete active
bytes, all row bytes, scalar levels, WB, native RGB16 TIFF, camera-linear tags,
full TIFF pixel read and consumed-source stability. The first evidence object
retains the actual decoder/domain witness. The parent requires all eleven
records and all eight domain records with exact IDs, true values and evidence
objects; it cannot count an old owned-visible-copy result as this method.

The parent pins the new script path and nine literal hashed-request commands.
The reader requires actual released original argv, the same build/runtime
refs and its source/spec closure. The parent's result consumer binds request,
original index, snapshot/primary/TIFF files, actual executable/cwd/options,
thread settings, recorded runtime, full source map, work fields and final
zero-exit observation. Successful source checks remain separate from the
historical native failure's meaning.

The captured runtime dictionary and its six original dependency records are
unchanged. Runtime functions are structurally identical to the held reader,
and actual runtime recomputation/equality plus consumed-file rechecks remain
on the native path. The separately recorded adjacent DLL observations are
still an external endpoint obligation of root's actual launch and are also
authenticated/rehashed by the reuse setup. They are not silently inserted
into the older runtime dictionary or recast as exhaustive loaded-module proof.

Native TIFF processing still uses the held bounded parser. It consumes the
whole RGB payload into a canonical digest in blocks; the native path does
not request a full NumPy RGB array. The old private optional pixel-array
path is unchanged. This distinction preserves the reader's128MiB named-array
limit while its byte buffers remain subject to the process memory ceiling.

## Parent reuse boundary and remaining execution scope

I read the parent's diff and interface handoff. Original0 has a dedicated
historical reuse branch, an old plan/receipt/snapshot/TIFF path association,
a fresh independent request and output, and explicit historical CPU provenance.
It does not send the old primary launch through the new CPU accumulator or
delete the retained failed-run snapshot. Other rows retain the old fresh
producer/snapshot/read path. The parent still stops on the first failure.
Root's independent full reuse source read and Socrates' separate provenance
review own the complete historical-authority assessment; this document's
primary scope is the domain helper and the reader-parent contract.

All original stage/work limits remain, and the new controls have no fresh
budget. Only a small execution-source subset is copied per reader, preserving
the4MiB per-frame metadata ceiling. The unchanged private/Rust/build evidence
is retained as evidence for unchanged paths; it is not renamed as a PASS for
the new helper. There have been no new scientific control results in this review.

A successful future run would be one reused primary TIFF, eight fresh primary
TIFFs and nine fresh independent reads, with17 newly launched children. That
is a planned population, not an observed count. The source-only prepared
coverage runner currently requires the old schemas and per-row snapshot
deletion, so it intentionally cannot admit this new run unchanged. Any later
coverage handoff needs its own explicit association update, including the
retained original0 snapshot. This does not block the reviewed native reader
method and grants no coverage, placement, physical-calibration or quality claim.

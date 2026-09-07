# M193c registration derivative — independent source review

2026-09-07. **SOURCE REVIEW ONLY / UNEXECUTED.** No adapter/helper import,
compilation, control, TIFF write/read, RAW byte read or decode occurred in
this review. Only this document was written. The reviewed implementation and
literal protocol were:

| File | Bytes | SHA256 |
| --- | ---: | --- |
| registration-derivative.rs | 38278 | e09fdef23725acf17ff44b98a78f0ae97a9a47dd5354ea8ef466e0f7b005463f |
| derivative-controls-preregister.md | 14144 | a8c8efefadee412bed7bce3e39e5d769ca71336dac126db86871528c78495257 |

Disposition: the active extraction, normalization, owned-buffer lifetime and
existing writer routing are coherent with the accepted design. Two narrow
items below need disposition before the source/command freeze: correct the
snapshot binding claim, and strengthen the existing publication control's
original-error/preserved-bytes assertion. No new image, numerical tolerance,
decoder or production-path change is requested. Compilation and all private
and native outcomes remain uncommissioned.

## Two concrete findings

1. **Same-buffer wording exceeds the decode seam.** The native plan is read
   once under its JSON bound, hashed, then parsed from those exact bytes.
   The RAW snapshot follows a different path: `verify_file` opens and hashes
   it, closes that stream, `strehl_raw::decode(path)` opens its own source,
   and the adapter hashes the file again afterward. Those are before/after
   file bindings, not a decode of the exact hashed buffer. The preregistration
   sentence saying all plan/snapshot hashes cover the same bounded bytes
   actually consumed should distinguish the two. The owned decoder's path
   interface and parent-created stable snapshot remain usable within that
   scope. If stronger atomic path stability is required, it needs an explicit
   lock/handle contract; postchecks alone cannot prove absence of a transient
   replacement. Do not describe the current API as a same-buffer RAW decoder.

2. **The late-publication control does not yet test preservation of the first
   cause.** `late-publication-revokes` currently requires any returned error,
   persisted `REFUSED`, and existence of `publication.first.json`. It can pass
   even if the publisher replaces the callback's cause or saves incorrect
   first-receipt bytes. Within the same existing ID and without an extra TIFF,
   assert the exact `private late-finalization source fault` in the returned
   and persisted error/finalization fields, and compare the retained first
   file with the known initial pretty-JSON bytes. Keep the successful initial
   write, actual recheck failure and restored readable first artifact as
   distinct evidence. This is a control-power gap; the reviewed publisher's
   normal source path does preserve the cause by inspection.

These are static findings, not executed failures. The source author/root was
notified. This review does not claim either repair has been executed.

## Active storage, levels and WB

`validate_frame` checks nonempty dimensions, each axis at most 8192, checked
active product at most 36,000,000, checked allocated product at most 40,000,000,
even active origin/extent, checked contained endpoints and exact buffer
length. The small invalid fixtures change headers on an existing small
buffer; they do not allocate the invalid declared volume. Native checks run
after the owned decoder returns and before the adapter's mosaic allocation.
That is the accepted postdecode boundary, not a predecoder allocation proof.

`normalized_active_mosaic` consumes `Frame::active_row(y)` and hashes exactly
the active u16 samples in little-endian native row order, both per row and
for the full payload. The padding sentinel is excluded. Full buffer extents
and allocated sample bytes are recorded separately; no statistic over the
decoded padding is used. Even active origins preserve local RGGB after the
owned decode wrapper's explicit camera-RGGB refusal. `Frame` itself does not
carry an independently checked CFA map, so actual rawpy/LibRaw phase/payload
agreement remains a necessary native consumer result.

The code uses the owned `Frame::wb_gains()` first-three-coefficient rule and
then rejects nonfinite/nonpositive normalized gains. Thus the overflowed
ratio control reaches `WB gains`, while zero/NaN source coefficients reach
`WB coefficients`. The fourth WB coefficient is never used arithmetically;
its bits may be NaN and are serialized as integers. Actual black/white,
inverse-range and normalized gain bits are retained alongside their values.

The normalization is exactly the declared f32 sequence
`((sample-black)*(1.0f32/(white-black)))*gain`, with one reciprocal computed
per frame and local RGGB channel choice. It checks every mosaic value for
finiteness and does not clamp signed or above-one values before demosaic.
The metadata explicitly discloses the wrapper's possible black/white
defaults of 0/65535. The wrapper also falls back to the whole buffer if active
area metadata is absent; native visible-array agreement must catch any
resulting disagreement. A valid resolved frame is not proof that original
metadata fields were present or independently calibrated.

## Actual MHC/writer path and the 32 controls

`write_registration_derivative` calls the existing
`image_out::write_demosaiced(..., Develop::measurement(false))` once per
prepared derivative. In that configuration the owned writer has no matrix,
tone, exposure adjustment or sRGB transfer; it executes MHC through the
normal `demosaic_row` choice and the existing final clamp/half-up RGB16
conversion. Unexpected `STREHL_*` variables are rejected and the parent must
launch a fresh exact test, so a previously cached demosaic override cannot
be silently inherited from another test in the same process.

The output is full-active CameraLinear registration development with as-shot
WB. It is not a ProPhoto/common-merge input, a colorimetric reconstruction,
registration truth or a quality result. MHC may alter edges; lack of an
additional sharpening pass is not a detail-preservation assertion. The
constant/signed private fields commission specific arithmetic choices only.

The 32 IDs match the literal order: one valid control, 21 individual header/
levels/WB refusals, then fourth-WB null, padding null, red-gain live, early
black-clamp live, WB-order live, nine-plan-before-decode, lifetime guard,
snapshot mutation, late publication and restored affine. Invalid-frame
controls require their exact error string and a restored valid companion,
rather than treating an unrelated exception as success. Their ordering
matches the validator: for example stride 41 reaches length disagreement,
the outside active rectangle reaches containment, and multiplication
overflow is checked before a large allocation.

The two arithmetic destroyers call the actual MHC helper. At the signed R
impulse, the early black clamp is required to change an unclipped neighboring
R reconstruction by 1/256 normalized; the control compares the same row after
restoration. The WB-order arm demosaics an unbalanced mosaic then applies
output gains, and must change the final-clamped green reconstruction at the
declared R site by more than 1/512. These are prospective live neighbor tests,
not a comparison of two identically clipped impulse centers. The independent
two-TIFF reader still must test the separate rational/mirror pixel oracles.

`private_controls` itself calls no product TIFF writer. After all 32 checks
are true, `private_child` makes exactly two calls, named `affine.tiff` and
`signed-border.tiff`. There are no restored writer calls hidden in the helper
population. The two frames are 30×22 active; the independently specified
affine 54-site/all-channel and signed-border 660-pixel oracles are still
unexecuted. Together with the ten geometry images these exhaust the current
twelve private product-output slots. A failed writer attempt remains counted
by the future parent; this source review does not grant a replacement slot.

## Ownership and what the lease witness means

`prepare_from_source` validates all nine plan entries and the selected index
before calling its `FnOnce` decoder. It wraps the returned owned frame in a
lease, builds an owned f32 mosaic plus scalar/hash metadata, then explicitly
drops the lease before returning. Rust completes the frame-field drop before
the subsequent zero-live check and writer callback. Error propagation from
normalization also drops the lease. No rawpy borrowed view or aligned-frame
stack is used.

The lifetime control reaches the actual `with_released_frame` guard used by
the writer. Its valid callback observes zero leases, an injected live count
must refuse before its callback, and restored zero count passes. This powers
the guard with a fake owned source; it is not a measurement of a native
decoder's internal memory or destructor. Several tiny fixture clones remain
in the private-control function; the “one frame” native claim must not be
misread as a count of every private allocation. The native path makes one
decoder call and holds no decoded `Frame` through writing.

The full RGB16 writer allocation, retained mosaic, encoder/scratch storage,
source snapshot and external decoder allocations still need the parent
resource envelope. The checked owned extents and lease counter cannot prove
an RSS cap. The adopted Windows Job committed-memory bound is distinct from
resident memory, while elapsed fields here are sampled before publication.
The parent must count setup, both decoders, writes, readers, failed artifacts
and final checks in its nonresetting stage budgets.

## Input, executable and publication authority

The input plan uses closed serde structs; integer fields reject bool/float
substitutions, duplicate recognized struct fields refuse, and the source map
has its own duplicate-key visitor. Nested settings must be the exact
registration-only conventions, including null matrix and false orientation.
All nine original indices, names, byte lengths and lexical corpus paths are
checked in order. Selection is an original index, not a local position.
The input-plan bytes and external hash are validated before any decode.

The child records parent-supplied mtime/attributes; it does not establish
their truth by reading all originals. It validates the complete nine-entry
shape and requires the four owned source pins, verifies supplied source
files remain inside the repository and match their hashes, binds the four
compile-time byte-includes, and matches the current executable path/bytes.
The source map's complete compiler-input set, build artifact and copy/listing
chain are parent responsibilities. A self-consistent map containing only the
four owned entries cannot supply that broader authority on its own.

Likewise `workspace_file` confines the plan and selected snapshot to the
repository and checks the expected snapshot basename/hash/length. It does
not itself require a specific fresh attempt subdirectory or prove the
snapshot was created by copying the selected original. The parent must bind
that fresh snapshot lineage and all originals before/after, keep only one
snapshot at a time and keep it until both decoders finish. No original or
XMP should be read merely by interpreting an arbitrary candidate path.
The private fake plan intentionally has nonexistent/zero-hash references
and exercises only semantic preparation; it is not accepted native authority.

The native closure checks source/executable state before decode, again after
writing, and through final publication on success. It also rechecks the
input plan, snapshot and emitted TIFF reference. The result retains whatever
identities and output refs were actually reached on failure; unresolved
fields may be null. If failure precedes the final `actual_plan` assignment,
the successful-source closure is not claimed, and the outer parent must
retain its own failed-attempt source accounting. An output file whose write
or hashing failed may exist without a completed FileRef; it remains a failed
artifact counted by the parent, not another admitted output.

`publish` writes an exclusive provisional record, runs final checks, and on
failure retains it as `.first.json` while writing a refused replacement. If
that retention/rewrite also fails, it returns the original finalizer cause
with the secondary persistence context. The callers additionally preserve
an earlier decode/control failure over a publication error. Setup failures
before the attempt record remain parent launch-log outcomes. The parent
must require actual zero exit and the final successful record, so a preserved
provisional success cannot be mistaken for admission after a nonzero exit.

A completed helper/two-TIFF run would mean only private derivative products
exist with the named controls. Native RAW release still requires the
separately frozen independent TIFF reader, exact nine-source plan and
independent rawpy/LibRaw active payload, phase, scalar-level and WB checks.
Do not loosen a decoder disagreement with crop/offset/color fitting or
promote a subset into an all-nine derivative package. Registrar first-refusal
and unvisited-frame semantics remain separate from this source review.

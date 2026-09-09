# External dimensions patch handoff

2026-09-08. DRAFT SOURCE ONLY; unapplied. No Rust parser/compiler, product,
fixture, control, image, core sampler or numerical execution.

Patch: draft.patch,18111 bytes,
SHA256 fee644d8854b3298d3083025dc8f2ae83c6ba7a189ceddbf98416f397b3de005.
Exactly three paths,29 hunks,+121/-65 lines. Every deleted line belongs to
count/grid/cap/schema/plumbing substitution or the three stale initializer
frame reservations. No core/CLI entry/parser/files helper/Cargo/default edit.

## Exact source buffers

All paths below are crates/strehl-cli/src/bin/common-stack/.
Original -> candidate bytes and SHA256:

- manifest.rs:10130/29c2b700c29e65c300d190deb9390e532bdb4bd18e856406ba1fbd2df9fe2900
  ->12220/9b12450a4f35848259f2bf40a83285ea0f0b12e4a64d80b0f2fa173297d8fc59;
  seven hunks,+74/-28.
- mod.rs:17543/50ba730b4b001c7c8db25416f739a7a1b5e16aa2bc3a1d60c7d17266099bf063
  ->18056/5b45a3b6ac36e66a453a0300ce9e16e7f1a3dacbbfc158bd2c4d1c1fdd778b1c;
  fifteen hunks,+32/-23.
- writer.rs:4486/df1b8d9f89034310f88e782250bae7bbc8da21b6d563e3c1cae61531633967e0
  ->4949/66569354c5c47ebd390342157c6f7b208eb72edc6685d6bb67eb98f2896f71b8;
  seven hunks,+15/-14.

A metadata-only unified-diff reader checked every old hunk against the actual
pinned source, reconstructed each candidate in memory, reversed all hunks to
the exact original bytes and rechecked the three live files unchanged. No
candidate source was imported or executed. This proves byte construction,
not compilation or scientific correctness. Sources and patch retain LF.
The first construction's mistaken CRLF assertion stopped before any write;
metadata inspection established LF and the corrected constructor preserved it.

## Narrow implementation

Manifest.inputs/Resolved.inputs become bounded vectors. Manifest::layout admits
only v1N3/128x96 or v2N2..8/axes64..512; channels/profile/noise/provenance and
Merge::fixed remain exact. Per-file and aggregate extents are checked before
visits. Per-visit preflight/read/parse still retains earlier folds on a late
shape/hash refusal. Dynamic receipt paths follow authenticated N.

Process passes actual layout into sizes, BandMerge/workspace, parsed dimensions,
proxy/variance allocations, complete counters and output observation. No fold
math or order changes. The existing four-level gate observer body is unchanged.
Initial incomplete is request-level v1; v2 result/frame schemas appear only
after valid manifest admission. The writer uses layout geometry/cap, retains
write/seek bounds and switches only version labels for v2. Its v1 labels,
quantization, tags and byte order stay literal. Whole-TIFF v1 identity remains
a future independently executed check, not a source-only outcome.

Only initial incomplete/stage are prechecked before manifest authentication;
all frame-slot freshness is checked afterward using N. That deliberately
changes the retained prefix of an existing-companion refusal, not any positive
image. Invalid v1 array length now reports an explicit bounded-count error.

## Exact new refusal predicates

- unsupported manifest schema
- v1 requires exactly three inputs
- v2 requires two to eight inputs
- unsupported common grid
- typed bounded input identity (per-file cap/identity)
- aggregate input capacity (defensive sum bound)
- TIFF dimensions do not match common grid (per-visit, before allocation)
- file hash mismatch (per-visit)
- complete declared input population (actual fold counter)

Grid is still u32; serde rejects out-of-range integers with its version-dependent
manifest JSON prefix. Do not call that execution of the checked-product guard.
Profile/noise/duplicate/provenance errors and actual reader semantics are inherited.
V2 pre-output report bound176KiB leaves16KiB under final192KiB; all complete
record sizing and component/resource/adversarial checks remain independent
release prerequisites. A report/image alone never supersedes actual exit.

Implementation-contract.md states all byte reservations and v1/v2 semantics.
Do not apply the patch until root admits the sampler final-source audit and
reviews this candidate; execution requires a separately frozen grant and
independently authored fixture/checker population.

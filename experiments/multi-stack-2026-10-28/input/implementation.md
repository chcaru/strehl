# Session input and original-CFA cache

Allocation: multi-stack-2026-10-28-input. Product ownership is limited to
session-input.rs and session-cache.rs. Root wires module exports and schedules
all Cargo builds, tests and RAW jobs.

## Input contract

SessionSpec version 1 has mode (combine/repeat/layers/hdr), ordered passes and an
optional primary_pass. PassSpec has a display name and ordered directory
segments. Unknown manifest and pass fields refuse. No filename relationship
implies equal focus. Session modes describe intent; a separate consumer must
refuse any mode it does not implement.

SessionSpec::load reads at most 1 MiB. resolve(manifest_path) uses the manifest
parent; resolve_from(base_directory) supports unsaved UI drafts. Canonical
directories/files cannot repeat. Each segment contains direct ARW files sorted
with the existing lexical order. The flattened census retains global, pass,
segment and both local frame indices. The ordinary merge's u16 index constraint
limits a session to 65,534 frames. primary_pass_index returns Option and does not
choose a numerical geometry anchor.

hash_sources(true) reads the complete original bytes with 64 KiB scratch and
rejects copied-content duplicates, irrespective of filename. File size and mtime
are checked before/after hashing. Cache consumers must obtain fresh identities
for each session, not reuse identities from an old manifest without hashing.
No duplicate-content result certifies independent sensor noise or focus identity.

SourceMetadata uses the owned identity and Sony optical readers only. It exposes
actual header ISO, rational exposure/aperture/focal-length, camera/lens/date and
header dimensions/CFA/levels. Actual decoded geometry/calibration still needs
consumer validation. Body serial and WB are explicitly None because these header
readers do not expose them. Malformed optical metadata refuses; it is not missing
metadata.

ensure_output_outside_sources resolves existing ancestors and links without
creating a path, and rejects capture descendants and exact linked RAW paths.
ensure_fresh_output also rejects every existing destination, including hardlink
aliases. A writer must still use create-new or atomic no-replace publication
because a preflight cannot close a later filesystem race.

## Cache contract

SourceCache::new(root, session, resident_cfa_budget_bytes) creates only an
external source-cache directory. load_or_decode(source, identity) returns
Arc<CachedSource>; load and store_original are also available. The owner is
mutable and serializes I/O. A shared owner can be protected by a caller mutex;
separate owners racing to publish the same entry refuse replacement.

CachedSource implements QuadSource directly. Its data are untouched active u16
CFA rows. Original active x/y, stride and buffer height are retained. Its
to_frame(max_allocation_bytes) restores original coordinates and synthetic zero
padding with an explicitly budgeted allocation. It never silently changes the
optical coordinate origin. Float calibration metadata is stored as exact u32
IEEE-754 bits, including the unused WB NaN. No aligned arrays or f32 pixels are
written to disk.

Cache entries bind complete input SHA256 and source identity to a decoder key
derived from cache-format generation, Cargo.lock and owned strehl-raw/lib.rs.
A bounded JSON header and little-endian u16 payload are covered by a SHA256;
length, version, geometry, calibration and digest are checked before admission.
Missing entries are distinct from stale/corrupt failures. A corrupt existing
entry is refused rather than silently replaced.

Publication writes a unique create-new temporary file, flushes it, checks source
stability and publishes complete bytes without replacement. Windows uses the
repository's MoveFileExW pattern without REPLACE_EXISTING; Unix uses atomic
hard-link creation followed by removal of the temporary name. Failure cleans
the owned temporary. Existing complete files are never overwritten.

The resident limit and high-water statistics cover u16 CFA samples retained by
the cache, including externally pinned Arc handles. Only unpinned least-recently
used entries are evicted. Two simultaneous originals need at least their combined
active byte count; insufficient budget produces typed CacheError::Budget.
Decoder scratch, metadata, fixed I/O scratch, guides, solve matrices and returned
Frame copies are separate working allocations that root's planner must include.
Disk size grows with distinct cached original identities; this is not a disk
quota or a total-process-RAM governor.

## Verification status

The root's first compile log, outputs/multi-stack/checks/session-input-cache.log,
shows the affected CLI compiling and all initial 9 session tests passing.
Its 13 warnings are in inherited research test paths. This note does not invent
an invocation absent from that log; root retains the run command.

After that run, three controls were added: fresh-output refusal including a
hardlink alias, strict merge frame-index limit, and no-replace publication under
an existing-destination race. Those changes are formatted and await the next
root-scheduled compile/test. Total focused tests: 12.

No RAW processing campaign or quality/performance claim comes from these unit
fixtures. They exercise source identity, ordering, offset/NaN preservation,
pinned-memory refusal, corrupt/truncated/stale files and safe publication.

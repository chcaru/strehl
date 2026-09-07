# M194b consumer implementation and evidence

The ignored test in `known-scene-benchmark.rs` uses M194's private
`run_pyramid_prepared` body for the actual CFA fold, gather, measured noise floor,
collapse, optional confidence reread and TIFF writer. M194 source arithmetic and
its existing tests are unchanged. The only addition to `merge_cmd.rs` is the
test-only module declaration. This does not exercise RAW decoding, metadata
discovery, sensor calibration, alignment estimation or defect preflight.

## Input and plan trust

Every invocation requires an external expected manifest SHA-256. Planning checks
strict typed JSON, duplicate and unknown fields, source paths and streaming
hashes, exact CFA lengths and the registered sensor/model settings. It constructs
the actual nine-frame WarpMap and production Crop before decoding pixels or
writing an image. Rendering requires the external expected plan SHA-256 and
compares the complete recomputed plan. Candidate-rehashed geometry cannot confer
trust on itself. Producer source/electron hashes in the manifest are declarations
bound by its external digest; their scientific commissioning remains separate.

`FileSource::decode` rechecks the exact file length and digest on every read,
copies active u16 little-endian samples into poisoned padded storage, and records
decode counts. The explicit injected noise model is gain0.25 DN/e, RN4 e,
black512/white15360 and ISO160. There is no camera profile lookup. Its coefficients
are shared with the synthetic producer, so these tests cannot validate calibration.
At 3000 DN signal the injected per-site variance is751 DN².

Both full9 and single4 use the full nine-frame crop and native coordinate gauge.
Original frame4 becomes source-local index0 only in the single arm; the receipt
states both indices. The output receipt binds actual TIFF bytes, decoded pixels,
dimensions, channels, writer Software tag and the entire planned configuration.
The registered actual crop is quad (9,7,142,106), hence native output284x212 and
canonical offset(18,14). Root's scorer owns the independent ROI/target checks.

Source-local reindexing also reaches the existing noise-floor probe's RNG seed:
the single arm uses local0, whereas original4 is index4 in full9. This is the
shipped single-input consumer behavior. The preserved reference/gauge statement
does not promise that every intermediate stochastic probe sample matches between
the single and stack arms.

## Builds and checks

`consumer-run.py build --build-record PATH` forces visible compilation, checks
unchanged source contents across the build and copies the resulting test binary
to a unique experiment directory. Later plan/render calls verify the external
build-record digest, source contents and copied executable before invocation.
Every subprocess clears numerical `STREHL_*` overrides and fixes two execution
threads. Raw command logs and structured evidence are retained.

`consumer-build-1.json` is the initial successful build with a full raw log.
Its field named `started_utc` was mistakenly assigned after compilation: interpret
it as record assembly time, not process start. `consumer-build-2.json` fixes that
metadata, recording start before subprocess and end after it. There is no timing
claim. Earlier development builds failed on an oversized JSON macro and the
SHA-256 output's formatting trait; both were corrected before build1. Those
development compiler failures are in tool history, not claimed as archived logs.

The final `consumer-build-3.json` also records the original Cargo compiler artifact's
path, SHA-256 and byte count before copying, then requires the copied executable
to match and rechecks the original. It has the same Rust source contents as build2;
the relinked executable has a different hash and receives a separate final check.

`consumer-checks.json` records successful scoped Rust formatting and Clippy. The
Clippy log contains `Checking strehl-cli` and no warning in the new consumer.
Existing build-script, estimator and writer warnings remain; this is not a claim
that the repository's strict all-target lint gate is clean.

`consumer-unit-tests.json` and its raw log record128 CLI tests passed, zero failed,
one ignored after a visible `Compiling strehl-cli` line. The ignored test is this
explicit-fixture benchmark; the focused fixture runs are recorded separately.

## Dependencies

Only dev dependencies were added: serde1.0.229 with derive,
serde_json1.0.151 with float_roundtrip, and sha2 0.11.0. The lockfile adds98lines
and removes none; the direct production dependency list is unchanged. Exact
resolved dependency versions, licenses and official metadata URLs are recorded
in `dependency-receipt.json`. All added dependencies are MIT or Apache-2.0, with
zmij MIT. Dependency metadata was inspected; implementation sources were not.

## Author controls and independent finding

`consumer-author-controls.json` binds the initial flat/noise-off author controls.
Full9, single4 and confidence-on main TIFFs are byte-identical, SHA-256
`4cf945da51c2fc41715c07c20188b0329c6de60d17f5a8aa3c2928b5ae86bfcd`.
Decode counts are nine times1, one times1, and nine times2 respectively. All three
receipts carry the same actual plan. This is an input/domain/writer and observer
control; it is not a texture, quality or noise-reduction result. Independent
verification is owned by another agent.

The independent verifier's initially expected padding identity failed on the
textured plane with the measured gate floor: changing only decoded storage layout
changed149804 of180624 TIFF components, maximum8 LSB. Preserve this initial
failure. Source inspection identifies a candidate mechanism in existing
`gatefloor::Probe::run`: its deterministic probe fills the entire flat storage
buffer, so active-coordinate samples depend on stride and origin. Original and
alternate layout logs also show different consumed floor summaries.

The follow-on isolation is preregistered separately in
`consumer-diagnostic-preregister.md`. A paired test-only marker and existing
`STREHL_GATE_FLOOR=white` setting is explicitly recorded in the plan; it cannot
reuse the measured-floor plan. It is excluded from the registered benchmark.
Independent white-floor pair/refusal results are recorded by the verifier.
No product correction or change to the registered measured-floor setting is made
here. The original storage sensitivity remains an observed limitation.

`independent-padding-isolation.json` records that the original and alternate
layouts become byte-identical with the white floor, while each measured-floor
arm reproduces its corresponding original TIFF exactly. The white floor also
changes the original output, so the intervention is live. Four diagnostic
pairing/plan-reuse refusals pass. Together with the source path this identifies
the existing measured-floor probe as the mediator for this fixture's storage
sensitivity; it does not establish layout invariance for every other render.

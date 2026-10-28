# Independent source review 02

Continuation of source-review-01, 2026-10-28. Reviewer independent_review remains
read-only outside this review directory. No build, test, RAW decode or render
was run in this review pass; execution receipts belong to the root's scheduled
lanes. Read source with numbered Get-Content/rg and recorded Get-FileHash SHA256.

## Fix verification

VERIFIED by source inspection: the original ordinary-setting carry-over defect
is addressed by app.rs import and app-session.rs prepare_session_controls. The
first revision saved only RenderSettings; reviewer identified an additional
counterexample: ordinary automatic exposure, session manual exposure, ordinary
import restored auto=true while leaving manual exposure set. Architecture then
changed the backup to existing history::Recipe. That object captures/applies
settings, exposure, gate and worker count. Backup survives reset_capture and is
captured only when entering a session from ordinary mode. Reload does not replace
it. Fresh ordinary import consumes it; absence falls back to normal Controls.

The revised session_control_restores_ordinary_defaults_and_user_choices_with_identical_command
control uses actual Controls for request scalars, changes session exposure/gate/
workers, and compares the complete Recipe plus ordinary command arguments across
default, automatic-exposure and temporal arms. This is meaningful coverage of the
reported interaction. Test execution was not independently run by this reviewer.

VERIFIED by source inspection: jobs-session validate_completed_sources compares
exact ordered engine source identities against frozen UI paths, byte lengths
and timestamps before TIFF validation, output-index publication and Completed.
Timestamp widening to u128 refuses an unrepresentable frozen value naturally.
The engine hash text and completion schema must be present. Controls cover
added/missing/reordered sources, path/length/time changes, invalid hash text,
missing completion and timestamp overflow. The UI snapshot is stamp-based; it
is not a claim to detect byte edits that deliberately preserve both size/time.

VERIFIED by source inspection: one-pass routing now writes source-identities
and carries SinglePassCompletion around the unchanged ordinary consumer. lib.rs
first propagates the consumer result, then completion rescans the exact census
and rehashes originals before creating completed.json. Failure does not enter
completed history; generated files can remain as failed-run evidence. The source
fixture includes unchanged, added-source and changed-source arms. These changes
address the original process-boundary census race.

## Noise-transfer cache review

No blocking source defect found in session-transfer-cache.rs or its integration.
The key binds full/cropped domain, exact f64 placement bits, complete optical
profile, resampler, every ProbeConfig field, OS/architecture, sampler/pyramid/
geometry/optics implementation sources and Cargo.lock. The cache records f32 bits
rather than formatted floating values. The measured operator is content-independent
only for supported linear resamplers; the nonlinear resampler is refused.

Reads are bounded to 1 MiB; schema/key/checksum, vector shape, positive finite
coefficients, minimum support, realization/seed identity and max-color bound are
checked. Invalid derived cache is rejected and remeasured. Create-new temporary
output, sync and atomic no-replace hardlink publication prevent partial records
from appearing under the addressed key. Concurrent publication accepts only a
valid existing record. Unsupported hardlinks and failed cleanup propagate errors;
this is a documented filesystem refusal, not a quality claim.

The integration supplies the same domain, placement, profile, resampler and probe
configuration as the former direct measure_band_transfer call. Source identity
is intentionally absent from the transfer key because source signal/noise values
do not enter this operator-only measurement. The source CFA cache is separate.

The existing cache control checks exact hit payload bits, a plausible positive
coefficient with a broken checksum, changed resampler/seed keys and nonlinear
refusal. An additional valid-checksummed wrong-operator envelope transplantation
would strengthen the key-binding control, though source inspection confirms the
mismatched key is rejected. These checks cannot establish photographic benefit.

## Reviewed source SHA256

| File | SHA256 |
| --- | --- |
| crates/strehl-ui/src/app.rs | 06e18c061d0a30ff7c97d766c4ca1f1cf751ddb00a93c81958806aab7b7e5326 |
| crates/strehl-ui/src/app-session.rs | f846098a5427d3f706ca988995fdee9dd80f4c30b1dcfc8ca6a0c74e22979bc3 |
| crates/strehl-ui/src/app-session-control-tests.rs | a400b235336b7c49f040fb7341d5a328378320412e96234c2456e080a288912d |
| crates/strehl-ui/src/jobs-session.rs | b1f0cbcaf00722a6bf7e9ef133fc15e5b785002b6ad7c6b94717cda5d9bc1123 |
| crates/strehl-cli/src/session-cmd.rs | 40b989fc4e24d6e238ad4b03a791270d8ede95d44f03d33cf52c8e6c78d18d9e |
| crates/strehl-cli/src/lib.rs | bfe63d3dfa915f954a1f767c7782f03e50e55188a5361668eba571778074aa81 |
| crates/strehl-cli/src/session-transfer-cache.rs | 2592a6741f3ea7071dad9a55ff5ad55e1c7e609632b12d9979d414aef30bff35 |
| crates/strehl-cli/src/session-consumer.rs | 6aa3c15df379d24fd8a782569e8ab7e3f0a838671c8e57815d73cfdb0e76f8e4 |

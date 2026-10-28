# Independent source review 01

Date: 2026-10-28. Reviewer: independent_review, not an implementation author.
Base: c149e52834fc1c86c2af0fe022713c39fa25f33c. Isolated multi-stack worktree only.

This is a source review checkpoint, not a photographic acceptance. No Cargo,
RAW decoding, render or desktop process was started by this reviewer. Commands
were read-only Get-Content/rg/Get-FileHash and explicit git -C/--work-tree diffs.
Read AGENTS, README, CONTRIBUTING, desktop-control, research-workflow and brief.
The root scheduled implementation/UI lanes; this reviewer made no source edits.

## Findings

1. P1, DERIVED: session preparation leaks forced flags into a fresh ordinary
   import. app-session.rs prepare_session_controls (reviewed lines 34-41) sets
   correct_lateral_ca/confidence_map false and clears ordinary choices; app.rs
   import (421-426) only clears settings.session. Creating a session then New
   stack changes ordinary behavior, including --fix-ca=off at jobs.rs 715-716.
   Architecture owner acknowledged and is preserving prior ordinary settings.
   Required control: nondefault ordinary settings, enter session, import a new
   ordinary folder, compare restored settings and generated ordinary command.

2. P1, DERIVED: frozen desktop source identity is not bound across the child
   process boundary. jobs-session.rs 119-136 compares UI import to a prelaunch
   rescan, but writes only SessionSpec into the engine manifest at 148-149.
   session-consumer.rs 502 and 523 resolve/hash the then-current folder census.
   Added/replaced files between these operations can produce a Saved photograph
   whose catalog/source recipe still describes the old census. Architecture
   owner acknowledged and is adding completed-source receipt validation.
   Required control: mutate a source census in an owned fake/delayed child after
   preflight and assert no Completed/Saved result and no accepted outputs index.
   Compare exact ordered paths, lengths and timestamps with checked Option/u128
   versus Option/u64 conversion. A count-only comparison is insufficient.

The one-pass delegation needs the same binding: session-cmd.rs 124-187 hashes
then discards source identities, writes session.json and delegates ordinary
stack. It emits neither source-identities.json nor completed.json, while the
current UI output index references the latter. Do not silently skip validation
for this route. Its metadata receipt describes a pre-consumer census; bind it
to the actual ordinary consumer or recheck before acceptance.

## Other reviewed contracts

ARGUED from source: optional primary remains distinct from the automatic
geometric reference. Repeat disagreement without primary uses the ordinary
fallback; a selected primary only prefers matched, supported overlap. Singleton
fast-path accumulation retains ordinary fallback behavior. Duplicate acquisition
keys, unfinished groups and nonfinite reconstruction are refused. This does not
validate calibration, focus equivalence or photographic benefit.

Session sources are grouped by explicit pass/segment order; no filename focus
coincidence is assumed. Session run snapshots clone layout/settings. Worker
outputs are create-new in isolated destinations and validate complete TIFF and
scene-linear master dimensions before acceptance. Native UI, error/cancel and
saved-run/layer interactions still require the scheduled executable exercise.

## Photographic controls requested

Complete images and float masters must be reviewed with one frozen display
transform before native witnesses. Joint-geometry --only-pass is a causal fusion
arm, but receives geometry from all passes and uses the new CFA sampler; it is
not the unchanged ordinary-stack reference. Include an ordinary primary-only
complete output to assess ordinary behavior and a no-repeat-grouping null to
assess the repeat policy. Explicit-primary Combine enables repeat grouping, so
that null removes both averaging and the matched disagreement preference; label
its interpretation accurately. Proposed same-focus pairs remain hypotheses.

## Reviewed source SHA256

| File | SHA256 |
| --- | --- |
| crates/strehl-ui/src/app-session.rs | 51f7feb2f4ad97aef4224aa85a8907fcc63b48c235ea9b9c97caeb2ec85c12c0 |
| crates/strehl-ui/src/jobs-session.rs | 7b3e78f3295bdc5619f0aa6a287fd1eb760ba2000ab848b30d0ee50309fa2719 |
| crates/strehl-cli/src/session-cmd.rs | 8eefbb25b395ce8a5350944aab4bcc1e001c4abe645e3dc9e1a3a8e117af3bb1 |
| crates/strehl-cli/src/session-consumer.rs | 43d2148bfef33a5378ab43b8a793b04ecf6d7a911d0ad177530a1f9dfaac9af6 |

# Independent engine formatting hunk audit

2026-10-28,root/independent_review. Product read-only. The supplied engine cargo-fmt check failed; this record does not claim an engine-wide formatting pass.

MEASURED audit command, exit0:

    python -X faulthandler -I experiments/multi-stack-2026-10-28/review/audit-engine-format.py

Input checks/engine-fmt-1.log SHA256 9a7f7e270b6c55ae350565d230b8e396e861e2cb53ac356652fd2cc43e1a2398. Every one of649hunks across50files was mapped against actual baseline commit c149e52834fc1c86c2af0fe022713c39fa25f33c and current source.642hunks are in files entirely equal to baseline;3more changed-file hunks remove only exact unchanged baseline lines. Four hunks describe three new logical formatting issues:

- crates/strehl-cli/src/lib.rs:19, put session_photometry before session_sampling.
- crates/strehl-cli/src/lib.rs:947, wrap route_single_pass assignment after the equals sign.
- crates/strehl-cli/src/merge_cmd.rs:73, relocate session_consumer declaration after sensor_master. Its insertion-only destination at reported79 is also new formatting, not inherited merely because the surrounding context predates this change.

Thus645hunks are inherited and4belong to3new logical issues. Full per-hunk old text, source hashes, baseline locations and classification are in engine-format-hunk-audit.json. Root was sent all three precise issues; this reviewer did not edit source. After their repair, only a fresh retained check can establish that no new formatting hunk remains; the645inherited hunks still prevent an engine-wide pass. UI's separately reported strict clippy and fmt success do not imply core/CLI success.

The first audit attempt failed because Windows subprocess decoded UTF-8 source as cp1252; no result was written. The helper then used explicit UTF-8, reran, and linked both halves of the module relocation. No Rust formatter, compiler, build or RAW job was run by this reviewer.

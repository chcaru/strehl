# Secondary owned import-capture launcher source read

Status: PASS_SECONDARY_SOURCE_REVIEW_ONLY. No launcher, collector, helper, control, child process, native API, image or numerical path was executed. Source text and selected original Job declarations were read; syntax was AST-parsed without evaluating it. Root owns the primary source review and actual release. This note supplies no execution permission or measured performance.

Exact reviewed files:

- local-image-checker-import-capture-launch.py: 19,019 bytes; SHA256 7779274a19161aebb83b7da19917dc77bbed3aa615418420ba97fe86052d32b8.
- local-image-checker-import-capture-preregister.md: 15,803 bytes; SHA256 19c2d953f5b29a460b9462bdb7e64784b4299f705886f28c5092755bfe015135.
- local-image-checker-import-capture-ledger.json: 1,782 bytes; SHA256 46efbfe2362522c323e1ec819c3cab1c8952f810b3bceec866f61098e78b1ad0.

The held collector remains 28,139 bytes / eebc2b6c8c0ba2c74672ac41287eab643ae16adb754e08639d3d7f45bdd12011. Its existing closed grant, original-plan, cumulative-resource and failed-audit authority checks remain in that process. This wrapper is capture-only transport, not an independent verifier of a complete registry or saved scientific data.

## Independent choices

Ownership starts with a private Job and a suspended direct child. The selected native declarations come from the original plan-bound harness; complete requested names/signatures must be selected before evaluation. Installed flags 0x2204 retain kill-on-close, the Job user-CPU limit and committed-memory limit. The actual queried configuration must match 15 s user CPU and 1 GiB committed memory. Live polling additionally checks total user-plus-kernel Job CPU against 15 s, peak Job committed memory and whole child wall against 25 s. These quantities are not RSS, and the kernel's user-time limit is not mislabelled as a complete total-CPU limit.

The child is assigned before it is resumed. If assignment fails, only the retained direct child is killed. Once assigned, termination addresses only the owned Job. The cleanup deadline is bounded by both five seconds from cleanup entry and launcher START+30. The original retained Popen handle supplies before/after creation and CPU fields; the observed direct-process CPU is a cross-check inside the Job, never another addition to the same work. A missing exit, live Job, read error, incomplete pipe thread or cleanup error prevents successful capture. Closing the kill-on-close Job is not itself evidence of a clean measured terminal state.

Each raw pipe has a dedicated reader and bounded queue; the consumer retains at most 8 KiB stdout and 31 KiB stderr. It records observed byte counts, EOF and overflow separately. Receiving both EOF markers in queue order implies all preceding enqueued data was handled. Failure cleanup can stop readers and retain only a prefix; such a prefix is not treated as complete transport. Ordinary success requires both EOFs, no overflow, no cleanup error, no termination and zero child exit with no active Job process.

The wrapper authenticates its own isolated -I -S -B argv, exact grant and sources before launch. It checks the unchanged collector's full command with actual grant digest substituted for the plan placeholder. Captured console schema/status/exit, fixed final path, same final bytes and grant association agree with the held collector's actual interface. The whole registry and control outcomes still require independent outcome review; shallow console agreement does not admit a downstream saved-data audit.

Final outer publication uses a complete fsynced stage, atomic replacement and same-object/same-byte readback. A post-publication exception changes the actual exit disposition to 1 and attempts one finite refusal publication. That recovery can itself fail; an earlier positive outer or escaped advertisement then remains stale. Consequently the separately captured actual launcher exit, full interval and raw advertisement are mandatory for admission. The source does not claim an infallible filesystem recovery or infer final process CPU from a prepublication sample.

## Reserve corrections and conclusion

The held version requires launcher_sample.cpu_seconds + 0.25 <= 3 and launcher_sample.wall_seconds + 2 <= 32 before preserving successful disposition. Final guard and independent actual external interval remain required; a reserve is not a terminal measurement. Collector CPU is inside its own 15 s lane, launcher CPU inside the separate external lane, and overlapping parent/child wall must not be charged twice as distinct elapsed intervals.

The simultaneous 64 KiB outer-stage file is now explicit in the existing 2 MiB capture allocation. Independent literal addition of every retained-family slot gives 1,548,288 bytes allocated and 548,864 unallocated, exactly 2,097,152 total. This is a source-derived maximum, not an observed output inventory. It grants no additional invocation and does not refund earlier attempts. Source and review files belong to the preparation lane.

No additional blocking ownership, cleanup, publication or collector-interface mismatch was found beyond the two corrected reserve omissions. Actual failure, overshoot, malformed output or missing terminal evidence must remain refused, even if some import evidence is useful. Include this note in the optional positive preparation-source closure if it is used at release. The source review does not make the original local-image subject complete or admit geometry.

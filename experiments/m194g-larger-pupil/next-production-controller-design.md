# Production command and matrix controller

Source preparation only,2026-09-07. No source import, child, build or output
has been executed by these new controllers. Root supplies externally pinned
releases and runs them after source/independent review. Held noise, build and
Rust bridge sources are unchanged by this lane.

`production-command.py` supplies the shared parent-observed launch path;
`production-matrix.py` uses it for the exact matrix in
`next-quality-matrix-design.md`. Matrix state ordinal is global0..17: flat's
nine states then textured's nine. Even state ordinals start HardFloor, odd
start FloorPedestalV1; final rows36/37 are endpoint0/4. This is fixed scheduling,
not a timing experiment or a setting selected from observed results.

## Executable and actual child observations

Every actual Rust command consumes the external `m194g-bridge-build-v1`
`COMPLETE_COMPILED_TESTS_ONLY` record, current compiled include/source closure,
actual compiler/copied executable pair and the exact eight-test listing.
The controller executes the pinned build helper's source discovery, never a
new compile. The helper itself is loaded from the checked bytes. The matrix
likewise loads its command dependency from release-checked bytes rather than
an unverified cache file. Root freezes fresh interpreter cache paths anyway.

Intended ignored test is
`merge_cmd::known_scene_benchmark::noise_pupil_bridge::m194g_noise_production_bridge`.
This is the actual build2 listing; the earlier design's `production_truth`
namespace inference was corrected before these controllers execute. The exact
ignored argv order is executable, `--exact`, test name, `--ignored`,
`--test-threads=1`, `--nocapture`.
The ordinary `::private_controls` filter requires6 passed/1 ignored; its
ignored `::m194g_private_production_outputs` test requires1 passed/0 ignored.
Actual source/executable hashes and actual parent return code are checked
before a single test-count summary can be accepted. A printed pass with exit7
is a refusal, as is a zero-exit zero-test result.

The environment clears other STREHL settings and pins defectoff, CAoff,
fullres-gather1, pyramid-workers2 and Rayon2. Launch records include explicit
nulls for removed floor/debug/scale and other inherited overrides. Namespace,
absolute paths and fields follow the held `production-bridge-command-design.md`.
The command wrapper does not introduce exposure, confidence or alternate merge
settings. A public invocation output directory is fresh; plans, receipts,
TIFFs and logs cannot overwrite prior files.

One child is active at a time. A queue of at most eight64KiB chunks drains the
combined stdout/stderr pipe. The parent writes at most16MiB, refuses on the
first excess chunk and retains that bounded prefix. A240-second operational
wall allowance applies to a production child; final observation checks the
same allowance. Timeout/overflow termination addresses only that `Popen`
child, never a peer or arbitrary host process. Cleanup has bounded waits and
any failure remains a failure. The meaning is exceeded operational allowance,
not an inference that a process was dead.

All controller-owned metadata and logs, including private fixture source/CFA
files and child plans/receipts, count toward64MiB. Actual intended/private
TIFF payloads are separately bounded by the independent TIFF reader; they are
still hashed through controller finalization. This is file bookkeeping,
not a process-RSS or performance claim. Late source/input/output failures
retain the first result as rejected and attempt to persist the downgraded
record, preserving the original exception if retention also fails.

## Twenty-three private launcher controls

The actual current build/list is a positive companion. Remaining process
fixtures use explicitly private local Python children, with real interpreter
hashes and actual exits; their private launch schema and absolute interpreter
observation cannot enter the repository-only production matrix. There are no
fake successful bridge authorities.

Exact control order:

```text
actual-build-and-list
build-source-omission-refused
build-artifact-mismatch-refused
build-list-omission-refused
build-metadata-restored
environment-overrides-cleared
environment-restored
output-association-valid
output-association-stale
output-association-restored
actual-zero-exit
actual-nonzero-exit
zero-tests-refused
duplicate-summary-refused
exact-log-limit
log-overflow-refused
actual-timeout-refused
fresh-output-refused
changed-source-refused
restored-source
preserved-prior-failure
wrong-executable-command-refused
final-build-and-list
```

The log positive writes exactly16MiB including one valid test summary. Its
destroyer writes16MiB+1; the retained prefix must remain16MiB. The timeout
control uses the same live capture/termination path with an explicitly private
0.2-second allowance against a five-second sleeping fixture. This can include
startup; it tests the operational deadline, not workload progress. A controlled
source file changes while a zero-exit child runs; the actual post-child source
guard must refuse. It is restored in a finally path, and a new successful
child follows. The earlier exit7 launch remains unchanged. Every started
control is retained if the suite stops.

The build controls call the real `Build` consumer on small metadata copies:
omitted source, mismatched copied artifact, missing listed test, and restored
metadata. They refer to the unchanged actual build2 artifacts. A poisoned
parent-environment companion checks actual removal and restoration. A small
private output tests path/hash/byte association with a stale-hash destroyer.
Every genuine render applies this same association to its actual receipt and
TIFF. Post-child artifact-validation failure retains the actual launch and
its zero exit separately from the parent's refusal; the matrix retains that
launch in `work.failed_launch` until all row checks pass.

Root-release scopes are `production-launcher-controls`,
`production-private-controls`, `production-private-outputs`, `production-plan`
and `production-render`. The CLI requires release/hash, build/hash, kind and
new output directory. Intended calls add noise-admission/hash and exact
scene/seed/subset/admission/observer; render adds its actual plan/hash.
Root's actual original argv must equal a released command. The wrapper result
is `m194g-production-command-v1`, status
`COMPLETE_PRODUCTION_COMMAND_UNVERIFIED` or `UNCOMMISSIONED_PRODUCTION_COMMAND`;
it retains the actual launch and child file refs, never a TIFF-quality verdict.
The private launcher child result is `m194g-production-launcher-controls-v1`,
status `PASS_PRIVATE_LAUNCHER_CONTROLS_ONLY`, with fixture_only true and all23
literal passing rows.

## Matrix and its two additional upstream commissions

The matrix release scope is `quality-production-matrix`. Before the first
child, it writes all38 exact plan commands/environments and render
commands/environments, with the sole dynamic render plan hash represented by
`ACTUAL_SAME_CASE_PLAN_SHA256`. All38 plans are executed, reopened, associated
with their settings and checked for the common geometry before any render.
The corresponding resolved plans are persisted. Each actual launch must match
its predeclared command/environment, substituting only its actual plan hash.

Every render is a new Rust process. The parent requires exactly one finite,
nonempty measured-floor banner of length at most2 and its single contribution
count5 (main) or1 (endpoint). It does not turn four-decimal printed floors into
exact calibration. No failed command is rerun or removed from the fixed index.
The index remains the closed `m194g-production-matrix-v1` from root's design;
success is `COMPLETE_38_RGB_OUTPUTS_UNSCORED`, not a quality result.

`bridge_commission` is a repository FileRef to the externally pinned closed
`m194g-production-bridge-commission-v1`, status `PASS_PRODUCTION_BRIDGE_ONLY`.
Exact keys are schema/status/ref_root/build/private_tests/private_outputs/
intended_outputs/independent_read/execution_release/sources_before/
sources_after/inputs_before/inputs_after/error/finalization_errors. The six
build/private_tests/private_outputs/intended_outputs/independent_read/
execution_release values are FileRefs. Root's independent read must establish
6 ordinary tests,6 private RGB and12 intended RGB including observers/endpoints,
actual exits/TIFFs/logs/settings. This controller binds that authority; it does
not issue it.

`instrument_commission` initially binds the exact
`m194g-quality-instruments-v1` / `PASS_QUALITY_INSTRUMENTS_ONLY` result with69
genuine passing rows, stable sources, null error and empty finalization errors,
as defined by `next-quality-instrument-interface.md`. Root will also require
the separately commissioned matrix-association adapter before candidate
scoring. The69 instrument result alone does not grant target or scoring
authority. Both gates, actual noise-file admission, build record and all
released source/input hashes are rechecked through final matrix persistence.

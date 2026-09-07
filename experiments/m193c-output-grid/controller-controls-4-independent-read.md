# M193c controller controls 4: independent actual-result read

**VERIFIED by independent readback: all fourteen registered process controls
passed, including the three powered post-exit drain cases.** This commissions
the amended owned-process helper within that finite scope. It is not a build,
private-image, RAW, registration, numerical, or quality admission. The earlier
failed private campaign remains failed; its missing pre-cleanup observation is
not reconstructed from these new controls.

This reviewer inspected all actual outcomes, logs, startup/completion markers,
source snapshots and release references with read-only metadata/byte operations.
No author module was imported and no experimental child, control, build, image
or RAW operation was rerun.

## Actual release, command and final result

Root executed the frozen revision
`4339bdaa06cc603fbc9f6f85f757e41e639960a1` using
`controller-controls-release-4.json`, 4,369 bytes, SHA256
`63e229c90510650678b52f384572498125543ebb662ff63ace1c635c1d48dd16`.
The actual result is `controller-controls-4/result.json`, **71,176 bytes**,
SHA256 `6598085965a18d0165073a0ebcfcbdc44ed543008af64f569182965eddea8b80`.
It has schema `m193c-controller-controls-v1`, status
`PASS_OWNED_PROCESS_CONTROLS_ONLY`, null error and empty finalization errors.

The original OS exit is root's observation, not a wait performed by this
reviewer. Its actual record, `work/controller-controls-4-outer.json`, is 1,031
bytes, SHA256
`cd450f0669e97a7d60b831c34f96d3e8d5fb75d134439de38ad6a557e0c29778`.
It records **exit 0 and 17.2566174 seconds** of direct invocation wall time.
The stored result separately reports **17.07900000002701 seconds before result
publication**. These are different observation scopes; both lie below the
registered complete-controller 120-second wall limit.

The actual interpreter argv matches the release after its sole actual-SHA
substitution and matches the outer launch record: the specified Python312
executable, `-X utf8`, `-X faulthandler`, the fresh
`work/cache-controller-controls-4` prefix, the controller script and its exact
release/hash/output arguments. The retained exit text and console status agree.
This is an observed invocation and source binding, not a hermetic Python runtime
or operating-system certificate.

## The original eleven outcomes remain separately visible

All row indices are exactly the integers 0 through 13, with the literal ordered
modes from amendment3. Every row has actual terminal Job accounting and zero
final active processes. The table records the relevant observations rather than
using the stored `passed` fields alone.

| Index / mode | Independently inspected deciding evidence |
| --- | --- |
| 0 valid | Exit 0, exact `M193C_VALID_CHILD` log, no error/cleanup; ordinary zero-active completion without termination. |
| 1 nonzero | Exit 7 and exact exit-seven marker; helper error remains null. A reported nonzero child is not converted into a successful caller result. |
| 2 exact-log | Exit 0; actual file contains exactly 65,536 `x` bytes. |
| 3 overflow-log | Named child-log bound refusal; exactly 65,536 retained `x` bytes; owned termination attempted/succeeded and final active 0. |
| 4 timeout | Actual sleep-start/PID markers; original one-second wall refusal, owned termination and terminal zero. |
| 5 nested-timeout | Parent PID 7476, requested/executing child PID 29772; actual lifetime associations 4 versus valid companion 2; original five-second wall refusal and owned cleanup. |
| 6 memory-allowed | Actual 134,217,728-byte allocation marker, exit 0; configured 256 MiB, peak Job committed usage 144,588,800 bytes. |
| 7 memory | Actual memory-refused marker and named parent committed-memory refusal; peak 144,863,232 bytes exceeds configured 64 MiB. Recorded route is `parent-observed-peak`; this is not relabelled a clean exit-7 route. |
| 8 late-log-binding | Original log-bound refusal retained, plus the sole intentional `M193C_PRIVATE_LATE_LOG_READ` cleanup error. Observation log ref is null, but the actual 65,536-byte `x` log is retained and independently hashed through the artifact list. |
| 9 changed-input | Actual changed-input marker, exact watched-input-change refusal and owned cleanup. |
| 10 restored | Original valid marker/exit 0 restored; same actual log bytes as index 0. |

The three large logs were independently read as byte arrays; each had length
65,536 and zero non-`x` bytes. Short logs were read in full. All fourteen actual
log extents/hashes matched their available observation refs or, for the intended
late-binding exception, its retained artifact ref. The final watched-input file
is retained at 22 bytes with its declared restored binding.

All calls retain ten CPU seconds and 65,536 log bytes. The ordinary committed
memory limit is 64 MiB; only the registered allocation-positive companion uses
256 MiB. Actual Job limit flags are 8,704 and the readback values match each
call's declared limit. Memory figures are committed-memory observations, not
RSS or proof that polling cannot overshoot. The named negative-memory predicate
remains the one registered after the prior refusal.

## Three actual post-exit drain chains

The independent choice here is to reconstruct completion from actual parent and
descendant identities, markers, direct exit, pipe EOF, retained positive-active
Job observations and explicit termination records. Neither direct exit 0 nor
final active 0 alone determines the disposition. In particular,
`TotalTerminatedProcesses == 0` is not used as evidence of natural completion.

| Mode | Parent / child PID | First / last ordinary drain active | Drain polls | Helper wall | Actual disposition |
| --- | --- | --- | ---: | ---: | --- |
| drain-finish | 44472 / 3668 | 2 / 0 | 192 | 2.155999999959022 s | Completed, no error, no termination attempt. |
| drain-persist | 25588 / 14372 | 2 / 2 | 470 | 5.032000000006519 s | Original five-second wall refusal; completed false; explicit owned termination succeeded, final active 0. |
| drain-restored | 26348 / 24088 | 2 / 0 | 192 | 2.14000000001397 s | Completed after the negative; no error or termination attempt. |

For all three, the actual direct parent exited 0 and the captured pipe reached
EOF. The separately saved startup JSON identifies the same child PID as both
the requested PID and executing PID in the actual parent log, a distinct parent
PID, and the matching startup SHA. The parent log explicitly records that the
child was live before parent exit. The owned fixture source directs the
descendant's standard streams to DEVNULL; the control therefore does not confuse
an inherited open pipe with its Job-lifetime witness. These controls identify
their actual participating PIDs; they do not identify every lifetime Job
association or explain the separate two-versus-four association multiplicity.

Both healthy completion files exist, have actual hashes matching their refs,
and repeat the startup mode/PIDs/start timestamp. Their monotonic pairs are:

- finish: `795819906000000` to `795821906000000` ns;
- restored: `795827078000000` to `795829078000000` ns.

Their independently subtracted descendant intervals are exactly 2.0 seconds in
the retained clock samples. The helper waits approximately 1.968 seconds after
direct exit/EOF in each, without resetting its original clock. Its total elapsed
time remains below the original ten-second allowance. The different timer
origins are not forced to be identical: no absolute helper-start timestamp is
present from which to infer a finer cross-process ordering than the actual
identity/active/EOF/completion records establish.

The persistent startup timestamp is `795822062000000` ns. There is no completion
file or completion ref. Its ordinary drain begins at approximately 0.172 seconds
on the helper clock, ends at 5.016000000061467 seconds with exactly
`ValueError('child wall bound')`, and retains active 2 both initially and in its
last ordinary sample. `completed` stays false. Cleanup separately records
termination attempted true, active 2 before that attempt, succeeded true, and
terminal active 0. The direct child's exit code remains 0; accepting merely that
zero would incorrectly admit this negative. Final helper wall includes cleanup
and is approximately 5.032 seconds, not an enlarged success allowance.

Each new case retains only the first sixteen actual polling records, in
nondecreasing time order, but also records its larger poll count and separate
last accounting. The 192/470/192 counts establish that the sixteen-record
retention cap did not stop the observed wait. The two healthy completion files
and absence of termination attempts distinguish normal completion from forced
cleanup; the persistent case demonstrates the opposite branch. All three have
empty cleanup errors and actual terminal accounting.

This is a powered contrast with the old immediate-zero rule: each healthy
companion actually presents a nonzero first sample. The old condition would
reject that sample. This statement is a source/counterfactual interpretation of
the actual stimulus, not a rerun of the old helper or a diagnosis of the lost
private1 observation.

## Complete actual bindings

Readback independently rehashed all four current source files, their four saved
snapshots, fourteen release inputs and twenty-four retained artifact refs.
There were no mismatches. Source names and before/after bindings equal the
released four-source map. A scoped diff against `4339bdaa` over the released
source/input paths was empty at inspection.

| Source | Bytes | SHA256 |
| --- | ---: | --- |
| `bounded-process.py` | 12,664 | `47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b` |
| `controller-child.py` | 4,416 | `8944b1387990a262d1ad47c44ee2bbd7de281323185a0758802f1637289d2788` |
| `controller-controls.py` | 18,455 | `217999b5969a29224868fe731284493e04ce0ef33bd225fc4c9f3bc3f8b5b84c` |
| Owned `m12-harness.py` | 117,908 | `6cfb408992f37b225f102da4d62ba836f9c5b67c92bdd418ff460987866a1bb9` |

The artifact set is four source snapshots, fourteen logs, the watched input,
three startup markers and two completion markers. A recursive `-Force` file
enumeration finds exactly these twenty-four artifacts plus the terminal result:
**25 files, 423,034 retained bytes**, with no unexplained file in the controlled
output directory. The negative's completion marker is absent. Original failed
control/private records referenced by the release remain unchanged.

## Scoped conclusion

The actual fourteen-case process result and its sources support the build3
prerequisite. The prepared build release must bind these exact current helper
bytes and this actual result, with this independent read; build2 does not acquire
authority over the new helper retroactively.

The new tests exercise post-exit waiting and the original wall boundary. They do
not independently isolate every possible post-exit CPU/memory/source-change
sequence, prove a universal shutdown-time bound, or establish successful images.
The retained source keeps the same clock/counters and caller checks throughout
drain; the original eleven actual cases retain their narrower established
coverage. No numerical threshold, image population or physical claim changes.

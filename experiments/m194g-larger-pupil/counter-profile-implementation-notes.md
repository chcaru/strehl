# Counter-profile harness handoff

2026-09-07. Implementation only; **no harness execution or private profile has
occurred** at this handoff. Root owns the source/command freeze and sequential
launch. `next-counter-plan.md` remains an unexecuted alternative, not the run
protocol. The implemented protocol is the committed
`counter-profile-preregister.md`, SHA
`eadf399b5998fa4d458b44ea565e1f27d29eaaab39f65751c25739df67412f3e`.

The CLI is `counter-profile.py --mode MODE --output FRESH_DIRECTORY`.
Modes count, placebo and mutated-cut additionally require
`--baseline-result OFF_DIRECTORY/result.json --baseline-result-sha256 OFF_SHA`.
Root obtains that external SHA from the actually completed off run; the
original argv records the supplied digest. Off forbids these arguments.
The fixed9×6/five-frame/three-arm scene is constructed literally in
`make_inputs`, and its complete dataclass representation is recorded.

Entry CPU/wall timestamps precede imports and fixture/profiler setup. They are
passed into the actual frozen `Budget` with10CPU/20wall, unchanged strict
point/node limits and array scope. The actual counter's per-cell/rule checks
remain untouched. Final checks occur after profile/payload persistence and
source revalidation. Failure evidence can be written after a limit refusal;
that does not authorize more geometry or change refusal into admission.

Every mode writes `result.json`, containing its complete actual counter result,
source/import bindings, exact arguments, private inputs, work receipt and
checks. A successful mode also writes canonical `geometry-payload.json`,
containing every frame/arm row, coordinate/branch/root/point/node count, actual
last coordinates, full integrator records, total counts and ordered digest.
Only timing/resource/observer information is omitted from that deterministic
comparison. The reopened baseline payload bytes and their digest are checked
against the externally pinned off result, then compared directly.

Count and placebo persist the binary `profile.pstats`, every function/caller
record in `profile-functions.json`, and the untruncated cumulative table in
`profile-functions.txt`. Function liveness uses the actual source filename plus
function name for count_geometry, point_cuts, angular_cuts, _stream and
Budget.check. The failure path attempts to preserve these same complete
artifacts if collection was active when geometry refused. A secondary
persistence/source error is separately recorded without replacing the original
failure traceback.

Off constructs no profiler. Count constructs and enables cProfile only around
the actual count_geometry call. Placebo constructs the same profiler but never
enables collection. Before the source freeze, root verified in the installed
Python3.12 standard-library source that `pstats.Stats` rejects empty stats. The
harness therefore handles the intentional empty placebo directly: binary empty
stats, JSON `[]`, explicit empty text and zero collected-call fields. This was
a source-review correction, not a failed profile population.

Seven real radiance/integration entry points are temporarily replaced in
memory. Each trap is deliberately called once under a separately labelled
direct-liveness phase; any call during genuine geometry is a distinct counter
and fails. No original file is changed. Mutated-cut wraps the actual frozen
angular_cuts and removes exactly the first interior cut of the first returned
multi-interval partition. Its before/after values and call witness are saved.
It must lower nominal work by one primary48-node interval, preserve points,
change the real ordered digest/payload, and be rejected by equality comparison.

All four modes run in separate fresh-cache processes in the registered order.
A mode failure exits nonzero and ends the diagnostic; later modes must not be
launched, and no profile allowance increases or extra stimuli are implied.
The harness reports `PASS_PROFILE_MODE` or `UNCOMMISSIONED_PROFILE`; neither
confers intended full-image cost or radiance authority.

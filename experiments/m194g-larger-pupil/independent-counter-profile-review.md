# Independent source review of the bounded counter profile

2026-09-07. **Source/design review only; no harness execution by this reviewer.**
No blocking source defect was found in `counter-profile.py` at SHA256
`fc1dd81cf3c6dbccdb46830dcffb98a91b21f05f2a89089d9f40c85f253d0020`.
The proposed four-mode schedule is suitable for a prospective diagnostic
release, conditional on inspecting the actual complete results. This is not
a claim that any mode has passed or will fit its resource allowance.

The reviewed preregistration SHA256 is
`eadf399b5998fa4d458b44ea565e1f27d29eaaab39f65751c25739df67412f3e`;
it was committed at `76b255db` before this harness was implemented. The reviewed
release draft is `counter-profile-release-1.json`, SHA256
`819ca88ca69919f1881aabb5fa3f21d140f1308e5e2441c876fc8b6c9c4f1a06`.
Its only deferred command substitution is the external SHA256 of the completed
off result. The root still owns the source/command commit and launch.

## Choice points checked in the actual source

- `make_inputs` uses the registered private 9×6, five-frame, three-arm model,
  including its nonidentity similarity and the original index/focus sequence.
  It does not import or silently resize the intended fixture. The actual
  counter and its low/high geometry helpers remain pinned and unchanged.
- `ENTRY_CPU`/`ENTRY_WALL` are sampled immediately after importing `time`,
  before remaining harness imports, NumPy, source loading, fixture construction
  and profiler setup. Those samples are passed into the unchanged real
  `Budget`, rather than replacing them with later counter-module entry times.
  The 10 CPU/20 wall clock does not reset across cells, frames or arms. It is
  checked after profile persistence, payload comparison and final source checks.
  This is a cooperative clock contract, not an operating-system process-kill
  deadline. Final terminal-JSON serialization and its last fsync occur after
  the last success check; do not describe the resource receipt as a measurement
  through process exit or reconstruct it from JSON start/end timestamps.
- `geometry_payload` retains all complete frame rows, input records, dimensions,
  frame/arm lists, final coordinates, coverage counts, both aggregate work
  counts, and the ordered stream digest. Resource/observer metadata is outside
  the invariant payload as preregistered. Both canonical bytes and the geometry
  digest are compared; the comparison is not merely between declared hashes.
- Non-off modes require an external baseline-result hash. `baseline_payload`
  reopens the actual off result and canonical payload file, requires the same
  source/input/protocol bindings and a complete private result, and verifies
  actual path/hash/length/canonical bytes. The root's independently collected
  off result supplies that external authority; embedded hashes alone do not.
- Off constructs no profiler. Count constructs and enables one only around
  actual `count_geometry`. Placebo constructs one but never enables it. The
  empty-placebo path writes empty collected artifacts without constructing a
  `pstats.Stats` object from an empty profile. Complete tables and the binary
  profile are retained, including failure salvage when possible.
- Count-mode liveness uses actual source filenames plus function names for
  `count_geometry`, `point_cuts`, `_stream`, `Budget.check`, and frozen
  `angular_cuts`. The corresponding actual module paths/import bindings are
  retained. Success requires all named call counts to be positive; the placebo
  requires zero collected functions and calls.
- Seven actual radiance entry points are replaced by exception traps. Each is
  called directly once under the separate intentional-liveness phase. During
  the actual counter phase, the same traps count genuine calls separately;
  success requires all seven intentional counts to be one and genuine counts
  zero. The intentional liveness exercise must not be reported as actual
  radiance computation or added to the zero-call observation.
- `mutated-cut` changes the actual return of frozen `angular_cuts` at the first
  multi-interval point, removing one interior cut without changing endpoint
  ordering. It does not edit a result descriptor. Success requires actual
  application, a different canonical payload and stream digest, unchanged
  point count, and exactly 48 fewer nominal angular nodes. The last requirement
  is appropriate because the fixed first arm is primary with 16+32 angular
  orders. The genuine geometry must still complete all 810 cells and 15 rows.
- Source snapshots include the harness, protocol and all five actual pinned
  implementation/model files; before/after source equality and frozen-module
  identity checks precede success. The release also binds the explanatory
  implementation note. The note is not an executable dependency silently
  omitted from a compiler/import set.

The harness retains partial count, exception, profile-salvage and source-capture
information on failure. A nonzero mode or failed independent result read ends
the released schedule. The first off result cannot authorize count/placebo
after its own failure, and the mutation cannot qualify an intended population.

## Scope of the report read

`docs/research/M194g-larger-pupil.md` at SHA256
`18d5e00f76ac20b0708f7cae8192d5bc332a8be8ecf710be8f3f02e5db7be429`
contains no consequential misstatement found in this read. It preserves the
CPU refusal, incomplete refined population, classified-versus-completed cell
distinction, active preflight limits versus frozen integrator fields, the
resource-clock start before the recorded timestamp, and arithmetic angle-order
doubling versus independent evidence. It does not grant radiance or quality
admission from the component passes or successful primary subset.

After execution, independently read every mode's actual population, source
snapshots, payload and profile table. Profiled timings attribute the instrumented
small fixture only. They must not become an unprofiled speed estimate, a claim
about the intended cost distribution, or an optical-model test. Any later
optimization or counter-only budget amendment remains a separate prospective
decision; this source review does not release it.

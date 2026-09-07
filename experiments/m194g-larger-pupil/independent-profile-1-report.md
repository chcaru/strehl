# Independent review of the stopped profile diagnostic

2026-09-07. **VERIFIED: off mode completed its private geometry population;
the profiling diagnostic is UNCOMMISSIONED.** Count mode refused at its
baseline-input comparison before constructing a profiler, running geometry
or installing radiance traps. Placebo and mutated-cut were not launched.
No attribution table, profiling overhead estimate, observer byte-invariance
claim or optimization evidence follows from this schedule.

## Cause established on the actual source and records

The frozen harness at
`fc1dd81cf3c6dbccdb46830dcffb98a91b21f05f2a89089d9f40c85f253d0020`
uses `dataclasses.asdict` in `make_inputs`. That operation preserves nested
tuples. Its saved JSON turns them into lists. `baseline_payload` compares
the reloaded `record['inputs']` directly against the next process's live input
dictionary. That is a real executable incompatibility, not an actual input
or source mismatch.

The independent diagnostic extracts only the actual `make_inputs`,
`baseline_payload`, `read_bound` and `canonical` function definitions from
the checked harness. It constructs inputs with the actual checked model
dataclasses and calls the extracted baseline reader on the externally pinned
off result. It does not execute `run`, `load_counter`, `count_geometry` or any
profiling mode. The exact recorded ValueError reproduces. Of the seven
conjuncts in that rejection condition, only the input comparison is false.

There are sixteen tuple-valued paths: both fields' affine/wave containers,
scene depths/normal, and each of five frames' similarity centre/translation.
The live input's canonical JSON exactly equals both saved input records.
Using only JSON-normalized containers as the read-only diagnostic companion
makes the same actual reader return the original payload bytes. Changing
the final frame's focus from 1.5 to 1.625 still refuses. This separates a
representation mismatch from a permissive numeric-input comparison. A later
correction, if ever commissioned, would need to address both direct input
comparisons in `baseline_payload`, including its payload-input comparison.
The historical harness was not edited or rerun.

My earlier source-only review at
`independent-counter-profile-review.md` did not catch this defect. Its
pre-execution no-blocker verdict was wrong about this executable boundary;
the historical review is retained. The actual failure is not reclassified as
an environmental error or proof that the harness behaved as intended.

## Actual off population and provenance

The off result SHA256 is
`c4d3298dd64df03f092e5904b3dbf08c6ebbb8284f5e7ddb5e142d0193f75762`.
Its canonical payload SHA256 is
`b05e5f7f4b5d9d86c69cee4fd6eb7ba116781d7b997b49611b884d566df2e78a`.
All fifteen expected arm/frame rows complete 54 cells each, ending at `[8,5]`:
810 complete cells, 167,040 points and 39,819,840 nominal angular nodes.
Each row's branches match an independent exact-dyadic predicate over the
private grid. All root/point/node/interval counts and the ordered stream
digest match the retained independently constructed private reference from
`independent-preflight-3`. The digest is
`70a91137c45db1004ad3517995d8986fec94b115764b2f16dc09b79243ea0ee2`.

Off recorded eleven passing checks. No profiler was constructed. Each of
seven radiance traps recorded one intentional direct call and zero genuine
counter calls; the intentional calls are liveness tests, not radiance
evaluations. Its resource receipt is 1.546875 CPU / 1.547000000020489 wall
seconds under the diagnostic 10/20 budget. Those numbers describe this small
off invocation and do not predict intended-frame cost or quantify profiler
overhead.

The count result SHA256 is
`d80f9f77b9bcb415eee5c423c30b4f114b6ecaaec6fcadc478bc7f7994c78bea`.
It has no completed check rows, count record, profiler record or generated
payload; frame/point/node counters are zero. Its receipt is 0.484375 CPU /
0.48400000005494803 wall seconds, so this refusal did not reach a time cap.

Both modes have exactly the same seven before/after source bindings, actual
import pins and source snapshots. All released source/note files also match
their Git blobs at source/command release
`25a223f639b642b56b2d0c716ebe0abc54dca0aa`, committed at
2026-09-07 10:14:16 −07:00 before the off start at 17:14:29.020108 UTC.
The two actual interpreter suffixes match the first two released commands;
the count command substitutes exactly the completed off result hash. Root
reported collecting OS exit 0 for off and exit 1 for count. Those exit codes
are attributed to root's launch sessions, not independently observed by this
reader. The saved terminal JSON, logs and absence of later mode directories
agree with the stopped schedule.

## Reproduction and next disposition

The bounded independent read/constructor diagnosis ran as:

```powershell
python -B -X faulthandler -X pycache_prefix=experiments/m194g-larger-pupil/work/cache-independent-profile-1-read experiments/m194g-larger-pupil/independent-profile-1-read.py
```

It exited 0. The reader SHA256 is
`16274c2e0cec491a07b3f0a34468104f8f18da5ec1fa1da20f67ab943d6386aa`;
`independent-profile-1-read.json` is
`4e6deb120f27d7b3cc80c40c03aa21878bb50ef8205ae022b5a18fc3f0538cfc`.
It preserves all false/true predicate results, tuple paths, complete off
population checks and source identities. The frozen implementation and both
actual mode results remain unchanged.

I support stopping this diagnostic as registered and choosing the prospective
counter-only 180 CPU / 240 wall second allowance. That choice spends a finite
additional engineering budget; it is not justified by a successful profile,
an optimization result or a completion-time prediction. Repairing and
recommissioning the instrument is possible, but it would require another
explicit release and would not itself advance the uncompleted intended cost
population. Preserve both this harness refusal and the original 60-second
cost refusal. A future complete cost pass still supplies no numerical,
physical-optics, noise, CFA, production-quality or SOTA authority.

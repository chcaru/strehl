# M194g intended cost run 1 — independent terminal review

2026-09-07. **VERIFIED refusal:** `preflight-1/result.json` is
`UNCOMMISSIONED_COST`, with no complete intended population or numerical
admission. Its SHA256 is
`f23b5b1d24ba3e9516b246dce452c336749a3824c373484018a63c68ba66d010`.
The recorded CPU time exceeded the prospectively fixed 60-second ceiling.
No subset is accepted by this review.

## Population and reason

The registered population is 15 frame/arm combinations and 1,152,000 cells:
320×240 cells, five original indices, and primary/angle-refined/cell-refined
arms in that order. The native-pixel gauge is reference index 2 with identity
placements; this does not measure an alignment fit.

The result contains ten complete rows: all five primary and all five
angle-refined frames. Cell-refined frame 0 is partial, with 53,287 completed
cells; the other four cell-refined frames were not started. The full result
therefore contains **821,287 completed cells**, not 1,152,000, and
`completed_frames=10` despite the budget having begun eleven frames.

The failing coordinate is `(167,166)` in cell-refined frame 0. Its branch was
recorded before numerical work finished, so that partial row legitimately
contains 53,288 branch records versus 53,287 completed cells. The traceback
ends at the final `Budget.check()` within `point_cuts`; the last rule's point
charge can precede its angular-node charges and stream emission. The artifact
retains an `ordered_partial_stream_sha256`, not a completed stream digest.
These distinctions explain the partial counts without treating attempted
work as completed coverage.

| Quantity | Terminal record | Active contract and interpretation |
| --- | --- | --- |
| Whole-run CPU | 60.015625 s | Exceeds 60 s; deciding refusal. |
| Whole-run wall | 60.828000000095926 s | Below 120 s; not the deciding ceiling. |
| Current-frame points | 1,780,160 | Below the strict 8,000,000 ceiling at refusal. |
| Current-frame nominal angular nodes | 514,394,112 | Below the strict 1,200,000,000 ceiling at refusal. |
| Total points across the partial run | 5,696,960 | Sum across rows, not a per-frame quantity. |
| Total nominal angular nodes | 2,091,280,512 | Sum across rows; the angular ceiling is per frame. |
| Tracked peak ndarray backing bytes | 91,280 | Below 33,554,432; excludes RSS, Python objects and frozen-helper transient allocations. |

The consumed rule records retain M194e's original integrator limit fields;
the active preflight limits are the separate exact `work.limits`, which match
`fixture.preflight_limits`. Those older integrator fields are not the time or
work limits being enforced here. The count is nominal geometric work, with no
angular radiance integrals evaluated. A CPU refusal of this instrumented
counter neither proves the later radiance program impossible nor supplies a
runtime estimate for it. The completed primary/angle rows cannot replace the
unmeasured cell-refined population.

## Independent read and bindings

`independent-cost-1-read.py` imports neither the counter nor the optical model.
It reads the terminal artifacts, verifies counts and bindings, and independently
uses exact dyadic row-boundary searches to classify the observed prefixes.
This is a different traversal strategy from the counter: binary searches at
each row boundary, with no rule/cut enumeration. It matches the branch totals
of all ten complete rows and the classified partial prefix. It independently
checks row sums, point/node totals, frame order, the partial-coordinate count,
and the actual deciding CPU ceiling. It does not regenerate the intended cost
run or claim an independent whole-stream digest.

All 14 released files match current bytes, recorded bindings and actual saved
source snapshots. The twelve local `sources_before` entries equal
`sources_after`; the two frozen M194e imports match their recorded pins and
current/snapshot bytes. The actual local loader and selector import bindings
also match. The three externally bound control records remain valid at their
own distinct schemas/counts: 41 author, 373 independent geometry, and 94
independent preflight checks. Their bytes and the 14 released files also match
the Git blobs at the release revision. This is source/record consistency, not
an assertion that a generic forged artifact is authenticated by its own hash.

The progress snapshot precedes refusal: CPU 59.953125 s and wall
60.78100000007544 s, with fewer completed cells. The run directory contains
only the expected source snapshots, progress and terminal result. Its launch
log reports the same `UNCOMMISSIONED_COST` status. The terminal JSON and log
do not themselves record the operating-system exit code; that remains the
root launch session's evidence. The root subsequently reported collecting
original exec session `83512`: terminal `exit_code=1`, stdout status
`UNCOMMISSIONED_COST`, and `PREFLIGHT_EXIT=1`. This is explicitly attributed
launch-session evidence supplied by the root, not an operating-system exit
independently observed by this reviewer. No intervention or second full run
was performed by this reviewer.

## Command and chronology

The source checkpoint is `dbf997d9f0dea914939e910e044ce966b066e1b9`
(2026-09-07 09:46:47 −07:00). Cost release
`0e125df2eb0319982a0cbf97c9f85608d68ab01e` was committed at
09:51:05 −07:00, before the run's recorded start at
16:51:21.596748 UTC. It ended at 16:52:21.989309 UTC. The exact release
document bytes match that Git revision; its SHA256 is
`e336c1d9829c201b690f7c2e14dc4f8bed487a314b99728b09e99941292b0eff`.

The actual interpreter suffix matches the released command exactly:

```powershell
python -X utf8 -X pycache_prefix=experiments/m194g-larger-pupil/work/cache-preflight-1 experiments/m194g-larger-pupil/preflight.py --output experiments/m194g-larger-pupil/preflight-1
```

`sys.orig_argv` resolves `python` to the recorded Python 3.12.10 executable;
the module records NumPy 2.4.4 and four numeric-library thread settings of 2.
The cache path is the released fresh path. The local and frozen model modules
are executed from the bytes their loaders checked. These Python source/cache
records are not Cargo rebuild evidence.

The independent reading command was:

```powershell
python -B -X faulthandler -X pycache_prefix=experiments/m194g-larger-pupil/work/cache-independent-cost-1-read-2 experiments/m194g-larger-pupil/independent-cost-1-read.py
```

It exited 0 and wrote `independent-cost-1-read.json`, SHA256
`70991f9ba06cbaf165acc155898df0ed04bf67af7323984d3655d3564890ccb2`.
The reader source hash is
`da31e6fba6d5aa1eb1d5becd83f7e2e903d1918b294742e4e3fd41138ca91ff7`.
Its first attempt exited 1 because the reviewer incorrectly assumed all three
control schemas used a boolean `passed` summary: the author stores an integer
count and the geometry controls use a status string. The original source and
log are retained in `independent-cost-1-reader-history`; the corrected reader
explicitly validates each actual schema and every check row. No cost artifact,
source implementation, acceptance limit or numerical threshold changed.

The next decision requires a prospective response to this observed cost
refusal. It cannot be discharged by extrapolating the ten completed rows,
calling the partial count a full preflight, or admitting float-model work
under this release.

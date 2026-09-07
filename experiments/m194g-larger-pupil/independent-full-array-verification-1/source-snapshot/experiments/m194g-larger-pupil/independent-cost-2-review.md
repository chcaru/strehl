# M194g amended intended cost run 2 — independent terminal review

2026-09-07. **VERIFIED: PASS_COST_ONLY.** The actual amended run completes
all fifteen expected frame/arm rows and all 1,152,000 native cells within its
prospectively declared elapsed and per-frame work ceilings. This discharges
the geometry-cost prerequisite only. It does not commission radiance
components, expected-electron arrays, physical optics, noise, CFA, production
quality or SOTA status.

The terminal result SHA256 is
`c9e9154fd395a06a5d1cbb28123ac84f92ee1ac61b1a97216f8904b8b6261677`.
It remains distinct from the original `UNCOMMISSIONED_COST` result and the
stopped private profile diagnostic; neither is retroactively promoted.

## Complete population and active limits

The actual rows contain indices 0 through 4 for primary, angle-refined and
cell-refined arms, in exactly that order. Each row has 76,800 completed cells,
exact integer counts, a complete status and final native coordinate `[319,239]`.
All branch totals agree with the separately derived exact dyadic row-boundary
oracle. The input gauge remains reference-2 native pixels with identity
placements. No fitted alignment or independent capture was introduced.

| Quantity | Actual terminal value | Active requirement |
| --- | --- | --- |
| Complete rows | 15 | 15 |
| Complete cells | 1,152,000 | 1,152,000 |
| Whole-run CPU | 113.9375 s | At most 180 s |
| Whole-run wall | 115.68799999996554 s | At most 240 s |
| Maximum points in one frame | 2,565,120 | Strictly below 8,000,000 |
| Maximum nominal angular nodes in one frame | 741,288,960 | Strictly below 1,200,000,000 |
| Tracked peak ndarray backing bytes | 91,280 | At most 33,554,432; restricted scope |

Both work maxima occur in cell-refined frame 0. Every row is checked against
the per-frame ceilings; the run totals of 11,750,400 points and 3,698,302,464
nominal angular nodes are sums across frames, not values to compare with a
single-frame ceiling. The work counts are actual nominal geometry counts;
no angular radiance integrals were evaluated. Tracked storage excludes Python
objects, RSS and frozen-helper transient allocations.

The newly complete cell-refined rows are:

| Original frame | Low+high points | Actual nominal angular nodes | Maximum intervals |
| --- | --- | --- | --- |
| 0 | 2,565,120 | 741,288,960 | 50 |
| 1 | 2,104,320 | 601,070,976 | 48 |
| 2 | 1,643,520 | 457,909,632 | 48 |
| 3 | 1,167,360 | 304,189,056 | 46 |
| 4 | 353,280 | 16,957,440 | 1 |

These angular counts were read from the complete actual traversal; they were
not inferred by multiplying primary rows. All ten formerly completed primary/
angle rows match the original run's row records exactly. That is an
implementation consistency check, not a second optical truth measurement.
The independent reader also checks low/high counts against each actual root
count and registered order, a work-accounting identity rather than an
independent integral test.

The result has no error, partial status or partial-stream digest. Its complete
ordered stream digest is
`74827222370a9d733c520adbe0515b71a3ca545e31e2d7e1c9457cf9de547e70`.
This reviewer verified its binding and the complete population but did not
replay the whole point stream to produce another digest. Coverage confidence
also rests on the independently commissioned omission/duplicate controls and
unchanged counter implementation, not on the presence of a digest alone.

## Source, release and command

The exact new release is `cost-release-2.json`, SHA256
`7214addd5905a0f238a51554b7bd7add67ba6aa8c2b1c5abb8135159117aabbf`,
committed at `44d2670dc30de10e2f4d2b8ca277c5278732c1eb` before launch.
Its twenty-one-file set exactly matches the nineteen local before/after source
entries plus two frozen M194e imports. Every recorded file matches current
bytes, its saved snapshot and its Git blob at that release. The amendment,
fixture and actual loader/selector imports have their exact released bindings.
The twenty-one snapshot basenames are unique and the directory has exactly
that set. The new reader was created after the run ended and is not pretended
to have been part of its source closure.

The new 53-check affected-control artifact and the historical 41/373/94 records
match their released bytes and schemas. All actual check rows pass. The latter
three were not rerun; unchanged-path reuse is supported by the affected
control's exact source-body/allowlist comparison. The active fixture/work
elapsed policy is 180/240, not the old helper-integrator fields stored inside
each row. All optical fields and later numerical/error limits remain separate.

Release commit time was 2026-09-07 10:32:14 −07:00. The run's recorded start is
17:32:35.001326 UTC and end is 17:34:30.242347 UTC. The actual interpreter
suffix matches the released command:

```powershell
python -X utf8 -X pycache_prefix=experiments/m194g-larger-pupil/work/cache-preflight-2 experiments/m194g-larger-pupil/preflight.py --output experiments/m194g-larger-pupil/preflight-2
```

The run records Python 3.12.10, NumPy 2.4.4 and four numeric-library thread
settings of 2. Its early clock starts before the recorded start timestamp;
terminal JSON serialization follows the final success check. The receipt is
a cooperative elapsed measurement, not an OS hard deadline or process-exit
time, and timestamp subtraction does not reconstruct it. Root reported
collecting original exec session `9359` with exit 0 and `PASS_COST_ONLY`.
That OS exit is explicitly attributed to root, not independently observed by
this reader. The saved launch log agrees with the terminal status.

## Independent reproduction and disposition

The preregistered read reused only `first_true` and `branch_prefix` from the
unchanged earlier independent reader, extracted from its pinned source. It
did not import the counter, selector or numerical integrator and did not run
the intended population again. Its exact row-boundary searches independently
check every branch row; all other full-stream work values remain read-and-bound
observations under the already commissioned counter contract.

```powershell
python -B -X faulthandler -X pycache_prefix=experiments/m194g-larger-pupil/work/cache-independent-cost-2-read experiments/m194g-larger-pupil/independent-cost-2-read.py
```

This bounded read exited 0 on its first invocation.
`independent-cost-2-read.json` SHA256 is
`a29b4fb9d95e668ebda8da14d97afc9e5a24875e58bb9858f017db95ca006715`.
It retains all fifteen reviewed rows, per-frame maxima, source/control/Git
checks and the scoped admission. The next step is the separately reviewed
numerical component/source/oracle release. This cost pass does not grant
permission to skip those prerequisites or assert image quality.

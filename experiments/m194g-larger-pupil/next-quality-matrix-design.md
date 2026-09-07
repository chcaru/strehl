# Fixed production matrix and its actual file index

Root,2026-09-07. Prospective controller/interface design, with no production
command or quality calculation yet. This concretizes the38-output population
in `next-quality-design.md`. It changes no admission rule, candidate parameter,
noise seed, target, mask or engineering review trigger. The larger bridge,
its private tests, final noise-file admission and independent TIFF/instrument
commission must pass before this matrix is released.

## Exact ordered population

Use scene order flat, textured. Within each scene use noise-off first, then
the fixed seeds701,709,719,727,733,739,743,751. Each state uses both admissions
`hard-floor` and `floor-pedestal-v1` on exactly the same five original CFA
frames. Alternate their run order by state ordinal: even starts with HardFloor,
odd with FloorPedestalV1. Both are still independently labeled; order is not
an acceptance variable or timing experiment. This gives36 main outputs.
Append textured/noise-off/HardFloor original frame0 and original frame4 alone,
in that order, giving exactly38. No missing command is replaced, retried into
the same output directory or silently removed from the index.

Main subset is `all-five`, with original indices[0,1,2,3,4] and local reference2.
Endpoint subsets are `endpoint-0` and `endpoint-4`, each with its one original
index and local reference/probe seed0, in the common identity reference2
coordinate gauge. The controller translates these semantic fields to the
bridge's exact released environment values; the independent plan reader
checks the bridge's actual selections. Keep observer off, confidence off and
the existing pinned production options. Actual source/plan environment includes
explicit removal of floor-scale/white-floor/debug overrides, not merely a
claim that no override was requested. Each output runs in a fresh child test
process because some environment settings are cached by the product.

## Closed matrix index

Use `m194g-production-matrix-v1`. The exact top-level keys are
`schema,status,ref_root,noise_admission,bridge_commission,instrument_commission,
execution_release,invocation,sources_before,sources_after,inputs_before,
inputs_after,entries,work,error,finalization_errors`.
`ref_root` is `repository`. Successful status is
`COMPLETE_38_RGB_OUTPUTS_UNSCORED`; all incomplete/failing paths use
`UNCOMMISSIONED_PRODUCTION_MATRIX`. Success requires null error, an empty
finalization-errors list and identical source/input before/after bindings.
Every FileRef is exactly `{path,sha256,bytes}`, with canonical contained
repository-relative POSIX path, lowercase SHA256 and positive integer length.
The source/input maps are repository path to `{sha256,bytes}`. The controller
must not issue a quality verdict.

`entries` is the exact ordered38-row population above. Each row has exactly
`ordinal,scene,noise_enabled,seed,admission,subset,original_indices,plan,
plan_launch,receipt,tiff,log,launch`. Ordinal is0..37; other population fields have the literal
types/values above. The last six fields are FileRefs. Index rows retain actual
file identities: two entries cannot alias the same TIFF, plan, receipt, log
or launch record even if their bytes happen to match.

The controller pre-registers38 pixel-free plan commands and38 render commands,
with fresh paths, before its first child starts. It executes all plans and
checks the common geometry before beginning renders. Each render consumes its
actual plan hash; `plan_launch` records that separate actual child.
It binds the genuine noise-file gate, independently commissioned
bridge and instrument results, exact executable and original argv/environment.
Each `launch` is the actual controller record, schema
`m194g-production-launch-v1`, with keys
`schema,status,ordinal,phase,command,environment,executable,started_utc,ended_utc,
wall_seconds,exit_code,log,error`. Its successful status is
`COMPLETE_CHILD_EXIT_ZERO`; failure is `FAILED_CHILD`. The executable and log
are FileRefs. `environment` is the actual relevant environment map, including
explicit nulls for removed overrides. `command` is the exact child argv list;
UTC timestamps, monotonic wall time and exit code are observations. Successful
launches have integer exit_code0 and null error. `phase` is exactly `plan` or
`render`. Failure retains the original
error and whatever log/result exists. Only the parent's observed process
completion can supply this record; child-written pass strings cannot.

## Consumption, limits and powered controls

One child runs at a time. Give each production child a prospectively fixed
240-second wall allowance, its stdout/stderr combined in a bounded16MiB log.
An over-limit process/log is a failed output, not a partial success. The
controller preserves its prior complete rows and failed launch, then stops
the matrix. These are operational limits, not speed or process-memory bars.
Log capture must enforce its limit while consuming bytes; checking file size
only after an unbounded pipe drain is insufficient. No extra production
invocation is performed to repair an index. Controller metadata/output
bookkeeping is bounded to64MiB, separate from the intended38 TIFFs, which
are each admitted by the independent1MiB decoder bound.

The independent scorer reopens the actual executable/source/command/input
chain, all38 plans/receipts and both launches/logs, and all38 actual RGB TIFFs.
Require exactly one successful measured-floor banner/count pair per render
log; pixel-free plan logs have no such requirement. The prefix is finite, nonempty
prefix at most2 and contribution count5 for main or1 for endpoint. The
four-decimal floor values remain descriptive. Level sizes, actual crop,
native coordinates, reference/probe indices, mode and source tuple come from
the actual plan; the controller's label does not override them. Verify all
plan/TIFF coordinate associations before testing the fixed support guards.
The separate quality result supplies the per-channel numerical findings.

Private controller tests must prove exact population38, stable source/command
preflight, real child exit-zero versus nonzero handling, output-path freshness,
actual log limit and timeout refusal, and preservation of earlier failures.
Use small local child fixtures, never fake successful production authority.
The independent index/plan reader must reject rehashed omissions, duplicates,
wrong typed seed/mode/subset/probe index, wrong actual file associations,
missing/duplicated/nonfinite floor banners and changed contribution count.
Valid/restored companions are required. A one-code changed TIFF under its
updated file hash is tested against the actual pixel oracle, not credited as
an integrity refusal. Unchanged inputs are rehashed after final persistence;
a late failure revokes successful matrix or quality admission.

The exact bridge/instrument authority schemas, concrete executable command
and final source pins are filled by their own released implementations.
Until those records exist this is an interface proposal, not execution
authorization or a claimed38-output result.

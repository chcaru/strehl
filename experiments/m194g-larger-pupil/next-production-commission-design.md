# Twelve actual bridge outputs before final bridge admission

Prospective source/controller specification, 2026-09-07. Root accepted this
literal order before execution. `production-commission.py` uses the held
`production-command.py` actual parent launch path. It performs no noise draw,
optical calculation, quality calculation or alternative merge.

The exact rows are:

| Ordinal | Scene | Seed | Admission | Subset | Observer |
| --- | --- | --- | --- | --- | --- |
| 0 | flat | noise-off | hard-floor | all-five | off |
| 1 | flat | noise-off | floor-pedestal-v1 | all-five | off |
| 2 | flat | 701 | hard-floor | all-five | off |
| 3 | flat | 701 | floor-pedestal-v1 | all-five | off |
| 4 | textured | noise-off | hard-floor | all-five | off |
| 5 | textured | noise-off | floor-pedestal-v1 | all-five | off |
| 6 | textured | 701 | hard-floor | all-five | off |
| 7 | textured | 701 | floor-pedestal-v1 | all-five | off |
| 8 | textured | 701 | hard-floor | all-five | count |
| 9 | textured | 701 | hard-floor | all-five | placebo |
| 10 | textured | noise-off | hard-floor | endpoint-0 | off |
| 11 | textured | noise-off | hard-floor | endpoint-4 | off |

Each has a fresh pixel-free plan process. All12 saved plans must exist and
agree on output geometry before any render. Each render is a fresh process
consuming the same case's full saved plan and hash. Plans, receipts, TIFFs,
logs and launch records are distinct actual files. Failed observations and
earlier complete rows remain visible; there is no retry or subset admission.
The exact child command and environment for all24 children are persisted
before the first starts, with only the not-yet-produced same-case plan SHA
represented by `ACTUAL_SAME_CASE_PLAN_SHA256`.

The build and actual90-file noise admission are externally pinned required
arguments and released inputs. Root additionally includes the independently
passed private bridge read as an exact released input before authorizing these
12 outputs. The final bridge commission does not yet exist and is not an
input. Its later independent read will bind this completed population along
with the actual6 ordinary tests and6 private RGBs. No circular authority is
created by this preparatory controller.

The release scope is `production-commission-matrix`. Required source closure
includes this design, `next-production-controller-design.md`, the command
module, this controller and the build helper. Invocation requires the exact
root-released original argv, fresh cache/output paths and build/noise external
hashes. The exact CLI is the matrix CLI without bridge/instrument arguments:
`--release`, `--release-sha256`, `--build`, `--build-sha256`,
`--noise-admission`, `--noise-admission-sha256`, `--output`.

The closed index uses `m194g-production-commission-matrix-v1`, status
`COMPLETE_12_RGB_OUTPUTS_UNSCORED` or
`UNCOMMISSIONED_PRODUCTION_COMMISSION_MATRIX`. Exact top-level keys are
schema/status/ref_root/build/noise_admission/execution_release/invocation/
sources_before/sources_after/inputs_before/inputs_after/entries/work/error/
finalization_errors. `ref_root` is repository. Each entry has exactly
ordinal/scene/noise_enabled/seed/admission/subset/original_indices/observer/
plan/plan_launch/receipt/tiff/log/launch. The last six are repository FileRefs.
Seed is null for noise-off and integer701 otherwise. Original indices are
[0,1,2,3,4] for all-five, [0] or [4] for the two endpoints. Observer is part
of this population identity, unlike the later38 matrix where it stays off.

The shared launch path retains the parent-observed actual executable, argv,
environment, child exit, timestamps and bounded combined log. Limits remain
240 wall seconds per child,16MiB per log,64MiB controller metadata/logs;
TIFF payloads are separately bounded by the independent reader. Each render
requires one finite measured-floor prefix/count pair,5 main or1 endpoint;
the descriptive four-decimal floor values are not precision calibration.
Count/placebo logs and receipts remain actual inputs to the independent
observer read. The parent additionally binds receipt output path/hash/bytes
to its actual TIFF and retains an actual zero-exit launch if subsequent
association checks refuse. It never substitutes output summaries for the
independent TIFF oracle or issues a bridge/quality gate.

Source/input/output checks extend through result persistence. A late failure
retains the prior result as rejected and attempts a downgraded record while
preserving the original exception. No positive result can survive a known
finalization failure. This operational controller does not claim hermetic
execution, runtime speed or process-RSS measurement.

# Independent fixed38 production-controller review

2026-09-07. Final source-only review of `production-matrix.py` SHA256
`6f57fb166bb2d18189157cdcac3e00d17c493cfd1a4954393d78578ca06f32f2`
against `next-quality-matrix-design.md`
`2d48d991898b8a5e478830b95652a4e671cbb84fc9834ba442fd812ad2f362fd`.
No numerical helper, controller, child, render, image decoder or metric ran in
this review. Held launcher, bridge and earlier reviews were not edited.

## Population and the consuming command boundary

I checked the scene-transition choice explicitly: state ordinal is global,
not reset for each scene. Flat's nine states occupy0..8; textured noise-off
is state9 and therefore starts FloorPedestalV1 at output ordinal18. The seed
order is noise-off,701,709,719,727,733,739,743,751. Two admissions per state
produce36 main outputs, followed by textured/noise-off/HardFloor original0
and original4 at ordinals36/37. Main outputs use all five original frames;
all observers are off. This is the registered order, not a timing study or
an optimization inferred from results.

Before any child, the controller persists all76 intended argv/environment
records with fresh paths. The only dynamic field is the same case's actual
plan SHA. All38 plan processes must complete, their actual saved plans must
match scene/seed/subset/admission/executable and original/local/probe indices,
and their output geometry must agree before the render loop is reached.
Each actual launch's argv and relevant environment are compared with its
predeclaration; observeroff is therefore checked even though the shared
invoke call uses its default. Each render receives the exact saved plan ref.
The held Rust consumer rechecks the whole plan; later independent consumption
still checks complete plan/pixel semantics rather than trusting row labels.

The endpoint local reference and probe seed remain0 in the common reference2
coordinate gauge. Their original indices remain0 and4. The controller checks
these different meanings rather than treating the original index as the
local/probe index. Printed measured-floor prefixes have a separate finite,
nonempty, at-most-two-values/count5-or1 predicate. Four-decimal terminal
values remain descriptive; this is not exact beta reconstruction.

## Gates, source and publication

The command dependency is read through a bound byte buffer and compiled only
after matching the external execution release's source digest. The full
controller then checks the strict release and actual original argv. Its four
explicit build/noise/bridge/instrument arguments must match both their external
hashes and exact released FileRefs; supplemental released inputs are retained
by `source_check` through publication.

I compared the final bridge-gate keys consumed by `gates()` with root's actual
`independent-production-bridge-read.py` writer: they agree, including the six
build/private-tests/private-outputs/intended-outputs/independent-read/release
refs, stable source/input maps and null/empty failure fields. It requires
the same build as the new production run and reopens all six child refs plus
the recorded current source/input files. The noise gate is separately bound
with all five referenced children. This consumes externally pinned completed
authority; it does not rerun or self-certify its independent reader.

The instrument gate requires the exact69-check result schema,69 unique IDs,
genuine passing booleans, null/empty failure fields and matching source maps.
A read-only check of the actual `independent-quality-instruments-1/result.json`
source map found all five declared Python files equal to their current hashes.
That source observation is not a recomputation of its numerical controls.
The69 instrument result does not independently admit the59 association
controls, the K0 target or quality scoring. Those remain separately bound
consumer requirements; the bridge gate is produced by root's independent12
read that integrates the association controls. No combined generic
instrument authority is invented by this controller.

Unlike the earlier standalone-launcher finalization gap, the matrix's
`recheck()` already calls `source_check()`, actual `Build.finish()` and all
three gates. The same function is used around every child and before/after
final publication. The copied/original executable and compiled include-set
therefore remain checked through the matrix index write. The shared metadata
ledger checks all adopted plan, receipt, TIFF and log hashes again at that
boundary. Source/input snapshots in the result must agree. A known late
failure downgrades the result and preserves the original failure through the
shared publication path.

## Failed and successful row bookkeeping

The actual launch reference is assigned to `work.failed_launch` immediately
after a child returns. It remains there while exit, postprocessing, declared
command/environment, plan/geometry, floor-log and file-identity checks run,
and is cleared only after the complete row is appended. Earlier completed
plans and render rows remain in the failed index. Missing artifacts after
child exit0 retain that actual zero-exit launch and a separate parent error;
no nonexistent nonzero child exit is fabricated.

Distinct actual nonzero filesystem identities are required across the six
refs of every output, including cross-row identity. Byte-identical results
may use distinct files; aliases cannot inflate the output population. No
retry, missing-row substitution or successful-subset completion exists.
Operational limits remain one child at a time,240 seconds per child,
16MiB combined log and64MiB metadata/log bookkeeping. Separate TIFF decoding
and its1MiB bound remain independent consumer obligations.

## Disposition

No blocking defect was found in this final38 controller. It is ready for
root's exact source/command release once the genuine bridge and other named
prerequisites are available and pinned. This verdict neither claims that76
processes or38 renders have run nor admits bridge pixels, software/physical
noise quality, a target, candidate quality or SOTA. Successful controller
status remains `COMPLETE_38_RGB_OUTPUTS_UNSCORED`.

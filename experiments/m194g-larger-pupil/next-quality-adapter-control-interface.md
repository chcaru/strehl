# Integrated actual12 adapter instrument child

Source-only interface. Root's intended12 independent reader owns the actual
external input/release CLI, authority/build loader, stage Budget and final
artifact persistence. No separate authority engine or child process is added.

Import the frozen `independent-quality-adapter-controls.py` only after source
and command admission. Call `child=initial_result()` and attach it to the parent
result before `run_controls(subjects,context,io=...,reads=...,adapter=...,
metrics=...,readout=...,budget=...,result=child)`. All arguments use the parent's
already running shared Budget and already admitted actual source modules.
The function catches failures, retains attempted controls and returns the same
child object. The parent must require its successful status before the twelve
actual TIFF decodes and final bridge-read admission.

Subjects is exactly twelve `{row,observer}` records. Each row has the existing
per-output semantic fields and six actual FileRefs expected by `read_entry`.
Population is both scenes ×noise-off/701 ×both modes under observer off,
plus textured/701/HardFloor count and placebo, plus the two textured/noise-off
HardFloor endpoints. Context has actual executable FileRef, noise_admission
FileRef, actual admitted authority object, manifest bundles, manifest_root,
and optional common_geometry. It comes from the real root-owned authority
reader. No fixture context substitutes for these twelve genuine companions.

The exact child keys are schema/status/checks/genuine_subjects/
private_load_counts/work_before/work_after/error/scope. Schema is
`m194g-quality-adapter-controls-v1`; successful status is
`PASS_QUALITY_MATRIX_ADAPTER_INSTRUMENTS`; failures use
`UNCOMMISSIONED_QUALITY_ADAPTER`. Success requires59 actual passing checks,
null error,12 genuine_subject records, private load rows
`{case:half-noise,calls:34}`, `{case:bias,calls:34}`,
`{case:spike,calls:34}`, and finite valid same-stage before/after Budget receipts.
No actual TIFF decode occurs inside this child; twelve actual TIFF files are
hashed and associated through read_entry before the parent decodes them.
The102 private callbacks return deterministic float arrays, not optical/noise
renders or actual TIFF files, and do not increment the TIFF decode counter.

Checks each have exactly id/passed/details; IDs are unique, passed is a genuine
boolean and details finite JSON. Groups are13 actual population/entry checks,
19 plan/endpoint/restored checks,7 consuming floor-log checks,11 private38
pure-schema/restored checks and9 complete18-row private-reducer checks. Failed
checks remain in place; an exception before a check records error and the
already attempted rows, never a false full-population PASS.

Pure private38 objects deliberately validate only that schema boundary and
are labeled fixture-only in their check details; they carry no genuine source
or product-command authority. Coherently negative floor injection preserves
the actual printed prefix length, so its refusal exercises the nonnegative
value check. The complete flat reducer uses exactly represented post-WB ideal
levels with fixed offsets; its24/6 variances,21/5.25 MSEs,81 biased MSE and
last-seed green67.5DN spike error are independently declared numerical oracles.
The single green spike is at native(23,19), outside the guarded window, and
the actual full-output sparse record must identify it.

The parent persists the actual child as a FileRef. The final two-child
instrument gate can bind this result alongside the previously completed69
math/TIFF result. No quality score, target admission or38 production launch
follows from the child alone. Root source review and exact command commit
remain required before any helper call.

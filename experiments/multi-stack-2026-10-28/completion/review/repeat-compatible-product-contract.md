# Repeat-compatible source evidence: minimal product integration

**ARGUED proposal after current source review,2026-10-28. No source edits or new engine runs.** A fixed-focus repeat is not a failed attempt to estimate a through-focus peak. It needs an independently commissioned local compatibility basis. The basis names below describe why a particular source cohort is admitted; they are not a probability, physical depth or proof of sharpness. A scene can contain both kinds of evidence, so an exclusive map describes the basis actually used by a consumer rather than claiming the other evidence is absent.

## Existing seams that must not be overloaded

- `strehl-core/src/focus-evidence.rs:199` retains ordinal, local three-sample shape width, modes, flags and usable sweep-peak support. `usable` currently means covered with zero sweep flags. Keep those semantics and existing ordinary behavior unchanged. Do not create a finite width, ordinal or zero flags for a plateau.
- `strehl-cli/src/session-reconstruction-plan.rs:10` currently schedules only `FocusSummary` with ordinal/width and evaluates `focus_mode_response`. Introduce a separate validated cohort admission path here; setting width to infinity, forcing qualified=true or assigning response1 from metadata would bypass the actual missing prerequisite.
- `strehl-cli/src/session-focus.rs:386,528` exports `strehl.session-focus.v1` with acquisition-ordinal and shape-width semantics. Preserve it as sweep evidence. An additive `evidence_kind: sweep_peak` is safe; a repeat receipt belongs in a separate artifact.
- `strehl-cli/src/session-reconstruction-consumer.rs:19` currently combines source/focus/motion refusal and has `No qualified focus`. Preserve numeric fallback codes for old runs, but new producer receipts should distinguish no sweep peak, repeat compatibility unmeasured, repeat compatibility contradicted, unsupported geometry and absent original support. Geometry-only brow opportunity must remain unadmitted.
- `strehl-ui/src/session-diagnostics-data.rs:270` loads focus maps and currently labels every file as acquisition ordinal/response shape. New repeat maps cannot be routed through that scope string. `session-diagnostics-reconstruction.rs:105` deliberately accepts exactly two v1 reconstruction maps; adding a third file there requires an explicit schema/parser update, not silent permissive parsing.
- `session-reproducibility.rs:585` and UI `session-diagnostics-data.rs:438` assign qualification1 specifically to two unambiguous interior peaks. Do not reuse that code for a repeat plateau. The existing descriptive curves may remain unverified until a new explicit repeat qualification is implemented and checked.

## Proposed additive evidence artifact

Use a sibling `source-evidence/geometry.json` and small bound scalar maps. This can serve repeat fusion and reconstruction without making all repeat evidence an SR feature. The root render report binds its geometry SHA; geometry binds source/session/alignment/algorithm/policy receipts and local files. Original source memberships live in bounded or streamed cohort records, not an aligned frame volume. A minimal illustrative record is:

```json
{
  "schema": "strehl.source-evidence.v1",
  "full_quad_geometry": [3516, 2344],
  "origin_sensor": [14.5, 10.5],
  "sample_location": "green-quad center",
  "dimensions": [3502, 2334],
  "step_sensor": [2, 2],
  "basis_codes": {"0": "Unknown", "1": "SweepPeak", "2": "RepeatCompatible"},
  "basis_semantics": "Admission basis used for this local source cohort; not sharpness or depth",
  "files": [
    {"path": "basis.tiff", "bytes": 0, "sha256": "ACTUAL_SHA256"},
    {"path": "reason.tiff", "bytes": 0, "sha256": "ACTUAL_SHA256"},
    {"path": "cohort-id.tiff", "bytes": 0, "sha256": "ACTUAL_SHA256"}
  ],
  "cohorts": [{
    "id": 1,
    "basis": "RepeatCompatible",
    "source_ids": ["ORIGINAL_CONTENT_ID_A", "ORIGINAL_CONTENT_ID_B"],
    "compatibility_receipt_sha256": "ACTUAL_SHA256",
    "geometry_receipt_sha256": "ACTUAL_SHA256",
    "measurement_scope": "Local color/PSF agreement under frozen sampling and tolerances",
    "peak_ordinal": null,
    "width_frames": null
  }]
}
```

All numeric geometry and file receipts above are illustrative; real values must be produced from the exact map domain. With half-resolution quad-center fields, the physical sample origin must include the existing0.5sensor center convention where appropriate; it must not blindly reuse an integer photograph corner. Use one explicitly documented convention and an odd-origin overlay test. Cohort IDs are categorical exact integers; zero means no admitted cohort. A reason map distinguishes missing coverage, unmeasured/low-power evidence and observed contradiction. Unknown must not hide a measured failure. If retaining per-source mixed bases is necessary, bind the explicit per-source basis in the cohort receipt rather than silently collapsing them.

A report summary should count SweepPeak/RepeatCompatible/Unknown used pixels and retained-native reasons, while maintaining exact final reconstruction support separately. An admitted repeat cohort still has to pass consuming RGB registration, phase conditioning, clipping/coverage, motion and estimator variance/overshoot controls. Compatibility must bind the exact cohort, original IDs, calibration regions and all guide/search/filter footprints; a connected chain of pairwise similarities is not automatically a transitive common-PSF certificate.

## Small UI change

Add one diagnostic group called **Source evidence** with a categorical legend: **Sweep peak**, **Compatible repeat**, **Not established**. Clicking a map reports the basis, reason, cohort/source count and saved scope. For repeat evidence show: “Local captures passed the recorded compatibility checks. No focus peak, metric depth or sharpness estimate.” Keep the native-fallback and conditional reconstruction counters separate. Existing focus `usable` should be presented as **Usable sweep peak**, not general source usability. Existing ordinal/width maps remain inspectable for sweep evidence; no fake values are shown for repeats.

No user control should force compatibility. The existing optional reconstruction request can invoke a validated alternate producer when available, while the immutable job/receipt states which basis actually ran. Fixed-focus metadata or an explicit capture-type declaration may nominate assessment, never admit sources. Existing saved runs without the new artifact remain legacy sweep-only or unverified; do not infer repeat compatibility from mode=Repeat, a successful render, equal focus metadata or lack of a peak. A future reproducibility code may say “Both outputs use validated local repeat compatibility,” while preserving the existing peak-specific code and its limitations.

## Required integration controls

1. A plateau with matching textured original signals reaches RepeatCompatible only after the actual compatibility and geometry paths pass; a fine-focus/one-color-blur/lighting/motion adversary reaches Unknown with a retained contradiction reason. Flat/low-information input stays unmeasured.
2. Sweep results, ordinary command defaults and saved v1 reports remain bit-identical and correctly labeled. Neither new evidence changes the existing selector reference implicitly.
3. Exact source membership, gauge, geometry/policy hashes and category ranges are checked. Same-length shifted maps, wrong original hashes, unknown codes and malformed cohort IDs refuse map loading without claiming support.
4. Actual UI inspection exercises legend, pixel sampling, native/overview coordinate mapping, selected output changes, save/reopen and immutable imported provenance. A geometry-only diagnostic must display no delivered reconstruction support.

The current bee brow geometry is a concrete opportunity for this path, not proof that repeat compatibility or photographic benefit exists. The full nine-region negative/positive census remains part of its scope; product validation cannot select a new location from candidate appearance.

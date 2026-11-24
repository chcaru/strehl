# Subject, highlights and detail: implementation log

**Status:** the whole plan except tiled capture (deferred) is built and on `main`:
stages Q, S, X, R and D and the owner's bug list (2026-11-23 and 24). The Pi runs X3
(deployed 2026-11-24); the rig gates below were run on the weevil's pronotum. **Plan:**
[subject, highlights and detail](../../../docs/proposals/2026-11-subject-highlights-and-detail-plan.md).
**Ledger rows:** `shd-*` (2026-11-23 and 24) in
[the milestone ledger](../../../docs/agents/milestone-ledger.md).

Labels: MEASURED, VERIFIED, DERIVED, ARGUED, UNVERIFIED, as in `AGENTS.md`.

## The owner's bug list

| Report | What was wrong | Change |
| --- | --- | --- |
| No way to reset the Capture stages; the Library's "From camera" and "New stack of this subject" opened the last capture's state | The review of an ended capture and the plan's stages (test shot, step calibration, names) stayed until the app restarted; nothing cleared them (VERIFIED in the code) | "New capture" on the review and on the plan; the Library's three entries call it. The Pi gains `new_plan` (marks, subject box, survey, outline) |
| "Survey again" before any survey | The label was fixed text | "Survey" until there is a survey |
| "Steps up to 9 keep the detail" with no row for 9 | The line uses width / 5, the table's rows came from fixed candidates and the engine's width / 7 | The width / 5 step is a row |
| Nothing visible while a capture starts | The Pi said only a status message during the light warm-up and the approach | The Pi reports `starting` (stage, seconds); the flight headline shows it and the warm-up's share of the bar |
| Develop and Export previews not at full resolution | Steady HDR and SDR draw native tiles (VERIFIED). A display change (Windows HDR switched, the window moved between the owner's HDR and SDR displays) dropped the photograph to the 1600 px overview until new tiles developed (VERIFIED, reproduced). Split's Before half was the overview. Export's Web preset shows its own 2560 px by design. Also: the desktop did not parse four-shot and restored renders' `wrote` line, so their maps were never certified and a saved one could not be reopened (VERIFIED) | Tiles carried through display changes, float layers painted when HDR is off, Split's Before half tiled, Export's strip says when it shows a smaller file, the parser reads both endings. [Results](../../desktop-studio-2-impl/shd-hdr-zoom.md) |
| Export name not reset | The name field edited the one template every photograph shares | The name belongs to the photograph; the template is the default, with "Back to the default", "Make it the default" and "Restore Strehl's default name" |

The owner's existing default template is whatever was last typed into the field;
"Restore Strehl's default name" brings back `{subject}-{view}-{preset}`.

## Quick fixes

| # | Built | Evidence |
| --- | --- | --- |
| Q1 | A fit at its ceiling takes the nearest stored fit for the same camera, lens and aperture within 16,000 focus units; every measured fit is stored (`optical-cutoffs.json` in the engine cache); the log, the progress stream and the Stack station's checks say which fit was used | The weevil renders restored with no environment variable; the other stacks' bytes unchanged (VERIFIED). The weevil's own fit failure is not explained: neither of the plan's two causes fixes it. [results](results.md) |
| Q2 | The target is never below the system response (floor on the noise-weighted target) | "Restored" equals "system" at 0.3 and 0.4 cycles/px on all four A7CR stacks (MEASURED, [results](results.md)) |
| Q3 | The Pi skips the warm-up the light has already had since it switched it on | Unit-tested; UNVERIFIED on the rig |
| Q4 | Test-shot levels per colour; advice and the clipped share read the most clipped colour, named in the line | Unit-tested on an RGGB frame with green pinned |
| Q5 | The four-shot check judges local disagreement in photosites against 0.3 of the blur width; whole-photosite slips are retaken | Same verdict at 1 s and 1/4 s for the same offset; the stopped 1 s capture keeps 20 of 24 planes four-shot (was 16); planted slips fail; the weevil's bytes unchanged (MEASURED, [planecheck](planecheck/results.md)) |
| Q6 | A capture stopped with two or more complete planes offers "Stack N planes" in its review | UI-tested; UNVERIFIED on the rig |
| Q7 | "Check stillness (20 s)": the largest magnifier over the subject, live frames registered (search, then Lucas-Kanade), sway, axis, frequency and the longest exposure under a quarter-pixel blur | Registration within 0.05 px on synthetic shifts; the close-tile sway reads 1/46 s (DERIVED); UNVERIFIED on the rig |

## The subject

- **S1.** `Plan.subject` on the Pi (rings normalised to the active area, reference
  focus, magnification rate, provenance), set by the `subject` command, written into
  every capture's manifest, cleared by `new_plan`. The box becomes the outline's
  bounding rectangle. A new stack of a catalog subject starts from the outline its
  newest capture was taken with.
- **S2.** `strehl_core::subject` and `strehl subject <run> --json`. IoU 0.992 and 0.994
  against the results note's weevil and scarab masks from 13 planes; an out-of-focus
  plane set gives an empty mask and says so (MEASURED, [mask](mask/results.md)).
- **S3.** Live view's "Outline": place, close, drag, insert, remove points; "Auto" finds
  the outline from the bounds survey's live frames, with Sensitivity, Grow and Buffer
  re-selecting from the kept evidence. Not built: the add/subtract brush and the depth
  limit (the engine keeps no per-plane evidence for it yet).

## The rest of the plan (2026-11-24)

| Stage | Built | Evidence |
| --- | --- | --- |
| X3 | The Pi takes highlight groups (`Plan.highlight`: shutter, every, range, shots) after the base group at the same plane number and focus, per-position shutters, and `queue_pass`; journal `tier` and `exposure` ([format](tiers.md)). The plan's Exposure step offers them and counts their time | Rig: two 21-plane captures, every highlight group at its base group's plane and focus, 42 and 22 shutter changes; 19.0 s a plane with a group, 11.3 s without (MEASURED, [rig](rig/)) |
| X4 | Highlight groups fused at the gather: identity by tier, measured ratio, replacement near the pin, sparse patches on CPU and GPU, noise scaled, writer ceiling raised ([results](fusion/results.md)) | Bytes identical without tiers; no pinned site left where the companion is not pinned; hand-over 0.975-1.005 on the rig; 17 of 21 planes fused, 4 refused for sway (VERIFIED, MEASURED) |
| X1 | One Calibrate survey at two shutters, read by `strehl survey` ([results](census/results.md)); its outline becomes the subject | Rig: 49 RAWs in 179 s; ratio 0.2500 measured against 0.2500; glints to 2.5x the 1/4 s full scale ([evidence](rig/evidence/survey-pronotum.json)) |
| X2 | The survey's three choices in the Exposure step, the suggested one first | The pronotum: a highlight pass at 2 s with 1/25 s groups |
| X5 | Highlight groups kept apart in the follower; pinned planes offered a highlight pass (two stops shorter where a group still pinned) | Unit-tested; the checker's `pinned` and `tier` from X4 |
| X6 | White from the subject's diffuse level with a shoulder (engine, [results](detail/results.md)); the master keeps fused values above 1 | Scarab 1.44 stops brighter; bytes identical without a subject. Not built: a RAW-referred clipping view in Develop |
| S4 | Metering, bounds offer, focus-step, plane checker and Develop region from the subject ([results](s4/results.md)) | Weevil bounds save 33 planes (core 66); a fault on the backdrop asks for no retake |
| R1-R4 | "Re-shoot…" in the Stack station's pinned region popover: rig continuity, highlight, shadow or retake pass into the same capture, stack again | Unit-tested. Not built: a probe group, infill planes, RAW evidence kinds in evidence.strehl |
| D2, D3 | "Detail" (Natural, Safe, Crisp; Safe by default) from each stack's noise; the guard follows real pinning ([results](detail/results.md)) | Safe: noise rise 0.93-0.97 of B on four stacks; weevil fine amplitude 1.27-1.29; unrestored share 1.81 % to 0.77 % |

Rig gates of the first round, run 2026-11-24 on the pronotum: Q3 (test shots after the
first in 8-11 s with "manage power" on), Q6 (a capture stopped after four of five planes
passes the stopped-capture check and stacks), Q7 (0.45 px rms along the vertical at
2.6 Hz, "up to 1/43 s"), the live Auto outline on a real 31-frame sweep (MEASURED).

## Open

- The owner's look at native crops: base, fused, fused with "Tame glints"; the Detail
  strengths.
- On a swaying rig some highlight groups are refused (4 of 21); stillness first.
- Optical restoration is skipped where every measured tile is near clipping (the 2 s
  pronotum capture): with fusion the guard could read the fused data.
- The A7CR white level: the engine reports 15360, the data reach 16383 (census note).
- Remote exposure changes are undone at the camera's shutdown by design (the Pi restores
  each connection's settings); the camera body now reads 1/15 s, not 1 s.
- Not built: the add/subtract brush and depth limit (S3), a RAW-referred clipping view
  (X6), a probe group and infill (R), pausing highlight groups when no base group pins
  (X5).

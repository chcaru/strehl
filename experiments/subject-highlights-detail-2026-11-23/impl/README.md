# Subject, highlights and detail: implementation log

**Status:** stages Q (Q1 to Q7), S1 to S3 and the owner's bug list are built on
`studio2/subject-impl` (2026-11-23). Not pushed, not installed, Pi not deployed. Nothing
in this round was run on the rig. **Plan:**
[subject, highlights and detail](../../../docs/proposals/2026-11-subject-highlights-and-detail-plan.md).
**Ledger rows:** `shd-bugs`, `shd-q-restore`, `shd-q-planecheck`, `shd-q-capture` and
`shd-s` (all 2026-11-23) in [the milestone ledger](../../../docs/agents/milestone-ledger.md).

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

## Before the owner uses it

1. Deploy the Pi host (it carries `new_plan`, `subject`, `starting` and Q3; older hosts
   are sent none of them) and install the desktop.
2. Rig gates still open: Q3 (a second test shot in about 10 s with "manage power" on),
   Q6 (stop a five-plane capture after three, stack it), Q7 (about 0.5 px on the rig as
   it stands, under 0.1 px when still), the live Auto outline on real survey frames,
   and Q5's retake count on the swaying rig.

## Next stages

S4 (the subject drives metering, bounds, step, checks and shares), X1 and X2 (one
Calibrate pass and the three-way exposure advice), then X3, X4 and X6 with a Pi deploy
and a rig session for X7 (plan section 8).

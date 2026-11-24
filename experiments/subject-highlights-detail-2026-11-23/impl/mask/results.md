# Plan S2: automatic subject selection, engine and CLI

Ledger row `shd-s-2026-11-23` (S2 engine part only). Plan:
[subject, highlights and detail](../../../../docs/proposals/2026-11-subject-highlights-and-detail-plan.md),
sections 2, 4 (S2) and S5. Branch `studio2/shd-mask`. Author-run, not independently
reviewed.

Labels: MEASURED (a command here produced the number), DERIVED, ARGUED, UNVERIFIED.

## What was built

- `crates/strehl-core/src/subject.rs` and `subject-*.rs`: per-frame evidence from one
  green site plane of a RAW exposure (`raw_frame_cells`, noise model injected as a
  variance function), assembly over planes with one magnification rate
  (`assemble`), the quiet population (`quiet`), selection (`select`, re-run per slider
  setting from the stored `Evidence`), crack-following outline rings simplified to at
  most 256 points, their even-odd raster (`rasterize`), and the live-view variant
  (`live_view_subject` on RGB8 frames).
- `crates/strehl-cli/src/subject-cmd.rs`: `strehl subject <run> [--every N | --planes
  a,b,c | --count 13] [--sensitivity 3] [--grow 3] [--buffer 16] [--no-register]
  [--json] [--out FILE] [--mask-png FILE]`. Reads member 1 of each plane's recorded
  group (`recorded_groups`, as `focus-step`), decodes four-shot archives through
  `strehl_raw::decode`, uses `profile::noise_model_for`. `SubjectJson` is the JSON
  contract (`rings`, `cell_px`, `provenance`, `depth`, `area_share`,
  `reference_focus`, plus extras). Outputs inside the capture folder are refused.

## Gates (plan S5)

Commands: [gates.sh](gates.sh); output: [gates.txt](gates.txt); comparison:
[compare.py](compare.py). Release build of this branch, 32 logical CPUs. Prototype masks
were produced by running `../../subject-mask.py --grow 3` on the per-plane summaries in
`C:/strehl-scratch/i-round/planes/` (outputs in `C:/w/shd-mask-out/proto/`, not committed).
The results note's outlines are the all-planes `--grow 3` masks (35.6 % weevil; scarab two
parts).

The product grid covers the decoder's active area (9504 x 6336); the prototype's covered
rawpy's visible area (9564 x 6376). The level maps place the active origin at visible
(32, 20) (correlation 0.99998 weevil, 0.99993 scarab, MEASURED); the prototype mask is
sampled at the product cells' centres. Product plane numbers are the capture's `plane`
field, one more than the prototype's `ordinal` (same focus targets, VERIFIED from
`planes.json`).

| Gate | Result | Label |
| --- | --- | --- |
| Weevil, 13 planes spread (default), against the results note's all-planes mask | IoU 0.9920; outline median 0, p95 1 cell | MEASURED |
| Weevil, the prototype's own 13 planes (`--every 16`), against all-planes / against the prototype on the same 13 | 0.9915 / 0.9920 | MEASURED |
| Scarab, 13 planes spread (default), against all-planes | IoU 0.9939; outline median 1, p95 1.4 cells | MEASURED |
| Scarab, `--every 17` (13 planes), against all-planes / against the prototype on the same 13 | 0.9932 / **0.9592** | MEASURED |
| Weevil planes 1-21 (prototype 0-20), subject out of focus | Empty; summary "No subject: nothing comes into focus in these 21 planes (119 in-focus cells, all in specks under 189 cells) ..." | MEASURED |
| Same 21 planes through the prototype | 67.0 % of the frame (fails the gate) | MEASURED |
| Unit: textured disc on a noise background | found, no cell misplaced beyond 3 cells of disc..disc + rim + buffer | MEASURED (`cargo test -p strehl-core subject`) |
| Unit: blank frames; untextured soft-edged bright blob | empty, says so | MEASURED |
| Unit: sensitivity 2.5 to 12, grow 0 and 3 | every mask inside the previous one; grow 0 shrinks | MEASURED |
| Unit: live view, textured disc / blank sweep | found loosely (within 21 cells, nothing missing inside 12 of a 15-cell disc) / empty | MEASURED |

The scarab's like-for-like 0.959 is below 0.97 against the prototype's own 13-plane mask,
but that mask is itself 0.954 from the prototype's all-planes mask, while the product's
13-plane mask is 0.993 from it. The difference is the noise floor: the prototype's fitted
floor gave the scarab's quiet population a lower spread of 0.41 (log), the injected
profile model gives 0.19, so the product's threshold sits at 3.2 x the floor instead of
22.6 x the prototype's floor, and the sure subject reaches the flank the prototype only
partly grew into (ARGUED from the two runs' printed statistics).

Other measured behaviour (13 planes spread, MEASURED):

- The quiet mode sits at 1.00-1.04 x the injected model's noise floor on both stacks and
  1.12 x on the out-of-focus set: the profile model describes the backdrop's Laplacian
  energy, which checks the injected model against these frames (a consistency check,
  not a photon-transfer measurement).
- Registration: -13.0 ppm per focus unit (weevil), -15.0 (scarab); the plan quotes about
  -13 for the weevil. `--no-register` on the weevil: IoU 0.991 against registered, 1,954
  cells outside it.
- Sensitivity on the weevil: 6, 8 and 10 give the same mask as 3 (growth restores it;
  seeds 200k, 28k and 6k cells); 12 gives an empty mask (threshold 68 x the floor, only
  specks survive). With 13 planes the three-plane running mean spans 48 planes, which
  dilutes peak evidence; high sensitivities behave differently from the results note's
  199-plane runs.
- Scarab without growth (`--grow 0`): 23.2 % of the frame in 10 parts against 43.8 % in 2,
  IoU 0.53: the dark flank needs growth, as in the results note.
- Depth: weevil planes 17-182 (central 99 %: 34-166), scarab 1-193 (18-193). The results
  note gives 34-162 and 20-179 for 99.8 % of blocks from all planes. The extremes sit one
  survey plane wide because the three-plane mean at a run's end repeats the edge plane;
  `core_first_plane`/`core_last_plane` in the JSON are the robust range.
- Rings: weevil 5 (outline 229 points, 4 holes left out between legs), scarab 2.

## Timing (13 planes, release)

MEASURED, warm file cache (the archives had been read minutes earlier):
decode and cells 0.20-0.21 s, evidence assembled 0.24-0.26 s, selection 0.027-0.029 s,
on a lightly loaded host. With other agents holding the host at 100 % CPU the same weevil
run took 4.3-4.7 s wall (decode 1.5-1.7 s, evidence 3.2-3.5 s, selection 0.8 s). Cold-cache
decode was not measured. Decode, the per-frame cell pass, the 81-scale registration
search, rescaling and the per-cell reduction run on rayon; labelling and tracing are
single-threaded.

## Deviations from the prototype

1. **Noise floor:** the injected profile model, `20 x variance(level)` for the
   4-neighbour Laplacian (its variance under independent noise), instead of the fitted
   lower envelope. Thresholds are therefore in units of the real floor.
2. **Sure subject is focus evidence only** (plan S2 step 6). The prototype also seeded
   from a strong level difference from the backdrop; that made the out-of-focus gate
   fail (67 % of the frame from planes 0-20). The level difference stays in growth.
3. **Specks do not seed:** in-focus regions under 0.02 % of the frame (at least 25 cells)
   are dropped before growth. One hot pixel inside a bright defocused blob otherwise grows
   into the whole blob.
4. **Registration uses focus positions:** the rate is per focus unit when targets are
   recorded (per plane otherwise); the prototype's was per plane used.
5. **Outline:** crack-following rings on cell corners for every part and hole (the
   prototype traced outer boundaries through cell centres and ignored holes); unsimplified
   rings fill back to the raster exactly (unit test); Douglas-Peucker from 1 cell,
   loosened until a ring has at most 256 points.
6. **Depth range:** first and last plane of any in-focus subject cell, plus the central
   99 % (the prototype printed 0.5-99.5 percentiles).
7. **Grid:** the decoder's active area, not rawpy's visible area.
8. **Live view:** growth on focus evidence only (plan); the sure subject is focus
   evidence only. The per-frame quiet-level normalisation is kept (no injected model for
   JPEG), so brighter areas carry more noise energy than a dark backdrop; a bright
   untextured blob in synthetic frames is picked up. This is the live outline's known
   looseness and is not in the RAW path.

## Not done

- S1/S3 wiring (host, manifest, desktop sliders, brushes, depth limit). The depth limit
  needs per-plane evidence, which `Evidence` does not keep (it keeps focus maximum, its
  plane and level).
- The live-view variant was tested on synthetic frames only, not on the rig's 30 live-view
  frames.
- Cold-cache timing; a textured backdrop in focus; a subject filling the frame (the
  absolute fallback is implemented but not exercised on real data).

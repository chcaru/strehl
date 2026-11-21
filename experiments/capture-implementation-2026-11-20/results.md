# Capture and storage, round 4: implementation results (2026-11-20)

What was built from [the round-4 plan](../../docs/proposals/2026-11-a7cr-capture-and-storage-plan-4.md)
after the owner's decisions, and what the rig and the recorded stacks measured. Commits on
`main`: `c4148fbe1` (engine: focus step, compact), `98db0e465` (capture: K1-K3),
`1a975d323` (desktop: calibrate, focus step, compact), `ef200f6bc` (retake rule, compacted
JPEG size). Installed: the studio Pi's controller and bridge (backups
`/root/strehl-before-round4-1795196379`, the originals, and later ones) and the owner's
desktop and receiver, in place.

Rig: ILCE-7CR, f/5.6, ISO 100, 0.6 s unless stated, four-shot; subject a pencil and a
printed part (structured lettering and layer lines at lens position 41000). Labels:
MEASURED, VERIFIED, DERIVED, ARGUED, UNVERIFIED.

## Owner's decisions and what became of them

| Decision | Done |
| --- | --- |
| D1 focus step: determine the ideal step, maybe a Capture feature | `strehl focus-step`; Capture screen "Calibrate step" and "Measure focus step" |
| D2 thinning: numbers and proof, nothing permanent | numbers for every stack on disk and three proofs below; nothing deleted |
| D3 compact as an optional action on finished stacks | `strehl compact`, Capture screen "Compact…" with an estimate and a confirmation |
| D4 drop the large preview JPEG | compacted files point the full-size JPEG's IFD at the preview |
| D5 deferred retakes: experiment first | measured acceptable, built (K3) |
| D6a exposure floor, a calibrate feature | floor measured; "Calibrate step" reports planes and time |
| D6b two upload streams by default | built (K2) |

## Capture (MEASURED on the rig)

| Four-shot plane, 0.6 s | Before | Now |
| --- | ---: | ---: |
| Plane period, error correction off | 7.3 s | 5.65-5.69 s (11 runs) |
| Focus step between planes | 1.25 s | 0.02 s (the lens moved during the last RAW's fetch) |
| A RAW on the Pi to saved on the PC | 1.36 s | 1.11-1.15 s |
| 12 planes with error correction and 2 retakes | about 108 s (DERIVED, 9 s a plane) | 85.8 s, every group passing |

- **K1.** The bridge acts on the camera's events, sends the lens on once the group's last
  exposure is in the camera, and ends the group when its RAWs are fetched and the move has
  settled; the settle counts from the camera's focus-result event. The remaining gap to the
  lab's 5.09 s is the last RAW, still fetched before the next shutter.
- **K2.** Two uploads at once, one hash per RAW, journal appends (one whole-journal upload
  per run, then appends), an 8-RAW queue in a 2 GiB tmpfs, the receiver's lock only around
  name checks and commits. Queue peaks of 2-3 at short exposures show uploads overlapping.
- **K3.** Verdicts are collected between planes; a failed plane is visited again later
  through the approach move. **D5 experiment** (`l11-return`, lab bridge): the same plane
  taken twice reads 0.068 px apart, a revisit after three planes forward and the approach
  back 0.17-0.28 px (sharpness 0.92-1.02), one plane on 0.38 px. A revisit lands within
  about one step of the first visit, far inside the 50-113 units a point stays sharp over:
  acceptable. A retake costs about 8.5 s.
- **Checker fix.** On the plain subject `follow` asked to retake every group: its gate
  judges what remains after the measured sub-photosite residual is subtracted, and that
  residual was about 0.4 photosite off while the witness pairs themselves agreed to
  0.05-0.15. A retake cannot fix the scene's estimate, so such groups are no longer
  retaken; the render's gate is unchanged (`evidence/ec-e2e-before-fix.json`).
- **Bug fixed.** Deleting a finished stack's folder on the PC left the Pi refusing to
  connect (its recovery re-sent that run's journal and the receiver refused a missing
  folder). Found when today's first connect failed after last night's cleanup.

### Settle (K4) (MEASURED, interleaved 12-plane runs; the engine's group check)

| Settle after the focus result | Groups passing | Witness shift, median (max) | Plane period |
| --- | ---: | --- | ---: |
| 500 ms | 45 of 48 (still house); 13 of 24 (owner walking) | 0.101 (0.205) px | 5.66-5.69 s |
| 1000 ms | 45 of 48 | | 6.00-6.02 s |
| 2000 ms | 48 of 48; 20 of 24 (walking) | 0.089 (0.168) px | 7.03-7.05 s |

Repeated once the owner had left (`evidence/ab-settle-empty-house.txt`): 500 ms 45 of 48,
2000 ms 48 of 48, and two of the three misses at 500 ms were the first plane, right after
the 128-unit approach move (0.320 and 0.201 px; the third was a local tile disagreement).
So the plane reached straight after an approach move (the first, and a retake's) now
settles at least 2000 ms; every other plane keeps the 500 ms default, which the last RAW's
fetch hides. Four runs of 12 planes with that (`ab-settle-first-plane.txt`): 48 of 48 pass,
first-plane shifts 0.05-0.15 px, plane period 5.66-5.69 s, 1.7 s more a run. ARGUED: with
people moving about, a 2000 ms settle on every plane is the safe choice (1.4 s a plane).

### Exposure floor (D6a) (MEASURED, ISO raised to keep the brightness, 8 planes each)

| Exposure | ISO | Four-shot plane | Single-shot plane | Wire per RAW | RAW to PC |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0.6 s | 100 | 5.67 s | 2.25 s | 47.5 MB | 1.11 s |
| 1/6 s | 400 | 4.44 s | 1.79 s | 56.7 MB | 1.42 s |
| 1/10 s | 640 | 4.32 s | 1.72 s | 59.8 MB | 1.53 s |
| 1/25 s | 1600 | 4.29 s | 1.64 s | 67.3 MB | 2.03 s |

Below about 1/6 s the camera's own cadence and the four fetches set the pace; at ISO 1600
a four-shot plane puts 63 MB/s on the Wi-Fi, against the two-stream ceiling of 69 MB/s.
The plane-time estimate (`timing::initial_plane`) now has that floor.

## The focus step (D1, D2)

`strehl focus-step` (MEASURED): the scarab stack's fine detail stays sharp over 113 units
(10th-90th percentile 95-132), suggested step 16, twice the 8 it was taken at; 4.7 s for
196 planes. The rig's pencil subject: 50 units (33-64), suggested 7. The ideal step
differs by setup, which is why the Capture screen calibrates it: "Calibrate step" (25
single RAWs, 61 s end to end through the control interface, survey deleted, pixel shift
restored) and "Measure focus step" on a completed capture.

**Thinning (numbers and proof only; nothing was deleted)** (`evidence/thinning-numbers.txt`,
`thinning-proof.txt`):

| Stack | Size | Planes at step | Sharp width | Suggested | Every 2nd plane keeps | Saves |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| scarab, four-shot | 51.2 GB | 196 at 8 | 113 | 16 | 98 planes | 25.6 GB |
| scarab, single shot | 12.8 GB | 196 at 8 | 115 | 16 | 98 planes | 6.4 GB |
| dark background, four-shot | 25.8 GB | 107 at 8 | 88 | 12 | (1.5 times finer than needed: not thinned) | 0 |
| dark background, single | 6.4 GB | 107 at 8 | 86 | 12 | | 0 |

Proof, renders from all planes against every second plane (detail energy where signal
dominates, floor removed; flat-tile energy is noise):

| Stack | Detail energy | Flat-tile energy (noise) | Crops at 200 % |
| --- | --- | --- | --- |
| scarab, four-shot (round-4 study) | 0.998-1.000 | 0.992-0.998 | same |
| scarab, single shot | 1.000-1.004 | 0.989-0.995 | same |
| dark stack (step 16, width 88: past the suggested step) | 1.006-1.014 | 1.019-1.069 (noise +1-3 % in amplitude) | same |

## Compact (D3, D4)

`strehl compact` (MEASURED on a hard-linked copy of the whole scarab stack; the capture
itself was hash-checked unchanged): 784 files in 2 min 28 s, 51.2 GB to 18.6 GB; the dry
run estimated 18.4 GB from four files in 1.4 s. Render from the compacted stack against the
lossless one (`evidence/compact-scarab-render.txt`): noise amplitude within 0.05 %, detail
energy 1.0000-1.0003, channel means within 3e-5; crops indistinguishable. First render
46 s (empty cache, every file verified), later 21 s. The merge adds the quantiser's 7.7 %
of variance to its noise model for compacted frames; every other render is unchanged
(6/6 reference hashes, byte-freeze 5/5). In a compacted file the full-size JPEG's IFD
points at the 1616 x 1080 preview and states its size (`compacted-jpeg-check.txt`).

## Follow-up: quality against time, and the compacted final image (2026-11-20 evening)

The owner asked where the quality floor is for shorter exposures and for coarser steps, and
for the final images from compacted and lossless files side by side. Charts and crops were
sent to the owner (kept in `outputs/quality-curves-2026-11-20/`,
`outputs/exposure-quality-2026-11-20/`, `outputs/step-curve-2026-11-20/`,
`outputs/compact-compare-2026-11-20/`, none committed); numbers in `evidence/`.

**Exposure (MEASURED, `exposure-quality.py`, `exposure-analyse.py`).** The rig subject;
for each setting two four-shot runs of the same 10 planes (step 8 from 40960, error
correction off), ISO raised to keep the brightness. Noise is temporal: run A minus run B,
for each RAW (same plane and shot) and for the final render (CLI default, pyramid merge),
in flat areas, so the scene's texture is not counted as noise.

| Setting | Plane (s) | Final image SNR, mid-tones | Relative | sqrt(exposure ratio) | One RAW SNR, relative |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0.6 s ISO 100 | 5.7 | 67.7 | 1.00 | 1.00 | 1.00 |
| 1/3 s ISO 160 | 5.0 | 48.1 | 0.71 | 0.75 | 0.70 |
| 1/6 s ISO 320 | 4.4 | 32.4 | 0.48 | 0.53 | 0.48 |
| 1/10 s ISO 640 | 4.4 | 27.2 | 0.40 | 0.41 | 0.38 |
| 1/25 s ISO 1600 | 4.3 | 15.4 | 0.23 | 0.26 | 0.24 |
| 1/50 s ISO 3200 | 4.0 | 9.7 | 0.14 | 0.18 | 0.17 |

(Plane times of 1/3 and 1/50 s read from the runs' capture events before they were deleted, to
0.1 s; the others match `exposure-floor.txt`.) The noise follows the light, not the ISO: SNR
falls as the square root of the exposure time (shot noise). Control: at 1/25 s, ISO 100
pushed four stops in the analysis gave a RAW SNR of 12.1 against 11.0 at ISO 1600, so the
camera adds no noise of its own when ISO goes up; the shorter exposure collects fewer photons
(at a scene point at 10 % of full scale at 0.6 s: about 3800 electrons, 260 at 1/25 s). The
curve: down to 1/6 s each step buys time (5.7 -> 4.4 s a plane, 22 %) at twice the noise;
below 1/6 s the plane hardly gets faster (4.4 -> 4.0 s) while the noise keeps rising.
At 1/25 s and shorter, coloured single-pixel speckles appear in dark flat areas of the
final image (crop `exposure-dark-flat-*.png`; cause UNVERIFIED). In this subject's flat
areas the brightest points reached only about 10 % of full scale at 0.6 s ISO 100
(MEASURED: no flat pixels above that). So more light, not a longer exposure, is the way to
get both speed and low noise (ARGUED).

**The light (MEASURED, `exposure-levels.py`).** Brightness of every RAW: within a four-shot
group the shots agree to 0.3-1.3 % (median) at every exposure, 1/25 s the steadiest (no
flicker at short exposures); single groups reached 5-9 %. Straight after switching on, the
light dimmed 9 % over the first run's 60 s and 6 % over the second's; later runs drifted
-6 to +4 %, with no pattern by exposure. ARGUED: with "manage power" switching the light on
at a stack's start, the first minute of planes is brighter than the rest; not tested here.

**Focus step (MEASURED, `step-curve.ps1`, `step-curve-analyse.py`).** Renders from every
k-th plane of two stacks captured at step 8, against all planes; fine detail (1.5 px
gradient energy, noise floor removed) at the worst 10 % of detail tiles, the points that
fall between planes:

| Step | Scarab (width 113) | Its stack time at 5.67 s a plane | Dark stack (width 88) |
| ---: | ---: | ---: | ---: |
| 8 | 1.000 | 18.5 min | 1.000 |
| 16 | 0.990 | 9.3 min | 0.989 |
| 24 | 0.988 | 6.2 min | 0.983 |
| 32 | 0.946 | 4.6 min | 0.982 |
| 48 | 0.895 | 3.1 min | 0.962 |
| 64 | 0.863 | 2.4 min | |
| 96 | 0.818 | 1.6 min | |

The knee is at about a fifth of the sharp width (scarab: 24 keeps everything 16 keeps; 32
loses 5 %). ARGUED from two stacks: the suggested step (width / 7) could be width / 5, a
third fewer planes; not changed (the owner's call). Finer steps buy no measurable noise
reduction: the pyramid merge chooses per detail band and does not average many planes. In
flat tiles the energy moved -21 to +19 % from step to step on the dark stack with no
direction, and on the scarab it tracked the detail (its flat tiles hold soft texture), so
noise is set by the exposure, not the step.

**Compact, the final images (MEASURED, `compare-compact.ps1`, `compact-final-compare.py`,
`compact-shift.py`; `evidence/compact-final-images.txt`).** The scarab stack compacted again
in a hard-linked copy (47.7 -> 17.3 GB of archives, 152 s; the capture's archives back to one
link each, the first three hash-checked unchanged; the copy deleted), both rendered with the
desktop's command (`stack --merge pyramid --srgb`, four-shot). In 8-bit display steps: mean
difference 0.2, 99th percentile 1.2, largest 11.5; 57.5 % of pixels identical. The
difference that remains is edge-shaped: the alignment, refitted on the quantised data,
places frames up to 0.13 px differently (median 0.01 px; phase correlation over 40
windows), which moves edges, not detail. Crops at 200 %: no visible difference.

## Not built, and what is next

- The last RAW of a group fetched during the next group's first exposure (5.65 s to about
  5.1 s a plane); it crosses group boundaries in the bridge's binding.
- `strehl thin` (F3 deletion): decision D2 asked for numbers only.
- A3 (a better lossless predictor) and A2 (deleting groups superseded by retakes).
- The render's gate on plain subjects: it demotes groups whose measured residual is off;
  a render-quality question, not changed here.
- The 8 CLI tests that need `STREHL_DEFECT`, `STREHL_M194G_BRIDGE_PRIVATE_OUTPUT` or
  `STREHL_GREEN_PROBE_OUTPUT` fail in the plain harness, as before this round.

## Files

`ab-settle.py`, `ec-e2e.py`, `exposure-floor.py`, `calibrate-e2e.py`, `return-analyse.py`,
`thinning-numbers.py`, `prove-thinning.ps1`, `compacted-jpeg-check.py`, `deploy.py`,
`build-pi.sh`, `clean-runs.py` (deletes only named test runs made on 2026-11-20); the
follow-up's `exposure-quality.py`, `exposure-analyse.py`, `exposure-levels.py`,
`step-curve.ps1`, `step-curve-analyse.py`, `compare-compact.ps1`, `compact-final-compare.py`,
`compact-shift.py`, `make-charts.py`; the lab
script `../capture-pipeline-2026-11-20/ptp-lab/l11-return.txt`; results in `evidence/`.

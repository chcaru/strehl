# First physical Sony focus-control review

Identifier: `sony-focus-control-2026-11-07-capture-review`. Owner: root.
Input: read-only `D:/remote-control-test`, two focus-test logs, one preflight and
146 ARWs in five DCIM folders. The owner identifies two different subjects:
irregular calibration slide and regular checkerboard, with different shutter
and white-balance settings. Analyze them separately; no cross-subject quality
ratio. The prior implementation/test brief is
[sony-focus-control-2026-11-07](../sony-focus-control-2026-11-07/brief.md).

The owner confirms both subjects were absolutely stationary throughout their
runs and suggests focus breathing as a contributor to apparent image changes.
Treat target stationarity as the capture condition. A changing fitted sharp
band does not establish subject motion; separate image geometry from blur
response, and leave the origin of any residual slow change unresolved.

## Scope and evidence

First reconcile the actual images with the intended 73-shot sequences using
timestamps, camera folder boundaries, exposure metadata and logs. Record input
hashes, source/runtime versions, commands, dimensions and decoding metadata.
Check all images for readability, duplicates, truncation and unexpected settings.
Inspect full-frame previews before selecting native image witnesses.

The consumer is physical focus-control feasibility, not a rendered image-quality
score. Compare fixed-null variability, command-null variability, the 512-unit
positive control, repeated fine sweeps and bidirectional returns. Native width-1
bursts are the practical comparator; their encoder changes are not calibrated
object-space distances. Fit scene-dependent geometry only within a run. Flat
controls precede any sharpness measurement, with scrambled-order and synthetic
blur/shift controls for any quantitative estimator. Noise, contrast, motion and
interpolation can fool a gradient statistic; it cannot alone establish quality.

## Prior work and limits

Executed `python scripts/research.py search focus repeatability --limit 6` and
`python experiments/ORCH-drift-check/prior_art.py FocusPosition 'focus repeatability' 'sharp band'`.
Relevant prior references include `docs/research/M-FRC-NODE-GATE.md` (repeatability
cannot be inferred from nearby witnesses), `docs/research/F-camera-lens-optics.md`
(camera metadata versus optical calibration), the implementation audit and
`docs/agents/capture-reference.md` (observed rig, active-area/noise requirements).

Report command acceptance separately from optical movement. Do not promote a
single-unit readback to a motor step, micrometre increment, or resolution gain.
If texture/geometry cannot resolve focus changes beyond the null, report that
limit rather than forcing a positive conclusion. No pixel shift, new capture,
merge-default change or SYNTHESIS fold is part of this review. Author-run checks
are not independent review of an optical conclusion.

## Resources and outputs

One analysis worker with bounded per-frame storage; original CFA as u16, analysis
as f32, never an aligned full-frame volume. Copy RawPy arrays inside its context.
Check decoding against an independent available decoder before numerical claims.
Use fixed within-run display transforms; thumbnails are orientation only.
Derived previews, tables and caches go to `outputs/sony-focus-control-capture-review/`.
Analysis code and the evidence report remain with this brief. Never write into
the capture root or create capture sidecars.

# Subject, highlights and detail: investigation brief

Owner request (2026-11-23), three research items and one feedback item that
depends on them:

1. The Capture station's exposure advice over-exposes shiny areas and glints
   on the subject. Is per-plane multi-exposure (HDR for clipped areas) worth
   building, planned at calibration and corrected during capture?
2. Could Develop drive corrective re-shoots of the planes behind a region
   while the subject is still on the rig?
3. The new A7CR glitter-weevil stack does not resolve the scales much better
   than the older A7C II stack. Is that the lens and sensor, or the software?
4. Feedback item: the subject box should become a polygon, with automatic
   subject selection (sensitivity, buffer, manual correction), and it should
   drive the calibrations.

Deliverable: a plan for an implementing agent,
`docs/proposals/2026-11-subject-highlights-and-detail-plan.md`. Ledger row
`subject-highlights-detail-2026-11-23`.

Honesty note: the two read-only summaries marked "exploratory" below ran
before this brief was written. Their scripts are kept as run. Everything else
is registered here first.

## Bounds

- No product code changes. No commits unless the owner asks.
- Read-only inputs:
  - `D:/StrehlCaptures/stack-1795460665629-8651`: glitter weevil, A7CR
    four-shot, 199 planes, step 7, ISO 100, 1/4 s (taken 2026-11-23).
  - `D:/personal/macro/insects/bug-3/107MSDCF`: the same weevil, A7C II,
    299 single shots.
  - `D:/StrehlCaptures/stack-1795300522964-6430`: green-gold scarab, A7CR
    four-shot, 211 planes, ISO 100, 1/10 s.
  - The owner's renders of these in `C:/Users/chris/Pictures/Strehl/`.
- Rig work, allowed by the owner for this round (the weevil is still on the
  rig): single-plane test captures only (`capture_kind` "test", which the
  open desktop neither follows, stacks nor lists), plus live-view frames.
  ISO, shutter, pixel-shift count and power are put back afterwards; camera
  and light off; "manage power" on. The owner may be walking nearby, so every
  rig series ends by repeating its first setting as a drift control.
- New renders use a copy of the installed build
  (`desktop-c30cb075f79533d0`) with its own cache directory, one at a time.
  Outputs and pictures stay in `C:/strehl-scratch/i-round/` (never in the
  repository: it is public and the pictures are the owner's).
- Stop a question when its size is bounded well enough to design against.

## Prior work read

- `docs/research/M30-hdr-cobracket-measured.md` and SYNTHESIS facts 242-243:
  HDR co-bracketing is supported by the model, not defaulted, to be triggered
  per stack by clipping at the gathered frames. Measured on A7C II stacks
  with at most 0.075 % clipping.
- BUILD-HIGHLIGHT, V-HIGHLIGHT, M109 (rendering of blown highlights), M100
  and M105b (exposure on the viewing path), M54 (clip mask).
- `experiments/image-quality-2026-11-02/results.md` (glint compression),
  `experiments/fine-support-guidance/charter.md` (defocused highlights).
- `experiments/capture-implementation-2026-11-20/results.md`: exposure
  advice (base ISO, longest exposure whose brightest 0.1 % stays under 0.9),
  SNR as the square root of exposure, step against sharp width.
- A7CR quality work: `experiments/a7cr-full-potential-2026-11-14/`,
  `a7cr-fourshot-quality-2026-11-16/`, `a7cr-fourshot-impl-2026-11-17/`;
  BUILD-SHARP, M5, G-edof, M79, facts 141-143, 474, 1074-1076, 1112
  (deconvolution verdicts, all A7C II era).
- `python scripts/research.py search` and
  `experiments/ORCH-drift-check/prior_art.py` for: hdr exposure bracket
  highlight clipping; specular glint; subject mask segmentation polygon;
  deconvolution restoration diffraction.
- Not found in the record: a point-spread measurement from glints, a
  four-shot stack scored against its own sharpest four-shot plane, a subject
  mask in Capture, restoration strength set from measured stack SNR.

## Questions, instruments, controls

| # | Question | Instrument | Control or placebo | Fooled by |
| --- | --- | --- | --- | --- |
| Q1 (exploratory) | How much of each plane clips, per colour, and does one test shot see it? | Full RAW histograms and clipped counts per 8x8 block, member 1 of every plane (`extract-planes.py`, `clip-summary.py`) | Planes far from focus must show no clipping where in-focus planes do | Member 1 samples each colour on its own lattice only; counts are of samples, not areas |
| Q2 (exploratory) | Does a glint's peak depend on focus, and over how many planes does it clip? | Block peak against plane offset from the block's brightest plane (`glint-focus.py`) | The same profile for blocks that never exceed 0.3 must be flat | Planes are not registered: a block is tracked over its 3x3 neighbourhood; clipped peaks are lower bounds |
| Q3 | How bright are the glints really, and how many stops must a short exposure sit below the body exposure? | Rig: four-shot test groups at three in-focus positions over a shutter ladder; peak of each glint in the shortest unclipped exposure, scaled by the measured exposure ratio | Ratio of unclipped mid-tones between adjacent rungs must match the shutter ratio; first rung repeated last | Light flicker at short shutter times; the light's warm-up drift |
| Q4 | Can a long and a short group of one plane be fused per sample without visible seams, and what do the glints look like then? | Python fusion in linear RAW units from Q3's groups; native crops against the long group alone | Fusing a group with a copy of itself scaled must return it unchanged | Misregistration between groups taken minutes apart |
| Q5 | What does a highlight pass cost in time? | Group seconds from the journal at each shutter; time for an exposure change and for a pixel-shift count change | The 1/4 s groups must match the owner's capture (6.06 s) | Test runs include an approach move that a same-visit pair would not |
| Q6 | How repeatable is a revisit of a plane (needed by retakes, highlight passes and corrective re-shoots)? | Six test groups at one position, each after its own approach; shift and focus difference between them | Members of one group against each other | The owner walking; thermal drift |
| Q7 | Is the weevil stack softer than its own sharpest plane, and how far is that plane from the lens's limit? | Fine-band power of the stack against the assembled in-focus plane at the same tiles; a fine focus sweep (step 2) around one plane; glint point-spread width in the shortest exposure against the diffraction width | Flat tiles first; a deliberately defocused plane must read lower; the same tiles on the half-stacks | Election-made detail and sensor pattern read as signal; glints are not guaranteed to be points |
| Q8 | Why was optical restoration not applied to the weevil, and what does the stack gain with it, with a longer exposure, and with a lower gate? | Re-renders with the cutoff supplied, the gather in the model, and gate settings; half-stack signal and noise spectra | Default re-render must reproduce the owner's result; odd/even halves for noise | Ringing beside glints reads as detail |
| Q9 | Can the subject be found automatically from data the rig already takes? | Mask from the per-plane focus-energy maps (all planes, every 8th plane, and live-view frames from a rig sweep); sensitivity and buffer swept | Hand-traced outline on the final render; a plane set with the subject out of focus must give an empty mask | Backdrop texture, dust and glare that come into focus |
| Q10 | What changes when the calibrations use the subject mask instead of the whole frame? | Exposure percentiles, clipped counts and sharp width inside against outside the mask on both stacks | The whole-frame numbers must match the product's own | A mask that leaks onto the backdrop |

## Stopping conditions

- Rig: stop at the first controller fault, at any sign that the subject has
  moved between the first and repeated rung by more than 2 px, or after
  40 minutes of camera time.
- Renders: at most twelve, one at a time.

# Close-tile test: results (2026-11-23, afternoon)

Addendum to [results.md](results.md). Author-run, not independently reviewed. Labels as
there: MEASURED, VERIFIED, DERIVED, ARGUED, UNVERIFIED.

The owner shot the weevil's pronotum at the lens's closest focus, first at 1/4 s, then
tried 1 s and stopped part-way. This note measures what the closer framing gives, why the
1 s attempt was so hard, and what moves on the rig.

## Inputs

- Close tile, 1/4 s: `D:/StrehlCaptures/stack-1795476520452-8651` (153 planes, step 13,
  focus 62800 to 60830, ISO 100, four-shot; 190 groups, 37 retakes of which 23 by hand).
  Owner's render: `C:/Users/chris/Pictures/Strehl/strehl-1795477911678-55588-0`.
- Close tile, 1 s, stopped: `stack-1795478933629-8651` (24 of 46 planned planes, 95 groups,
  51 manual and 21 automatic retakes, 21 minutes).
- Stillness test: `stack-1795481648910-8651` (30 single shots at 1/8 s at focus 61845, no
  lens move between them) and two 60 s series of magnified live view (9.3x, about 6 frames
  a second) in scratch.
- This morning's life-size stack and the rig series of [results.md](results.md).
- Same engine copy and private cache as before. Half-stack renders have restoration off.
- Scripts are in this folder; text outputs in [evidence-close-tile/](evidence-close-tile/).
  Pictures and arrays stay in `C:/strehl-scratch/i-round/`.

Rig state after the stillness test (from its log): ISO 100, 1 s (the owner's setting at the
time), four-shot, magnifier off, camera and light off, "manage power" on, plan 61624 to
62202 step 13 unchanged.

## C1. What the closer framing gives

`object-detail.py`, [evidence](evidence-close-tile/object-detail.txt). MEASURED unless
marked.

- Magnification 2.83 times this morning's: the scale lattice repeats every 42.7 px against
  15.1 px. One scale is about 32 px wide.
- Signal against noise at one detail size on the subject (cycles per scale spacing, signal
  from the odd and even half-stacks):

| Cycles per scale spacing | Close tile | Life size |
| --- | --- | --- |
| 4 | 198 | 90 |
| 6 | 71 | 23 |
| 7 | 53 | 9.8 |
| 8 | 43 | beyond its pixels |
| 12 | 15.7 | beyond its pixels |
| 16 | 3.7 | beyond its pixels |

- The life-size stack runs out of pixels at 7.5 cycles per scale spacing. The close tile
  holds signal above noise to between 12 and 16. About twice the real detail.
- The restoration's cutoff fit succeeded on this stack: green 0.588 cycles/px. DERIVED: a
  working aperture of about f/12 and an object-side aperture of about 0.12. The plan had
  derived 0.089. The fit is biased by other blur (see C4), so the lens may be better still.
- The render sits at a tone white of 0.178, about 2.3 stops under. 63.8 % and 26.8 % of
  the two finest bands were averaged as noise.

Instrument caveat: half-stack signal counts sensor pattern and election-made detail.

## C2. One second against a quarter

`group-snr.py`, [evidence](evidence-close-tile/group-snr.txt). One four-shot group against
another at the same focus position; signal is the cross-spectrum of the two green samples
each photosite gets, noise the rest. MEASURED.

A trap first. Glints pinned in the longer exposure lose modulation, and that reads as lost
signal: without matching the clipping, a 1.3 s group at life size seems to keep only 0.51 to
0.61 of a 1/4 s group's fine signal. With the shorter exposure clamped at the same
radiance, it keeps 0.91 to 1.00. Every exposure comparison below is clip-matched.

| | Light | Fine signal power kept (0.15 to 0.40 cycles/px) | Signal over noise |
| --- | --- | --- | --- |
| Life size, 1.3 s against 1/4 s | 5.3 times | 0.91 to 0.99 | 3.3 to 3.8 times |
| Closest focus, 1 s against 1/4 s | 4.0 times | 0.65 to 0.82 | 2.1 to 2.7 times |

- Controls: two 1/4 s groups at one position agree within 4 % in signal at life size. Two
  1/4 s groups one focus step apart differ by up to 1.4 times in the finest bands, so the
  6-unit focus offset inside the closest-focus pair matters; the tiles were chosen by the
  1 s group, which favours it.
- So a 1 s exposure at closest focus is softer by about 0.3 to 0.4 px of blur. Not at life
  size.

## C3. Why the plane check failed so often at 1 s

`checker-relation.py` on `strehl pixel-shift --json` reports,
[evidence](evidence-close-tile/checker-relation.txt). MEASURED.

- The check's reason for every automatic retake was "witness tiles disagree locally"
  (tile ratio p99 over median z squared at or above 2.5).
- For one offset between the four shots, that ratio is far higher at 1 s:

| Offset between shots | Tile ratio at 1 s | Tile ratio at 1/4 s |
| --- | --- | --- |
| under 0.15 px | 1.52 | 1.28 |
| 0.15 to 0.25 px | 1.88 | 1.31 |
| 0.25 to 0.40 px | 4.49 (one group) | 1.52 |
| 0.40 px and over | 7.66 | 1.92 |

- Fitted: ratio minus one is 22.6 times the offset squared at 1 s and 4.3 times at 1/4 s.
  The 2.5 threshold is reached at 0.26 px at 1 s and at 0.59 px at 1/4 s. The ratio of the
  two fits (5.3) is close to the exposure ratio: the check measures how statistically
  clear a mismatch is, and that grows with light.
- The offsets themselves are not larger at 1 s: median 0.28 px over 149 groups at 1/4 s
  (109 at or above 0.2 px); median 0.18 px over the 20 surviving groups at 1 s.
- Whole-pixel slips ("offsets do not cover the four CFA parities"): 4 of 24 groups at 1 s,
  4 of 153 at 1/4 s.
- In my render of the stopped capture 8 of 24 planes fell back to one shot, and
  restoration was skipped (25 of 27 in-focus tiles near clipping).
- Between tries of one plane the picture sits 0.1 to 2.5 px away (`drift.py`): each try
  re-approaches the focus position. A manual retake took 47 to 73 s.

The stopped capture's folder passes the desktop's own `verify_stopped` (380 RAWs, 24
planes: VERIFIED by reading the function against the receipts). Why the Capture station
did not offer it for stacking was not traced.

## C4. What moves

`stillness.py`, `still-analyse.py`, [evidence](evidence-close-tile/stillness.txt). The
desktop was closed; nothing on the rig was commanded to move. MEASURED.

| | Whole-picture motion about its drift, rms | Largest | Tiles against each other |
| --- | --- | --- | --- |
| RAW burst, 30 frames over 88 s | 0.18 px along x, 0.46 px along y | 1.8 px | 0.05 px |
| Live view, first minute | 0.24 px, 0.52 px | 1.5 px | 0.20 px (four quadrants) |
| Live view, three minutes later | 0.25 px, 0.62 px | 2.0 px | 0.21 px |

- The picture moves as one piece: tiles agree to 0.05 px while the whole frame moves
  0.49 px. This is the camera against the subject, not air shimmer and not parts of the
  insect flexing.
- It is mostly along the picture's vertical axis.
- Part of it is a steady oscillation: 0.35 to 0.41 px amplitude at 2.6 Hz in both live
  series. Live view arrives 6 times a second, so 3.6, 8.9 or 9.9 Hz would look the same.
  The RAW burst's frames (1/8 s) still scatter by the full amount, which argues for the
  slower values (ARGUED).
- Slow drift on top: 1.7 px in the first minute after a 150 s warm-up, 0.8 px in the
  minute three minutes later, 1.6 px over the burst between them.
- On the subject, 0.5 px is about 0.65 um. At life size the same sway is 0.18 px.

## C5. The sway is in the finished pictures

`aniso.py`, [evidence](evidence-close-tile/anisotropy.txt). Signal power of detail that
varies along y over detail that varies along x, from half-stacks. MEASURED.

| Band, cycles/px | Close tile, 1/4 s | Life size, 1/4 s | Close tile, 1 s (24 planes) |
| --- | --- | --- | --- |
| 0.10 to 0.20 | 0.51 | 0.74 | 0.34 |
| 0.20 to 0.30 | 0.39 | 0.75 | 0.12 |
| 0.30 to 0.40 | 0.32 | 0.86 | 0.03 |

- In the finished 1/4 s close tile, fine detail along the vertical axis has about a third
  of the strength of detail along the horizontal one. DERIVED: that is an extra blur of
  about 0.49 px along y, which matches the sway measured in C4.
- The scales are round, so the subject itself should not favour an axis; the life-size
  stack's 0.74 to 0.86 is the reference for what subject and optics contribute.
- At 1 s the vertical detail is nearly gone. That stack is partial and has eight planes
  reduced to one shot, so read the direction of the result, not its size.

## What it means

- The lens at closest focus is worth tiling with: twice the real detail, and that with a
  third of the vertical detail missing.
- The sway is the largest loss at this magnification. A 1/4 s exposure already spans most
  of a 2.6 Hz cycle, so shortening the exposure does not help until about 1/30 s.
- The plane check has to stop depending on exposure before any capture is taken brighter.

## Not measured

- The sway's true frequency and its source on the rig.
- Whether the life-size stack's mild anisotropy is the same sway.
- The close tile with a longer exposure and the sway removed.
- The two-pixel mesh seen beside one clipped glint in the owner's close-tile render: cause
  and extent.

# Grounding the capture planning design: brief

**Opened:** 2026-11-27, at the owner's direction ("ground it in reality first … feel free to
experiment with the rig … verify everything … don't over index on the current subject").
**Design under test:** [the capture planning proposal](../../../docs/proposals/2026-11-capture-planning-flow.md).
**Ledger:** not allocated. The checkout this was written in is 42 commits behind
`origin/main`; the row `cpf-grounding-2026-11-27` is to be added on `main` with the
proposal's other rows (its section 14).

## Questions

| # | Question | Consumer |
| --- | --- | --- |
| G1 | On the dragonfly, do the measures the product uses call blur and highlights "in focus"? What is the true sharp range, tile by tile? | Bounds offers; the depth rail; the outline |
| G2 | Is there a measure that separates focus from bright blur on one RAW frame, on a sparse set, and on live view? Does it hold on other subjects? | The calibration pass; the plane checker |
| G3 | Why did the dragonfly stack's highlight groups not reach the picture, and what would make them? | Highlight fusion |
| G4 | What does a proof plane report, and does waiting after the light comes on change its verdict? | The proof plane, the rest gate |
| G5 | How long does a live sweep take, and how well does it locate the subject's range? | Finding the range |
| G6 | Are the proposal's other additions true on real data: glints local in depth, the sharp depth against tile size, retention from thinned curves, the final frame? | Section 16 and 17 of the proposal |

## Inputs

- The owner's dragonfly stack `D:/StrehlCaptures/stack-1795713444768-14989` (151 planes at
  step 8, four-shot, 1.3 s with highlight groups at 1/40 s on every second plane) and its
  render in the owner's catalog. Read only.
- Seven other A7CR stacks in `D:/StrehlCaptures` (weevil, scarab, a close tile and four
  more), read only, for generality.
- The rig with the dragonfly on it: test runs only (`capture_positions`, kind `test`, one
  position a run), which the owner's desktop neither follows nor lists, and live view.
- Installed build `desktop-91cc19f0619a9ac4` (`strehl-cli.exe`), source `origin/main`
  `b2c8a07aa`.

## Controls, stated before use

- A focus measure must give no in-focus tiles on planes where nothing is in focus (the
  stack's first and last planes, checked by eye in native crops) and on the backdrop.
  It must find tiles whose focus is confirmed by eye. Gradient energy alone cannot do
  this; that is the failure under test.
- Truth for "in focus" comes from all 151 planes, not from the measure being judged: a
  tile's narrow fine-band peak, cross-checked against native crops.
- An exposure ratio measured between two frames must be the same at every brightness
  level (a black-level error shows as a trend).
- Rig timings are taken with the owner's settings; anything changed is put back and the
  record says what was changed.

## Bounds and stopping

Outputs and caches live in `C:/strehl-scratch/plan-flow/` (pictures of the owner's subjects
never enter Git). No product code is changed in the owner's installation; an engine
prototype, if needed, is built in a separate worktree and not installed. Test runs made
on the rig are deleted after their summaries are taken. Stop when each question has a
measured answer or a stated reason it cannot be answered tonight.

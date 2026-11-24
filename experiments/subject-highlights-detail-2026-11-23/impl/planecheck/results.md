# Plan Q5: the four-shot plane check, judged in pixels

Ledger row `shd-q-planecheck-2026-11-23`. Branch `studio2/shd-planecheck` from
`e09d0593f`. Author-run, not independently reviewed. Labels: MEASURED, VERIFIED, DERIVED,
ARGUED, UNVERIFIED.

## The rule

- **Whole-group offsets are lined up, not judged.** The assembly already compensates each
  shot's measured sub-photosite offset (`STREHL_PIXEL_SHIFT_RESIDUAL=compensate`, the
  default since 2026-11-16). The whole-group gate on what compensation leaves (0.2 px) is
  unchanged.
- **Local disagreement is judged in photosites.** The green witness now keeps, per 64 px
  tile and witness pair, the regression sums it already computed. With the pair's
  whole-group shift taken out, the leftover is expressed as the displacement that would
  cause it: `sqrt(max(0, leftover - noise) / (gradient energy / 2))`
  (`pixel_shift::Witness::tile_local_px`). The check judges its p99 over tiles with at least
  64 regression sites against `LOCAL_TOLERANCE_PX` = 0.3 x the lens's blur width
  (1.7 px, `1.03 / cutoff` at the fitted 0.588-0.616 cycles/px) = 0.51 px. Signal,
  gradient energy and leftover scale together with light, so the value does not.
- The old tile ratio (p99/median z^2 >= 2.5) is no longer judged; it is still reported
  and was drawn in the plane view, which now draws the new map.
- **Whole-photosite slips ask for a retake.** A parity failure now asks for one when a shot
  registers on the scene and the camera shifted at all ("a shot slipped by a whole
  photosite"); a flat scene or an unshifted camera still does not.
- A local fault that also spoils a shot's whole-frame fit reads "disagree locally" (retake)
  rather than "too little scene structure" (no retake).
- `GROUP_CHECK_VERSION` 1 -> 2: journaled measurements are measured again once.

Choice of fraction: ARGUED. Fault-free groups read about 0.2 px; on the scarab,
whole-frame misregistration of 0.1-0.3 px cost nothing measurable and 0.2-0.6 px cost 10 %
of the fine detail; the smallest planted fault reads 1.0 px.

## Gate

Commands: [run-gate.sh](run-gate.sh) (`strehl pixel-shift --all-groups --json`, then
`strehl stack <run> --merge pyramid --srgb` with `STREHL_PIXEL_SHIFT=remosaic`, private
`STREHL_CACHE_DIR` per arm, `STREHL_GROUP_JOURNAL=off`), base engine built from
`e09d0593f`, new engine from this branch. Rule 45's `STREHL_WARPMAP` could not be used:
`strehl align` solves all 380 RAWs of a four-shot capture and the stack refuses the map;
each arm solved its own map in its private cache, and the capture folders gained no file
(VERIFIED by listing). Analysis: [planecheck-relation.py](planecheck-relation.py),
[verdict-changes.py](verdict-changes.py), [tile-clusters.py](tile-clusters.py),
[compare-renders.py](compare-renders.py). Text outputs in [evidence/](evidence/).

1. **Same offset, same verdict at 1/4 s and 1 s.** MEASURED, every group of both captures
   ([relation](evidence/relation.txt)). Median local p99 by offset between the shots,
   1 s against 1/4 s: under 0.15 px 0.208 / 0.205; 0.15-0.25 px 0.207 / 0.210;
   0.25-0.40 px 0.250 / 0.258. The old ratio in the same bins: 1.52 / 1.28, 1.94 / 1.31,
   3.88 / 1.53. New local failures: 1 s 0 of 55; 1/4 s 6 of 163 (5 at offsets 0.82-0.96 px,
   where first-order removal leaves 0.52-0.63 px, and plane 147, below).
2. **Stopped 1 s capture, no plane reduced to one shot under the tolerance.** MEASURED
   ([renders](evidence/renders.txt)). Base engine: 8 of 24 planes at one shot (planes 7, 15,
   17, 21 for tiles; 19, 22, 23, 24 for parity). New engine: 4, all whole-photosite slips.
3. **A planted one-pixel slip still fails.** VERIFIED on real groups (1 s planes 10 and 18;
   1/4 s planes 74 and 100; [plants](evidence/plants.txt),
   `cargo test --release -p strehl-cli --lib planted_faults_on_real_groups -- --ignored`):
   one shot moved one row up or down fails on parity and asks a retake. Also planted: a
   768 px patch of one shot moved 1 px reads 1.01-1.19 px, moved 2 px 2.14-2.37 px (one of
   four instead pulled the shot's whole-frame fit onto the next photosite: slip, retake);
   one shot from the next focal plane 1.10-1.68 px. Every plant fails with a retake; every
   unplanted group passes at 0.20-0.22 px.
4. **Weevil default render.** VERIFIED: pixels identical, base against new
   (`numpy.array_equal`); the files differ only in the `Software` tag (build identity). No
   verdict changed among its 199 groups.

## Verdict changes

[verdict-changes](evidence/verdict-changes.txt). Old verdicts are reconstructed from the
report's tile ratio (self-fitted noise model); on the 1 s capture they match the base
engine's render log exactly (planes 7, 15, 17, 21).

- Stopped 1 s capture, groups the stack uses: planes 7, 15, 17, 21 now assemble.
- 1 s, every group: 39 tile failures now pass (would not have been retaken). 40 parity
  failures now ask a retake.
- 1/4 s, every group: 9 tile failures now pass; one pass now fails, plane 147's only group:
  0.76 px, with 135 of its 366 measured tiles at or above 0.5 px along the subject's
  outline ([tile-clusters](evidence/tile-clusters.txt)). The old ratio missed it because
  the disagreement covers a third of the measured tiles, which lifts the median too. Its
  cause and whether assembling it harms the picture: UNVERIFIED. Among the groups that
  1/4 s stack uses, plane 147 is the only change.
- Weevil: none.

## Checks

- `cargo test --locked -p strehl-core`: 800 passed. `-p strehl-ui`: 1539 passed.
  `-p strehl-cli --no-fail-fast`: pixel-shift tests pass, the byte-freeze renders still
  produce their recorded bytes; 13 `merge_cmd` experiment controls and the `Command::Stack`
  doctest fail, as they do on the base tree (VERIFIED, same commands there).
- `cargo clippy --all-targets --no-deps -- -D warnings`: `strehl-ui` clean; `strehl-core`
  and `strehl-cli` report the same count as the base tree, none in the files changed here.
- `cargo fmt --check`: no difference in the files changed here; the base tree's
  differences elsewhere are unchanged.
- New tests: `the_same_offset_gets_the_same_verdict_at_any_exposure` (the old ratio passes
  the dim group at 2.36 and fails the bright one at 4.75; the new value reads 0.146 and
  0.169 px), `motion_in_one_part_of_the_frame_fails_at_any_exposure`,
  `a_whole_photosite_slip_fails_and_asks_for_a_retake`, the ignored
  `planted_faults_on_real_groups`, and `a_slipped_shot_is_retaken_and_named` (desktop).
- The desktop's plane view was exercised only through its headless tests, not live.

## Not done

- The 1/4 s close tile was not re-rendered; its stack-used verdicts were compared from
  reports only (DERIVED).
- No rig run: retake load under the new slip rule (up to two per slipped plane) is
  unmeasured. The Pi host needs no change (it reads `retake` only).
- The local value still rises with the offset (slope 0.2-0.4 px per px), from first-order
  removal with a 2 px gradient stencil. It is the same at both exposures.

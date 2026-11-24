# Plan D2, D3 and the subject's tone placement

Ledger row `shd-d-detail-2026-11-24`. Plan: [subject, highlights and detail](../../../../docs/proposals/2026-11-subject-highlights-and-detail-plan.md),
section 7 (D2, D3) and the "tone placement at the write" rows of S4 and X6. Branch
`studio2/shd-detail`, base 7b786abae. Author-run, not independently reviewed.

Labels: MEASURED (a command here produced the number), VERIFIED (a check that could fail
passed), DERIVED, ARGUED, UNVERIFIED.

## What was built

- **D2, restoration strength** (`strehl_core::optical_restore::choose_sigma`, used in
  `merge_cmd/optical-restore.rs`): candidates 0.70 to 0.35 px in 0.01 px steps, each through
  the Q2 floor (`design_response`). Each candidate's designed noise rise in 0.30-0.50
  cycles/px is `sum G^2 N / sum N` over a 128 x 128 frequency grid under green's measured
  noise spectrum (the half-stacks', as before). The sharpest candidate within the budget B
  is taken (the widest if none fits). One target for the three channels, chosen on green:
  the write's 1 px chroma smoothing hands red and blue green's finest bands (ARGUED; the
  flat tiles' luminance rise equals green's below). `STREHL_OPTICAL_RESTORE_SIGMA` still
  forces a target.
- **Detail control:** `stack --detail natural|safe|crisp|B` (published as `STREHL_DETAIL`).
  `natural` is the earlier fixed 0.70 px target with no budget; `safe` B = 1.7 (default,
  owner's decision); `crisp` B = 3.3; a number 1.0-6.0. The log gives the chosen target, the
  budget, and per channel the designed and kernel-delivered noise rise and the signal's
  amplitude gain at 0.1-0.2 / 0.2-0.3 / 0.3-0.4 / 0.4-0.5 cycles/px.
- **Desktop:** `RenderSettings.detail` (serde default Safe, so older recipes load as Safe),
  `--detail=` passed only when not Safe (like `--fix-ca`). The Stack station's Develop section
  shows "Detail" with a ruled three-way segmented control (`develop_station::style::seg`),
  Natural / Safe / Crisp, and one plain sentence for the chosen strength. The agent interface
  accepts `detail`.
- **D3, the highlight guard:** the restoration is held back around merged samples at or
  above 0.95 of the raw pin (16383 - black, `strehl_core::clip::CONTAINER_MAX_DN`; 15871 DN
  over black on the A7CR) instead of above 0.80 of the white level (0.75 of the pin). Same
  dilation (5 quads) and blur. The spectrum tiles' selection is unchanged (`CLIP_FRACTION`).
- **Tone from the subject** (`image_out/tone-subject.rs`, wired into `write_rgb_full` and the
  full-resolution mosaic write): when the capture's `manifest.json` has `plan.subject`, or
  `stack --subject <json>` gives one (`strehl subject --json` output or a manifest; `off`
  disables), the white is placed on the subject's diffuse top: the 99.9th percentile of the
  developed brightest colour over the subject's quads, highlights set aside, at 0.85; and
  `Tone.shoulder = 0.80` rolls the brightest colour off above 0.80
  (`strehl_edit::highlight_shoulder`: slope one at the knee, chromaticity kept, never reaching
  one). Highlights set aside: (a) pinned quads (a camera colour at 0.95 of the matrix's
  saturation ceiling) and every quad within 4 of one; (b) quads brighter than 2 x their
  neighbourhood's diffuse level (largest 75th percentile of 16-quad blocks, 3 x 3 around).
  The frame's black point is kept. The shoulder is recorded in the master's
  `DisplayBaseline` (`shoulder`, omitted when none, so the description's bytes are unchanged
  without a subject) and applied by the desktop's SDR view after its development; the HDR
  rendering keeps the headroom. Region-only repairs pin it from the original's baseline.

## Gates

Release builds, default features (GPU fold auto), 32 logical CPUs, other agents possibly
building on the machine. Base binary 7b786abae (SHA-256 7a7736a85c3f...), new binary
52d812913e09... (both report `strehl 0.1.0-alpha.6 (7b786abae637)`; the tree was dirty). Every
render through [render.py](render.py) (the desktop's arguments and environment, a private
`STREHL_CACHE_DIR` shared by the arms, capture folders checked unchanged after each render).
Arms: `base` and `off` (base binary, restoration on / `STREHL_OPTICAL_RESTORE=off`);
`newoff`, `natural`, `safe` (no flag), `crisp`, `safe2` (`STREHL_DETAIL=safe`, a re-render),
`subj` (`--subject=<strehl subject output>`), `subjoff` (`--subject=off`). Full log extract:
[gate-logs.txt](gate-logs.txt) (`summarise.py`).

### D2: chosen target, noise cost and amplitude (MEASURED)

Green, from the render logs; "flat tiles" is [noise-rise.py](noise-rise.py)
([noise-rise.txt](noise-rise.txt)): 256 px tiles of the unrestored master holding noise, not
scene, the median over them of the restored over unrestored power at 0.30-0.50 cycles/px.
"Master" is [../band-gain.py](../band-gain.py) ([band-gain.txt](band-gain.txt)): amplitude over
the unrestored at 0.3-0.4 / 0.4-0.5 cycles/px on the brightest half of the tiles (signal and
noise together).

| Stack | Arm | Target | Designed / delivered rise | Flat tiles (n) | Flat / B | Master 0.3-0.4 / 0.4-0.5 |
| --- | --- | --- | --- | --- | --- | --- |
| Weevil | safe | 0.55 px | 1.64 / 1.58 | 1.598 (278) | 0.94 | 1.272 / 1.290 |
| Weevil | crisp | 0.44 px | 3.28 / 3.16 | 3.371 | 1.02 | 1.584 / 1.836 |
| Scarab | safe | 0.53 px | 1.64 / 1.61 | 1.652 (3) | 0.97 | 1.195 / 1.183 |
| Scarab | crisp | 0.41 px | 3.24 / 3.16 | 2.968 | **0.90** | 1.471 / 1.577 |
| Harlequin | safe | 0.56 px | 1.68 / 1.62 | 1.622 (230) | 0.95 | 1.286 / 1.310 |
| Harlequin | crisp | 0.46 px | 3.20 / 3.02 | 3.021 | 0.92 | 1.593 / 1.878 |
| Lanternfly | safe | 0.47 px | 1.65 / 1.60 | 1.583 (273) | 0.93 | 1.341 / 1.204 |
| Lanternfly | crisp | 0.35 px (floor) | 2.93 / 2.83 | 2.870 | **0.87** | 1.661 / 1.723 |

- The flat tiles' rise equals the kernel-delivered prediction within 0.94-1.07 on every arm
  and stack, including natural/base (0.96-0.98 against 0.96-0.97 delivered). VERIFIED.
- Within 10 % of B: all four at safe; weevil and harlequin at crisp. The scarab's crisp
  reads 0.90 on 3 tiles (its backdrop is clamped at zero, so few tiles qualify; delivered
  predicts 0.96). The lanternfly's crisp ran to the sharpest candidate with its budget unspent
  (designed 2.93 < 3.3), so it cannot reach B. The safe arms sit 3-7 % under B: the 0.01 px
  grid and the kernel's 0.96-0.98 delivered fraction (the search uses the design).
- Failing control: base and natural read 0.96-0.98, nowhere near 1.7 or 3.3.
- Weevil anchors: safe gives 1.27 / 1.29 fine amplitude (plan: 1.3), crisp 1.58 / 1.84
  (plan: 1.6-1.8), at 0.55 and 0.44 px rather than the plan's 0.50 and 0.40: the plan's
  anchors were measured before Q2 floored the response, on a different baseline (DERIVED).
- Red's own rise is larger (safe 2.0-2.4, crisp 4.0-4.7, logs); the chroma smoothing makes
  the written fine bands green's: the flat tiles' luminance rise equals green's within 1 %.
- Re-rendering with another strength reuses the caches: every arm after the first reads the
  alignment from the cache (`align-result source=cache`) and the group journal reuses every
  measurement (`25 / 174 reused, 0 measured`). VERIFIED in the logs.

### D3: what the guard holds back (MEASURED, same 0.70 px target: base vs natural)

| Stack | Before (0.80 of white) | After (0.95 of the pin) | Sites at the pin |
| --- | --- | --- | --- |
| Weevil | 1.81 % | 0.77 % | 0.0030 % |
| Scarab | 1.54 % | 1.23 % | 0.1394 % |
| Harlequin | 0.11 % | 0.01 % | 0.0000 % |
| Lanternfly | 0.31 % | 0.11 % | 0.0062 % |

The weevil's restored share rises by 1.04 % of the frame, the scales around its unpinned
glints. Natural differs from base only by the guard; on the harlequin, whose guard was
already small, the master's band amplitudes agree to three decimals.

### Tone from the subject (MEASURED; subjects from `strehl subject <run> --out`)

| Stack | Subject | Set aside (pinned) | Diffuse top | White, frame rule -> subject | Subject median luminance, placed |
| --- | --- | --- | --- | --- | --- |
| Weevil | 36.0 % | 0.994 % (0.097 %) | 0.2836 | 0.25662 -> 0.33370 (-0.38 stops) | 0.01440: 0.056 -> 0.043 |
| Scarab | 43.8 % | 1.580 % (0.937 %) | 0.3731 | 1.18769 -> 0.43899 (+1.44 stops) | 0.01385: 0.012 -> 0.032 |

- The scarab's body renders 1.44 stops brighter, its pinned sheen rolled off by the shoulder.
  With the local rule alone the scarab's diffuse top was the pin itself (1.0689, white
  -0.08 stops): its sheen is pinned over 0.28 % of the subject and broad enough to raise
  whole blocks ([setaside.txt](setaside.txt), [subject-dist.txt](subject-dist.txt)). Hence the
  pinned rule.
- The weevil gets darker. Its frame white was not set by glints (they are 0.003 % of sites):
  its brightest diffuse colours are saturated blue scales (the brightest 1 % median
  saturation 0.91), whose brightest colour is 1.3 to 1.7 times their luminance, so placing
  the brightest colour at 0.85 lowers white. Under the frame rule those scales' blue channel
  went past 1 and was desaturated by the gamut map. Whether the owner prefers that is
  UNVERIFIED (no look at native crops).
- Without a subject the write is unchanged: `newoff` (this binary) equals `off` (base) byte
  for byte, photograph and master, on all four stacks; `subjoff` equals `safe`; `safe2`
  equals `safe`; the `subj` master's pixels equal `safe`'s (only its description records the
  tone). VERIFIED.

## Tests (VERIFIED)

`cargo test --locked -p strehl-core --lib optical_restore` (14, incl. the budget's choice and
white noise through a designed kernel matching `kernel_response`'s predicted rise within 5 %);
`cargo test --locked -p strehl-cli --lib -- tone_subject optical_restore image_out region_only`
(48); `cargo test --locked -p strehl-edit` (all); `cargo test --locked -p strehl-ui --bin
strehl-ui -- jobs:: controls agent` (141). Clippy `-D warnings` on core, edit, cli, ui: no
finding in the changed code (core and cli keep their earlier findings elsewhere).

Desktop: `python scripts/strehl-control.py --exe target/release/strehl-ui.exe screenshot
--source D:/StrehlCaptures/stack-1795460665629-8651 --route stack --catalog <scratch>
--output-dir <scratch> --png <scratch>/stack.png --size 1680x1050` (exit 0, capture folder
unchanged): the Stack station's Adjust tab shows "Detail" with the ruled Natural / Safe /
Crisp control, Safe chosen, and its sentence beneath. The control was not clicked and no
render was started from the desktop (the `--detail=` argument is covered by the jobs test).
The sentences were reworded after the screenshot (fine-detail gains instead of targets).

## Not done / open

- The scarab's crisp arm on 3 flat tiles and the lanternfly's crisp at the candidate floor;
  a wider candidate range (below 0.35 px) was not tried.
- The search uses the designed gain; using the kernel's delivered response would put the
  safe arms nearer B (they sit 3-7 % under).
- Subject tone on the half-size (binned) and session writes: not wired (frame rule there).
- The outline is mapped to the output as drawn (no per-plane magnification); about 1 %
  scale drift over the weevil's depth (ARGUED from -13 ppm per focus unit).
- After plan X4, the guard should read X4's list of sites still pinned rather than a level,
  since fused values may exceed the pin legitimately.
- No look at native crops by the owner: the shoulder's knee (0.80) and the 0.85 target are
  ARGUED, not chosen by eye.

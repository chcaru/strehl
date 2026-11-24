# X4: highlight fusion at the gather — implementation and gates

**Status:** built 2026-11-24 on `studio2/shd-x4` from 7b786abae (ledger row
`shd-x4-fusion-2026-11-24`). Plan: `docs/proposals/2026-11-subject-highlights-and-detail-plan.md`
X3, X4, X7. Capture format: `../tiers.md`.

## What was built

- **Identity** (`pixel-shift-cmd.rs`). `all_groups` reads `tier` per file, else per event
  (`data.tier`), absent = base, and the commanded `data.exposure.shutter`. `plane_groups`
  keeps the last complete **base** group per plane, so a highlight group under its base
  group's plane number never replaces it; `tier_groups` gives the highlight groups.
  `highlight_plan` reads `manifest.json` `plan.highlight`; `shutter_seconds` decodes Sony
  codes. A `shadow` (any other) tier is recorded and not used.
- **Companions** (`highlight-fusion.rs`, `companions`). Each complete four-shot base plane
  in the stack gets its own plane's highlight group, or with `every` > 1 the nearest
  plane's within `every - 1` (ties to the lower plane). The companion is placed by the
  placement of the base frame of *its own* plane plus its measured shift against that
  frame's member 1 (same visit). Installed per render; banner line `highlights      : ...`.
- **Ratio.** Starts from the commanded shutter ratio (`STREHL_HIGHLIGHT_RATIO_PLANT`
  multiplies it, a gate hook), corrected by the session pipeline's bounded fit, restated
  here because `session-photometry.rs` is compiled only with `multi-stack`: up to 64
  patches of 32 x 32 quads where the base is below 0.70 of the pin and the companion
  has signal, alternating fit / held-out, trimmed means per CFA plane, 8 sigma of the
  injected model on both, median log ratio, **at most 0.25 EV** of correction, held-out
  residuals within 1 / 3 / 5 %, textured agreement within 0.1 of the texture's power.
  One deviation: the textured-patch eligibility uses the model's variance without the
  session's 16x allowance (its passes lie within ~1 EV; at 3-4.3 EV no weevil patch
  qualified, MEASURED 0 of 32 on two fixture planes). A refusal leaves the plane its base
  exposure and is logged once (`highlights      : plane N: ...; this plane is the base
  exposure alone`).
- **Where.** Per output site (4 CFA sites, plus the 8 carried channels when colour carry
  is on, the default for four-shot stacks), the brightest raw sample (red, two greens,
  blue of the four members) over the Catmull-Rom footprint of the site's pull plus a
  2-photosite guard (2 more for a demoted base: Malvar's stencil); weight =
  smoothstep from 0.75 to 0.90 of the raw pin (16383 - black). All colours of a
  photosite switch together.
- **Value.** The companion gathered through the same banded gather
  (`align_cmd::gather_companion`, only the bands and columns holding replaced sites),
  through its own placement, times the ratio. Same-visit shift: `pixel_shift::register`
  (block-luma Lucas-Kanade, as member offsets are measured) on both member 1s clipped at
  0.6 of the pin, the companion scaled by the data's ratio.
- **Storage.** Sparse per-frame list `(plane, index, w, v)`, applied as
  `p = p * (1 - w) + v * w` when the planes are lifted to f32: CPU after extraction and
  the carried copy (`merge_cmd::load_frame_impl_observed`), GPU in preparation after the
  gather and before the restoration crops, luma and variance (`strehl-gpu`: a read-only
  `patches` binding 9, kernels `patch_planes` and `patch_variance`, a region per frame
  slot). u16 frames untouched.
- **Noise.** Patched luma pixels: `0.25 * sum_g [(1-w_g)^2 var_g(L) + w_g^2 k^2 var_g(L/k)]`
  with the injected model (`fused_variance`, identical on CPU and GPU).
- **Election.** Untouched (no clip mask, M54).
- **Writer.** `Render::with_fused_headroom` (strehl-core `color.rs`) multiplies the
  saturation ceiling by the smallest ratio of frames that replaced sites, so a sample is
  neutralised only where the companion pins too. No fused sites: nothing changes.
- **Demoted groups** (needed on the rig, where 17 of 21 base groups failed their check):
  a demoted base frame is fused as its member 1 (Malvar); a demoted highlight group is
  used as its member 1 alone.
- **In-capture checker** (`follow-cmd.rs`). Every journal line carries `tier`; a highlight
  group is measured (group journal), never a retake, never an alignment plane, verdict
  `"highlight"` (its own check in `group_verdict`), not counted in the plane list or
  "retaken". Plan X5 cue: `"pinned"` = member-1 CFA quads with any photosite at or above
  0.90 of the pin (where fusion replaces outright), inside `plan.subject` when present,
  and `"pinned_scope": "subject"|"frame"`. Follower file:
  `<cache root>/follow/<run name>-<hash>.jsonl` (`follow_cmd::journal_in`).
- **Switches.** `STREHL_HIGHLIGHT_FUSION=off` renders the base alone;
  `STREHL_HIGHLIGHT_REPORT=<path>` writes one JSON line per planned frame.

## Gates (engine 445e4690..., `bin/new.exe`; base 7b786abae, `bin/base.exe`)

Commands: `final-gates.sh` here (identity, `gates.sh`, fixture, follow). Scratch was
`C:/w/shd-x4-out`; text evidence is in `evidence/`.

| Gate | Result | Label |
| --- | --- | --- |
| No tiers: weevil `stack-1795460665629-8651`, scarab `stack-1795300522964-6430`, default four-shot render | TIFF SHA-256 identical, base vs new (`identity-sha256.txt`) | VERIFIED |
| GPU patch kernels = CPU | fused sensor master, GPU fold vs `STREHL_GPU_FOLD=off`: identical SHA-256 (`gpu-cpu-sha256.txt`) | VERIFIED |
| Pinned sites where the companion is not pinned | every fused plane: 0 sites with a pinned sample in their footprint left without weight 1 and a companion value (`pinned_not_fully_replaced`), rig every-1, every-2 and fixture | VERIFIED (plane level) |
| Hand-over (green at 0.50-0.75 of the pin, scaled companion / base) | fixture 0.9982-1.0000, spread 1.8-2.0 %; rig every-1 0.975-1.005 (median 0.995), every-2 0.981-1.005 (median 0.990), spreads 1.5-5.6 % | MEASURED |
| Unpinned areas equal base-only | sensor masters, CA refinement, optical restoration and carry off in both arms: beyond 1024 px of bright sites all photosites within 0.15 DN (every-1) / 0.42 DN (every-2); within 512 px up to 6.5 DN (the pyramid's coarse bands reach that far) | MEASURED |
| Planted ratio error 5 % | 19 of 21 planes fused, ratio as unplanted within 0.01 (correction -0.03 to -0.12 EV) | MEASURED |
| Planted ratio error 25 % | 21 of 21 refused ("a correction of -0.29 to -0.37 EV, beyond the 0.25 EV bound") | MEASURED |
| Checker | highlight lines `tier: highlight`, `retake: false`; retake list from base groups only; `pinned` on every line | VERIFIED |

Rig, every plane: 17 of 21 fused (14 on a demoted base's member 1, all 17 on a demoted
highlight group's member 1), ratio 7.72-8.20 (commanded 8), shift -0.53..+0.73,
-1.83..+1.58 px; 4 refused by the textured check (sway between groups). Every second
plane: 12 of 21 fused (5 on the nearest plane's companion); refusals: 2 companions' shift
unmeasurable (structure 0.38, 0.79), textured or held-out disagreement. Fixture
(1.3 s + 1/15 s, three planes): 3 of 3, ratio 18.99-21.24 (commanded 19.5), shift
-0.26..-0.20, -0.24..-0.12 px.

At the output, of the base-only render's photosites at 0.98 of the pin or more, 30-68 %
per colour read above 1.02 of it fused (MEASURED); the rest sit near 1.0 in the fused
render too (median 0.99-1.21): refused planes keep their pinned samples, and part of
those sites' radiance is at the pin. Not resolved further (UNVERIFIED which).

## Checks

- `cargo test --locked -p strehl-cli --lib`: 305 passed, 13 failed (the 13 pre-existing
  environment-dependent `merge_cmd` experiment tests: gatefloor native probe and
  writeback controls, m194f, m194g); new tests `highlight_fusion::tests::*` (5) and
  `pixel_shift_cmd::tests::a_highlight_group_never_replaces_its_plane` pass.
- `cargo test --locked -p strehl-gpu -- --ignored` (device): all pass, including
  `the_gpu_fold_is_bit_identical_to_the_cpu_fold` and `twelve_planes_fold_bit_identically`.
- `cargo test --locked -p strehl-core --lib color`: 38 passed.
- `cargo clippy --locked -p strehl-cli -p strehl-gpu --all-targets --no-deps -- -D warnings`:
  the same findings, file for file, as the base commit (all pre-existing); strehl-core's
  clippy fails on pre-existing findings, none in `color.rs`.
- `rustfmt --edition 2024 --check` clean on `highlight-fusion.rs`, `follow-cmd.rs`,
  `pixel-shift-cmd.rs`, the strehl-gpu files; the changed hunks of `merge_cmd.rs`,
  `align_cmd.rs` and `color.rs` are formatted (those files carry pre-existing diffs).

## Cost (MEASURED, this machine, no other render running)

Rig every-1 default render: 21 s fused against 9 s with `STREHL_HIGHLIGHT_FUSION=off`
(final pass 14.1 s against 5.5 s). Fusion work on the fold thread 0.2-0.5 s a plane
(`seconds_load_shift_bright_ratio_sites_gather` in the reports): companion decode runs
on a background thread one plane ahead; the companion gather covers only the bands
holding replaced sites. Memory: up to 4 companions decoded (4 frames each) and one
companion gather scratch, released when the render ends.

## Remaining

- Owner look at native crops (base, fused, fused + "Tame glints") — not done.
- Tone placement for fused data (X6: white from the subject's diffuse level) — not mine;
  the writer only moves the ceiling.
- Later passes (`queue_pass`, R3) are treated as same-plane companions (shift measured
  against the plane's base group); not tested on a real follow-up pass.
- The textured check refuses swaying groups at the 0.1 limit (0.11-0.24 seen); the
  hand-over of swaying groups is 1-2 % low. Rig sway, not the fusion, decides here.
- The checker's `pinned` counts member-1 quads (consistent across demoted and assembled
  groups), not the fusion's four-member sites.
- `STREHL_SELF_FLAT` is not applied to the companion's gather.

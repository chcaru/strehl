# P8, first half: focus evidence for ordinary stacks (E5)

**Phase:** P8 of [Strehl Studio 2: implementation plan](../../docs/proposals/2026-11-desktop-studio-2-implementation.md)
(section 2 D6, section 8 E5, section 9 P8, section 12 "E5 memory").
**Date:** 2026-11-21. **Branch:** `studio2/p8-focus-evidence`, based on `91ebd7e70`.
**Evidence labels:** MEASURED, VERIFIED, DERIVED, ARGUED, UNVERIFIED, as in the plan.
No default was changed. The depth lens is not built; this half ships the engine switch, the
file records and a reader for the lens.

## Recommendation

**Keep focus evidence off by default.** It is affordable in memory and not affordable in
time.

- **Memory: affordable.** The pass reserves 453 bytes per quad pixel whatever the frame
  count. That is 3.48 GiB at the A7C II plane (MEASURED peak 3.47-3.96 GiB working set,
  3.92-4.78 GiB private during the pass) and 6.35 GiB at the A7CR plane (DERIVED). The pass
  runs after the render has freed its own memory, so at the A7C II the run's peak stays the
  render's (6.4-9.4 GiB working set). At the A7CR the pass is projected at about 6.9 GiB
  private (DERIVED below), well within this machine's 61.6 GB; whether it exceeds the
  A7CR render's own peak was not measured. The plan's risk ("about 6.5 GB at the A7CR
  plane") is confirmed in size and is not the blocker.
- **Time: not affordable as a default.** On the 299-plane weevil the pass took 215-319 s
  after a 9 s render (MEASURED, 19-51 % other-process load): 24 to 35 times the render.
  On the 1,444-plane bracket it took 923-1,393 s (15-23 minutes) after a 20-159 s render
  (MEASURED, 14-53 % other load). At the A7CR plane the per-frame cost scales with pixels,
  about 1.8 times: about 7-10 minutes for 299 planes and 28-42 minutes for 1,444
  (DERIVED).
- **Coverage is sparse, and on the long bracket empty.** On the weevil 3.8 % of pixels carry
  usable evidence; 629 of 10,880 areas (5.8 %) are a quarter usable, all on the subject
  (VERIFIED by eye on the scratch share map, not kept: it is the owner's picture). On the
  1,444-plane bracket 3,427 pixels (0.04 %) are usable and no area is a quarter usable: the
  field is written as not usable (reason 5). A depth lens drawn only where the evidence is
  usable would be a scatter over the subject on the short stack and absent on the long one.
  Most refused pixels carry the scale-disagreement and competing-mode flags (table below),
  so the evidence policy, not the cost, is what limits the lens. That needs its own look
  before the lens is built.
- **How it could become a default (ARGUED, not measured):** green-only gathering (the pass
  samples all four CFA planes and uses two), parallel folds in `FocusEvidenceBuilder` (its
  per-pixel loops are serial), and a decode window over one frame would cut the per-frame
  time; a coarser analysis grid would cut it far more but changes the operator's scale and
  needs its own validation against the full-resolution field. Until one of these is
  measured, offer it as an explicit action (like "Save confidence map"), or as a background
  activity after the render that the depth lens asks for.

## What was built

**A frame-loader abstraction for the shared pass** (`crates/strehl-cli/src/focus-pass.rs`).

- `FocusSource` (CFA rows, camera, ISO, levels) and `FocusFrames` (load by global index),
  `compute(frames, sweep, map, domain, noise, profile, budget, label)`,
  `reservation_bytes`, `complete_support`.
- `session_focus::compute_pass` is now a wrapper: the session's `SourceCache` behind
  `FocusFrames`, its pass's `global_range` as the sweep. The loop is the same code in the
  same order; `algorithm_sha256` now also hashes `focus-pass.rs`.
- `session-sampling.rs` (the native sampler the pass gathers with) is compiled without the
  `multi-stack` feature; nothing else of the session code is.

**`strehl stack --focus-evidence`** (`crates/strehl-cli/src/merge_cmd/focus-evidence.rs`).

- Off by default; pyramid backend only (refused under the estimator before a frame is read).
  `STREHL_FOCUS_EVIDENCE=on|off|placebo` does the same for a harness; the flag wins. The
  placebo runs the whole pass and writes nothing.
- It runs after the photograph and the linear master are written, once per render: the last
  finished non-preview attempt's inputs are kept (a restoration retry, the lateral-colour
  preview and calibrated fusion's two folds do not run it twice).
- Inputs are the render's own: its frames, warp map, analysis domain, level grids and
  injected noise model (one noise model, AGENTS). No optical profile: green is the
  reference channel, so `OpticalProfile::compose` leaves it alone (ARGUED from the code).
  A clamped resampler is refused, as the session pass refuses it.
- RAWs are decoded again, one frame ahead on a thread of their own, twice per placed frame
  (the builder's anchor and shape passes).
- Memory is checked first against `STREHL_FOCUS_EVIDENCE_MEMORY_GIB` (default 16, the
  sessions' default).
- A pass that cannot run or fails says why in the summary; it never fails the render. Codes:
  1 fewer than three frames, 2 not aligned, 3 memory, 4 failed (the error's text), 5 no area
  a quarter usable.

**The records** (appended to `<run>/evidence.strehl`; `ui-evidence.rs` documents them).

- All on level 0's lattice (at most 128 x 96, the plane maps' lattice), frame 0, with the
  format's largest sequences (`u32::MAX - 2 ..= u32::MAX`), after every plane map.
- Kind 4, focus depth: per area, the median measured acquisition ordinal of its usable
  pixels (`FocusEvidence::usable`), `f32 min, max` = `0, frames - 1`, one byte per area
  `0..=254`; 255 where no pixel of the area is usable. An order of planes, not a distance.
- Kind 5, focus share: per area, the share of usable pixels, `0..=255` over `[0, 1]`; at
  least 1 wherever a depth is stored.
- Kind 6, summary: `u8 format (1), u8 usable, u16 reason, u32 frames, u32 field width, u32
  field height, u32 usable pixels, u32 covered pixels, f32 seconds, u64 reservation bytes,
  u16 text bytes`, then the reason as UTF-8 (at most 1,024 bytes). The field is usable when
  at least one area is a quarter usable.
- Area `(i, j)` of a `w x h` lattice over a `W x H` analysis domain is pixels
  `[i W / w, (i + 1) W / w)` by `[j H / h, (j + 1) H / h)`.
- The render's file is joined (its own header); a render without the desktop's progress
  gets a new file with the merge's level grids.

**Old readers skip the new kinds (VERIFIED).** The desktop's `EvidenceDecoder` returns
`None` for any kind it does not know and counts it as skipped; it stops reading a file only
when a record declares more than `8 + 128 x 96` payload bytes, and the largest new record is
exactly that. Tests: `focus_records_are_skipped_by_the_maps_reader_and_read_by_read_focus`,
`the_largest_focus_record_keeps_the_maps_reader_reading`. No side file was needed.

**The reader for the lens** (`crates/strehl-ui/src/evidence-file.rs`).

- `read_focus(path) -> Option<EvidenceFocus>`: reads record heads and seeks over every
  other payload.
- `EvidenceFocus`: `lattice`, `extent`, `frames`, `usable`, `reason`, `reason_code`,
  `usable_pixels`, `seconds`, `reservation_bytes`; `ordinal(i, j)` (only when the field is
  usable and the area at least a quarter usable), `ordinal_with_share(i, j, min)`,
  `share(i, j)`.
- A usable summary without its maps, a torn record, or no field reads as `None`.

## Measurements

Harness: [`p8-focus-evidence-run.py`](p8-focus-evidence-run.py), the desktop's command and
environment as in P2 (`stack SRC --merge pyramid --srgb --out ... --linear-master ...`,
`STREHL_UI_PROGRESS=1`, `STREHL_GPU_FOLD=on`, `STREHL_TEMPORAL_ENERGY=off`, isolated
`STREHL_CACHE_DIR`), plus `STREHL_FOCUS_EVIDENCE`. The engine ran at below-normal priority;
memory is the OS's peak counters (`peak_wset`, `peak_pagefile`) and a 0.5 s sample of the
working set split at the first `focus evidence` log line. Captures were only read; outputs
went to scratch and the TIFFs were deleted after hashing.

Engines (release, `--features temporal-energy`, GPU default, this branch):

- `9ab14e27...` (first five 299-plane arms; depth stored only for areas a quarter usable).
- `b23ae160...` (depth for every area with a usable pixel; no refusal counts in the
  summary; a share rounding to zero not yet lifted to 1).
- `83d92ffd...`, the committed code (refusal counts in the summary).

Host: 32 logical processors, RTX 5090, 61.6 GB. Other agents were running throughout: other
processes used 31-78 % of the CPU on average and up to 100 %. Times are bounds on a busy host.

### 299 planes (A7C II, `bug-3\107MSDCF`, quad 3516 x 2344)

| Arm | Wall | Render (`total`) | Pass | Peak working set, run | Pass peak, working set / private | Other load mean |
| --- | --- | --- | --- | --- | --- | --- |
| off (cold) | 28.7 s | 10.9 + 8.2 s | | 8.69 GiB | | 49.8 % |
| on | 241.5 s | 3.7 + 8.3 s | 228.9 s | 6.70 GiB | 3.55 / 3.97 GiB | 31.0 % |
| placebo | 275.7 s | 2.3 + 5.2 s | 267.2 s | 6.57 GiB | 3.52 / 3.94 GiB | 44.9 % |
| off | 9.1 s | 2.2 + 6.5 s | | 6.38 GiB | | 32.5 % |
| on | 246.9 s | 2.5 + 5.3 s | 238.3 s | 6.65 GiB | 3.47 / 3.93 GiB | 31.2 % |
| on (`b23ae160`) | 314.9 s | | 303.8 s | 6.57 GiB | 3.51 / 3.92 GiB | 51.2 % |
| on (committed code) | 348.4 s | 2.2 + 27.0 s | 318.5 s | 6.43 GiB | 3.83 / 4.70 GiB | 45.8 % |
| placebo (committed code) | 224.2 s | 2.5 + 5.9 s | 215.1 s | 6.71 GiB | 3.96 / 4.78 GiB | 19.0 % |

(`total` has two figures: the lateral-colour preview, then the render.)

- **Output bytes (MEASURED, rule 26):** every arm, on, off and placebo, both engines: result
  `f29b2c9ff6b3bea1...`, linear master `9fd75acecd1d6b3f...` (the master P2 recorded).
- **Plane maps unchanged (MEASURED):** in every on arm the evidence file's bytes before the
  focus records hash to the off arm's whole file (`f03cff13...`, 2,472,248 B). Off and
  placebo files are identical. The focus records add 21,862 B.
- **The field (MEASURED):** 313,998 of 8,241,504 pixels usable (3.8 %); 7,985,600 covered;
  lattice 128 x 85; 629 areas a quarter usable, 3,442 with any usable pixel. The two on
  arms of `9ab14e27` gave the same depth and share maps.
- **Refusal flags (MEASURED, committed code), pixels of 8,241,504:** boundary 483,911;
  scale disagreement 6,161,814; competing mode 5,988,835; weak response 4,957,455; no local
  fit 4,255,362; missing coverage 1,277,218; unresolved mode 1,941,164 (a pixel can carry
  several).
- **Reservation (DERIVED, `the_reservation_is_set_by_the_plane`):** 3.48 GiB here;
  the measured private peak of the pass is 0.45-1.3 GiB above it (two decoded frames in
  the decode window, the process, and, ARGUED, memory the allocator had not yet returned
  from the render: the same build read 3.95 GiB on the 1,444-plane run and 4.70-4.78 GiB on
  the 299-plane runs).

### 1,444 planes (A7C II, `bug-7\100MSDCF`)

| Arm | Wall | Render (`total`) | Pass | Peak working set, run | Pass peak, working set / private | Other load mean |
| --- | --- | --- | --- | --- | --- | --- |
| off (cold alignment) | 311.9 s | 27.5 + 64.6 s | | 9.36 GiB | | 78.0 % |
| on (`b23ae160`) | 1,581.1 s | 20.7 + 159.3 s | 1,392.8 s | 6.32 GiB | 3.48 / 3.95 GiB | 53.1 % |
| on (committed code) | 947.8 s | 4.4 + 19.9 s | 922.9 s | 6.48 GiB | 3.54 / 3.95 GiB | 14.1 % |

- **Output bytes (MEASURED):** off and both on arms: result `78eca336d24a2b6a...`, linear master
  `edd7d80950a5c267...` (the master P2 recorded for this bracket).
- **Plane maps unchanged (MEASURED):** the on file's bytes before the focus records hash to
  the off file (11,939,108 B).
- **The field (MEASURED):** not usable, reason 5 ("no area has 25 % of its pixels usable");
  3,427 of 8,241,504 pixels usable, 7,985,600 covered; 173 areas with any usable pixel, none
  a quarter usable; the same in both on arms.
- **Refusal flags (MEASURED, committed code):** boundary 324,656; scale disagreement
  7,453,701; competing mode 7,627,877; weak response 5,380,758; no local fit 3,445,778;
  missing coverage 258,256; unresolved mode 4,774,877. Competing modes and scale
  disagreement cover about nine pixels in ten: over 1,444 fine steps the policy finds more
  than one near-equal peak almost everywhere.
- **Memory (MEASURED):** the pass peaked at the same 3.48 / 3.95 GiB as at 299 planes: the
  frame count does not set it.

### A7CR projection (DERIVED)

- Plane 4752 x 3168 = 15,054,336 quad pixels, 1.83 times the A7C II's 8,241,504.
- Reservation 6.35 GiB (`the_reservation_is_set_by_the_plane`); with the measured
  overhead, about 6.9 GiB private during the pass. Frame count adds 128 bytes a frame.
- Time: the pass is compute-bound per pixel (the decode thread runs ahead), so about 1.83
  times the A7C II per frame: about 7-9 minutes for 299 planes, about 42 minutes for 1,444.
  Four-shot captures stacked as planes (`STREHL_PIXEL_SHIFT=remosaic`) read one RAW a
  plane, so the plane count, not the RAW count, sets it.

## Commands

```text
cargo build --locked --release -p strehl-cli --features temporal-energy
python -I experiments/desktop-studio-2-impl/p8-focus-evidence-run.py ENGINE SOURCE OUT --focus {off,on,placebo} --gpu on --cache CACHE
cargo test --locked -p strehl-cli --lib focus
cargo test --locked -p strehl-ui evidence_file
```

| Check | Result |
| --- | --- |
| `cargo test --locked -p strehl-cli --lib focus` | MEASURED: Compiling strehl-cli; 32 passed, 0 failed, 1 ignored. New: the planted-order positive control and textureless negative control through `focus_pass::compute`, the median and share reduction, a sparse area keeping a nonzero share, the summary layout and its length bound, the reservation at both planes, the records joining the render's file with the last sequences and refused when the format cannot hold them |
| `cargo test --locked -p strehl-cli --lib --bins` | MEASURED: 282 passed, 13 failed, 19 ignored. The 13 are experiment controls compiled into the crate (`m194f` independent reader controls, `m194g` private controls, native green probe and parallel writeback) that need private inputs or a prepared output root; they fail the same way outside this change (the main checkout carries their retained `independent-input-*` folders). None touches the focus code |
| `cargo clippy --locked -p strehl-cli --lib --bins --tests --no-deps -- -D warnings` | MEASURED: no finding in the changed files; the crate's existing findings (image_out, gatefloor, experiment sources) remain |
| `cargo fmt -p strehl-cli -p strehl-ui -- --check` | MEASURED: no difference in the changed lines; the crates' existing differences remain |
| `cargo check --locked -p strehl-cli --lib --tests --features multi-stack` | MEASURED: exit 0 (the session path through the new loader compiles; its behaviour is the same loop, ARGUED) |
| `cargo test --locked -p strehl-ui evidence_file` | MEASURED: 11 passed, including the old reader skipping the new kinds and `read_focus` |
| `cargo clippy --locked -p strehl-ui --all-targets --no-deps -- -D warnings` | MEASURED: exit 0 |

## Open issues

- **The lens itself** (P8's second half, after P3's Stack station): draw `ordinal` only where
  `usable` and the area's share allow, with the legend's caution ("an order of planes, not a
  measured distance"); hide it on renders without a field.
- **The desktop does not ask for the field yet.** `jobs.rs` would pass `--focus-evidence`
  when the owner asks; nothing does today.
- **Speed** before any default: the ARGUED items above, each needing its own measurement
  and a byte-identical field (or a validated coarser one).
- **Sparse coverage** is the evidence policy's (`FocusEvidencePolicy` defaults: 8 nominal
  sigma prominence, perplexity 0.25, competing peak 0.8). Whether the lens should show
  areas under a quarter usable is a display question for the lens, which `share` and
  `ordinal_with_share` leave open.
- No milestone-ledger identity was allocated for this measurement; the orchestrator
  allocates lanes.

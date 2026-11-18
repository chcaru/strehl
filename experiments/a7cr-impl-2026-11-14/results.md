# A7CR stages A, B, D, E (partial): crop, fast decode, pixel-shift groups

**Status:** author verification only; no independent review; nothing committed.
Ledger row `a7cr-impl-2026-11-14`. Plan:
[2026-11-a7cr-pixel-shift-streaming-plan](../../docs/proposals/2026-11-a7cr-pixel-shift-streaming-plan.md).

## Done

- **A1 crop (MEASURED):** `strehl_raw` reads DefaultCrop (0xC61F/0xC620) and
  Sony 0x74C7/0x74C8 from the raw IFD (`strehl-raw-codec/src/cfa.rs`); requires
  both to agree, even origin/size, inside the buffer. It is used when the linked
  decoder reports no area or the whole buffer. A7CR renders are now
  9504 x 6336 at (32, 20), not 9600 x 6376.
- **A2 nonzero origin (MEASURED):** CPU and GPU stacks identical at 9504 x 6336;
  planting 15000 DN into all 992,256 margin photosites of each of 4 real frames
  leaves CPU and GPU outputs byte-identical to the unplanted ones and the warp
  maps identical except the stack name ([plant-margin.py](plant-margin.py)).
- **B2 direct CFA decode (MEASURED):** archives decode chunk-parallel straight
  into the `u16` buffer with the whole-file SHA-256 still verified; plain
  uncompressed ARWs copy the strip directly. Every sample and metadata field
  equals the linked decoder on all 37 A7CR files
  (`tests/lossless-jpeg.rs` now includes `.ARW.straw`). Probe of 32 archives
  2.56 s -> 0.99 s.
- **B1 cause of the 61 MP slowdown (MEASURED):** not the device (production-order
  kernels 7.75 ms/frame at 33 MP, 13.86 at 61 MP, `STREHL_TIMING_PLANE=4752x3168`
  in `strehl-gpu/tests/timing.rs`). It was metadata readers (`identity`,
  `sony_focus`, `sony_optical`, UI preview) expanding and hashing the whole
  124 MB archive per call. `archive::open_original` is now sparse: metadata
  chunks only, verified full expansion if any read touches the strip.
  48-frame synthetic GPU stack: 21.2 s -> 3.2 s total, fold 10.9 -> 1.8 s,
  output unchanged. A7C II byte-freeze 5/5 passed (required mode) after the
  decoder changes.
- **D (MEASURED on a truth-referenced synthetic):** `strehl pixel-shift <run>`
  takes groups only from `events.jsonl` + durable receipts; registers members
  by Lucas-Kanade on 8x8 block luma with noise-attenuation correction (offsets
  (1,0),(1,1),(0,1) recovered exactly); green witness z^2 = 1.00, colour-exact
  pair misregistration 0.000-0.002 px (truth 0); photon transfer from the
  witness 0.3999 DN/e- against a planted 0.400. Dark runs are demoted (no
  structure), as they should be.
- **E (MEASURED, one synthetic scene, 5 planes):** `STREHL_PIXEL_SHIFT=remosaic`
  stacks one frame per focal plane and the banded CPU gather reads measured
  R/G/B from the four members instead of Malvar; groups failing checks fold
  as member 1 and are reported; GPU preparation is refused in this mode.
  Against truth, with identical frames, warp map and cover transform:
  RMSE R/G/B 116/118/58 -> 108/106/55, neutral-edge HF chroma 78 -> 57,
  edge RMSE 83 -> 75, zone plate 1263 -> 1158
  ([synth-pixel-shift.py](synth-pixel-shift.py), [eval-synthetic.py](eval-synthetic.py)).

## Not done / open

- E's gate-floor probe still models Malvar noise (conservative); GPU assembly
  kernel; F; S1's live alignment pairs and provisional preview; S2 (loupe,
  coverage advice, measured-ratio admission); S3; desktop A6 check; desktop
  controls for exposure, burst, retake and the follow panel.
- `cargo test -p strehl-cli --lib`: 233 passed, 8 failed, all harness inputs:
  seven M194g private controls need `STREHL_M194G_BRIDGE_PRIVATE_OUTPUT`,
  `STREHL_DEFECT=off` and `STREHL_FIX_CA=off`; the two native-probe controls
  need `STREHL_GREEN_PROBE_OUTPUT` and each passes alone with a fresh folder (in
  one run they collide on the folder). Desktop tests 1047 passed; byte-freeze
  rerun 5/5 passed in required mode after all merge-path changes
  (`outputs/a7cr-impl/tests-3.log`). Clippy clean on the new modules.
- `scripts/check-defaults.py` declares `STREHL_PIXEL_SHIFT` and
  `STREHL_TIMING_PLANE`; its pre-existing 76 undeclared switches remain.
  `STREHL_PIXEL_SHIFT` is in the byte-freeze test's hermetic environment list.
- Accidental rustfmt edits to 15 unrelated files were reversed; the reverse
  patch is kept at `outputs/a7cr-impl/accidental-rustfmt.patch`.

## Real-camera follow-up (2026-11-14 day session)

Captures 1 and 2 on the A7CR are analysed in
[the calibration results](../a7cr-calibration-2026-11-14/results.md#capture-1-photon-transfer-at-iso-100-plan-c1):
the `ILCE-7CR` noise profile is added (green gain 0.4040 DN/e- at ISO 100), the
real shift table is (0,0), (0,-1), (1,-1), (1,0), the witness pair-shift
tolerance moved from 0.1 to 0.2 photosite on 16 static groups
(`PAIR_SHIFT_TOLERANCE_PX`, `TILE_RATIO_TOLERANCE` in `pixel-shift-cmd.rs`),
the witness now also reports its pair regression per image quadrant, and the crop
margins are measured light-sensitive (A3).

## E on a real paired capture (MEASURED, capture 3, no ground truth)

Input: the coin-cell four-shot run `stack-1794689780304-11226` (107 groups, 2 s,
ISO 100) and its single-shot pair `stack-1794689213508-11226`, same bounds and
step. Arms via `STREHL_PIXEL_SHIFT`: `member1` (new comparison mode: every group
folded as its member 1, so the frames are identical), `remosaic` (71 of 107
groups assembled; 36 demoted by the checks) and `remosaic-ungated` (new
comparison mode: every group whose offsets are measured and cover the lattice
is assembled; 36 overrides logged). All four-shot arms reused one solved warp
map (`alignment: ON (sidecar)`, reference frame 53, cover 0.9897). Default
pyramid merge, CPU preparation, 41-72 s per stack. Binned measurement output
compared with [compare-capture3.py](compare-capture3.py) over the in-focus face
(226 tiles of 128 px, 3.7 MP; edge = top 20% luma gradient, flat = bottom 50%):

| Arm | Edge HF chroma | Flat HF chroma | Edge HF luma |
| --- | --- | --- | --- |
| member1 | 0.0940 | 0.00559 | 0.0921 |
| remosaic (gated) | 0.0960 (+2%) | 0.00580 (+4%) | 0.0914 (-1%) |
| remosaic-ungated | 0.1062 (+13%) | 0.00679 (+22%) | 0.0881 (-4%) |

- Native crops of the binned outputs (5 regions, 384 px) and of full-resolution
  `--srgb` renders (the X marking at (1248, 1504) and a dimple at (5600, 736),
  320 px) show no visible difference between arms; all carry the same red/blue
  edge fringes (lateral CA, correction off for this body). Mean absolute sRGB
  difference from member1: 100 (gated) and 308 (ungated) of 65535.
- Reading: E only replaces the warp-stage interpolation; the output still
  demosaics (or bins) the merged CFA, so its best case is small, and on this
  run's member misregistration (median 0.13 photosite) it is neutral when gated
  and slightly harmful ungated: more edge colour, less edge luma detail, as
  misregistration predicts. The gate is doing its job here. The metrics have no
  truth reference and confound noise with false colour (single-sample chroma
  is expected to be noisier than Malvar's smoothed chroma even when perfect),
  so they rank arms on this input only.
- Implication for the plan, as first written: F (no output demosaic) is where
  pixel shift could pay, so reduce member motion and re-measure before building
  F. **Superseded by the next section:** on a group with almost no motion,
  measured colour is still indistinguishable from the same four exposures
  demosaiced. Motion is not what limits pixel shift on this rig.
- Binned TIFFs and crops are in ignored
  `outputs/a7cr-calibration-2026-11-14/capture3/stacks/` and `compare-binned/`;
  the full-resolution renders were deleted (regenerate with `--srgb`).

## Pixel shift on one still group, no stack (MEASURED, capture 3 plane 97)

**Superseded in part (2026-11-15)** by
[the full-potential results](../a7cr-full-potential-2026-11-14/results.md).
The by-eye finding below stands for one unprocessed group. Its reading does
not: the effective aperture measured from the stack's own spectrum is 13.1,
not the 15 assumed here, which puts green's cutoff above the sensor's Nyquist;
and through a stack with per-channel focus and measured-coherence fusion, four
measured-colour shots carry 1.2 to 1.35 times the fine-detail signal and 1.35
to 2.0 times the fine-detail signal-to-noise of one demosaiced shot per plane.

Question: with motion removed, does measured colour beat demosaicing on this
camera and lens? Plane 97 of `stack-1794689780304-11226` (focus 61818, near the
dome's peak) is the stillest in-focus group: witness pair shift 0.006-0.020 px,
member residuals at most 0.055 px, offsets (0,0), (0,-1), (1,-1), (1,0), gains
within 0.2%. [single-group.rs](single-group.rs) (`cargo run --locked --release
-p strehl-cli --example a7cr-single-group -- DIR 97 OUT`, build cbca976b7-dirty)
renders three full-resolution arms with one white balance and no warp:
`demosaic1` (member 1, Malvar), `demosaic4` (all four members demosaiced, read
at their integer offsets, gain-corrected and averaged: the same light as pixel
shift, colour still interpolated) and `shift` (`pixel_shift::assemble`: every
colour measured). [compare-single-group.py](compare-single-group.py) wrote six
native 384-px crops at the frame's highest green high-pass energy, origins
(1536,1536), (1152,2688), (768,1920), (2304,3072), (768,1152), (1920,2304), plus
3x nearest-neighbour zooms of their central 128 px (zooms for the eye only).

- **Eye, native and zoomed, one display transform:** `demosaic4` and `shift`
  are indistinguishable. Both are visibly cleaner than `demosaic1`, which shows
  noise and isolated red/black demosaic speckles on the brightest edges. The
  finest detail in the frame (coin-surface pits, edge serrations) spans about
  4-6 photosites. Every arm carries the same red/cyan lateral-CA fringes, 1-2
  photosites wide.
- **Flattest 30% of each crop, green high-pass RMS:** `demosaic1` is 1.05-1.72x
  `shift` and 1.13-1.52x `demosaic4`. The flattest areas still hold coin
  texture, so these ratios understate the noise gain.
- **High-pass chroma is not a false-colour measure here, and this run shows
  it.** Edge HF chroma: `demosaic1` 0.945, `demosaic4` 0.824, `shift` 1.467;
  flat 0.0184 / 0.0159 / 0.0299, normalised by crop mean green. `shift` scores
  worst while looking the same as `demosaic4`. Malvar interpolation low-passes
  chroma (noise and real colour detail alike) and measured single-sample R/B do
  not, so the metric penalises measured colour. The same confound applies to
  the stack table above. Its gated-versus-ungated ordering also had the
  witness's motion evidence behind it, but its "+2%" for gated E is not a
  defect.
- **Reading (DERIVED arithmetic, ARGUED conclusion):** with the owner's
  effective aperture N about 15, the diffraction cutoff is 1/(0.55 um x 15)
  = 121 cycles/mm and the Airy first-zero diameter is 2.44 x 0.55 x 15 =
  20 um, 5.4 photosites at 3.76 um. That matches the 4-6 photosite detail seen
  here. Bayer red and blue sample at 7.5 um (Nyquist 66 cycles/mm), so measured
  colour can only add the 66-121 cycles/mm band. Even a perfect lens transfers
  only about 0.33 to 0 contrast there, and the 2x teleconverter and lateral CA
  leave less. Pixel shift's resolution and false-colour gain is therefore close
  to nothing at this effective aperture. What the four shots do deliver is four
  times the light per plane. `demosaic4` delivers the same, so that gain is
  not specific to pixel shift: any four-exposure average of a static plane
  gives it.
- **Implication for the plan:** for this lens, value the four-shot mode as
  light (noise) per plane, not as resolution. The present stack (E) spends
  that light poorly. Remosaicing keeps one measured sample per site (two for
  green), so most of the extra light never reaches the merge. A fold that keeps
  all four members' light (F, or a cheaper demosaic-and-average fold like
  `demosaic4`) is what would turn it into a visibly cleaner stack. That is
  worth testing next, against the alternatives of a longer exposure (where
  highlights allow) and an unshifted burst.
- Crops and `metrics.json` are in ignored
  `outputs/a7cr-calibration-2026-11-14/capture3/single-group-97/` (about 21 MB).

## A6, partial (VERIFIED, offscreen)

`scripts/strehl-control.py ... screenshot --source <four-shot A7CR run> --metadata`
on the rebuilt desktop: the real workspace imports the run (4 photos, 131 MiB),
renders source previews from the archives, and the metadata explorer identifies
ILCE-7CR with AF and optical layouts reported as unsupported, not misread.
Screenshot: ignored `outputs/a7cr-impl/logs/a7cr-metadata.png`. Rendering,
viewing at 1:1 and exporting a 9504 x 6336 result in the UI are not yet
exercised.

## S1, first cut: `strehl follow <run>` (MEASURED on replays)

- Admits a focal plane only when every bound member has a durable receipt with
  its bound SHA-256; never writes in the capture folder; tolerates a torn final
  journal line; waits (bounded) for a run's journal to appear.
- Per plane: decode (archives verify SHA-256), and for four-shot groups the same
  verdict the stack applies (shared `pixel_shift_cmd::verdict`). 0.22-0.35 s per
  61 MP four-shot plane against a 9.1 s capture cadence.
- Journal under `<cache root>/follow/`, one JSON line per plane; a restarted
  engine resumed with all 5 planes already checked.
- At completion it prints retakes as a controller `capture_positions` command
  and, with `--out`, runs the ordinary `stack` (remosaic for four-shot runs).
  **VERIFIED:** the closing TIFF is byte-identical to `stack` run afterwards on
  the same folder (plan decision 6, by construction).
- Replayer [replay-run.py](replay-run.py) (hard links, never copies): clean,
  torn-tail and missing-member replays. A withheld member (plane 3, member 2)
  gave `incomplete`, retake `{"op":"capture_positions","positions":[30003]}`,
  and the closing stack folded that plane's first durable member as an
  ordinary frame.
- **Failing input exercised (plan D3/D4):** plane 2's member 3 replaced by
  plane 4's (same shift, other focus). Pair shift stays 0.003 px (nothing is
  displaced), so the pair-shift test alone would pass it; the witness tile map
  catches it (tile p99/median z^2 4.20 against 1.06 on clean groups). The
  verdict now also requires that scale-free ratio < 2.5 (provisional until
  capture 2), in the report, the stack and `follow`. The contaminated group also
  inflated the pooled witness read noise (1.41 -> 2.23 DN); the report now pools
  photon transfer only from groups with a clean tile ratio, which restores
  gain 0.4000 DN/e- and read noise 1.413 DN on the same run.
- Scratch data (synthetic runs, replays, templates, 48-frame copies, renders,
  about 12 GB) was deleted; regenerate with [synth-pixel-shift.py](synth-pixel-shift.py)
  and the replayer. Logs and reports are in ignored `outputs/a7cr-impl/logs/`. A
  second reverse patch for formatter edits to two `#[path]`-included experiment
  files is `outputs/a7cr-impl/accidental-rustfmt-experiments.patch`.

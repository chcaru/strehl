# A7CR, four-shot pixel shift and stacking during capture: implementation plan

**Status:** Proposal, partly implemented 2026-11-14 (author verification only, uncommitted):
A1, A2, A5, B1, B2, controller exposure/burst/retake commands, D (report command and
stack-time checks), E on the CPU behind `STREHL_PIXEL_SHIFT=remosaic`, and a first cut of
S1 (`strehl follow`). Darks for C1 are captured; gain, A3, A4, A6, B3, B4, C2, C3, F, the
rest of S1, S2 and S3 are open. Results:
[calibration](../../experiments/a7cr-calibration-2026-11-14/results.md),
[implementation](../../experiments/a7cr-impl-2026-11-14/results.md). Section 1 describes
the state before this work.
**Date:** 2026-11-13.
**Scope:** `strehl-raw`, `strehl-raw-codec`, `strehl-core`, `strehl-gpu`, `strehl-cli`,
`strehl-ui`, `strehl-capture` (manifest only until stage S3).
**Order of work:** A (A7CR correct) -> B (61 MP fast) -> C (A7CR calibrated) ->
D/E/F (pixel shift, static stacks) -> S1..S3 (stacking during capture).

Read first: [AGENTS.md](../../AGENTS.md), [ARCHITECTURE.md](../ARCHITECTURE.md),
[native-capture.md](../native-capture.md) section "Boundary for streaming processing",
[research-workflow.md](../agents/research-workflow.md).

No milestone identifiers are allocated. Before dispatching any stage, allocate one
row per stage in [milestone-ledger.md](../agents/milestone-ledger.md) (workflow step 2).
The stage letters below are plan-local labels, not ledger identities.

---

## 1. What is true today

All rows were run on 2026-11-13 against build `strehl 0.1.0-alpha.6
(desktop-55c0fc330e607669)`, `target-ui/release/strehl.exe`, on the owner's desktop
(Ryzen 9 9950X3D, 64 GB, RTX 5090). Input: the real four-shot A7CR run
`D:\StrehlCaptures\stack-1794623749395-10639` (four `.ARW.straw` members, one focal
plane, ISO 100, a nearly dark scene). Outputs and warp maps went to a scratch folder
through `STREHL_WARPMAP`; the capture folder was not written. Logs, maps and the
inspection script are in ignored `outputs/a7cr-plan-2026-11-13/`. Host load was not
recorded and nothing was repeated, so every timing is a single smoke observation,
not a benchmark.

| # | Finding | Label |
| --- | --- | --- |
| 1 | A7CR archives decode. `probe` reports `ILCE-7CR`, ISO 100, black 512, white 15360, RGGB, buffer **9600 x 6376**. | MEASURED |
| 2 | The decoder reports **no active area**, so `Frame::active` falls back to the whole buffer (`strehl-raw/src/lib.rs`, the `unwrap_or(Region{0,0,..})` branch its own comment calls a correctness hazard). The file's raw IFD carries crop origin **(32, 20)** and crop size **9504 x 6336** in tags `0xC61F`/`0xC620` and again in Sony `0x74C7`/`0x74C8`. Renders are therefore 9600 x 6376 and include 96 columns and 40 rows that are not part of the photograph. | MEASURED |
| 3 | The margin is not zero padding: no all-zero row or column exists in the buffer. Whether it is light-sensitive cannot be told from a dark frame. Prior work decoded a LibRaw visible area of 9564 x 6376 ([A7CR qualification](../../experiments/sony-a7cr-2026-11-13/results.md)). | MEASURED / UNVERIFIED |
| 4 | Noise model is `Provenance::Fallback` (unity gain, 4 e- guessed). `profile.rs` has one body, `ILCE-7CM2`. Every gate threshold on an A7CR stack is currently uncalibrated. | MEASURED |
| 5 | Lateral CA is off: no optical profile for body `ILCE-7CR` with lens `33094`. Refinement is skipped with it. | MEASURED |
| 6 | Sony focus metadata is `Unsupported` for this body (`sony-focus.rs` gates on `ILCE-7CM2` and two firmware strings). | MEASURED |
| 7 | An ordinary `stack` of the four members succeeds and **undoes the pixel shift**: the aligner measures the sensor shift as drift (0.556 plane px frame 0 -> 3, nominal 0.5), then the gather resamples each member back onto the reference and the merge treats them as four ordinary frames. No pixel-shift information survives. | MEASURED |
| 8 | Shift pattern between members, by integer cross-correlation of colour-blind 2x2 sums: member 2 at (0,-1), 3 at (1,-1), 4 at (1,0) relative to member 1. The scene is nearly dark and the winning margin is 2e-4 in correlation, so treat the pattern as a prior to verify, not a constant. | UNVERIFIED (weak) |
| 9 | CPU and GPU folds produce byte-identical TIFFs at 61 MP (`cmp`), on 4 frames and on 48. | MEASURED |
| 10 | Throughput on a synthetic 48-frame stack (12 copies of the four members, warm cache): alignment 225 edges in 6.5 s; CPU fold **0.74 s/frame**; GPU fold with GPU preparation **0.27 s/frame**, 3045 MB device memory; totals 45.9 s and 23.5 s, of which about 9.7 s lies outside fold and write in both and is unattributed. For scale, ARCHITECTURE records about 0.011 s/frame for the GPU fold at 33 MP on bug-7. The 61 MP GPU path is roughly 25x slower per frame for 1.84x the pixels. | MEASURED, unattributed |
| 11 | Decode cost: one `.ARW.straw` 263 ms on one thread; the same file restored to plain ARW 88 ms; 48 archives across the pool 37 ms/frame amortised. The archive path rebuilds the whole 124 MB original in memory, hashes it, then hands it to the linked decoder, which copies the samples again. | MEASURED |
| 12 | Look-ahead is 2 frames at 61 MP against 4 at 33 MP (`prepare_lookahead`: 128 bytes per site against a fixed 4 GiB). The alignment window needs `max_span + 2 x batch` = 136 planes of 61 MB = 8.2 GB against the nominal 6 GiB `LADDER_WINDOW_BYTES`. | DERIVED from source |
| 13 | The capture manifest's top-level fields are wrong for this run: `journal.rs:53-54` hard-codes `"raw_format":"sony-lossless-compressed-raw-l"` and `"pixel_shift_shots":1`, while `camera.hello` in the same file says uncompressed and 4. Group truth lives only in `events.jsonl` (`capture_buffered.files[]`: `plane`, `group_id`, `member_index`, `members`, `sha256`) and in each ARW's Sony PixelShiftInfo tag. | MEASURED |
| 14 | The archive is already at the noise floor for this scene: 34.33 MB is 4.49 bits/sample; same-photosite temporal SD between members is 7.2/sqrt(2) = 5.1 DN, whose Gaussian entropy is 4.40 bits. | DERIVED from MEASURED |
| 15 | GPU fold refuses more than four planes (`strehl-gpu/src/lib.rs:798`). The device already holds three full-resolution channel planes (`rgb`) between Malvar and the gather. | MEASURED (source) |

Commands, from the repository root, with `S=target-ui/release/strehl.exe`:

```text
$S probe D:\StrehlCaptures\stack-1794623749395-10639
$S align <run> --out <scratch>\ps4-warpmap.txt
STREHL_WARPMAP=<scratch>\ps4-warpmap.txt [STREHL_GPU_FOLD=on] $S stack <run> --out <scratch>\x.tif --srgb
target/release/strehl-raw-archive.exe restore <run> --output-dir <scratch>\restored
python -X utf8 a7cr_inspect.py <scratch>\restored
```

## 2. Prior work this plan depends on

Name these in every brief. Do not re-derive them.

- [sony-upgrade-2026-11-07](../../experiments/sony-upgrade-2026-11-07/results.md):
  the optical argument (ARGUED/DERIVED). At the reference working aperture of
  f/13.5-17.2 the green diffraction cutoff is 106-135 lp/mm against an A7CR grid
  Nyquist of 133 lp/mm, and red/blue Bayer planes sample at 66.6 lp/mm. Four-shot
  capture supplies what the optics pass and a single Bayer exposure does not sample;
  sixteen-shot mostly samples above the cutoff. Its proposed integration list is the
  parent of stages D-F here.
- [sony-raw-compression-2026-11-12](../../experiments/sony-raw-compression-2026-11-12/results.md):
  temporal prediction across pixel-shift members saves 0.27-3.98% beyond independent
  coding (MEASURED on 20 genuine 61 MP files); a lit 61 MP frame is about 54.5 MB.
- [sony-a7cr-2026-11-13](../../experiments/sony-a7cr-2026-11-13/results.md) and
  [sony-raw-storage-2026-11-13](../../experiments/sony-raw-storage-2026-11-13/results.md):
  the capture path, group delivery and archive format.
- [image-quality-2026-11-02](../../experiments/image-quality-2026-11-02/results.md) section 2,
  **"Fuse each source's reconstructed RGB instead of re-mosaicing (REJECTED)"**. A
  12-plane fold (4 sites x 3 colours, weights bit-identical to the default) was built
  and archived as `rgb-fusion-arm.patch` and `rgb-fusion-arm-merge_cmd.diff`. It was
  rejected because Malvar-estimated chroma carried 1.48-1.57x more high-frequency
  chroma on a neutral razor blade than the second demosaic leaves. Stage F reopens
  this branch. Workflow rule: reopening needs new evidence and a changed question.
  The changed question is stated in F.
- [super-resolution-2026-11-01](../../experiments/super-resolution-2026-11-01/results.md):
  rejected breathing super-resolution. Not reopened here.
- `crates/strehl-core/src/reconstruction.rs` and the session reconstruction consumers:
  an opt-in original-CFA reconstruction with native fallback, quality-rejected as a
  default. Not the route taken here; integer pixel shift needs no regression.

Licence boundary, restated because pixel-shift research leads straight to it:
RawTherapee and darktable both contain pixel-shift reconstruction and are on the
do-not-open list. Sony PixelShiftInfo may be parsed from tag IDs and offsets as
facts; do not read ExifTool Perl source.

## 3. Decisions

Each is a recommendation with its reason. Section 11 lists the ones the owner should confirm.

1. **A focal plane is the unit, not a RAW.** A four-shot group enters alignment, the
   fold, progress, the ensemble count and the UI as one observation. Its four members
   are an implementation detail of how that observation's RGB is obtained.
2. **One source abstraction: an RGB source.** Today the gather samples three
   Malvar-estimated full-resolution channels. A group supplies the same three
   channels *measured*. A single-shot frame and a demoted group supply them
   *estimated*. Everything downstream of the gather is identical for both. On the GPU
   this is one kernel swap in front of the existing `rgb` buffer.
3. **Integer shifts or nothing.** A group is assembled by integer indexing only when
   its measured member geometry agrees with the nominal pattern within a tolerance.
   Otherwise the group is demoted to estimated sources and reported. No sub-pixel
   resampling of a Bayer member is introduced.
4. **Sixteen-shot is out of scope**, on the optical argument in the prior work.
5. **No group-aware compression.** Finding 14 and the prior measurement agree: the
   archive is noise-entropy bound. Disk is controlled by not persisting derived data,
   by admission that uses the measured ratio, and by not capturing planes that
   contribute nothing (S2), not by a new codec.
6. **Stacking during capture has a byte-identity contract.** The photograph produced
   at the end of a streamed capture is byte-identical to `strehl stack` run afterwards
   on the same folder. During capture the engine does everything whose result does not
   depend on frames not yet taken (decode checks, group QC, every alignment pair
   measurement) and maintains a provisional preview. A fold whose inputs are still
   moving is never presented as final. Whether a lag-committed streaming fold can
   replace the closing fold is experiment S3, with a pre-registered gate.
7. **The streaming engine persists one small journal and nothing else.** No decoded
   frames, no composites, no proxies, no accumulator checkpoints on disk.

## 4. Stage A: A7CR single-shot correctness

Goal: an ordinary A7CR stack renders the right pixels with honest provenance.

**A1. Active area.** In `strehl-raw::decode_with`, when the linked decoder reports no
active area, read the crop from the raw IFD (`0xC61F`/`0xC620`, falling back to Sony
`0x74C7`/`0x74C8`; require both pairs to agree when both exist) and set
`Frame::active = {32, 20, 9504, 6336}` for these files. Reuse the bounded IFD walk in
`strehl-raw-codec::layout` or `sony-tiff.rs`; do not add a second TIFF parser. Refuse
an odd origin (it would change CFA phase) and a crop outside the buffer. Keep the
whole-buffer fallback only for files with no crop tags, and print it in the banner.

**A2. Nonzero-origin audit.** This is the first body whose active origin is not
(0, 0). 61 uses of `active.x`/`active.y` exist outside `strehl-raw`, most in examples.
Audit the production ones: `align_cmd.rs`, `direct-cfa-gather.rs`, `merge_cmd/gatefloor.rs`,
`lib.rs`, the GPU upload in `merge_cmd.rs` and `strehl-gpu` (does it upload the buffer
or the active area, and with which stride?), `defect_map.rs` coordinate space, and the
UI source preview. Tests: a synthetic frame with origin (32, 20) and a distinct value
in the margin must produce output with no margin value, on the CPU and GPU paths,
with identical bytes. The A7C II byte-freeze must not move.

**A3. Margin verification.** With the first lit A7CR frame (any capture in section 10),
establish whether the ring outside the crop is valid image data: row and column
statistics continuous across the crop boundary, and the 28 columns right of the crop
compared with the 36 beyond them. If valid, expose it as gather support (the warp may
read real pixels past the crop instead of the border rule) and as the one-pixel ring
stage D needs. If not, the crop is the limit. Do not assume.

**A4. Provenance plumbing.** Add `ILCE-7CR` handling to `sony-focus.rs` only if its
block layout is established from the owner's files; otherwise leave it `Unsupported`
and rely on the capture manifest's focus positions. Do not copy the A7C II offsets.

**A5. Capture manifest.** Fix `journal.rs` so top-level `raw_format` and
`pixel_shift_shots` report the run's actual values, and add `planned_planes`. Bump the
schema string. Readers must treat the per-file bindings in `events.jsonl` and the
in-file Sony tags as authoritative and the top-level fields as a summary.

**A6. Desktop at 61 MP.** Exercise the real UI with a 9504-wide result and source:
texture limits (`app.rs:234` assumes 8192 when no device), preview memory, the
developed-image path, export. `pipeline.rs` parses the CLI banner as text; any banner
line it reads must keep its shape, and new lines need parser tests.

Done when: an A7CR single-shot stack renders 9504 x 6336 with no margin content, CPU
and GPU identical, A7C II freeze unchanged, UI opens and exports the result.

## 5. Stage B: 61 MP performance

Goal: per-pixel throughput at 61 MP no worse than at 33 MP. Proposed budgets, to be
replaced by measured ones after B1: single-shot GPU path at most 40 ms per frame in
steady state on this host; peak private memory at most 12 GB; CPU path within 2.2x of
its 33 MP per-frame time.

**B1. Attribute before optimising.** Finding 10 is not explained. Hypotheses, in the
order I would test them: decode-ahead starving on the archive path (263 ms per file on
one thread, B2); the linked decoder's internal parallelism fighting 16 decoder threads
on uncompressed files (the 33 MP corpus is lossless-compressed and uses
`lossless-jpeg.rs`, so this code path has never carried a deep stack); look-ahead 2;
device-side costs that scale worse than area (the probe's f64 reductions, the
readback at chunk end with only 2 canonical chunks); the 9.7 s outside the fold.
Use `crates/strehl-gpu/tests/timing.rs` at 9504 x 6336, decode-ahead queue depth
logging, and a plain-ARW against archive A/B on the same frames. Record host load.
The synthetic 48-frame stack in section 1 is a valid harness for throughput and
memory, not for quality: it is dark and repeats four frames.

**B2. Decode archives straight to CFA.** Add `strehl_raw_codec::archive::decode_cfa_into`
and use it from `strehl-raw` for archives whose `layout()` is a plain 14/16-bit CFA
strip (finding 1: 52 chunks, 50 of them 128-row CFA strips of method 8).

- Each CFA chunk is an independent Zstd frame plus the reversible predictor. Decode
  chunks in parallel and write samples directly into the destination `Vec<u16>` rows
  (`decode_into`'s reused buffer). No 124 MB byte image, no second copy.
- Give the linked decoder only the bytes before the strip for metadata, as
  `native_pixels` already does for lossless JPEG. Verify every `Frame` field against a
  full linked decode in a test over all owned A7CR files.
- Keep the original-bytes SHA-256 check. On a little-endian host the destination
  buffer *is* the strip's original bytes, so hash prefix, strip rows in order, suffix,
  on a separate thread while the frame is uploaded; fail the frame on mismatch before
  it is folded. A switch may defer verification for receipts verified within the same
  process lifetime, but default is verify.
- Test: sample-for-sample equality with `read_original` + linked decode on every
  archive; corrupt-chunk, truncated and wrong-hash refusals; a non-CFA archive falls
  back to the existing route.
- Target: at most 60 ms per 61 MP archive on one thread. UNVERIFIED until measured.

**B3. Planner constants.** `prepare_lookahead` and `LADDER_WINDOW_BYTES` were calibrated
on 33 MP. Re-measure the per-slot cost at 61 MP with GPU preparation (the CPU gather
temporaries the 128 bytes/site figure describes are not allocated there) and set the
look-ahead from the measurement. For the alignment window, store planes as `u16`
green sums (`G1 + G2` fits 15 bits; promote at use) to halve it to about 4.1 GB at
136 planes, and prove edges bit-identical to the `f32` window. `canonical_band_chunks`
must not change for existing geometries: it is arithmetic, and the byte-freeze pins it.

**B4. Deep real stack.** Section 10 capture 3a is the acceptance input: record
frames/s, peak private memory, device memory, and CPU against GPU identity.

## 6. Stage C: A7CR calibration

**C1. Noise profile.** Add an `ILCE-7CR` `CameraProfile` from section 10 capture 1:
gain, read noise per ISO, the second base ISO if one is measured (do not assume the
A7C II's 400), PRNU measured and left off as on the A7C II. Follow the photon-transfer
method and the independent-decode rule already used for M4/M71. Until it lands, A7CR
renders stay stamped Fallback; do not ship a guessed profile.

**C2. Optical profile.** Add (`ILCE-7CR`, `33094`) to `optics.rs` only from A7CR
measurements. Add a measure-only mode to the per-capture refinement that reports red
and blue scale and translation against green with no prior, run it on at least five
A7CR captures, and derive the profile from those. Until then CA stays off for this
body, which is the current, safe behaviour.

**C3. Runtime cross-check from pixel shift** (depends on D). See D4. It can supply a
`Provenance::Measured` model for pixel-shift stacks before C1 exists and an
independent check of C1 afterwards. A constant fitted from the witness must be
validated against C1's separate capture, never against itself.

## 7. Stages D, E, F: pixel shift on a stack already on disk

### D. Group model, discovery and QC

**D1. Types.** In `strehl-core` (new `pixel-shift.rs`): `ShiftGroup { plane, members:
[MemberRef; 4], offsets: [(i8, i8); 4], gains: [f32; 4], verdict }` and
`FocalPlaneSource::{Single(path), Group(ShiftGroup), Demoted(ShiftGroup, reason)}`.
The stack's frame list becomes a list of `FocalPlaneSource`. Single-shot stacks map
one-to-one and must stay byte-identical.

**D2. Discovery, in order of authority.** (1) A capture manifest beside the files:
`events.jsonl` bindings, checked against receipts and hashes. (2) Sony PixelShiftInfo
in each file (group id, shot k of n), parsed in `strehl-raw` from tag facts; validate
against the owner's 24 qualified files, whose tags are already recorded. (3) Nothing
else. Never infer groups from counts or timestamps. `--pixel-shift=off` forces every
file to `Single`; a group with missing members becomes `Demoted`, never silently
dropped, and the banner says so.

**D3. Member geometry check.** For each group, measure members 2-4 against member 1
with the existing `align_pair` on green-luma planes and compare with the nominal
integer offset. The offset table is a prior confirmed by this measurement on every
group, not a compiled constant; finding 8 is too weak to hard-code. Pass when every
residual is under a tolerance set from the distribution observed on section 10
capture 2 (static groups). Failing input for the gate: a group with one member
replaced by the same member from the neighbouring focal plane, and a synthetic plant
that rolls one member by one extra pixel.

**D4. The green witness.** With shifts {(0,0), (0,1), (1,1), (1,0)} mod 2, every scene
site receives red once, blue once and green twice, and the two greens come from
members that differ by a diagonal step: pairs (1,3) and (2,4), one G1-type and one
G2-type photosite each. At nominal registration both green samples are the same
scene point at the same site, with no interpolation between them. That gives, for
free on every group:

- *Consistency.* `z = (Ga - Gb) / sqrt(var(Ga) + var(Gb))` from the injected model.
  The mean of `z^2` per 64 x 64 tile is about 1 for a static, registered, flicker-free
  group and rises with motion, vibration, misregistration (as `delta . grad G`) or a
  wrong noise model. Report the tile map and its quantiles per group. Verdict
  thresholds come from capture 2; the failing input is the same pair used in D3.
- *Sub-pixel residual.* Least-squares regression of `Ga - Gb` on the green gradient
  gives the residual displacement of each witness pair without resampling. Use it as
  the precise half of D3; `align_pair` links the two pairs.
- *Member gains.* Per-member flux ratios (reuse the flux-ratio estimator in
  `photometric.rs`; no offset term) equalise exposure flicker before assembly. This
  is mandatory, not cosmetic: green at even-parity sites comes from one witness pair
  and at odd-parity sites from the other, so a 0.5% flicker between pairs is a 0.5%
  Nyquist checkerboard in green, and a four-phase pattern in red and blue. Scale each
  member's noise model with its gain (sigma scales by `c`, as `photometric.rs` already
  does).
- *Photon transfer.* On low-gradient tiles, `Var(Ga - Gb) / 2` binned by mean signal
  is `r^2 + g S + (kappa S)^2`. Robust variance per bin, weighted fit, pooled over the
  stack. Most of every macro frame is defocused, so the stack is its own flat field.
  The quadratic term absorbs the G1/G2 photosite mismatch. Computed once, before the
  fold, and injected as the one noise model (rule: no private per-stage estimates).
  Controls: a synthetic group with known `g`, `r` must return them; a planted 0.2 px
  misregistration must not move the fit on the selected tiles; compare with C1.

**D5. Analysis pass.** One pass decodes every RAW once and produces: group verdicts,
gains, the witness statistics, and one alignment plane per focal plane (mean of all
eight green samples per quad; noise variance one quarter of the single-shot plane).
Alignment then runs on focal planes: N nodes instead of 4N, same ladder, same solver,
same sidecar format with a strategy string that names the group policy. The
placement of a group is the placement of its composite in member 1's sensor frame.

### E. Assembled source through the existing fold (comparator and plumbing)

Replace per-source Malvar with assembly for `Group` sources and change nothing else.

- **Kernel.** For site `(x, y)` in member 1's frame, member `k` contributes sample
  `(x + dx_k, y + dy_k)` to the channel `CFA(x + dx_k, y + dy_k)`, times its gain.
  Red and blue are one sample; green is the mean of two. Integer indexing, one
  multiply, one add and halve: trivially bit-reproducible under the GPU's existing
  `NoContraction` rules. CPU and GPU versions, pinned identical by test.
- **Defects** are corrected per member before assembly (the map is indexed by
  photosite; one hot photosite lands on four scene sites).
- **Border.** Use the verified margin ring (A3) or drop the incomplete one-pixel ring
  from coverage. Never fill it with a guess.
- **GPU.** Upload four members (about 490 MB per plane), write the existing `rgb`
  buffer, continue into the unchanged gather. Raw slots grow from 2 + probe to
  8 + probe (about 1.1 GB). The CPU path must exist and match.
- **Noise.** Green planes carry half the variance: express it as `PlaneNoise` with
  gain `g/2` and read noise `sqrt(2) x RN_e`, which reproduces `(g S + r^2)/2` exactly.
  The gate-floor probe must push its noise through assembly instead of Malvar, with
  the per-channel variances above, so the measured floor describes the operator that
  ran. Control: a pure-noise group stack averages and does not select, and flat-ROI
  temporal sigma matches the injected model.
- **Demoted groups** contribute one observation: the mean of their members' Malvar
  sources, each gathered through its own measured placement.

E still re-mosaics after the gather and demosaics the merge, so it keeps one colour
per site and discards most of the measured red and blue. It is not the goal. It is
the smallest change that makes a pixel-shift stack correct (finding 7), makes the
fold one step per focal plane, and it is the control arm that isolates what F adds.
Ship it behind `--pixel-shift=remosaic`.

### F. Full-colour fold

Changed question for the rejected RGB-fusion branch: *with measured rather than
Malvar-estimated channels, does fusing all three colours at every site and skipping
the closing demosaic lower error against truth, without the high-frequency chroma
the rejected arm added?* The rejection's cause was estimated chroma. Group sources
have none.

- **Fold.** Resurrect the archived 12-plane arm: four sites x three colours at quad
  resolution, weights computed as today from the green luma and shared by all planes,
  so every calibrated constant (band gains, gate, exponent ladder, ensemble null)
  keeps its meaning. `BandMerge::new(w, h, 12, cfg)` already takes a plane count.
  Lift the GPU's four-plane limit (finding 15); budget about 3x the plane-dependent
  device memory (measure it; 3045 MB at four planes today).
- **Writer.** A 12-plane result interleaves to full-resolution camera RGB and enters
  `write_merged` after the demosaic step: black, white balance, matrix, highlight
  roll-off, sRGB, and the scene-linear master, unchanged. Flags that assume four CFA
  planes (`--sensor-master`, `--binned`, `--demosaic`, region recipes) are refused on
  this path until each is defined. Refused, not ignored.
- **Mixed stacks.** Estimated sources (single frames, demoted groups) feed the same
  12 planes from their Malvar RGB. Report the count; a stack that is mostly estimated
  falls back to the default path with a message, because that is the rejected arm.
- **Gates, registered before any render is inspected** (workflow "Before dispatch" 4):
  1. Flat-ROI controls first: temporal noise in flat regions against the injected
     model, and against arm E and the single-shot arm at equal light.
  2. Neutral razor blade (truth: no chroma), the exact statistic of the rejection:
     high-frequency chroma of F at or below the default path's on the same target.
     Failing input: the archived Malvar-fed arm, which must still fail.
  3. Truth-referenced synthetic through the production merge, as in the 2026-11-02
     harness, with a planted full-colour scene sampled into four shifted mosaics.
     State which direction each metric can be fooled.
  4. Causal placebo: the same four members assembled with a deliberately wrong
     offset table must score worse. If it does not, the metric is not measuring
     pixel shift.
  5. Complete photographs and native crops under identical display transforms,
     arms: member 1 single-shot, four members as ordinary frames (today), E, F, and
     optionally Sony's own composite as a comparator, never as truth.
- **Open research arm, not a deliverable:** the 12-plane fold makes one focus
  decision per quad. A three-plane full-resolution pyramid with one more octave and
  full-resolution green luma is the alternative. Run it only after F passes, as its
  own allocated experiment.

Done when F passes its gates on captures 2 and 3 and an independent review has
re-chosen the estimator, reference and null. Until then the default for group
stacks is E.

## 8. Stages S1-S3: stacking during capture

Capture cadence is 5.9 s per single-shot plane and 9.1 s per four-shot plane
(MEASURED, one plane each). The PC is idle for almost all of that. The design problem
is finality and memory, not speed.

### S1. Follow engine

A new long-lived CLI mode, `strehl follow <run-dir>`, started by the desktop when a
stack starts (and attachable to a run already in progress). The Pi and the receiver
do not change.

- **Admission.** Tail `transfer-receipts.jsonl` and the uploaded `events.jsonl`. A
  focal plane is admitted when its `capture_buffered` binding exists and every member
  has a durable receipt with the bound hash. Poll; do not depend on directory
  notifications. Never read a file without its receipt.
- **Per admitted plane, bounded work:** decode members once (B2); group QC and witness
  (D3, D4); build the alignment plane; measure its ladder pairs against the planes
  still in the window (spans 1..128 back, the window of B3); append results to the
  journal; update the provisional solve (banded factorisation, already O(n b^2));
  update the preview.
- **Journal.** One append-only file in the cache root, keyed like warp maps by run
  identity and solve configuration, never inside the capture folder. It holds group
  verdicts, gains, witness summaries and pair measurements with hex-exact floats.
  A few megabytes per stack. A restarted engine replays it and resumes; a missing or
  stale journal is rebuilt from the RAWs.
- **Preview.** A reduced-resolution fold with the production merge code on
  box-decimated sources (start at one eighth linear; planes kept in RAM as `u16`,
  about 7.5 MB each, under a fixed budget that coarsens rather than grows). Because
  proxies are cheap, the preview is refolded from scratch whenever the provisional
  solve moves an admitted plane by more than a quarter of a proxy pixel, so it always
  agrees with the current geometry. It is labelled provisional everywhere it appears
  and is never written to disk.
- **Close.** When `result.json` reports completion (or the owner stops the run and
  every admitted group is complete), the engine writes the standard warp sidecar from
  the journaled pairs and runs the ordinary `stack` path on the folder.
- **Contract and its test.** The sidecar written from journaled pairs is
  byte-identical to the one `strehl align` writes afterwards on the same folder, and
  the photograph and master are byte-identical to `strehl stack`. Pairs are measured
  by the same `align_pair` on the same planes and tagged with their ladder ordinal, as
  `measure_ladder_streaming` already does, so this is a property to prove, not an
  approximation to tune. Test it with a replayer.
- **Replayer.** A test tool that replays a completed run directory into a fresh
  folder in receipt order at a chosen speed, including faults: a late member, a
  member that never arrives, a duplicate receipt, an engine killed and restarted
  mid-run, a stop mid-group. Every streaming test runs against it; no camera needed.
- **Resource rules.** Below-normal priority and a thread cap while the receiver is
  writing; the receiver's durability always wins. Fixed RAM ceiling (propose 16 GB)
  with the alignment window as the largest tenant. No per-plane work that grows with
  the number of planes already admitted, except the solve.
- **Desktop.** The Capture tab gains a live panel: provisional photograph, per-plane
  QC strip, counts of admitted, demoted and waiting planes, and the closing render's
  progress. Use `scripts/strehl-control.py` and its `screenshot` command to test it.

Budget: live work per plane under 1 s of wall time; closing render under 10% of
capture duration. For 300 four-shot planes that is roughly 45 minutes of capture
and a closing render of about a minute if B meets its targets (DERIVED from targets,
not measured).

### S2. Use the live evidence

Each item is small once S1 exists, and each is where streaming pays for itself.

- **Loupe.** Keep full-resolution crops of an owner-chosen region per plane in RAM
  (1024 x 1024 x 4 members is 8 MB per plane) and fold that region at full quality on
  demand, so critical detail can be judged at 1:1 while the rig is still set up.
- **Coverage and stop advice.** From the preview's weights, report how much of the
  frame each plane wins. Planes at either end that win nothing mean the bounds are
  too wide; a run of such planes at the end is a prompt to stop. This is the largest
  disk saving available: a plane not captured costs nothing. Advice only. The engine
  never stops a capture.
- **Admission with the measured ratio.** After the first planes, replace "assume no
  compression" with the worst observed ratio plus margin, keeping the per-plane
  recheck. Today an 1801-plane four-shot plan is refused at 1,209 GB against a likely
  250-400 GB.
- **Retakes** (needs a controller change, so last). Focus positions are absolute and
  the approach is repeatable. At the end of the pass the PC can hand the controller
  the ordinals of demoted groups to shoot again from the same approach direction.
  The stack then uses the best group per plane and keeps the rest out of the fold.

### S3. Can the closing fold be avoided? (experiment)

Question: if a plane is folded at full resolution once its placement has stopped
moving, how far is the result from the offline render? Replay bug-7 and the first
deep A7CR stack in capture order; record, per plane and per lag, the corner
displacement between the causal solve and the final solve, and the output difference
of a lag-committed fold. Three things besides placement are only known at the end
and must each be handled or shown not to matter: the reference frame (the middle
plane; its index is known from the plan unless the run is stopped early), the cover
crop and canvas scale, and the CA refinement preview. Pre-register the tolerance.
If it fails, the closing fold stays, and at a minute per stack that is acceptable.

## 9. Storage

| Artifact | Persisted | Note |
| --- | --- | --- |
| RAW members, `.ARW.straw` | yes | Exact; already at the noise floor (finding 14). About 34-55 MB each, so 137-220 MB per four-shot plane. |
| Manifest, events, receipts | yes | Kilobytes. |
| Follow journal | yes, cache root | Megabytes; rebuildable. |
| Warp sidecar | yes, cache root | As today. |
| Decoded frames, composites, alignment planes, proxies, loupe crops | never | RAM, fixed budgets. |
| Accumulators, provisional previews | never | The closing fold is cheaper than a checkpoint is large. |
| Photograph and scene-linear master | yes | 361 MB and 722 MB uncompressed at 61 MP. Confirm lossless compression is on for both and measure it. |

Considered and not proposed: a lossy archive tier that quantises to a fraction of
the calibrated noise SD (a step of sigma/2 adds 2.1% variance and would bring a lit
frame from about 54 MB to about 23 MB; DERIVED). It breaks the exactness contract
and the receipt hashes, and it needs C1 first. Raise it only if the owner asks.

## 10. Captures needed from the owner

Add these to [captures-needed.md](../captures-needed.md) when the stages are allocated.
Stabilisation off, fixed manual exposure, fixed illumination, nothing touched between
frames. None of them asks for a different aperture.

1. **Noise calibration, single-shot, at each ISO actually used** (about 10 min): 32
   darks at the working shutter time, and a 32-frame static burst of a strongly
   defocused scene spanning dark to near-clipping. Unblocks C1.
2. **Static pixel-shift burst** (about 5 min): 8 four-shot groups at one fixed focus on
   a flat, finely detailed target with a neutral region (the calibration slide or
   razor blade), plus one group shot while deliberately tapping the table. Unblocks
   D3, D4 thresholds and their failing input, the shift table, A3.
3. **Paired stacks of one static subject, same bounds and step** (one sitting):
   (a) single-shot, 100-300 planes; (b) four-shot, 60-100 planes. Include the neutral
   razor blade once. Unblocks B4, E, F and S1's replayer inputs.

## 11. Open decisions for the owner

1. Confirm the byte-identity contract for streamed results (decision 6), or accept a
   tolerance and let S3 decide.
2. Whether F, once its gates pass, becomes the default for group stacks.
3. Whether the controller may take retake requests from the PC (S2).
4. Archive retention: exact archives kept indefinitely (assumed here).

## 12. Risks

- **Vibration between members.** At this magnification one pixel is about a micron
  on the subject. If static groups fail D3/D4 often, pixel shift on this rig is a
  capture problem before it is a software one. Capture 2 answers this first; do not
  build F before looking at it.
- **Chroma noise.** Measured chroma is unbiased but single-sample per site; Malvar's
  is smoothed and biased. F can look noisier at 1:1 in colour while being more
  accurate. Gate 1 measures it; do not judge it by eye alone.
- **61 MP GPU slowdown has an unknown cause.** If it is structural, B's budget moves
  and so does the closing-render estimate in S1.
- **Nonzero active origin** can hide off-by-origin bugs that A7C II tests never
  exercised. A2's planted-margin test is the guard.
- **Banner coupling.** The desktop parses CLI text. New source kinds must not change
  lines it reads.

## 13. Working rules for the implementing agent

- The tree has unrelated changes (`experiments/ca-before-mhc/gpu.rs`, untracked
  `experiments/m194f-production-bridge/` folders). Leave them. Commit with
  `git commit -- <paths>`.
- Capture folders are read-only. Use `STREHL_WARPMAP` with a fresh map per arm.
- Never use Cargo `-q` for evidence; capture `$LASTEXITCODE` before piping.
- Every quality or speed claim carries its command and a label. Exercise each gate
  with its failing input before using it. Author checks do not replace independent
  review of F's conclusions.
- Single-shot A7C II output must stay byte-identical through every stage here. Any
  hash movement on the existing freeze is a bug in this work until shown otherwise.

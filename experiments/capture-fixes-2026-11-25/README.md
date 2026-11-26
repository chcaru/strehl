# Capture fixes, 2026-11-25: slide stacks, the four-shot check, the stillness check

The owner put a backlit calibration slide (filmhever.info: USAF bars, Siemens stars,
dot grids) on the rig to chase the sway, shot two short four-shot stacks with highlight
groups (`D:/StrehlCaptures/stack-1795638138175-14989`, 6 planes, 27 groups, and
`stack-1795640925619-14989`, 5 planes, 13 groups; 1.3 s base, 0.4 s highlight, ISO 100),
and reported that both failed to stack and that the live-view stillness check looked
inaccurate. Three faults were found and fixed. Labels as in `AGENTS.md`.

Analysis scripts, kept outside the repository with the owner's pictures:
`C:/strehl-scratch/i-round/sway/` (`register.py`, `witness.py`, `blur2.py`,
`checker-bias.py`, `stillness-test.py`, `still-live.py`, `raw-still.py`, `lags.py`) and
`C:/strehl-scratch/fix/` (`verify-engine.sh`, its logs).

## 1. Both slide stacks crashed in the GPU fold

MEASURED, both render logs: `Buffer binding 9 range 2147483648 exceeds
max_*_buffer_binding_size limit 2147483644` in `create_bind_group 'fold-bind'`, then
`re-map upload buffer: BufferAsyncError`.

Cause: the highlight patches (plan X4) of both frame slots live in one storage buffer,
bound whole, and `ensure_patch_words` grew it to the next power of two. The slide's
backlight clips over a quarter of the frame, so a frame carried about 47 M site patches
(236 M over 5 planes, 12 carried planes), and the power of two came to exactly 2^31
bytes, 4 bytes over the device's binding limit.

First fix (installed 2026-11-25 as `desktop-934cf5a41562aa17`): the buffer grew
geometrically but never past the device's limit, and a frame whose patches did not fit
was applied in parts. VERIFIED then: both stacks render on the GPU equal to the CPU
fold, also with the parted path forced. Superseded the same day by section 4, which
removes the patch buffer altogether.

## 2. The four-shot check misread members on the slide

MEASURED: on every group the check reported residuals of 0.2-0.45 photosite for members
moved by an odd number of photosites (member 3 about (-0.44, -0.34) in every group),
"witness pairs misregistered by 0.54-0.57 photosite after residual compensation" on
every plane, and "a shot slipped by a whole photosite" in four groups. All four-shot
groups of the second stack were rendered as single shots, and five automatic retakes
were taken for nothing. Three independent measurements on the RAWs (2x2-window
luminance, green-only witness pairs, and the check's own method sampled on both CFA
parities) agree on about 0.05 photosite and no slip.

Cause (VERIFIED by reproducing the check's residuals to three decimals in Python): the
check registers 8 x 8 block sums, and one block's red photosites sit one photosite from
its blue ones, which way round depending on the block's parity. Sampling every second
block from an even origin reads one parity only. Red alone registers an odd-shifted
member one photosite short, blue alone one long; they cancel only when red and blue
carry the same detail, which the white balance (equal means) does not ensure, and on a
backlit slide under a blue light they do not.

Fix (`crates/strehl-core/src/pixel-shift.rs`): registration uses `Integral::luma`, the
four blocks at `(x, y)`, `(x + 1, y)`, `(x, y + 1)`, `(x + 1, y + 1)` summed: a 9 x 9
window weighted 1, 2, ..., 2, 1 in which every colour weighs the same and centres on the
window at either parity. `GROUP_CHECK_VERSION` 2 -> 3, so journaled measurements of the
old code are measured again.

Tests: `registration_ignores_a_parity_pattern_in_block_luma` (failed with the old luma:
0.199 photosite; passes) and the pinned measurement digest, updated.

VERIFIED with `strehl pixel-shift --all-groups`, old against new engine:

| Capture | Groups | Old: pass / demoted / parity | New: pass / demoted / parity | Residuals moved |
| --- | --- | --- | --- | --- |
| Slide, first stack | 27 | 25 / 2 / 1 | 26 / 1 / 0 | up to 1 photosite |
| Slide, second stack | 13 | 5 / 8 / 6 | 7 / 6 / 0 | up to 1.03 |
| Scarab (`stack-1795300522964-6430`) | 260 | 122 / 138 / 17 | 122 / 138 / 17 | median 0.034, max 0.079 |
| Weevil (`stack-1795460665629-8651`) | 205 | 179 / 26 / 0 | 179 / 26 / 0 | median 0.047, max 0.106 |

No verdict changed on the scarab or the weevil. The groups of the second slide stack
still demoted had real member movement of 0.20-0.28 photosite (the rig drifted 1-2 px a
minute while the light warmed it); every group the stack uses now assembles.

## 3. The stillness check (plan Q7)

Measured on the rig (stillness-test.py: three 25 s magnified live series and 48 RAW
shots at 1/100 s, ISO 3200, at one focus position):

| | Frozen RAWs | Live view |
| --- | --- | --- |
| Movement over 0.4-2.4 s, side to side (rms) | 0.15-0.21 px | 0.15-0.31 px |
| The same, up-down | 0.16-0.20 px | 0.30-0.64 px |
| The old check's line | | 0.23, 0.57 and 1.05 px in three runs minutes apart |

- The picture wanders; it does not oscillate. The old check's frequency was always 0.1 Hz,
  the bottom of its search, and its exposure limit came from that frequency.
- The old check registered the centre 320 x 320 only; in the third run that patch
  disagreed with the whole frame by 0.8 px rms.
- Live view moves about twice as far up-down as the captures. Cause not established
  (lens or body stabilisation is a candidate); the check reports live view as it is.

Rewrite (`crates/strehl-ui/src/capture-stillness.rs`): the whole frame is registered (a
4x-reduced search, then Gauss-Newton with a gain and an offset), a frame whose quarters
disagree with the whole by more than half a live pixel is left out, and the result is
the rms movement over spans from 0.2 to 8 s, the drift in px a minute and the axis of the
movement over about a second. The longest exposure is the longest span over which half
the movement stays under a quarter pixel (ARGUED: a steady drift spreads a point over
0.29 of its movement in an exposure, a fast sway over 0.71). A drift over 1 px a minute
adds "still settling".

Replayed on the rig's three series (the ignored test `stillness_on_the_rigs_frames`):
"Moves 0.32 / 0.46 / 0.39 px within a second, mostly up-down; drift 0.2 / 1.4 / 1.1 px a
minute; exposures up to 5.1 / 1.1 / 1.6 s", every frame registered. Unit tests cover
sub-pixel shifts through brightness changes and a featureless centre, a non-rigid frame,
a fast sway, drift with a random walk, and a still series.

## 4. Highlight fusion was slow: dense, on the GPU

The owner shot a full highlight-pass stack of the slide (`stack-1795649995211-14989`, 11
planes, 6 highlight groups, every second plane) and found stacking very slow.

MEASURED with `STREHL_FOLD_TRACE=1` and `STREHL_HIGHLIGHT_REPORT` (the installed
engine): the render pass took 46.4 s, 3.4 s a frame, against 3.9 s with
`STREHL_HIGHLIGHT_FUSION=off`. The backlit slide is clipped at the base exposure over
most of the frame, so each frame replaced about 51 M sites. Plan X4 listed every one
on the CPU (find 0.6-0.85 s, gather 0.5-0.75 s, then building and sorting a 51 M-entry
list on one core, about 1.5 s) on the thread that feeds the GPU, one frame after
another, and uploaded the list (816 MB a frame).

Rewrite (same arithmetic, no list):

- **Weights where they lie.** A site's weight is the ramp of the brightest base
  photosite in a window about its pull. The two window maxima (the weight's and the
  pinned count's) are kept as padded per-photosite maps built by separable running
  maxima, exactly `Bright::max` at every floor position (test
  `the_window_maxima_are_brights_maxima_everywhere`), so each site is one lookup.
- **On the GPU** (`fold.wgsl`: `hl_bright`, `hl_dilate_h`, `hl_dilate_v`, `hl_blend`,
  `hl_variance`): the companion group is uploaded into one of two companion slots (a
  new binding; skipped when a slot already holds it), its channels assembled or
  demosaiced by the existing kernels (`sensel` reads the companion binding for an index
  with the top bit set), and each site blended where its weight is above zero: the
  companion sampled through its own pull exactly as `gather_value`, unquantised for a
  native site and quantised for a carried one, as the CPU's companion gather. The
  variance kernel reads the two greens' weights. Counts for the log come back through
  a small atomic buffer, read as each chunk finishes.
- **On the CPU** (`Fusion::apply_planes`): the same maps; the companion gathered over
  only the bands and 32-column blocks whose pulls can reach a bright tile; each site
  blended in parallel inside the gather's callback.
- **Ahead of the fold.** Each frame's ratio fit and its companion's shift are measured
  on the decoder threads as the frame is decoded (`highlight_fusion::warm`), into the
  render's caches; the fold thread's planning is then 3 ms a frame. The shift is still
  measured by the pass's first frame of each companion, as before. A run keeps its
  decoded companions and its measured shifts (by measuring frame and scale) from the
  lateral-colour preview pass to the render pass, and a pass starts decoding its first
  companions when it begins.

VERIFIED, bit for bit (`result.tiff` and the linear master), with the installed engine
as reference: the new GPU fold, the new CPU fold (`STREHL_GPU_FOLD=off`) and the old
engine agree on all three slide stacks; also with `STREHL_PIXEL_SHIFT_RESIDUAL=off`
(which demotes groups: a base group's member 1 alone on the first stack, three
highlight groups' on the second) and with `STREHL_CARRY_RGB=off`. The site counts in
the log are identical (559,475,065 sites on the highlight stack).

MEASURED, `strehl stack ... --merge pyramid --srgb` (preview pass + render pass, RTX
5090, 16 decoders; repeat runs vary by about 0.3 s on the GPU and 2 s on the CPU; the
first run of a new build adds about 3 s while the driver compiles the changed shader):

| Stack | Old engine | New | Highlights off |
| --- | --- | --- | --- |
| Highlight stack, GPU | 11.0 + 46.4 s | 5.2 + 4.8 s | 3.8 + 3.9 s |
| Highlight stack, CPU fold | 13.0 + 46.0 s | 8.4-9.0 + 19.9-21.8 s | 6.3 + 14.1 s |
| First slide stack, GPU | 4.5 + 14.7 s (fixed engine) | 3.9 + 3.9 s | |
| Second slide stack, GPU | 17.1 + 24.6 s (fixed engine) | 4.8 + 2.8 s | |

What remains on the GPU path is mostly decoding the highlight groups' 24 extra RAW
files (the fold waits on decoders) and their upload; on the CPU fold, the companion's
gather, which on this slide covers most of every frame. A stack with ordinary
specular highlights replaces far fewer sites.

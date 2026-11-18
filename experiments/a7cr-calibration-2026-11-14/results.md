# A7CR controller exposure/burst control and lens-capped dark campaign

**Status:** author verification; no independent review. Ledger row
`a7cr-calibration-2026-11-14`. Plan:
[2026-11-a7cr-pixel-shift-streaming-plan](../../docs/proposals/2026-11-a7cr-pixel-shift-streaming-plan.md)
stages A5 and C1 (darks only).

## Result

**VERIFIED (software, simulator):** The Pi controller accepts two new commands.
`exposure {iso, shutter}` sets manual ISO and shutter by the camera's own property
values, refused unless the camera offers the value and is in M; both are saved and
restored when the bridge releases the camera. `capture_positions {positions}`
captures an explicit list of focus positions approached once in the plan's
direction: one position repeated is a fixed-focus burst, a list of planes is a
retake. Positions must be monotonic in the capture direction so every plane is
reached from the same side. The state JSON now reports `exposure` (ISO, shutter,
f-number, offered values). 40 capture library tests pass, including a new
simulator test of exposure plus a three-frame burst and its approach position.

**VERIFIED (hardware):** the new controller and bridge are deployed on the Pi with
the existing rollback deployment (configuration, keys, marks and plan preserved):
controller `dafdc9a2ed8a0cd8...`, bridge `571ffb565158116...`. Exposure control
was exercised on the A7CR: 15 dark series at 13 ISO settings and three shutter
times, each restored to ISO 100, 0.6 s, four-shot afterwards.

**VERIFIED (hardware, 2026-11-14 day session):** `capture_positions` works on the
camera: fixed-focus bursts of 1 to 32 planes, single-shot and four-shot, at three
shutter times, each followed by a full restore of exposure, mode, focus, marks
and plan (checked after every run). The night's `054c:0d68` episode was the
camera powered off; once it was on again, `recover` reconnected.

**MEASURED, fixed (plan A5):** the capture manifest's top level now reports the
run's actual `pixel_shift_shots` and raw format (`sony-uncompressed` on the A7CR)
instead of the hard-coded `1` / lossless-compressed, plus `planned_planes`,
`planned_raws`, `capture_kind` (`plan` or `positions`) and an explicit authority
note; schema `strehl-capture-v2`. The desktop handoff still reads
`focus_positions` and `camera.pixel_shift_shots`, unchanged.

**Observation:** twice tonight the idle controller faulted with "Camera status
failed: USB transaction uncertain" during status polling, with no exposure in
doubt, after long idle periods. Explicit recovery worked the first time. The
second time the camera had powered off. Camera auto power-off while idle is
the likely cause; not established.

## Dark campaign

Lens capped, dark room, preview mean 1.1 of 255. Stabilisation and focus are
irrelevant to darks; each series is one controller stack with step 1. Analysis:
`cargo run --release -p strehl-raw --example a7cr-dark-analysis -- OUT DIR...`
([dark-analysis.rs](dark-analysis.rs)) over the declared active area 9504 x 6336
at (32, 20), f64 accumulation, decoded by `strehl_raw::decode` (the direct CFA
path, equal to the linked decoder on all 37 A7CR files checked; see
[a7cr-impl results](../a7cr-impl-2026-11-14/results.md)). Read noise is temporal
SD per photosite pooled as RMS over the channel; "median SD" is the median
photosite. DSNU is the master dark's spatial SD with the temporal share removed.
Row/column excess is the temporal SD of row (column) means beyond the pixel-noise
share. "Hot" uses a fixed 50 DN threshold on the master dark, so above ISO 800 it
counts noise outliers, not defects.

MEASURED, 2026-11-14, ILCE-7CR, f/5.6 lens setting, black 512, white 15360.
Single-shot unless labelled.

| Series | Run folder | Frames | R | G1 | G2 | B | G1 median SD | DSNU G1 | Row / column excess | Hot (>50 DN) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| iso100-0.6s-single | stack-1794645991941-10639 | 32 | 1.316 | 1.330 | 1.338 | 1.256 | 1.136 | 0.298 | 0.174 / 0.102 | 0 |
| iso50ext-0.6s | stack-1794646224061-11226 | 16 | 1.319 | 1.336 | 1.342 | 1.259 | 1.147 | 0.306 | 0.175 / 0.103 | 0 |
| iso125-0.6s | stack-1794646279022-11226 | 16 | 1.603 | 1.629 | 1.645 | 1.544 | 1.360 | 0.321 | 0.254 / 0.168 | 0 |
| iso160-0.6s | stack-1794646334587-11226 | 16 | 1.959 | 1.984 | 2.004 | 1.881 | 1.611 | 0.330 | 0.259 / 0.129 | 0 |
| iso200-0.6s | stack-1794646390130-11226 | 16 | 2.418 | 2.467 | 2.495 | 2.343 | 1.974 | 0.353 | 0.373 / 0.262 | 0 |
| iso250-0.6s | stack-1794646445728-11226 | 16 | 3.020 | 3.060 | 3.097 | 2.923 | 2.419 | 0.409 | 0.400 / 0.240 | 5 |
| iso320-0.6s | stack-1794646504038-11226 | 16 | 3.759 | 3.836 | 3.865 | 3.644 | 3.005 | 0.468 | 0.563 / 0.411 | 8 |
| iso400-0.6s | stack-1794646559590-11226 | 16 | 2.212 | 2.224 | 2.255 | 2.141 | 1.693 | 0.536 | 0.239 / 0.142 | 9 |
| iso500-0.6s | stack-1794646615055-11226 | 16 | 2.761 | 2.797 | 2.837 | 2.684 | 2.113 | 0.653 | 0.266 / 0.144 | 17 |
| iso640-0.6s | stack-1794646669791-11226 | 16 | 3.486 | 3.510 | 3.561 | 3.389 | 2.633 | 0.815 | 0.347 / 0.225 | 188 |
| iso800-0.6s | stack-1794646725108-11226 | 16 | 4.385 | 4.406 | 4.535 | 4.251 | 3.306 | 1.020 | 0.401 / 0.247 | 2006 |
| iso1600-0.6s | stack-1794646781346-11226 | 16 | 8.580 | 8.642 | 8.760 | 8.352 | 6.462 | 2.005 | 0.680 / 0.412 | 20921 |
| iso3200-0.6s | stack-1794646838907-11226 | 16 | 16.676 | 16.808 | 17.077 | 16.276 | 12.500 | 4.027 | 1.294 / 0.903 | 64985 |
| iso6400-0.6s | stack-1794646897331-11226 | 16 | 32.416 | 32.590 | 33.202 | 31.707 | 24.014 | 8.169 | 2.192 / 1.472 | 205597 |
| iso100-1/8s | stack-1794646957742-11226 | 16 | 1.290 | 1.305 | 1.314 | 1.233 | 1.109 | 0.315 | 0.146 / 0.037 | 0 |
| iso100-2.5s | stack-1794647005639-11226 | 16 | 1.348 | 1.363 | 1.371 | 1.287 | 1.181 | 0.332 | 0.172 / 0.096 | 13 |
| iso100-0.6s-fourshot | stack-1794647092116-11226 | 16 | 1.324 | 1.335 | 1.346 | 1.264 | 1.147 | 0.307 | 0.182 / 0.115 | 0 |

Findings:

1. **MEASURED: dual conversion gain switches at ISO 400.** Read noise in DN
   rises roughly in proportion to ISO from 100 to 320 (1.33 to 3.84) and drops to
   2.22 at ISO 400, then rises again in proportion (4.41 at 800, 32.6 at 6400).
   Do not assume the A7C II's switch point; this body's second base ISO is 400.
2. **MEASURED: ISO 50 is a pull of ISO 100**: the same DN read noise (1.336 against
   1.330) and DSNU. The profile's analogue base ISO is 100.
3. **MEASURED: the per-photosite noise distribution is heavy-tailed**, as on the
   A7C II: pooled RMS 1.33 DN against median photosite 1.14 DN at ISO 100 (17%).
   An injected model must state its basis.
4. **MEASURED: dark current is negligible at working exposures**: 1/8, 0.6 and
   2.5 s give 1.305, 1.330 and 1.363 DN at ISO 100, and no master-dark photosite
   is 50 DN above black at 0.6 s at ISO 100-200.
5. **MEASURED: black is 512.2-512.4 DN at ISO 100-3200**, with frame-to-frame
   drift of +-0.2 DN at ISO 100; at ISO 6400 the mean rises to 513.5.
6. **MEASURED: temporal row pattern noise** is 0.17 DN at ISO 100 (13% of pixel
   read noise), columns 0.10 DN.
7. **MEASURED: four-shot darks equal single-shot darks** (1.335 against 1.330).
8. **MEASURED: the margins outside the declared crop are real photosites**, not
   padding: same black, read noise and DSNU as the active area on every channel
   (the right margin about 10% noisier). Whether they are light-sensitive needs a
   lit frame (plan A3).

## Scene for captures 1 and 2 (owner setup, 2026-11-14)

Transparent resolution slide (black markings) about 25 mm above white paper,
f/5.6 lens setting, ISO 100, focus position 28001, continuous room lighting.
MEASURED from one RAW at 0.6 s ([scene-levels.rs](scene-levels.rs)): green median
137 DN and p99 1437 DN of 14848 DN headroom, so the scene is dim at the working
shutter. The target is tilted against the sensor: the centre and top right are
sharp, bottom left soft, top left clearly defocused. Neither matters for
captures 1 and 2; both matter for capture 3.

## Capture 1: photon transfer at ISO 100 (plan C1)

Focus moved 1500 units off the subject (strongly defocused in the live preview),
then three fixed-focus single-shot bursts with [ptc-sweep.py](ptc-sweep.py):
16 x 0.6 s (`stack-1794684207243-11226`), 32 x 2.5 s (`stack-1794684263347-11226`)
and 16 x 6 s (`stack-1794684439651-11226`); controller state restored afterwards.
Analysis [ptc-analysis.rs](ptc-analysis.rs): per-photosite temporal variance over
the declared active area, photosites within 5% of white excluded, weighted fit of
`var = r^2 + g S` over 30 DN to 85% of headroom. Cross-check
[pair-noise.rs](pair-noise.rs): two-frame differences with the scale removed per
32 x 32-site tile.

1. **MEASURED: green gain 0.4040 DN/e- at ISO 100** (G1 0.40401, G2 0.40398;
   G2/G1 0.99993; even and odd frames 0.40407 and 0.40404). Two-frame
   differences give 0.4039-0.4068 on the 0.6 s and 6 s series. Full well about
   36,750 e- (14848 DN headroom); read noise 1.334 DN = 3.30 e-.
2. **MEASURED: the light drifts 0.3-1.2% frame to frame**, more in blue than red.
   At 8000 DN a 1% drift adds twice the shot-noise variance, so drift removal is
   load-bearing. The 6 s series (0.34% drift) gives a flat `var/S` of 0.400-0.405
   from 1000 to 8000 DN; the 2.5 s series (1.0% drift) is the least reliable
   (0.416 alone). The global per-channel correction leaves negative intercepts
   (-1.2 DN^2 on green) where the darks give +1.78, so the read term is taken
   from the darks, not from this fit.
3. **MEASURED: `var/S` falls above about 9500 DN** (0.394 at 9560, 0.367 at 13000
   in the 6 s series): the response compresses near full well. The fit stops at
   85% of headroom; the noise model keeps the linear form.
4. **MEASURED: blue is processed in camera.** Blue's apparent gain is 0.37-0.38
   at every signal in every series (R 0.398-0.402), its dark sigma is 5.6% below
   green (1.256 against 1.334 DN, table above), and its temporal noise is
   correlated with its blue neighbours (+0.009 to +0.046) and with the two greens
   in its cell (+0.02), where R and G show 0.000 +- 0.009. A real per-colour
   conversion gain cannot correlate neighbours; a small digital mix into blue
   can. No comb in the code histograms (roughness at the Poisson level in every
   channel), so it is not a rescale. The profile uses one green-derived model for
   all four planes, which over-predicts blue variance by about 8%.
5. **Profile added (`strehl-core/src/profile.rs`, `ILCE-7CR`):** gain 0.4040 x
   ISO/100; read noise 3.30 e- below ISO 400 and 1.386 e- from ISO 400, each
   measured at its mode's base ISO so that the dark floor is exact at ISO 100 and
   400, at most 11% high elsewhere in a mode and never more than 0.6% low. Gain
   above ISO 100 is assumed proportional to ISO (UNVERIFIED). PRNU not measured.
   Test `the_a7cr_profile_reproduces_its_dark_floor_and_errs_high_within_a_mode`
   pins it to the dark table. A7CR stacks are now `Provenance::Profile`.
6. **MEASURED, independent check (plan C3):** capture 2's green witness under this
   profile gives mean `z^2` 0.986-1.002 on the eight 0.6 s groups and 1.025-1.051
   on the eight 1.6 s groups (it was 0.377 under the fallback). The witness's own
   self-fitted gain is 0.4096 and 0.4182: 1.4% and 3.5% above capture 1, biased
   high as expected from G1/G2 response differences and residual member motion,
   both of which grow with signal.

## Capture 2: static pixel-shift groups (plan D3, D4)

Eight four-shot groups at fixed focus at 0.6 s (`stack-1794683631859-11226`) and
eight at 1.6 s (`stack-1794683752817-11226`), [burst.py](burst.py), restored
afterwards. `strehl pixel-shift <run> --json`; reports in ignored
`outputs/a7cr-calibration-2026-11-14/capture2/`.

1. **MEASURED: the shift table is (0,0), (0,-1), (1,-1), (1,0)** for members 1-4 in
   all 16 groups (structure 0.997-0.998). It differs in order and sign from the
   table assumed by the synthetic generator; the code measures it per group and
   only requires the four CFA parities, so nothing depended on the assumption.
2. **MEASURED: members agree in exposure** within +-0.5% (gains 0.9949-1.0051).
3. **MEASURED: the groups are static and flicker-free at the witness:** fitted
   `z^2` 1.00-1.02, tile p50 0.99-1.01, tile p99/median 1.09-1.37.
4. **MEASURED: residual member misregistration is real but small.** Whole-frame
   witness pair shift 0.046-0.127 photosite. The same regression per image
   quadrant (new `pair_shift_quadrants`) puts the estimator's own whole-frame noise
   at about 0.012; the group-to-group scatter is 0.02-0.05 (two to four times
   that), so members genuinely move by a few hundredths of a photosite between
   shots. A systematic x component of about -0.05 repeats in every group at both
   exposures, and a rotation of about 1e-5 rad (about 0.06 photosite at the
   corners) repeats at both exposures with opposite sign for the two diagonal
   member pairs, which points at the sensor-shift mechanism.
5. **Tolerance moved from 0.1 (provisional) to 0.2 photosite**
   (`PAIR_SHIFT_TOLERANCE_PX`): 5 of the 16 good groups failed 0.1; all pass 0.2.
   The tile-ratio tolerance stays 2.5 (static 1.09-1.37; wrong-member placebo
   4.20).
7. **MEASURED: disturbed groups (same scene and focus, 0.6 s, owner moving).**
   Walking in the adjacent rooms is what breaks pixel shift on this rig; tapping
   the table does not.

   | Condition | Run folder | Groups passing | Worst pair shift | Tile p99/median | Failure kinds |
   | --- | --- | --- | --- | --- | --- |
   | Static (two runs above) | | 16 / 16 | 0.127 | 1.09-1.37 | none |
   | Careful walking | `stack-1794686724346-11226` | 2 / 6 | 0.370 | 1.16-7.03 | one member about half a photosite off (offsets fail the parity check); one member translated 0.37; two local (3.44, 7.03) |
   | Regular walking | `stack-1794687317465-11226` | 2 / 6 | 0.372 | 1.49-17.84 | translations 0.26-0.37; local up to 17.8 (z^2 mean 3.41) |
   | Tapping the table | `stack-1794687527310-11226` | 4 / 4 | 0.111 | 1.20-2.37 | none (one group at 2.37) |

   Local failures concentrate on the steepest detail (the slide's top edge over
   bright paper, the sharp top-right star, the bottom-left star centre): small
   misregistration multiplied by large gradients, so the tile ratio is
   scene-dependent. A per-tile displacement map in photosites would not be; it is
   the natural next form of this check. Tolerances stay 0.2 photosite and 2.5:
   every static group passes and every walking failure is caught, but whether the
   passing walking and tapping groups (tile ratio 1.81 and 2.37) are visibly worse
   in an assembled image is untested (plan E/F).
6. **MEASURED (plan A3): the crop margins are light-sensitive.** On the 32 lit
   frames the margin means are 588-1922 DN against black 512 (top margin
   brightest, under the bright paper strip), with active-like noise. They are
   ordinary image photosites the camera crops; the declared crop stays the image.

## Capture 3: paired stacks of a coin cell (plan B4, E, F, S1)

Owner setup: CR-type coin cell, dimpled face with markings up, on the slide;
light increased, 2.0 s, ISO 100, f/5.6 lens setting.

1. **Bounds (MEASURED).** A coarse live-view sweep ([focus-sweep.py](focus-sweep.py),
   61065-63065 step 50) put the face's best focus near 61715 and the falling rim
   down to about 61115; the eyeballed 62065 was about 350 units behind the face.
   The camera's magnifier does not change the PTP live-view stream, so depth of
   field was measured on RAWs: 21 single-shot frames 61635-61835 step 10
   (`stack-1794688969510-11226`), half-resolution green Laplacian energy per tile.
   The face is slightly domed (best focus 61715 at the edges, 61795 at the
   centre) and the sharpness peak is 80-120 units wide at half maximum. Exposure:
   0.3% of greens clip, all on specular dimple highlights.
2. **Captured through the ordinary plan and Start path** ([capture3.py](capture3.py)):
   61050-61898, step 8, 107 planes, approach 128, settle 500 ms.
   Single-shot `stack-1794689213508-11226` (107 RAWs, 566 s, 6.1 GB); four-shot
   `stack-1794689780304-11226` (428 RAWs, 1483 s including a 1.5 min owner
   pause at plane 105, 25 GB). Both complete. The new marks and plan were left
   on the controller.
3. **VERIFIED: `strehl follow` ran live on the four-shot capture**, admitting each
   plane on its durable receipts and checking it in 0.32 s median (0.36 s p95)
   against a 13.9 s capture cadence; it ended on `result.json` and printed a
   36-position `capture_positions` retake.
4. **MEASURED: 71 of 107 groups pass; 36 are demoted** (13 for pair shift
   0.20-0.34 photosite, 23 for the tile ratio 2.58-11.0). The whole-run median
   pair shift is 0.10-0.16 per block of planes, against 0.08 on the static
   slide, so this run's members moved more (2 s exposures and a 14 s group
   cadence against 0.6 s and about 8 s). Tile-ratio demotions concentrate in
   planes 65-102, where the face is in focus: there even median tiles rise
   (`z^2` p50 1.07-1.37), because 0.1-0.15 photosite of misregistration on
   sharp specular texture is 2-3 times the noise. The check measures something
   real; whether such a group is still better than demosaicing one member is
   what decides the tolerance, and that is the E/F comparison this paired
   capture exists for. Retaking would not help while the member motion is at
   this level.
5. **Fixed (failing input exercised):** the witness ignored the white level, so
   a highlight clipped in one member counted as disagreement. `MemberView` now
   carries `white`, and sites with either green sample or a gradient neighbour
   within 5% of white are skipped (`CLIP_FRACTION`); test
   `clipped_samples_do_not_count_as_disagreement` covers the clipped case and
   its below-clip control. On this run it moves one group (71 -> 72 pass): not
   the cause of the in-focus demotions.

## Captures still needed (owner)

None for this plan's calibration and paired stacks. The razor blade was not
included in capture 3; its neutral-edge colour test can use the slide's neutral
markings instead, or one later stack.

## Commands

```text
python -X utf8 experiments/a7cr-calibration-2026-11-14/darks.py --frames 32 --label iso100-0.6s-single
python -X utf8 experiments/a7cr-calibration-2026-11-14/campaign.py
cargo test --locked --offline -p strehl-capture --no-default-features --lib
wsl -u root bash .../experiments/a7cr-calibration-2026-11-14/build-arm.sh
python -X utf8 experiments/a7cr-calibration-2026-11-14/deploy.py
cargo run --release -p strehl-raw --example a7cr-dark-analysis -- outputs/a7cr-calibration-2026-11-14/darks.json <17 run folders>
python -X utf8 experiments/a7cr-calibration-2026-11-14/burst.py --frames 8 --shots 4 --label static-ps-0.6s
python -X utf8 experiments/a7cr-calibration-2026-11-14/burst.py --frames 8 --shots 4 --shutter 1048586 --label static-ps-1.6s
python -X utf8 experiments/a7cr-calibration-2026-11-14/ptc-sweep.py --defocus 1500 --series 16:393226 32:1638410 16:3932170 --label ptc
cargo run --release -p strehl-raw --example a7cr-ptc-analysis -- OUT.json 1.33 <three ptc run folders>
cargo run --release -p strehl-raw --example a7cr-pair-noise -- <frame 1> <frame 2>
cargo run --release -p strehl-raw --example a7cr-scene-levels -- OUT_DIR RAW...
strehl pixel-shift <run> --json report.json
```

Captures 1 and 2 add about 6.6 GB and capture 3 about 33 GB (seven run folders, including two one-frame scene tests). Raw dark captures (about 9 GB) are in `D:\StrehlCaptures` under the run folders
above, read-only. Analysis JSON, before/after controller states and the deployment
receipt are in ignored `outputs/a7cr-calibration-2026-11-14/`.

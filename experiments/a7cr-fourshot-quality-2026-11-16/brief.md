# A7CR four-shot quality: investigation brief (registered before any measurement ran)

Owner request (2026-11-16): find what would further improve image quality on
the A7CR four-shot pixel-shift path. Investigate and experiment; do not
implement in the product. Deliverable: a proposal for a later implementing
agent, `docs/proposals/2026-11-a7cr-four-shot-quality-improvements.md`.
Ledger row `a7cr-fourshot-quality-2026-11-16`.

## Bounds

- No product code changes, no new captures, no commits.
- Inputs, all read-only: scarab four-shot run
  `D:/StrehlCaptures/stack-1794786793543-11226` and its single-shot pair
  `stack-1794785495615-11226`; calibration bursts and darks listed in
  `experiments/a7cr-calibration-2026-11-14/results.md`; the prototype's
  decoded member cache `outputs/scarab-fp/cache4`; existing renders in
  `outputs/scarab-rgb/`, `outputs/scarab-merge/`, `outputs/scarab/`.
- New renders only with the existing release binary
  (`target/release/strehl.exe`, build `cbca976b7e96-dirty` of 2026-11-16),
  one at a time (peak 22 GB each). Outputs under ignored
  `outputs/a7cr-fourshot-quality/`.
- Stop a question when its size is bounded well enough to rank it; a
  proposal needs a measured or derived size, not a finished design.

## Prior work read

- `experiments/a7cr-full-potential-2026-11-14/results.md` (all sections),
  `a7cr-calibration-2026-11-14/results.md`, `a7cr-impl-2026-11-14/results.md`.
- `crates/strehl-core/src/restore.rs` (the gather-kernel restoration and its
  negative verdict on A7C II single-shot stacks), M95-kernel, M95-resample,
  BUILD-SHARP (resampling kernel 18.6 % of blur variance; Lanczos-3 a null).
- M71 and M90 (A7C II PRNU 0.31 % per green photosite; warped fixed pattern
  correlates 0.31-0.68 between adjacent frames and decays to zero by 6-22
  frames; no flat-field correction exists in `crates/`).
- `python scripts/research.py search` for: PRNU flat field fixed pattern;
  resampler Catmull-Rom Lanczos gather MTF; super-resolution drizzle
  sub-pixel (no matches); chroma luminance cross-channel.

Old verdicts were measured on the A7C II, single shot. They are hypotheses
here, as the full-potential brief already argues.

## Questions, instruments, controls

Scoring instrument unless stated: odd/even half-stacks of one capture
(`STREHL_FRAME_PARITY`), 256 px in-focus tiles, cross-spectrum = signal,
auto minus cross = noise (`compare-colour.py`, `evaluate.py pair_spectra`).
Known blind spot: anything both halves share that is not scene (fixed
pattern, deterministic artefacts) counts as signal.

| # | Question | Instrument | Control or placebo | Fooled by |
| --- | --- | --- | --- | --- |
| Q1 | Do red and blue carry fine detail that the output discards, and does a joint three-channel filter raise fine-band signal-to-noise over green alone? | Cross-channel spectra of the raw-carry halves (`h-f-carryraw-*`); filter designed on half the tiles, scored on the other half | One channel displaced 8 px before the joint filter (must lose the gain); per-channel filter as the no-borrowing baseline | Fixed pattern shared by halves; chromatic subjects (one subject here) |
| Q2 | How large is the A7CR's pixel response non-uniformity, and does it survive into four-shot stacks? | Split-half covariance of high-passed mean frames of the fixed-focus defocused bursts, against signal level; the same pattern looked for in scarab members | Covariance with one half rolled by a few photosites (must vanish); dark series (no signal: must read the dark fixed pattern only) | Scene texture that survives the defocus; dust (fixed too, and wanted) |
| Q3 | What does the four-tap Catmull-Rom gather cost per sub-pixel phase, and is that visible as a spatial pattern? | Kernel responses by phase (closed form); local high-pass noise power of a single gathered frame against its sub-pixel phase field | A frame gathered at the reference (identity: no pattern); phase field rolled | Scene detail in the noise map (use defocused areas, shot-noise normalised) |
| Q4 | Why does depth-guided fusion lift dark areas, and is the measured lift real? | `halo.py` with the mask taken from the other half (selection independent of the scored noise); lift against level and distance | The carry arm (no fusion) under the same independent mask must read 1.00 | Mask selection on the scored image; genuine detail in gaps |
| Q5 | Does the half-resolution site-plane pyramid send the finest full-resolution detail to coarse levels (aliasing inside each site plane), and does fusion lose it there? | Radial signal ratio fusion / election by frequency on existing halves, against the predicted level boundaries 0.375 and 0.4375 cycles/px | Same ratio for restore / election (a smooth filter: no steps) | Tile set; fusion's own level-dependent widths |
| Q6 | Does member-to-member exposure or position mismatch leave a two-photosite-period pattern in assembled output? | Power at the three Nyquist points of flat tiles against neighbouring bins; per-channel member gains from the member cache | Single-shot render (no assembly); a planted pattern of known amplitude | Demosaic structure in single-shot renders |
| Q7 | Do the frames near a point's focus sample it at well-spread sub-pixel phases (enough for super-resolution beyond the 0.5 cycles/px grid)? | Sub-pixel phase of each plane at tile centres from the solved alignment, over the planes within the coherent width | Phase coverage at the scale centre (expected poor) | Alignment error (0.18 px between neighbours) |
| Q8 | What defects does the eye find in the current default output? | Native crops, one display transform, origins recorded | Same crops of the single-shot render | Viewer resampling (crops at or under 400 px) |

A result that does not separate from its control is reported as such.
Sizes are properties of one matte subject and one rig setting.

---

# Round 2 (registered 2026-11-16, before any round-2 measurement ran)

Owner request (2026-11-16, after round 1): keep looking for quality
improvements on top of those already proposed; novel territory is allowed;
consider the whole chain from first principles. Same bounds as round 1 (no
product code changes, no new captures, no commits). Ledger row
`a7cr-fourshot-quality-r2-2026-11-16`. Results go to
[results-round2.md](results-round2.md); recommendations extend the same
proposal.

Approach: walk the chain from photons to file and ask at each stage what
information is lost or what error is added, then measure the candidates that
are not already in the proposal. Stages: exposure and sensor response;
sensor pattern and defects; member assembly and rig stability; frame
registration; which frames reach each output coefficient (the merge);
colour registration; restoration; what the eye finds.

Old results (A7C II, or the specular coin on the A7CR) are hypotheses here
and are re-measured on the scarab four-shot run where they bear on a
question.

## Prior work read for round 2

- Round 1 results and proposal (this folder).
- `a7cr-calibration-2026-11-14/results.md`: darks (no photosite 50 DN above
  black at 0.6 s, ISO 100; offset pattern 0.30 DN; temporal row noise
  0.17 DN), photon transfer (`var/S` falls above 9 500 DN), member
  residuals of static groups (0.05-0.13 photosite).
- `a7cr-full-potential-2026-11-14/results.md`, "Axial colour investigation"
  (coin, single-shot and member 1): frames one apart sit 0.18 px from each
  other and five apart 0.53 px; a similarity per pair leaves 0.08 and 0.33;
  the rest is largely one spatial pattern; red 5.5 frames from its own
  focus had lost 6-13 % of plane amplitude on that tenfold-oversampled
  stack; the finest red could not be borrowed because the gather had
  demosaiced it against that frame's green (not true of carried four-shot
  colour).
- Product diagnostics available without code changes:
  `STREHL_FRAME_PARITY=K-K` (one gathered group, 6 s),
  `STREHL_PYRAMID_WEIGHT_DUMP` (per-band participation ratio and winner),
  `STREHL_OPTICAL_RESTORE_DUMP`, `STREHL_FUSION_DUMP`.

## Questions, instruments, controls

| # | Stage | Question | Instrument | Control or placebo | Fooled by |
| --- | --- | --- | --- | --- | --- |
| R1 | Sensor | Can the response map be estimated from the stack's own raw frames, so the flat field needs no capture? | Per photosite, the mean over the stack's 784 raw frames of (sample / local same-colour smooth), weighted by local smoothness and level; scored by covariance with the map from the calibration burst of another day, normalised by each map's split-half covariance | The self map rolled (5, 3) photosites (must read zero); the burst-with-burst and stack-with-stack split halves as the ceilings; by radius (the scene barely moves on the sensor near the centre) | Scene detail that stays on the same photosites; the burst map's own noise (handled by split halves) |
| R2 | Exposure | How much of the sensor's range does the stack use, and is the response linear over the range a brighter exposure would use? | Percentiles of the raw members over the whole stack per channel; ratio of the three calibration bursts' means (0.6, 2.5, 6 s, same scene) against level | Ratio flat over 500-8 000 DN (the range the photon-transfer fit found linear) | Lamp drift between bursts (a global factor; only the shape against level counts); black-level error at the low end |
| R3 | Registration | How far apart do gathered neighbouring frames sit on this matte subject, and is what remains a global, a smooth or a random field? | Per-tile displacement (phase ramp of the cross-spectrum, green) between single-group renders 1 to 8 planes apart, in-focus tiles; similarity fit, then the residual's spatial correlation | A planted sub-pixel shift recovered; the same measurement between red and green of one frame as a noise yardstick | Blur difference between frames (reads short); one-dimensional texture |
| R4 | Merge | What do the frames around a point's focus hold, by frequency and channel: (a) where each channel's focus sits and what red and blue lose by being read at green's plane; (b) the matched-filter bound on signal-to-noise against what the election and the fusion deliver; (c) the same with each frame registered locally | Series of single-group renders around one plane; per in-focus tile, each frame's transfer against a reference built from the other parity's frames (independent noise), radial bins | Transfer must peak at the tile's own focus plane and fall both ways; tiles rolled against their focus planes (must flatten); the series' own odd/even election as the delivered baseline | Reference noise bias (other-parity reference); tiles spanning several depths; registration error read as defocus (arm c separates it) |
| R5 | Merge | How many frames does the default election average into each coefficient, by level and by local texture, and how much noise would a signal-adaptive window along the focus axis remove at equal detail? | `STREHL_PYRAMID_WEIGHT_DUMP` on the default render (participation ratio per band); an adaptive-window prototype on the R4 tile stacks scored by noise and by error against the independent parity | Participation ratio of a one-group render must read 1; the prototype with its window fixed must reproduce the fixed-window arm | Selection bias (weights correlated with the noise they weigh); the prototype's bands are not the product's |
| R6 | Restoration | Does a locally adaptive restoration (gain withheld where a neighbourhood holds no detail above noise) beat the global filter? | Post-merge prototype on existing half-stack pairs: error of each restored half against the other half's restored content by region class (smooth, textured), and noise in smooth regions | The adaptive arm with its mask forced to one must equal the global arm; mask taken from the other half versus from the scored half (selection bias) | A mask that follows noise; region classes chosen on the scored image |
| R7 | Colour | Is the channel displacement left in the output (blue 0.21 px in y, red 93 ppm radial, round 1) a per-stack constant that a runtime fit removes, and is it the blue rim? | Per-tile channel displacement on the default render and on single groups; post-merge prototype resampling red and blue by the fitted model; fringe by edge orientation; crops | The fitted model with reversed sign (must be worse); model fitted on half the tiles, scored on the other half | Channels' independent fine detail (round 1 Q1) makes per-tile displacement noisy; blur differences between channels |
| R8 | Rig | Is member motion on this run drift or jitter, and does it bound blur inside one 0.6 s exposure? | Time series of the measured member residuals over 196 groups (`members.jsonl`): spectrum, increments between consecutive members | The static-slide groups of the calibration campaign (0.05-0.13) as the floor | The residual estimator's own noise (0.012 whole-frame) |
| R9 | Sensor | Are there response outliers (dead or weak photosites) large enough to draw trails? | Tail of the response map; positions checked in the default render | Map rolled | Dust in the calibration burst |
| R10 | Eye | What defects does a wider visual survey of the default render find? | Native crops at 2-4x of depth edges, bristles, highlights, deep shadows, smooth areas, the frame border; one display transform plus a shadow-lifted copy | Same crops from the single-shot render and from a one-group render | Viewer resampling (crops under 400 px) |
| R11 | Optics | What would a short-wavelength detail exposure buy (pixel shift samples blue fully)? | DERIVED from the fitted cutoffs and measured per-channel signal-to-noise by frequency | none (no capture) | Subject reflectance differs by wavelength; lens correction in the violet |

Stop rule as in round 1: a question stops when its size is bounded well
enough to rank it. A result that does not separate from its control is
reported as such.

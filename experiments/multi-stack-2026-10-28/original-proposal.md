# Multi-bracket stacking: repeat passes, super-resolution and depth-aware mosaics

Oct 28, 2026 · @Chris Caruso

## Summary

Strehl should accept several brackets of one subject and solve and fold them as one frame set, paired by focus position rather than by filename order. That single change enables two capabilities: repeat passes of one pose, and mosaics warped by depth.

- **Repeat passes (Part A).** The first gain is noise in in-focus detail, where one bracket gives each site only about 3–6 sharp frames. It is collected only if same-focus frames are averaged before selecting across focus. Super-resolution comes second: a nudge between passes fills the field centre, where breathing gives no sub-pixel diversity, but the optics limit it mostly to red/blue resolution and moiré removal.
- **Mosaics (Part B).** Stacking each tile and then stitching cannot be registered, because each stacked tile is a perspective view from its own position. At about 2.7×, depth-dependent parallax reaches tens to roughly 200 px per tile step. The fix is a depth-dependent warp per tile, driven by each tile's own focus-index map. Same-focus frames in the overlaps calibrate it, because their sharp content sits at a single depth.
- **Shared groundwork.** Multi-directory input, focus-keyed pairing, cross-bracket edges in the global solve, one smoothness track per bracket, and per-bracket reporting. Today's code assumes one directory in filename order, an index-span edge ladder and a single smoothness track.

Recommended order: shared groundwork, a two-pass detail map (FRC), same-focus averaging, mosaics once the fold tiles spatially, and super-resolution last, behind a kernel-regression merge.

Nothing here is a measured quality gain. Every gain is DERIVED or ARGUED and gated by the checks below. Rail capture, rotation panoramas and 3-D reconstruction stay out of scope.

## Evidence and labels

Nothing here was measured for this proposal: no RAW was opened and nothing was rendered. Each claim carries one of the repository's labels.

- **MEASURED** — a corpus measurement, with its report named beside the number.
- **DERIVED** — arithmetic from cited constants, reproduced by the script on the Derivations tab.
- **ARGUED** — reasoning without a number.
- **UNVERIFIED** — a hypothesis nobody has tested.

Code facts come from `main` at `4813e46b` (2026-10-26); file:line references point at that commit. Derivation inputs: λ = 0.55 µm, 5.12 µm pitch, m = 2.7198 (M84b), pupil factor p = 1.31–1.94 (M88), 7032 px frame width, 30% tile overlap. The entrance-pupil-to-subject distance D is not measured, so distances are given for D = 120, 200 and 260 mm.

Script and full output: Derivations

## What the code assumes today

The pipeline assumes one bracket in at least thirteen places. The alignment graph and the track prior break first: a second pass can be left unplaced, and interleaved passes would have their offsets smoothed away.

| Assumption today | Where | What multi-bracket needs |
| --- | --- | --- |
| One directory of `.ARW`, sorted by filename as capture order | `strehl-cli/src/lib.rs:1345` (`raw_paths`) | A session of brackets, each with a role (repeat, interleave, tile, exposure) and an optional stage offset |
| Pairwise edges by index span `[1, 2, 4, …, 128]` | `align_cmd.rs:158` (`DEFAULT_SPANS`) | Cross-bracket edges chosen by focus proximity; same-focus partners in two 299-frame passes sit 299 indices apart |
| Only the reference's measured connected component is placed; other frames are refused and dropped | `align.rs:2254`; ARCHITECTURE §7 | Cross-bracket edges dense enough that every bracket joins the component, with refusals reported per bracket |
| Second-difference track prior in frame index, on by default (λ = 1, Huber 1 px), because breathing is smooth in focus position | `align.rs:1945`; `align_cmd.rs:723`, `:1529` | One track per bracket and no prior rows across bracket boundaries |
| Warp-map cache keyed by the canonical capture directory and solve config | `align_cmd.rs:1499` | A key over the ordered set of bracket directories, roles and pairing config |
| Geometry, levels, camera, ISO, white balance, colour matrix and noise model read from frame 0 | `merge_cmd.rs:7048–7066` | Per-bracket calibration where ISO, exposure or white balance differ; mixed bodies refused |
| A frame whose black or white level differs is an error | `merge_cmd.rs:1599` | Keep, checked per bracket |
| Geometry is a 4-parameter similarity; no affine or homography | ARCHITECTURE §7 | Unchanged for repeat passes; a per-tile depth-dependent field for mosaics |
| Fine-band exponents 7.68, 8, 8 — "already close to winner-take-all" | `pyramid.rs:1426`, `:1446` | Same-focus averaging before selection, or the estimator backend, to collect repeat-pass gains |
| Catmull-Rom gather destroys most sub-pixel motion (planted gain 0.29 against 0.98) | ARCHITECTURE §7 | Super-resolution on the kernel-regression merge (B §6.5), never through the gather |
| Photometric gain is estimator-only; `--photometric` refused on pyramid | ARCHITECTURE §6 | A pyramid-path gain with noise propagation, for exposure passes and tile flat-fielding |
| The pyramid computes no focus field | ARCHITECTURE §8 | A per-tile focus-index map from a prepass, for mosaic warps |
| Frame-chunked fold, no spatial tiles, 6 GiB budget | `stack.rs:62`; ARCHITECTURE §9 | Spatially tiled canvas accumulators beyond about 2×1 tiles |

## The focal-plane argument

What is sharp in a frame lies close to that frame's focal plane, so it moves almost rigidly when the camera moves sideways. Its misregistration grows with how far the camera moved, not with how deep the subject is. Both parts of this proposal rest on that.

For a lateral move, a point δz off a reference plane shifts relative to that plane by (plane plus parallax, small angles; DERIVED):

```latex
\Delta = s \, \frac{\delta z}{D}
```

Here s is the plane's image shift between the two positions in px, and D is the entrance-pupil-to-subject distance. With D = 120–260 mm (DERIVED):

| Case | s | δz | Residual Δ |
| --- | --- | --- | --- |
| Repeat pass, nudge between passes, sharp content | 10–50 px | ≤ 0.1 mm | ≤ 0.04 px |
| Same nudge, defocused content | 10–50 px | 5 mm | 0.2–2.1 px, under heavy blur |
| Mosaic, one shift per frame, adjacent focus slices | 4,922 px | 20–60 µm | 0.4–2.5 px |
| Mosaic, stack each tile then stitch | 4,922 px | 1–5 mm deep subject | 19–205 px |

- **Repeat passes need no new geometry.** One similarity per frame stays exact, to hundredths of a pixel, for everything sharp. The 0.1 mm bound is generous; the depth of field at f/5.6 and 2.7× is about ±0.02 mm for a 2 px blur circle.
- **Mosaics need a depth-dependent warp,** since a tile step is a hundred times a nudge. One shift per frame still leaves adjacent slices 0.4–2.5 px apart, and stacked tiles disagree by up to 205 px.
- **The argument also says how to measure that warp.** A same-focus pair in a tile overlap isolates one depth, so its offset is the parallax for that slice, free of the multi-depth bias that a whole-image correlation carries.

Limits (ARGUED): an axial move adds a scale, which a similarity absorbs; a tilt adds projective terms; field curvature bends the focal surface (M-PHASE0-CURV), cancelling only on the overlap's bisector. Occlusion order also changes between positions at depth edges, and no warp can supply content that neither view saw.

## Part A — Repeat passes: noise first

A second pass mainly lowers noise in in-focus detail, which one bracket cannot average today. Collecting that gain needs a merge that averages same-focus frames before it selects across focus.

**Why one bracket leaves it on the table.** Each site is sharp in only about 3–6 frames (DERIVED, sota-path C1). The fine bands run at exponents 7.68, 8 and 8, which `pyramid.rs:1446` calls close to winner-take-all. So fine detail carries roughly one capture's noise, and the corpus already measures a selection premium on mid-frequency coefficients (facts 1843–1845, 1849).

**What K passes buy.** K sharp observations per site at each focus, with independent noise: frame-to-frame sensor noise is independent to within 1% (MEASURED, M62). Averaging them scales noise by 1/√K — 0.71 at K = 2, 0.58 at K = 3, 0.50 at K = 4 (DERIVED, ideal).

**Two capture modes, two different gains.**

- **Repeat** — the same commanded focus ladder each pass. Same-focus frames are averaged, so the gain is noise.
- **Interleave** — the second pass offset by half a step (captures-needed §13a). Focus sampling doubles, so fewer sites miss their focus peak; today 48.7% miss it (MEASURED, M33). The gain is sharpness, not noise.

**On the estimator backend this already works** once input and alignment do (ARGUED). Admission averages every frame within the gate of the winner, and on a static burst gate 4 admits 29.5 of 30 frames for a 5.43× noise reduction against an ideal 5.48× (MEASURED, `merge.rs` calibration ladder).

**On the pyramid backend it needs a slice step.**

1. Pair frames across passes by focus: same slice when fitted breathing scales differ by under a quarter of a focus step, otherwise treat them as interleaved (ARGUED threshold; check P1).
2. Average each slice after registration, with inverse-variance weights from the injected model. Decomposition is linear, so this equals averaging band coefficients.
3. Fold the slice as one input with a propagated noise model. A K-frame average, σ²/K, is exactly the existing model with gain g/K and read noise RN·√K (DERIVED, checked numerically). Propagated, never re-estimated, so AGENTS rule 3 holds.
4. Refuse the average per tile where passes disagree beyond the model (subject creep, light drift), falling back to selection.

Memory grows by K frame workspaces, not N, so the fold stays a fold. Same-focus pairs across passes also make the best alignment edges: their blur matches, which removes the defocus mismatch behind M6's correlation bias (ARGUED; check P2).

## Part A — Super-resolution from repeat passes

Repeat passes give super-resolution sub-pixel diversity across the whole field, but at f/5.6 the optics stop at or just above sensor Nyquist. The realistic gain is full-resolution red and blue plus alias-free fine structure, not a 2× luma image.

**Diversity.** Breathing sweeps sub-pixel phase in proportion to radius: about 1.6 px across five sharp frames at r = 1000 px, 0.5 px at r = 300, and nothing below r ≈ 150–300 (DERIVED, sota-path C1). An offset between passes is uniform across the field, so it fills that central dead zone. A hands-off rerun adds almost nothing: random jitter is 0.075 px (MEASURED, fact 9).

**Identifiability.** Unfolding aliases needs well-conditioned sub-pixel phases among the frames sharp at a site (DERIVED, sota-path C1). Each pass with a distinct offset adds a row to that system. The merge reports the condition number per tile and refuses super-resolution per pixel where it is poor.

**What the optics allow.** These are diffraction-only upper bounds. The rig measures about 2.2× softer than diffraction alone (BUILD-SHARP), and fact 1149 puts the real cutoff at 87 cy/mm, below sensor Nyquist; M88 could not adjudicate between the two.

&#91;embedded content: DERIVED · diffraction only, λ 0.55 µm, m 2.7198 (M84b), pupil factor 1.31–1.94 (M88)\]

The blue band is f/5.6 across the measured pupil-factor range; grey is f/11, which passes nothing above 69 cy/mm.

- At f/5.6, red and blue are sampled at half density each way, where the optics still pass 43–55% contrast: that is real, recoverable alias.
- Luma at sensor Nyquist passes only 2–17%, and nothing past 106–135 cy/mm. A 2× lattice holds full-resolution red, blue and green diagonals; luma beyond the cutoff cannot be recovered.
- At f/11 the cutoff, 54–69 cy/mm, sits below green's diagonal Nyquist, and super-resolution buys almost nothing (consistent with M5).

**Merge requirement.** Super-resolution needs kernel regression of raw CFA samples onto an arbitrary output lattice, sampled through the warp (B §6.5, sota-path C1). The Catmull-Rom gather destroys sub-pixel motion, so it cannot be bolted onto the pyramid fold. Relative placement among contributing frames must reach about 0.1–0.15 px; same-focus cross-pass pairs are the easiest case of that.

**Capture guidance.**

- Body SteadyShot and lens OSS off. IBIS added a per-frame change that is not a rigid translation and failed the nontranslation gate at 0.1077 (MEASURED, captures-needed).
- Offset between passes, never during one. Any move works: luma needs the fractional pixel part, red and blue need the integer part's parity. One pixel is 1.9 µm at the subject at 2.72×, so a tap on the stage is plenty.
- Four or more passes cover the red and blue parities near the centre; breathing helps off-centre (ARGUED).
- f/5.6 or wider. Stopping down removes the very signal this recovers.

The merge reports what it achieved, per pixel: phase coverage and the number of frames contributing above native Nyquist (B §6.5's `phase_coverage` and `sr_contributing_frames`).

## Part A — Other uses of repeat passes

The same plumbing turns two passes into a per-subject map of reproducible detail, and differently set passes into HDR, aperture-diverse depth, separable reflections or photogrammetry input.

- **Reproducible-detail map (FRC).** Merge each pass separately, register them, and compute Fourier ring correlation per tile. Frequencies where two independent merges agree are detail that reproduces; noise and invented values do not. This is the repeat-pair instrument behind the 407-frame session, already GO to commission on synthetic and development data (M-FRC-VIABILITY). Sota-path D8 builds the same map from interleaved half-stacks of one bracket; two full passes give each arm the delivered merge's focus sampling.
  - As a user overlay, name it "reproducible detail", not resolution. M-FRC lists three blind spots: processing common to both arms is invisible, the windowed estimator has signed residuals, and fixed-pattern noise shared by both passes inflates agreement.
  - A nudge between passes moves fixed pattern relative to the scene and so decorrelates it (ARGUED), but adds resampling loss unless both arms render to one lattice.
  - It fits the README's promise to make the evidence explorable, at the cost of two merges.
- **Exposure-varied passes for HDR.** The README states that HDR export does not fuse exposure brackets. With passes at different shutter speeds, inverse-variance weights plus refusal of clipped samples make the fusion fall out of the noise model (ARGUED). It needs a per-pass gain on the pyramid path, scaling gain by c with read noise unchanged (ARCHITECTURE §6), and a per-pass noise model if ISO changes across the dual-gain step at ISO 400.
- **Polariser and lighting passes.** Passes with the polariser rotated or the lights moved register exactly like repeats, but stay separate aligned layers. Crossed minus parallel separates specular from diffuse; several light directions allow relighting or surface normals (ARGUED).
- **Aperture-varied passes.** A second bracket at another aperture is sota-path C11: blur-ratio depth, smaller defocus discs at occlusion edges, and PSF calibration. Merging it needs exactly this groundwork plus per-frame N\_eff, which the noise and MTF bookkeeping already carries.
- **Different angles.** Large viewpoint changes are 3-D reconstruction, not a 2-D merge. A focus-driven bracket keeps the entrance pupil fixed (F §5.2), so each stack is a single-viewpoint image plus a focus-index map. Exporting both with the reference geometry gives photogrammetry tools clean input; reconstruction itself stays out of scope.

## Part B — Mosaics

A mosaic needs a depth-dependent warp per tile; stacking each tile and stitching the results cannot be registered at macro distances. The warp is calibrated from same-focus frames in the overlaps and driven by each tile's own focus-index map.

**Why stack-then-stitch fails (DERIVED).** Each stacked tile is a perspective view from its own position. A 30% overlap makes the tile step 4,922 px, or 9.3 mm at the subject at 2.72×. Near and far surfaces of a 1–5 mm deep subject then disagree by 19–205 px, which no global 2-D transform removes. A stitcher hides it in seams, and it resamples demosaiced pixels a second time, against ARCHITECTURE §7's one resampling pass.

**The design: plane plus parallax, per tile.**

1. Stack each tile as today, keeping a focus-index map k(x) from a prepass, since the pyramid has no focus field. Use estimator pass one's regularized index, interpolated below one frame and smoothed edge-aware; never raw argmax (AGENTS invariant).
2. In each overlap, register same-focus frame pairs across the two tiles. Each offset is the parallax at that slice's depth, by the focal-plane argument. Fit a smooth monotone curve T(k) per tile pair, Huber-weighted, and report slices with nothing sharp in the overlap as gaps.
3. Warp every frame of a tile by its breathing similarity composed with one shared field: the parallax T(k(x)) at each pixel's own depth. Sharing the field keeps the tile internally consistent, which one shift per frame would break by 0.4–2.5 px between adjacent slices.
4. Ramp the correction across each overlap so the two tiles meet at an intermediate viewpoint, while each interior keeps its own view. The result is a seamless multi-perspective image, with disocclusion confined to overlaps where the other tile saw round the edge (ARGUED).
5. Fold every frame of every tile once into the canvas. The pyramid then blends seams itself: it is the Burt–Adelson multiresolution spline, which was published for mosaics, once coverage enters its weights.

The field is gathered at consumption, so there is still one resampling pass. It is the per-tile refinement SYNTHESIS §3.3 predicted rail capture would make mandatory, derived from depth rather than searched by correlation. It rides on sota-path C4's residual warp layer, and is the multi-tile counterpart of C4's depth-dependent magnification term. Its error is about the focus-index error times the per-slice parallax step; at 0.3 frame of index error that is 0.1–0.75 px (DERIVED). Untextured regions have no reliable depth (fact 73), but nothing in them can show misregistration (ARGUED). A single-perspective or orthographic output would have holes at depth edges, since no tile saw those surfaces; it stays out of scope.

**Translate, don't rotate.** Rotating about the entrance pupil removes parallax in principle and suits a sphere of views around the camera. At 2.72× one tile step is a 2.0–4.4° turn, and a 5 mm deep subject then tolerates only 0.3–1.4 mm of pupil error for 0.5 px (DERIVED). Internal focusing moves the pupil during the bracket by an unmeasured amount, and rotation needs homographies the model lacks. For specimens an XY stage is the better geometry.

**Engineering it needs.**

- **Spatially tiled fold.** Canvas accumulators scale with area: 1.7× a frame for 2×1 tiles, about 2.2 GiB per worker; 5.8× for 3×3, about 7.5 GiB per worker, over the 6 GiB budget (DERIVED from the planner's 1,328 MB; M12 already measures peaks above plan). Each canvas region reads only the tiles that cover it, so work stays linear in tiles.
- **Coverage-aware weights.** A frame contributes only inside its feathered footprint, the fallback mean averages covering frames only, and the coverage mask enters every band.
- **Flat-fielding before the fold.** Vignetted tile edges carry less band energy and lose elections, and `BaseBand::Mean` would average mismatched levels into a low-frequency seam (ARGUED). It needs the pyramid-path gain from the code table.
- **Overlap-restricted correlation.** Cross-tile edges correlate only inside the overlap and only on slices with sharp content there; the rest are refused.
- **One joint solve.** Per-frame similarities for every tile in one least squares and one gauge. Stage positions are a prior, not a constraint.
- **Reporting.** Per-overlap residual after warping, T(k) coverage and gaps, and refusals per tile.

## Shared groundwork

Both parts need the same six changes, and none of them alters single-bracket behaviour: a one-bracket session must stay byte-identical to today.

&#91;embedded content: proposed pipeline · 4 stages, 3 bracket roles\]

Only the joint solve is new at the core; each role differs only in what the fold does with its frames.

1. **Session input.** Several directories, each a bracket ordered by filename as today, each with a role: repeat, interleave, tile, exposure or layer, plus an optional stage offset for tiles. Mixed bodies are refused; ISO, exposure and white balance are calibrated per bracket where they differ.
2. **Focus-keyed pairing.** Solve each bracket alone first, with today's code. Its fitted per-frame scale is a focus coordinate inside that bracket; a few cross-bracket probe correlations fix the offset between two brackets' axes, and each frame then gets its nearest-focus partner. Sony focus metadata is a check, not the key: it took two distinct values across a 33-frame stack (F §5).
3. **Joint solve.** One least squares over every frame of every bracket, in the anchor bracket's gauge. Edges are today's intra-bracket ladder plus cross-bracket same-focus pairs, overlap-restricted for tiles. Track-prior rows stay inside a bracket. Frames outside the anchor's component are refused and reported per bracket, with cycle rank stated.
4. **Merge plumbing.** Each frame carries its bracket and focus slice. Repeats are averaged per slice (pyramid) or by admission (estimator); interleaved frames enter as distinct slices; tiles fold into the canvas through their parallax field; exposure and layer brackets carry their own gain, noise and outputs.
5. **Sidecar.** A warp-map version bump keyed on the ordered bracket set, roles and pairing config, with the per-tile parallax curves stored beside it as hex-exact data. Every failure is a refusal, never a default, as today.
6. **Reporting.** Per bracket: placed and refused counts, cross-bracket edges and residuals, and the pairing table with each pair's scale gap. Per pixel: frames actually averaged, phase coverage for super-resolution, and overlap residual for mosaics.

Bracket role is orthogonal to `CaptureMode`. Each bracket still gets its own breathing-or-rail detection, and the rule stands: never apply the breathing model to rail data silently (SYNTHESIS §9).

## Pre-registered checks

Each claim gets a check whose control must behave as predicted before its bar means anything. None uses the sealed 407-frame holdout; development captures commission every instrument here. Bars are proposals until registered at dispatch.

| ID | Claim | Check | Control that must fail or hold | Pass bar (kill otherwise) |
| --- | --- | --- | --- | --- |
| G1 | A one-bracket session is unchanged | All byte-freeze rows through the session path | Sabotage a constant: the rows must move, as in BUILD-FREEZE-PYRAMID | Every row holds |
| P1 | Focus pairing finds true partners | Pairs against a commanded-focus manifest on a development repeat capture | Shuffled partners must fail; a half-step interleave must be classed interleave | ≥ 99% exact partners; no repeat declared in the interleave arm |
| P2 | Same-focus cross-pass edges are the best edges | BUILD-SHARP's re-align-through-placements residual, cross-pass vs span-1 | Self-pair reads ≈ 0 px; a planted 0.25 px offset is recovered within 0.05 px | Cross-pass residual ≤ span-1's (0.588 px on bee-2-cpl) |
| P3 | Same-focus averaging scales noise by 1/√K | Temporal σ, flat-ROI controls first, then in-focus detail ROIs, against the injected model | The same pass fed twice must claim no gain; a second pass misregistered by 0.5 px must lose on the detail metric | σ ratio within 10% of 1/√K and no detail loss beyond the instrument floor |
| P4 | Interleaving sharpens | M33's peak-miss fraction and ESF rise, one pass vs two | An interleave with zero focus offset must not improve | Peak-miss fraction falls ≥ 25% relative |
| S1 | Super-resolution appears only where phases are diverse | FRC above native Nyquist, red/blue and luma separately, §30 chart and §33 subject | Zero-nudge repeats must show no gain at the centre; shuffled placements must destroy it | Red/blue FRC cutoff rises where coverage is high; no M8 regression |
| S2 | Relative placement reaches 0.1–0.15 px | Planted sub-pixel shifts on plants carrying measured curvature (rule 6), then real pairs | Interpolator-free planted gain ≥ 0.9, against the gather's 0.29 | ≤ 0.15 px; kill above 0.25 px |
| F1 | The two-pass map tracks reproducible detail | Separate merges per pass, FRC per tile | A blur on one arm must lower it; a common post-filter must be shown invisible; darks bound fixed pattern | Responds as M-FRC predicts on all three arms |
| B1 | Stack-then-stitch parallax is s·δz/D | Two tiles over a pin above a textured card | A fronto-parallel flat target must show ≈ 0 differential | Within ±25% of s·δz/D with D measured |
| B2 | Overlap pairs measure T(k) | Per-overlap fit of T(k), predicting held-out slices | Shuffled slice labels must break monotonicity; the flat target must give constant T | Held-out error ≤ 0.25 px |
| B3 | The parallax field removes seams | Overlap residual after warping, plus native crops at seams | One-shift-per-frame and stack-then-stitch arms must both do worse | p90 residual ≤ 0.5 px and no visible seam |

## Captures needed

Four development sessions, about 700 frames in all, cover every check; none may reuse or touch the sealed 407-frame holdout. All use the A/B sheet's discipline: A7C II with FE 100mm Macro GM + 2x TC, M mode, ISO 100, f/5.6, fixed white balance, SteadyShot and OSS off, and a recorded commanded-focus list per pass.

| Session | What to shoot | Frames | Feeds |
| --- | --- | --- | --- |
| Repeat with nudges | One textured subject, five passes of one 55-frame ladder. Nudge the stage between passes 1–4 and note the rough offset; pass 5 repeats pass 4 untouched as the zero-nudge placebo. Add 32 darks. | 307 | P1, P2, P3, S1, S2, F1 |
| Half-step interleave | Captures-needed §13a: the same subject twice, the second pass offset by half a focus step | 110 | P1, P4 |
| Two tiles, two targets | XY stage, about 30% overlap, known stage step. First a pin held above a textured card, then a fronto-parallel flat textured target; one flat-field set per tile position. | 284 | B1, B2, B3 |
| Pupil location | The ruler measurement of the entrance pupil in the shooting configuration, as in captures-needed's pupil-factor request | 0 | D for B1, and the rotation tolerance |

If the camera cannot replay an identical commanded ladder, P1 loses its truth. The scale gaps between paired frames still measure how repeatable the ladder is, which decides whether repeat mode is usable on this body at all.

## Sequencing

Build the shared groundwork first; every later step depends on it, and each step ships only when its checks pass.

&#91;embedded content: proposed order · 5 steps, 2 outside prerequisites (dashed)\]

Steps 2 and 3 can run in parallel once step 1 passes. Mosaics also wait for the fold to meet its memory budget with spatial tiles, and super-resolution waits for the kernel-regression merge, which this proposal does not build.

## Risks and open questions

The largest risk is memory: M12 already fails at a 35.66 GiB peak against the 6 GiB bar, and every part of this proposal adds frames or canvas.

**Risks**

- **Memory.** Multi-bracket work should not ship before the fold meets its budget; the canvas also needs spatial tiling the fold does not have.
- **Drift between passes.** A 299-frame pass takes about 3.2 min at the measured 0.649 s interval (fact 2), so K passes give specimen creep, thermal drift and light drift K times longer. The per-tile consistency refusal in Part A is the guard.
- **Ladder repeatability.** Sony's bracket step width is relative and non-linear (F §F1.11), so a repeat may come back as an interleave. The pairing handles that, but the noise gain then turns into a sharpness gain.
- **Occlusion.** Tiles see different occlusion order at depth edges. The overlap ramp confines it but does not remove it, and rims already fail on 13 of 26 subjects (ARCHITECTURE §11).
- **Invented values.** Averaging or warping errors can create values no capture saw; M8-R must not regress in any arm.
- **Prepass cost.** Mosaic depth maps need a focus prepass on the pyramid path, an extra decode per frame on a fold that is 98.5% of run time.

**Open questions**

- Where is the entrance pupil, and how far does it move through a bracket? D sets the mosaic parallax and the rotation tolerance; neither is measured.
- Does the body replay a commanded ladder exactly? The 407-frame sheet needs the same answer.
- Is the f/5.6 cutoff 87 cy/mm (fact 1149) or 106–135 cy/mm (M84b)? Below Nyquist, luma super-resolution has no target at all.
- Should repeat averaging become a pyramid slice step, or is multi-bracket input the case that finally makes the estimator the default (sota-path move A)?
- How should Projects present several brackets in one stack, and admission per bracket?

## Prior art

Every mechanism here is published; what I could not find is their use on focus brackets. Two pieces have no prior use I could confirm: fusing sub-pixel samples within same-focus slices across passes, and calibrating mosaic parallax from same-focus overlap pairs. The search was a dozen English web queries plus B §6.1's four arXiv queries, so this is "could not confirm", not absence. Inside the repository, B §6 and sota-path C1, C4, C11 and D8 already anticipate pieces; what this adds is the multi-bracket input and joint solve, which C11 needs outright and which gives C1 and D8 their cleanest data.

| Idea | Closest prior art | What differs here |
| --- | --- | --- |
| Raw multi-frame super-resolution | [Wronski et al. 2019](https://research.google/pubs/handheld-multi-frame-super-resolution/): handheld bursts, hand tremor as the shift source, merged straight onto an RGB grid | Shifts come from breathing plus deliberate offsets between passes, within same-focus slices |
| Super-resolution from a focal stack | [Lee & Tai 2016](https://api.openalex.org/works/doi:10.1109%2FTIP.2016.2523419): defocus-kernel diversity plus multi-image deconvolution | Sampling diversity, not blur diversity; M115 already measured reweighting across focus as limited |
| Stacked macro mosaics | [photomacrography.net thread](https://photomacrography.net/forum/viewtopic.php?p=189648): stack each position, then stitch; rotate about the entrance pupil unless the lens is telecentric | Translation with a depth-dependent field from each tile's focus map; one fold, one resample |
| Commercial tile stitching | [Helicon Focus 9 help](https://www.heliconsoft.com/focus/help9/english/HeliconFocus.html): Micro Panorama aligns tiles by shift only, subject moved sideways | Shift-only alignment leaves the 19–205 px parallax derived above at 2.7× |
| Plane plus parallax | [Sawhney 1994](https://mlanthology.org/cvpr/1994/sawhney1994cvpr-d/): warp by a plane, residual motion encodes structure | Depth comes from focus, not from estimating the residual motion |
| Multi-viewpoint composites | [Agarwala et al. 2006](https://grail.cs.washington.edu/projects/multipano/): long scenes built from regions of ordinary perspective | Overlaps ramp to an intermediate viewpoint using known depth |
| Seam blending | [Burt & Adelson 1983](https://persci.mit.edu/pub_abstracts/spline83_abs.html): the multiresolution spline, introduced for mosaics | Strehl's pyramid already is this |
| Two-acquisition resolution | [Nieuwenhuizen et al. 2013](https://repository.escholarship.umassmed.edu/entities/publication/6df7bf2c-d43f-4377-96f1-b7fbbd66d6c5): Fourier ring correlation for optical nanoscopy | A per-tile overlay from two passes, labelled reproducible detail |
| Stacks per viewpoint for 3-D | [scAnt, Plum & Labonte 2021](https://peerj.com/articles/11155): 20–50 images per view, one extended-depth image per view, 180–360 views | Export only; reconstruction stays out of scope |

One caution from practice: [Helicon's staff](https://forum.heliconsoft.com/viewtopic.php?p=8601) call multi-image super-resolution more marketing than practical, and recommend panoramas for more pixels. The optics bound above agrees for luma; the claim here is narrower, red/blue resolution and alias removal.

## Sources

Repository files at commit `4813e46b`:

- [ARCHITECTURE.md](https://github.com/chcaru/strehl/blob/4813e46bdc9aaf5f9220115911df5cd5aa3fd808/docs/ARCHITECTURE.md) — pipeline, merge backends, alignment, systems model
- [SYNTHESIS.md](https://github.com/chcaru/strehl/blob/4813e46bdc9aaf5f9220115911df5cd5aa3fd808/docs/research/SYNTHESIS.md) — facts 2 and 9, §3.3 on rail and per-tile refinement, §9 on `CaptureMode`
- [2026-08-sota-path.md](https://github.com/chcaru/strehl/blob/4813e46bdc9aaf5f9220115911df5cd5aa3fd808/docs/proposals/2026-08-sota-path.md) — C1 sample-level fusion, C4 residual warp layer, C11 aperture diversity, D8 split-stack FRC; corpus constants
- [B-algorithms-sota.md](https://github.com/chcaru/strehl/blob/4813e46bdc9aaf5f9220115911df5cd5aa3fd808/docs/research/B-algorithms-sota.md) — §6 super-resolution from breathing, §6.5 merge interface
- [captures-needed.md](https://github.com/chcaru/strehl/blob/4813e46bdc9aaf5f9220115911df5cd5aa3fd808/docs/captures-needed.md) — §13a half-step interleave, the IBIS nontranslation gate
- [2026-09-319-frame-session.md](https://github.com/chcaru/strehl/blob/4813e46bdc9aaf5f9220115911df5cd5aa3fd808/docs/capture-requests/2026-09-319-frame-session.md) — the sealed 407-frame A/B holdout
- [M-FRC-VIABILITY.md](https://github.com/chcaru/strehl/blob/4813e46bdc9aaf5f9220115911df5cd5aa3fd808/docs/research/M-FRC-VIABILITY.md) — repeat-pair FRC verdict and blind spots
- [M88-optical-ceiling.md](https://github.com/chcaru/strehl/blob/4813e46bdc9aaf5f9220115911df5cd5aa3fd808/docs/research/M88-optical-ceiling.md) and [BUILD-SHARP.md](https://github.com/chcaru/strehl/blob/4813e46bdc9aaf5f9220115911df5cd5aa3fd808/docs/research/BUILD-SHARP.md) — optical cutoff, the 2.2× softness
- [F-camera-lens-optics.md](https://github.com/chcaru/strehl/blob/4813e46bdc9aaf5f9220115911df5cd5aa3fd808/docs/research/F-camera-lens-optics.md) — §5.2 focus-driven versus rail geometry, §F1.11 step width
- Code: [align\_cmd.rs](https://github.com/chcaru/strehl/blob/4813e46bdc9aaf5f9220115911df5cd5aa3fd808/crates/strehl-cli/src/align_cmd.rs), [align.rs](https://github.com/chcaru/strehl/blob/4813e46bdc9aaf5f9220115911df5cd5aa3fd808/crates/strehl-core/src/align.rs), [merge\_cmd.rs](https://github.com/chcaru/strehl/blob/4813e46bdc9aaf5f9220115911df5cd5aa3fd808/crates/strehl-cli/src/merge_cmd.rs), [pyramid.rs](https://github.com/chcaru/strehl/blob/4813e46bdc9aaf5f9220115911df5cd5aa3fd808/crates/strehl-core/src/pyramid.rs), [lib.rs](https://github.com/chcaru/strehl/blob/4813e46bdc9aaf5f9220115911df5cd5aa3fd808/crates/strehl-cli/src/lib.rs), [stack.rs](https://github.com/chcaru/strehl/blob/4813e46bdc9aaf5f9220115911df5cd5aa3fd808/crates/strehl-cli/src/stack.rs)

External pages opened for this document are linked in the Prior art table.

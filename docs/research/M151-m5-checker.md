# M151 - M5 depth-of-field coverage checker

**State at freeze:** definitions and controls frozen before measurement code;
commissioning results pending.

## Question and registered bar

The real question is whether the planned sealed capture contains everything
needed by an output-blind coverage instrument that can both stay quiet on a
complete stack and respond to a missing depth slab. The scorecard success
clause is:

> coverage point estimate `>=99%`, Wilson LCB95 `>=98%`, longest failed run
> `<=1%` of the sweep dimension, retained FOV `>=99%`, and strehl coverage no
> lower than the best comparator.

The whole M5 card also fixes 128x128 input-coordinate tiles, at least 500
eligible sites overall and 50 per capture, election in `0.05-0.12
cyc/native px`, evaluation in `0.15-0.25 cyc/native px`, eligibility at
best/far source-signal ratio `>=2.0` with bootstrap lower bound `>=1.5`,
`rho_best>=0.90`, `rho_best-rho_far>=0.05`, and `rho_far` at least three
focus nodes from the elected best frame
(`docs/proposals/2026-09-sota-scorecard.md:730-773`). M133 found
`source-signal` and the non-planar run undefined and the checker
uncommissioned (`docs/research/M133-blocker-audit.md:690-704,805-834`).

## Frozen definitions

These definitions are mirrored machine-readably in
`experiments/M151-m5-checker/frozen-definitions.json`. They apply before any
candidate output is opened.

### F1. `source-signal`

All calculations use the common input's linear ProPhoto RGB D50 luminance

`Y = 0.2880402 R + 0.7118741 G + 0.0000857 B`.

Each input-fixed 128x128 tile is divided into sixteen non-overlapping 32x32
blocks. Within a block and frame, divide `Y` by its positive arithmetic mean,
subtract one, apply a separable Tukey window with `alpha=0.25`, and Fourier
transform. For an interior focus node `j` and frequency band `B`, define the
block source signal as

`C(j,B) = 0.5 Re[sum_B F_j conj(F_(j-1)) + sum_B F_j conj(F_(j+1))]`.

The tile value is the arithmetic mean over its sixteen blocks and, when the
capture has complete repeated passes, over passes. Cross-power common to
independently exposed neighboring frames estimates subject structure; raw
single-frame power, which admits shot/read noise by construction, is forbidden.
The same adjacent-frame definition is used for legacy single-pass and new
paired-pass captures so capture type cannot select the estimator. Fixed-pattern
residue can bias it upward, so a textureless real-input null is a mandatory
commissioning control; failure of that null retires this definition.

Endpoints have no two-sided estimate and are not election candidates.
Negative cross-power remains negative through averaging and regularisation;
only the final numerator and denominator used in a ratio are floored at zero.

For the eligibility confidence bound, resample the sixteen spatial blocks with
replacement 10,000 times using PCG64 seed `20260902` mixed with the stable site
identifier. The same block draw is used at every node and in both bands. Each
draw re-regularises and re-elects the best node, then recomputes the far
maximum and ratio. The LCB is the nearest-rank 5th percentile (the 500th sorted
draw). A draw with non-positive best signal has ratio zero; a positive best and
non-positive far signal has infinite ratio. This bootstrap is an input-only
robustness check, not another Wilson trial.

### F2. Non-planar failed-run construction

Every eligible physical tile receives the scalar depth coordinate `d_t`, its
input-only elected best frame index. Spatial planarity is never assumed.
Collapse equal depth coordinates; that depth level is failed when **any**
eligible tile at the level fails. Sort the unique depths and partition

`[min(d)-0.5, max(d)+0.5]`

at midpoints between adjacent unique depths (a one-dimensional Voronoi
partition). A failed run is a maximal union of adjacent failed depth cells.
Its length is measured in focus-node units and divided by
`max(d)-min(d)+1`. Ties choose the earliest interval. With fewer than two
unique eligible depths, the run arm is `UNMEASURED`, never zero.

This maps planar and non-planar subjects onto the only common measured sweep
coordinate. It is conservative at duplicate depths (`any` failure) and in
sparse depth regions (Voronoi width is exposed rather than silently omitted).
The checker therefore also reports the largest depth-cell fraction so a
coarsely sampled capture cannot masquerade as precise run localisation.

### F3. Input-only eligibility and best-frame election

The site grid, input validity, spectra, source-signal curves, elected best
node, far set, point ratio, bootstrap LCB, and eligibility bit are created by a
manifest command whose API accepts **no candidate output path or score**. The
manifest is hashed before scoring.

Election uses F1 in `0.05 <= f < 0.12 cyc/native px`. The node curve is
regularised with the fixed five-node binomial kernel
`[1,4,6,4,1]/16`, using edge replication. Candidates are nodes 3 through
`N-4`, inclusive; an exact tie selects the lower index. This guards the raw
argmax defect in `AGENTS.md` rule 4 and guarantees a two-sided neighboring
estimate and far frames on both sides.

At that elected node, evaluate F1 in
`0.15 <= f < 0.25 cyc/native px`. `far` is the maximum over nodes whose
absolute index distance from the elected best is at least three. A tile is
eligible iff the all-block best/far ratio is at least 2.0 and the re-electing
bootstrap LCB is at least 1.5. There is no candidate-derived exclusion.
Frames, A/B passes, channels, and bootstrap draws do not create extra sites.

### F4. Retained-FOV accounting

The denominator is every pixel in the frozen native active-pixel mask of the
common-input anchor, after only sensor-edge exclusions recorded in the input
manifest. It is **not** the eligible-tile hull, the output bounding box, or the
all-frame intersection.

The numerator is denominator area covered by a finite, non-padding candidate
sample whose footprint and inverse sample support are reconstructed by the
independent score harness in anchor coordinates. Pixel value (including
black) does not determine validity, and output-provided claims do not enlarge
the mask. Report this area ratio per required output and use the minimum;
never average FOV across captures or modes. Resizing cannot create area because
the footprint is evaluated in anchor coordinates.

### F5. Wilson aggregation

Use the lower one-sided 95% Wilson score bound with
`z = Phi^-1(0.95) = 1.6448536269514722`:

`LCB = [p + z^2/(2n) - z sqrt(p(1-p)/n + z^2/(4n^2))] / [1+z^2/n]`.

The Bernoulli unit is one distinct, non-overlapping, input-eligible physical
128x128 tile. Pixels, RGB channels, Fourier coefficients, focus frames, A/B
passes, and bootstrap draws never increase `n`. The same subject coordinate
reused across required A/B or step-width outputs in one session counts once
and succeeds only if every required output succeeds. Compute every capture's
point estimate and LCB separately and require every capture to pass. For the
pooled row, sum successes and distinct physical-site units after that
within-session collapse; pooling may not rescue a failed capture.

## Frozen checker details

- Coherence follows the scorecard exactly in the evaluation band after the
  same luminance, mean removal, and Tukey window:
  `rho_j = |sum O conj(I_j)| / sqrt(sum |O|^2 sum |I_j|^2)`.
- `rho_best` uses only F3's elected source frame. `rho_far` is the maximum for
  `abs(j-best)>=3`. A site passes only both `rho_best>=0.90` and
  `rho_best-rho_far>=0.05`.
- Frequency upper edges are exclusive. Numeric work is float64. A zero-energy
  coherence denominator yields a failed site, not a NaN omission.
- Tile origin is the top-left of the frozen active rectangle; tiles do not
  overlap. Incomplete edge tiles are not sites and are recorded before output.
- The machine-readable definition file is part of every result by SHA-256.

## Pre-registered commissioning

1. **Healthy null:** on a complete development stack, create an output-blind
   manifest, then make an oracle tile mosaic by copying each elected best
   source tile. Required response: zero failed eligible sites, zero failed-run
   length, 100% retained FOV.
2. **Depth-slab defect:** choose, without reading a candidate output, the
   lexicographically first shortest contiguous interval of at least three
   input nodes whose Voronoi depth width is at least 10% of eligible depth.
   Remove those nodes from the renderer input only, keep the complete frozen
   manifest as truth, and make the same oracle mosaic from surviving nodes.
   Required response: coverage falls by at least 5 percentage points and the
   longest failed run overlaps the planted slab.
3. **Planted improvement:** compare an oracle constrained to far frames
   (`abs(j-best)>=3`) with the complete best-source oracle. Required response:
   coverage and longest-run results improve, with magnitudes reported.
4. **FOV plant:** remove a known 2% strip from the geometric output-valid mask.
   Required response: retained FOV moves from 100% to 98% and fails the 99%
   bar.
5. **Source-signal noise null:** a photon/read-noise-only input with the
   development stack's measured mean and conservative noise amplitude must not
   manufacture 50 eligible tiles. If it does, F1 is not commissioned. The
   development directory named `flat-*` is a fronto-parallel **textured
   calibration slide**, not a signal-free flat field; it is a depth-topology
   null and is not allowed to stand in for this test.
6. **Non-planar topology:** permute a measured real depth map spatially without
   changing any elected depth or pass/fail value. The one-dimensional run
   result must be byte-identical. This proves that the definition is actually
   invariant to planar layout rather than merely claiming to support it.

Synthetic controls may prove exact arithmetic. Claim-bearing commissioning
must additionally consume only the explicitly development/burned slide data.
No holdout output may be rendered or read.

## Capture-sufficiency finding at freeze

The 891-frame scored sitting has the needed M5 payload: converter-on
`sw4-A/B` (55 each), `sw10-A/B` (27 each), dense checker-only `sw1` (91),
ordered automated focus nodes, independent A/B flats and darks, fixed-focus
witnesses, and a coplanar nonperiodic patch sized for at least 64 guarded
256-pixel sites
(`docs/capture-requests/2026-09-319-frame-session.md:285-346,585-670`).
F1 deliberately works with a single complete pass, so it does not demand a
frame type absent from legacy M5 holdouts; the new A/B passes improve
precision but do not change the estimator.

**The scored sitting is structurally sufficient for its controlled-slide M5
arm, but the pre-shutter proof is not yet sufficient.** The documented
768-frame rehearsal contains TC0 focus ladders and a converter-on fixed-focus
atlas, not converter-on `sw4/sw10` M5 ladders
(`docs/OWNER-ACTIONS.md:290-301`). Existing converter-on development stacks
are IBIS-on single passes. They can commission this checker, but they cannot
prove that the final patch and tilt will yield at least 50 eligible native
128-pixel sites in both the planned 55- and 27-frame converter-on arms.
Before the 891 sequence, run an exact-configuration converter-on M5 rehearsal
or an owner-approved equivalent input-only gate proving that count and
gap-free depth support on the final patch. This is a preflight omission, not a
request for another frame type inside the sealed 891 sitting.

The 891 arm also cannot alone satisfy comparator parity or establish the whole
pooled M5 score; the registered ruler/natural holdouts and commercial
comparator outputs remain separate dependencies.

## Holdout discipline

The only real captures permitted in commissioning are those already classified
burned/development. The holdout unit is subject plus uninterrupted session, and
no holdout output, metric, visual verdict, or tuning read is permitted before
the registered score run
(`docs/proposals/2026-09-sota-scorecard.md:345-349`). All writes go under this
lane; `D:\personal\macro` and `D:\edited\macro` remain read-only.

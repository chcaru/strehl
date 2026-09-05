# M151 - M5 depth-of-field coverage checker

**State at freeze:** definitions and controls frozen before measurement code;
commissioning results pending.

**Commissioning verdict:** **PARTIAL, and the planned capture is not yet
demonstrated sufficient.** The checker responds in both directions, but the
frozen real-input eligibility arm does not produce enough sites to commission
the complete scorecard bar. The non-zero commissioning exit is an intentional
fail-closed result, not a runtime failure. The result verifier asserts that
exact partial verdict and exits zero.

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

The 1,215-frame scored sitting has the needed M5 payload: converter-on
`sw4-A/B` (55 each), `sw10-A/B` (27 each), dense checker-only `sw1` (91),
ordered automated focus nodes, independent A/B flats and darks, fixed-focus
witnesses, and a coplanar nonperiodic patch sized for at least 64 guarded
256-pixel sites
(`docs/capture-requests/2026-09-319-frame-session.md:285-346,585-670`).
F1 deliberately works with a single complete pass, so it does not demand a
frame type absent from legacy M5 holdouts; the new A/B passes improve
precision but do not change the estimator.

At freeze, I judged the pre-shutter proof insufficient because the rehearsal
has TC0 focus ladders rather than converter-on `sw4/sw10` ladders. That
inference was also based on an unlabelled 64-site sample and the nominal
50-site floor. **It is superseded by the exhaustive census and A ruling
below:** the existing final-patch/final-tilt TC0 rehearsal is the
owner-approved input-only feasibility gate, and its effective minimum is 133
eligible tiles per capture, not 50.

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

## Post-freeze commissioning results

The frozen definition file has SHA-256
`04bad98c8bb8099f3a674d464ffbf72f57c97559d038af07e4ee8d450731b09f`.
It was committed before measurement code in `6783d497`; the pre-code
noise-null correction was committed in `697e735f`.

### Exact reproduction

Run from the `strehl` repository root:

```powershell
python experiments/M151-m5-checker/checker.py self-test
python experiments/M151-m5-checker/test_checker.py
python experiments/M151-m5-checker/test_full_population.py
python experiments/M151-m5-checker/commission.py --refresh
python experiments/M151-m5-checker/verify_results.py
python experiments/M151-m5-checker/full_population.py --refresh
python experiments/M151-m5-checker/verify_full_population.py
```

The self-test exits 0. The core unit suite runs 14 tests and the census suite
runs 5 tests; both exit 0. The full
commission command forces all numerical thread pools to one, reads 174
explicitly development/burned RAWs in 67.9 seconds of RAW preparation on this
run, writes only under the lane, and exits **1** because the real-input site
count and exact-length capture-sufficiency controls correctly remain red.
`commission-results.json` is the compact result; detailed manifests and site
rows are reproducible caches under ignored `out/`.

The exhaustive command serially rereads only the three named
burned/development stacks and writes
`full-population-results.json`. `verify_full_population.py` checks its frozen
definition hash, active-area arithmetic, all four eligibility counts, selected
window and Wilson feasibility.

### Null, defect, improvement, and FOV magnitudes

| arm | eligible | coverage | Wilson LCB95 | longest failed run | retained FOV |
|---|---:|---:|---:|---:|---:|
| synthetic complete oracle null | 160 | **100.0%** | **98.3372%** | **0 / 21 nodes = 0%** | **100%** |
| synthetic three-node slab deletion | 160 | **95.0%** (8 fail; **-5.0 pp**) | **91.3434%** | **1 / 21 = 4.7619%** | **100%** |
| synthetic far-only defect | 160 | **0%** | **0%** | **21 / 21 = 100%** | **100%** |
| development tilted-sw10 complete oracle null | 4 | **100.0%** | **59.6521%** | **0 / 14 nodes = 0%** | **100%** |
| development tilted-sw10 three-node slab deletion | 4 | **75.0%** (1 fail; **-25.0 pp**) | **35.6168%** | **3.5 / 14 = 25.0%** | **100%** |
| development tilted-sw10 far-only defect | 4 | **0%** | **0%** | **14 / 14 = 100%** | **100%** |

The synthetic plant deleted nodes 5-7, covering 14.2857% of eligible depth.
Twenty-four elected sites lay in the slab, eight failed, coverage moved exactly
5.0 percentage points, and the longest failure overlapped the planted slab by
one node. Replacing the far-only output with the complete best-source oracle is
a planted improvement: coverage moved **0% -> 100%** and the failed run moved
**100% -> 0%**.

On real development data, the selected slab was nodes 17-19. One of the four
eligible sites changed source, coverage moved **100% -> 75%**, and longest
failed run moved **0 -> 3.5 nodes** (**25%** of represented depth). The reverse
far-to-best improvement again moved **0% -> 100%**. These real magnitudes prove
that the scoring path is not constant, but four sites are not a commissioned
M5 population.

The independent FOV plant removed a two-percent geometric strip and read
**100% -> 98%** on both fixtures, correctly failing the 99% bar without
changing spectral coverage. The noise-only source-signal null admitted **0 of
64** sites. Permuting site coordinates while preserving measured depths and
statuses left the non-planar run JSON byte-identical. Four synthetic captures
of 160 distinct physical units gave pooled **640/640**, Wilson LCB95
**99.5790%**, confirming the frozen pooled-unit implementation.

### Real eligibility and the capture blocker

The decisive red result is input-only and precedes every candidate output:

| explicitly non-holdout input | frames | point ratio `>=2` | bootstrap LCB `>=1.5` | eligible |
|---|---:|---:|---:|---:|
| burned calibration grid sw4 | exact planned **55** | **0/64**; max 1.08784 | **0/64**; max 1.04749 | **0/64** |
| burned calibration grid sw10 | exact planned **27** | **0/64**; max 1.27195 | **0/64**; max 1.18673 | **0/64** |
| development tilted-sw10, full | 92 | **4/64** | **5/64** | **4/64** |
| development tilted-sw10, best of all 66 contiguous 27-frame windows | 27 | point upper bound **15/64** | **17/64** separately | **13/64** |

The best 27-frame development window was nodes 6-32. Its median point ratio
was 1.39945 and maximum 12.3001. Because point ratio `>=2` is conjunctive, 15
is a hard upper bound even before bootstrap; the frozen combined result is 13.

### Exhaustive-census correction

The 64 sites above were **not the candidate population**. They were an imposed
fixed 8x8 M131-style grid subsample, chosen to bound the first commissioning
run. `rawpy.raw_image_visible` is 7028x4688 pixels. Before eligibility, it
contains

```
floor(7028 / 128) * floor(4688 / 128)
= 54 * 36
= 1,944 complete, non-overlapping candidate tiles
```

with 116 pixels left at the right and 80 at the bottom. The exhaustive
input-only census produced:

| development arm | point-qualified / 1,944 | bootstrap-eligible / 1,944 |
| --- | ---: | ---: |
| burned grid, exact sw4/55 | **0** | **0** |
| burned grid, exact sw10/27 | **0** | **0** |
| tilted sw10, full 92 | **69** | **53** |
| tilted sw10, best exact 27-frame window (nodes 9-35) | **328** | **275** |

The exact-27 tilted result has an all-success Wilson LCB95 of **0.990258**.
Thus the earlier `13/64` result was a sample count, not evidence that the
geometry could not reach 133. The exhaustive result proves that an exact-length
tilted capture can exceed the effective Wilson minimum. It does not rescue the
planar burned grid, whose complete populations remain 0/1,944.

### Denominator provenance

Every proportion reported by this lane has the following denominator:

- **Synthetic coverage controls:** 160/160 (complete null), 152/160
  (three-node deletion), and 0/160 (far-only) use the entire generated
  160-site fixture, not a sample or cap. The four-capture 640/640 Wilson check
  uses all 160 generated sites in each of four synthetic captures.
- **Initial real coverage controls:** 4/4, 3/4, and 0/4 use every eligible site
  found inside the fixed 64-site development subsample. They do **not** use
  every eligible site in the frame.
- **Initial real eligibility:** burned sw4 0/64, burned sw10 0/64, tilted-92
  4/64, and best-27 13/64 (with separate point/bootstrap counts 15/64 and
  17/64) all use the same imposed fixed 8x8 subsample and computational cap.
  The corroborating M131 0/64 figures likewise use that audit's fixed 8x8
  subsample. The noise-null 0/64 instead uses the entire generated 64-site
  synthetic fixture.
- **Exhaustive real eligibility:** 0/1,944, 0/1,944, 53/1,944, and 275/1,944
  use the full population of complete 128x128 tiles in the 7028x4688
  RAW-visible rectangle. The associated point counts 0/1,944, 0/1,944,
  69/1,944, and 328/1,944 have the same population denominator.
- **Coverage percentages** always divide passing tiles by all input-eligible
  tiles in the stated fixture or census. **Failed-run percentages** divide
  failed Voronoi depth length by the complete represented
  `max(best)-min(best)+1` interval (reported examples: 0/21, 1/21, 21/21,
  0/14, 3.5/14, and 14/14). The synthetic planted slab's 14.2857% depth
  coverage is 3/21 of that same complete interval.
- **Retained-FOV 100% and 98%** use every pixel in the complete frozen
  synthetic anchor mask; the planted 2% strip was not a sampled region.
  Wilson percentages use the explicitly reported eligible-tile `n`; the
  50/50, 64/64, 128/128, 133/133, and 256-site values are arithmetic
  feasibility examples, not observed populations.

**Previously under-specified:** the first headline ruling published the
0/64, 0/64, 13/64 and four-eligible-site results without stating that 64 was
an imposed subsample/cap or that 1,944 candidates were available. Treating
those sample counts as population evidence produced the wrong capture ruling.
This subsection and the exhaustive census above are the correction.

Existing M131 focus curves independently show the same broad-through-focus
mechanism with different statistics: best/far-at-three ratios reached the 2.0
bar at **0/64** sites for Tenengrad and Laplacian on both sw4 and sw10. Their
maxima were 1.1374 / 1.1478 on sw4 and 1.2447 / 1.6234 on sw10. Those are
corroboration, not substitutions for F1.

There is a second arithmetic blocker hidden by the scorecard's nominal
"at least 50" wording. Under F5, even 50/50 successes have Wilson LCB95
0.948667; 64/64 have 0.959441; and 128/128 have 0.979300. The first population
that can reach 0.98 with zero failures is **133/133**. At 256 sites only one
failure is permitted. Thus 50 is merely an eligibility floor, not a passable
sample size.

## Final capture-sufficiency ruling

**A — measurable on the 1,092-frame rehearsal as currently specified; added frame
cost: zero.** The full census changes the earlier ruling. The rehearsal already
contains the required final-patch/final-tilt input ladders:
`TC0-sw4-A/B` at 55 frames and `TC0-sw10-A/B` at 27 frames. M5 eligibility and
best-frame election are input-only, so these four named captures can be read
without rendering an output and without touching the sealed holdout.

Add this M5 rehearsal exit gate:

1. enumerate all complete non-overlapping 128x128 tiles in the RAW-visible
   rectangle using the fixed origin `(0,0)`;
2. for sw4, average the block cross-powers from the complete A and B passes
   **before** regularisation, best-frame election, ratios, and bootstrap; do
   the same independently for sw10;
3. require **at least 133 eligible tiles in the pass-averaged sw4 manifest**;
4. require **at least 133 eligible tiles in the pass-averaged sw10 manifest**;
   and
5. require **at least 133 common eligible physical tiles in the intersection
   of those two required step-width manifests**.

Failure of any one count is a stop: do not shoot the 1,215-frame session until
the target/framing/sweep is corrected in another non-holdout rehearsal. The
intersection count is the controlled-slide capture's effective Wilson
denominator after the frozen within-session duplicate collapse; 133/133 has
LCB95 0.980063. Do **not** count A, B, sw4 and sw10 as four independent
populations. The scorecard's 500-overall floor must be met by distinct physical
sites across the full registered M5 capture set; this one rehearsal cannot
commission that future pooled total. This is a feasibility gate, not an M5
score: the converter-off rehearsal does not replace the converter-on holdout
outcome. The existing G0-G3, gap-free-depth, M147 and physical-control gates
remain independently required.

The sealed sitting is therefore **conditionally sufficient for M5 if this
rehearsal gate passes**. It contains the scored through-focus arms, ordered
nodes, witnesses, independent calibration and FOV reference. M5 requires no
extra frame type or configuration beyond the already specified rehearsal and
scored blocks.

## Can this bar bite?

**The scoring core can bite.** It stayed quiet on both complete-oracle nulls,
charged the synthetic deletion 5.0 points and the real deletion 25.0 points,
localized a failed run in both, rejected a 2% crop, rejected far-only outputs,
and moved 100 points in the planted-improvement direction. It is not an
always-green statistic and its error sign is not one-sided by construction.

**The complete registered bar can bite, but no claim-bearing population has
yet been read.** The exact-27 development census supplies 275 eligible sites,
so the 133-site Wilson requirement is reachable without lowering the frozen
optical threshold. `all_commissioned` remains `false` because no scored
common-input/output population exists. If the exact final-patch rehearsal
cannot reach 133 sites per capture, the correct action is to stop and repair
the capture design, not move the bar.

## Not commissioned

- No scored common-input ProPhoto adapter was available. The real-data arm
  uses a documented linear green RAW proxy and no final geometric
  registration. It is diagnostic evidence and cannot substitute for the
  registered common-input score path.
- No production Strehl or commercial-comparator output was rendered. The
  complete and defective outputs are input-only oracle tile mosaics. This
  avoided sustained rendering during M139's timing campaign.
- The accepted real null/defect response used four eligible sites from the
  original 64-site sample and therefore does not commission Wilson,
  per-capture coverage, or comparator parity. The later census found 53
  eligible sites over the full 92-frame tilted stack and 275 in a
  development-selected exact-27 window; it tested eligibility, not outputs.
- The source-signal noise null uses independent centered cross-power at unit
  scale. Because the eligibility ratios are scale-invariant it exercises the
  zero-signal sign path, but it does not reproduce measured sensor
  fixed-pattern correlation; the stronger measured-noise null registered
  before code remains uncommissioned.
- FOV arithmetic and its crop plant are commissioned; an actual output-adapter
  geometry trace is not.
- The non-planar constructor is commissioned by an invariant permutation
  plant. The all-axis real stack was not reread for a separate output score.
- No holdout outcome was rendered, scored, or viewed.

# M-PHASE0-ASTIG — preregistration

Status: **REGISTERED BEFORE THIS LANE DECODED OR MEASURED ANY REAL PIXEL.**

Claim: C7, `docs/proposals/2026-08-sota-path.md`, section
“Orientation-resolved election: astigmatism is a focus split, and no stacker
looks”.

This registration uses the proposal's requested quantity, not the summary in
the dispatch: split the through-focus response into `Gx²` and `Gy²`, fit the two
peaks with M33's baseline-subtracted log-parabola, and measure the local
orientation-dependent focus split. One premise in C7 is stale relative to the
code: `strehl-core/src/focus.rs::gradient_magnitude` ships
`sqrt(Gx² + Gy²)`, not the squared Tenengrad sum stated by C7. It is still an
orientation-blind scalar, so the decision question is unchanged.

## 1. Exact question

At the **same off-axis field point and the same subject depth**, are the best
focus positions of tangentially and sagittally oriented structure separated by
at least one captured frame?

The controlled answer comes from the calibration grid, not the razor. The grid
puts horizontal and vertical lines on the same film plane and repeats them
throughout the field. The razor has only one dominant edge orientation, and
M128 showed that its apparent edge has intrinsic width; it can exercise the
loader and a flat/no-edge refusal but cannot identify an astigmatic split.

At a point on the horizontal field axis:

* `Gx²` measures tangentially oriented grid lines (their gradient is radial);
* `Gy²` measures sagittally oriented grid lines.

On the vertical field axis those assignments swap. Define

```text
δ = z_tangential-structure - z_sagittal-structure
```

so the four cardinal sectors have the same expected sign for rotationally
coherent astigmatism. The sign convention is about line orientation, not the
often-ambiguous convention used for an MTF curve's scan direction.

## 2. Corpus search completed before instrument design

Rule 40's commissioned search was run:

```powershell
python experiments\ORCH-drift-check\prior_art.py --commission
python experiments\ORCH-drift-check\prior_art.py astigmatism sagittal tangential orientation anisotropy
```

It returned the following relevant records. None contains a commissioned
through-focus `z_t - z_s` measurement, so this question is not already
answered.

* `docs/research/M16-orientation-fpn-measured.md` is preregistered and
  commissioned. Its orientation effect is a **focus-window optimum** caused by
  anisotropic subject texture; it explicitly refutes row/column FPN as the
  cause. It warns that an unpaired `Gx/Gy` statistic can read subject content.
* `docs/research/M103-halfdrift.md` contains a retraction banner over its
  former `+37%` acutance claim. Its surviving anisotropy instrument measures
  radial registration smear in a finished render, not two through-focus peaks.
* `docs/research/BUILD-SHARP.md` measures a `2.2x` non-diffraction blur, but
  names astigmatism only as one unseparated candidate and contains explicit
  withdrawals of its earlier aperture inference.
* `experiments/M128-razor-ladder/PREREGISTRATION.md` and
  `out/controls.json` are commissioned evidence **against using the razor as an
  optical reference**: the measured-contamination, planted-ladder, locator and
  settings controls are RED. Amendment A4 finds a real edge but shows its width
  is intrinsic rather than diffraction-scaled.
* `docs/research/M-PHASE0-RHO.md` commissioned the new grid and razor only as
  geometry controls (`4/4` known-answer passes, `2/2` plants caught). It finds
  the grid fundamental at `0.039062 cyc/sensor-px` on both axes and the razor's
  low-band slope at `2.379`; neither result uses focus position.
* SYNTHESIS fact 412 is not an existing C7 instrument. It is Wang et al.'s
  local-edge-orientation partition for an occlusion problem. The proposal's
  phrase “fact 412's edge-orientation-split” is therefore a useful analogy, not
  a reusable astigmatism measurement.

## 3. Fixed substrate

All inputs are read-only under `D:\personal\macro\requests`.

### Controlled primary

All five stacks in `30-calibration-grid`, all at f/5.6:

| setup | native focus-step setting | frames |
|---|---:|---:|
| grid-1 | 1 | 91 |
| grid-1 | 4 | 55 |
| grid-1 | 10 | 23 |
| grid-2 | 4 | 46 |
| grid-2 | 10 | 27 |

The two step-width-4 stacks are the **primary pair**. They give two physical
placements at the same sampling. Step widths 1 and 10 are a sampling ladder,
not extra independent subjects.

### Aperture sensitivity

All five `7-aperture-pairs/fabric-weave-*` stacks, at f/5.6, f/8, f/11, f/14
and f/18, native focus-step setting 5. This is a second subject and a real
aperture ladder. Its absolute split is not allowed to establish C7 because
orthogonal threads can occupy different physical heights. The four-sector sign
mapping cancels a global horizontal-versus-vertical thread offset, but not
local weave or waviness. It may invalidate robustness; it may not rescue a
failed controlled grid.

### Physical negative/control

`19-razor-edge/horizontal-flat/...-f8-cpl` supplies a fixed, texture-poor region
away from the silhouette. It is a refusal check only. No number from its
one-orientation edge enters the C7 verdict.

## 4. Sampling and response statistic

RAW is loaded only through a copied `rawpy.raw_image_visible` array. Each
sensor quad becomes one green-luma sample,
`L = (G1 + G2)/2`, before any spatial filtering. A second decode through the
repository's `strehl probe`/`strehl-raw` path must agree on active dimensions,
CFA layout, black/white levels and per-plane summary to the precision printed
by both paths. A mismatch stops the lane.

Seventeen fixed `192 x 192` green-luma tiles are used: the sensor centre and
the four cardinal sectors at elliptical field radii
`r = {0.25, 0.50, 0.75, 0.90}`. Coordinates are derived only from active-array
dimensions, before image content is read. A separable Hann weight and a
four-pixel Sobel margin keep boundary crossings from determining the result.

For each frame and tile, 2-D Sobel is run **per frame** (never on a
`[frame,y,x]` cube):

```text
Ex(k) = weighted_mean(Gx(k)^2) / weighted_mean(L(k))^2
Ey(k) = weighted_mean(Gy(k)^2) / weighted_mean(L(k))^2
```

The common denominator removes multiplicative illumination drift without
mixing the arms. No high-frequency or best-frame mask selects pixels.

For each response curve `E(k)`, set `b = percentile_5(E)`,
`S(k) = max(E(k)-b, 1e-12 * max(E))`, choose the discrete maximum `k0`, and
fit a parabola to
`log S(k0-1), log S(k0), log S(k0+1)`. The vertex is `z`.

A peak is valid only if:

1. `k0` is in `[2, n-3]`;
2. the log parabola is concave and its vertex offset is at most `0.75` frame;
3. `max(E) / median(E)` is at least `1.10`;
4. fewer than `0.01%` of tile samples are within 16 DN of RAW white;
5. at least 90% of block-bootstrap replicates return valid paired peaks; and
6. each arm's 95% bootstrap interval is no wider than `1.50` frame.

The tile is divided into a fixed `4 x 4` block grid. `2,000` paired block
bootstrap draws (seed `0xA5716`) resample the **same blocks in both arms**.
Uncertainty is the percentile 95% interval. The point statistic at each radius
is the median mapped `δ` of the four cardinal sectors.

## 5. The one number and its bar

The decisive number is

```text
D4 = abs(mean(δ_grid1-sw4(r=0.90), δ_grid2-sw4(r=0.90)))
```

in native step-width-4 **captured-frame intervals**, with a hierarchical paired
bootstrap interval. Radius 0.90 is fixed because optical astigmatism is an
off-axis aberration. It is not chosen as the maximum after seeing the map.

Verdicts:

* **SURVIVE** — both setup-specific signed 95% intervals have the same sign and
  lie wholly beyond `|δ| = 1.00` frame; the lower 95% bound of `D4` is also
  above 1.00; no registered field, sector, sampling or aperture ladder gives a
  contradictory classification outside uncertainty.
* **KILL** — the simultaneous 95% upper bound is below 1.00 frame in every
  valid controlled-grid cell at all four off-axis radii and all five stacks,
  and no interval excludes zero after multiplicity control. This is C7's
  “sub-step everywhere” null.
* **NARROWED** — a coherent nonzero split survives multiplicity control, but
  every controlled-grid upper bound remains below 1.00 captured frame. The
  aberration exists, but C7's claim that it changes frame election is narrowed
  away at these capture densities.
* **NOT ROBUST** — any primary setup changes sign or threshold class outside
  uncertainty; horizontal-axis versus vertical-axis sectors disagree; any
  off-axis field rung `r >= 0.50`, empirically rescaled sampling rung, or
  aperture rung flips the applicable verdict; fewer than three cardinal
  sectors are valid at the decisive radius; or a required control/refusal
  gate fails.
* **ALREADY ANSWERED IN CORPUS** is unavailable: section 2 found no direct
  commissioned measurement.

The centre tile is a null control and is excluded from the field-flip rule:
on-axis astigmatism should vanish by construction.

### Sampling-width comparison without assuming the camera setting is linear

For each grid setup and step width, fit a robust plane to
`mu = (z_t + z_s)/2` over all valid tiles. Its spatial slope is the target
tilt in frame units. Convert a step-1 or step-10 split to step-4-equivalent
frames by the ratio of that slope to the setup's step-4 slope. The nominal
`1:4:10` setting is **not** treated as a physical calibration. If the slope is
unresolved or the independently fitted x/y slopes disagree by more than 25%,
that comparison refuses.

## 6. Field curvature is not astigmatism

Field curvature and target tilt are common-mode focus shifts. For every tile:

```text
mu    = (z_t + z_s) / 2       # tilt + field-curvature bowl + scene depth
delta =  z_t - z_s            # astigmatic orientation split
```

Both peaks use the same tile, frames, weights, photometric denominator and
bootstrap draw. No fitted bowl is subtracted from `delta`; therefore an
incorrect curvature model cannot manufacture the answer. A robust plane is
removed from `mu` only to display the residual bowl and to rescale the
step-width ladder. Commissioning must add a large common focus ramp and bowl:
`mu` must move by the plant while `delta` changes by less than `0.10` frame.
The deliberate “compare one arm to a fixed global reference” defect must make
that control RED.

## 7. Bias directions declared before measurement (rule 18)

| source | direction | handling |
|---|---|---|
| fixing the headline at the outer field, where astigmatism should be largest | **favours SURVIVE** | radius 0.90 is fixed now; all inner radii and the centre null are reported |
| squared gradients include shot/read noise and alias energy | **favours SURVIVE** by permitting arm-specific noise peaks | flat/no-split controls, G1/G2 sensitivity, peak prominence and bootstrap gates |
| selecting each arm's maximum before fitting | **favours SURVIVE** through winner's-curse separation | fixed synthetic null and focus-axis reversal; report the null with SE |
| a `192 px` tile averages field position and a tilted plane | **favours KILL** by blending distinct local peaks | same fixed size on all arms; synthetic dose ladder measures attenuation |
| four-sector median cancels a global x/y target or sensor asymmetry | **favours KILL** if the lens is decentered and opposite sectors genuinely differ | publish every sector and file NOT ROBUST rather than average a conflict away |
| unregistered breathing changes which repeated grid lines enter a tile | **either direction** | fixed Hann window, no content mask, and the step-width/setup replications |
| fabric thread height and waviness can mimic an orientation split | **favours SURVIVE** | aperture subject cannot establish the verdict; it can only support or break robustness |
| log-baseline choice can move a broad peak | **either direction** | fixed at percentile 5; linear-parabola and no-baseline sensitivities reported but never substituted |

The strongest discretionary choice — outer-field placement — favours C7. A
clean SURVIVE is therefore the verdict to distrust most.

## 8. Commissioning and deliberate plants

Synthetic truth generation is in a module that never imports the estimator.
It creates additive horizontal and vertical gratings, blurs each orientation
with an independently centred through-focus Gaussian PSF, then adds noise.
The checker receives only the generated cube and a separate truth manifest.

At least these controls must pass before any real-effect estimate runs:

1. **P1 known split, fully present:** planted `δ = +4.00` frames at all four
   cardinal sectors; recover within `0.20` frame and record the estimator's
   achieved reading, not merely the physical plant.
2. **P2 dose ladder:** plants `{0, 1, 2, 4}` frames; readings must be monotone,
   the zero reading `<0.10`, and each nonzero reading within 10% or 0.10 frame
   of the fully-present calibrated transfer.
3. **P3 curvature rejection:** add a common ramp of 6 frames and a radial bowl
   of 3 frames; recovered `mu` follows both within 5%, while `delta` changes by
   `<0.10` frame.
4. **P4 cardinal mapping:** all four sectors recover the same sign and their
   range is `<0.20` frame.
5. **P5 focus-axis reversal:** reversing frame order flips `delta` with
   `|δ_forward + δ_reverse| <0.10`.
6. **P6 flat/no-texture:** a flat noisy cube refuses every peak and therefore
   cannot report an astigmatic split.
7. **P7 fixed external predicate:** two literal scalar response tables, not
   generated by estimator or truth-factory code, have peaks fixed at
   `3.25` and `7.375`; recover split `4.125 +/- 0.02`. This is the
   cancellation-immune control required by the dispatch.
8. **P8 uncertainty coverage:** over 100 independently generated noisy
   `δ=1.00` cubes, the nominal 95% interval covers truth 90–99 times and the
   empirical SD / median reported SE lies in `[0.8, 1.25]`.

Each control has one named plant and must be demonstrated RED individually:
pooled arms (P1), a constant `+1` split (P2), a global rather than paired
reference (P3), failure to swap axes in vertical sectors (P4), absolute-value
sign loss (P5), forced fit on flat data (P6), integer argmax (P7), and
independent rather than paired arm resampling (P8). A plant counts only when
the named control itself fails. Required tally: **8 controls pass, 8 plants
RED, 0 missed**.

## 9. Sensitivities and falsifiers

The full real reduction is repeated with:

* tile sizes 128 and 256;
* G1 and G2 separately instead of their quad mean;
* linear three-point parabola and log parabola without baseline;
* block grids 3x3 and 5x5;
* each cardinal sector omitted in turn.

These are sensitivity arms, never opportunities to replace the registered
answer. A sign or one-frame-threshold flip is **NOT ROBUST**.

The lane stops rather than interpreting numbers if the loader cross-check
fails, any commissioning control or plant fails, the centre null excludes zero
by more than one frame in both grid setups, or the primary pair has fewer than
three valid outer sectors.

## 10. Rust consequence registered before knowing the verdict

* A robust **SURVIVE** would justify a follow-on change in
  `crates/strehl-core/src/focus.rs` to expose orientation-resolved responses,
  in `crates/strehl-core/src/pyramid.rs` to elect the two finest bands by a
  steerable/Gx-Gy pair, and in `crates/strehl-cli/src/merge_cmd.rs` to carry and
  recombine the two arms. It does **not** license those edits in this phase-0
  lane; C7's own FRC and flat-ROI gates still apply.
* **NARROWED** justifies orientation-aware reporting in the future D2 acuity
  map but no election change.
* **KILL** means no Rust change: retain the scalar focus response and remove C7
  from the phase-3 implementation queue.
* **NOT ROBUST** means no Rust change until a repeat controlled chart resolves
  the named ladder. It is not permission to pick the favourable stratum.

All scripts and generated outputs will live under this experiment directory.
No file under `D:\personal\macro` will be written.

---

## Amendment 1 — the two decoders expose different valid contracts

Status: **REGISTERED AFTER THE LOADER PREFLIGHT FAILED, BEFORE ANY REAL
SHARPNESS RESPONSE OR FOCUS SPLIT WAS COMPUTED.**

The original §4 required rawpy and `strehl probe` to agree on active dimensions
and white level. The first loader-only preflight correctly made that requirement
RED:

```text
rawpy:        visible 7028 x 4688, black 512, container white 16383
strehl probe: active  7032 x 4688, black 512, linear    white 15360
```

This is not a newly discovered discrepancy and it is not evidence of corrupt
pixels. The corpus already distinguishes the two representations:

* `docs/research/BUILD-CHROMA.md` records rawpy's `4688 x 7028`,
  `raw_pattern [[0,1],[3,2]]`, `RGBG`, black 512 and container white 16383;
* `crates/strehl-raw/src/lib.rs` and `strehl probe` record rawler's
  `7032 x 4688` active rectangle inside its padded decode, black 512 and
  camera-linear white 15360;
* `experiments/M-PHASE0-LCA/src/commission.py::loader_control` explicitly
  accepts both contracts, explains the four-column difference, and uses only
  rawpy's copied 7028-column array for that lane's verdict.

The failed original gate asked two unlike representations to be identical. It
cannot be repaired by silently choosing the one that lets this lane continue.
The replacement gate, fixed now, is:

1. two independent rawpy opens must be byte-identical and each must report
   `(4688,7028)`, `uint16`, pattern `[[0,1],[3,2]]`, `RGBG`, four black levels
   of 512 and container white 16383;
2. the committed release binary must exit zero and report camera `ILCE-7CM2`,
   ISO 100, active `7032 x 4688`, black 512 and linear white 15360 on that same
   directory;
3. a planted padded shape `(5120,7168)` must make the rawpy contract RED;
4. all measurement coordinates are derived from rawpy's visible array only;
   the clipping gate uses the stricter camera-linear white 15360; and
5. shifting every horizontal tile centre by the entire representation
   difference (±2 green-plane columns) is added as a mandatory sensitivity. A
   sign or one-frame-threshold flip is **NOT ROBUST**.

The replacement does **not** claim an independent pixel-by-pixel decode:
`strehl probe` prints no pixel checksum or per-plane moments. That part of the
original requirement is **not verified and is withdrawn**, rather than
pretended satisfied by opening rawpy twice. The two rawpy opens test lifetime
and determinism; the rawler probe independently tests file identity, camera
metadata, geometry and levels.

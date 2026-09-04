# M145 — an input-defined population for M7 colour seams

**Status:** proposal plus commissioned checker fixture.
**Code pin inspected:** `6e581c059070c3ac7b8541b161bcdacf45bb99b7`.
**Scorecard change:** proposed here only; `docs/proposals/2026-09-sota-scorecard.md`
was not edited.

## Verdict

The phrase “regions sourced from different frames” is not a valid definition for
the shipping merge. Strehl now defaults to the pyramid backend
(`crates/strehl-cli/src/merge_cmd.rs:429`). Its default is a soft weighted mean
(`crates/strehl-core/src/pyramid.rs:559-579,1273-1280`), accumulated separately
for every Laplacian band (`pyramid.rs:1788-1811`), and the code explicitly notes
that different bands have different weight fields (`pyramid.rs:786-792`). The
base is an unweighted mean (`pyramid.rs:1688-1693`). One output pixel therefore
has neither one source-frame label nor one candidate-invariant source boundary
**[VERIFIED]**.

The legacy estimator does expose `best_index`, but it then admits the winner
unconditionally and averages every frame passing its focus gate
(`crates/strehl-core/src/merge.rs:343-349,867-870,1715-1723`). Its winner map is
not the shipping pyramid's provenance **[VERIFIED]**. It is also forbidden as a
scorecard input: §1.6 says the checker may not import Strehl's focus map,
weights, contributor mask, noise constants, depth estimate, or certificate.
Historical winner-jump masks therefore cannot close M7. `V-seam.md:44-48`
defined one such internal mask, while `BUILD-CHROMA.md:1339-1382` correctly
warned that winner-index excursions were not themselves proven image seams.

I propose an **input-only focus-transition opportunity manifest**. It locates,
from a calibrated tilted target and the common inputs, where adjacent focal
slices are equally close to best focus. Every product is tested at the same
frozen sites. An empty manifest is `UNMEASURED`, never PASS. A perfect merge
cannot erase its test population because outputs are not consulted when the
manifest is made.

## Normative proposed definition

Terms such as MUST and INVALID below are normative.

### 1. Required seam capture and reference

M7's ordinary uniform ColorChecker is not by itself an adequate seam stimulus.
The seam arm MUST use a separate tilted, matte, colour-textured coupon, or a
composite target containing an equivalent coupon, in the same measured
illuminant/session as the M7 patch capture **[ARGUED]**.

Before any stacker output is opened, freeze and hash:

1. the exact common linear-ProPhoto input TIFFs and their focus order;
2. the common-input-to-chart transforms;
3. the coupon's region polygons and validity mask; and
4. an independently acquired native-grid CIELAB-D50 reference raster. The
   reference MUST come from single-frame, within-DOF views or independent
   scanning/metrology, never from a candidate or comparator focus stack.

The focus sweep MUST contain at least 13 frames on a motorised rail. Successive
rail increments must differ from their median increment by no more than 1%;
otherwise the capture is `UNMEASURED_CAPTURE_INADEQUATE`. Frame number
`j = 0,...,K-1` is then the registered focus coordinate. This restriction avoids
silently treating unequal steps as equal.

The coupon must have fixed fine luminance texture inside its colour regions so
that focus changes are observable, and its local colour/texture is removed by
the reference-error construction below. It needs at least 12 represented
regions: at least four neutral regions with reference median
`C*ab <= 5` and eight chromatic regions with `C*ab >= 20`.

### 2. Input-only focus field

All work is on the native common-input grid after the frozen input-derived
chart transform. Do not use a stacker output in this section.

1. Convert each linear ProPhoto-D50 input to luminance

   `Y = 0.2880402 R + 0.7118741 G + 0.0000857 B`.

2. Tile the coupon bounding box with non-overlapping `32 x 32` pixel tiles whose
   centres are `(16 + 32i, 16 + 32j)`. Keep only tiles wholly inside the frozen
   coupon-valid/common-overlap mask.
3. On each complete aligned input plane, convolve `Y` with

   `Kx = [[-1,0,1],[-2,0,2],[-1,0,1]] / 8`

   and its transpose `Ky`. For tile `t` in frame `j`, set

   `S(j,t) = mean_t((Kx*Y)^2 + (Ky*Y)^2) / median_t(Y)^2`.

   A non-positive median invalidates the tile.
4. A tile has a focus coordinate only when its maximum score is unique, its
   maximizing frame `j` is not an endpoint, and
   `S(j,t) / median_k S(k,t) >= 1.15`. Fit the three samples around the maximum:

   `delta = 0.5 * (S(j-1,t)-S(j+1,t)) /
            (S(j-1,t)-2*S(j,t)+S(j+1,t))`.

   Require a strictly negative denominator and `|delta| <= 1`; then
   `z_t = j + delta`.
5. Fit `z(x,y) = a*x + b*y + c` by ordinary least squares. Compute residual
   median and `MAD`; reject once all tiles farther than
   `3 * 1.4826 * MAD` from the residual median, and refit by ordinary least
   squares. If `MAD = 0`, retain only residuals within `1e-9` of the median.
6. The fit is valid only with at least 256 retained tiles, at least 32 in each
   quadrant of the coupon bounding box, and every retained tile's absolute
   residual `<= 0.25` focus step. Otherwise the capture is
   `UNMEASURED_CAPTURE_INADEQUATE`.

This affine model is justified only for the required planar, equally stepped
rail target. It must not be generalized to arbitrary natural scenes.

### 3. Boundary-site population

For every integer `m`, focus boundary `B_m` is the contour

`a*x + b*y + c = m + 0.5`

that intersects the valid target. It is an independently estimated opportunity
for a transition between adjacent focal slices, not a claim that any merge has
a hard selector there.

Let `n = (a,b)/sqrt(a^2+b^2)` point toward increasing focus coordinate,
`u = (-n_y,n_x)` be its tangent, and
`P = 1/sqrt(a^2+b^2)` be one focus-step pitch in native pixels. Require
`P >= 24 px`. The search dilation is

`D = floor(P/4)` pixels

on each side of the contour. This covers the allowed maximum focus-fit error
and keeps adjacent boundary corridors disjoint.

Clip each `B_m` to each single colour-region mask after the scorecard's 20%
patch erosion. Further erode by `D + 5` pixels so every possible scoring window
below remains inside that same region and the common overlap. Each resulting
connected line segment is ordered from the endpoint with lexicographically
smaller `(y,x)`. Its sites are at arclength

`s = 6 + 12q px`, for integer `q >= 0`.

Thus sampling has a fixed half-spacing phase and 12-pixel spacing; the
9-pixel-tall windows of adjacent sites do not overlap. The **population** is
these site records `(capture, m, region, x, y, n, u, D)`, serialized and hashed
before any output is read. There is no random subsampling.

A capture is reportable only with:

- at least 1,000 sites total;
- at least 10 distinct contours `B_m`;
- at least 50 sites on every retained contour; and
- the 12-region neutral/chromatic coverage above.

The 1,000-site floor is the weakest defensible floor for p99: with nearest-rank
p99 it leaves ten observations strictly above the selected rank. A p99 over 20
members has no tail resolution. The contour and colour-region floors prevent a
single long, convenient boundary from supplying the nominal sample size
**[DERIVED/ARGUED]**.

No output-dependent masking is allowed. A missing, non-finite, clipped, or
out-of-bounds output sample at a manifest site scores `+infinity`; it does not
remove the site. The scorecard's common geometry rule may invalidate the whole
arm, but it may not create different seam populations for different products.

### 4. Per-site colour discontinuity

Convert each output through the frozen ICC to floating-point CIELAB D50. For a
site at `p`, and every integer offset `d` from `-D` through `+D`, bilinearly
sample output and reference Lab at these two `3 x 9` windows:

- minus window: `p + r*n + q*u`, `r in {d-4,d-3,d-2}`,
  `q in {-4,...,+4}`;
- plus window: `p + r*n + q*u`, `r in {d+2,d+3,d+4}`,
  `q in {-4,...,+4}`.

Take the component-wise median of each window, yielding output values
`O-`, `O+` and reference values `T-`, `T+`. Define the shared local anchor and
differential colour errors:

`A = (T- + T+)/2`

`E- = O- - T-`

`E+ = O+ - T+`

`e(d) = DeltaE00(A + E-, A + E+)`

with CIEDE2000 `kL = kC = kH = 1`. The site's value is
`e_s = max_{d=-D...D} e(d)`.

This removes the target's real local texture as a **vector error on each side**.
It is preferable to subtracting two scalar DeltaE00 magnitudes: equal
magnitudes in different chromatic directions can cancel under scalar
subtraction even though the output contains a seam.

Sort the `N` finite-or-infinite site values ascending. The reported p99 is the
**nearest-rank empirical quantile**, one-based rank `ceil(0.99*N)`; do not
interpolate.

If any population prerequisite fails, report
`UNMEASURED_CAPTURE_INADEQUATE`, with no numeric p99. In particular, zero sites
is never zero DeltaE and never PASS. Because the manifest is frozen from inputs,
a truly seamless output still receives the full non-empty population and can
pass with low values; an empty population instead diagnoses an unexercising
capture or failed detector.

### 5. Comparator independence

The same manifest, reference raster, ICC, and scoring code are used byte for
byte for Strehl and every comparator. No product output chooses a site, mask,
normal, search width, reference, or exclusion. No Strehl focus/election map,
pyramid weight, contributor count, depth output, noise constant, or
certificate is consumed. This satisfies scorecard §1.6 **[VERIFIED by
construction]**.

## p99 is not sufficient by itself

A pooled p99 can miss a conspicuous short seam whenever it occupies less than
1% of a large manifest. Increasing the sample count makes that dilution easier,
not harder. I therefore recommend retaining nearest-rank p99 as the
distributional summary but adding a morphology guard:

> No connected contour segment may contain three consecutive 12-pixel-spaced
> sites with `e_s > 1.0`.

Three sites represent a coherent affected length of at least 33 native pixels
(24 pixels between centres plus the 9-pixel tangent footprint), while an
isolated noisy site does not fail the guard. This threshold is **[ASSUMED]**, not
perceptually commissioned. If the program refuses a second bar, my preference
is still to reject pooled p99 alone rather than pretend it excludes sparse
seams. The sparse-defect commissioning arm below is not hypothetical: its
`4.072293 DeltaE00` three-site seam produced a pooled p99 of exactly `0`.

For uncertainty, resampling must cluster by capture, then contour, then site;
treating the 12-pixel-spaced sites as globally IID will understate uncertainty.

## Commissioning

### Method

`experiments/M145-seam-population/commission.py` is the executable fixture and
`results.json` is its complete result. It reads, but does not modify,
`D:\personal\macro\couch-fibers-cpl\DSC00150.ARW` (SHA-256
`9054a75b784915a9dbca5bbb267cf0fe5eeada67de99f6a7b87c386f5a3ceaba`).
A fixed `1024 x 1024` crop of this real project photograph supplies actual
luminance texture and a frozen local Lab reference raster. The script creates a
25-frame deterministic tilted-focus sweep from that texture, estimates the
focus field without using its planted truth, and applies differential `a*`
steps at the true adjacent-focus boundaries. A fourth arm limits the same
large defect to three consecutive sites. This is a checker
commissioning plant, not a claim about a physical ColorChecker or the shipping
merge.

Command:

```text
python experiments\M145-seam-population\commission.py
```

The recovered focus field retained 1,024 tiles (256 in each quadrant), with
focus-coordinate residual p95 `0.187713` and maximum `0.216440` frame. Against the planted field, its
boundary-position error was p95 `0.799488 px`, maximum `0.980736 px`.
It produced 18 contours, 72 sites per contour, and 1,296 sites total, satisfying
the proposed population floor **[MEASURED]**.

### Results

| arm | planted adjacent-region `Delta a*` | sites | nearest-rank p99 `DeltaE00` | maximum | longest run `>1.0` | rule |
|---|---:|---:|---:|---:|---:|---|
| baseline | `0.50` | 1,296 | **0.721553** | 0.726956 | 0 | PASS |
| planted defect | `3.00` | 1,296 | **4.300124** | 4.328416 | 72 | FAIL |
| planted improvement | `0.15` | 1,296 | **0.216801** | 0.218135 | 0 | PASS |
| sparse planted defect | `3.00`, three sites | 1,296 | **0.000000** | 4.072293 | 3 | FAIL by run guard; p99 alone passes |
| identical-frame null | none | 0 | **undefined** | — | — | `UNMEASURED_CAPTURE_INADEQUATE` |

The defect raised p99 by `3.578570 DeltaE00` over baseline. The improvement
reduced it by `0.504752 DeltaE00`. The identical-frame detector had no unique
interior focus peak, emitted zero sites, and invoked the non-pass empty rule
**[MEASURED]**. The sparse plant proves that pooled p99 alone can miss the
failure mode it is named for. The script asserts all five outcomes.

## Exact scorecard text proposed

### Insert after M7 “Exact computation” step 3

> **Boundary-seam population.** Use the dedicated tilted, textured colour-seam
> coupon and its independently measured, pre-output Lab-D50 reference raster.
> From the common inputs only, compute normalized 32x32-tile Sobel focus curves,
> three-point peak coordinates, and the one-pass 3-MAD affine focus field
> specified by M145. Its half-integer contours, dilated normally by one quarter
> focus-step pitch, are clipped to single 20%-eroded colour regions and sampled
> every 12 native pixels from a fixed half-spacing phase. At each site, search
> the frozen corridor with paired 3x9 median-Lab windows and score the maximum
> CIEDE2000 difference between the two sides' local reference-corrected colour
> errors. Freeze and hash the manifest before opening outputs. Require at least
> 1,000 sites, 10 contours, 50 sites per contour, four neutral regions, and
> eight chromatic regions. Any deficient or empty population is
> `UNMEASURED_CAPTURE_INADEQUATE`, never PASS. Output defects are scored as
> infinity, not masked. The p99 is nearest-rank at one-based rank
> `ceil(0.99*N)`. No candidate/comparator output or Strehl internal map may
> affect membership.

### Replacement for the M7 row near line 424

> Median DeltaE00 `<=1.0`, p95 `<=2.0`, maximum `<=3.0`; on the frozen M145
> input-only seam population, nearest-rank boundary-seam p99 `<=1.0` and no
> connected contour segment has three consecutive sites `>1.0`; an empty or
> sub-minimum population is `UNMEASURED_CAPTURE_INADEQUATE`; ICC/300-DPI
> conformance `100%`; no worse than best comparator.

### Replacement for the M7 Success sentence near line 833

> **Success.** **SCORECARD ADDITION:** median DeltaE00 `<=1.0`, p95 `<=2.0`,
> maximum `<=3.0`; on the frozen M145 input-only seam population, nearest-rank
> boundary-seam p99 `<=1.0` and no connected contour segment has three
> consecutive sites `>1.0`; an empty or sub-minimum population is
> `UNMEASURED_CAPTURE_INADEQUATE`; ICC/300-DPI conformance `100%`; and no
> summary is worse than the best comparator.

The existing exact-computation step 4 should be deleted when the insertion is
made; retaining “subtracting the target's true patch-to-patch difference” would
leave two conflicting seam definitions.

## What remains unknown

1. No physical tilted M7 target, textured seam coupon, or independent
   full-field Lab reference is present, so the production population count and
   production M7 seam value cannot be established. Honest current status
   remains `UNMEASURED` **[VERIFIED]**.
2. The commissioning uses real captured texture and colour, but synthetic
   defocus and seam plants. It establishes detector localization, direction,
   population sufficiency, and the empty rule; it does not establish transfer
   to a physical printed target or any product **[MEASURED limitation]**.
3. The inherited `1.0 DeltaE00` seam threshold and my three-site coherence
   guard have not been perceptually validated at the intended print size
   **[UNVERIFIED]**.
4. The proposed `1.15` peak-ratio and `0.25`-frame fit-residual gates passed one
   real-texture plant but have not been piloted across target materials
   **[UNVERIFIED]**. They must be commissioned on development coupons before
   holdout capture, without tuning on scored outputs.

## Defects reported to the orchestrator

- The current phrase assumes a single source boundary that the shipping
  multi-band merge does not possess.
- “Subtract the target's true patch-to-patch difference” is direction-blind:
  two equal DeltaE magnitudes can represent different colour-error vectors.
  The local reference-error construction above removes that cancellation.
- Pooled p99 alone can ignore a short severe seam; the coherent-run guard is
  required if M7 is meant to reject visible localized seams.
- M144's future seam uncertainty resampling needs contour-level clustering in
  addition to capture and site. Otherwise the nominal site count overstates
  independent information.
- The seam arm needs its own textured, referenced stimulus. It may share a
  physical composite target and lighting session with the patch arm, but a
  flat/untextured ColorChecker capture cannot be presumed to exercise focus
  transitions. If the combined target cannot meet the frozen population
  floors, use a separate seam capture; do not relax the floors after seeing
  outputs.

# M84 — ruler metrology pre-registration

**Frozen before enumerating, decoding, previewing, or reading EXIF from either
delivered ruler stack.** The frame counts and capture settings below are the
owner's inventory in `docs/captures-needed.md` §16, not M84 measurements. M84
has read the method sources named below but has not touched
`D:\personal\macro\flat-on-ruler-cpl` or
`D:\personal\macro\highly-angled-ruler-mm-cpl`.

The question is whether the two captures identify an absolute, physically
scaled plane well enough to serve as real-image depth truth. A negative result
is the required result if any identifiability, control, resolution, or
uncertainty gate below fails.

## 1. Source facts and assumptions frozen before data

- **MEASURED elsewhere, not by M84.** M5 measured the composite bellows factor
  `B = N_eff / N_marked = 1 + m/p` only as a bracket
  **`[2.41, 3.06]`** at one working distance. M5 explicitly says its
  `m ~= 2` was derived from its brief because no ruler had been photographed;
  it did not separately measure `m` or `p`.
- **DERIVED elsewhere.** M20 verification gives object-space defocus and
  image-space circle of confusion as `c = m^2 delta / N_eff`.
- **DERIVED elsewhere.** The optics profile derives sensor pitch as
  `35.9 mm / 7008 = 5.122 um`, rounded there to **5.12 um**, and labels the
  35.9 mm sensor width unverified at **+/-0.3%**. The Rust `CameraProfile`
  contains noise constants but no pixel-pitch field. M84 will therefore use
  **5.122 um +/- 0.015 um (systematic, 1 sigma)** and will keep that systematic
  separate from bootstrap precision.
- **ARGUED assumption to test.** Each ruler face is rigid and planar; its long
  edges and graduation lines are straight, and graduation lines are
  perpendicular to the ruler axis. The image-space residuals below can reject
  these assumptions.
- **ARGUED camera model.** Over the accepted ruler polygon, one central
  projection with square pixels, zero skew, principal point at the active-area
  centre, and no radial-distortion term is the primary model. A free one-term
  radial-distortion fit is a sensitivity arm only. If it moves tilt,
  magnification, or depth span by more than their primary 95% intervals, the
  metric result is model-dependent and cannot be called ground truth.

The physical pitch is **not** an assumption. Geometry is first measured in
anonymous graduation units. Millimetres enter only through the inference gate
in §4.

## 2. Locked inputs, frame order, ROI, and flags

| order | stack | inventory N | role | ROI |
| ---: | --- | ---: | --- | --- |
| 1 | `D:\personal\macro\flat-on-ruler-cpl` | 79 | mandatory zero-tilt control and plane-parallel scale transfer | full even visible RAW area |
| 2 | `D:\personal\macro\highly-angled-ruler-mm-cpl` | 299 | tilted-plane measurement | full even visible RAW area |

Files are filename-sorted `*.ARW`; every ARW is used. There is no frame limit,
manual crop, demosaic, white balance, sharpening, or output resampling.
`rawpy.raw_image_visible` is copied inside its context manager. The primary
working image is native RGGB green luma,

`G = 0.5 * (raw[0::2,1::2] + raw[1::2,0::2]) - black`,

with coordinates always reported back in **sensor pixels** (one green-luma
sample spans two sensor pixels). G1 and G2 are retained separately as a
localisation replicate. The expected even visible ROI from the source corpus
is `7028 x 4688` sensor pixels; any different decoded geometry is reported and
used only after the full-area/even-dimension rule above is applied.

ExifTool is run as an audit, not as geometry:

```powershell
exiftool -T -FileName -ISO -FNumber -FocalLength -LensModel `
  -FocusPosition2 -FocusDistance2 -r -ext ARW <stack>
```

M84 expects, but does not presume, one ISO value (100), one marked aperture
(5.6), one focal-length value (200 mm), and the inventory frame counts. Any
disagreement is a finding. No EXIF distance, focal length, or focus-position
tag enters the metric fit.

All generated files stay under `experiments/M84-ruler-metrology/`. The capture
directories and every other external corpus path are read-only.

## 3. Graduation and ruler geometry

### 3.1 Line location

The detector operates over the full frame. A locally sharp envelope is formed
from native-green Sobel magnitude, but no intensity pixel from that envelope
enters a physical estimate. Long straight segments seed two line families:
ruler-longitudinal boundaries and transverse graduation marks. Seeds are
refined on the native green planes by weighted total least squares of gradient
centres in a `+/-6` sensor-pixel normal band. G1 and G2 are refined
independently and then combined by inverse variance.

For each transverse line, intersections with both fitted longitudinal
boundaries define two image points. Ordered transverse lines receive integer
ordinals. A one-dimensional projective sequence

`u(j) = (a*j + b) / (c*j + 1)`

is fit by Huber loss. A line is retained only when it is present in both green
replicates within 1.0 sensor pixel, has at least 5-MAD contrast over its local
background, and its ordinal is unique. There is no manual deletion. Fewer than
20 retained minor intervals, or coverage below 40% of the visible ruler
length, makes the physical result unreadable.

Subpixel localisation uncertainty comes from a block bootstrap over edge
samples and the G1/G2 difference. The empirical line-spread function and its
FWHM are reported. A median 95% line-centre interval wider than **1.0 sensor
pixel**, or a p95 interval wider than **2.0 sensor pixels**, is a diffraction /
contrast failure: no micron-scale claim may survive it.

### 3.2 Plane homography and convergence

After §4 supplies a physical pitch and the control supplies ruler width, tick
ordinal `j` and boundary side `q in {0,1}` define ruler-plane coordinates
`(j*pitch, q*width)`. A normalised DLT seeds a homography. It is refined by
Huber-loss nonlinear least squares over all tick/boundary intersections.
Convergence requires optimizer success, finite full-rank parameters, relative
cost change `< 1e-10` and relative parameter step `< 1e-8` for three
successive iterations. Failure of any condition is non-convergence, not a
licence to change models.

Generalisation is five-fold by tick ordinal (`j mod 5`): fit four folds and
score the held-out fifth. The primary image residual is held-out orthogonal
reprojection error in sensor pixels. The final fit uses all accepted ticks only
after cross-validation.

With principal point fixed at the active-area centre, the two metric-homography
constraints (orthogonal plane axes and equal rotation-column norms) estimate
effective focal length in pixels. They are solved jointly, not from EXIF.
The two individual focal estimates must be positive and agree within **10%**;
the joint bootstrap coefficient of variation must be below **10%**. Otherwise
single-view pose is numerically unidentified and M84 will not emit metric
depth. This is an explicit identifiability gate: one-dimensional ruler spacing
alone cannot separate tilt, magnification, and axial scale.

The plane normal and ray/plane intersections then give tilt, camera-space
depth, and the analytic depth map. Two thousand deterministic tick-block
bootstrap fits (seed `0x4d84_2026`) propagate line, pitch, ruler-width, focal,
pose, and sensor-pitch uncertainty.

## 4. Pitch inference — measure first, name second

The first reported quantity is the anonymous minor-interval spacing in sensor
pixels, including min/median/max and projective trend. Physical pitch is
inferred only if the image itself supplies both:

1. a periodic longest-mark hierarchy with a stable integer number `r` of
   measured minor intervals per longest-mark interval; and
2. readable adjacent printed labels, or a readable unit legend, that identifies
   the physical distance of that longest-mark interval.

Then `pitch = labelled_distance / r`, with uncertainty from line locations.
The obvious candidate **1 mm** is checked only after this inference. Ten minor
intervals between adjacent centimetre labels would infer 1 mm; it is not
entered beforehand. If labels/legend are unreadable, hierarchy is ambiguous,
or the inferred pitch is not 1 mm, that is reported. Without an image-supported
physical pitch, all results remain in graduation units and the capture fails
as absolute physical truth.

## 5. Mandatory zero-tilt control — run and freeze first

No tilted-stack decode starts until the control result JSON and log have been
written.

Each graduation is tracked through all 79 frames by its per-frame projective
line fit, so focus breathing is gathered at the mark rather than materialised
as aligned frames. At five equally spaced locations along each retained mark,
M84 computes native-green Tenengrad magnitude (2-D Sobel followed by the
project's 27-by-27 green-plane box support), divided by that location's robust
`p95-p05` contrast. The primary sub-frame peak is a seven-sample concave
quadratic fit to `log(F - min(F))`; it is accepted only if its vertex lies
inside the seven-sample bracket. A three-sample raw parabola is the sensitivity
estimator and must agree within **0.25 frame**. Spatial locations and G1/G2
provide the peak bootstrap.

The control focus surface is the Huber line `k(j) = a + b*j`. It passes only
if:

- at least 20 graduations have accepted peaks;
- the fitted endpoint-to-endpoint change is at most **1.0 frame**;
- zero lies in the 95% interval for that change; and
- the eventually metric pose reports `|tilt| <= 2.0 degrees` with zero inside
  its 95% interval.

A larger control tilt means the method or the purported control is broken.
M84 will still report diagnostics but will not process the tilted stack into
ground truth.

Only after that pass is plane-parallel magnification measured:

`m_flat = pitch_sensor_pixels * 5.122 um / pitch_object_um`.

The ruler's physical width is transferred without assuming a commercial ruler
width:

`width_mm = (boundary_spacing_px / pitch_spacing_px) * pitch_mm`.

Both use the control's best-focus neighbourhood; uncertainties include the
0.3% sensor-pitch systematic.

## 6. Tilted plane, focus axis, and M5 cross-check

### 6.1 Plane, magnification, and depth

The tilted stack uses the identical line and focus code and the control-derived
metric ruler coordinates. Tilt is `acos(|n dot optical_axis|)`. Local
unforeshortened magnification is

`m(X,Y) = f_px * pixel_pitch_um / Z(X,Y)`,

reported at the valid-mask centre and as a min/max range. This is derived from
image-measured ruler geometry and sensor pitch; EXIF and a lens model are not
inputs.

The validity mask is the convex ruler polygon intersected with the tick
coverage, eroded by the p95 bootstrap boundary error. No background, ruler
mount, extrapolation beyond the outer accepted ticks, saturated patch, or
low-contrast patch is valid.

### 6.2 Microns per frame and drift

At each accepted graduation midpoint, ray/plane intersection supplies physical
depth `z_j` and the focus curve supplies best frame `k_j`. The primary
calibration is Huber regression

`z_j = alpha + beta*(k_j-k0)`,

where `beta` is reported in microns/frame. A quadratic alternative and a
monotone PCHIP calibration are fitted as diagnostics. Drift is the fitted
quadratic derivative at the first and third frame quartiles, reported both in
microns/frame and as a fractional span.

The constant-step assumption survives only if the quadratic lowers
leave-one-tick-out RMSE by less than 10% **and** the 95% upper bound on
first-to-third-quartile step drift is at most **5%**. Otherwise it is refuted;
the monotone calibration may describe the stack, but one scalar step may not.

### 6.3 Independent optical cross-check

For accepted high-contrast tick edges, profiles away from best focus are fit as
the best-focus profile convolved with the line-spread function of a uniform
defocus disk. The disk diameter is constrained to
`c_px = q_px_per_frame * |k-k_best|`; gain, offset, and subpixel translation
are nuisance terms. Fits use offsets 2 through 12 frames on both sides when
available, and are rejected if disk convolution does not beat a Gaussian-width
placebo by 10% held-out RMS.

The metric focus step and image-measured circle-of-confusion growth give

`N_eff = m^2 * beta_um_per_frame / (q_px_per_frame * 5.122 um/px)`

and `B_metric = N_eff / 5.6`. This estimate is independent of M5's spectral
knee. Its 95% interval is compared, without tuning, with **M5's `[2.41, 3.06]`
composite bracket**. Agreement means interval overlap; disagreement is
reported as the stronger finding. If the edge model fails its placebo, M84
reports the cross-check as unreadable rather than forcing a value.

## 7. Frozen accuracy and usability bars

These bars are fixed before the capture is seen:

| quantity | success bar |
| --- | --- |
| held-out homography residual | RMS `<= 1.5` sensor px and p95 `<= 3.0` sensor px |
| control endpoint focus change | `<= 1.0` frame, 95% interval includes zero |
| control tilt | `<= 2.0 deg`, 95% interval includes zero |
| tick localisation | median 95% width `<= 1.0` px; p95 `<= 2.0` px |
| held-out linear focus-depth residual | RMS `<= 10 um` and p95 absolute `<= 25 um` |
| depth-map uncertainty | median 95% half-width `<= 10 um`, p95 `<= 25 um` |
| constant focus step | quadratic RMSE gain `< 10%` and 95% drift bound `<= 5%` |

The claim **"usable as physical ground truth at micron scale" is refuted** by
any mandatory-control failure, ambiguous physical pitch, pose-identifiability
failure, fewer than 20 accepted depth samples, non-monotone focus ordering, or
either depth residual/uncertainty bar failing. If the method is sound but only
a coarser error is achieved, the verdict states that coarser measured accuracy;
it does not round it into a pass.

Pixel residual can be fooled low by fitting too many parameters; five-fold
held-out scoring is the defence. Gradient focus can be fooled high by contrast
and noise; within-mark normalisation, G1/G2 replication, the alternate peak
fit, and the flat control are the defences. A plane fit can hide curvature;
held-out signed residual versus ruler coordinate is reported, not only RMS.

## 8. Control that must fail

A deterministic synthetic fixture contains pixel intersections rendered from a
known plane, camera, ruler pitch, magnification, tilt, and focus step. The
ordinary self-test must recover each within the tighter of one reported
standard error or 1%.

The mutation control byte-replaces the fixture's declared pitch with a value
10% too large. It must:

1. require exactly one matching byte string;
2. write the plant and verify it by byte read-back;
3. run the unchanged self-test and observe a non-zero exit naming the pitch /
   scale error;
4. restore the fixture byte-for-byte in `finally`; and
5. verify the restored hash.

Zero tests, a zero exit, a missing read-back, or a non-identical restoration is
a failed control and blocks every real-data claim.

## 9. Locked outputs and claim labels

The implementation, configuration, logs, JSON results, diagnostic figures, and
map live only in `experiments/M84-ruler-metrology/`. The depth artifact is
`depth-map.npz` at full `7028 x 4688` sensor-pixel coordinates, carrying:

- signed `depth_um` relative to the valid-mask median;
- `uncertainty_um` as a 95% half-width;
- explicit boolean `valid_mask`;
- coordinate origin, pitch, pose, reference depth, quantisation, and units.

The analytic map may be losslessly integer-quantised at `0.1 um`; that
quantisation contributes at most `0.05 um` and is included in uncertainty.

`docs/research/M84-ruler-metrology.md` will label every substantive statement
**MEASURED**, **DERIVED**, or **ARGUED**, namespace imported values (for example
"M5's composite bracket"), report uncertainty on every physical quantity, and
end with candidate facts `P1`, `P2`, ... rather than absolute fact numbers.

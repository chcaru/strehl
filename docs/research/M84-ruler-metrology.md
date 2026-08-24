# M84 — ruler metrology

**Status:** complete negative result. The pre-registration is commit `f6ee015`.
M84 modified only `experiments/M84-ruler-metrology/` and this report.

## Independence disclosure

**MEASURED.** M84 committed its complete methods, artefacts, report, and
negative verdict as `23e35c3` before receiving any sibling result. After that
commit, an unsolicited collision notice relayed a sibling claimant's control
interpretation, anonymous-spacing diagnostics, lens-ceiling pointer, and
projective-geometry / validity-mask cautions. M84 did not open any sibling
file, and none of its methods, numbers, uncertainties, or conclusions was
tuned to that message. The only post-message change is this disclosure.

> ## VERDICT
>
> **MEASURED — THIS CAPTURE CANNOT SERVE AS PHYSICAL GROUND TRUTH AT ANY
> DEFENSIBLE MICRON ACCURACY.** The mandatory zero-tilt control fails before
> the angled stack is allowed to become metrology. Across the visible control
> graduations, the fitted best-focus endpoint changes by **5.248 frames, 95%
> CI [4.714, 5.776]**, against the registered maximum of one frame with zero
> inside the interval. Only **5/11** intervals pass both peak estimators on both
> native green planes.
>
> **MEASURED.** The failure is deeper than the focus slope. The control exposes
> only one ruler boundary, no readable unit legend or adjacent labels, **12**
> candidate graduation lines rather than the required 20, median tick-centre
> 95% width **8.952 sensor pixels** rather than at most one, and p95 width
> **15.160 pixels** rather than at most two. Physical graduation pitch, ruler
> width, plane pose, magnification, and depth scale are therefore
> **UNIDENTIFIED**.
>
> **MEASURED.** A deliberately permissive, post-failure diagnostic finds 14
> apparent graduations in the angled stack, but its 5-MAD sensitivity arm
> finds zero and **0/13** inter-graduation focus curves pass the frozen
> replicate and estimator checks. No constant or drifting focus step can be
> estimated even in anonymous graduation units.
>
> **ARGUED.** M84 therefore emits no `depth-map.npz`. The explicit result is
> `depth_map.emitted = false`, `valid_pixels = 0`; an assumption-scaled plane
> or an all-false file would be easier to misuse than an explicit refusal.
> The attainable physical-depth accuracy is **not coarse-but-finite**. It is
> unbounded because scale and pose are not identified.

## 1. Question, evidence order, and claim discipline

**ARGUED.** M81 §11 leaves two routes after its failed merge-gate calibration:
identify a spatially local response-noise unit on real texture, or choose the
gate by a truth-linked estimator loss. M84 tests whether the delivered ruler
stacks supply the physical truth needed by the second route.

**MEASURED.** The evidence order was:

1. freeze and commit `PREREGISTRATION.md`;
2. inventory and analyse `flat-on-ruler-cpl`;
3. write its result and establish `control_pass = false`;
4. only then decode `highly-angled-ruler-mm-cpl`;
5. run non-metric diagnostics, the synthetic positive control, and the
   required wrong-pitch mutation control.

**ARGUED.** The owner's descriptions and `docs/captures-needed.md` §16 were
treated as hypotheses. In particular, §16.3's claim that the angled ruler
closes the analytic metric-ground-truth request does not survive measurement.

## 2. Capture and metadata audit

**MEASURED.** ExifTool was run recursively over every ARW. The values below are
uniform unless a distribution is shown.

| stack | N | ISO | marked aperture | focal length | composed optical path |
| --- | ---: | ---: | ---: | ---: | --- |
| `flat-on-ruler-cpl` | 79/79 | 100 | f/5.6 | 200.0 mm | FE 100mm F2.8 Macro GM OSS + 2X Teleconverter |
| `highly-angled-ruler-mm-cpl` | 299/299 | 100 | f/5.6 | 200.0 mm | FE 100mm F2.8 Macro GM OSS + 2X Teleconverter |

**MEASURED.** Control `FocusPosition2` counts are 56: 13, 57: 40, and
58: 26. Angled-stack counts are 56: 13, 57: 40, 58: 40, 59: 41, 60: 40,
61: 40, 62: 40, 63: 41, and 64: 4. These maker-note values audit the capture;
they do not enter geometry or depth.

**MEASURED.** Rawpy decodes both stacks as a 7028 x 4688 visible sensor area,
3514 x 2344 samples per green plane, RGGB, black 512, and container white
16383. Every frame was filename-sorted and used. No demosaic, white balance,
sharpening, manual crop, frame limit, or alignment was used.

**MEASURED.** Before/after directory snapshots agree on file count, ARW count,
total bytes, and newest write time for both read-only capture directories.
The control remains 79 files and 5,379,518,464 bytes; the angled stack remains
299 files and 20,075,192,320 bytes.

## 3. Mandatory zero-tilt control

### 3.1 Graduation geometry and resolution

**MEASURED.** The control detector retains 12 graduation lines, giving 11
anonymous intervals over 83.50% of the frame width:

| diagnostic | result |
| --- | ---: |
| interval median | 532.208744 sensor px |
| interval min / max | 526.467303 / 540.128980 sensor px |
| interval coefficient of variation | 0.008962 |
| median tick-centre 95% width | 8.951698 sensor px |
| p95 tick-centre 95% width | 15.159603 sensor px |
| median empirical edge-LSF FWHM | 34.084752 sensor px |
| p95 empirical edge-LSF FWHM | 50.622978 sensor px |
| longitudinal ruler boundaries | one |
| readable printed labels / unit legend | none |

**DERIVED.** Using the source profile's **5.122 +/- 0.015 micrometres per
sensor pixel (1 sigma systematic)**, the tick-centre widths correspond to
45.85 and 77.65 micrometres on the sensor, with sensor-pitch systematic
components of approximately 0.14 and 0.23 micrometres. The empirical LSF
FWHM corresponds to 174.58 micrometres median and 259.29 micrometres p95 on
the sensor, with approximately 0.52 and 0.78 micrometres of sensor-pitch
systematic. Object-space widths are **UNIDENTIFIED** because magnification is
unidentified.

**MEASURED.** These localisation widths fail the registered at-most-one-pixel
median and at-most-two-pixel p95 bars by factors of 8.95 and 7.58. The
registered requirement of at least 20 graduations also fails.

### 3.2 Focus-flatness test

**MEASURED.** Native G1 and G2 each used a 3 x 3 Sobel magnitude, the project's
27 x 27 green-plane box support, local `p95-p05` contrast normalisation, a
seven-point log-quadratic peak, and a three-point raw-parabola sensitivity
peak. A position survives only when both estimators and both green replicates
agree under the frozen bars.

**MEASURED.** Only 5/11 intervals survive. A Theil-Sen line over those accepted
positions gives:

| diagnostic | result |
| --- | ---: |
| endpoint best-focus change | **5.248097 frames** |
| deterministic bootstrap 95% interval | **[4.714059, 5.775578] frames** |
| accepted-line residual RMS | 0.308705 frame |
| accepted-line p95 absolute residual | 0.510593 frame |
| successful bootstrap replicates | 1,807 |

**MEASURED.** The registered control requires at most one frame of endpoint
change and a 95% interval containing zero. Both conditions fail decisively.

**ARGUED.** Per the pre-registration and capture brief, this is an instrument
failure, not evidence that the owner supplied a five-frame tilted control.
M84 does not reinterpret the control to rescue the method. A physical
zero-tilt angle and its uncertainty are therefore **UNIDENTIFIED**, not
5.248 frames translated through an assumed scale.

### 3.3 Plane-fit disposition

**MEASURED.** A metric plane fit was not run. Its registered inputs do not
exist: physical pitch is not image-supported, the second longitudinal
boundary is absent, fewer than 20 graduations survive, localisation fails,
and the focus-flatness control fails.

**ARGUED.** Consequently, control tilt, angled-plane tilt, held-out homography
residual, and their uncertainty intervals are all **UNIDENTIFIED**. Reporting
the ruler baseline's image angle as a three-dimensional tilt would conflate a
line orientation in the sensor plane with plane pose.

## 4. Angled stack: diagnostic evidence only

### 4.1 Frame support

**MEASURED.** At 879 x 586 diagnostic resolution, one analysis pixel spans
eight sensor pixels. Only **39,711 pixels, 7.7095%** of that frame clear the
frozen temporal focus-readability threshold. The largest connected readable
component occupies **1.3586%** of the frame and the mask has **989**
components.

**MEASURED.** An intentionally unmasked affine fit of focus index against
image coordinates has RMS **95.864 frames** and p95 absolute residual
**203.592 frames** over the readable samples. This is a failure demonstration,
not a plane estimate: background occupies most of the frame and the ruler is
a narrow, nearly edge-on wedge.

**ARGUED.** This framing does not instantiate the target requested by
`docs/captures-needed.md` §8, which needs a plane with enough two-dimensional
support to fit and validate an affine depth field.

### 4.2 Graduation sensitivity

**MEASURED.** A post-control-failure all-focus diagnostic chooses one dark
ruler baseline with image angle -20.3616 degrees. That is a two-dimensional
line angle, **not physical plane tilt**, and its integer, 8-sensor-pixel
endpoint construction supplies no defensible physical uncertainty interval.

**MEASURED.** An initial 3-MAD prominence threshold found zero graduations.
After observing that failure, a 1-MAD diagnostic was selected and found 14
apparent graduations. The full threshold sensitivity is:

| prominence threshold | apparent graduations |
| ---: | ---: |
| 0.75 MAD | 14 |
| 1.00 MAD, post-data diagnostic | 14 |
| 1.25 MAD | 14 |
| 1.50 MAD | 13 |
| 3.00 MAD, initial diagnostic | 0 |
| 5.00 MAD, numerical threshold from the registration | **0** |

**MEASURED.** At the permissive 1-MAD setting, 13 anonymous intervals span
88 to 120 sensor pixels, median 96. A one-dimensional projective sequence
fits those integer detections with RMS 2.303 sensor pixels and p95 absolute
residual 4.148 sensor pixels.

**ARGUED.** This is not the registered native-green two-boundary detector or
plane homography. It is quantised at eight sensor pixels, was selected after
the control failed, uses fewer than 20 intervals, and finds no marks when its
prominence multiplier is raised to the registered numerical contrast
threshold. It cannot supply metric pose or validate the registered 1.5-pixel
RMS / 3-pixel-p95 homography bars.

### 4.3 Focus-axis readability

**MEASURED.** All 299 frames were scored around the 13 permissive anonymous
intervals with native G1/G2. **Zero of 13** intervals passes both green
replicates and both peak estimators. Peak candidates are non-monotone and
include boundary, bracket, estimator-sensitivity, and replicate-disagreement
failures.

**MEASURED.** Because fewer than four intervals pass, no linear or quadratic
fit is emitted. Frames per anonymous graduation, quadratic improvement, and
relative drift are **UNREADABLE**. Micrometres per frame are additionally
**UNIDENTIFIED** because neither physical pitch nor plane pose exists.

**ARGUED.** The data therefore neither confirms nor refutes a constant focus
step. It supplies no estimate of the step and no finite drift uncertainty.

## 5. Absolute scale, magnification, and uncertainty

**DERIVED ELSEWHERE.** `F-camera-lens-optics.md` derives pixel pitch from
35.9 mm / 7008 default-crop pixels as 5.12 micrometres and marks the sensor
width unverified at approximately +/-0.3%. M84 uses
**5.122 +/- 0.015 micrometres, 1 sigma systematic**. Contrary to the initial
pointer, Rust `CameraProfile` has no pixel-pitch field.

**MEASURED.** No readable printed unit, adjacent numbered labels, or
unambiguous longest-mark hierarchy appears in the analysed control area.
The physical minor-interval pitch is therefore **UNIDENTIFIED**, with no
finite uncertainty. The obvious 1 mm candidate was not silently assumed.

**DERIVED SENSITIVITY, NOT A MEASUREMENT.** If, contrary to the inference gate,
one assigns exactly 1 mm to the anonymous control interval, then

`m | pitch=1 mm = 532.208744 px * 5.122 um/px / 1000 um = 2.72597`.

The sensor-pitch systematic alone would be +/-0.00798 at one sigma, and the
observed interval extrema map conditionally to 2.69657 through 2.76654. This
is not a confidence interval: it omits the unidentified physical pitch,
projective trend, failed localisation gate, missing second boundary, and
failed control. It must not be quoted as measured magnification.

**ARGUED.** The absolute-quantity disposition is:

| physical quantity | M84 result | uncertainty |
| --- | --- | --- |
| sensor pixel pitch | 5.122 um | +/-0.015 um, 1 sigma systematic, imported |
| ruler minor pitch | **UNIDENTIFIED** | unbounded under admitted evidence |
| control plane tilt | **UNIDENTIFIED** | no finite interval |
| angled plane tilt | **UNIDENTIFIED** | no finite interval |
| subject magnification | **UNIDENTIFIED** | no finite interval |
| focus advance | **UNIDENTIFIED um/frame** | no finite interval |
| focus-step drift | **UNREADABLE** | no finite interval |
| per-pixel physical depth | **UNIDENTIFIED** | no finite interval |

## 6. Diffraction and the actual resolution limit

**DERIVED FROM SYNTHESIS FACT 27 / M5.** M5 measures the composite bellows
factor `B = N_eff/N_marked = 1 + m/p` as **[2.41, 3.06]** at one working
distance. If that bracket transfers to these nearby focus positions, marked
f/5.6 is effective f/13.50 through f/17.14. This range is conditional on M5's
configuration and is not a new M84 measurement.

**DERIVED FROM SYNTHESIS FACT 12, CONFIRMED BY M5.** At M5's representative
`B = 3`, marked f/5.6 is `N_eff = 16.8`; M5's table gives Airy FWHM 1.86
sensor pixels and only 0.036 diffraction MTF at Nyquist. SYNTHESIS fact 28
independently warns that EXIF `FNumber` is marked, not bellows-corrected.

**MEASURED.** The control graduations are visually distinct enough to produce
an anonymous spacing, but their empirical edge-LSF FWHM is 34.08 pixels
median and their line-centre 95% width is 8.95 pixels median. Those are much
larger than M5's conditional 1.86-pixel diffraction-only FWHM.

**ARGUED.** Diffraction is serious and forbids assuming pixel-sharp marks, but
it does not by itself explain M84's failure. Engraving shape, contrast,
near-edge-on framing, absent metric labels, one-dimensional geometry, and the
failed focus control dominate. The measured resolution limit is image-space:
roughly 9-pixel median / 15-pixel-p95 line-centre 95% widths. There is no
defensible conversion of that limit to object micrometres.

## 7. Independent optical cross-check

**MEASURED ELSEWHERE.** M5 did not measure magnification or pupil
magnification separately. It measured their composite
`B = 1 + m/p` as [2.41, 3.06], and explicitly labels its `m ~= 2` as derived
from the earlier brief because no ruler had been photographed.

**ARGUED.** M84 cannot run the planned independent cross-check. The equation
needs metric focal advance and measured circle-of-confusion growth; M84 has
neither. The conditional 2.72597 magnification above cannot test M5 because
its 1 mm premise is not image-identified, while M5's `m ~= 2` was not a
measurement to agree or disagree with.

**ARGUED.** The cross-check result is therefore **N/A, not disagreement**.
M84 contributes no new interval for `B`, `p`, or `N_eff`.

## 8. Falsifying control

**MEASURED.** The deterministic synthetic fixture renders 42 metric-plane
intersections and 21 focus samples from an independent camera and plane. The
unchanged self-test recovers all five registered quantities within the tighter
of one reported standard error or 1%:

| synthetic quantity | truth | recovered | tolerance |
| --- | ---: | ---: | ---: |
| pitch | 1.000000 mm | 1.000000000001 mm | 0.001 mm |
| centre depth | 120.000000 mm | 119.999999999864 mm | 0.02 mm |
| plane tilt | 38.543340551 deg | 38.543340551 deg | 0.01 deg |
| magnification | 0.418296667 | 0.418296667 | 0.0001 |
| focus step | 40.000000 um/frame | 40.000000000189 um/frame | 0.02 um/frame |

**MEASURED.** Synthetic reprojection RMS is
`3.94e-10` pixels. These noiseless synthetic values validate arithmetic and
are not accuracy claims about the ruler captures.

**MEASURED.** The mutation control found exactly one declared-pitch byte
string, replaced 1.0 mm by 1.1 mm, verified the written bytes, and ran the
unchanged self-test. It exited 1 with `PITCH_SCALE_ERROR`: recovered centre
depth became 132 mm, magnification 0.380269697, and focus step 44 um/frame.
The fixture was restored byte-for-byte and its SHA-256 returned to
`a19b588daab14b181ee4d9032b0e479c85105d3c3495f6059ec8f2343073df04`.

**ARGUED.** The control proves the harness can expose an absolute-scale error.
It cannot manufacture the scale evidence missing from the real image.

## 9. Depth-map disposition

**MEASURED.** `data/tilted-result.json` records:

```text
depth_map.emitted = false
depth_map.valid_pixels = 0
metric_geometry.tilt_deg = null
metric_geometry.magnification = null
metric_geometry.focus_step_um_per_frame = null
```

**ARGUED.** No valid ruler polygon can be constructed from one boundary, no
metric ray-plane intersection exists without pose and pitch, and the control
forbids promotion of the tilted diagnostics. A full-resolution array of NaNs
plus an all-false mask would add bytes, not information. The durable refusal
JSON is the ground-truth artefact for this failed capture.

## 10. What capture would work

**ARGUED.** A replacement should change geometry and semantics before changing
the focus operator:

1. Use a certified two-dimensional grid, checker, or calibration plate with
   known pitch in both axes. Keep its unit legend or certificate identifier in
   a readable frame.
2. Fill most of the image with the plane and place it approximately 30 to
   60 degrees from fronto-parallel, not nearly edge-on.
3. Preserve at least two non-collinear metric directions, two complete plane
   boundaries, and 20 to 40 high-contrast intervals across the focus sweep.
4. Shoot a matched plane-parallel control at comparable magnification,
   illumination, aperture, and focus range.
5. Continue using the widest marked aperture available with this
   teleconverter, f/5.6, and add light rather than stopping down. Removing the
   circular polariser is optional if glare can be controlled and exposure is
   the constraint; it does not repair geometry.
6. Include a wider contextual frame proving target identity and units, then
   the frame-filling metrology stack. Image spacing cannot infer the semantic
   unit of an anonymous periodic pattern by itself.

**ARGUED.** M5 suggests f/5.6 retains limited usable contrast, so the current
negative does not establish that the 2x-teleconverted rig can never support
metric truth. It establishes that this target presentation and control cannot.

## 11. Reproduction and durable evidence

**MEASURED.** The experiment used Python 3.12.10, NumPy 2.4.4, SciPy 1.17.1,
rawpy 0.27.0, Pillow 12.2.0, and OpenCV 4.13.0.

**MEASURED.** Principal durable files are:

| file | role |
| --- | --- |
| `PREREGISTRATION.md` | frozen methods and bars |
| `data/control-exif.tsv` | complete control metadata audit |
| `data/control-result.json` | control geometry, curves, bootstrap, and gates |
| `data/tilted-exif.tsv` | complete angled metadata audit |
| `data/tilted-result.json` | coarse readability and explicit map refusal |
| `data/tilted-lines.json` | post-failure graduation sensitivity |
| `data/focus-axis-result.json` | 0/13 focus-axis acceptance |
| `fixture/metric-plane.json` | deterministic synthetic fixture |
| `data/synthetic-selftest-result.json` | five passing synthetic recoveries |
| `data/pitch-mutation-control.log` | plant, nonzero failure, and restoration |
| `data/readonly-verification.json` | before/after capture integrity |

**MEASURED.** Generated PNG, NPY, and NPZ diagnostics are intentionally ignored
by repository policy. No metric depth NPZ was generated.

**MEASURED.** All M84 Python sources compile. The graduation and focus-axis
reducers reproduced byte-identical JSON at SHA-256
`02ee3c9e2e2ac2f4d47adefe30d111847abfd7c0c792fdcb282756d357c119ae`
and
`f154153bfaedf4b8b35710fd61ca6b28d198b5d2487c05f2a983cc47faa79de2`.
The synthetic self-test reproduced byte-identically at SHA-256
`db5d3b6028dcb9ca1061f3b4a475ccbf732327b46bb345657792ae5f8386b760`.

**MEASURED.** Full corpus lint was run as a separate command and exited 1 on
one C3 violation: the concurrent sibling
`experiments/M84b-ruler-metrology/`. The rule-41 ledger records M84b as an
intentional independent claimant on this subject. It is outside M84 ownership,
so M84 neither edits nor suppresses it; no M84 file produced another lint
finding.

## 12. Registered bars and final disposition

| registered requirement | result | disposition |
| --- | --- | --- |
| at least 20 control graduations | 12 | **FAIL — MEASURED** |
| at least 20 accepted focus positions | 5/11 intervals | **FAIL — MEASURED** |
| control endpoint change <=1 frame, CI includes zero | 5.248, CI [4.714, 5.776] | **FAIL — MEASURED** |
| median / p95 localisation <=1 / 2 px | 8.952 / 15.160 px | **FAIL — MEASURED** |
| two longitudinal boundaries | one | **FAIL — MEASURED** |
| pitch supported by image labels/hierarchy | no labels or unit | **FAIL — MEASURED** |
| physical pose identified | no | **FAIL — MEASURED** |
| at least 20 accepted depth samples | 0 | **FAIL — MEASURED** |
| focus-depth RMS <=10 um, p95 <=25 um | not identifiable | **N/A — ARGUED** |
| map uncertainty median <=10 um, p95 <=25 um | no valid map | **N/A — ARGUED** |
| focus-step drift upper bound <=5% | no accepted intervals | **UNREADABLE — MEASURED** |

## 13. Candidate facts for owner review

| candidate | claim | class | source |
| --- | --- | --- | --- |
| P1 | Both ruler stacks are uniformly ISO 100, marked f/5.6, 200 mm, and identify the FE 100mm F2.8 Macro GM OSS + 2X Teleconverter; N is 79 control and 299 angled. | MEASURED | `control-exif-summary.json`, `tilted-exif-summary.json` |
| P2 | The mandatory flat-control focus surface changes 5.248 frames end to end, 95% CI [4.714, 5.776], with only 5/11 accepted intervals; the registered zero-tilt control fails. | MEASURED | `control-result.json` |
| P3 | The control exposes 12 tick lines, one ruler boundary, no readable unit legend, median/p95 localisation widths 8.952/15.160 sensor px, and empirical edge-LSF FWHM 34.085/50.623 px. | MEASURED | `control-result.json` |
| P4 | Physical pitch is not image-identified. Assigning 1 mm would imply `m = 2.72597`, but that is a sensitivity assumption, not measured magnification. | MEASURED / DERIVED | `control-result.json`; §5 |
| P5 | The angled capture has only 7.7095% readable coarse pixels, its largest readable component is 1.3586% of frame area, and it presents the ruler as a narrow wedge rather than a frame-filling plane. | MEASURED / ARGUED | `tilted-result.json` |
| P6 | A post-data 1-MAD diagnostic sees 14 angled graduations; its initial 3-MAD and corresponding 5-MAD sensitivity arms see zero. No registered plane geometry survives. | MEASURED | `tilted-lines.json` |
| P7 | Zero of 13 angled inter-graduation focus curves passes both native-green replicates and both peak estimators. Constant step, drift, and micrometres per frame remain unreadable/unidentified. | MEASURED / ARGUED | `focus-axis-result.json` |
| P8 | M84 cannot cross-check M5's `[2.41, 3.06]` composite because neither metric focus advance nor defocus-blur growth is identified; this is N/A, not disagreement. | ARGUED | M5; §§5–7 |
| P9 | A deterministic +10% pitch mutation is read back, rejected with a named scale error, and restored byte-for-byte to its original SHA-256. | MEASURED | `pitch-mutation-control.log` |
| P10 | This capture cannot provide physical depth truth at a finite defensible accuracy; no depth map is emitted and the explicit valid count is zero. | MEASURED / ARGUED | `tilted-result.json`; VERDICT |

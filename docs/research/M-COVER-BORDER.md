# M-COVER-BORDER: why native Crop is contaminated inward

Date: 2026-09-03

> **Correction resolved.** The two-worker b2/b7 rerenders do not equal the old
> cover-default files; the previous claim that they did was wrong.
> `profile-final.json` therefore mixed worker/order histories in its b4 ladder
> and is superseded for that intervention. A fully matched rerun reproduces
> Scale 8 px / Crop 256 px and gives the exact Crop ladder 8/32/256,
> log2 slope 1 and `R²=1`. The correction, contradiction predicates and two
> instrument amendments were committed before their corresponding scores.

## Verdict

The mechanism is **late-crop black-fill boundary poisoning followed by
nonlinear, cross-band pyramid reconstruction overshoot**.

`CoverMode::Crop` does not resample the final image, but it does not make the
common crop rectangle the merge domain either. Each aligned frame is first
warped over the complete `3516x2344` reference plane. Where a shifted frame has
no source sample, the warp writes that frame's black level. `prepare_frame`
subtracts the black level, turning those unavailable samples into exact zero.
The seven-band pyramid is then built, weighted, merged and collapsed over the
whole plane. Its five-tap analysis/reconstruction filters see the artificial
real-signal-to-zero step outside the common intersection. Independent,
spatially varying choices at each band prevent those edge transients from
cancelling as they would in a single linear pyramid. The collapse transports a
positive level error inward at dyadically increasing scale. Only after collapse
does `write_merged` address the covered rectangle.

The emitted Crop rectangle itself is not missing data: all 22 frames have valid
Catmull-Rom samples at every emitted pixel. The bad values are produced by
allowing invalid samples *outside* that rectangle to participate in nonlocal
filtering before the rectangle is cut out.

On 109, `Scale` is not concealing the same defect by smearing it thinly. It
contracts the placements before the gather, so all 22 frames cover the full
pyramid domain and the artificial black step does not exist. Its
preregistered positive residual mass through 256 px is `0.05833%` of Crop's,
not approximately conserved. The same conserved-error test is unresolved on
113, whose radial statistic fails a new artificial-boundary specificity
control.

This is a software defect, not a physical necessity.

## Evidence status

Labels in this report mean:

- **MEASURED**: read from a committed instrument and frozen image inputs.
- **VERIFIED**: direct source/geometry fact or exact hash reproduction.
- **DERIVED**: arithmetic from measured or verified values.
- **ARGUED**: the causal interpretation that best explains the discriminating
  interventions.
- **UNKNOWN**: deliberately not established by this lane.

The preregistration was committed as `067ee68c35b25c8e753b653fcc4f52c3637e604f`
before new source, geometry or image measurements. The first real profile had
an invalid specificity statistic and is retained as
`results/profile-v1-invalid.json`; it is not used as evidence. The repair was
frozen before another Crop score in `AMENDMENT-1.md` and commit `447b988c`.
`AMENDMENT-2.md` and commit `9d348c55` corrected an implementation omission of
the preregistered 8 px candidate before another Crop score. Commit `38b23a4c`
commissioned the residual-mass statistic, including an improvement plant,
before `results/profile-final.json` was generated.

The contradiction follow-up was preregistered in
`CONTRADICTION-PREREGISTRATION.md`, commit `61196edc`, before matched Scale or
113 renders. `contradiction.py` and its GREEN commission were committed as
`75fcf84e` before real scoring. A concentration-denominator implementation
error was frozen and corrected in `CONTRADICTION-AMENDMENT-1.md`, commit
`25f5f85f`, before the corrected 109 score or any 113 score. The centered
artificial-boundary control was frozen and commissioned in
`CONTRADICTION-AMENDMENT-2.md`, commit `ed69e7b2`, before that control was read
on either source.

## Numerical contradiction resolved

The three disputed records do not measure one admitted physical safe inset.
They mix two sources, two output spaces, two coordinate systems, and—most
importantly—nominal tail statistics with geometry after a failed specificity
gate.

### Common definition

The independent rerun used one pinned executable, one environment and default
camera-linear RGB16 for both sources and both cover modes. For green:

```text
E(lo,hi) =
  (mean G_b7(lo,hi) / mean G_b2(lo,hi)) / R_deep - 1

R_deep =
  mean G_b7(distance >= 768) / mean G_b2(distance >= 768)
```

Distance is from the emitted boundary in **binned linear-plane pixels**.
Threshold is `abs(E) <= 0.001`. Fixed edges are
`0,2,4,8,16,32,64,96,128,160,192,256,320,384,448,512,640,768`.
The nominal safe inset is the smallest registered edge at least 8 for which
that and every deeper annulus pass. It becomes an admitted black-fill reach
only when the statistic is specific to a physical boundary.

One linear-plane pixel is two full-resolution sRGB-output pixels, and two
sensor photosites, per axis.

### What each historical number means

| Record | Source/space | Native statistic | Linear-plane px | Full-resolution output/sensor px | Admission |
| --- | --- | ---: | ---: | ---: | --- |
| cover-default | 109, default linear | Scale 8 / Crop 256 plane px | 8 / 256 | 16 / 512 | specific on 109 |
| deleted `COVER-BORDER-RESULT` | 113, nonlinear full-resolution sRGB | 768 / 768 output px | 384 / 384 | 768 / 768 | withdrawn |
| deleted corrected-linear profile | 113, default linear | 640 / 320 plane px | 640 / 320 | 1280 / 640 | nonspecific |
| sensitivity required clearance | full-resolution site coordinates | 1280 / 640 output px | 640 / 320 | 1280 / 640 | copied conservative gates |

The sRGB record also used `deep_start=768` **sRGB output pixels**, equivalent
to 384 plane px, not the linear profile's 768 plane px. It was rendered through
a nonlinear viewing path explicitly documented as not for measurement.
Both linear profile records use threshold `0.001`, deep start 768 plane px and
the fixed edges above. The sensitivity file performs no new border profile; it
copies the corrected-linear nominal values into a site-clearance filter.

The sensitivity file does not say that Scale physically needs 1280 px and
Crop 640 px. Those are the nonspecific linear nominal tails multiplied by two
to filter a full-resolution site list. Its
`minimum_retained_clearance_px={scale:1289,crop:1263}` reports where the few
surviving paired patches happened to lie after the stricter Scale gate removed
38 sites. Those observed coordinates are geometry; they are not minimum safe
requirements. Inferring “Crop needs half of Scale” from them is a category
error.

### Independent matched rerun

**MEASURED** (`results/common-linear-109.json`,
`results/common-linear-113.json`):

| Source | Scale nominal safe | Crop nominal safe | Scale specificity | centered artificial-window safe, Scale/Crop |
| --- | ---: | ---: | --- | ---: |
| 109 | **8 px** | **256 px** | passes | 8 / 8 |
| 113 | **640 px** | **320 px** | fails | 320 / 320 |

The 109 result uses fresh b2/b7 renders for both modes with identical
two-worker ordering. It reproduces cover-default's 8/256 exactly.

The 113 rerun independently reproduces the deleted corrected-linear nominal
safe values. Its serialized map also reproduces the deleted map SHA-256
`A5DF650CCE1224A7B6F54B5570B0BC1E643F1728B030D2496BD2BC13E462623E`.
Against the deleted JSON, maximum row-effect disagreement is
`9.06e-8`; neither historical JSON value was adopted on trust.

The decisive specificity control profiles a centered `1024x1024` window whose
edge is artificial, not an output boundary. On 113 that control returns 320 px
for **both** modes and peaks at `1.0088%` for Scale and `1.0213%` for Crop,
despite the window being 660/637 px from the physical output edge. The 113
tail statistic therefore fires on scene structure away from any emitted
boundary. Its physical 640/320 values cannot be interpreted as required safe
insets or as evidence that Crop is twice better.

On 109 the same artificial control returns 8 px for both modes, with peaks
`0.0983%` and `0.0897%`, below threshold. Crop's physical 256 px profile is
therefore boundary-specific on that source.

### Program-level disposition

**The 8 px / 256 px cover-default result survives exactly on 109. It is not a
measurement artifact on that source.** The repaired matched Crop ladder and
the artificial-window control strengthen that conclusion.

**It does not survive as a general 32x law.** On 113 the common statistic is
nonspecific, so neither 640 nor 320 is an admissible boundary requirement and
their reversed ordering says nothing about which cover mode is safer.

The shipping default therefore is not resampling 98% of 109 to avoid an
imaginary defect. It is avoiding a real, stack-specific late-crop/pyramid
boundary defect. But the evidence does not establish that Scale always settles
at 8 px, that Crop always needs 256 px, or any finite general inset. Scale can
itself produce a large b7/b2 radial statistic on structured scenes; absence of
black fill does not guarantee this particular statistic will read 8.

This does not vindicate Scale's resampling or weaken the case for repairing
Crop. Scale still changes `98.1462%` of the registered external overlap and may
remain implicated in M8 overshoot. It establishes only that the 109 border
blocker was real rather than invented by a unit or output-space mistake.

## Recovered prior-corpus review

The orchestrator identified a deleted V-HEADTOHEAD3 cover corpus only after
this experiment, report and evidence had already been committed as
`f83de900a2751e2483f2f2f1afa8dc10d9c7d643`. I reviewed it read-only from
`d1ad7458^`; no file was restored and none of its reported numbers was imported
as evidence.

The named preregistrations, both corrections and all three result JSONs were
read. The Python files were statically inventoried, and the border-relevant
render, statistic, commissioning and measurement routines in
`cover-border.py` were read in full. `cover-check.py`, `cover_core.py` and
`cover-commission.py` are principally the V-HEADTOHEAD3 geometry, site-mapping,
ordinal spectral-power and bootstrap apparatus rather than a border-mechanism
instrument.

The reusable part of `cover-border.py` is a sound convergent design:

- `border_rows` computes the same b7/b2, deep-normalized,
  distance-to-emitted-border annular effect and tail safe inset;
- its commission includes a null, a `+2%` defect, a `+0.05%` improvement,
  an external annulus oracle and four degradation mutants;
- its render path clears inherited `STREHL_*`, pins provenance and fails closed
  on hashes, geometry and frame counts.

It is not equivalent to the completed mechanism instrument:

| Capability | Deleted V-HEADTOHEAD3 harness | M-COVER-BORDER |
| --- | --- | --- |
| b7/b2 annular profile | yes | yes |
| commissioned defect/null/improvement | yes | yes |
| restoration plant | no | yes |
| b2/b4/b7 causal depth ladder | no | yes |
| exact contributor/slack audit | no | yes |
| frozen source/literal audit | no | yes |
| synthetic zero-boundary/continuous-extension commission | no | yes |
| conserved positive-error test for Scale | no | yes |

In particular, the deleted code contains no positive residual-mass or
conserved-error calculation, so it does not test hypothesis 5. Its sRGB profile
was explicitly withdrawn for output-space specificity failure. Its corrected
camera-linear result reports `specific=false` and
`PROFILE_NOT_SPECIFIC_ON_113`; the sensitivity result keeps
`black_fill_reach="UNRESOLVED"` and stops for insufficient central sites.
None of its values was imported. The later common-linear rerender independently
reproduced its 640/320 nominal profile before retaining the same nonspecific
disposition.

**Decision:** keep the M-COVER-BORDER harness. It had already been
preregistered, commissioned and reproduced; it uses the already-burned 109
unit, obeys the current six-thread cap, and adds every discriminator needed for
the mechanism and conserved-error question. Replacing it with a hard-coded
113/eight-thread harness would lose causal tests and create new provenance
without benefit. The prior corpus is cited here as a convergent instrument
design and an independent warning about narrow-annulus specificity, not as a
source of results. The frozen preregistration was not edited retroactively.

## Prior result and independent re-derivation

The prior lane established:

- Crop exactly matched external LibRaw for all `24,580,566` tested samples,
  while Scale changed `98.1462052%` of its tested overlap
  (`cover-default.md:230-234`).
- The independent second-session replication made all `72,106,680` emitted
  Crop RGB16 samples exact while Scale changed `94.7696%`--`99.1441%`
  (`cover-default.md:22-23`).
- Crop's 8--16 px ring reached `+2.6106%`
  (`cover-default.md:366`).
- Scale's minimum safe inset was 8 px and Crop's was 256 px; the old 256 px
  inset retained `64.6047%` of the original plane
  (`cover-default.md:386-388`).
- The registered 128 px and 80% gates failed
  (`cover-default.md:411-413`).
- The previous work could establish only “256 px is the smallest evidenced
  safe inset on 109; no finite general safe inset”
  (`cover-default.md:399`).

Those facts motivated this mechanism experiment. The external-decoder result
was not repeated here. The 109 border profile was subsequently re-rendered and
re-derived independently under the common-linear follow-up; no general safe
inset is claimed.

## Frozen source and render

All source citations below refer to the pixel-producing source commit
`4e5278870a5e6ff6e0da38762f716e5291508c16`, not to a moving working tree.
The executable was:

```text
D:\strehl-out\cover-default\target\release\strehl.exe
bytes:   9,913,344
sha256:  1AC423529D5AAD88B7141801E47DCD612FCA8061558578A88592DB715CE81A0F
```

The new middle intervention was:

```text
D:\strehl-out\M-COVER-BORDER\q3-109-crop-b4.tiff
bytes:   48,136,827
sha256:  4B98B8D31F8FBB9F37B484B928508A74894C0259FF30AFA7E69C97A3CF39BC10
```

It reused the already-burned `109MSDCF` unit and frozen sidecar:

```text
experiments\M-PHASE0-SPLIT\out\real-109\109-warpmap.txt
sha256: C29CAB9C6F944F4D03C4402998E54AAD4D4221CC450AC4BEF42A453DE848434D
```

No outcome was read from a new holdout unit. `D:\personal\macro` was read only;
all new render outputs went to `D:\strehl-out\M-COVER-BORDER`.

## Code path that creates the defect

### 1. Crop preserves the unscaled placements

**VERIFIED.** `align_cmd.rs:1667` returns the placements unchanged for
`CoverMode::Crop`. Scale instead composes a centre contraction into every
placement before gathering.

The covered rectangle is calculated with a 3 px guard
(`align_cmd.rs:1738,1761`) but it is not yet used as the pyramid domain.

### 2. Unavailable full-plane samples become zero-valued signal

**VERIFIED.** `merge_cmd.rs:4801` calls
`align_cmd::warp_frame_in_place`. The warp calls
`sample_checked` at `align_cmd.rs:2108`; a failed sample becomes `black_dn` by
`align_cmd.rs:2135`. `prepare_frame` starts at `merge_cmd.rs:4751`, obtains the
black level at `merge_cmd.rs:4825`, and black subtraction maps that fill to
zero before the frame is folded.

Only 7 of 22 placements cover the complete unscaled plane with the 3 px guard.
Therefore 15 frames contain an artificial zero region somewhere outside the
common crop.

### 3. The complete contaminated plane enters every pyramid band

**VERIFIED.** `BandWorker::fold` calls
`add_frame_with_gain` at `merge_cmd.rs:4699`.

The pyramid uses the five-tap kernel
`[1,4,6,4,1]/16` (`pyramid.rs:79`), seven bands by default
(`pyramid.rs:136`), repeated reduction and expansion
(`pyramid.rs:151,211`), band construction/collapse
(`pyramid.rs:323,352`), local smoothed energy
(`pyramid.rs:1644`), and an independently accumulated result at each level
(`pyramid.rs:1679`). Final per-band resolution/collapse begins at
`pyramid.rs:2185`.

This is nonlocal in space and nonlinear across frames: a zero boundary changes
both a frame's Laplacian coefficients and the local evidence used to choose
weights. Independently resolved bands no longer retain the exact
analysis/reconstruction relationship of any one input frame. A hard zero step
therefore produces a net reconstruction excursion rather than a cancelling
linear filter transient.

### 4. Crop occurs after collapse

**VERIFIED.** `merge.finish` has already collapsed the pyramid at
`merge_cmd.rs:5829`. The rectangle is merely passed onward at
`merge_cmd.rs:5922`. `write_merged` starts at `merge_cmd.rs:7052`, and the
source itself labels `merge_cmd.rs:7079` as “THE ONE PLACE THE CROP IS
APPLIED”. The crop is addressing performed on the already reconstructed plane.

This ordering is the defect.

## Measurements that identify the mechanism

### Instrument commissioning

`instrument.py commission` went GREEN on an untouched null, RED on a planted
boundary defect, GREEN on a planted improvement, and returned to RED when the
defect was restored.

**MEASURED** (`results/commission-final.json`):

| Plant | Peak | Safe inset | Positive radial mass |
| --- | ---: | ---: | ---: |
| untouched null | `0` | `8 px` | `0` |
| `+2%` in outer 64 px | `+2.0000%` | `64 px` | `0.0046875` |
| improvement: `+0.05%` in outer 64 px | `+0.0500%` | `8 px` | `0.0001171875` |
| restored `+2%` defect | `+2.0000%` | `64 px` | `0.0046875` |

The improvement retained `2.5%` of the defect's positive mass, a `97.5%`
reduction. This commissions both the threshold/reach detector and the
nonnegative mass statistic against a possible no-op.

The common-linear contradiction instrument was separately commissioned
(`results/contradiction-commission.json`). It passed 24 controls/plants:
null, defect, improvement and restoration; swapped bands; threshold, edge and
normalization mutations; binary/map/exit/shape/dtype guards; all unit
conversions; and the centered artificial-boundary control. A physical outer-64
plant left the central control at 8, while a planted ring on the artificial
window returned 64.

A separate synthetic operator commission fed a real-to-zero boundary step
through the production five-tap reduce/expand geometry and deliberately mixed
the affected reconstruction. Its measured threshold reaches were:

| bands | reach |
| ---: | ---: |
| 2 | `10 px` |
| 4 | `40 px` |
| 7 | `317 px` |

The log2(reach)-versus-band slope was `0.997139`, `R²=0.999998`. Replacing the
zero exterior with a continuous extension reduced the synthetic error to
exactly zero. This does not prove the production amplitude; it commissions the
proposed transport mechanism and its octave scaling.

### Coverage falloff was not present in emitted Crop pixels

**MEASURED** (`results/coverage.json`):

```text
plane:                       3516 x 2344
Crop rect:                   x=23, y=16, 3470 x 2312
placements:                  22
contributors at Crop sites:  min 22, max 22
minimum exact site slack:    3.086628 px
whole-plane placements:      7 / 22
Scale site slack:            2.251502 px
```

Thus the direct contributor count does not fall from 22 toward the emitted
border. It cannot explain the level profile. Coverage does fall *outside* the
rectangle, and those unavailable external samples are precisely what poison
the pyramid's filter support.

### Band depth moves the boundary in octaves

The corrected intervention held capture, sidecar, placements, cover mode,
resampler, worker count and backend constant and changed only
`--pyramid-bands`. It uses the fixed historical edges, not the superseded
Scale-selected uniform bins.

**MEASURED** (`results/common-linear-109.json`):

| Crop bands | safe inset versus Crop b2 | peak absolute level effect |
| ---: | ---: | ---: |
| 2 | `8 px` | `0` (self-control) |
| 4 | `32 px` | `2.5765%` |
| 7 | `256 px` | `2.6106%` |

The log2-reach fit has slope `1.000000`, `R²=1.000000`. Five additional bands
predict a spatial ratio of `2^(7-2)=32`; the measured endpoint ratio is exactly
`256/8=32`.

**ARGUED.** This is the decisive discriminator. Neither an alignment window,
photometric fit, a fixed contributor-count profile nor Catmull-Rom's 2 px
support changes when only pyramid depth changes. Repeated dyadic pyramid
support does. The observed reach tracks it almost one-for-one over the three
registered depths.

The old “256 px” is still a registered bin edge rather than a literal kernel
radius: the last failing interval is 192--256 px and every interval beginning
at 256 passes. The exact octave ladder shows why that coarse edge is selected.

### Scale does not smear a conserved Crop defect

The preregistered test compares b7 to b2 within each mode, normalized by the
deep interior. The authoritative 109 values below use matched fresh renders.

**MEASURED** (`results/common-linear-109.json`):

```text
Crop peak before deep region:                     2.610634%
Scale peak before deep region:                    0.064717%
Scale / Crop peak ratio:                          2.478976%

Scale / Crop positive radial residual mass
through 256 px:                                   0.058335%
over the full plane:                              1.437374%
preregistered rejection maximum:                  20% in both scopes
```

Both preregistered rejection predicates pass by wide margins. A rescale that
merely spread the same positive error over a larger area could lower its peak,
but it would approximately conserve positive residual mass. It does not.

Crop places `98.1615%` of its positive residual level mass within 256 px;
Scale places only `3.9346%` there. This is consistent with a localized Crop
boundary field and a much smaller, mostly non-boundary Scale difference.

The physical explanation is direct: Scale composes the contraction *before*
gathering, and geometry confirms all 22 contracted frames cover the complete
full-plane pyramid domain. Crop leaves the unavailable exterior in place until
after reconstruction.

On 113, Scale/Crop positive-mass ratios are `15.2404%` through 256 px and
`33.4610%` over the full plane. Per the frozen predicate, that is
**UNRESOLVED**, not conserved-error support. Its artificial-boundary control
also fires, so the nominal 640 px Scale tail cannot be assigned wholly to a
physical output boundary.

## Alternatives tested

### A literal 128/256 px production neighbourhood

**TESTED AND REJECTED AS THE SPATIAL MECHANISM.** The frozen-source search found
no merge/election/halo/gate operation with a 128 px half-window or 256 px
boundary radius.

Relevant hits were:

- alignment span/fine-tile settings used to estimate the already-frozen
  sidecar;
- diagnostic integer scaling by 256;
- comments and tests;
- `BandGain::measure_uncached`'s minimum `256x256` deterministic synthetic
  calibration field (`pyramid.rs:462`).

The `BandGain` field produces spatially homogeneous per-band coefficients, not
a 256 px image neighbourhood. It may influence amplitude, which this lane did
not isolate, but it cannot explain why the same sidecar's reach changes
8→32→256 when pyramid depth changes. The round number came from measurement
binning, while the causal scale comes from repeated dyadic filtering.

### Fewer contributing frames near the Crop border

**TESTED AND REJECTED for output sites.** The exact sidecar geometry gives
22 contributors everywhere in the emitted Crop rectangle. There is no
22→fewer radial count profile to correlate with the `+2.61%` level profile.

The distinct exterior-coverage fact—15 frames become unavailable somewhere
outside the rectangle—is part of the accepted mechanism, because the pyramid
reads across that boundary.

### Photometric normalization fitted over the wrong support

**TESTED STRUCTURALLY AND REJECTED for this frozen backend.**
`run_pyramid` identifies photometric gain as “not applied” at
`merge_cmd.rs:5579`. No fitted photometric gain can create this render's level
excess. The warning in `photometric.rs` remains relevant to other backends, not
this one.

### Catmull-Rom support at the edge

**TESTED AND REJECTED AS THE LONG-RANGE TRANSPORT.** Catmull-Rom support is
2 px (`align.rs:2867,2888`); the source's warning about one additional
unavailable pixel per side is at `align.rs:2765`. The measured Crop rectangle
still has `3.086628 px` exact full-resolution site slack. This can govern the
last few valid coordinates, not a 256 px field. Most importantly, changing
only pyramid depth moves the reach by exactly 32x.

### Scale masks the same defect

**TESTED.** On 109, rejected: Scale's positive residual mass is not conserved,
and the centered artificial-boundary control remains at 8. Scale removes the
artificial uncovered region before pyramid analysis; its 8 px result is not a
smeared Crop defect.

On 113, the conserved-error predicate is unresolved, but the radial instrument
is also nonspecific: a centered artificial boundary returns 320 px in both
modes. Therefore 113 supplies neither evidence that Scale cleanly mitigates the
Crop defect nor evidence that it conserves and conceals it.

## Defect versus physical necessity

**VERIFIED:** every emitted Crop pixel has a valid Catmull-Rom value from every
one of the 22 frames.

**ARGUED:** therefore no 256 px physical inset is required by absent capture
data. A small geometric guard remains physically necessary because a resampler
cannot evaluate beyond source support. The existing common rectangle already
provides at least `3.086628 px` exact site slack against 2 px Catmull-Rom
support. The additional hundreds of pixels are an implementation-order defect:
invalid exterior values are admitted to a nonlocal operation before a valid
domain is enforced.

## Proposed fix — description only

Do not change `CoverMode::Crop` into a post-collapse address window.

In `crates/strehl-cli/src/merge_cmd.rs`, change `run_pyramid` and the
`BandWorker::fold`/`prepare_frame` path so that the common Crop rectangle is the
analysis, weighting, accumulation and collapse domain *before*
`BandMerge::add_frame_with_gain` sees a frame:

1. Keep the original full-plane coordinate system while evaluating each warp;
   the transform and CFA/full-resolution gather coordinates must not be
   re-based accidentally.
2. Allocate or present each prepared luma/variance/RGB plane only over
   `fit.rect()` for Crop. No black-filled sample outside that rectangle may
   enter `Pyramid::build`, local energy smoothing, band weighting or collapse.
3. Carry the crop origin `(x,y)` alongside the cropped plane for any later
   coordinate-dependent consumer and for output metadata.
4. Write the collapsed cropped plane directly. Do not apply the same crop a
   second time in `write_merged`.
5. Preserve current Scale behavior and dimensions.

A mathematically equivalent alternative is a shared continuous boundary
extension for every prepared frame, provided that:

- the extension is derived only from valid samples;
- every frame uses the same emitted-domain convention;
- filled samples can affect filters but can never be emitted as observations;
- commissioned tests show no new level or detail bias.

Early domain restriction is preferable because it gives the operation honest
semantics: the pyramid never receives values for coordinates Crop promises not
to emit.

For this fix to work, all pyramid operations, including local energy/variance
smoothing and every reduced level, must use the same cropped domain. Cropping
only the RGB bands after their weights were computed on the full plane would
leave the poisoning path intact.

## Predicted effect

**PREDICTION, not measured:** on 109, the safe inset should fall from the
present 256 px estimate to the Scale/control floor, `<=8 px`.

An 8 px inset on the `3470x2312` Crop rectangle leaves `3454x2296`:

```text
(3454 * 2296) / (3516 * 2344) = 0.9622496
```

**DERIVED:** retention would be `96.22496%` of the original plane, comfortably
above the registered 80% gate at `cover-default.md:413`. Even a 128 px inset
would satisfy that gate for this geometry; the proposed mechanism predicts
much less.

The prediction assumes that the remaining finite support, TIFF comparison and
specificity noise behave like the Scale/b2 control. It is a target for the
implementation lane, not a result of this diagnosis lane.

## Reproduction

The environment was sanitized by removing every inherited `STREHL_*` variable.
The b4 render then set:

```text
STREHL_WARPMAP=<absolute path to 109-warpmap.txt>
STREHL_FULLRES_GATHER=1
STREHL_DEFECT=off
STREHL_FIX_CA=off
STREHL_PYRAMID_WORKERS=2
RAYON_NUM_THREADS=6
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
```

All other `STREHL_*` variables were unset. The command was:

```powershell
& 'D:\strehl-out\cover-default\target\release\strehl.exe' `
  stack 'D:\personal\macro\109MSDCF' `
  --merge pyramid `
  --pyramid-bands 4 `
  --resampler catmull-rom `
  --cover crop `
  --out 'D:\strehl-out\M-COVER-BORDER\q3-109-crop-b4.tiff'
```

All omitted CLI options retained executable defaults. The complete stderr/stdout
record is `results/render-b4.log`.

After the final score, b2 and b7 were independently rerendered under the same
two-worker/six-thread environment:

```text
b2: 10F7DEAF5A82CA2A311C76A323AE5627207520E7DA3BB71D237BB861CC7CC977
b7: 0465D253F14431CE76BA1DD68E54C1BD2CBAE56DA17F079D5DD572852FCAD304
```

They **do not** equal the preregistered existing b2/b7 inputs
(`02C147...` and `B2489C...`). They were not used by
`profile-final.json`; that file used the old inputs. Their logs are
`results/render-b2.log` and `results/render-b7.log`. That discovery withdrew
the mixed-history b4 ladder before it was replaced.

The authoritative matched 109 rerun uses:

| arm | SHA-256 |
| --- | --- |
| Scale b2 | `A23EA4CE25DC9616971E0841D19DCE58642F4827898BADFAB5E965D20EB92185` |
| Scale b7 | `84901F122C256961199EB153674309C328AE7ABF9C33D371A4BBBEE26CD4F594` |
| Crop b2 | `10F7DEAF5A82CA2A311C76A323AE5627207520E7DA3BB71D237BB861CC7CC977` |
| Crop b4 | `4B98B8D31F8FBB9F37B484B928508A74894C0259FF30AFA7E69C97A3CF39BC10` |
| Crop b7 | `0465D253F14431CE76BA1DD68E54C1BD2CBAE56DA17F079D5DD572852FCAD304` |

The Crop b2/b7 hashes reproduced the earlier two-worker files exactly.

The same binary and environment produced the independent 113 arms:

| arm | SHA-256 |
| --- | --- |
| Scale b2 | `EA61568B0BF00C521D97303D3D1415AD87168880CF5247427681DBE39D2FBA29` |
| Scale b7 | `D5D7693DE2BA02ABDACD1527CFF64131EEB7025E1A2F81779CB96B6671ED303E` |
| Crop b2 | `983E687A02F2E26B4D00DC22492F1A90A3E1A0FE95A31FB1923B9A4F8AB03A7C` |
| Crop b7 | `8959EEF23E1E87BC3E475E2C845FCF0295CE4F36C8D16BC4106727CD5649A3F5` |

Its private-cache map hash is
`A5DF650CCE1224A7B6F54B5570B0BC1E643F1728B030D2496BD2BC13E462623E`.
All eight new b2/b7 render logs are retained under
`results/common-<109|113>-<scale|crop>-b<2|7>.log`. Every render placed all
frames and exited zero. The source capture tree remained read-only.

Instrument commands:

```powershell
python experiments\M-COVER-BORDER\instrument.py commission `
  --out experiments\M-COVER-BORDER\results\commission-final.json

python experiments\M-COVER-BORDER\instrument.py source-audit `
  --commit 4e5278870a5e6ff6e0da38762f716e5291508c16 `
  --out experiments\M-COVER-BORDER\results\source-audit.json

python experiments\M-COVER-BORDER\instrument.py coverage `
  experiments\M-PHASE0-SPLIT\out\real-109\109-warpmap.txt `
  --out experiments\M-COVER-BORDER\results\coverage.json

python experiments\M-COVER-BORDER\instrument.py profile `
  --crop-b2 D:\strehl-out\cover-default\q3-109-crop-b2.tiff `
  --crop-b4 D:\strehl-out\M-COVER-BORDER\q3-109-crop-b4.tiff `
  --crop-b7 D:\strehl-out\cover-default\q3-109-crop-b7.tiff `
  --scale-b2 D:\strehl-out\cover-default\q3-109-scale-b2.tiff `
  --scale-b7 D:\strehl-out\cover-default\q3-109-scale-b7.tiff `
  --out experiments\M-COVER-BORDER\results\profile-final.json
```

The instrument verifies all five TIFF hashes before profiling. Python used
`PYTHONIOENCODING=utf-8`. No Rust source was edited.

The common-linear follow-up commands are frozen in
`CONTRADICTION-PREREGISTRATION.md`. Its scored commands were:

```powershell
python experiments\M-COVER-BORDER\contradiction.py commission `
  --out experiments\M-COVER-BORDER\results\contradiction-commission.json

python experiments\M-COVER-BORDER\contradiction.py profile `
  --source-label <109MSDCF|113MSDCF> `
  --binary D:\strehl-out\cover-default\target\release\strehl.exe `
  --expected-binary-sha 1AC423529D5AAD88B7141801E47DCD612FCA8061558578A88592DB715CE81A0F `
  --source D:\personal\macro\<source> `
  --map <frozen-map> --expected-map-sha <map-sha> `
  --scale-b2 <scale-b2.tiff> --scale-b7 <scale-b7.tiff> `
  --crop-b2 <crop-b2.tiff> --crop-b7 <crop-b7.tiff> `
  --commission experiments\M-COVER-BORDER\results\contradiction-commission.json `
  --out experiments\M-COVER-BORDER\results\common-linear-<109|113>.json
```

The 109 invocation additionally supplied the matched `--crop-b4` arm.

## What this lane could not determine

1. **UNKNOWN:** the proposed fix was not implemented, so its actual residual
   and safe inset are unmeasured.
2. **UNKNOWN:** this experiment cannot supply a finite safe inset valid for all
   scenes. 109 is specific and 113 is not; no third source was opened.
3. **UNKNOWN:** early domain restriction and continuous boundary extension
   were not compared experimentally.
4. **UNKNOWN:** the amplitude contribution of individual production choices
   inside `BandMerge`—energy smoothing, gate/floor, variance calibration,
   base-level selection and channel coupling—was not isolated. The depth
   intervention identifies the pyramid as the transport and late black fill as
   its source, not the percentage attributable to each weighting term.
5. **UNKNOWN:** the post-fix output's external-decoder byte equality was not
   tested. Preserving it requires retaining Crop's original sample addressing
   and avoiding any resampling of emitted sites.
6. **UNKNOWN:** 113 may contain some genuine Scale boundary-local band-depth
   component in addition to scene structure. The artificial-boundary control
   proves that its 640 px nominal tail is nonspecific, but it does not decompose
   every physical-edge pixel into causal components.
7. The independently written V-HEADTOHEAD3 harness and this lane agree on the
   113 corrected-linear rows to `9.06e-8`, but that corpus contains neither the
   causal band ladder nor the conserved-error test. It is an independent
   replication of the nominal nonspecific profile, not of the full mechanism
   diagnosis.

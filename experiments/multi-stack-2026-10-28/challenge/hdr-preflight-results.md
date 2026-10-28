# Nine-source HDR preflight results

MEASURED / VERIFIED on 2026-10-28. Root released exactly nine frozen sources,
then a narrow second decode of those same files for four excluded columns.
No additional source frame, full render, private noise fit or production edit
was used. The sample manifest and baseline-only patch freeze preceded exposure
residual inspection. All capture files remained read-only.

## Independent decoding and clipping

All nine whole-file hashes matched the frozen manifest. rawpy0.27.0 /
LibRaw0.22.1 decoded uint16 original CFA; each visible copy was made inside the
RAW context, checked after context closure, saved and read back exactly.
All296,525,376 shared samples in absolute [0,7028)x[0,4688) matched the production
cache exactly. Both paths report black512 and white15360.

Production includes width7032, while LibRaw visible width is7028. The separately
authorized strip check compared all168,768 samples in [7028,7032)x[0,4688) exactly
against rawpy.raw_image. These are heterogeneous original decoded sensor codes,
not zero/constant padding. Whether they are optically active is not established
by the decoder agreement. All reported statistics use the shared7028-wide domain.

The first/middle/last1s and2.5s samples had zero original sites at or above white.
The6s samples show real clipping in both greens and blue, with no clipped red.

| 6s index | G1 clipped | G2 clipped | B clipped | All clipped sites | Registered1s usable support |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 377903 | 375236 | 101693 | 854832 | 854832 (100.0000%) |
| 32 | 540944 | 538071 | 128195 | 1207210 | 1206636 (99.9525%) |
| 64 | 412816 | 409460 | 92271 | 914547 | 905106 (98.9677%) |

Usable support here means the existing direct global geometry places the
original clipped site inside the independently decoded1s-middle image with all
nonzero bilinear taps unclipped and signal>=64DN above black. The minimum observed
support signal was326DN. This is a fixed engineering floor, not a noise fit or
a same-focus certificate. Uncovered border sites were counted, not filled.
Coverage opportunity does not establish recovered detail or HDR quality.

## Frozen spatial photometry

Twelve128x128sensor-pixel interiors were chosen visually using ONLY the1s-middle
locator: six at x<2200 for scalar fitting, six elsewhere for validation. The
patch JSON hash is06d6d16cfeee5cf1a87da073923a94dee0e4fdd1e3e983eee8eee195ac212471.
Each CFA site uses an independent float64 bilinear gather, actual original-tap
clipping eligibility, and10%-trimmed means. Ratios are black-subtracted, divided
by nominal exposure1/2.5/6s, then compared to1s middle. A single scalar is the
median of eligible calibration site/patch ratios. Validation values never fit
that scalar. Original-clipped patches and reference means<64DN are excluded.

Geometry is reused from the186-frame direct global solve. The validation patches
are held out from gain fitting, NOT proven absent from geometry fitting. This is
registered radiometry evidence, not an independent placement audit. No optical
color correction is applied in this broad-interior estimator.

| Pass/index | Fitted normalized ratio | Held-out median abs residual | Held-out95th percentile | Fixed screen |
| --- | ---: | ---: | ---: | --- |
| b10/0 | 0.990750 | 0.2477% | 15.3240% | fail |
| b10/30 | 1.000000 | 0.0000% | 0.0000% | pass |
| b10/59 | 1.013921 | 0.1988% | 15.3748% | fail |
| b11/0 | 0.997277 | 0.3197% | 15.9122% | fail |
| b11/30 | 1.006741 | 0.0660% | 0.2674% | pass |
| b11/60 | 1.019999 | 0.2293% | 15.3683% | fail |
| b12/0 | 1.061057 | 0.4802% | 15.5514% | fail |
| b12/32 | 1.065204 | 0.0902% | 0.8988% | pass |
| b12/64 | 1.076850 | 0.3655% | 15.9468% | fail |

The screen requires at least four distinct calibration and validation patches,
median<=1% and95th percentile<=3%. Both stricter0.5/2% and looser2/5% sensitivity
bars give the same pass/fail decisions. The1s-middle row is an exact no-op control.

The middle2.5s and6s samples support scalar photometry on these broad interiors.
The6s-middle normalized ratio1.06520 means nominal6:1 shutter scaling undercorrects
brightness by about6.5%; the corresponding additional exposure correction is
-0.09113EV. This is capture-specific, not a sensor/profile constant. Exposure,
acquisition time, lighting and focus are confounded; the measurement cannot assign
the6.5% offset to one physical cause.

All first/last rows fail because p12, a dark chart interior near bright pattern
content, is14-17% brighter relative to the middle-focus reference. The same effect
occurs within the1s pass. Perturbing placement by+/-2sensor pixels changes that
patch by<0.9%, so small translation error does not explain the full difference.
Focus/flare or another scene-dependent effect is plausible; it is not proven.
The adverse patch stays in the frozen score. Calling a patch visually flat
does not establish focus-invariant radiometry.

POST HOC, explicitly not a revised acceptance arm: comparing corresponding
first/middle/last strata to the same1s stratum gives2.5s normalized ratios
1.00659/1.00674/1.00599 and6s1.07096/1.06520/1.06206. Their held-out95th percentiles
are0.13-0.41% and0.52-1.32%. Thus a constant pass correction is promising, with
about0.84% full variation for6s. These ranks are not exact same-focus matches;
relative geometry scales differ by as much as0.104%. Full matched-focus evidence
is required before automatic calibration can use that apparent stability.

## Product recommendation

Use one explicit per-pass radiometric scalar relative to the chosen anchor.
Estimate it only from multiple independently acquired compatible overlap pairs
spanning focus ranks, with clipped originals excluded in every color and spatial
fit/validation sets fixed before residuals. Keep the original injected noise model;
multiply its propagated absolute variance by total gain squared. Never fit a
separate noise curve from the chart or evaluate the unscaled model at gained DN.

A conservative proposed runtime screen is >=3 useful compatible pairs spanning
focus, +/-0.25EV correction bound, held-out median1%/p953%, and<=2% cross-pair gain
variation. These are engineering hypotheses for explicit adversarial tests, not
physical constants derived from these nine images. Pair selection must validate
local focus/photometric compatibility; geometry scale alone is insufficient.
The primary6s case must use only its uncensored original supports. A failed screen
should provide measured reasons and offer aligned layers rather than silently
falling back to nominal HDR. An explicit user gain override can be added later
as a persisted calibrated-input assumption. No hardcoded6s correction.

A uniform gain error is mathematically absorbed by scalar calibration. The
commissioning10%wrong-nominal control deliberately demonstrates that fact; the
nominal-ratio check detects the error before refitting. For the runtime calibrator
whose purpose is to correct unknown scalar gain, a within-bound planted scalar
should be recovered, while an excessive correction or spatial/color/focus drift
must fail. Do not claim that a scalar fit validates its own illumination model.

## Controls, commands and resource receipts

Synthetic controls ran first: per-color black/white/clipping, below-black values,
active-coordinate/CFA phase foils, copied identity rejection; then sampler exact
identity/nonzero-tap clipping, no-change photometry, wrong nominal gain, spatial
half-field drift and channel drift. All passed. One initial photometry attempt
failed solely because NumPy bool was not JSON serializable; no result was saved.
The source and failed receipt are retained, the serializer and its control were
fixed, and controls+measurement reran successfully without new RAW decoding.

Commands actually run from C:/Users/chris/.codex/worktrees/multi-stack/strehl:

    python -X faulthandler -I experiments/multi-stack-2026-10-28/challenge/hdr-preflight.py controls
    python -X faulthandler -I experiments/multi-stack-2026-10-28/challenge/hdr-preflight.py decode
    python -X faulthandler -I experiments/multi-stack-2026-10-28/challenge/hdr-preflight.py compare-cache --cache outputs/multi-stack/hdr-source-cache
    python -X faulthandler -I experiments/multi-stack-2026-10-28/challenge/hdr-preflight.py compare-strips
    python -X faulthandler -I experiments/multi-stack-2026-10-28/challenge/hdr-photometry.py controls
    python -X faulthandler -I experiments/multi-stack-2026-10-28/challenge/hdr-photometry.py measure
    python -X faulthandler -I experiments/multi-stack-2026-10-28/challenge/hdr-opportunity.py

All final commands exit0. Python3.12.10, NumPy2.4.4, one compute worker with
OMP/OpenBLAS/MKL/NumExpr limited to1. StageA8.34s, sampled peakRSS180.5MB/private
168.4MB; cross-decoder1.86s, strip addendum3.59s, photometry0.53s. These are
measurement-run receipts under concurrent host work, not engine performance
benchmarks. Receipts bind exact source/manifest/geometry hashes and commands.
Original-copy storage593,050,752bytes; no aligned float volume was produced.

All evidence files are under outputs/multi-stack/hdr-preflight. Complete masters
and independently reviewed fixed-display native crops remain required for any
future HDR photographic-gain claim; this preflight establishes no such claim.

# M-PHASE0-SPLIT2 — scorecard-licensed registration fails the second-light gate

**Final verdict: NOT ROBUST / NO BUILD.** The directory really does contain
two sets of 32 repeated exposures per ISO at fixed reported focus. The original
protocol stopped on 1–2 quad-pixel motion. After that result, the orchestrator
supplied the independently preregistered SOTA scorecard, which names this
capture and licenses analytical Fourier translation. Amendment 1 therefore
tested the two scorecard-registered ISO-100 runs without inspecting an FRC
outcome. The bright run passes the scorecard's 0.10-native-pixel
non-translation RMS gate at 0.064031; the second-light run fails at
**0.107703**. An independent spatial estimator reproduces the decisions at
0.070005 and **0.105202**. No real FRC or `P_sig/P_noise` result was retained,
no frequency above the 0.25 cycles/native-pixel licence was inspected, and no
Rust is warranted.

Preregistration and metadata-validator commissioning precede pixel measurement
in commit `f24b08da`. All capture paths were read only.

## What the capture actually is

`out/capture-manifest.json`, produced by `validate_capture.py`, establishes:

* 576 contiguous ARWs, `DSC00296.ARW`–`DSC00871.ARW`;
* two time-ordered passes, each containing all nine ISOs
  `{50,64,80,100,200,320,400,500,640}`, with exactly 32 consecutive exposures
  in every ISO run;
* f/5.6, 1.6 s, 200 mm, 14 bit, Sony ILCE-7CM2, manual focus throughout;
* `FocusDistance2 = 0.273841307296975 m` in all 576 files;
* each run lasts 68.871–70.013 s and its maximum inter-frame gap is 2.400 s;
* pass 2 is 0.940063–1.108521 EV darker than pass 1, while the largest
  within-run EXIF brightness range is 0.367188 EV;
* `ImageStabilization = On` in all reported metadata.

Thus the directory name is substantially truthful: these are no-bracket
repeats at fixed reported focus under two light levels. They require
registration before Fourier correlation, and the two light blocks do not both
pass the same registered translation-only geometry gate.

## The load-bearing fixed-scene gate

The preregistered gate uses pass 1, ISO 50,
`DSC00552.ARW`–`DSC00583.ARW`. `measure.py --gate-only` extracts the centred
512-square quad-green crop with no registration or resampling. Relative to
frame 0, FFT phase correlation reads:

| alignment shift (quad pixels) | frames |
| ---: | ---: |
| `(0,0)` | 1 |
| `(1,0)` | 21 |
| `(2,0)` | 10 |

The maximum displacement is 2 quad pixels, or 4 Bayer sensor-pixel pitches.
This violates the fixed zero-shift predicate. Focus itself does not show the
same failure: the maximum deviation of the log high/mid spectral-power proxy is
0.037008 against the 0.10 bar. The normalization-strip level CV is 0.018249 and
the crop has zero saturated samples.

This was challenged with a separately written spatial-domain verifier that
does not import `frc.py` and does not use an FFT. Direct normalized correlation
over all shifts in `[-3,3]^2` agrees with the FFT result on all 32 frames,
with non-identity best correlations 0.997857–0.999778. Its planted
zero-shift-only search goes RED. `ImageStabilization = On` is consistent with
sensor motion, but metadata plus correlation do not prove the physical cause.

## Scorecard-licensed amendment and corrected geometry statistic

The scorecard was committed independently before this lane reported and says
translation may be removed analytically as a Fourier phase ramp. It also names
`DSC00328.ARW`–`DSC00359.ARW` and `DSC00584.ARW`–`DSC00615.ARW` as the two
ISO-100 bee repeats. `AMENDMENT-1.md` freezes those inputs, excludes the pixels
used for alignment from FRC, and allows only a unit-modulus phase ramp.

The first amended gate used maximum quadrant range as a conservative proxy and
went RED at 0.07/0.10 quad pixel. Audit found that the scorecard's literal is
vector **RMS in native pixels**, not maximum component range.
`GATE-CORRECTION.md` records this error and its flattering-direction correction
before re-running the checker. The correct result is:

| light pass | Fourier estimator RMS (native px) | independent ECC RMS | 0.10 bar |
| --- | ---: | ---: | --- |
| bright ISO 100 | 0.064031 | 0.070005 | PASS |
| second-light ISO 100 | **0.107703** | **0.105202** | **FAIL** |

The second method uses OpenCV ECC in the spatial domain; it does not import the
Fourier estimator. Both assign the same per-light decisions. This rules out a
phase-ramp sign error and makes the 7.7% overrun decision-relevant rather than a
single-estimator accident.

## Commissioning retained, real FRC forbidden

Although the geometry gate stops the measurement, the offline instrument was
completed and commissioned before FRC was read. `out/commission.json` records
eleven named plants, all RED:

| control | clean reading |
| --- | ---: |
| independent-noise mean `|FRC|` | 0.029622 |
| independent-noise maximum ring `|t|` | 1.725586 |
| null band FRCs | -0.003631, +0.011965, -0.014001 |
| same-signal positive, low/high FRC | 0.991000 / 0.004115 |
| full identity maximum error from 1 | 4.44e−16 |
| common-mode adversary, low-band FRC | 0.973986 |
| identical sharpening crossing move | -0.000754 cycles/quad-pixel |
| naive acuity gain from that sharpening | 1.832679x |

The common-mode synthetic reproduces the closed split-half failure
(0.973986 here versus 0.972099 there), rather than silently losing sensitivity.

The missing data-dependent control is no longer algebraic window dressing. A
nonlinear shrinkage parameter is selected on training repeats and evaluated on
held-out repeats. Plant T1 illegally tunes shared-data leakage on the evaluation
pair. It chooses full leakage, drives high-band FRC to its exact ceiling 1.0,
and makes the nominal C output move by 25.002575 when only D receives a fixed
external checkerboard. The external lineage predicate requires no C movement,
so T1 goes RED. This directly demonstrates why self-tuning must be held out.

The analytical translator recovers an externally evaluated
`(1.25,-0.40)`-quad-pixel displacement within 0.02 pixel, leaves Fourier
magnitude unchanged to 1.67e-16 relative, and aligns it to 0.002651 relative
RMS. Wrong-sign A1 goes RED. Local-warp A2 plants a known 0.12-native-pixel RMS
and the checker reads 0.123288; the independent ECC checker reads 0.108305 and
its own zero-residual plant also goes RED.

Across the metadata, FRC/stability/alignment, and two independent-verifier
instruments, 17/17 planted defects go RED.

## Illumination and the stopped claim

The approximately 1 EV second-pass change could depress a genuine cross-light
FRC. The protocol therefore never pairs the light levels: each 32-frame block
must pass independently, with drift-cancelling ABBA contrasts and a disjoint
photometric-normalization sensitivity arm. None was run after the second
geometry gate failed. Illumination cannot flatter this STOP: both geometry
estimators remove mean and scale, and only local translation residual decides.

There is deliberately no `out/measurement.json` and no
`out/aligned-measurement.json`. Therefore the requested real repeat null versus
the 0.25 SNR bar, and its comparison with historical 0.438734, are **not measured**.
Quoting a value would violate both conditional protocols. Likewise,
the 0.972099 comparison above is a commissioned synthetic adversary, not a
result from these ARWs.

## Consequence for source

**Nothing changes in Rust.** A repeat-only product already would not apply to a
normal single focus stack; the scorecard-registered second-light sentinel also
fails the commissioned translation-only gate. Building dual accumulators or an
FRC product now would productise an unidentified
registration/fixed-pattern/illumination mixture.

Reopening requires a new capture with stabilization off or both independent
light blocks passing the scorecard geometry gate.
Even then, repeated exposures share stable sensor structure; an ABBA difference
null cancels that structure and cannot prove it does not inflate scene-pair
FRC. For the SOTA scorecard this means FRC remains unavailable from this
sentinel; this lane cannot supply a licensed M1 detail result, so the headline
detail claim remains unmeasured unless an independent admitted instrument
succeeds elsewhere.

## Traceability

* `PREREGISTRATION.md` — fixed gate, bars, bias, and stop rule.
* `validate_capture.py`, `out/capture-manifest.json` — metadata structure.
* `frc.py`, `commission.py`, `out/commission.json` — offline controls/plants.
* `measure.py`, `out/pixel-gate.json` — preregistered pixel gate.
* `verify_pixel_gate.py`, `out/pixel-gate-verification.json` — independent
  direct-correlation verification and its RED plant.
* `AMENDMENT-1.md`, `GATE-CORRECTION.md` — externally licensed phase-ramp
  protocol and post-RED correction to the scorecard's literal RMS statistic.
* `align.py`, `measure_aligned.py`, `out/alignment-gate.json` — analytical
  translation control and the two ISO-100 geometry gates.
* `verify_alignment_gate.py`, `out/alignment-gate-verification.json` —
  independent spatial subpixel verification and its RED plant.

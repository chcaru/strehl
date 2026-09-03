# M-PHASE0-SPLIT2 — repeated exposures are not a stationary FRC pair

**Verdict: CAPTURE GATE FAIL / NO BUILD.** The directory really does contain
two sets of 32 repeated exposures per ISO at fixed reported focus, but the
images are not stationary in sensor coordinates. The preregistered first-pass
ISO-50 gate measured a monotone 1–2 quad-pixel displacement while in-camera
image stabilization was on. Per the committed protocol, no real FRC or
`P_sig/P_noise` result was retained and no Rust is warranted.

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
repeats at fixed reported focus under two light levels. It is not, however, a
set of co-registered observations of one latent, which is the property the
proposed Fourier correlation needs.

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

## Commissioning retained, real FRC forbidden

Although the capture gate stops the measurement, the offline instrument was
completed and commissioned before the gate was read. `out/commission.json`
records nine named plants, all RED:

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

Across the metadata, FRC/stability, and independent-verifier instruments,
14/14 planted defects go RED.

## Illumination and the stopped claim

The approximately 1 EV second-pass change could depress a genuine cross-light
FRC. The protocol therefore restricted the primary null to each 32-frame
fixed-light run, used drift-cancelling disjoint ABBA contrasts, and reserved
cross-light scalar normalization as sensitivity analysis. None was run after
the geometric gate failed. Consequently illumination cannot flatter this STOP:
the deciding statistic is displacement, and the independent verifier removes
mean and scale before correlation.

There is deliberately no `out/measurement.json`. Therefore the requested real
repeat null versus the 0.25 SNR bar, and its comparison with historical
0.438734, are **not measured**. Quoting a value would violate the conditional
protocol. Likewise, the 0.972099 comparison above is a commissioned synthetic
adversary, not a result from these ARWs.

## Consequence for source

**Nothing changes in Rust.** A repeat-only product already would not apply to a
normal single focus stack; this candidate dataset additionally needs an
uncommissioned registration model before its halves share a latent. Building
dual accumulators or an FRC product now would productise an unidentified
registration/fixed-pattern mixture.

Reopening requires a new capture with stabilization off and a zero-shift gate,
or a separately preregistered, commissioned lossless registration experiment.
Even then, repeated exposures share stable sensor structure; an ABBA difference
null cancels that structure and cannot prove it does not inflate scene-pair
FRC.

## Traceability

* `PREREGISTRATION.md` — fixed gate, bars, bias, and stop rule.
* `validate_capture.py`, `out/capture-manifest.json` — metadata structure.
* `frc.py`, `commission.py`, `out/commission.json` — offline controls/plants.
* `measure.py`, `out/pixel-gate.json` — preregistered pixel gate.
* `verify_pixel_gate.py`, `out/pixel-gate-verification.json` — independent
  direct-correlation verification and its RED plant.

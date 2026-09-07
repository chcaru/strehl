# M194f amendment 1 — supported white-balance potency control

2026-09-07, root. Prospective correction after the retained first intended
population failed. This amendment must be committed with the independent
design reviews before implementation. It changes no optical input, merge
default, production exposure policy, private coordinate bar or noise model.

## Observed failure and rejected repair

The first four genuine RGB outputs and the confidence auxiliary were written
at `production-population-1`. The fifth, exposure-plus-one-count, refused at
`Exposure::resolve(false, 1, false)`: exposure is a viewing control and is
deliberately unavailable to CameraLinear measurement output. Its exact failed
command and error are in `exposure-plus-one-count/receipt.command.json` and
`.log`. The scheduler returned exit1 without a completed index. Preserve every
partial output; this is an incomplete population, not a bridge pass.

The earlier protocol called this exposure control supported without executing
the relevant production guard. That design choice was wrong. Do not weaken the
guard or switch this experiment to display-referred output. Add a regression
that the original exposure request still refuses, and reject it during plan
validation before any pixel work.

Independent source reviews also rejected root's first replacement bar. WB is
applied to the CFA samples before MHC; cross-channel curvature terms mean
red-only WB changes can move interpolated green and blue. All-pixel red
doubling and all-pixel green/blue identity are therefore invalid. Uniformly
doubling all three WB gains would depart from the normalized green=1
convention and reintroduce a measurement rescale; that alternative is not
adopted either. No output observation was used to fit a replacement tolerance.

## Adopted replacement

Retain eleven intended TIFFs. Replace only exposure-plus-one-count with
**red-wb-double-count**. All five genuine runs use exposure0. Baseline-off,
baseline-count, baseline-placebo and confidence-count retain prepared WB
`[float32(4/3),1,float32(5/3)]`. The replacement uses
`[float32(8/3),1,float32(5/3)]`. All original M194e CFA bytes, source-frame WB
metadata, gather/probe inputs, injected noise, merge settings and output domain
remain the same. Only the WB supplied to the final prepared writer changes.
This is an intentionally changed conversion coefficient for a software
potency control; it is not another calibrated camera measurement or quality arm.

Use explicit `STREHL_M194F_WB_MODE=baseline|red-double`, record `wb_mode` and
the actual represented `wb_f32` in each plan, and bind them through the existing
external plan hash and recomputation. Unsupported modes and stale settings
must refuse. Keep the ordinary three private RGB and two private Gray controls
at baseline WB. Their existing .25DN and63.5DN bars remain unchanged.

## Delivered-value bar and failure direction

Derive the native CFA parity from each actual output coordinate and its
recorded canonical native crop offset. On the complete common output grid:

- At every measured red sensel (native x even, y even), require positive,
  unclipped baseline and replacement R codes and
  `abs(replacement_R - 2*baseline_R) <= 1` in u16 code units. Every such site
  must also increase. Both output images must contain red sensels, and the
  maximum baseline measured red code must exceed1 as an amplitude witness.
- At every measured green sensel (native x/y parity different), require its
  G code to be exactly equal between the two outputs. Both green parities
  must occur.
- At every measured blue sensel (native x odd, y odd), require its B code to
  be exactly equal. Blue sensels must occur.

MHC copies the observed component at each of these sites, including its edge
fallback. Doubling the represented red WB is an exact binary scale before
writer quantization. For unclipped round-half-up output, independently rounded
x and2x can differ from the code-level doubling by at most one code. The bar
must refuse clipping rather than treating clipping as successful scaling.
No additive black subtraction is introduced. Record the unchanged source-frame
WB separately as `frame_wb_f32`; the selected `wb_f32` is the prepared writer WB.

Report complete per-channel changed counts and maximum absolute code movements
over the interpolated components separately. They carry no identity or
doubling bar. This control can detect an ignored/wrong WB input, wrong CFA parity,
channel leakage into a measured component, extra scaling or clipping. It does
not establish optical fidelity, MHC accuracy at interpolated sites or better
merge quality. The unchanged private affine oracle retains its own scope.

Before using the replacement reader, independently commission a valid parity
fixture plus null WB, wrong channel/parity, changed measured green/blue,
out-of-tolerance red, clipping, empty-parity and wrong-CFA-phase offset controls. Include
a non-affine MHC source witness explaining why interpolated components cannot
inherit the measured-component rule; do not substitute a constant image whose
cross-channel corrections vanish for that witness.

Use the separately derived direct MHC witness from the independent acceptance
review: a10x8 RGGB mosaic with all channels1000DN, red(4,4) increased by64DN
and green(5,4) by80DN. Double red samples only. At red(4,4), interpolated G
must change1052 to1084 and B1048 to1096. At green(5,4), interpolated R must
change1082 to2114; a post-MHC red multiplication would incorrectly give2164.
The constant mosaic companion has no interpolated G/B movement. These exactly
representable component values test the actual MHC function before quantization;
they do not supply an optical reference or another intended TIFF. Neither the
sampled-site bar nor the affine fixture alone proves WB ordering.

## Complete rerun and provenance

Register this amendment and its independent design reviews in the final run
index alongside the original preregistration. Freeze new adapter, launcher,
scheduler and reader bytes; visibly rebuild and refresh affected input/plan,
driver/scheduler and delivered-reader controls. Run the complete eleven-file
population afresh under one build. Do not splice the four earlier successful
arms or earlier private images into it. The final independent reader must
consume all eleven actual files and the new explicit settings. The original
exposure refusal, failed first population and rejected all-pixel interpretation
remain in the report.

# M194c independent probe and layout controls

Frozen before independent execution on 2026-09-07. This document follows
inspection of the candidate destination helper (a context-restoration read of
gatefloor.rs also included it); it is **not** represented as a blind pre-edit
registration. The independent choices and semantic corrections were sent before
implementation. The author's test source has not been read or copied.

Prior art is the parent preregistration's recorded search, M194b's actual
padding failure/white-floor intervention, the original frozen fill function,
PlaneGeometry::from_active, both gather implementations, Probe::measure and
BandMerge::add_frame_with_gain. No external source, capture, or new quality
criterion is used.

## Choices and falsifiers

* Rechoose sampler extents 70x46 and 118x82, indices 0/17/43. Compare packed
  storage with origin(5,7), stride W+18, height H+18, and origin(2,9), stride
  W+31, height H+25. The latter also has an odd trailing active row/column.
  Outside values have a deterministic high poison pattern. Every consumed
  photosite must match exactly; every outside address must retain its old value.
  The frozen legacy function must match every packed value and must disagree
  for relocated storage. Seeds must change the consumed sequence.
* Rechoose actual Probe active extent274x190 (quad137x95), whole and offset
  Crop(9,6,112,78), bands3/6. Five transforms have scales
  [1.041,1.023,1,.992,.969], true rotation angles
  [.009,-.007,0,.004,-.003], plane translations
  [(.17,-.21),(.23,.17),(0,0),(.41,-.19),(-.13,.11)], and off-axis
  native centre(163,71). Frame2 is the identity gauge. These are an explicitly
  nonlinear software stimulus, not optical/alignment truth or measured M103
  camera parameters. Every layout must produce bit-identical finite beta for
  every transform/domain/band depth. Seeds17/43 and a nonidentity warp must
  change beta. Template sample changes must leave beta unchanged because the
  probe replaces the samples. Noninteger fullres WB[1.15,1,1.65] versus
  [1.9,1,.7] must be live; WB must be inert in the per-CFA-plane gather.
* Run both gather modes in isolated processes, measured floor, CA off, all
  ambient STREHL settings removed. A small valid native28x18 frame must give
  empty beta. A normal measured band is finite. The direct pooling helper on
  16x24 must return None; 32x30 must return a finite value; injecting NaN into
  the retained interior must propagate NaN. These are labelled direct fault
  injection. Valid finite Probe input cannot ordinarily produce the advertised
  small-band NaN: two remaining descendants >=8 imply measured extent>=29 and
  at least23x23=529 samples, above256. Do not pretend an impossible plant exists.
* Through real BandMerge, None, an empty beta slice, and a NaN slice must give
  identical fallback output. A finite destructive floor must change it, proving
  the fallback comparison is live. A changed injected variance must change the
  result. This does not calibrate a camera noise model.
* Through the shared production prepared-frame seam, render five deterministic
  nonphysical textured frames at the same274x190 geometry, full and cropped.
  Rechoose low/high-frequency sinusoidal texture, distinct CFA offsets and
  deterministic small integer noise. Packed, relocated, odd-tail and poisoned
  layouts must give identical TIFF bytes; genuine active-data, injected noise
  model, WB and warp changes must each change delivered bytes. A small active
  photosite perturbation is a separate power control. Main output with the
  existing stats observer on/off/placebo must be byte-identical.

The raw texture is512+3000+site offset[0,80,-70,160]+70 sin(2pi(x/31+y/19))
+amplitude[k] sin(2pi(x/7+y/11)+.19k)+15k+integer noise[-6,6], amplitudes
[18,60,135,50,25]. Fixed model baseline gain.25 DN/e, RN4e; destructive model
gain2 DN/e, RN10e; these are injected and not learned from the plant. Single
active green site at(136,95) in frame2 receives+500 DN. Broader active-data
control adds200 DN to every consumed site. Bands3, gate2, CameraLinear,
Catmull-Rom, no exposure/photometric/defect/CA correction.

If any planned power control is inert, retain that failure and narrow the
claimed test power; no post hoc threshold tuning to obtain green. Source/API
or compile corrections retain failed logs and are labelled before rerun. Parent
owns complete fixed M194b40-output comparison and quality conclusions. This
independent script owns no quality claim and no candidate promotion.

## Evidence boundary

Actual legacy M194b TIFF failure stays in its committed report/artifacts. The
local legacy function control is a direct sample-order counterexample, not a
second invocation of the old production binary. Exact bit/byte identity can be
fooled by a dead branch; seed, warp, source sample, noise and WB controls provide
the complementary power. Empty/NaN branch checks have only their stated software
scope. Tests are included privately under cfg(test); no new product API or
production option is introduced. All sources freeze before the candidate build
and remain fixed through the parent's scored run. Preserve compile lines, exact
child environment and all assertion/summary output; retain generated TIFFs.

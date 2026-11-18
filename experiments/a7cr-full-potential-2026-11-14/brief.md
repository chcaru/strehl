# A7CR full potential: brief (registered before any arm ran)

Owner request (2026-11-14): get the most out of the A7CR; anything about the
system may change, new techniques allowed. Input for the first round is the
existing capture 3 (coin cell, 107 planes, step 8, ISO 100, 2 s):
four-shot `stack-1794689780304-11226` and single-shot
`stack-1794689213508-11226`. Read-only; all outputs under ignored
`outputs/a7cr-full-potential/`.

## Why the old verdicts do not settle this

SYNTHESIS facts 141-143, 474, 1074-1076 and 1112 rule deconvolution out of the
*core merge* and price a matched filter at +0.91 dB. They were measured on the
A7C II (5.12 um, Nyquist 97.7 cycles/mm, below this rig's 106-135 cycles/mm
cutoff, fact 1153), single shot, on captures about 1.76 stops dark (fact
1253), at coarse focus steps. Capture 3 differs on every count: the A7CR
samples the whole optical band (Nyquist 133 cycles/mm), exposure fills the
well, four shots give four times the light with every colour measured, and the
focus step is about a tenth of the focus peak's width. Facts 1413-1414 (axial
and lateral chromatic aberration baked into every render) and fact 1075 (the
shipped gate takes 1.2-1.8 frames of light where about 4 were available) name
defects this round can attack directly. Fact 474 sets the re-opening bar for
restoration: flat high-pass noise at most 1.05x the shipped merge.

## Pipeline under test (prototype, Python on the GPU; not the product path)

1. **Measured-offset assembly.** Each four-shot group becomes full-resolution
   R, G, B with nothing interpolated; each member's measured sub-photosite
   offset is compensated (first-order, from the assembled plane's own
   gradient) instead of the group being demoted.
2. **Per-plane similarity alignment**, solved from near-span plane pairs.
3. **Lateral colour:** one radial scale per channel, fitted on this stack.
4. **Depth map and per-channel matched fusion.** A through-focus energy fit
   gives each location's focus plane; each band of each channel is combined
   over neighbouring planes with weights following that channel's own focus
   curve (axial colour offset included), normalised to the peak plane.
5. **Restoration.** One linear filter per channel taking the in-focus system
   OTF (diffraction at the cutoff measured on this stack, pixel aperture,
   resampling) to a ringing-free target, capped by noise.

## Arms

| Arm | What |
| --- | --- |
| S0 | Shipped `strehl stack`, full resolution, on the single-shot run and on the four-shot run as `member1` (two independent realisations) |
| C1 | S0 with arm P3's restoration filter applied (naive sharpening control) |
| P1 | Steps 1, 2 and 4 with one focus curve for all channels (no colour steps) |
| P2 | P1 plus lateral colour and per-channel focus |
| P3 | P2 plus restoration |

## Bars (pass/fail fixed here)

- **N1 noise.** Independent-realisation noise, high-pass (value minus 5x5 box
  mean), over in-focus tiles: P3 <= 1.05 x S0. S0's noise from the difference
  of its two realisations after registration; P arms from odd-plane versus
  even-plane halves (difference / 2). Fooled by: registration blur lowering
  S0's figure (conservative), signal-dependent weights correlating the halves.
- **R1 resolution.** Signal amplitude from the cross-spectrum of the same
  independent pairs (noise cancels), band 0.25-0.40 cycles/px: P1 >= 0.95 x
  S0 (fusion must not blur) and P3 >= 1.5 x S0. Fooled by: deterministic
  ringing or fixed pattern common to both halves, so crops and the edge
  overshoot check below are part of the bar.
- **N1 and R1 must hold together**; C1 is expected to pass R1 and fail N1.
- **L1 lateral colour.** Tile R-G and B-G displacement after correction:
  radial trend removed to <= 0.10 px rms residual about zero.
- **A1 axial colour.** Per-channel focus peak offsets against a G1-versus-G2
  null; P2's red and blue signal amplitude (cross-spectrum, 0.15-0.40
  cycles/px) >= P1's. Placebo: red and blue offsets swapped must not help.
- **M1 motion.** On groups the shipped checks demote, the assembled plane's
  2-photosite-period checker energy after compensation falls to within 1.2x
  of passing groups' level.
- **Eye.** Native 384-px crops, one display transform, origins recorded; no
  halos or ringing at 1:1 that S0 lacks.

A failed bar is reported as failed. Numbers are properties of this one
capture and subject.

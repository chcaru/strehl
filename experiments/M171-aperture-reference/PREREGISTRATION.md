# M171 aperture-reference preflight — preregistration

Status: **FROZEN BEFORE ANY M171 PIXEL DECODE OR CANDIDATE EXECUTION**

Written: **2026-09-04T11:47:53.629-07:00**

## 1. Question

Can the recorded aperture of an existing Sony A7C II + FE 100mm F2.8 Macro GM
OSS + 2X Teleconverter capture impose an external, output-independent ordering
of the *realized* scene-to-sensor transfer, so that the aperture ladder may
serve as truth for a detail instrument?

The distinction between ideal and realized transfer is binding.  The
diffraction-limited circular-pupil MTF is only an upper envelope for an
aberrated system.  A monotone ideal envelope is not by itself a monotone
ordering of the realized lens, teleconverter, focus state, target geometry and
sensor system.

## 2. Frozen preflight gate and stop rule

The aperture ladder is admissible as external truth only if all of the
following can be established without reading image outcomes:

1. EXIF confirms the camera, lens/teleconverter, focal length and the three
   recorded f-numbers rather than relying on directory names.
2. The interpretation of recorded f-number does not double-count the
   teleconverter.
3. The ideal diffraction MTF is computed from the circular-pupil formula, not
   from Airy diameter alone.
4. An independently justified bound on the *actual* optical transfer rules out
   an aberration/focus reversal between every adjacent aperture.

If item 4 is not established, the physical truth ordering is **NOT FORCED**.
M171 then stops before building or running a detail candidate, before invoking
the M167 adjudicator, and before decoding any RAW pixel.  An observed
slanted-edge ordering cannot repair this gate because that ordering would be
derived from the same image outcomes the aperture metadata was meant to label.

## 3. Capture-unit split

The holdout unit is subject plus uninterrupted capture session, not a directory
or step width.

### Development

The entire `requests\19-razor-edge` session of 2026-08-30 is development:

- `diagonal-tilt-all-axes\diagonal-tilt-all-axes-sw4-f5.6-cpl`
- `diagonal-tilt-all-axes\diagonal-tilt-all-axes-sw4-f8-cpl`
- `diagonal-tilt-all-axes\diagonal-tilt-all-axes-sw4-f11-cpl`
- `horizontal-flat\razor-edge-horizontal-flat-sw4-f5.6-cpl`
- `horizontal-flat\razor-edge-horizontal-flat-sw4-f8-cpl`
- `horizontal-flat\razor-edge-horizontal-flat-sw4-f11-cpl`

This unit was already burned before M171: tracked M128 artifacts name decoded
members of all three horizontal-flat aperture stacks.  The same-subject,
uninterrupted-session rule therefore makes every member development-only.

### Holdout

**None assigned and none spent by M171.**  The
`requests\7-aperture-pairs` fabric-weave session is not eligible for M171:
tracked M129 artifacts already enumerate decoded members across its aperture
stacks, despite the older M141 register still calling three rows clean.  The
single `misc-diagnostic\razor-flat-vertical-slightly-tilted-sw1-cpl` stack is
not an aperture ladder.  M171 will not consume a different clean unit after a
failed physical preflight.

## 4. Access ledger at freeze

- M171 ran ExifTool metadata-only reads over the 789 files in
  `requests\19-razor-edge`; no RAW pixel array was decoded and nothing was
  written under `D:\personal\macro`.
- During planning, an agent surfaced numerical values from already-tracked
  M128 outputs before this declaration.  That was an outcome read on the
  already-burned development unit, not a new holdout burn.  It will not be
  used to decide the physical gate.
- No M171 outcome has been rendered or measured.

## 5. Consequences for the requested controls and M167

Depth of field, exposure/noise, unequal frame count, diffraction-versus-defocus
controls, confidence intervals and M167 P1–P6 become executable requirements
only after the physical gate passes.  Under the stop rule, failure of the gate
means:

- no point estimate and therefore **NO CI**;
- no candidate and no M167 verdict;
- no aperture-ladder negative-control execution; and
- no bulk or subsampled RAW decode.

This is a negative preflight result, not an instrument result.

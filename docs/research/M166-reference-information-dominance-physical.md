TARGET HOLDS AT 1.32x

# M166 — physical protocol for `REFERENCE_INFORMATION_DOMINANCE`

> **SUPERSEDED IN PART.** M164's later complete-input witness contract in
> `M164-reference-dominance.md` makes this report's `96`-frame fixed-focus TC0
> witness inadmissible. `M166-reference-dominance-rehearsal.md` replaces that
> witness with complete candidate-excluded `sw4-A/B` and `sw10-A/B` inputs
> (`164` frames) and corrects the combined scored total from `1,147` to
> `1,215`. The `1.32x` target, hard `1.33x` maximum, and four reference strips
> remain in force.

Status: **COMPLETE — PHYSICAL DESIGN; CAPTURE REMAINS BLOCKED**

## 0. Result

**INFERRED.** M164's formal gate is physically testable on the Sony A7C II,
Sony FE 100 mm F2.8 Macro GM OSS, and communicating 2x Viltrox. It is not
proved to pass. The exact-configuration non-holdout rehearsal must establish
that the Viltrox reference really dominates the bare-lens scored state in
every licensed cell.

**INFERRED.** The minimum defensible holdout protocol from currently measured
optical bounds uses:

- `4 x 32 = 128` converter-on reference frames;
- `3 x 32 = 96` converter-off scored-path witness frames;
- the existing A/B calibration sources in each optical state; and
- one held-out `FLAT-V/DARK-V` pair in each optical state, `128` frames total.

**VERIFIED BY RUNNING.** Relative to the current `891`-frame request, those
changes produce a `1,147`-frame registered session, an increase of `256`.
The one existing throwaway histogram exposure makes `1,148` shutter releases.
The two-frame M147 preflight remains outside that session.

**INFERRED.** The witness must be in the same uninterrupted scored sitting.
A development witness is required to commission and power the gate, but it
cannot substitute for the scored-session witness.

**VERIFIED BY RUNNING.** This audit opened no file under
`D:\personal\macro` or `D:\edited\macro`, decoded no RAW, and performed no
wall-clock measurement.

## 1. Does the TC0 target move?

**INFERRED — ANSWER: NO.** Keep the TC0 target at `1.32x`, with the existing
hard maximum `1.33x`.

**VERIFIED BY RUNNING.** At the conservative reference lower bound:

```text
2.7015 / 1.32 = 2.0465909x
2.7015 / 1.33 = 2.0312030x
```

**INFERRED.** Moving TC0 lower merely to make reference dominance easier would
change the tested optical regime in the direction favored by the gate. There
is no physical evidence authorizing that change, and `1.32x` already clears
the geometric screen before uncertainty.

**VERIFIED BY RUNNING.** At `35.9 mm / 7008 px`, the eight-row M135 panel
occupies `7.947973 mm` at `1.32x`. Designing the artwork to survive the
registered `-0.25%` scale error and then applying the opposite `+0.25%`
fabrication extreme gives `7.987812 mm`, still below the `8.0 mm` panel
height by `12.188 um`.

**INFERRED.** The packing clearance is real but narrow. The panel must be
fabricated from the accepted `1.32x` mapping, and final eligibility must use
measured pixel spans for every interior and guard. Nominal artwork dimensions
alone are insufficient.

**INFERRED.** The two-frame M147 preflight is still aimed at the correct TC0
placement. It remains a geometry gate only and cannot release the long
capture without the dominance rehearsal.

## 2. Exact strip count

### 2.1 Geometry that must be frozen

**INFERRED.** Use the M135 `10 x 8` panel with its **eight-row direction as
the only depth-gradient direction**. Freeze target tilt at
`1.00 degrees +/- 0.02 degrees`; the ten columns must be iso-depth to the
fiducial residual allowed by the frozen geometry checker.

**INFERRED.** This does not reduce the requested roughly one-degree focus
challenge. It removes the current unspecified tilt-axis branch that produced
the earlier `3–7` range.

### 2.2 Reference strips

**VERIFIED BY RUNNING.** One complete guarded cell spans `256` scored pixels,
or `0.993497 mm` in object space at `1.32x`. At the worst allowed
`1.02-degree` tilt, one guarded row spans `17.68565 um` in depth.

**VERIFIED BY READING.** M84b's measured converter-on bellows-factor lower
bound is `2.412`. With reported `f/5.6`, conservative
`m_reference = 2.7015`, and the repository's practical
two-sensor-pixel/Nyquist-matched CoC, the macro-DoF equation gives a total DoF
floor of `37.92414 um`.

**VERIFIED BY RUNNING.** Two complete guarded rows fit:

```text
35.37130 um < 37.92414 um.
```

**VERIFIED BY RUNNING.** Three rows do not:

```text
53.05695 um > 37.92414 um.
```

**INFERRED — EXACT REFERENCE COUNT: `4`.** Capture one reference strip per
adjacent row pair: `01–02`, `03–04`, `05–06`, and `07–08`. The strip centers
are the four fiducial-derived row-pair centers, not subjective
near/middle/far thirds.

**INFERRED.** The earlier `3–7` result used a permissive two-pixel CoC and an
unspecified tilt axis over a continuous plane. Freezing the gradient along the
eight-row short axis and respecting complete guarded-row extents resolves the
branch: three strips cannot contain the two `3`-row groups they would need,
while four contain four `2`-row groups.

**INFERRED.** The four-strip minimum has little focus-centering slack and is
not released by arithmetic alone. The non-holdout rehearsal must prove that
both edge rows of every pair clear the frozen focus and transfer gates in both
repeats. Failure blocks the holdout; it is not repaired after scored capture.

### 2.3 Scored-path witness strips

**INFERRED.** Use three TC0 witness strips covering rows `01–03`, `04–06`,
and `07–08`. This preserves the existing near/middle/far physical-control
shape without borrowing the unmeasured bare-lens pupil-magnification bracket.

**VERIFIED BY RUNNING.** Even the deliberately pessimistic physical floor
`B = 1` gives a TC0 two-pixel DoF of `65.85678 um` at `1.32x`. Three
complete guarded rows fit (`53.05695 um`); four do not
(`70.74259 um`).

**INFERRED — EXACT SCORED-WITNESS COUNT: `3`.** This is the minimum that
covers all eight rows under the conservative `B = 1` floor and the frozen
tilt tolerance.

## 3. Scored-path physical witness

### 3.1 Frame cost

**INFERRED.** For each witness strip `01–03`, `04–06`, and `07–08`, capture:

```text
TC0-DOM-S<strip>-A: 16 fixed-focus RAWs
TC0-DOM-S<strip>-B: 16 fixed-focus RAWs
```

**INFERRED.** Move focus away and return from the registered direction between
the A and B groups. Both groups use the same row center, exposure, aperture,
ISO, stabilization state, and physical target. Focus Bracket is off.

**VERIFIED BY RUNNING.** The scored-path witness costs:

```text
3 strips x (16 A + 16 B) = 96 frames.
```

**INFERRED.** The candidate and comparator input manifests must exclude every
`TC0-DOM-*` frame. These RAWs exist only to admit or refuse the reference.

**VERIFIED BY READING.** The current 60 TC0 reset/start/end witnesses cannot
replace this block. They contain only six frames per state, do not cover all
eight target rows, and were designed to test focus reset and bracket
endpoints rather than independent per-cell information.

### 3.2 Same sitting, not a substitute sitting

**INFERRED.** The scored witness must be captured in the same uninterrupted
holdout sitting as its reference and scored brackets. Otherwise session-common
illumination, focus, sensor, and calibration terms are not the terms bounded
by the gate.

**INFERRED.** The exact-configuration non-holdout rehearsal must contain its
own `R` and `S` witness blocks and must pass before the holdout is released.
Those development frames freeze power, margins, and execution; they receive
no score credit.

### 3.3 Calibration and common-mode frames

**VERIFIED BY READING.** M164 requires residual common-mode power to be
bounded on matched featureless, dark, and flat controls. The staged design
implements this with held-out `FLAT-V/DARK-V` groups that fit neither A nor B
map.

**INFERRED.** The current `891`-frame request has only A/B flat and dark
groups. Add:

```text
TR-FLAT-V   32
TR-DARK-V   32
TC0-FLAT-V  32
TC0-DARK-V  32
```

**VERIFIED BY RUNNING.** Those held-out validation groups cost `128` frames.

**INFERRED.** The `1,147` total assumes M165 proves one focus-portable
A/B/V calibration class per optical state. If it requires another flat-focus
class, add the class before capture and recompute the total; do not reuse
`1,147`.

## 4. Revised registered frame count

**VERIFIED BY RUNNING.** The exact reconciliation against the current
`891` is:

| change | frames |
|---|---:|
| current registered session | `891` |
| replace three reference strips (`96`) with four (`128`) | `+32` |
| add three-strip TC0 physical witness | `+96` |
| add converter-on and TC0 held-out flat/dark validation | `+128` |
| **revised registered session** | **`1,147`** |
| existing throwaway histogram frame | `+1` |
| **revised shutter releases in the sitting** | **`1,148`** |

**VERIFIED BY READING.** M147's two-frame scale preflight is a separate
pre-session gate and is not included in `1,147`.

**INFERRED.** If the orchestrator instead starts from M164's already
V-amended `1,019` combined-session count, the same answer is:

```text
1,019 + 32 reference-strip frames + 96 witness frames = 1,147.
```

## 5. Can strict transfer dominance exist through the shared objective?

### 5.1 Clarification of the inequality

**VERIFIED BY READING.** M164 does **not** require `delta_H,k > 1`. It
requires:

```text
LCB95(|H_R,k| / |H_S,k|) > 1 + delta_H,k
```

with `delta_H,k > 0`.

**INFERRED.** If `delta_H,k > 1` were read literally, the transfer ratio would
have to exceed `2` in every licensed cell. The current optical evidence does
not support that interpretation.

### 5.2 Physical plausibility

**VERIFIED BY RUNNING.** Using only the proposal's diffraction Airy intervals
and the circular-aperture MTF, the conservative ideal
`|H_R|/|H_S|` ratios at the four licensed radial frequencies are:

| cell (`cyc/scored px`) | conservative diffraction-only ratio |
|---:|---:|
| `0.10` | `1.03405` |
| `0.15` | `1.05534` |
| `0.20` | `1.08031` |
| `0.25` | `1.10985` |

**INFERRED.** A small strictly positive `delta_H,k` is therefore physically
plausible through the shared objective on non-null modes. The shared prime
does not force the ratio to one because the converter state, object sampling,
effective pupil, and downstream noise differ.

**INFERRED.** The margin is smallest in the lowest-frequency cell and is not
large. Viltrox aberration, transmission loss, focus error, or bare-lens pupil
behavior can erase or reverse it. Diffraction arithmetic cannot admit the
rig.

### 5.3 Measurement that settles it

**INFERRED.** The settling measurement is the frozen M164 gate on the
same-target, same-session physical pair:

- converter-on `TR-S01..S04`, two independently calibrated 16-frame repeats
  per two-row strip; and
- converter-off `TC0-DOM-S01..S03`, two independently calibrated 16-frame
  repeats covering `3/3/2` rows.

**INFERRED.** Common fiducials provide subject-space mapping. The matched
featureless cells and held-out A/B/V calibration bound common-mode error.
Every licensed cell must clear both simultaneous lower bounds; one failed
cell returns `UNMEASURED`.

**VERIFIED BY READING.** No existing archive frame can supply this
measurement. M141 found all `10,509` inventoried ARWs report the
converter-on `200 mm` state, all have stabilization on, and zero stacks expose
a recoverable bare-lens `1.32x–1.33x` state. There is no same-subject,
same-session TC-on/TC0 fixed-focus A/B witness pair with disjoint calibration.

**INFERRED.** The two-frame M147 pair can establish scale and field only. It
cannot establish `I_R/I_S` or `|H_R|/|H_S|`.

## 6. Exact owner-facing replacement text

**INFERRED — PASTE-READY TEXT FOLLOWS.**

> ### M1 reference-information-dominance amendment — blocking
>
> **Do not begin the scored session until the exact-configuration non-holdout
> rehearsal has passed `REFERENCE_INFORMATION_DOMINANCE` in every licensed
> channel/frequency/orientation cell. The two-frame M147 result is necessary
> but not sufficient.**
>
> **TC0 magnification:** target `1.32x`; hard maximum `1.33x`. Do not move the
> target lower to make the reference gate easier. Accept the placement only
> when the frozen M147 lower bound is at least `2.0`, the complete target and
> every guard remain in the common field, and the measured carrier/interior/
> guard mapping is valid.
>
> **Target orientation:** use the independently seeded `10 x 8` panel. Put the
> ten-column direction on one iso-depth line. Tilt only across the eight-row
> direction at `1.00 degrees +/- 0.02 degrees`, measured from fiducials. A roll,
> yaw, plane residual, or depth gradient along a row outside the frozen
> geometry tolerance is STOP.
>
> **Converter-on reference:** replace `TR-REF-NEAR/MID/FAR` with four
> row-pair blocks: `TR-S01-R01-02`, `TR-S02-R03-04`,
> `TR-S03-R05-06`, and `TR-S04-R07-08`. For each strip, turn Focus
> Bracket off, approach the fiducial-derived row-pair-center focus from the
> registered direction, take the `-A` half (`16` RAWs), move focus away,
> return by the same approach, and take the `-B` half (`16` RAWs). Keep every
> full guarded site inside one fixed-focus support; no site may cross a strip
> seam. Total reference: `4 x 32 = 128` RAWs.
> The four-strip layout is allowed only after the exact-configuration
> non-holdout rehearsal proves both edge rows of every pair eligible in both
> A/B repeats.
>
> **Converter-off scored-path witness:** after converter removal, successful
> live M147 placement, and TC0 A/B calibration acquisition, capture three
> fixed-focus strips: `TC0-DOM-S01-R01-03`,
> `TC0-DOM-S02-R04-06`, and `TC0-DOM-S03-R07-08`. At each strip take the
> `-A` half (`16` RAWs), move away and return by the registered approach, then
> take the `-B` half (`16` RAWs), with Focus Bracket off. Use the scored
> optical state and exposure exactly. These `96` RAWs are excluded from every
> candidate and comparator input manifest; they exist only for
> `REFERENCE_INFORMATION_DOMINANCE`.
>
> **Held-out calibration validation:** in addition to the existing A/B
> flat/dark sources, capture `TR-FLAT-V`, `TR-DARK-V`, `TC0-FLAT-V`, and
> `TC0-DARK-V`, `32` RAWs each. V fits neither A nor B map. Move or rotate the
> diffuser for each flat lineage and preserve the frozen temperature/focus
> class.
>
> **Physical order:** acquire converter-on A/B calibration sources; complete
> the existing converter-on subject/focus blocks; acquire the four reference
> row blocks; acquire converter-on V validation; remove the converter once;
> pass the live M147 ratio/field gate; acquire TC0 A/B calibration sources;
> acquire the three TC0 dominance-witness strip blocks; reset by the registered
> approach and complete the existing TC0 scored brackets and endpoint
> witnesses; acquire TC0 V validation; hash and seal the sitting before any
> candidate render.
>
> **Frame total:** `1,147` registered frames. This is the current `891`, plus
> `32` frames from replacing three reference strips with four, plus `96`
> scored-path witness frames, plus `128` held-out validation frames. The one
> histogram frame makes `1,148` shutter releases. The M147 two-frame preflight
> remains outside the scored sitting.
>
> **STOP conditions:** any missing row, failed focus return, failed
> per-row scale/geometry, failed A/B/V calibration lineage, failed common-mode
> control, or any licensed cell that does not clear both simultaneous M164
> dominance bounds makes M1 `UNMEASURED`. Do not add strips, change
> magnification, change target tilt, or change a threshold after any scored RAW
> is read.

## 7. Final physical ruling

**INFERRED.** The rig is not proved incapable. Diffraction predicts only a
small positive reference-transfer advantage, and the required paired physical
witness can be captured without per-node A/B interleaving.

**INFERRED.** The current archive cannot settle the gate, and the current
`891`-frame session cannot satisfy it. The owner should perform the
exact-configuration non-holdout rehearsal first; only a pass licenses the
`1,147`-frame holdout sitting.

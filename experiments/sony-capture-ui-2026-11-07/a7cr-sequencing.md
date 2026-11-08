# A7CR pixel-shift / focus alternation

Scope: `sony-capture-ui-2026-11-07`. Research date: 2026-11-07. No A7CR hardware
was available; no A7CR was connected, rented or requested from the owner.

**Answer: four-shot pixel shift alternating with externally commanded focus is
a credible, documented implementation path, and I would design the A7CR backend
around it. It is not an end-to-end hardware-verified feature. Sixteen-shot
automation is not established by the supplied public interface.**

The earlier statement that the firmware's native Focus Bracket restriction makes
external alternation impossible does not follow. An external sequencer need not
select native Focus Bracket at all. Conversely, separate support for two commands
does not prove every combination of camera mode, firmware and lens accepts them.
That distinction is the remaining limit on a research-only answer.

## What the sources establish

| Evidence | Classification | Consequence |
| --- | --- | --- |
| Sony's A7CR help guide supports pixel shift from Imaging Edge Remote, permits Camera Only saving, and prohibits setting changes within a group. | VERIFIED | Treat the complete four/sixteen exposures as one atomic group; change focus only after completion. |
| The public PTP 3 compatibility table marks A7CR support for pixel-shift properties and absolute focus. | VERIFIED in supplied 2.02.00 reference; see earlier SDK audit | A single direct PTP backend can address both feature families. This is not an SDK property-enum trick. |
| `0xD23A` is a writable count; the explicit note permits only 1 and 4. | VERIFIED, printed p. 460 | Four-shot selection has a permitted public write. The listed read value 16 does not authorize writing 16. |
| `0xD23C` exposes group status, `0xD23D` progress; absolute focus uses `0xE042`/`0xE043` with a completion event. | VERIFIED, pp. 461–463, 567–568, 691 | The sequence can use completion and readback instead of blind sleep timing. |
| Sony Remote offers manual-focus adjustment and four/sixteen-shot pixel shift. | VERIFIED in Sony documentation | Both operations exist in the official product; its sixteen-shot control is not proof that the public command supports that write. |
| Focus moves are accepted between groups with this exact A7CR + FE100 GM + Viltrox 2× combination. | UNVERIFIED | No lens-specific precision, successful 900-plane run or unconditional purchase guarantee is claimed. |

Sources: [A7CR pixel-shift help](https://helpguide.sony.net/ilc/2370/v1/en/contents/0414M_pixel_shift_shooting.html),
[A7CR pixel-shift workflow](https://support.d-imaging.sony.co.jp/support/ilc/psms/ilce7cr/en/index.html),
[Sony Remote operation panel](https://support.d-imaging.sony.co.jp/app/imagingedge/en/instruction/4_3_panels.php),
[Camera Remote Command release/support page](https://support.d-imaging.sony.co.jp/app/cameraremotecommand/en/index.html).
The release page confirms the supplied June 10, 2026 version 2.02.00 and lists
A7CR support; it is not a model-specific combined-operation certification.

The supplied archives have unchanged identities:

- `CameraRemoteCommand-2.02.00.zip`: SHA-256
  `eea563acb772f99001ac530b116423a337ce464193371b10fed0ba4768acb4a9`.
- `CrSDK_v2.02.00_20260610a_Win64.zip`: SHA-256
  `4d4cc0bee7fdd60e1e947bfa7a524cbfb5550465ceccc8647eb7b7cdc383ef77`.

Reference locations and original extraction commands are retained in the
[SDK audit](../sony-focus-control-2026-11-07/sdk-audit.md). This continuation read
the extracted `Camera Control PTP 3 Reference.txt` at the named property sections,
the Remote Command README/example manual, and the SDK's live-view, focus
magnifier, focus-position and setting-file API pages directly from its ZIP.
It searched the SDK headers for pixel shift/composite/multishoot property names;
none expose a usable pixel-shift control in this version. No third-party
GPL/LGPL implementation was consulted. Public searches for combined remote
focus/pixel-shift automation did not establish the exact A7CR sequence.

## Proposed four-shot state machine

1. Open one PTP 3 session, negotiate extended properties and query actual support,
   writable flags and allowed values. Use MF, manual/fixed exposure, and card-only
   storage. Native Focus Bracket is off. Preserve relevant original settings.
2. At idle, set count 1 if required to leave pixel-shift selection before moving
   focus. Read back count and mode; do not assume count alone changed the mode.
3. Set the next absolute focus target, require the focus-result event and current
   value readback, then allow the measured settling time.
4. Set count 4 through `SDIO_SetExtDevicePropValue` (`0x9205`) and select an allowed
   interval, normally Shortest for the owner's continuous light. Require readback
   and the expected `0xD239` mode. The mode property itself is read-only.
5. Release once. Wait for four acknowledged captures, consistent group progress,
   group-idle and media-idle states. Idle alone before the exposure starts is not
   completion. Never move focus within a group or retry an uncertain release.
6. Record the group and repeat from step 2. Pause/stop take effect after the whole
   group. Capacity, power, temperature, sequence duration and lens range bound the
   run; the native 299-frame bracket limit does not govern this external loop.

This is an **ARGUED** implementation plan from documented primitives. It covers
the likely case where focus needs pixel shift temporarily deselected, without
relying on simultaneous mode availability. Whether count selection produces the
required mode transition in every applicable state is not specified as a full
sequence in Sony's reference. A production backend must refuse unsupported
transitions rather than substitute ordinary captures and label them pixel shift.
The Windows SDK helper in the new A7C II app cannot perform steps 2/4 because
the high-level SDK lacks those properties; a direct PTP transport must own the
whole A7CR session. Alternating competing SDK and PTP sessions is not the design.

## Sixteen shots

**VERIFIED:** A7CR and Sony Remote can capture sixteen shots. **UNVERIFIED:** the
supplied public protocol can select that mode programmatically. Do not write
`0x0010` contrary to the reference note. Preselecting sixteen on the camera and
only moving focus between groups is a possible route, but depends on the preset
surviving the session and focus being writable without falling back to count 1.
If changing to count 1 is required, the documented write interface cannot restore
16. Thus sixteen remains an optional investigation, not a promised capability.

Four independent ordinary four-shot groups also do not reproduce sixteen-shot
half-pixel sampling: the required physical sensor offsets must actually exist.
The [optical analysis](../sony-upgrade-2026-11-07/results.md) already favors four
shots for this diffraction-limited macro path, especially for full-color
sampling. No new resolution measurement is claimed by this protocol research.

## SD sidecars

**VERIFIED scope:** PTP 3 `SendObject` is documented for fixed special handles
used by camera/FTP settings (pp. 112–113); the SDK offers typed setting/LUT/grid
and firmware transfers. The documented interfaces inspected do not provide an
arbitrary filename/directory write of a JSON sidecar during PC Remote capture.
Standard PTP's name alone does not establish that a camera implements arbitrary
`SendObjectInfo`/filesystem writes. A JSON manifest must not be disguised as a
camera-settings file. The implemented path journals on the laptop and exports
new metadata files to the mounted SD card afterward. Normal RAW EXIF/MakerNotes
remain camera-generated; command units are not embedded as calibrated depth.

## Decision

Prioritize the A7C II app now and a separate, capability-gated **four-shot PTP 3
A7CR backend** next. The conclusion is feasibility, not a claim that the new
package already supports A7CR. Research cannot honestly erase the remaining
combined-operation uncertainty, and the owner is not being asked to acquire a
camera to complete this report. No production merge default or sensor profile
changes follow from these results.

# Sony SDK and Camera Remote Command audit

Evidence date: 2026-11-07. **VERIFIED** describes supplied documentation/header
contents, not an operation performed on a camera. Optical behavior remains
**UNVERIFIED**. Source archives are owner-provided local files, unchanged.

## Package contents

- `Downloads/CrSDK_v2.02.00_20260610a_Win64.zip`:
  SimpleCli, RemoteCli, SDK HTML API reference, SDK Readme, sample manual, USB
  drivers and third-party source archives. RemoteCli is an SDK sample; this ZIP
  does not contain the separate Camera Remote Command reference.
- `Downloads/CameraRemoteCommand-2.02.00.zip`:
  PTP 2 and PTP 3 reference PDFs, protocol examples for Windows/Linux, example
  manual and README. The later supplied archive resolves the documentation gap.

The SDK headers and both SDK sample trees contain no pixel-shift symbol matching
`pixel[ _-]?shift` (case insensitive). This establishes absence from those public
surfaces, not an inability of the camera to do pixel-shift remotely. The Command
reference explicitly documents such properties.

The references are extracted locally to ignored
`outputs/sony-control/command-2.02.00/`. PTP 3 PDF page numbers below are the printed
page numbers and also match the PDF's one-based page index. Relevant table pages
were rendered for visual inspection; text extraction alone does not preserve
which camera column contains a check mark.

## Pixel-shift controls in PTP 3

Source: **Camera Control PTP 3 Reference**, pp. 71, 97-98, 459-463.
The compatibility matrix marks these five properties supported on **ILCE-7CR**
and leaves **ILCE-7CM2** blank. They are device properties, not standalone shutter
operation codes, and their wire codes are not SDK `CrDeviceProperty` enum IDs.

| PTP device property | Code | Access / values |
| --- | --- | --- |
| Pixel Shift Shooting Mode | `0xD239` | Read only; 0 off, 1 burst shooting |
| Pixel Shift Shooting Number | `0xD23A` | Get/set UINT16; table lists 1, 4, 16 |
| Pixel Shift Shooting Interval | `0xD23B` | Get/set UINT16; enumerated seconds, with `0xFFFF` shortest |
| Pixel Shift Shooting Status | `0xD23C` | Read only; 0 not shooting, 1 shooting |
| Progress Number of Pixel Shift Shooting | `0xD23D` | Read only UINT16; current shot index starting at 1 |

**Critical restriction, p. 460:** although the number table includes 16, its note
permits writing only **1 or 4**. Do not implement a 16-shot selector by blindly
writing `0x0010`. A camera-menu-preconfigured 16-shot mode is a separate hardware
test, not a documented exception to that restriction. This makes four-shot mode
the appropriate first integration target for the owner's stated preference.

`SDIO_SetExtDevicePropValue` is operation **`0x9205`**, with the device property
code in operation parameter 1 (pp. 116-117). A raw PTP implementation must also
handle the connection/authentication sequence, supported properties, enabled
state, permitted values, data phase and events. It cannot send these numbers
through the SDK property API and assume they have the same meaning.

**ARGUED integration sequence to validate on an a7CR:** read capabilities and
original settings; configure four-shot count and interval; verify the reported
mode/count; release the shutter; observe an actual group start/progress and four
completed RAWs; wait for group completion and media readiness; then move focus,
wait for focus completion and settle, and repeat. If setting the count does not
enable the mode, stop and inspect the camera/menu state. The reference's read-only
mode property alone is not proof of a separate remotely writable enable switch.
An idle status before a group begins must never be mistaken for completion.

**UNVERIFIED:** alternation of pixel-shift and focus commands on the actual a7CR,
whether focus movement is enabled while pixel-shift remains selected, transfer
and buffering behavior, and the resulting optical benefit. The original proposed
ESP32 loop did not establish these. They now have a documented basis for testing.

## Focus control in SDK and PTP 3

SDK headers expose `CrDeviceProperty_FocusPositionSetting` and
`CrDeviceProperty_FocusPositionCurrentValue`. Its HTML property pages describe
UINT16 range 0..65535, step 1. The SDK Tips / Trouble shooting section calls this
a normalized value and recommends calibration for each camera/lens and shooting
environment. It warns that return position can vary.

PTP 3 exposes the corresponding quantities:

| Quantity | PTP code | Source |
| --- | --- | --- |
| Focus Position Setting | `0xE042` | p. 567; UINT16 range 0..65535, step 1; setting contains the target |
| Focus Position Current Value | `0xE043` | p. 568; returned current normalized value |
| Focus-position result event | `0xC218` | p. 691; result 0 invalid, 1 OK, 2 NG, 3 canceled |

The extended property option must be enabled when negotiating/using the extended
`0xE000..0xEFFF` space (p. 116, subject to camera protocol support). Using the raw
protocol does not itself demonstrate a finer focus actuator than the SDK: the
documented normalized coordinate is the same size. No direct lens encoder-unit
claim is supported by these documents.

The current helper uses the SDK, waits for
`CrWarning_FocusPosition_Result_OK`, reads back the current value, then adds the
requested settle time. A same-position request with no event can be recorded as
`unchanged-readback-no-event` after the timeout; a nonzero move without completion
fails. No outcome is labelled an optical movement merely from a successful return.

## Strehl integration boundary

The delivered acquisition helper is independent of the Rust merge pipeline.
Its ordinary RAW stacks can be manually copied from the SD card and imported
when the owner chooses. The helper transfers no image files. It records a
transport-independent plan and photographic provenance, with separate native
group captures. This is the right place to add a future PTP backend without
mixing competing SDK and raw-PTP sessions on one USB interface.

For pixel-shift, extend capture records to identify focal plane, shift-group ID,
member index, requested sensor offset, actual RAW dimensions/CFA origin, exposure,
focus read-back and completion evidence. Admit a group only if all required
members exist. Nominal shift positions are initialization data; fit residual
geometry from the capture rather than treating the requested motion as exact.

At reconstruction, preserve the existing storage and noise invariants: original
u16 CFA, f32 arithmetic, one injected noise model, gather samples in the consumer,
and a single final demosaic/reconstruction. Do not route a prematurely demosaiced
pixel-shift composite back through an ordinary Bayer input path. Group focus
planes explicitly, so members of one fixed-focus group are not mistaken for
distinct depth samples. Sensor calibration for an a7CR remains a separate task.

Wi-Fi transport and power design do not need to precede this optical test.
The current Windows USB SDK backend deliberately provides a bounded first test;
neither wireless control nor sustained power adequacy has been measured here.

## SD-card-only completion

The SDK 2.02 HTML reference's `op_flow_and_seq/op_capture_an_image_sequence.html`
describes `CrNotify_Captured_Event` in `OnWarning` after an image reaches camera
memory, separately from the host-download callback. The helper counts these
events and polls `MediaSLOT1_Status`, `MediaSLOT1_WritingState` and
`FocusBracketShootingStatus`, requiring all expected events and a one-second idle
interval. The remaining-image count is used as a capacity estimate, not an exact
file counter. These rules are **VERIFIED against local SDK documentation**;
their behavior on the owner's rig is **UNVERIFIED** until the physical test.

`StillImageStoreDestination = MemoryCard` is checked before every shutter command.
No `SetSaveInfo`, image-fetch or preview-fetch API is called. SDK live view is
disabled. The old download/review-copy path and host destination options were
removed. Camera events and idle status do not independently prove that each SD
file is complete or readable; the operator checks the card after the run.

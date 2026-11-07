# Implementation verification and pending camera test

Date: 2026-11-07. Owner: root. **Implementation handoff complete; optical
experiment pending.** No photographs were taken during this development session.
No merge/sensor profile defaults changed and no SYNTHESIS conclusion was folded.

Follow-up on 2026-11-07: the owner completed two 73-RAW SD-only runs. Their
[separate physical review](../sony-focus-control-2026-11-07-capture-review/results.md)
confirms command/capture completion and reports local optical plateaus,
approach dependence and finer-than-native response. The pending statements
below describe the original development handoff, before those captures; the
follow-up does not establish production readiness or image-quality gains.

The owner's follow-up changes acquisition to **SD-card only**. The earlier
PC+card ZIP is superseded. The current driver has no image-download or review-copy
path; the computer retains only logs. Captures finish on camera events plus card
and bracket idle status, without fetching or checksumming image files.

## VERIFIED: build and SDK loading

Command actually run from the Strehl root:

```powershell
& tools/sony-control/build.ps1
```

Successful x64 Release build with MSVC 19.44.35226 / Visual Studio 2022 Build
Tools, Windows SDK 10.0.26100.0, `/W4 /WX`, two build workers. MSBuild compiled
`strehl-sony-control.cpp` and linked the executable after its final edits.
The SDK is external; the build copies its DLLs and supplied notices beside the
helper. The exact source/binary/archive SHA-256 values and timestamp are in
ignored `outputs/sony-control/build-receipt.json`.

Input SDK archive SHA-256:
`4d4cc0bee7fdd60e1e947bfa7a524cbfb5550465ceccc8647eb7b7cdc383ef77`.
Camera Remote Command archive SHA-256:
`eea563acb772f99001ac530b116423a337ce464193371b10fed0ba4768acb4a9`.

```powershell
python experiments/sony-focus-control-2026-11-07/inspect-toolkit.py
```

Exit 0. The reproducible read-only audit scanned 32 SimpleCli source/header files
and 181 RemoteCli source/header files; zero matched `pixel[ _-]?shift` ignoring
case. Archive inventories and hashes are in
`outputs/sony-control/toolkit-audit.json`. The separate PTP 3 PDF has the pixel-shift
properties described in [the audit](sdk-audit.md), including the restriction on
writing the 16-shot count. Relevant compatibility tables were visually inspected.

## VERIFIED: offline execution and failure controls

```powershell
python tools/sony-control/test-sony-control.py
& outputs/sony-control/bin/strehl-sony-control.exe self-test
```

Current result: **17 Python tests passed** and **19 native completion-gate
assertions passed**, both exit 0. Python 3.12, one test worker. The native
self-test runs before SDK initialization and makes no camera connection.

The tests exercise the actual plan/execution functions with a fake camera bridge.
They cover repeated sweeps, both approach directions, nulls before focus motion,
the positive-control offset, range refusal, a 1,000-frame sequential plan,
the native order/count dependency, failure before exposure, no shutter retry,
host/PC+card argument refusal, card capacity/readiness, strict completion metadata,
all 73 simulated card images accounted in a complete fake run, contiguous expected
image ranges, persisted unfinished-capture intent, no image files on the computer,
and exposure preflight. These are software checks, not image-quality measurements.

The native gate rejects an idle card without new events, missing or extra events,
an unfinished bracket/write, a card error and any unexpected host-download event.
It waits for a stable idle interval after the complete event count. This is the
exact gate called by the capture loop, exercised with synthetic states; hardware
event delivery and card durability are not established by these tests.

The original 14-test run and host-file checks in `outputs/sony-control/offline-tests.txt`
belong to the superseded PC+card version. Tests now write checked temporary log
directories under the workspace and never fabricate image files.

## VERIFIED: real SDK smoke test without a camera

Before the SD-only revision, the real native binary was invoked (its directory
was the working directory):

```powershell
& outputs/sony-control/bin/strehl-sony-control.exe list
python tools/sony-control/sony-control.py status --out outputs/sony-control/no-camera-smoke-001
```

Enumeration returned exit 0 and
`{"ok":true,"sdk_version":33685504,"cameras":[]}`. The version value is
`0x02020000` (SDK 2.02.00). No camera was visible to this SDK session.
The status invocation intentionally returned exit 1 with a diagnostic requiring
one USB ILCE-7CM2; it preserved a failed-session manifest with no captures.
Both exact process argument lists, stdout/stderr, expected exits and actual exits
are recorded in `outputs/sony-control/native-smoke.json`.
Replacement-package relocation and SDK-loading checks are recorded separately in
the repository's `experiments/sony-focus-control-2026-11-07/portable-package.md`
and `outputs/sony-control/packages/sd-card-only-verification.json`.

## DERIVED: capture plan; UNVERIFIED: photographic result

The default plan requests 73 RAWs in 57 shutter commands: 5 fixed nulls, 3 command
nulls, 2 larger-move/return images, 39 fine-sweep images, 6 approach/return images,
and 18 images from two native nine-shot bursts. This count was verified through
the software executor, not by capturing on the owner's camera.

Hardware-dependent behavior remains unverified: writable absolute focus with the
Viltrox converter, focus-result callbacks, physical motion per normalized unit,
repeatability, per-image capture events and native bracket triggering, camera/card
readiness, settings restoration, sustained power, and finer-than-width-1 optical
movement. The default plan stops on uncertainty and retains evidence. It must not
be described as a production-validated camera driver.

The [operator guide](../../tools/sony-control/README.md) provides setup, commands,
rejection conditions, and photographic review instructions. The owner should
retain the log directory and SD images, and manually copy the images for analysis
when desired, with rig/target details. A successful camera
run plus an independent optical review is required before any precision or image
quality claim, or any adoption as a default Strehl acquisition method.

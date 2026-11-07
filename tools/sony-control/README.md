# Sony a7C II focus capture prototype

This standalone Windows helper uses your Sony Camera Remote SDK 2.02.00 to move
focus to normalized absolute positions, capture RAWs, and compare those moves
with native focus bracket width 1. It includes a reusable sequential stack mode.
The native executable has been built locally under `outputs/sony-control/bin/`.

**Photos save only to the SD card.** The computer keeps settings and command logs.
There are no image downloads, preview downloads, or review-image copies. This
version replaces the earlier PC+card package; replace the entire extracted folder.

**Physical distance per command is uncalibrated.** The
[first two physical tests](../../experiments/sony-focus-control-2026-11-07-capture-review/results.md)
found repeated optical plateaus, approach dependence and approximately threefold
finer local response than native width 1. Command units are not motor steps or
micrometres. A successful command/read-back is not proof that focus moved.
The a7C II has no pixel-shift multi-shooting. This version uses USB; it does not
yet implement Wi-Fi control, live view, ESP32 firmware, or a7CR pixel-shift capture.
See [the SDK/Command audit](../../experiments/sony-focus-control-2026-11-07/sdk-audit.md)
for the now-confirmed PTP 3 pixel-shift controls.

## 1. Prepare the camera and target

Use your FE 100mm F2.8 Macro GM, **Viltrox 2x**, X4 CPL, and stabilized KL1500 LCD
lighting with the existing diffuser/polarizer. Keep the same magnification,
aperture, polarization, and illumination throughout this first test.

1. Secure the camera and a **sloping, finely textured target**. A finely marked
   ruler or printed fine text on a rigid plane tilted about 30-45 degrees to the
   sensor plane works for an initial screen. At your macro magnification, the
   target needs texture finer than ordinary ruler divisions. Include a nearby
   featureless matte patch for the noise/brightness control. Avoid metallic glare.
2. Use still-photo mode, exposure **M**, fixed ISO, fixed shutter speed, and fixed
   white balance. Use your normal wide-open setting (approximately reported f/5.6
   with the 2x). Expose below clipping. Set SteadyShot off for this rigid setup.
   Choose uncompressed or lossless compressed full-size RAW in the camera.
3. Set **MF** and manually focus a textured area near the middle of the visible
   slope, leaving room for the sharp band to move both ways. Avoid the lens's
   near/infinity stops. Do not touch the lens, camera, target, CPL, or light during
   the sequence. Let the continuous light stabilize first.
4. Insert a card with space for at least **73 RAWs**. The helper checks the camera's
   remaining-image estimate. Note the first/last filename, or create a new camera
   folder for this test. Keep normal camera filenames and take no unrelated photos
   during the run. The computer needs space only for the small logs.
5. Close Imaging Edge Remote and any other tethering application; disconnect the
   smartphone remote session. Connect the camera directly with a USB data cable.
   On the camera choose **Remote Shoot (PC Remote)**. Alternatively select Setup
   > USB > USB Connection Mode > PC Remote. Sony documents these options in the
   [USB guide](https://helpguide.sony.net/ilc/2360/v1/en/contents/0601_usb_connection.html)
   and [PC Remote guide](https://helpguide.sony.net/ilc/2360/v1/en/contents/0903_pc_remote_function.html).
6. Start with a charged battery and turn USB Power Supply on. A computer port
   supplying USB data is not a guarantee of sufficient power for indefinite use.

The helper first sets and verifies **memory-card-only saving**, then sets single
drive, MF and RAW-only capture. It also changes the native bracket settings during
the comparison. It attempts to restore those other settings and the initial
normalized focus position on a clean exit. **SD-card-only saving stays selected**;
an old PC/PC+card destination is never restored. **Inspect the restoration result.** Restoration
of a numeric focus value does not prove return to the identical optical plane.

## 2. Check the connection without shooting

Open PowerShell. The following commands use the already-built executable:

```powershell
Set-Location 'C:\dev\blog\death-of-software\projects\strehl'
python tools/sony-control/sony-control.py list
python tools/sony-control/sony-control.py status --out outputs/sony-control/preflight-001
```

`list` must show one USB camera with model `ILCE-7CM2`. `status` saves a
`preflight.json` containing property values and availability. It does not change
settings, focus, or release the shutter. Use a new `--out` name on every run;
existing directories are deliberately refused.

On Windows, the SDK needs Sony's libusbK USB driver. Seeing the camera in File
Explorer or under **Portable Devices** does not establish that this driver is
installed: Sony's setup manual shows that state before driver installation, even
after selecting PC Remote. The helper includes the driver files but does not
install them automatically.

If the check reports `found 0`, keep the camera connected in PC Remote mode and
open **Device Manager**. If it appears under **Portable Devices**, install the
bundled driver:

1. In the extracted laptop package, open `drivers/sony-usb/`.
2. Right-click **`srcameradriver.inf`** and choose **Install**. In Windows 11,
   use **Show more options** if needed. This is the file for the a7C II; the
   separate `srcameradriver_dscrx0m2.inf` is for the RX0 II.
3. Complete the administrator/driver installation prompts for Sony's supplied
   driver, then reconnect the camera and select **Remote Shoot (PC Remote)**.
4. Check for **libusbK Usb Devices > Sony Remote Control Camera** in Device
   Manager, then rerun `01-check-camera.cmd`.

These are the installation steps in Sony's `RemoteSampleApp_IM_v2.02.00.pdf`,
pages 9-11, supplied in the original SDK archive. If Windows rejects installation,
record its exact error. If the correct device entry already exists, close other
tethering applications, reconnect, and retain the check output and device status
for diagnosis. No change to SD-only saving is required.

## 3. Run the focus test

This command **moves the lens and takes 73 RAW photographs**:

```powershell
python tools/sony-control/sony-control.py focus-test --out outputs/sony-control/focus-test-001
```

Default settings: 1,000 ms extra settling after Sony's focus-complete event;
90 seconds maximum for each exposure/card write or native bracket group; one
sequence worker. The native helper checks SD-only saving before every shutter
command. It waits for the expected number of Sony capture events, then requires
card writing and native bracketing to remain idle for one second. A previously
idle card alone cannot mark a new exposure complete. Missing events, an unexpected
count or a card error stops the sequence; there is no download fallback.

| Phase | RAWs | Purpose |
| --- | ---: | --- |
| Fixed null, before any focus command | 5 | Noise, illumination drift, target/camera motion |
| Command the same focus position | 3 | No-op command placebo |
| Move +512 normalized units, then return | 2 | Check that the target can reveal a larger real focus change |
| Three identical monotone sweeps | 39 | Offsets 0, 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64 |
| Return to baseline from either side, three times | 6 | Direction dependence and return repeatability |
| Two native brackets, width 1, nine shots each | 18 | Physical step-size comparator |

Each fine sweep approaches from 128 normalized units below the baseline. Native
brackets are configured as 0 -> + (toward infinity); the sign of an SDK numeric
increment should be established from the photographs. If needed, repeat in a
**new** directory with `--direction -1`. This reverses the custom sweeps and their
approach, not the camera's native bracket direction.

For long exposures increase `--timeout`, e.g. `--timeout 300`; a native nine-shot
group must fit within that whole timeout. `--settle-ms 2000` increases settling.
The test validates all targets before moving. If it would cross 0 or 65535,
refocus away from the endpoint; it will not silently clamp positions.

Press Ctrl+C once to stop scheduling further shots. The helper waits for the
active command, then attempts restoration. On an uncertain focus/capture timeout
it retains settings for inspection and does **not** retry the shutter or move the
lens as if the exposure had completed. Photos remain on the card and logs on the computer. Close the
session and inspect the camera before starting a new run.

If native bracket settings are rejected, the default test stops before exposures.
`--skip-native` runs the 55-RAW absolute-focus diagnostic, but cannot establish
an improvement over native width 1. Do not silently treat that as a passing test.

If absolute focus is unavailable with the Viltrox, a separate run with the bare
lens can isolate whether the converter affects control compatibility. Label that
run separately: changed magnification makes it unsuitable as a direct optical
resolution comparison. A successful bare-lens run does not certify the converter.

## 4. What to inspect and return

The output directory contains logs only (portable launchers put it under `logs/`):

- `manifest.json`: exact plan, resolved settings, before/after read-backs, expected
  image order for each phase, camera capture-event counts, SDK/build identity,
  completion state, restoration status. An unfinished command remains under
  `active_capture` if the sequence stops before confirming completion.
- `events.jsonl`: timestamped command and response record, including warning codes.
- `preflight.json`, `native-stderr.log`: connection/capability diagnostics.

The photos use the camera's normal naming and folder behavior on the card.
Completion means **camera-reported capture events plus an idle card**, not file
readback or checksums. Verify the 73 RAWs on the card after the run. A failed or
interrupted run may have some images from the unfinished command: compare the
card contents with `active_capture` before repeating anything.

For later analysis, manually copy the test images when you choose, retaining
filenames and camera folder structure. Keep the corresponding log directory with
them. The manifest's one-based `image_range` identifies each command's expected
images; the two native brackets occupy images 56-64 and 65-73 in a complete run.
Provide magnification or field width, target angle, and camera/lens/teleconverter
firmware versions with the logs. No image import happens automatically.

Start photographic assessment with the matte patch and five fixed-null frames.
Check for brightness drift, clipping, noise and any target motion. Then confirm
that the larger-move control actually shifts the sharp region; if it does not,
the small-step experiment is **inconclusive**, not evidence that all steps work.

Compare full frames and identical native crops using one fixed RAW development
transform, without adaptive sharpening/denoising changes. On the sloping texture,
track the position of the sharp band along the target, not just total edge energy.
Noise, sharpening, breathing, changing framing and ringing can inflate an edge
score. Register the target geometry before comparing band positions. Record crop
origin/size; avoid judging from resized overviews.

A useful result requires a custom displacement that is **both smaller than the
native width-1 displacement and reproducibly distinguishable from the null and
return-position variation**. Read-back increments alone do not count. Report the
distribution across all three sweeps and both native bursts, including failures;
do not select the best-looking repeat. A coarse printed target may only bound the
minimum resolvable change; finer texture or a calibrated tilted target may be
needed before claiming micrometre accuracy.

If several consecutive command values produce indistinguishable optical focus,
record the plateau and test larger increments. If return error rivals the desired
step, use a consistent approach direction and report the residual uncertainty.
Native step width depends on aperture and initial focus; repeat calibration when
those, magnification, lens, teleconverter, or camera change.

## 5. Capture a longer custom stack after calibration

For example, from a manually selected starting focus:

```powershell
python tools/sony-control/sony-control.py stack --step 4 --count 600 --out outputs/sony-control/custom-stack-001
```

`4` is an example normalized increment, **not a recommended or measured step**.
Use the measured useful increment and direction from your rig. The helper takes
one RAW per focal plane, so the camera's native 299-shot burst limit does not cap
the total plan. Focus range, storage, battery/power, temperature, elapsed time and
connection reliability still limit a run. All photos are saved only to the card;
the computer must remain connected to send commands and retain the log.

When ready, manually copy a completed custom stack from the card and import those
RAWs into Strehl as an ordinary stack. Keep this acquisition manifest beside the
input. Sensor calibration and merge defaults are unchanged.
Do not feed all focus-test control arms into one stack as though they were a single
monotone acquisition.

## Rebuild and offline verification

Requires Windows x64, Python 3.11+, and Visual Studio 2022 C++ Build Tools with
CMake. Sony SDK dependencies remain under ignored `outputs/sony-control/`.

```powershell
& tools/sony-control/build.ps1
& outputs/sony-control/bin/strehl-sony-control.exe self-test
python tools/sony-control/test-sony-control.py
python tools/sony-control/sony-control.py plan
```

The default SDK archive is
`Downloads/CrSDK_v2.02.00_20260610a_Win64.zip`.
Override it with `build.ps1 -SdkArchive 'path-to-your-zip'`. The executable needs
the DLLs and `CrAdapter/` beside it; do not move the `.exe` by itself. The original
client source is MIT OR Apache-2.0; Sony's SDK/runtime has its own terms and
third-party notices. No Sony implementation or binary is vendored in tracked
Strehl source.

See [the experiment brief](../../experiments/sony-focus-control-2026-11-07/brief.md)
and [verification record](../../experiments/sony-focus-control-2026-11-07/results.md)
for the distinction between software checks and pending physical evidence.

# Strehl Capture

A Rust/egui capture workspace for the Sony A7C II (`ILCE-7CM2`) on Windows x64.
It uses Strehl's native palette and a small original C++ bridge for Sony's C++
SDK ABI. The UI, sequence engine, preview analysis and durable journal are Rust.
The capture executable does not link the RAW decoder or stacking engine.

**RAWs stay on the camera SD card.** Only transient live-view JPEGs reach the
viewer; they are not saved. Captures are single RAW exposures, each acknowledged
before the next focus move. A7CR/pixel-shift capture is not enabled in this build;
see the [separate feasibility answer](../../experiments/sony-capture-ui-2026-11-07/a7cr-sequencing.md).

## Run on the laptop

1. Extract the entire portable ZIP. Open **Strehl-Capture.exe**. No Python, Rust,
   Visual Studio or separate SDK installation is needed to run it. Windows x64
   and a working graphics driver are required; the supplied SDK targets Windows 11.
2. Connect the camera with a USB **data** cable and select **Remote Shoot
   (PC Remote)**. Close Imaging Edge Remote and phone camera control first.
   Use the Sony USB driver already installed for the previous test. If discovery
   reports `found 0`, follow `drivers/sony-usb` and the included Sony manual:
   Device Manager should show **Sony Remote Control Camera** under **libusbK USB
   Devices**, rather than only Portable Devices. Driver installation is manual.
3. Use manual exposure **M**, a fixed ISO, a timed shutter speed, fixed white
   balance, your stable illumination and a sufficiently full camera battery.
   Enable USB Power Supply on the camera when appropriate. The app displays
   battery level; a laptop USB connection is not a promise of sufficient power
   for an arbitrarily long stack. Keep the laptop awake throughout capture.
4. Click **Connect camera**. This selects MF, single drive, RAW-only and SD-only
   saving. It does not release the shutter. Exposure, ISO, aperture and WB remain
   under your camera settings. Disconnect restores the saved settings and initial
   focus when the last operation is known to be safe; SD-only saving is retained.
5. Jog with **−128 / −16 / −1 / +1 / +16 / +128**. Inspect the near boundary and
   **Mark current** in A. Find the other boundary and mark B. The numbers are
   normalized focus commands, not millimetres or hardware encoder positions;
   determine near/far visually for your lens.
6. Enlarge the preview with its zoom control, then drag to pan. **Preview edges**
   overlays strong edges as an aid; noise and out-of-focus boundaries can also
   appear. This is not calibrated focus peaking. If the camera advertises a focus
   magnifier, its additional buttons request a camera-generated magnified view from the
   camera, which provides more useful focus detail than enlarging a small JPEG.
7. Use **Go to mark** to inspect each end after approaching it in the planned
   capture direction. This matters: the physical tests found approach dependence.
   Leave some subject-depth margin at both boundaries. An insufficient approach
   range is refused rather than clamped at a lens limit.
8. Leave **Focus step = 1** for the smallest available command; **Settle = 500 ms**
   is the starting default used in the physical tests. Some adjacent commands
   repeat physical focus. The measured roughly threefold finer response than
   native width 1 does not make every unit a distinct focal plane. The UI shows
   the actual commanded RAW count, including both endpoints. A last interval may
   be shorter than the selected step. There is no 299-frame native-bracket limit.
9. **Start stack**; **Pause** waits for the active operation, and **Resume**
   continues at the next operation. **Stop** completes the active operation and
   prevents future exposures. It leaves completed RAWs on the card. The capture
   timeout defaults to 120 seconds per exposure; increase it for long exposures
   plus camera processing. No shutter is automatically retried after an error.

Start with a short stack to confirm the new live preview on the laptop. The
underlying SDK capture/focus path has the owner's two physical tests; this new
live-view UI and magnifier have only software/simulator verification so far.
`try-demo.cmd` opens a clearly marked simulator without loading the Sony SDK.

## Optional preview survey

Mark rough A/B limits extending beyond the visible subject depth. At **Fit**,
choose **Select subject**, then drag a rectangle around the subject. **Sweep
preview** visits at most 33 positions in that range, with no RAW exposures. It
uses the median of three distinct fresh previews at each position, after
discarding the first changed frame. Keep the camera magnifier off for the survey.

The suggested limits include margins around broad local texture peaks. **Apply
suggested bounds** is separate from capture and never starts a stack. Inspect
both limits using **Go to mark** before starting. If a supported peak reaches a
search limit, the app retains the full range and asks for wider rough limits.
Flat/noisy scenes can produce no suggestion. Breathing, preview sharpening,
lighting changes, reflective objects, a textured background and weak subject
features can mislead this heuristic. It is a convenience aid, not a guarantee of
complete subject coverage or a metric depth estimate.

## Metadata beside the RAWs

By default, local journals are under `%LOCALAPPDATA%/Strehl/Capture/stack-*`.
**Approach, timeout & storage** lets you choose another writable journal folder.
Each run has `manifest.json`, append-only `events.jsonl`, and `result.json` when
it finishes or stops. They contain planned positions, focus readbacks, exposure
settings, camera identity, application/bridge hashes, timestamps, capture intents
and acknowledgements. Intent is flushed to disk before each shutter command.

Sony's documented remote APIs do not provide an arbitrary sidecar-file upload to
the card. After disconnecting, mount the SD card in a reader and choose **Copy
metadata to SD…**. Pick the card or the RAW folder; the app writes a fresh
`STREHL/stack-*` subfolder. It neither copies nor modifies photographs and refuses
to overwrite an existing journal export. The local copy is retained.

This backend knows capture ordinals, not camera-generated filenames or verified
file checksums. Use a fresh camera folder or note the first/last filenames; avoid
unrelated manual exposures during a run. Check the SD file count afterward.
An interrupted run with a `capture_intent` but no corresponding completion is
uncertain; inspect the card before starting another run. Automatic recovery after
an application/USB failure is deliberately unavailable. Journals are supplemental:
Strehl currently imports the ordinary RAW folder and does not automatically bind
or consume this new journal schema.

## Build and verify

From the Strehl repository (Rust 1.98.0 and Windows C++ Build Tools):

```powershell
./tools/sony-control/build.ps1
cargo build --locked --release -p strehl-capture -j 2
cargo run --locked -p strehl-capture -- --bridge outputs/sony-control/bin/strehl-sony-control.exe
```

The private portable packager builds from its own copied source snapshot:

```powershell
python tools/sony-control/package-capture.py --out outputs/sony-capture-ui/strehl-capture-win-x64
```

Focused verification and real offscreen UI controls:

```powershell
cargo test --locked -p strehl-capture -j 2
cargo clippy --locked -p strehl-capture --all-targets --no-deps -j 2 -- -D warnings
cargo fmt -p strehl-capture -- --check
python scripts/strehl-capture-control.py --exe target/debug/strehl-capture.exe exercise --out outputs/sony-capture-ui/fresh-ui-check
python scripts/strehl-capture-control.py --exe target/debug/strehl-capture.exe screenshot --png outputs/sony-capture-ui/fresh-preview.png --size 1280x720
```

The control helper always uses the simulator. It sends egui input to the actual
rendered UI and uses a wgpu texture readback, with no desktop automation or
camera connection. Camera commands have a single worker owner; the UI stays
responsive while the bridge waits. Preview buffers and reply lengths are bounded.
This package is for the owner's supplied Sony SDK and is not an official public
Strehl release. Keep its source and third-party notices with the binaries.

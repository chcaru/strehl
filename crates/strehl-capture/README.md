# Strehl Capture

A Rust capture workspace for the Sony A7C II (`ILCE-7CM2`), with a Windows
desktop app and a headless Raspberry Pi service.
It uses Strehl's native palette and a small original C++ bridge for Sony's C++
SDK ABI. The UI, sequence engine, preview analysis and durable journal are Rust.
The capture executable does not link the RAW decoder or stacking engine.

**The desktop app keeps RAWs on the camera SD card.** Only transient live-view JPEGs reach the
viewer; they are not saved. Captures are single RAW exposures, each acknowledged
before the next focus move. A7CR/pixel-shift capture is not enabled in this build;
see the [separate feasibility answer](../../experiments/sony-capture-ui-2026-11-07/a7cr-sequencing.md).

The optional [Pi capture service and PC receiver](../../docs/pi-capture.md)
use a different, explicit storage mode: full-resolution Lossless Compressed RAW L
passes through unswappable Pi RAM to the PC over the local network. A bounded
four-file queue overlaps uploads with subsequent captures. The UI separates
captured from saved counts; pause, stop and completion drain the queue, with
checksum-verified, flushed PC files required before success. RAWs are not stored on
either the camera card or the Pi microSD in this mode.

The Pi and receiver automatically negotiate lossless transport compression.
CFA-aware or generic Zstd coding reduces network bytes while restoring the exact
original ARW on the PC. Retries retain the RAM source until durable verification;
older receivers use the original transfer format. The browser shows effective
RAW MB/s and byte savings. See the [production qualification](../../experiments/sony-transport-2026-11-12/results.md)
for measured rates, memory bounds and failure tests.

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
   determine near/far visually for your lens. Manual marks remain available when
   the preview fails: inspect focus on the camera display, then mark the reported
   position. Jogging and capture do not depend on decoding a preview.
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
10. The plan shows a rough **Initial estimate** from shutter speed, settling and
    camera/SD overhead. During capture, the footer shows **elapsed time and an
    estimated countdown**, updated from completed capture cycles. Pausing freezes
    active time and the countdown; stop/error freezes the elapsed total. The
    estimate is approximate, especially before the first few completed RAWs.

Start with a short stack to confirm the new live preview on the laptop. The
underlying SDK capture/focus path has the owner's two physical tests; this new
live-view UI and magnifier have only software/simulator verification so far.
`try-demo.cmd` opens a clearly marked simulator without loading the Sony SDK.

### Recover after a camera error

If focus information, a focus move or a capture fails, **Camera needs attention**
shows the error and the number of confirmed captures in both the desktop and
browser. Check the lens/USB connection and camera display, then use **Reconnect
camera**. There is no need to close the app. If the previous connection is still
finishing an operation, wait for the camera/card to become idle and retry that
button. The app waits for the old connection to release before opening another.

Reconnecting does not take a photo. It keeps the previous RAWs, journal and
confirmed count. A/B marks are retained when the camera reports the same identity;
review both with **Go to mark**, especially if you touched the lens or camera.
**Start stack** then begins a new run from A with a new journal; it does not resume
or overwrite the failed run. Ordinary Disconnect clears the focus marks.

If a shutter was sent but its completion could not be confirmed, the last RAW
may already be on the card. Wait for camera/card activity to finish, inspect that
exposure, and tick the acknowledgement beside Reconnect. This check is required
only for an uncertain exposure; focus-information failures alone do not need it.
The app never retries a shutter automatically.

## Control from a phone or another computer

1. On the camera laptop, open **Web remote → Enable web remote**. Choose
   **Nearby · local network**, then scan its QR code with your phone, or use
   **Copy pairing link** and open that link in another browser. Both devices must
   be on the same reachable LAN/Wi-Fi. Guest Wi-Fi may isolate devices.
2. The page includes live view, zoom, camera magnifier when available, focus
   jogging, A/B marks, subject selection, preview survey, step/settle settings,
   Start/Pause/Resume/Stop, and the countdown. Focus step still defaults to **1**.
   Desktop and browser use the same camera session and shared marks/settings.
3. If the browser closes, the phone sleeps, or Wi-Fi drops, the sequence keeps
   running on the laptop. Pairing is remembered by this browser; reopen the same
   page to reconnect and see its progress. Commands
   whose replies are lost are not automatically retried; check the current
   status before acting again. A stale plan or duplicate Start is refused.
4. Keep the laptop awake, powered, connected to the camera and running Strehl
   Capture. Disabling web remote revokes its links without stopping the stack;
   closing Strehl Capture stops the sequence cooperatively. A new remote session
   creates a new pairing key. Treat the pairing link as access to camera control.

**Long stacks:** pairing has no inactivity or elapsed-time limit. A temporary
network failure or authorization rejection keeps the saved key and retries
read-only status requests automatically, including after the phone wakes.
Progress while offline is labelled **last confirmed**, and camera controls stay
disabled until the connection is verified. Camera commands are never retried
automatically. A late reply from an earlier pairing attempt cannot sign out a
newer pairing.

If repeated rejections require attention, the page offers **Retry saved pairing**
and a field for the current pairing link while retaining the last confirmed
progress. Copying that link from the laptop's Web remote panel does not stop a
stack. Do not disable/re-enable Web remote to copy it: doing so revokes the key.
An identified server restart/revocation is reported separately from connection
loss. **Forget this browser** removes its stored pairing and updates its other
open tabs; it does not stop capture. LAN and HTTPS addresses each remember their
own pairing. If persistent browser storage is unavailable, the page falls back
to tab storage or memory, so reopening may require the link again.

For an update during a capture, let that stack finish before closing/replacing
the laptop application. The website's assets are embedded in the executable;
installing an update requires a later app restart and a new pairing link.

**Access while away:** install [Tailscale](https://tailscale.com/docs/how-to/quickstart)
on the camera laptop and your phone/other computer, and sign in to the same
Tailscale account. Connect both devices to Tailscale. In Strehl Capture, enable
web remote and select **Away · Tailscale**; scan/copy that pairing link. If you
installed or connected Tailscale after enabling the remote, disable and re-enable
web remote so it discovers the new address. This is a private website served by
the laptop; there is no cloud site to deploy or router port to forward. The
Tailscale connection carries the HTTP traffic through the encrypted private VPN.
Local-network HTTP uses the pairing key but does not itself encrypt traffic.

If Windows Firewall blocks the connection, allow **Strehl Capture** on your
private network when Windows prompts. The package also includes
`allow-web-remote.ps1`: open **PowerShell as administrator** in the extracted ZIP
folder, then run `powershell -NoProfile -ExecutionPolicy Bypass -File .\allow-web-remote.ps1`.
This optional helper allows only this executable on TCP port **8787**, from the
local subnet and Tailscale's IPv4 range. It does not turn off the firewall.
Rerun from the new folder if you move the package. Custom firewall/managed
network policies may still require local configuration. The helper prints the
rule name if you later want to remove that rule in Windows Firewall.

Try the away link with your phone's Wi-Fi off and Tailscale connected before
leaving the laptop unattended. Software/simulator checks exercise HTTP control
and browser reconnection; an actual away connection and physical-camera remote
capture still need this check on your devices.

The server starts only when enabled, listens on port 8787, and accepts local,
LAN or private-VPN clients with a per-session pairing key. It exposes embedded
page assets, session state, transient preview JPEGs and bounded camera commands.
It has no filesystem browser, RAW download, metadata export or shell endpoint.
Metadata export to an SD reader remains a desktop action. If another application
uses that port, start with `Strehl-Capture.exe --web-bind 0.0.0.0:8788` and adjust
your firewall rule to match. All page assets are bundled; no CDN is required.

### Android Chrome cannot reach the local address

If the page loads on another computer but Android Chrome shows
`ERR_TOO_MANY_RETRIES`, check **Android Settings → Apps → Chrome → Permissions →
Nearby devices → Allow**, then reopen the HTTP link. Android's local-network
permission belongs to the Nearby devices group on recent versions. The owner
confirmed that this resolved access from `10.0.0.13` to the camera laptop at
`10.0.0.7`. This symptom did not require changing the camera server or firewall.
See [Android's local-network documentation](https://developer.android.com/privacy-and-security/local-network-permission).

### Corporate laptop cannot install Tailscale

A separate personal PC on the LAN can relay just the existing camera website
through a [Cloudflare Quick Tunnel](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).
That is a fallback requiring both PCs to stay awake. It needs explicit approval
to carry live preview/control traffic through Cloudflare; it is not a method for
overriding corporate installation or network policy. A laptop-only arrangement
depends on an outbound remote-access method permitted on that laptop.

The prepared personal-PC helper is `tools/sony-control/away-relay.py`. It uses
a pinned, SHA-256-verified official connector, verifies the camera pairing gate
before starting, retains ownership information for stopping its process, and
never reads the camera's pairing key or sends camera commands. The accompanying
`package-away-relay.py` creates start/stop/status launchers for the personal PC.
Python is needed for this helper; the capture application itself still does not
require Python. The helper downloads its connector directly from the official
release instead of redistributing it in the helper ZIP.

Open the relay's HTTPS link, then paste the camera app's full **Copy pairing
link** into the pairing field. Keep the pairing key out of the connector's
target URL and logs. RAWs remain on SD; transient preview/control traffic passes
through Cloudflare, while the relay-to-camera hop uses LAN HTTP. The generic
pairing page is public; every camera API request requires Strehl's key.
Quick Tunnels are temporary development relays without an uptime guarantee;
the hostname changes on restart. Loss of the relay does not stop an active stack.

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
python experiments/sony-capture-ui-2026-11-07/verify-web-remote.py --exe target/debug/strehl-capture.exe --out outputs/sony-capture-ui/fresh-web-check
```

The control helper always uses the simulator. It sends egui input to the actual
rendered UI and uses a wgpu texture readback, with no desktop automation or
camera connection. Camera commands have a single worker owner; the UI stays
responsive while the bridge waits. Preview buffers and reply lengths are bounded.
The browser check requires Python Playwright and Microsoft Edge. It launches a
bounded, loopback-only `--demo --web-test-session` server, exercises desktop and
phone-sized browsers, and removes its temporary pairing key when done. It does
not connect physical hardware or change firewall/VPN settings.
This package is for the owner's supplied Sony SDK and is not an official public
Strehl release. Keep its source and third-party notices with the binaries.

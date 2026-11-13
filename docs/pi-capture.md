# Raspberry Pi capture and PC RAW receiver

Strehl Capture can run headlessly on a Pi 5 and use the existing phone/browser
focus controls. This path currently targets the Sony A7C II, single exposures,
and full-resolution **Lossless Compressed RAW L**. A7CR and pixel-shift sequencing
are not enabled. The Windows desktop app's default remains camera-card saving.

## Running the prepared installation

1. Power the Pi with its own supply. Connect the Sony camera to a blue USB-A port
   using the USB data cable. Power the camera separately with the selected
   SmallRig NP-FZ100 adapter. Select **Remote Shoot / PC Remote** on the camera;
   close other camera-control applications.
2. Keep the PC receiver running. Its **Receiver settings** shortcut opens the
   configurable capture folder. The default for this installation is
   `D:\StrehlCaptures`. **Start receiver.cmd** and **Stop receiver.cmd** live in
   `%LOCALAPPDATA%\StrehlCaptureReceiver`. Stop the stack before stopping the
   receiver. Closing the settings browser does not stop the receiver.
3. Open the saved **Pi camera control** pairing link. The normal address is
   `http://10.0.0.187:8787/` for this installation (`strehl.local` where local
   name resolution works). The persistent key in the saved link is required;
   the bare address shows a pairing form. Open the same pairing link on the
   phone using **Copy pairing link** in the controller. Android Chrome may
   require **Nearby devices** permission for LAN access.
4. Connect the camera, use fixed exposure/ISO/WB, inspect the live preview, jog
   focus and mark A/B. Focus step 1 remains the smallest command, with 500 ms
   settling by default. Start with three to five planes before a long stack.
5. Start, pause, resume and stop work through the shared sequence owner. Pause
   and stop finish the active exposure and drain queued transfers. The display
   distinguishes **captured** from **saved on PC**, and shows upload speed and
   pending files. The initial time estimate is rough; measured cycles teach it
   the actual cadence, with a finishing phase for the final uploads.

The Pi service starts automatically at boot; it never starts exposures by itself.
The receiver keeps the PC awake while it runs, while allowing the display to
sleep. This installation now starts the receiver automatically at Windows
sign-in, as approved by its owner. The PC must be signed in and awake to receive.

The prepared installation accepts only `10.0.0.0/24` and loopback clients. It uses
no relay, VPN, cloud endpoint or router port forwarding. The receiver currently
uses this PC's LAN address, `10.0.0.109:8789`; reserve that address in the router
or update `/etc/strehl-capture/headless.json` if it changes. Settings and pairing
keys are private installation data, excluded from source packages and commits.

## File handling and failure behavior

The Sony SDK finishes one `.ARW` in `/run/strehl-raw`, a dedicated 512 MiB tmpfs
mounted with `noswap`. The bridge refuses a disk-backed destination. Swap
generators are disabled, service swap and core dumps are disabled, and service
temporary directories also use unswappable RAM. The Pi microSD holds software
and small journals, never the intended RAW spool.

The receiver writes a temporary file on the selected PC disk, validates byte
length and SHA-256, flushes it, and commits it without overwriting an existing
RAW. An identical retry is acknowledged without creating a duplicate. The Pi
persists the PC receipt before deleting its RAM copy. A background uploader
overlaps PC delivery with the next focus move and exposure. At most four
completed RAWs await acknowledgement; before another exposure the controller
also reserves 256 MiB plus headroom in the 512 MiB RAM mount. A full queue or a
reported connection failure prevents the next exposure. Unexpected unbound
files in that directory stop capture for inspection.

The SDK still finishes each complete RAW in RAM before that file is uploaded.
Only one camera operation and one upload run at once. The uploader holds one
additional bounded original byte body in RAM, plus bounded compression buffers.
Four workers encode independent chunks while HTTP delivers earlier chunks. A
Linux available-memory check reserves encoder workspace and headroom before
another exposure, in addition to checking the RAW tmpfs capacity.
Journal snapshots are coalesced in memory; original capture intents and
per-file pending bindings remain durable on the Pi microSD. Completion is
reported only after every queued RAW and the final metadata are acknowledged.

Each stack has its own folder containing `frame-000001.ARW`, subsequent frames,
`manifest.json`, `events.jsonl`, `result.json` and `transfer-receipts.jsonl`.
`capture_buffered` events bind focus commands to filenames, lengths and
checksums; they confirm RAM acquisition, not durable PC delivery. PC receipts
confirm the latter. Exposure
metadata stays in the original ARW. Automatic lossless **transport compression**
reduces bytes sent over Wi-Fi; the receiver reconstructs and hashes the entire
original file before acknowledging it. No pixels, metadata or original camera
compression are changed, and the PC disk still holds original-size ARWs. There
is no demosaicing on the Pi. Changing the destination folder applies to future stacks; an active
stack retains its original folder across receiver restarts.

The sender uses CFA-aware prediction plus Zstd for supported uncompressed RAW
layouts and generic Zstd for camera-compressed or unfamiliar layouts. Chunks
that would grow are sent as original bytes. The receiver advertises support;
older receivers continue using the existing identity transfer. Chunk dimensions,
decoded/wire lengths, checksums and trailing bytes are checked before commit.
Interrupted uploads rebuild a complete stream on retry, including duplicate
validation after a lost acknowledgement. Original Pi RAM copies remain until
the verified durable receipt has been recorded.

The camera page shows **RAW MB/s**: original file bytes divided by the successful
upload attempt's encoding/transfer/receiver time. This is an effective RAW rate,
not Wi-Fi link speed or exposure cadence. **Fewer bytes** reports transport
savings, which vary with scene, noise and the camera's original compression.
Refresh an already-open camera page after installing this update to see the new
labels. Existing pairing links and capture-folder settings remain valid.

Wi-Fi/receiver failures retry delivery, never the shutter. A transfer that cannot
finish enters recovery with its queued RAWs retained in RAM. Restore the receiver
and use **Reconnect camera**; delivery of recorded pending files is retried
before another camera session starts. Review the focus marks before explicitly
starting a new stack. A pending file without a matching receipt is not silently
discarded. An interrupted SDK download without a completion record requires
inspection before reconnecting.

Because RAWs have no persistent Pi/card backup, loss of Pi power before the PC
acknowledges a file can lose that exposure. A checksum verifies transport bytes;
it is not a photographic-quality or complete-RAW decode test. Real-camera
qualification must include an independent decode, dimensions/compression check,
matching counts, a network interruption and a longer run.

## Build and provisioning

The headless binaries avoid the desktop GPU dependencies:

```powershell
cargo build --locked -p strehl-capture --no-default-features --release --bins
cargo test --locked -p strehl-capture --no-default-features
cargo clippy --locked -p strehl-capture --all-targets --no-deps -- -D warnings
cargo fmt -p strehl-capture -- --check
```

`tools/sony-control/build-pi.sh` cross-compiles the original SDK bridge and Rust
service for `aarch64-unknown-linux-gnu`. It takes the repository root, extracted
Sony ARM64 SimpleCli SDK directory, output directory and optional mounted Pi OS
root for the linker's runtime-library search. It requires the AArch64 GNU C++
toolchain, CMake, Rust 1.98 and the ARM64 Rust target. The Sony SDK is supplied
separately by its owner; its runtime layout and notices are preserved.

`provision-pi.py` only configures an already mounted image on a Linux loop device.
It installs Wi-Fi settings supplied through the local password form, SSH public
key access, USB permissions, RAM mounts and systemd services. It does not write
physical disks. `write-pi-card.ps1` is the separate Windows administrator helper:
it rechecks the specifically authorized F: disk identity/size/USB/non-system
status and image checksum, locks the volume, writes it and verifies a full image
readback. Its manifest and result identify the exact target and bytes written.

## Verification for the initial port

**VERIFIED:** 26 Rust tests passed, including real HTTP transfer, wrong-checksum
and short-upload rejection, overwrite refusal, retry idempotence, and recovery
between RAM deletion and intent deletion. Desktop and headless static checks
passed. Both Windows and ARM64 bridges passed 19 card-completion and 9 preview
assertions. QEMU using the actual Pi OS libraries loaded the ARM64 SDK and USB
adapter and completed enumeration without an attached camera.

**VERIFIED:** `tools/sony-control/verify-pi-ui.py` exercised the actual HTTP
servers and phone-sized browser: JPEG preview, focus marks, start/pause/resume/
stop, persistent pairing across controller restart, receiver folder changes and
a 64 MiB transfer fixture with PC-disk hash readback. A fixture is not a camera
RAW. Evidence is under `outputs/pi-capture-2026-11-11/`, including
`ui-check-01/verification.json`, screenshots, ARM64 loader results and the card
write receipt. The installed receiver endpoint and visible interface were also
checked. The customized image passed ext4/FAT checks and card readback SHA-256.

**VERIFIED on the physical Pi 5 and A7C II:** Wi-Fi reconnected after reboot;
Ethernet was disconnected for camera qualification. The RAW mount reports
`tmpfs,noswap`, system swap is absent, and power diagnostics reported
`throttled=0x0`. A 64 MiB synthetic transport fixture bound explicitly to
`wlan0` reached the installed PC receiver in 3.857 seconds (16.59 MiB/s), with
PC-disk readback SHA-256 matching. This measures that one transfer, not camera
capture cadence or guaranteed Wi-Fi performance.

Two three-plane stacks at focus commands 34970–34972, step 1, completed over
Wi-Fi. Live JPEG preview decoded at 1024×680. Pause/resume held the first run at
one confirmed RAW. During the final run, stopping the receiver prevented the
first exposure; restarting it allowed the same run to finish with three RAWs
and a cleared recovery status. The second run took 14.10 seconds of measured
active time, excluding its initial receiver wait. Six files passed independent
`rawpy 0.27.0` decode and receipt/hash/length checks, with a 7028×4688 visible RAW
array. Camera settings read back RAW type 2, Lossless L compression 5, host-only
destination 1, ISO 100, f/5.6 and 1.6-second exposures. These were dark-frame
transport tests, not image-quality or focus-resolution evidence. The SDK did not
report camera-card remaining count in host mode; no card filesystem inspection
is claimed. The Pi RAM buffer was empty after delivery.

Physical evidence includes `physical-raw-verification.json`,
`pi-receiver-recovery-result.json`, `final-raw-verification.json`,
`pi-wifi-transfer.json`, and `pi-after-reboot.jsonl` under the dated output folder.
The test stack folders are `D:\StrehlCaptures\stack-1794459224880-641` and
`D:\StrehlCaptures\stack-1794459734209-822`.

A third three-plane stack used an illuminated subject at focus commands
37335–37337. Its three Lossless RAW L files were about 35.8 MB each; all passed
independent full-resolution decode, byte-count and receipt SHA-256 checks. The
run took 16.85 seconds of active time. The actual camera preview and a complete
decoded RAW overview showed the same subject, and the phone-sized browser
displayed the live JPEG correctly. This verifies usable image transport, not
optical quality. The output is
`D:\StrehlCaptures\stack-1794460247102-822`; evidence is
`illuminated-stack-verification.json` and `physical-illuminated-phone.png`.

An SDK property-read error (`0x8402`) occurred during the subsequent reconnect.
The browser's **Reconnect camera** button recovered the session without a
service restart or additional exposure. The camera was left ready with a fresh
preview, its starting focus restored, and test marks cleared. This intermittent
connection error remains a known qualification finding, not a resolved cause.

Qualification caught and fixed two issues: NetworkManager's saved radio-off
state overriding an early `rfkill` command, and a recovered transfer leaving a
stale waiting message. Provisioning now enables Wi-Fi after NetworkManager;
duplicate uploads consume and validate their request body before acknowledging
it, and successful retries clear the waiting state. The running Pi was updated
over SSH. The original card-write receipt remains a record of the initial
flash; `updated-image-receipt.json` describes the refreshed recovery image.

**UNVERIFIED:** multi-hour stability and sustained performance with larger,
more detailed scenes. No improvement in optical resolution or image quality is
claimed by these transport tests.

## Wi-Fi diagnosis and capture overlap, 2026-11-11

**MEASURED:** the studio Pi reported 5 GHz, a 433.3 Mbit/s link, about -53 dBm
signal, power saving off and a DDR50 SDIO connection. The PC used 1 Gbit/s
Ethernet; its Qualcomm Wi-Fi 7 adapter was disconnected. Camera USB negotiated
5 Gbit/s. CPU load was low in the diagnostic snapshot and no power throttling
was reported. These link rates are not application transfer rates.

`python outputs/pi-capture-performance-2026-11-11/bench-network.py` ran iperf3
3.18 with 12-second measurement windows and two warm-up seconds. Pi-to-PC TCP
achieved 235.7 Mbit/s with one stream and 238.5 Mbit/s with four; PC-to-Pi was
222.6 Mbit/s. The client ran in WSL on the wired PC. A separate 35.8 MB HTTP
retry of an unchanged existing RAW achieved 23.2–24.5 MB/s, excluding a new
disk write. Receiver loopback tests with a 64 MiB fixture, SHA-256 and durable
disk acknowledgement achieved 736–1013 MB/s on this PC's C: workspace drive. That
separates the receiver from the radio limit; it is not a claim of camera speed.

`python -X faulthandler outputs/pi-capture-performance-2026-11-11/qualify-stack.py baseline`
and the same command with `overlap` captured six planes each, with matching
2-second exposures, ISO 100, f/5.6, step 1 and 500 ms settling. Baseline active
time was 30.97 seconds, with a 5.00-second mean interval. Overlap active time
was 24.03 seconds, with a 3.62-second mean interval. The final upload measured
24.77 MB/s. Each of the twelve RAWs passed independent full-resolution decode
and PC receipt/hash checks. **DERIVED:** 27.7% shorter steady intervals, or
38.2% more frames per unit time, in this short comparison. Whole-run improvement
is smaller because setup and final delivery still take time. This was an
engineering qualification, not a multi-hour or broadly controlled benchmark.

`qualify-queue-recovery.py` then suspended the owned receiver process during a
physical run. The queue held at four files (five captured, one saved), with no
additional exposures while full. The actual phone-sized browser's Stop control
stopped capture; restoring the receiver delivered all five files. A subsequent
three-frame run paused with all pending uploads drained, resumed, and completed.
All eight files independently decoded and matched their receipts. The camera
was reconnected and the test marks cleared. `queue-recovery.json` and
`phone-buffer-full.png` record the result. No synthetic upload fixture is counted
as a camera RAW.

The overlap build passed 27 Rust tests, including a real stalled HTTP receiver,
four-file capacity, metadata coalescing, per-file crash recovery and corrupted
RAW retention. The matching native bridges passed their 19 card-gate and 9
preview assertions. Initialization now waits for required SDK properties to be
readable before configuring the camera; subsequent physical reconnects passed.

## Production compression, 2026-11-12

**VERIFIED / DEPLOYED:** the Pi service and Windows receiver now use the exact
streaming codec automatically. Both build configurations passed 31 Rust tests;
the installed HTTP receiver rejected nine malformed/interrupted controls. Three
new real camera RAWs passed full-file hash receipts and independent decoding;
focus and unset bounds were restored. Browser checks verified preview, controls
and displayed compression savings. Receiver sign-in startup was preserved.

**MEASURED:** a 123 MB A7R IV reference RAW took 1.18-1.51 seconds through the
production transfer call with compression, versus 1.99-2.25 seconds with identity;
wire bytes fell to 54.5 MB. The tested dark A7C II RAW fell from 33.2 MB to 18.5 MB
on the wire. These are short tests of specific files, not universal ratios or an
A7CR hardware result. See the [integration report](../experiments/sony-transport-2026-11-12/results.md)
for commands, bounds, negative controls, environment, rollback copies and limits.

# Native Capture integration

## Outcome

**VERIFIED:** Strehl has a native Capture rail tab with Pi live view, display
zoom, subject ROI, focus jog/marks/go, minimum-step settings, bounded focus survey,
camera magnification controls, start/pause/resume/stop, timers, transfer status,
PC destination/compression settings and completed-stack import. It uses egui and
the existing authenticated LAN camera API. There is no embedded browser.

The same Strehl executable hosts the receiver with
`--capture-receiver --config PATH`, using the shared receiver runtime. Its process
survives closing the editing window. Existing phone control and the Pi camera
owner are unchanged. Camera commands carry the revisions observed when requested;
an unanswered mutation is not automatically replayed.

**VERIFIED:** Desktop discovery and camera JPEG browsing now accept `.ARW.straw`.
Both reject duplicate original/archive observations. Archived previews use the
existing verified in-memory original-byte reader, with lazy opening so a cached
JPEG does not require another complete RAW decompression. No restored RAW file is
created. Completed handoff requires a registered run, a complete durable result,
every expected pixel-shift member's receipt, and matching stored lengths.
Archive reading separately verifies the original checksum.

## Final artifact and environment

- Package: `outputs/strehl-desktop-native-capture-2026-11-13-ready/`.
- Build: `desktop-1280e2a4549036fb`.
- Source manifest SHA-256:
  `1280e2a4549036fb2666efa244ba0cc5a9e35a7adeb7edea5d3b7e568ad303f4`.
- `Strehl.exe` SHA-256:
  `87d69ec026c8072455c4e8e95086964e48ce62c1f9f82644b7ed018388928374`.
- Windows x64; Rust 1.98.0; native egui/wgpu offscreen rendering. Test concurrency
  was two threads for the complete desktop suite, one for focused client tests.
  No image reconstruction or photographic performance comparison was run.
- The packager builds a frozen source snapshot and delivers its source/relink
  route, lockfile and decoder notices. All manifest inputs matched the working
  source after final build. Credentials, captured RAWs and unrelated work are
  excluded from the source commit and package.

Build command actually run:

```powershell
./scripts/package-desktop.ps1 -Destination ./outputs/strehl-desktop-native-capture-2026-11-13-ready -TargetDirectory ./target-ui
```

## Verification

**VERIFIED, automated:**

```powershell
cargo test --locked --offline -p strehl-ui -- --test-threads=2
cargo test --locked --offline -p strehl-capture --no-default-features
cargo clippy --locked --offline -p strehl-ui -p strehl-capture --all-targets --no-deps -- -D warnings
cargo fmt -p strehl-ui -p strehl-capture -- --check
```

The desktop suite passed 1,041 tests with 15 existing opt-in tests ignored; the
capture library passed 33. The final connected-label and initial receiver-status
polish was subsequently rebuilt, linted and exercised with native rendering and
the lifecycle harness. Focused controls exercised incomplete pixel-shift receipt
sets, truncated files, stopped results, duplicate original/archive inputs,
corrupted archive checksums, off-LAN addresses, stale native snapshots and a lost
HTTP acknowledgement without replaying the exposure. Python helpers also passed
`py_compile`; the repository has no separate unittest suite for the control helper.

**VERIFIED, final native service lifecycle:**

```powershell
python experiments/native-capture-2026-11-13/qualify-lifecycle.py --exe outputs/strehl-desktop-native-capture-2026-11-13-ready/Strehl.exe --out outputs/native-capture-2026-11-13/lifecycle-ready
```

An isolated simulator exercised native receiver start, compression off/on,
focus marks/jog/settings, capture/pause/resume/stop/restart and completed state.
The receiver still answered after the native workspace exited. The harness then
stopped only its own simulator and uniquely identified test receiver. Native
screenshots at 1440 × 940 and 1100 × 760 were inspected. These are functional
simulator checks, not physical-camera timing or image-quality evidence.

**VERIFIED, real A7CR and EDUP Wi-Fi:** The installed final executable drove one
four-shot group at focus 37180, saved four compressed RAW members in
`D:\StrehlCaptures\stack-1794618614613-9932`, reached zero pending uploads and
imported all four into an isolated Projects catalog. The test restored the camera
to ready at focus 37180 with the test bounds cleared. No exposure/aperture/ISO
settings were changed. The existing production receiver remained running.

```powershell
python scripts/strehl-control.py --exe outputs/strehl-desktop-native-capture-2026-11-13-ready/Strehl.exe --session-file outputs/native-capture-2026-11-13/ready-session.json launch --capture --capture-settings C:\Users\chris\AppData\Local\Strehl\capture.json --output-dir outputs/native-capture-2026-11-13/ready-processing --wait
python experiments/native-capture-2026-11-13/qualify-native.py --exe outputs/strehl-desktop-native-capture-2026-11-13-ready/Strehl.exe --session-file outputs/native-capture-2026-11-13/ready-session.json --out outputs/native-capture-2026-11-13/ready-live --action one-plane
python scripts/strehl-control.py --exe outputs/strehl-desktop-native-capture-2026-11-13-ready/Strehl.exe screenshot --capture --capture-settings C:\Users\chris\AppData\Local\Strehl\capture.json --png outputs/native-capture-2026-11-13/ready-native-live.png --size 1440x940 --output-dir outputs/native-capture-2026-11-13/render-output
python scripts/strehl-control.py --exe outputs/strehl-desktop-native-capture-2026-11-13-ready/Strehl.exe screenshot --source D:\StrehlCaptures\stack-1794618614613-9932 --png outputs/native-capture-2026-11-13/ready-projects-archives.png --size 1440x940 --output-dir outputs/native-capture-2026-11-13/render-output
```

Complete native previews of all four archived files were inspected. Every test
workspace used a separate catalog/output folder and was shut down through the
control helper, with exit confirmed. An earlier development run successfully
captured four files but exposed the desktop's old `.arw` filter; that failure
motivated the discovery/preview integration above. Intermediate simulator harness
failures (non-hex fixture key and null initial receiver state) were corrected and
rerun. Earlier screenshots also caught an unknown-model label and premature
receiver-status rendering; final screenshots include both fixes.

## Installation and preserved state

`install-native.ps1` installs native pairing preferences and a **Strehl Capture**
desktop shortcut. It backs up existing receiver launchers/configuration and
retargets the already-authorized sign-in launcher to the integrated receiver.
An active receiver is attached without termination. Existing per-run destination
and compression choices remain byte-identical. A separate administrator script
installed and read back a firewall rule for this exact executable, TCP 8789 and
`10.0.0.0/24`; it did not broaden existing rules or expose an internet relay.

Private installation backups and credentials remain under the ignored local
output tree. The tracked/untracked source preservation receipt predates edits;
the unrelated `experiments/ca-before-mhc/gpu.rs` hash remains
`56870cbff57787d388ea42e8fe129b53ebcbc8a38e396fc91c5c3e03904e9af7`.

## Limits and next stage

**UNVERIFIED:** a fresh Windows sign-in/reboot, multi-hour capture through the
native workspace, physical-camera survey/magnification changes in this turn,
power-loss recovery and Linux/macOS desktop deployment. A complete capture already
received by the old service was not interrupted merely to replace its process.
The final integrated service was independently exercised on a test receiver.

**Not implemented in this stage:** incremental stacking/development during
capture or dedicated pixel-shift reconstruction. Opening a complete group in
Projects does not assert a super-resolution result. Per-plane journals, member
identity and durable receipts remain available for the next streaming stage;
that stage must distinguish provisional observations from a fully finalized
stack and handle incomplete groups explicitly. No optical or quality improvement
is claimed by this UI integration.

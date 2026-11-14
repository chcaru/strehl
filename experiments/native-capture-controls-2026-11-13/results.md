# Native capture controls qualification

## Result

**VERIFIED:** The native Capture workspace and phone controller expose focus
scrubbing, JPEG focus peaking, single/four-shot selection and mode-aware duration
and storage estimates. Native phone pairing has a QR with a four-module quiet
zone. The permanent yellow subject rectangle is removed. Shared native dropdowns
have bounded button and popup widths throughout the application.

**VERIFIED:** Whole-stack disk admission runs before focus movement or shutter
release, including API requests. The controller rechecks the registered
destination before subsequent planes. Unknown capacity refuses capture. The
budget includes every pixel-shift member, the backend RAW ceiling, framing and
receipt allowance, and 512 MiB headroom. Compression savings are deliberately
excluded; this can reject a stack whose eventual compressed files would fit.

## Build and inputs

- Windows x86-64, Rust 1.98.0; desktop build `desktop-55c0fc330e607669`.
- Source manifest SHA-256:
  `55c0fc330e607669c47ad68302591684d2a7d8eaa7293e8aa3b274d03617f81a`.
- Desktop executable SHA-256:
  `540bd70b3a1073a6494aeba28ab15e3a40883908267bba1ad6962387fceb5abb`.
- Pi 5 ARM64 controller and bridge hashes, sanitized receipts and assertions:
  [evidence/qualification.json](evidence/qualification.json).
- Real ILCE-7CR on the existing LAN Pi, streaming uncompressed camera RAWs through
  exact CFA transport to the existing PC receiver, retaining `.ARW.straw` archives.
  No camera card or persistent Pi RAW staging was introduced.
- Camera qualification used one focal plane per mode, step 1, 500 ms settle,
  approach 128 and 120 s capture timeout. Original focus 37308, marked range
  37180 through 37308, ROI and sequence settings were restored after testing.
- Native UI exercised at 1440 by 940 and 1100 by 760. Browser fixture used a
  412 by 915 viewport. Tests used Cargo's default test concurrency; ARM builds
  used two jobs. No controlled host-load or throughput benchmark is claimed.

## Commands and checks

Commands were run from the repository root. Native socket tests and deployment
used the permitted host context. Full logs and screenshots remain under
`outputs/native-capture-controls-2026-11-13/`; they are not capture-corpus inputs.

```powershell
cargo test --locked --offline -p strehl-ui --bin strehl-ui
cargo test --locked --offline -p strehl-capture --no-default-features --lib
cargo clippy --locked --offline -p strehl-capture -p strehl-ui --all-targets --no-deps -- -D warnings
cargo fmt -p strehl-capture -p strehl-ui -- --check
node --check crates/strehl-capture/web/app.js
python -X utf8 experiments/native-capture-controls-2026-11-13/qualify-web.py outputs/native-capture-controls-2026-11-13/phone-ui-4
python -X utf8 experiments/native-capture-controls-2026-11-13/qualify-camera.py
.\scripts\package-desktop.ps1 -Destination outputs/strehl-desktop-capture-controls-2026-11-13-ready -TargetDirectory target-ui
python -X utf8 experiments/native-capture-controls-2026-11-13/qualify-lifecycle.py --exe outputs/strehl-desktop-capture-controls-2026-11-13-ready/Strehl.exe --out outputs/native-capture-controls-2026-11-13/lifecycle-ready
```

The ARM build used [build-arm.sh](build-arm.sh); all-target ARM clippy used the
existing `experiments/sony-a7cr-2026-11-13/lint-arm.sh`. Deployment used
[deploy.py](deploy.py), which preserves configuration and backs up the previous
matched controller/bridge pair. The final rebuild matched the installed hashes.

| Check | Outcome |
| --- | --- |
| Native Rust tests | 1047 passed, 15 ignored |
| Capture library tests, final run | 38 passed |
| Windows and ARM clippy; Rust formatting; JS parse | Passed |
| Flat and low-amplitude noisy preview controls | No peaking highlights; positive edge control highlights |
| QR fixture | Independently decoded with OpenCV to the exact fixture pairing URL |
| Focus scrub | Coalesces drag targets; revision-bound readback; clears pending targets after failure |
| Slider range change | Changing Fine/Marked/Full range alone does not move focus |
| Shared dropdown | 45 pointer frames with long rows and 1.25 scale remain bounded |
| Actual Edit profile dropdown | 50 pointer frames stay stable; selection tests pass |
| Phone browser | Focus readback advances five units; peaking visible; ROI hidden; modes switch; stack completes; no page errors |
| Packaged native lifecycle | Receiver start/settings, pause/resume/stop/restart and receiver survival after UI close pass |
| Live A7CR native preview | Connected camera, cyan peaking, four-shot selection, planned duration and storage visible |

## Physical camera and failure controls

**VERIFIED:** An 1801-plane four-shot plan required 1,209.64 GB against 289.11 GB
free. A Start command was refused with a useful message, unchanged focus position
and sequence ID, no uncertain exposure and no queued upload. A unit test also
panics if either focus or shutter is touched after failed admission.

**VERIFIED:** The final single-shot run
`D:\StrehlCaptures\stack-1794623743175-10639` contains exactly one durable archive.
The final four-shot run `D:\StrehlCaptures\stack-1794623749395-10639` contains
exactly four. Manifests report the matching member count; results are complete
and pending transfer count is zero. Each original RAW is 124,239,872 bytes.
The single archive is 34,339,273 bytes; the final four-shot member archive is
34,340,975 bytes. Earlier qualification runs are retained separately.

**MEASURED, smoke test only:** Initial one-plane estimates were 3.6 s and 8.4 s
for one/four shots. Observed wall times were 5.94 s and 9.09 s. Initial estimates
are allowances; measured whole-plane cadence takes over during a stack. These
two short runs do not establish sustained throughput or hours-long reliability.

The no-shutter mode probe found that Sony resets the interval in single-shot
mode. The four-shot interval invariant now applies only to four-shot mode, and
the controller explicitly restores the shortest interval when enabling it.
The Sony maximum-file prediction exceeded the previous 128 MiB limit, so the
PTP member ceiling is now 160 MiB and admission uses that ceiling.

The pinned-destination test deliberately changes the receiver default to a
missing folder. Windows can report volume free space even for a nonexistent
path; explicit directory validation now rejects that default while preserving
capacity queries for the already registered run. Older running receivers are
accepted only when their default still matches the pinned run.

## Limits and installation

The original short-label mouse-only dropdown growth was not reproduced in an
isolated baseline. The shared width bound and actual-menu regression tests are
verified; a specific renderer root cause is not claimed. Peaking is a contrast
aid derived from the live JPEG, not an optical quality measurement or a RAW edit.
There is no new long-stack soak or independent photographic quality claim.

The source-inclusive desktop package is
`outputs/strehl-desktop-capture-controls-2026-11-13-ready/`. The desktop
**Strehl Capture** shortcut points to it. Existing receiver state, launchers and
desktop settings were backed up; the running receiver and old desktop window
were left intact. Reopen the desktop using the updated shortcut to load the UI.
The Pi is updated. After explicit user approval of the second Windows prompt,
`update-firewall.ps1` updated the existing receiver rule to the new executable.
Read-back verified it is enabled for inbound TCP 8789 from `10.0.0.0/24` only.
The sign-in launcher now selects that executable. The running receiver was left
intact and its authenticated status check passed. Private local receipts are
`outputs/native-capture-controls-2026-11-13/firewall-approved.json` and
`receiver-launcher-approved.json` in the same directory.

**VERIFIED:** All 896 packaged source-manifest entries match the workspace bytes
at code commit `5178f7eb93cf6234c36e98df0af18a93d60ff3cd`. The source-inclusive
`outputs/Strehl-5178f7eb9-Windows-x64.zip` contains 907 files and is 33,628,768
bytes. Every ZIP member passed CRC validation; the embedded executable matches
the tested executable hash above. Archive SHA-256:
`e218d86fa0b38c4b7c3fe18a52f014ac4dcde3183ac5dc058748330a954511e8`.
Extract the complete archive and launch `Strehl/Strehl.exe`.

Unrelated `experiments/ca-before-mhc/gpu.rs` remains untouched, with SHA-256
`56870cbff57787d388ea42e8fe129b53ebcbc8a38e396fc91c5c3e03904e9af7`.
Public evidence excludes production pairing and receiver keys.

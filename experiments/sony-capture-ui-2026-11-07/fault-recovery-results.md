# Camera fault recovery and capture UX audit

Allocation `sony-capture-ui-2026-11-08-fault-recovery`, November 8 Pacific.
Root, author verification only. [Brief](fault-recovery-brief.md).
The owner recalled a failure to get focus information and could not restart
without closing the app. Their previous stack had finished before this work.

**VERIFIED in source and simulator UI exercises:** camera faults now expose an
explicit **Reconnect camera** action in both interfaces. The native panel stays
outside the scrolling controls; the web footer offers **Recovery options** from
any scroll position. The error and confirmed capture count remain visible.
Reconnection does not release the shutter. It preserves the prior run's journal
and count, then allows a separate new stack from A after the operator reviews
the focus marks. The failed run is not automatically resumed or overwritten.

## State and ownership corrections

- **VERIFIED:** missing focus status clears the old reported position. A failure
  enters an actionable fault state instead of leaving apparently usable stale
  focus information. Both manual and sequence failures can be reconnected.
- **VERIFIED:** the worker retains ownership through initial handshake,
  configuration, recovery and release failures. A replacement SDK process cannot
  open until the previous owned process exits. If release is still pending,
  the UI explains that the operator can wait for camera/card idle and retry.
  No process is forcibly killed to recover an uncertain physical operation.
- **VERIFIED:** an uncertain shutter completion requires explicit acknowledgement
  of camera/card inspection. The last exposure may already exist. Focus/status
  errors alone do not require this acknowledgement. No shutter is automatically
  retried. Disconnect/ordinary Connect cannot bypass the uncertainty check.
- **VERIFIED in source:** confirmed progress advances immediately after a valid capture
  receipt, before journal writing, so a subsequent journal error cannot erase
  an already acknowledged exposure from the visible count.
- **VERIFIED:** reconnect retains bounds/settings for the same reported identity;
  a changed identity or ordinary disconnect invalidates the marks. **LIMIT:** the
  existing bridge identity contains model/transport and build information, not a
  unique camera/lens serial. A matching value does not establish unchanged
  physical focus. Both marks must be reviewed, especially after touching hardware.

## Verification performed

All final commands below exited 0. Rust 1.98.0 MSVC x64, Windows 11 build 26200,
two Cargo build workers; native rendering used RTX 5090 / NVIDIA 621.01 / Vulkan.
The bridge remains Sony SDK 2.02.00. Browser tests used Edge/Playwright with
isolated simulator servers. No physical camera was connected, moved or exposed;
SDK enumeration returned zero cameras. No RAW corpus was accessed. These are
functional/UI checks, not a timing or image-quality benchmark.

```powershell
cargo test --locked --offline -p strehl-capture -j 2 --target-dir outputs/sony-capture-ui/cargo-target
cargo clippy --locked --offline -p strehl-capture --all-targets --no-deps -j 2 --target-dir outputs/sony-capture-ui/cargo-target -- -D warnings
cargo fmt -p strehl-capture -- --check
node --check crates/strehl-capture/web/app.js
python tools/sony-control/package-capture.py --out outputs/sony-capture-ui/strehl-capture-win-x64-2026-11-08-r10
python experiments/sony-capture-ui-2026-11-07/verify-package.py --zip outputs/sony-capture-ui/strehl-capture-win-x64-2026-11-08-r10.zip --out "outputs/sony-capture-ui/recovery-package-check r10" --preview-fix --web-remote
python experiments/sony-capture-ui-2026-11-07/verify-web-fault.py --exe outputs/sony-capture-ui/strehl-capture-win-x64-2026-11-08-r10/Strehl-Capture.exe --out outputs/sony-capture-ui/fault-recovery-browser-r10
python experiments/sony-capture-ui-2026-11-07/verify-web-remote.py --exe outputs/sony-capture-ui/strehl-capture-win-x64-2026-11-08-r10/Strehl-Capture.exe --out outputs/sony-capture-ui/recovery-normal-browser-r10-isolated
```

**VERIFIED:** 22 Rust tests, clippy with warnings denied and formatting pass.
Logs show the affected crate being Compiled/Checked. Negative controls precede
successful recovery: recovery before a fault is refused; Start in Fault is
refused; uncertain recovery without acknowledgement is refused; a failed release
cannot create a second camera; failed initialization and failed replacement
initialization both retain their owner. An inert owned Windows child actually
outlived the first release wait and exited before the next release succeeded.

**VERIFIED:** the relocated package passes 19 native capture and nine preview
assertions, plus ten actual egui interaction checks. Native focus and uncertain
shutter faults recover and complete separate two-plane runs. The phone exercise
does the same, verifies old journal bytes are unchanged, and confirms no new
run/capture occurs until Start. Its hidden failure fixture requires explicit
demo and headless-test flags; both missing-flag controls exit 2 before SDK use.

**VERIFIED:** the normal browser audit covers decoded preview, manual A/B marks,
jog/Go to mark, shared settings, stale edit/duplicate Start rejection, ROI,
browser closure during capture, pause/frozen countdown/resume/stop, a new complete
three-plane stack, and disconnect clearing marks/preview. The native exercise
also covers preview-only survey and usable manual marks when JPEG decoding fails.
Desktop 1366 x 900/1280 x 720 and browser 1366 x 1000/390 x 844 outputs were
inspected; mobile pages have no horizontal overflow. No unexpected browser
errors occurred; the normal audit intentionally elicits one stale-edit HTTP 409.

The first r8 native exercise failed because the new acknowledgement control
scrolled outside the viewport. The fixed panel placement passes that same check
in r9/r10. Visual review also found the primary-button hover style obscured its
label; r10 keeps readable contrast. Failed and intermediate output directories
were retained locally. No gate was relaxed to accept either issue.

The first r10 normal-browser run completed its workflow assertions but failed
the browser-error check on one `net::ERR_NO_BUFFER_SPACE` resource error while
the native exercise ran concurrently. The same executable and unchanged browser
test passed in isolation, with zero unexpected errors. The cause of that
transient resource error was not established; the failed log remains recorded.

Receipts: [build identity](evidence/fault-recovery-build.json),
[native/browser/recovery checks](evidence/fault-recovery-verification.json), and
[pairing regression](evidence/session-recovery-verification.json).
The package includes matching source/notices and still has no RAW-decoder
dependency. The native bridge and SD-only capture protocol are unchanged.

**UNVERIFIED:** the precise original physical focus-information failure and
recovery on the owner's camera/laptop. The tests reproduce that failure class,
not its hardware cause. Actual multi-hour deployment remains untested. Install
the complete new package after capture finishes; reconnect, review A/B with
Go to mark, and start a short real stack first. No merge default, optical finding,
pixel-shift capability or research decision changed; no SYNTHESIS fold.

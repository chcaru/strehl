# Browser remote verification

Continuation: `sony-capture-ui-2026-11-07-web-remote`, 2026-11-07 Pacific.
Owner/reviewer: root, author verification only. [Brief](web-remote-brief.md).
This adds remote capture control; it makes no reconstruction, optical-quality,
pixel-shift feasibility or performance claim and needs no SYNTHESIS fold.

**VERIFIED in source and simulator exercises:** Strehl Capture serves an embedded
browser UI from the camera laptop. Desktop/browser controls share the existing
camera worker, plan, marks and subject ROI. The worker alone owns the Sony bridge;
HTTP requests do not create a second camera connection or depend on desktop
painting. The page offers live preview, zoom, advertised camera magnification,
focus jogging/marks, plan settings, preview survey, start/pause/resume/stop and
the existing countdown. RAW capture still uses the SD-only acknowledgement gate.
Preview JPEGs are held in memory; metadata export remains a desktop operation.

Queue admission atomically reserves one camera command and checks its revision.
The browser additionally checks plan revisions and remembers recent request IDs.
An old controller cannot overwrite another controller's plan or repeat Start.
Pause/resume/stop address the active sequence identity; Stop cannot be cancelled
by a racing Pause/Resume. Browser closure does not stop the worker. Browser state
updates reject older camera/plan revisions, and no camera command is retried
automatically after a lost HTTP reply.

Web remote is opt-in, with an OS-random 192-bit key in a QR/pairing link. The key
is carried in the initial URL fragment, removed from browser history, stored in
session storage and sent as an Authorization header. It rotates when the server
is disabled/re-enabled. HTTP denies missing/wrong keys, foreign browser origins
and public peer addresses. Responses use no-store and a restrictive content
policy. The API has no file-browser, arbitrary output-path, RAW transfer,
metadata-export or shell endpoint; command JSON is bounded to 16 KiB.

**ARGUED deployment route, not a field test:** the laptop serves the website on
LAN or its private Tailscale IPv4 address. The native panel discovers the local
Tailscale address and labels its pairing link for away access. Tailscale must be
installed and connected on the actual laptop and client; the laptop must remain
awake with the camera attached and Strehl Capture open. The bundled optional
firewall helper allows only this executable/port from the local subnet and
Tailscale IPv4 range. Its PowerShell syntax was checked; it was not applied here.
There is no public-hosting, router-port-forwarding or account-creation step.
Local HTTP itself is unencrypted; the away route relies on Tailscale's VPN.

## Verification performed

Commands below ran from the repository root and returned exit 0. Builds used
Rust 1.98.0 MSVC x64, two Cargo workers, Windows 11 build 26200, and the existing
Sony SDK 2.02.00 bridge. Native UI rendering used RTX 5090 / NVIDIA 621.01 / Vulkan.
Tests used an explicit simulated camera. SDK enumeration found zero cameras;
there was no physical camera connection, focus move or exposure, and no corpus
access. Environment, executable/source identities and log hashes are recorded
in the receipts below. No timing benchmark is claimed.

```powershell
cargo test --locked --offline -p strehl-capture -j 2 --target-dir outputs/sony-capture-ui/cargo-target
cargo clippy --locked --offline -p strehl-capture --all-targets --no-deps -j 2 --target-dir outputs/sony-capture-ui/cargo-target -- -D warnings
cargo fmt -p strehl-capture -- --check
node --check crates/strehl-capture/web/app.js
python tools/sony-control/package-capture.py --out outputs/sony-capture-ui/strehl-capture-win-x64-2026-11-07-r5
python experiments/sony-capture-ui-2026-11-07/verify-package.py --zip outputs/sony-capture-ui/strehl-capture-win-x64-2026-11-07-r5.zip --out "outputs/sony-capture-ui/web-package-check r5" --preview-fix --web-remote
python experiments/sony-capture-ui-2026-11-07/verify-web-remote.py --exe "outputs/sony-capture-ui/web-package-check r5/strehl-capture-win-x64-2026-11-07-r5/Strehl-Capture.exe" --out outputs/sony-capture-ui/web-browser-package-r5
```

- **VERIFIED:** 18 Rust tests, clippy with warnings denied, and formatting passed.
  Changed Rust code showed `Compiling` / `Checking`. Tests include actual TCP
  authentication/origin/key-rotation checks, stale/duplicate/in-flight requests,
  invalid command payloads, multi-controller Stop precedence and SD-only capture
  acknowledgement failures. The existing JPEG, preview-survey and timer tests
  also passed. The Windows incremental-cache hard-link warning used Cargo's
  copy fallback during development; it was not a source/test failure.
- **VERIFIED:** the exact relocated package passed 19 native capture-gate and
  nine native preview assertions, plus nine actual egui interaction checks.
  These include preview failure/manual marks, countdown freeze, completed and
  stopped captures, preview survey, and enabling/revoking the web remote.
  Packaged native checks used PATH restricted to Windows System32.
- **VERIFIED:** Edge/Playwright exercised the packaged HTTP server at desktop
  1366 x 1000 and phone 390 x 844 CSS pixels. It decoded the served JPEG, marked
  both focus boundaries, moved focus, shared settings across two clients,
  rejected a stale edit and a second Start, selected an ROI, closed/reopened a
  browser during capture, paused/resumed/stopped, completed a three-plane run,
  and cleared marks/preview on disconnect. The pause held both completed count
  and active elapsed time. There were no unexpected browser errors; one HTTP
  409 was deliberately elicited by the stale-settings negative control.
- **VERIFIED:** neither viewport overflowed horizontally. Complete desktop and
  phone page screenshots and the native pairing panel were inspected. Native
  canvases were 1366 x 900 and 1280 x 720. OpenCV's QR decoder read the actual
  native panel's pairing URL and 48-character key; the test key was revoked and
  is not included in the textual receipts. These are UI/simulator checks, not
  photographic evidence.
- **VERIFIED:** all 504 package manifest entries plus the manifest matched;
  all 91 copied inputs matched the working source and the delivered source
  snapshot. The private package includes the embedded web assets, setup guide,
  optional firewall helper and matching source/notices. It has no RAW decoder
  dependency and contains no image captures. The simulator produced two local
  metadata journals and no RAW/preview image files in those journals.

Earlier development checks intentionally exposed invalid/stale requests. The
first socket test required the environment's local-network permission. A unit
enum originally ignored unknown fields; empty struct variants now reject them.
The r4 package preflight also exposed a legitimate startup gap between source
preview availability and the JPEG transport cache. r5 returns HTTP 204 during
that gap, and the browser waits without attempting to decode an empty image.
Stale previews are labelled while waiting for a new frame, and responses arriving
after disconnection are discarded. The final checks above passed on r5.

**UNVERIFIED:** actual phone hardware/Safari, physical camera operation through
the new browser layer, Windows firewall configuration and an away Tailscale
connection on the owner's devices. The included guide asks the owner to test
the away link with phone Wi-Fi off before leaving the camera laptop unattended.
The bounded browser test server, temporary pairing file and headless browser
processes were retired after the exercise; no remote server is left running.

## Delivered artifact

- `strehl-capture-win-x64-2026-11-07-r5.zip`: 19,487,144 bytes; 505 files.
- ZIP SHA-256: `0c299f5ad0110e001beea0dde58bb967a5d29cb3d702cf99c0b0ce30473d5c6d`.
- App SHA-256: `d25a59160b213b76a76c5f73e4f9910f6113590f0d551948059be8578d5d7288`.
- Bridge SHA-256: `1b1bfe295b44af122a484aac37224ac389a6381370273e87fd59d1d8e3db264b`.
- [Build/source receipt](evidence/web-remote-build.json).
- [Package/browser verification receipt](evidence/web-remote-verification.json).

Extract the complete ZIP to a new folder, close the old capture application,
then open the replacement. Use Web remote to enable access and obtain the
pairing link. The source kit contains the implementation, test harness and setup
guide; these final verification receipts are recorded in the repository after
the source snapshot was built, avoiding a self-referential package hash.

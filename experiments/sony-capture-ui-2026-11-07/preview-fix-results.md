# Preview repair and timer verification

Continuation: `sony-capture-ui-2026-11-07-preview-fix`, 2026-11-07 Pacific.
Owner and reviewer: root, author verification only. [Brief](preview-fix.md).

**VERIFIED in code and regressions:** the bridge now encodes from Sony's returned
JPEG pointer and byte count, checking the subrange against its receive allocation.
The old pointer-equals-allocation-base assumption rejected an otherwise valid
offset payload. Nine native preview assertions cover offset/zero-offset payloads,
null, truncated/oversized/out-of-range and non-JPEG inputs, and the installed SDK's
data-pointer accessor. The accessor's offset before any camera operation was
zero; that is not a measurement of the owner's failing camera frame. The exact
physical payload and repaired live camera path remain **UNVERIFIED** here.

The Rust camera decode path now has an actual JPEG encoder/base64/JSON/decoder
round-trip with dimensions and color tolerance checked, plus invalid-image and
invalid-base64 controls. This closes a gap in the original RGB-only simulator
coverage; it does not substitute for the owner's laptop/camera confirmation.
Decoder error chains and native payload-range diagnostics are retained in the UI.
There is no captured-file download or preview-image file fallback.

**VERIFIED in the actual UI with a failed-preview simulator:** both manual focus
marks and jogging remain available when the preview reports invalid JPEG. They
record the displayed camera-reported command position, allowing inspection on
the camera display. The preview error stays visible. The automatic survey is
disabled without fresh usable preview data, and the exercise confirms that
clicking it in that state cannot move focus. Disconnected/active-operation focus
locks remain in place.

**VERIFIED timing behavior:** the plan offers a rough initial estimate from the
SDK shutter fraction, configured settle duration, one second of approximate
per-cycle overhead, and a similar initial approach allowance. Completed
acknowledged capture cycles replace the guessed cadence with the observed mean;
the initial approach is excluded from that mean. The footer counts active elapsed
time and estimated remaining time. Pause freezes both and is excluded from cycle
measurements. Resume continues the same clock; stop/error freezes elapsed time.
An overrun says it is updating the estimate rather than falsely claiming completion.
The estimate is a convenience calculation, not a calibrated camera timing model.

## Verification run

Commands actually run from the repository root, with exit 0 unless separately
noted. Builds used two workers, Rust 1.98.0 MSVC x64, Sony SDK 2.02.00 and the
same Windows/RTX 5090 environment as the [initial report](results.md). No camera
was connected, focused or exposed; SDK enumeration found zero cameras. No capture
corpus was read or changed. No image-quality or performance comparison is claimed.

```powershell
./tools/sony-control/build.ps1
./outputs/sony-control/bin/strehl-sony-control.exe self-test
python tools/sony-control/test-sony-control.py
cargo fmt -p strehl-capture
cargo test --locked --offline -p strehl-capture -j 2
cargo clippy --locked --offline -p strehl-capture --all-targets --no-deps -j 2 -- -D warnings
cargo fmt -p strehl-capture -- --check
cargo build --locked --offline -p strehl-capture -j 2
python scripts/strehl-capture-control.py --exe target/debug/strehl-capture.exe exercise --out outputs/sony-capture-ui/ui-preview-fix-01
python -X utf8 tools/sony-control/package-capture.py --out outputs/sony-capture-ui/strehl-capture-win-x64-2026-11-07-r3
python -X utf8 experiments/sony-capture-ui-2026-11-07/verify-package.py --zip outputs/sony-capture-ui/strehl-capture-win-x64-2026-11-07-r3.zip --out "outputs/sony-capture-ui/relocated laptop verification r3" --preview-fix
```

- Native `/W4 /WX` build, 19 existing capture-gate assertions and nine new preview
  assertions passed. The existing 17 Python controller tests passed.
- Fourteen Rust tests passed, including actual JPEG decoding and deterministic
  clock tests for pauses, approach exclusion, observed-cadence replacement,
  long durations, invalid shutter fractions, completion and overruns.
- Clippy and formatting checks passed. The existing Windows incremental-cache
  hard-link fallback warning appeared; Cargo copied files. Changed code showed
  `Compiling`/`Checking`, and the release build compiled from the source snapshot.
- The final packaged executable passed eight native egui interaction checks with
  wgpu readback, including manual marks while JPEG preview fails, pause/resume,
  stop, countdown rendering/freeze, complete capture and preview survey.
- The relocated ZIP's 448 manifest entries plus its manifest matched; all 80
  copied inputs matched the working source. Tests ran with PATH restricted to
  Windows System32 and a relocated directory containing spaces.
- Inspected complete packaged renderings: `04-paused.png`,
  `07-manual-marks-without-preview.png` at 1366 x 900, and active
  `laptop live preview.png` at 1280 x 720. The countdown, error state and enabled
  manual controls are visible; no physical image quality is inferred.

The final release exercise also covers two small refinements made after the
first debug UI exercise: the connected/error placeholder, and refusal to begin
an automatic survey without a fresh preview. Historical ZIP verification remains
available without the new `--preview-fix` flag.

## Delivered artifact

- `strehl-capture-win-x64-2026-11-07-r3.zip`: 18,793,144 bytes; 449 files.
- ZIP SHA-256: `1d2e2143458fea6e8b695b0ef531d803b127db15d4753552fe00d0c17514eb72`.
- App SHA-256: `4b085c32141e8e4b21d11af914399aaee4c0a88efb8ee3769a5f276ccc16bba0`.
- Bridge SHA-256: `1b1bfe295b44af122a484aac37224ac389a6381370273e87fd59d1d8e3db264b`.
- [Build/source receipt](evidence/preview-fix-build.json).
- [Relocated verification receipt](evidence/preview-fix-verification.json).

Extract the complete ZIP to a new folder and close the old application before
connecting with the replacement. RAWs remain on SD, live preview remains in
memory, and existing local journals are preserved. Confirmation of the repaired
live camera preview is still pending the owner's use of this build.

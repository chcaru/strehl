# Windows laptop package

**The PC+card package documented below is superseded by the SD-card-only
revision requested by the owner. Use the new ZIP whose name includes
`sd-card-only`.** The old ZIP is retained as an artifact, not recommended for use.

## Original PC+card package (historical)

Owner-requested packaging continuation, 2026-11-07. No capture behavior or native
driver code changed. This is a private portable helper, not a public Strehl
desktop release; no RAW decoder or Rust engine binary is included.

Command actually run from the repository root:

```powershell
python tools/sony-control/package-portable.py --out outputs/sony-control/packages/strehl-sony-control-win-x64-2026-11-07
```

**VERIFIED:** exit 0. ZIP size 21,690,393 bytes, 84 files including its manifest.
SHA-256: `18619b1a83a91f6871c3c3ce1c3a2022907ffc7088bbb8e32fd5969915ab3a30`.

The package includes the unchanged, receipt-checked native executable; Sony SDK
DLLs; app-local VC 14.44.35112 runtime DLLs; official Python 3.13.17 embeddable x64;
the client's sources, tests and documentation; Sony's USB driver files and Readme;
and licence notices with Sony's supplied libusb source archive. Python was fetched
from its official release URL and checked against the SHA-256 published on
[Python's release page](https://www.python.org/downloads/release/python-31317/).
No installer was run and no USB driver was installed.

**VERIFIED relocation checks:** extract the delivered ZIP into
`outputs/sony-control/package-verification/laptop folder with spaces/`, validate
ZIP CRC and all 83 payload hashes, limit PATH to Windows System32 and set invalid
PYTHONHOME/PYTHONPATH. Using that extracted copy:

- Bundled `runtime/python/python.exe -I` reports Python 3.13.17 from the package.
- `sony-control.cmd plan` exits 0 and describes the 73-RAW plan.
- `03-offline-check.cmd` exits 0; all 14 original offline tests pass.
- `01-check-camera.cmd` loads the real SDK and enumerates no cameras, then returns
  the expected exit 1 and records a failed preflight under that copy's `captures/`.
- `02-run-focus-test.cmd --help` exits 0, displays test options and creates no
  focus-test capture session. No photographs or focus moves were requested.

The three bundled VC runtime DLLs were inspected with MSVC dumpbin; their imports
are satisfied by the packaged DLLs and Windows system/UCRT libraries. Exact
relocated command lines, stdout/stderr, exit codes and dependency lists are in
`outputs/sony-control/packages/portable-verification.json`.

**UNVERIFIED:** physical camera operation on the laptop. A missing Sony USB driver
can still require manual installation with administrator rights. The first
verification attempt stopped before executing a launcher because its harness used
the wrong case for the Windows SYSTEMROOT environment key; correcting the harness
was sufficient. No package changes were needed for the subsequent passing checks.

## Replacement SD-card-only package

The owner requested that photographs remain on the SD card. The native driver
was rebuilt to accept only `MemoryCard` saving, remove `SetSaveInfo`/download
handling, and wait on capture events plus card/bracket idle status. Live view is
disabled and the Python image validation/copy/export path is removed. Only
settings and command logs are written on the computer. The camera's SD-only
destination remains selected on exit; other modified settings are restored when
operations have completed cleanly.

Commands actually run from the repository root:

```powershell
& tools/sony-control/build.ps1
python tools/sony-control/test-sony-control.py
& outputs/sony-control/bin/strehl-sony-control.exe self-test
python tools/sony-control/package-portable.py --out outputs/sony-control/packages/strehl-sony-control-sd-card-only-win-x64-2026-11-07
python experiments/sony-focus-control-2026-11-07/verify-portable.py --zip outputs/sony-control/packages/strehl-sony-control-sd-card-only-win-x64-2026-11-07.zip --extract-to 'outputs/sony-control/package-verification/sd card laptop with spaces verified' --report outputs/sony-control/packages/sd-card-only-verification.json
```

**VERIFIED:** fresh native compilation, 17 Python tests and 19 assertions on the
native capture-completion gate, all exit 0. The build used the same SDK/compiler
and two build workers described in [results.md](results.md). Native executable
SHA-256: `fd4cd3f0f173af86190e1a4a7a80b36c73155ad3f1843ad5e735511c050256d2`.
The build receipt now includes the completion header and CMake source hashes;
packaging refuses a stale native build if any of those inputs differ.

**VERIFIED:** replacement ZIP is 21,682,784 bytes, 85 files including its manifest.
SHA-256: `7935bc1e5152bf90f8868172216828f2a550d3b4c11ac0eae7b314acd546f032`.
All 84 payload hashes and ZIP CRC were checked after fresh extraction into a
folder with spaces. The environment had Windows System32 as its only PATH entry
and deliberately invalid PYTHONHOME/PYTHONPATH. Six checks used the extracted copy:

- Bundled isolated Python starts successfully.
- The CLI plan describes 73 RAWs.
- The offline launcher runs all 17 Python tests and 19 native gate assertions.
- The focus-test launcher's help exits successfully, exposes no host destination
  option and creates no capture session.
- An obsolete `--destination host` request is rejected with exit 2 before a session.
- The connection check loads the real SDK, enumerates zero cameras, returns the
  expected exit 1 and records a failed read-only preflight under `logs/`.

No photographs or focus movement were requested. No image files were created.
Exact commands, outputs, expected/actual exits and environment are in
`outputs/sony-control/packages/sd-card-only-verification.json`. This verifies
software packaging and failure handling, **not physical capture behavior**.

The first relocation harness attempt hit `cmd.exe /c` quote stripping when both
the launcher and its test-only output argument contained spaces. It did not run
the rejected-host-option test or make a camera connection. The harness now uses
a relative output argument for that negative test; the actual portable launcher
passes its absolute log path directly to Python. The package was unchanged.
The failed attempt is preserved in
`outputs/sony-control/packages/sd-card-only-verification-first-attempt.json`.

**UNVERIFIED:** camera events, card completion and optical focus precision on the
owner's a7C II/Viltrox rig. After the physical run, verify the 73 RAWs on the card;
event counts and idle status are not file checksums. Manually copy the images for
analysis only when desired, preserving camera names/folders and the matching log.

## Owner's first USB connection report

The owner subsequently reported the a7C II visible in laptop File Explorer after
selecting remote control, while the check returned `found 0`. The laptop's device
binding has not been inspected, so a missing SDK USB driver is a **suspected**
cause, not a confirmed hardware diagnosis.

**VERIFIED against Sony's supplied manual:** `RemoteSampleApp_IM_v2.02.00.pdf`,
pages 9-11, explicitly shows the camera under Portable Devices before installing
the SDK driver. It instructs installing `srcameradriver.inf` for models other than
the RX0 II and checking for `Sony Remote Control Camera` under `libusbK Usb
Devices` afterward. Those pages were extracted with pypdf and rendered/inspected
with PyMuPDF. The already-delivered package contains this INF and its dependencies.

The operator guide now makes this setup step explicit, and the package builder
includes the actual illustrated installation manual in future packages. The
previous reference to the SDK Readme was insufficient: that PDF inventories
files and release notes but does not contain these installation steps. No driver
was installed on this development machine or the owner's laptop; no new capture
was requested and the previously delivered ZIP was not modified.

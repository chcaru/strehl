# Sony capture workspace results

Date: 2026-11-07 Pacific (build receipts extend into 2026-11-08 UTC).
Owner: root. Scope and controls: [brief](brief.md).
This is author-run implementation verification, not independent review or a
physical validation of the new live-view path. No SYNTHESIS fold is proposed.

## Delivered behavior

**VERIFIED in source, tests and the rendered simulator UI:** the separate
`strehl-capture` Windows application provides transient live preview, preview
zoom/pan and edge overlay, advertised camera magnification controls, A/B focus
marks, directional approach, configurable stepping/settling, and cooperative
start/pause/resume/stop. Both endpoints are included; a final interval can be
shorter. Step 1 is the default and smallest command, not a physical-distance unit.

The UI and sequence engine are Rust. A small original C++ process bridge owns
Sony's C++ SDK ABI. Exactly one worker owns the camera; a timeout cannot queue a
replacement shutter. The new executable does not link the stacking engine or
RAW decoder. It changes no production merge default, sensor profile or RAW path.

**VERIFIED implementation:** captures use RAW-only, single drive and camera-only
saving. The viewer receives bounded live-view JPEG buffers in memory and never
saves them. The bridge's existing capture gate requires camera events plus media
idle, rejects a host-file callback and never treats pre-exposure idle as success.
Manual exposure, fixed ISO and a timed shutter are required. Exposure settings
are checked before each RAW; uncertain operations stop the sequence.

**VERIFIED in software controls; UNVERIFIED for real subject coverage:** the
optional preview survey visits at most 33 positions inside rough user bounds,
uses a selected subject rectangle and the median of three distinct previews,
and discards the first changed preview after a focus move. It examines broad
local texture peaks and adds two survey intervals of margin. An edge-clipped
peak retains the full search range; applying a suggestion is a separate manual
action and cannot start a stack. No survey makes RAW exposures.

Flat/noise and gain-only controls precede the known blurred-texture positive
control in `bounds.rs`. These commission the operator, not a calibrated sharpness
or resolution metric. Noise, sharpening, breathing, background detail and weak
subject texture can produce false peaks or missed bounds. The user must inspect
both ends; the application does not promise autonomous whole-subject discovery.

**VERIFIED journal behavior:** `manifest.json`, durable append-only `events.jsonl`
and final `result.json` record commands, readbacks, exposure settings, capture
ordinals, timestamps, camera identity and application/bridge hashes. An intent is
flushed before each shutter. The manifest explicitly says normalized focus,
single-shot capture and unbound camera-event ordinals. It does not invent physical
depth, verified SD filenames or RAW checksums. An unacknowledged shutter is
uncertain and is never automatically retried or resumed after a crash.

Sony's documented interfaces inspected here do not expose arbitrary SD-sidecar
uploads. The implemented exporter copies metadata only into a fresh `STREHL/`
subfolder after the SD card is mounted, preserves the local journal and refuses
overwrite. Strehl currently imports the ordinary RAW folder; automated binding
and ingestion of this new journal are future integration work. Details and the
short first-use check are in the [laptop guide](../../crates/strehl-capture/README.md).

## A7CR research answer

**ARGUED:** alternating external focus moves and complete four-shot pixel-shift
groups has a credible documented PTP 3 implementation path. The native Focus
Bracket prohibition does not itself prohibit an external sequencer that never
enables native bracketing. Capability/readback checks must establish each mode
transition. Combined operation on the exact A7CR/lens/teleconverter remains
**UNVERIFIED**; this is not an unconditional hardware guarantee.

**VERIFIED documentation limit:** the public pixel-shift count write permits
only 1 and 4. Sixteen is a readable value and an official Sony Remote feature,
but that does not make it a supported public write. Preserving a manually chosen
sixteen-shot mode between focus moves remains unestablished. The high-level SDK
does not expose the needed pixel-shift property, so the proposed A7CR backend
would own a direct PTP session. This A7C II package does not enable pixel shift.
See the [source-by-source answer and state machine](a7cr-sequencing.md).

The earlier [900-plane / sensor / pixel-shift analysis](../sony-upgrade-2026-11-07/results.md)
and [physical focus tests](../sony-focus-control-2026-11-07-capture-review/results.md)
were published in `dd6c19d58cfce3f3ac9372891da0d63bd76f5411`. Their optical and
physical limits still apply. Software completion here establishes no new image
quality, speed, distinct-plane count or super-resolution gain.

## Commands and outcomes

All commands ran from the repository root unless stated otherwise. Native exit
codes were checked immediately; all final commands below exited 0. Builds used
two workers. Rust tests used the standard test harness worker default; concurrency
tests create their own single camera worker. No timing comparison is claimed.

```powershell
./tools/sony-control/build.ps1
./outputs/sony-control/bin/strehl-sony-control.exe self-test
python tools/sony-control/test-sony-control.py
cargo test --locked --offline -p strehl-capture -j 2
cargo clippy --locked --offline -p strehl-capture --all-targets --no-deps -j 2 -- -D warnings
cargo fmt -p strehl-capture -- --check
python scripts/strehl-capture-control.py --exe target/debug/strehl-capture.exe exercise --out outputs/sony-capture-ui/ui-check-02
python tools/sony-control/package-capture.py --out outputs/sony-capture-ui/strehl-capture-win-x64-2026-11-07-r2
python -X utf8 experiments/sony-capture-ui-2026-11-07/verify-package.py --zip outputs/sony-capture-ui/strehl-capture-win-x64-2026-11-07-r2.zip --out "outputs/sony-capture-ui/relocated laptop verification r2"
```

| Check | Observed result | Scope / failure exercised |
| --- | --- | --- |
| C++ Release build | Passed `/W4 /WX` with the supplied SDK 2.02.00. | Rebuilt changed bridge; SDK remains external to Git. |
| Native self-test | 19 card-capture gate assertions, plus four base64 vectors passed. | Host-file callbacks, incomplete/uncertain capture and non-completion states remain refused; JPEG transport encoding checked. |
| Existing Python controller tests | 17 passed. | Existing command orchestration and SD-only capture behavior. |
| Rust tests | 10 passed. | Endpoints and range overflow, malformed protocol, flat/noise and gain placebo before blur positive, clipped bounds, durable intent/export, stale command rejection, pause/resume/stop, uncertain capture with no retry/advance, and corrupt receipt/exposure rejection. |
| Clippy / rustfmt | Passed for `strehl-capture`. | Compiler showed `Compiling`/`Checking` for the changed crate. The Windows incremental cache emitted a hard-link fallback warning and copied files; this was not a source warning. |
| Native UI exercise | Six actual egui interaction checks passed; GPU readback produced complete screenshots. | Connect, subject-rectangle drag, mark/jog/mark, start/pause/resume/stop, inclusive three-plane completion, and preview-only bounds suggestion/application. Disconnect clears preview and marks. |
| Relocated release package | 441 manifest entries plus manifest verified; source snapshot and executable identities matched. | Extracted into a path with spaces, with PATH restricted to Windows System32; bridge self-test, SDK enumeration, complete UI exercise and active 1280 x 720 preview all passed. |

Publication checks parsed all three new Python tools and checked seven changed
Markdown documents: 60 local links, 351 table rows and exactly one final newline
per document passed. All 73 copied package inputs matched the working source.
`python -X utf8 scripts/corpus_lint.py` was also run with Git metadata available;
it exited 1 with 16 existing violations in seven unchanged historical reports
(seven unescaped-pipe rows, the same seven code-span pipe findings, and two
missing final newlines). `git diff --exit-code HEAD --` on those seven named paths
exited 0. The full [lint output](evidence/corpus-lint.txt) records them; no new
capture-app or allocation failure was reported. This is not a claim that the
whole research corpus passes its linter.

The offscreen helper is the capture app's local control interface. It sends real
egui pointer input and reads a wgpu render texture; it does not use Computer Use
or substitute a separately drawn mockup. The relocation test runs the exact
shipped release executable. SDK enumeration reported zero connected cameras;
enumeration only was performed, with no connect, focus or exposure command.
All UI captures/journals were generated by the explicitly selected simulator.

The inspected complete images were the relocated package's
`rendered ui and journals/04-paused.png`, `05-survey.png` (1366 x 900), and
`laptop live preview.png` (1280 x 720). Controls, ROI, preview, status, and survey
curves render coherently; the sidebar scrolls at the smaller size. These are UI
layout checks, not photographic comparisons or resolution evidence. The earlier
UI exercise exposed stale preview/mark state after disconnect; that was fixed
before the final build and the relocated exercise checks the corrected behavior.

The first packaging attempt failed on pre-1980 dependency-license timestamps.
The packager now permits ZIP timestamp normalization; the completed `-r2` ZIP
is the delivered artifact. The failed initial ZIP is not a deliverable.

## Build and artifact identities

Environment: Windows x64; Rust 1.98.0 (`88d9e12ae`, LLVM 22.1.8,
`x86_64-pc-windows-msvc`); Visual Studio 17 2022 Release x64; Sony SDK 2.02.00.
Rendered verification used NVIDIA GeForce RTX 5090, driver 621.01, Vulkan.
No statement about the owner's laptop GPU or actual camera live-view performance
is inferred from this machine.

The packager copies the owned source and builds a minimal workspace from that
snapshot using the resolved lockfile, not an arbitrary pre-existing application
binary. The native bridge must match its source/build receipt. Rust dependencies'
notices, the app's source/lockfile, Sony runtime/driver materials, app-local VC
runtime, and the bundled libusb corresponding source accompany the package.
The raw decoder is not linked. Rebuilding Rust requires the locked dependencies;
this private SDK package is not the public release's fully vendored relink kit.

- ZIP: `strehl-capture-win-x64-2026-11-07-r2.zip`, 18,754,061 bytes, 442 files.
- ZIP SHA-256: `667ca8835309cca419ea2ab41321d419dfb75ccc788201719334deb85df8541c`.
- Application SHA-256: `28e6a54bf7d03a82b5a72a182467ebde8fa42461c49f3e3cb444dcdf0190d933`.
- Bridge SHA-256: `888ca58899661903987455bb7d9a0b2b42ac1d3b68d1c8ba12be920c47e940c9`.
- Source identities and compiler receipt: [build evidence](evidence/build.json).
- Exact relocated verification: [package evidence](evidence/verification.json).

The package and original UI renderings remain under ignored
`outputs/sony-capture-ui/`. No SDK binary, private RAW, capture-corpus cache or
unrelated research edit is included in the source commit. No new capture was
requested or taken to finish this work. The new live-view/magnifier integration,
preview-bound usefulness on actual subjects, sustained power, and A7CR combined
operation remain unverified on hardware. The guide starts with a short manual
check before committing to a long stack.

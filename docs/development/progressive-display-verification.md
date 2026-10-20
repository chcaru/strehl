# Progressive photograph display: verification

Recorded October 20, 2026, alongside the implementation tested below.
This report distinguishes display correctness,
CPU cost, native interaction, and photographic judgment.

## Correctness and controls

**VERIFIED:** 749 desktop tests passed, with 11 intentionally ignored
hardware/corpus tests, including the final worker-notification and drawing changes
described below. Three GPU controls were also run explicitly. The shared
editing crate passed 35 tests; the standalone native-audit script passed eight controls. Formatting
and strict all-target Clippy passed. Fresh `Compiling` / `Checking` lines were
observed. Commands:

```console
cargo test --locked -p strehl-ui -- --test-threads=2
cargo test --locked -p strehl-ui photo_viewport::tests -- --test-threads=2
cargo test -p strehl-edit --all-targets
cargo fmt -p strehl-ui -p strehl-edit -- --check
cargo clippy --locked -p strehl-ui -p strehl-edit --all-targets --no-deps -- -D warnings
python scripts/test-release-package.py
python scripts/test-display-performance.py -v
```

Viewport controls exercise native alternating detail, a flat field, coarse
anti-aliasing, odd image extents, feathered global-coordinate regions,
cancellation, invalid samples/baselines, bounded allocation, cache coverage,
and recipe/Before publication identity. The initial-zoom fixture first failed
with a whole-image aperture; it now preserves an explicit view through first
publication, subsequent refinement, and Undo.

The final opening-path controls require a bounded first overview, full source
geometry, native pixels in the standalone viewer, and an actual visible crop
request from the legacy Result canvas. Attaching and detaching progressive
painting preserves a zoomed view; failed editing support receives one native
fallback without entering a retry loop.

The native early-view check also found a publication-order bug: a retained live
reconstruction consumed a requested crop before the final photograph arrived.
A regression with real Preview diagnostics first failed at whole-image UVs.
It now checks five request timings across delayed overview/developed arrivals,
plus actual image/matrix clicks, wheel, double-click, and Undo/Redo actions that
must supersede the waiting crop. Intent follows the linked controls' target view
instead of reapplying an older request over newer input.

Independent Adaptive controls cover a same-path image replacement with repeated
recipe revision, frozen-base amount reuse, and a disconnected worker.
The [Adaptive report](adaptive-development.md) records the rejected initial
calibration-slide treatment and the final complete-photograph comparisons.

**VERIFIED, real GPU:** production shaders were rendered and read back on an
RTX 5090 using DX12. Two separately authored controls use different colors,
white levels, crop coordinates, and alpha values:

```console
cargo test -p strehl-ui native_float_pixels_ui_white_and_sdr_negative_control -- --ignored --nocapture
cargo test -p strehl-ui independent_crop_peak_alpha_and_sdr_encodings -- --ignored --nocapture
cargo test -p strehl-ui registered_sdr_images_preserve_color_crop_alpha_and_deferred_lifetime -- --ignored --nocapture
```

They retain distinct above-white values on a float target, deliberately destroy
that contrast on an 8-bit target, preserve negative scRGB components, fit peak
light without independent channel clipping, and check translucent compositing
and SDR transfer functions. The patched renderer's capture control preserves
all 256 opaque SDR gray codes. A native 1200 × 800 screenshot of four known
colored patches also passed the existing release-smoke image inspector.

The third control exercises the final batched SDR path using production-default
and deterministic renderer options, three attachment formats, two simultaneous
crops, non-unit layer coordinates, partial visibility, and unchanged clipping.
It checks worker registration and texture retirement at zero, one, and two
completed frames. Independent review requested the default-renderer and non-unit
coordinate cases because simpler fixtures could conceal errors in those choices.

These controls establish framebuffer arithmetic, not monitor appearance.

## Bounded development cost

**MEASURED:** the self-contained CPU benchmark uses a 7032 × 4688 source and a
1536 × 1152 native-pixel inspection region, eight worker threads, four sweeps in
alternating order, and the minimum for each arm:

```console
cargo run -p strehl-edit --example display-benchmark --release
```

| Work | Minimum wall time for CPU development |
| --- | ---: |
| Previous whole-image SDR path | 254.526 ms |
| Visible-region SDR | 14.495 ms |
| Visible-region SDR plus linear HDR | 19.480 ms |

The native SDR crop is byte-identical to the corresponding previous-path crop.
This particular region requires about 17.6× less SDR development time. The
comparison excludes decoding, GPU transfers, rendering, and display latency;
it is not a frame-rate multiplier. A larger viewport costs more work.

## Native photograph interaction

**VERIFIED:** an isolated app session reopened the existing 299-capture,
7032 × 4688 insect photograph. At 8× zoom, the requested visible region refined
to a 1504 × 1056 source-pixel patch with stride 1. A second test issued the view
immediately after loading, before the completion reveal settled; the view was
preserved. Adaptive application, repeated amount changes, Undo, and exact
amount-zero preview restoration passed through the app's real MCP interface.
The copied result/log and the user's actual project catalog hashes were
unchanged. Only the isolated session and copied recipe were exercised.

The local reproducible harness and receipts are under
`outputs/progressive-display-review`. The command used for the early-view check:

```console
python outputs/progressive-display-review/check-native.py outputs/quality-october20-target/release/strehl-ui.exe --early --motions 10
```

The first trace and matched comparison are superseded as per-frame CPU evidence:
they counted `App::update` calls, and egui can invoke that more than once while
settling one frame's layout. That duplicated some preceding-framework-CPU
observations. Their original receipts are retained with the correction recorded.
The corrected counter sums update work under one egui frame ID and samples the
preceding framework CPU value once. The regression control supplies two passes
for one frame and requires their work to sum without increasing the frame count.

The first corrected comparison exposed a separate redraw regression. Its
per-frame percentiles overlapped the baseline, but the detail path drew
2408–2559 frames over about 19 seconds versus 596–771 baseline frames over about
20 seconds. Summed framework work rose from 2.30–2.92 seconds to 8.42–9.11 seconds.
Those results were rejected. Measuring only the cost of an individual frame
would have hidden the excess work.

The cause was unbounded repaint requests during detail reveals and waits. In
egui 0.33, a nonzero repaint delay is reduced by the predicted frame duration;
a naive 16 ms request therefore becomes immediate at the default 60 Hz.
The corrected scheduler compensates that duration while keeping the 120 ms
detail reveal. Controls inspect the actual emitted repaint deadline, intermediate
blend, final opaque patch, and absence of animation wakes after the reveal ends.
They vary predicted frame durations across 24, 60, and 240 Hz. Work that is still
settling sleeps until the remaining deadline. The final worker notification
arrives only after its result is readable or its channel is disconnected;
waiting for a patch needs no polling timer. Success, error, cancellation, and
panic each receive one notice. Pointer-driven paints remain unrestricted.

Pacing alone still drew 1051–1057 frames for the same trace, versus 593–594
baseline frames. It repeatedly started a new 120 ms fade from the coarse overview
for neighboring patches, softening pixels that were already sharp. The final
implementation preserves the existing reveal clock only when the new patch uses
the same complete sampling bins, covers the current aperture, and the previous
patch already covered at least 80% of that aperture. At most 20% newly exposed
area joins that reveal; this is an explicit visual tradeoff for small pans.
Large jumps, partial coarse edge bins, changed resolution, and new recipes retain
the full reveal. Opaque detail that covers the viewport also omits the hidden
overview draw. Controls check common source pixels and negative cases with
shifted correspondence, changed scale, sparse overlap, and missing textures.

The final cache keeps a preferred 35% margin on each side, falling back to 12%
and then exact stride-aligned visible bounds before permitting a coarser stride.
The 3072-side and 6 Mi-pixel limits are unchanged. This gives nearby pans more
reusable pixels without spending visible resolution on padding. Regression
controls include off-grid apertures near both allocation limits: extra cache-grid
rounding alone must not reduce a visible region that fits at native resolution.

SDR photo layers also register their immutable texture bindings on the
development worker and use ordinary batched image meshes. HDR layers retain
their float-photo rendering path. Translucent photos on an sRGB attachment keep
the previous callback because the upstream mesh shader's premultiplied-alpha
transfer differs there. Registrations are retired after outstanding meshes
have finished using them.

**MEASURED, final matched comparison:** Windows 11 / DX12 / RTX 5090, SDR,
2600 × 1300 window, the same 7032 × 4688 insect photograph and copied layout.
Each arm issued 100 identical view targets at 8× zoom, in baseline–candidate–
candidate–baseline order. Builds and other native checks were stopped.

| Arm | Painted frames | Framework CPU sum | App update sum | Framework p95 |
| --- | ---: | ---: | ---: | ---: |
| Baseline A1 | 594 | 2.277 s | 1.343 s | 4.345 ms |
| Candidate B1 | 675 | 2.733 s | 1.535 s | 4.703 ms |
| Candidate B2 | 674 | 2.727 s | 1.522 s | 4.725 ms |
| Baseline A2 | 597 | 2.269 s | 1.325 s | 4.291 ms |

The final candidate still costs more than the coarse baseline: comparing
per-arm minima, framework p95 is 9.6% higher and summed framework work is 20.2%
higher. **Zero regression is not established.** App-update mean per frame was
2.258–2.274 ms versus 2.219–2.261 ms; the remaining framework interval averaged
1.774–1.788 ms versus 1.573–1.581 ms. These observed ranges are not confidence
intervals. Framework sums already include app-update work.

Both candidate arms performed 28 detail jobs, read 77,023,808 source samples,
produced 44,410,968 refined pixels, reused cached coverage 74 times, and reused
25 reveal clocks while starting three new reveals. These counters accumulate
from opening through the end of the trace; the timing table covers motion only.
Neither arm cancelled a job
or reported an error. Both finished at native stride 1. The preceding cache
candidate performed identical detail work but drew 859–863 frames and spent
3.454–3.474 seconds in the framework interval. The final scheduling and drawing
changes reduced that overhead without reducing the measured detail workload.
The coarse baseline does not perform those native-detail jobs and reveals.

All 400 targets matched the actually painted aperture. All frame IDs and their
following CPU observations were captured; selected photo, recipe, log, catalog,
and binary hashes were unchanged. This verifies movement and final native detail,
not native detail in every transitional paint. Opening maxima were
23.524–38.036 ms for the candidate versus 43.342–67.696 ms for the baseline, but
opening followed fixture copies and is **not a cold-start measurement**.

Framework CPU includes UI work and renderer submission, excludes vsync wait,
and is neither GPU duration nor input-to-photon latency. Its sum measures
instrumented main-thread work, not whole-process CPU utilization; background
development is excluded. MCP supplies the view commands and imposes its own
transport cadence. High-rate pointer movement, concurrent stacking, other
platforms, other codecs, and long-duration memory behavior are outside this
comparison. No universal smoothness or pointer-latency parity claim follows.

Commands run from this checkout, in this order:

```console
python scripts/check-display-performance.py --binary outputs/display-baseline-target/release/strehl-ui.exe --run outputs/feature-validation/insect-run --catalog outputs/feature-validation/state/Strehl/projects.json --output outputs/progressive-display-review/final-batched-a1 --motions 100
python scripts/check-display-performance.py --binary outputs/quality-october20-target/release/strehl-ui.exe --run outputs/feature-validation/insect-run --catalog outputs/feature-validation/state/Strehl/projects.json --output outputs/progressive-display-review/final-batched-b1 --motions 100
python scripts/check-display-performance.py --binary outputs/quality-october20-target/release/strehl-ui.exe --run outputs/feature-validation/insect-run --catalog outputs/feature-validation/state/Strehl/projects.json --output outputs/progressive-display-review/final-batched-b2 --motions 100
python scripts/check-display-performance.py --binary outputs/display-baseline-target/release/strehl-ui.exe --run outputs/feature-validation/insect-run --catalog outputs/feature-validation/state/Strehl/projects.json --output outputs/progressive-display-review/final-batched-a2 --motions 100
```

The harness accepts another saved run/catalog and copies its inputs into an
isolated fixture. Its SHA-256 for these measurements is
`185a6e55e3412eca597e2a7facdc59dc4e2c17d4b1c87be4d895e3b5ee7a563e`.
Full local receipts and the independent aggregate are retained in
`outputs/progressive-display-review/final-batched-*`; the private photographs
are not distributed with this repository.

The optimized candidate is 28,758,016 bytes, SHA-256
`570726353f6c97cc920e89c6e14d8733d2c9775b2ca171587643e44c4875ab4c`.
The baseline source is `71807aefdda87abeebed2fb337fc722971ac8588`,
with the same per-frame telemetry and painted-aperture witness added for the
comparison; its executable SHA-256 is
`8016b33d6a40ee27487305fe41c7717846b72e9c81a49123375285d094829af8`.

## Platform and distribution limits

The connected monitor reported Windows HDR off. No system display settings
were changed. Windows HDR and macOS EDR presentation are implemented, but actual
HDR-monitor appearance remains **UNVERIFIED** on this machine. Linux and
unsupported backends deliberately use SDR. An imported SDR photograph cannot
recover capture headroom.

The MIT/Apache egui-wgpu patch and original license texts are checked in.
Packaging tests and independently inspected Cargo metadata confirm the local
patch is included in source/relinking kits and third-party notices.
The four-platform [CI run for `91dfa4dd`](https://github.com/chcaru/strehl/actions/runs/39479291300)
passed Windows, Linux, Apple Silicon, and Intel Mac desktop tests, native builds,
regional-repair/reconstruction controls, and embedded-engine smoke checks.
This verifies compilation and the listed controls on each platform; it does not
establish physical HDR output on either Mac runner.
The existing alpha.5 public release is unchanged.

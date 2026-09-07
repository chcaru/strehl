# M194 — synthetic decoded CFA reaches the production Pyramid path

2026-09-07. Source-path commissioning, not a quality or SOTA result. Allocated
by the orchestrator in AGENTS before implementation. Author:
`implementation_audit`; independent verifier: `roadmap_audit`.

## Question and prior decisions

Can a controlled decoded-CFA bracket exercise the merge and writer that the
shipping Pyramid command actually uses, without writing another merge? The
answer under test is a private decoded-frame source and one prepared-state
handoff, leaving RAW preparation and all existing numerical operations in
their original order.

The prior-art search and symbol-by-symbol audit are recorded in
[`experiments/review-production-truth/audit.md`](../../experiments/review-production-truth/audit.md).
The brief names M25, BUILD-BLEND, BUILD-DEMOSAIC, M87, M63, M79, M135, M6,
M164, M166, M84b, M136, BUILD-ELECT, BUILD-SHARP, M103, and the existing
byte-freeze registry. SYNTHESIS architecture and its simulator, calibration,
selection-noise, deep-placement and diagnostic-invariance decisions were read
before this abstraction was chosen.

The existing `blend-truth::merge_multiband` exercises a real one-plane
`BandMerge`, but skips the CLI's decoded CFA gather and output consumers.
Its commissioning warning appears after rows have already been printed and
does not turn the process result into an error. That prior limitation is
preserved, not treated as successful commissioning. BUILD-DEMOSAIC exercises
the actual gather and demosaic on a single analytic frame, but does not fold
a focus bracket through the current merge.

M25 remains a separate renderer with prior optics/occlusion refusals. Its
calibration and truth-coordinate issues are not repaired here. In particular,
running three wavelengths does not establish independently varying scene
chroma: the inspected path uses scalar layer radiance multiplied by channel
scales. None of those historical fixtures or reports is edited by M194.

## Registered falsifiers and threat boundary

The author wrote
[`preregister.md`](../../experiments/m194-production-truth/preregister.md)
before production edits. The verifier independently chose controls in
[`independent-preregister.md`](../../experiments/m194-production-truth/independent-preregister.md)
before reading the prospective source seam.

The tests must fail if the source is ignored, a confidence reread falls back
to disk, interior per-frame placements are ignored, CFA/crop addressing is
wrong, the observer changes the main TIFF, or a refused/failed source silently
produces a successful image. Large upstream input changes and changed output
settings provide live controls; identical inputs and a delegating source
provide inert controls. Actual TIFF decoding, source call counts, and
explicit fixture-occurrence assertions are required.

After reviewing the seam and before implementing the added checks, the
orchestrator additionally requested malformed decoded-storage controls. These
check matching plane geometry, storage dimensions/length and active bounds
before indexing. They preserve `PlaneGeometry::from_active`'s documented
whole-quad behavior for an odd final sensel row/column.

This is a private Rust test seam, not an authenticated external scene or
geometry consumer. Tests supply trusted prepared metadata, a noise model and
per-frame transforms directly. They do not validate RAW decoding, EXIF,
sensor calibration, automatic alignment, cover estimation, defect preflight,
physical defocus/occlusion rendering, or output quality. A physical renderer
sharing its constants with the consumer would still not certify those
constants (AGENTS rule 34). No sharpness or noise-quality score is introduced.

## Shared implementation

`crates/strehl-cli/src/merge_cmd.rs` adds a private `PyramidFrameSource` with
`len()` and indexed `decode()` returning the existing u16 `Frame`.
`RawPyramidSource::decode` delegates directly to `strehl_raw::decode`.
The normal `run_pyramid` still performs its first RAW decode, metadata/noise
preparation, alignment/cover resolution, option checks and defect preflight.
It then passes `PreparedPyramid` and the RAW source to
`run_pyramid_prepared`.

There is one production body after that handoff. It retains the canonical
chunk boundaries, worker reset/absorb sequence, memory plan, band merge and
collapse, and `write_merged` TIFF consumer. `BandWorker::fold`,
`confidence_pass`, and `confidence_debug_pass` all call the same source-backed
`load_frame`. The post-decode sequence remains defect correction, per-frame
gather, measured gate floor, compact four-CFA-plane extraction, green luma,
injected noise variance, and the existing band merger. No aligned-frame volume
or alternate pixel implementation is added.

`validate_pyramid_frame`, called immediately after every source decode,
requires nonempty matching `PlaneGeometry`, checked `stride * buffer_height`
equal to the data length, and checked active bounds inside that storage.
The existing black/white-level equality guard remains. Valid padding and active
origins may differ between frames. Invalid source count is refused before the
prepared merge body allocates its workers. These guards change error behavior
for malformed inputs; they perform no pixel arithmetic on valid frames.

The test-only child
`crates/strehl-cli/src/merge_cmd/production-truth.rs` supplies a generic
`run_fixture_from` bridge so the verifier can choose an independent source,
including a decode error occurring only on a confidence reread. Metadata is
prepared from the fixture directly, excluding the RAW prologue decode. Thus
an all-placed N-frame synthetic fold must call every source index once;
normal or debug confidence adds a second call to each index. The native
wrapper retains its additional first-frame prologue decode.

The synthetic paths are deliberately nonexistent. `Frame` storage has a
nonzero active origin and padded stride. The author uses 192x136 active
sensor pixels, seven frames, distinct CFA sites, an off-axis texture, and a
nonlinear placement track. The author explicitly asserts that its midpoint
departs the endpoint chord in the full-plane frame-0 gauge. This establishes
a curved software stimulus, not transfer to the measured M103 deep-stack
track. A crop at plane origin (3,5), size 84x56, produces 168x112 full-resolution
or 84x56 binned output through the actual writer.

## Author checks

The first author regression run used a fresh
`target/m194-production-truth` target directory. A subprocess cleared every
inherited `STREHL_*` variable and set `RAYON_NUM_THREADS=2` and
`STREHL_PYRAMID_WORKERS=2`, then ran:

```text
cargo test -p strehl-cli --bin strehl m194_actual_source_gather_fold_writer_controls -- --test-threads=1
```

It visibly printed `Compiling strehl-cli`, then passed one test in 0.90 s.
This initial run preceded the additional decoded-storage and explicit
curvature-occurrence guards, so it is a development regression result.

**MEASURED author regression before final formatting/lint cleanup:**
`python -X utf8 experiments/m194-production-truth/author-run.py` cleared all
inherited `STREHL_*` variables, `RUSTFLAGS` and `CARGO_ENCODED_RUSTFLAGS`, then
set `STREHL_PYRAMID_WORKERS=2`, `RAYON_NUM_THREADS=2` and ran the whole CLI
unit suite serially:

```text
cargo test -p strehl-cli --bin strehl --target-dir target/m194-production-truth -- --test-threads=1
```

It explicitly printed `Compiling strehl-cli`, then **128 passed, 0 failed,
0 ignored, 0 filtered out**, in 9.68 s, exit 0. The run includes the
author controls and the independently authored tests under normal confidence.
Evidence is
[`author-verification.json`](../../experiments/m194-production-truth/author-verification.json).
The production source SHA-256 was
`675bbd2a298c5ae9112c47559eaddeea8e6e48ee7368822627dd25eedd79bfde` before
and after; both included test sources were also unchanged. This is author
regression evidence; the independent invocation below is a separate check.
Full output was captured before the exit status was read; no truncating
pipeline supplied a pass/fail result.

A source-edit encoding mistake briefly changed existing Unicode comments to
mojibake. The diff audit caught the unrelated changes before any regression
test was run on that revision. The inverse conversion restored the original
text; a fresh compile preceded the first author test above. This was an
authoring error, not a product finding. The current production diff retains
only the source seam and guards; deletions replace the former path arguments,
direct decoder call, and source-loop variable/call sites.

The first independent build then caught a compile-only error in the author's
new midpoint-occurrence assertion: `Cx` does not multiply by a scalar using
the `*` operator. It was corrected to the existing `Cx::scale` method before
the verifier reran. The failed invocation is retained as
`independent-first-compile-failure.json`; no test result is attributed to that
failed build.

**MEASURED final cleanup checks:** the first `rustfmt --check` omitted the
edition and could not parse existing Rust 2024 let-chains; its failed log is
retained. The corrected `--edition 2024 --config skip_children=true` check
found both new wrapping and unrelated historical formatting. Only the new
production chunks and new test files were formatted. Both new files now pass
full rustfmt checks. The full production file still differs from rustfmt in
historical code; it is **not reported formatting-clean**. The read-only
`check-format-scope.py` confirms that none of the remaining differences
intersects a changed production line and saves the full residual diff in
`remaining-format.diff` and its disposition in `format-verification.json`.

Strict `cargo clippy ... -- -D warnings` first failed on the existing
`build.rs` nested-if warning. Default Clippy then exposed the seam's two
unnecessary `&paths` borrows and argument-count warning. The borrows were
removed; the confidence functions have local argument-count annotations to
keep their inputs explicit. The verifier corrected an equivalent range
predicate in its own test. No historical lint was suppressed or fixed here.
The final command was:

```text
cargo clippy -p strehl-cli --bin strehl --tests --no-deps --target-dir target/m194-production-truth
```

It printed **`Checking strehl-cli`**, exited 0, and left only warnings in
unchanged build, writer, estimator, common-input and command-enum code.
The strict warnings-as-errors check remains a recorded failure, not a green
gate. Raw logs are `clippy-check.log`, `clippy-default.log` and
`clippy-final.log`.

`cleanup-verification.json` and `author-cleanup.diff` bind this small cleanup
to the earlier compiled source: after reversing the two named borrow removals
and two comment/lint-attribute additions, all non-whitespace production text
is identical. This is a scope check, not output verification. Final production
SHA-256 is
`f62c8dd0cbfc7ef61cc52ed7880170952ea304f1e3b816380cc04c65a26dc425`.
The focused final author rerun,
`python -X utf8 experiments/m194-production-truth/author-run.py --focused`,
again printed `Compiling strehl-cli`, passed **1/1** in 0.84 s, and recorded
unchanged source hashes in `author-focused-verification.json`. The verifier
reran its normal/debug tests and the native after-arms on this final source;
their results belong to the next section.

## Independent verification

**VERIFIED by `roadmap_audit`: accepted for the declared source-path scope.**
The final production source above passed five independently authored Rust
tests in each of two isolated processes: normal confidence and debug
confidence. The first invocation printed `Compiling strehl-cli`; the second
used that same unchanged binary. Both returned **5 passed, 0 failed**. The
source hashes match before/after in
[`independent-verification.json`](../../experiments/m194-production-truth/independent-verification.json).

The verifier chose a different stimulus from the author: five frames with
208x152 active sensor pixels, active origin (6,2), stride 223, storage height
159, black/white 256/12000, WB gains (1.4,1,0.65), distinct structured CFA
sites, and an off-axis checker/ramp. Its zero-noise flat-color placebo has
equal green-site means; the structured arm deliberately separates G1/G2.
Known placements use a different curved track in the full-plane frame-0
gauge; the interior scale departure from the endpoint chord is explicitly
asserted. These are software stimuli, not a physical focus/noise model or a
replication of M103's measured curvature.

| Independent control | Observed final result |
|---|---|
| Absolute N=1 CFA/crop coordinates | All 7,904 full-grid RGB pixels and 5,632 cropped pixels agree with independently calculated black subtraction, WB and quantization within **1 output DN**. Crop origin (5,3), size 88x64; full-resolution output 176x128. Known R/B demosaic photosites independently checked. |
| Live source and geometry | An inert source delegate is byte exact. Changing interior frame 2, changing its placement while preserving both endpoints/reference, and substituting identity placements each changes delivered pixels. An explicit synthetic invertible color matrix plus sRGB output reaches ICC and build-tag emission. |
| Refusal and storage | Injected decode error, inconsistent levels, wrong source count and all-refused placements fail without a main TIFF. Eight malformed storage/extent cases return errors without panicking. A changed refused frame leaves both merge and confidence bytes unchanged. Valid odd trailing sensels and poisoned padding are byte-inert. |
| Confidence reach and non-perturbation | Nonexistent RAW paths still succeed through normal/debug source rereads. Every index is decoded once for folding and twice with confidence, including decode-before-placement-refusal behavior. A second-call-only failure aborts before either main/confidence TIFF. Texture and flat-color observer placebos preserve complete main TIFF bytes. |
| Cross-process artifact check | Python/tifffile inspected **54** saved TIFFs. All **22** corresponding normal/debug files are byte-identical, including the shipped confidence maps. Debug candidate maps have the expected plane dimensions; centrality equals the shipped map. |

The source review found one shared `BandWorker::fold`/`load_frame` path,
unchanged canonical reduction/collapse/writer arithmetic, and no confidence
fallback to disk. The malformed-frame guards are the intentional new refusal
behavior. The independent coordinate oracle does not copy the pyramid,
gather or demosaic implementation. No sharpness/quality score is introduced.
The controls and TIFF hashes are in
[`independent-controls.rs`](../../experiments/m194-production-truth/independent-controls.rs)
and [`independent-artifacts.json`](../../experiments/m194-production-truth/independent-artifacts.json).

**MEASURED native byte lineage:** the existing development registry's
`coffee-bean` first 20 RAWs, DSC00016–DSC00035, were rendered with the archived
e93f0bde695961d53cbd66587a060a41552b4a63 executable and the new release binary.
Both alignment-off and the copied committed 20-frame sidecar were exercised,
with two execution threads, Pyramid gate 2.0 and the registered binned writer.
The final cleaned source was rebuilt and its two after-arms rerun against the
preserved before TIFFs. Every render folded 20/20 frames. Both 3516x2344 RGB16
files are **49,450,019 bytes** and exactly reproduce the existing registry:

| Native arm | Before = final-after whole-file SHA-256 |
|---|---|
| Alignment off | `C6765BFA0D2FD203F65A7B02FE36920902B26A6706CCEAA8E87B76AC1CE5CD65` |
| Pinned sidecar, reference frame 10 | `FB76DE79359F46E4E7E7601520FCE45F08A79381F9019F0AEE763B2DDD88B084` |

The orchestrator then re-chose the remaining native choice point: binned
TIFFs do not exercise the RAW WB/XYZ handoff into full-resolution developed
output. One final-binary `bee-1-cpl` N=33, W=8 after-arm therefore used the
exact completed M192d suffix, copied N33 sidecar, reference frame 16,
full-resolution MHC and linear-sRGB output. Its already completed M192d
baseline was hashed and decoded, not rerendered. The final render folded
33/33 frames and reproduced the **197,798,956-byte**, 7032x4688 RGB16 TIFF:
whole-file SHA-256
`3309E33318C701FB75C55507BFB49AD279D8950492B592EC247DBE2D1193AC9E`,
decoded-pixel SHA-256
`6EFC261E892DCDB5D492AD3FD79BDC7E5A208D93D0227A41B258FB3B900F9B89`.

All selected RAW content hashes, directory-entry metadata (including hidden
entries), source content and original/copied sidecars remained unchanged.
Cache, temporary state and output lived in this experiment's scratch paths.
Inherited `STREHL_*` settings were cleared; exact per-arm settings, source and
input manifests, commands and logs are bound in
[`independent-native.json`](../../experiments/m194-production-truth/independent-native.json)
and [`independent-full-native.json`](../../experiments/m194-production-truth/independent-full-native.json).
The final release build visibly compiled; its SHA-256 is
`942668EABD75930C01EBA09A3B9587FC6818E516E0335A3A0F2BE508BD108D64`.
Only the compiled Software stamp was normalized to the old commit for the
comparison. This stamp is a comparison control, **not** the new binary's
source identity; its actual source hash is recorded above and in the manifests.
The native developed TIFF carries that stamp. Camera-native TIFFs deliberately
carry package version only, so their source lineage comes from these manifests.

Commands run, with complete child argv/environment and rebuild output retained:

```text
python -B experiments/m194-production-truth/independent-run.py
python -B experiments/m194-production-truth/independent-artifacts.py
python -B experiments/m194-production-truth/independent-native.py
python -B experiments/m194-production-truth/independent-native-finish.py
python -B experiments/m194-production-truth/independent-native-recheck.py
python -B experiments/m194-production-truth/independent-full-native.py
```

Failed attempts remain part of the evidence. The first compilation caught the
author's invalid `Cx * 0.5` midpoint expression, fixed to the actual `scale`
API. Two subsequent test failures were the verifier's incorrect assumption
that camera-native or merely demosaiced TIFFs carry the build stamp; inspection
showed the existing discriminator is ICC/colorimetric output. The corrected
controls assert both branches. The first native driver stopped **after a
successful aligned baseline render** because it expected the registry's
`on-sidecar-override` disposition rather than the actual
`ON (sidecar-override)` log text. Recovery validated the three already completed
executions and ran only the missing fourth arm. Their initial JSON/logs and
the pre-cleanup native/synthetic results are preserved under `independent-*`.
None of these test/driver errors is represented as a product defect or hidden
by replacing a failed quality threshold.

This establishes the tested RAW and synthetic source handoff, valid-input byte
lineage, and diagnostic non-perturbation. It does not validate independent RAW
decoding, camera calibration, defocus/occlusion truth, live registration,
quality, native resource admission, all product options, or SOTA.

## Limits and next use

The seam removes one concrete obstacle to a production truth benchmark:
synthetic decoded input can now be supplied to the existing gather, merge,
confidence and writer body. It does not finish that benchmark. A subsequent
commission must provide independently supported scene/noise rendering,
per-frame curved truth in the consumer's gauge, defocus and occlusion controls,
spatially varying chroma where claimed, and delivered-image truth after crop,
demosaic, colour and quantisation. It must demonstrate that its instruments
reject known destroyers before evaluating a candidate merge change.

No admission threshold, sensor calibration, alignment policy, public option,
historical certificate, scorecard or SOTA claim changes. Native memory/timing
certification and all prior simulator refusals remain separate work.

## Applicable rule checks

- Rules 1–7: existing u16 `Frame`, source-at-consumption fold and injected
  `PreparedPyramid::noise`; no aligned volume, chained solve or new selector;
  active-area storage checks and exact CFA coordinate controls.
- Rules 8, 11–13, 18, 20–24, 30, 34–36 and 39: preregistered live/inert/error
  controls, independent scene/source choices, actual writer and call-count
  observations; no quality metric or calibration assertion to self-certify.
- Rules 9, 10, 15, 17, 21 and 23: no sharpness score, spatial/temporal sigma
  comparison, occlusion-halo score, fitted-constant gate or new array filter.
  The confidence constant-source control is an observer placebo, not a noise
  or quality measurement.
- Rules 14, 27, 32 and 45–49: synthetic author tests read no RAW; authorized
  native scope and evidence isolation belong to the separate independent
  lineage record. No process was stopped and no peer lane was locked.
- Rules 16, 19, 25, 28–29, 31–33, 37–38 and 40–44: no performance sweep or
  SYNTHESIS fold; new files use kebab-case with an explicit Rust module path;
  prior-art audit and allocation precede implementation;
  source diff/deletion review and visible compiler rebuilds precede claims.
  Parent owns the scoped commit.
- Rule 26: confidence on/off compares the complete main TIFF bytes, including
  a constant-source placebo; final independent results state its actual scope.

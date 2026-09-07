# M193c — actual output-grid authentication and complementary-focus coverage

2026-09-07. **DESIGN ONLY; root review required before implementation.** This
charter is the only new file in this assignment. No image bytes were read, no
RAW/TIFF was decoded, no experiment or product ran, and no held M194g or product
source was changed. The metadata-only accessibility check below was executed.

## Decision and precise first consumer

Build a bounded adapter that connects an input-only geometry record to the
actual native strehl Pyramid gather/crop/writer and to an independently read
output TIFF. Separately measure whether the frozen M193b input registrar can
place the fixed complementary-focus development inputs. These are two named
outcomes of one end-to-end geometry rehearsal, not a new image-quality score.

The immediate consumer is the mapping of each original frame and each output
pixel centre into a named common coordinate gauge. A syntactically valid
descriptor or favourable retained-area number is insufficient. Wrong crop
origin, native/quad factor, output scale or frame association must be capable
of failing through actual pixel coordinates, not merely through a stale hash.

There is an explicit scope correction to the preliminary audit recommendation.
The repository's `CommonTiffFrame` supplies strict input identity, but its only
CLI consumer, `strehl-common-input`, reads one file and optionally exercises one
`BandMerge` frame with unit variance; it emits an identity report, not a stacked
TIFF. M165 also reports no campaign common-input TIFFs and retains
`PROPHOTO_DISPROVED` for the required fork's colour interpretation. Neither
M194g's CFA bridge nor M165's identity success is a complete common-TIFF stack
route. **First scope is native-product geometry plus input-only registration
coverage.** It cannot close the competitive common-merge geometry blocker.
A true common-TIFF production route needs a later explicit RGB gather,
injected noise/transfer, colour and writer contract; this charter does not
invent those missing semantics or copy a RAW scalar gain onto demosaiced RGB.

## Decision record and exact reuse

Read architectural decisions in `docs/research/SYNTHESIS.md` §3 before drafting.
Keep u16 CFA storage/f32 arithmetic, gather at consumption, injected noise and
runtime geometry. Its historical pipeline text must be read with subsequent
corrections: §3.3's fixed reference is superseded for deep stacks; M103 further
rejects endpoint-only acceptance and unconditional deletion of short edges.
Do not replace the stacker architecture, merge, resampler or default cover.

Reuse these existing boundaries by frozen bytes, without editing their records:

- `experiments/m193b-geometry-consumer/consumer.py`: streamed input snapshots,
  `construct_overlap_paths`, immutable `TrustedInputBinding`, strict overlap,
  output-grid and retention consumers. Preserve v1's input-byte ordering,
  registrar, original identity/crop verdicts and complementary refusal.
- `experiments/M193-cover-overlap/contract-v1.json`: Q32 coordinate convention,
  input-only reference/overlap, held-out split and unchanged geometry bars.
  Its registered source-to-reference fit allows1 pixel held-out RMS; the
  output-map residual bar is0.1 pixel. Do not conflate these two conditions.
- Actual `run_pyramid_prepared`/gather, early-Crop implementation and final
  writer in `crates/strehl-cli/src/merge_cmd.rs`, through one narrow test-local
  adapter or an existing supported public invocation. No alternate merge and
  no remosaicing an RGB TIFF to pretend it is RAW input.
- M194g's actual parent child/exit/log/build binding, strict TIFF decoding and
  rank-two coordinate-control patterns. New versioned adapters may reuse
  these implementations by exact source pins; do not edit or relabel held
  M194g sources/results. Its320x240 CameraLinear reader limits cannot simply
  be applied to a native linear-sRGB TIFF; the new reader must explicitly
  freeze the actual output tag/profile/transfer and size contract.
- M165 `CommonTiffFrame` only for its demonstrated strict TIFF/premerge
  identity scope if a separately declared registration derivative uses its
  compatible format. Identity is not evidence about a full merge or colour
  interpretation.

Controlling reports are `M193-geometry-review.md` §2–3,
`M193b-geometry-consumer.md` (remaining work), `M130-crop-early.md`,
`M103-halfdrift.md` §16/18, `M165-common-input.md`, and
`M192d-production-rehearsal.md` §Timing limits. The current program is
`docs/proposals/2026-09-sota-program.md` §2. Another full M192 systems campaign
is not a prerequisite to this bounded development task.

## Fixed development inputs and observed accessibility

The live scorecard explicitly lists `coffee-bean` as **FIXED HISTORICAL
BENCHMARK — NOT HOLDOUT** (`docs/proposals/2026-09-sota-scorecard.md`, capture
table). It cannot recover the retracted detail claim. This selection does not
access any protected `bee-1-cpl`, ruler, foam or other holdout.

On2026-09-07 the following read-only PowerShell operation listed directory
entries including hidden/system entries, then selected filename-sorted ARWs:

```powershell
$m193cItems = @(Get-ChildItem -LiteralPath 'D:\personal\macro\coffee-bean' -Force)
$m193cRaws = @($m193cItems | Where-Object {
    -not $_.PSIsContainer -and $_.Extension -ieq '.arw'
} | Sort-Object Name)
# Inspect FullName, Length, LastWriteTimeUtc and Attributes at these indices:
# 0,13,26,39,52,65,78,91,104
```

**OBSERVED METADATA ONLY:**210 entries:105 ARWs and105 XMPs, no subdirectory or
TIFF in that directory. ARW total4,161,077,248 bytes, first`DSC00016.ARW`,
last`DSC00120.ARW`. All nine selected paths were listed as ordinary files with
Archive attribute. This confirms metadata accessibility, not successful
decoding, common-TIFF availability or byte identity with a historical copy.

| Original sorted index | Filename under that directory | Bytes | LastWriteTimeUtc |
| --- | --- | ---: | --- |
| 0 | DSC00016.ARW | 39030784 | 2026-05-10T23:31:09.7600000Z |
| 13 | DSC00029.ARW | 39878656 | 2026-05-10T23:31:25.9600000Z |
| 26 | DSC00042.ARW | 40873984 | 2026-05-10T23:31:42.0600000Z |
| 39 | DSC00055.ARW | 40669184 | 2026-05-10T23:31:58.9500000Z |
| 52 | DSC00068.ARW | 39497728 | 2026-05-10T23:32:14.5000000Z |
| 65 | DSC00081.ARW | 39235584 | 2026-05-10T23:32:29.6900000Z |
| 78 | DSC00094.ARW | 39096320 | 2026-05-10T23:32:44.7000000Z |
| 91 | DSC00107.ARW | 39018496 | 2026-05-10T23:32:59.5200000Z |
| 104 | DSC00120.ARW | 38969344 | 2026-05-10T23:33:14.1500000Z |

Later execution must hash exactly these nine source files before/after and
bind their original indices, not only local0..8. No source or XMP writes,
mtime/attribute changes, corpus-side caches or new captures. Do not interpret
Archive as an operating-system write prohibition; read-only is the runner's
behaviour. Outputs/caches/derivatives belong under this experiment's fresh
workspace directory. Do not use the neighbouring XMP processing instructions.
Any deterministic registration derivative must be separately specified and
commissioned before these ARWs are decoded. It must keep the native active
centre coordinates and declare its colour/luma construction, with no
alignment, resized view, sharpening or fitted tone adjustment disguised as
an input. Such a development derivative is not a qualified common-merge input.

## Concrete adapter and record seam

Use two stages, plan then render, with externally pinned build/source/input
and actual parent-observed commands. A future `m193c-output-grid-plan-v1`
record contains: schema/status, build and adapter source refs, settings,
ordered original-index/source/derivative refs, trusted registrar result and
reference identity, product per-frame transforms with their gauge, full native
and quad domains, actual Crop rectangle, expected output dimensions and
sampling transform, and a frozen common-to-output Q32 descriptor with its
input-only residual evidence. Freeze all child fields and exact failure names
in the implementation preregistration; a descriptor cannot mint input trust.

The product plan is observed from the same preparation object later consumed
by the real gather/crop/writer, not a second reimplementation of its settings.
Input-derived overlap is constructed first without product transforms, crop,
output dimensions or pixels. The adapter may consume product pre-render
geometry to describe its output, but may not feed that result back into the
trusted overlap. A product plan and the registrar can disagree; preserve both.

The render consumes the full saved plan/hash and records the actual selected
input indices, actual consumed per-frame transformations and dimensions,
decode/fold completion, writer configuration, TIFF file/pixel hashes, and
source/input before/after bindings. A separately implemented output consumer
reopens those actual bytes and either confirms the frozen descriptor or
refuses. No output-derived fit, crop or translation can repair a pre-output
descriptor or change its denominator. Metadata dimensions alone do not pass
the private pixel-coordinate controls below.

Initial real population is one frozen native baseline configuration with
explicit Crop and Scale arms, each planned before either renders; at most two
real TIFFs. Crop is an existing opt-in mode, not a default promotion. Use the
same product settings/noise injection/resampler/frame list in both arms.
If preparation or registration refuses, retain the cause and do not generate
an invented common-to-output descriptor. Private adapter commissioning can
complete independently; the real geometry outcome remains unmeasured.

## Powered private controls before real output

Rechoose a finite, literal private population before code runs. Reuse the
commissioned rank-two RGB affine coordinate fields and unequal native crop
origins from M194f/g, with nonzero distinct x/y gradients and an interior set
of sites. Bind both actual pixel errors and consumed geometry. Add an actual
nonidentity similarity and a curved nine-frame placement sequence derived
prospectively from M103's retained nonlinear track; do not replace that control
with a linear ramp. The exact coefficients/sites/expected pixels and numeric
rounding allowances must be independently derived and frozen before rendering.
No scene/noise sweep or post-result tolerance selection is permitted.

Required active wrong implementations/descriptors and restored companions:

1. Input unchanged, output map changed: wrong unequal crop origin, swapped
   x/y, and native-versus-quad factor2 must fail actual coordinate pixels.
2. A coherently rehashed descriptor that labels actual Scale output as identity
   must fail. A known nonidentity transform must be observed, not inferred
   merely from a different filename, plan label or output dimensions.
3. Swap two actual per-frame placement associations while retaining the same
   endpoint transform. The fixed curved sequence and per-frame coordinate
   witnesses must detect this; an endpoint-only checker is a negative control.
4. Change only the output pixels by a known coordinate translation and update
   all TIFF hashes. The unchanged frozen descriptor must fail its coordinate
   oracle; a hash failure cannot count as power for this test. The independent
   checker must exercise the real file-reading entry, not only an arithmetic
   helper or fabricated child summary.
5. Rehashed smaller overlap/rebound descriptor must still refuse with the
   original trusted input binding. Keep M193's identity PASS/cropped FAIL and
   unchanged-denominator-under-output-mutation controls.
6. Keep same-focus transformed-texture positives and the complementary-focus
   identity refusal as an explicit old-algorithm outcome. A non-perturbing
   observer runs off/count/placebo through actual private outputs, requiring
   file/pixel byte identity and live hook counts.

Constant/affine fields prove coordinate response only within their derived
scope. They do not prove an adaptive noise law, MHC/WB ordering, preserved
detail or real registration truth. A scalar ramp alone is rank deficient for
two-axis mapping; merely identical copies cannot power frame-association
faults. These pitfalls must be addressed in the literal preregistered controls.

## Gauge, unknown truth and decision after a refusal

For native product reporting use local reference4/original52 for the nine-frame
development population if that preparation API supports an explicit anchor;
otherwise record its actual anchor and freeze the conversion before any run.
Never silently assume a reference. M193's minimum-byte-hash input reference
is independent and may be another original frame. Report the exact map between
these gauges. Every placement/error is in native pixel centres, or explicitly
labelled quad centres with factor2; output sites use the descriptor's gauge.

The real coffee-bean transforms are unknown ground truth. Held-out SIFT residual
and consensus establish compatibility on admitted landmarks, not absolute
whole-frame accuracy. Report per-frame coverage, reference distance and
held-out residuals, including refusal counts. Do not call the nine rungs
adequate deep-stack coverage, substitute their envelope for105 inputs, or use
an output's apparent sharpness to validate its input geometry. A planted known
transform on real content tests equivariance; shared baseline error can survive
it. M103's independent historical ladder is evidence about its own stack,
not coffee-bean truth or permission to read that other corpus.

Use named failures to choose the next task:

- Incorrect actual output mapping with adequate input registration: repair the
  adapter/product coordinate consumer on its powered private control first.
- Inadequate complementary-focus matches/held-out support: retain the fixed
  reference refusal, then preregister one direct multi-span edge measurement
  change. Do not assume a graph solve creates missing correspondences.
- Adequate pairwise support but graph/placement inconsistency: a separate
  bounded graph experiment may compare direct constraints, check connected
  component/cycle rank and per-frame held-out placements. No chaining or
  unconditional short-edge deletion; tree consistency is not independent
  validation. No graph implementation is included in this charter.
- Empty/inadequate true overlap: report it. Do not shrink the denominator,
  change the nine inputs after viewing outputs, or reinterpret a retention miss.
- Missing common-TIFF pipeline/noise/colour prerequisites: retain
  `UNMEASURED_COMMON_MERGE_PATH`; native geometry success cannot clear it.

## Bounds and completion

Prospective operational ceilings for this first implementation: nine selected
real inputs, one input decode/snapshot at a time, at most two real renders and
12 small320x240 private renders. No aligned-frame stack. Each child has240 wall
seconds and16MiB retained combined log. Entire real rehearsal:1200 CPU seconds,
1800 wall seconds,8GiB process-tree peak and4GiB new workspace file bytes,
including registration derivatives, one temporary input snapshot, outputs and
failed artifacts; metadata/logs within128MiB. Private commissioning has its own
600CPU/1200wall ceiling. These are operational caps, not measured cost, M12
bars or a speed claim. Bind actual enforcement/array ownership and final
persistence coverage before release; do not pretend named-array accounting is
RSS. Native dimensions and decoded allocation bounds are checked before large
allocations. Resource refusal remains a retained outcome, not a partial pass.

Completion delivers one versioned runnable adapter, strict independent reader,
private controls and complete finite real outcomes, with original errors and
late-publication revocation retained. Separate dispositions are
`PASS_GRID_ADAPTER_PRIVATE_ONLY`, `COMPLETE_NATIVE_GEOMETRY_REHEARSAL` or named
unmeasured/refused real outcomes. None implies SOTA, native default promotion,
common-merge qualification, comparator parity, M1/detail or full M10 coverage.
The charter itself grants no implementation, decode, build or render release.

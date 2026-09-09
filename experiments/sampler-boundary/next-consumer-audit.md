# Next common-TIFF consumer audit

2026-09-08. SOURCE-READ / ARGUED. No product edit, build, test, render, RAW/model
access or numerical call. Root reports sampler runtime complete; independent saved-result review remains
required. This note is outside the sampler's frozen source map.

Recommend a bounded v2 of the completed identity-grid common-TIFF consumer:
variable frame count and dimensions, with unchanged color/noise/merge semantics.
Known-map gather should be the next separate consumer commission.

## Prior answers checked before recommendation

These mandatory searches actually ran once each, exit0:

    python -I -S -B experiments/ORCH-drift-check/prior_art.py "common TIFF" "frame count" dimensions "known map" gather "resampling noise"
    python -I -S -B experiments/ORCH-drift-check/prior_art.py common-TIFF "common RGB" frame-count "odd dimensions"

Interpreter: C:/Users/chris/AppData/Local/Programs/Python/Python312/python.exe.
Headline hits were V-GATHER, V-HEADTOHEAD2, BUILD-DEMOSAIC, BUILD-GATE and
common-tiff-stack-integration. Secondary mentions were search leads.

Read the relevant answers in context:
- docs/research/common-tiff-stack-integration.md records the completed
  three-frame 128x96 route and all twelve cases. Do not repeat that commission
  or describe the multi-frame consumer as still missing.
- docs/research/M165-common-input.md and
  experiments/review-output-adapter/audit.md distinguish byte identity, color
  semantics and image production. The required external consumer remains
  PROPHOTO_DISPROVED; real calibration/campaign admission remains absent.
- docs/research/V-GATHER.md must be read with BUILD-GATE.md: warped band noise
  differs from the white-input floor, predates the gather flip, and does not
  justify forcing the old arm's averaged fraction. Invalid gathered borders
  must not become noise observations.
- BUILD-DEMOSAIC.md shows lower R-B high-pass power can hide increased actual
  error through channel covariance. V-HEADTOHEAD2.md's corrected registration
  sign shows why apparent comparator agreement is not a geometry oracle.

SYNTHESIS sections 3.1-3.2 were reread: u16 storage/f32 arithmetic, no cached
aligned-frame stack, fixed concurrency, injected noise and consumer-gauge truth.
The current 2026-09-sota-program.md's latest common-RGB section records software
completion and queues the sampler contract before larger inputs. Older
missing-consumer paragraphs are history. No SYNTHESIS/program edit is made.

## Actual consuming restriction

Source locations below are repository-relative.

| Source | Restriction or reusable seam |
| --- | --- |
| crates/strehl-cli/src/bin/common-stack/manifest.rs:9,24,143,155 | WIDTH=128, HEIGHT=96, inputs:[Input;3], resolved paths:[PathBuf;3], exact grid equality. A fourth input or different geometry cannot reach the consumer. |
| same file:14,211,311 | Fixed 256KiB TIFF cap and per-visit fixed-dimension preflight. New extents must be admitted before bounded reads/decoding. |
| common-stack/mod.rs:247,278,290,337 | Core/workspace, parsed dimensions, proxy/variance lengths and completion use the fixed grid/count. The ordered fold loop at264 already streams one frame; data drops at333. |
| common-stack/mod.rs:137,200; writer.rs:11,72,95 | Census/output observation and encoder have fixed shapes; writer128KiB and metadata/stage allowances need honest new bounds. |
| crates/strehl-core/src/pyramid.rs:103,119,1737 | Ceiling reduction and BandMerge already accept runtime geometry/repeated three-plane folds. No new merger is required. |
| crates/strehl-raw/src/common_tiff.rs:116,176,381 | Public common-TIFF parser supports positive dimensions and strip layouts, stores u16 and produces per-visit f32 planes. No RAW parser redesign is needed. |

Shortened common-stack paths are under crates/strehl-cli/src/bin/. Noise remains
the two simulated RGB16-code-squared laws, proxy variance0 or24; changing count
must not admit uncalibrated photographic RGB.

## Smallest next implementation and bounded tests

Preserve v1 behavior and the CLI entry; add a versioned bounded manifest using
input/path vectors and runtime dimensions throughout the existing own modules.
Keep RGB, the exact linear-ProPhoto/D50 profile, identity coordinates,
HardFloor, three Laplacian bands plus base, InputRange and both simulated noise
laws. Add no band-count option, exposure fitting, color conversion or maps.

Proposed intake: 2..8 ordered frames, each dimension64..512, pixels<=262144,
and require level_sizes(...,3) to contain four levels. These are operational proposals, not quality limits. A separate reviewed grant
must set process/work/output limits before execution.

Derive bounds using checked arithmetic: 6*width*height RGB16 payload, bounded
TIFF metadata/strips, manifest/paths, output plus simultaneous stage, N frame
receipts and final/refusal records. Maximum raw payload is 1572864 bytes, so
the current256KiB input/128KiB output caps are insufficient. Keep only one
encoded input, one decoded u16 frame and its f32 preparation beside reusable
merge/workspace state. Only bounded metadata grows with N. Bind actual output
dimensions/profile, ordered folds and consumed variance/proxy identities.

Have the independent fixture/checker author freeze a finite list exercising:
- N=2,5,8 distinct constant contributors on small/even, odd non-square129x97
  and upper-bound512x512 grids. Choose a literal palette where every dropped
  or duplicated contributor changes the independently rounded mean. Require
  that mean AND every distinct fold identity/counter; image agreement alone
  can conceal a missing mean-valued contributor.
- Identical asymmetric RGB address fields at odd geometry, distinguished last
  row/column/corners and multiple strip arrangements. InputRange supplies
  full-grid literal truth for addressing/color, not pyramid quality.
  Independently enumerate129x97 ->65x49 ->33x25 ->17x13. Mutated width/height,
  omitted odd edge and channel/interleaving operands must fail.
- One new odd-size mixed noisy population, off/on/placebo: whole TIFF/pixel
  equality, actual variance hashes/values, actual white BandGain values and
  both accumulated-denominator populations in Laplacian levels only.
  This commissions generalized diagnostics, not physical calibration.
- Early N=1/N=9, dimension bounds and overflow refusals; late wrong final-frame
  geometry/hash after exactly N-1 folds. Require durable prefix, no admitted
  image and named reason. Preserve duplicate/profile/noise rejection.
- One legacy v1 case against its held output, not the whole completed study.

Keep two threads, fresh-source/binary/terminal evidence and bounded memory
observations. A memory ceiling is not a throughput/asymptotic measurement.
Reuse the existing owned-process/saved-output tools.

## Why geometry waits

An integer translation plus input-only common crop remains the smallest
subsequent map integration. Exact sample reindexing can preserve the declared
white generating law and use only current-frame preparation. Its independent
truth must name output origin, map direction and each frame's prepared values;
poisoned outside-crop invariance and illegal support must fail. A final
InputRange image alone can conceal an incorrectly mapped contributor.

Combining maps with the first dynamic-shape change creates two new addressing
failure sources. Remove hardcoded intake/output restrictions first.

Fractional RGB sampling waits longer: output variance depends on squared
weights, while neighboring outputs share weighted inputs. Identity variance
does not describe the resulting spatial covariance; clamped cubic is also
content dependent. Existing frame_beta is an injection seam, not a calibrated
RGB resampling solution. Never silently reuse identity24/white BandGain, derive
a new scene noise estimate inside each stage, or fit until census counts look
familiar. Sampler coordinate repair does not establish this noise contract.

No new corpus/model intake, physical calibration, external comparator
equivalence, quality score/default change or performance sweep is proposed.

## Secondary-hit inventory and scope read (2026-09-08 addendum)

The first query's exact secondary report names were BUILD-SHARP.md,
ORCH-veiling.md, M107b-lateral-correction.md, M95-resample.md, BUILD-TRIAGE.md
and BUILD-CROP.md. The second query's were M20-VERIFICATION.md,
M126-composite.md, M181-m4-feasibility.md, M-COVER-NATIVE.md,
M152-site-census.md and M12-shrinkage-measured.md. All are under docs/research/.
The matching passages were read before the new implementation contract:

- BUILD-SHARP section16.6 qualifies its frame-count noise separation because
  the arms used different geometry; it does not calibrate this RGB law.
  ORCH-veiling sections8/105 discuss different captures and warn that different
  subjects/counts/binaries cannot be called an improvement. Neither is a
  variable-cardinality TIFF software admission.
- M107b-lateral-correction section1 records corrected application direction
  and composition into the existing gather. M95-resample sections2/3 rejects
  the two-resample story and distinguishes fractional phase from zoom size.
  BUILD-CROP sections2-4 distinguishes native-scale crop from stretching and
  reports chroma's failed identity null. These constrain the later map task;
  this identity RGB extension adds no CFA co-siting or resampling.
- BUILD-TRIAGE sections5/8.5 treats master-width variation as packaging, not
  an alignment or stack-depth diagnostic. New dimension admission likewise
  makes no quality/coverage inference from count or output shape.
- M20-VERIFICATION section4's common-count comparison rejects a rig-wide
  noise assertion. M126-composite sections3b/12.5 shows short populations can
  leave across-frame gates inert. Therefore N<=8 proves only the declared
  consumer/fixed merge path, never potency of deep-stack native gates.
- M181-m4-feasibility opening/section1 and M152-site-census sections1/next
  capture recommendations retain real common-TIFF, calibration, transfer and
  eligible-site gaps; frames are not independent eligible sites. They are
  not closed by generated RGB fixtures or flexible dimensions.
- M-COVER-NATIVE amendments distinguishes native size from native scale and
  retains comparator/common-TIFF obligations. M12-shrinkage-measured section4
  retracts a frame-count-derived step ratio as an arithmetic identity. The
  extension infers neither physical spacing nor placement from its N.

No new numerical evaluation or campaign gate followed these source reads.

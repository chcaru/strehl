# Common-TIFF stack-to-image integration

2026-09-08. **MEASURED and independently VERIFIED within the fixed software
scope.** The new manifest-driven consumer folds three ordered128x96 RGB16
frames, finishes the shared three-plane merge and writes already-linear
ProPhoto/D50 TIFF. All twelve registered product cases, sixteen original
saved-data controls and six path-association controls pass.

This completes the bounded multi-frame common-RGB consumer. It establishes
neither photographic quality nor physical RGB noise calibration, real geometry
or comparator equivalence. HardFloor and native merge defaults are unchanged.
M194h's completed causal experiment remains separate and is not repeated.

## Actual result and what passed

The final independent result is
[verify2 result](../../experiments/common-tiff-stack/verify-2/check/result.json),
9134 bytes/SHA256
dc56084ebe1d4ff900e07b5bd0fa903439003bf51b11f1addcba123b0a184692,
committed with actual transport/source evidence at4f085b86.
It reports PASS_COMMON_RGB_STACK_SOFTWARE_INTEGRATION with no failures.
The separate [independent final review](../../experiments/common-tiff-stack/work/independent-final-review.md)
re-chooses interpretations and audits the actual saved command/result chain
without rerunning the checker or product.

| Fixed population | Verified outcome | Scope and failure direction |
|---|---|---|
| Three distinct constant frames | Every output RGB is exactly(17000,23000,29000), unlike every input; all three distinct input identities and immutable fold receipts agree | Copied reference, omitted/duplicate contribution and wrong divisor can fail. The literal mean and consumed population are both required. |
| Three identical asymmetric address/color frames | All36864 RGB16 samples equal their independently calculated values | InputRange makes this an exact addressing/color oracle; it cannot certify unconstrained pyramid reconstruction. A shift, channel swap and extra transfer curve are rejected. |
| Identical mixed noiseless frames | All36864 samples equal the literal mixed flat/textured input | Null checks transmission, not photographic quality. |
| One fixed noisy population, off/on/placebo | Complete TIFF and independently decoded pixels are byte-identical | Both gate census and output observer participate. A real altered-pixel TIFF is rejected by the same comparison. |
| Unsupported noise, variance1, profile and camera-native output | Four specific semantic refusals, each with zero folds | Correct process failure must agree with the exact reason and incomplete prefix. |
| Wrong-size and altered third payload | Each refuses after exactly two completed folds, with no admitted output | Tests a late failure after real work; an early refusal cannot satisfy it. |
| Original sixteen checker controls | All pass their positive/restoration or exact negative disposition | Includes actual ICC/pixel mutations, contribution and literal-color destroyers; not mere rehashed descriptions. |
| Six new path controls | Supported same-file spellings pass; different same-content file, wrong extent and wrong digest fail | Contents alone cannot establish file-path identity. |

All six positive outputs retain the exact548-byte linearized ProPhoto/ROMM
primaries D50 profile, authenticated separately from literal color samples.
The product does not redevelop these values through black subtraction, white
balance, demosaic, camera matrix or transfer curve. This evidence applies to
the declared simulated producer; it does not rescue the previously failed
external comparator's profile behavior.

The noisy off/on/placebo TIFF hash is
e17cb1701346694b2509c8fa5605dbaea92168415d8ca3422983855b20a50e0e;
its pixel hash is
f2a9dd6ec2f3f6a53b47241e88d7651b3e95ddb8a9d47d538a001614b296b08f.
The product also retains equal prequantization f32 digests in these arms.
That is a retained product witness; the independent TIFF reader does not
reconstruct unsaved floats from quantized pixels.

## Noise and gate interpretation

The input law is simulation-only: independent per-channel +/-8 code values
around a fixed signal, with no generating clip. Channel variance64 and proxy
variance24 for (R+2G+B)/4 are DERIVED from that law. Actual constant f32 variance
arrays, selection-proxy arrays, their before/after hashes and the passed core
white BandGain values are checked. This validates the software handoff, not a
camera constant or an empirical independence claim.

The checker excludes the always-mean base from its mixture test. The separate
review re-chooses a stricter descriptive view: every Laplacian level has both
zero and positive accumulated denominators after each of the three folds.

| Laplacian level | Fold1 zero / positive | Fold2 zero / positive | Fold3 zero / positive |
|---|---:|---:|---:|
| 0 | 5644 / 6644 | 5619 / 6669 | 5599 / 6689 |
| 1 | 1260 / 1812 | 1213 / 1859 | 1164 / 1908 |
| 2 | 284 / 484 | 267 / 501 | 260 / 508 |

These are counts in the identity common-RGB grid at each level, shared across
RGB planes. They do not locate newly admitted pixels, establish independent
threshold correctness for each contributing frame, or measure image quality.
No sharpness metric, spatial-SD noise claim or statistical confidence interval
is used for this deterministic software commission.

## Failures preserved and exact execution

Build1 exceeded its3GiB Job limit before producing an executable. Build2 used
two Cargo jobs, stayed within memory and exposed three digest-formatting
compile errors. Build3 corrected only the digest encoding and unused import,
then freshly compiled the product. Both failed builds remain preserved.

The original saved verifier rejected every case before pixel admission because
Rust's extended Windows local-drive path spelling differed from Python's
ordinary spelling. That failure is preserved at47a39191. The separate verifier2
normalizes the supported spelling while preserving path/extent/SHA association,
and runs six new metadata controls. No product image or fixture was rerun.

The exact commands and local source/input bindings live in these committed
releases. Controller source/contracts define the sanitized environment and
stage results retain its observed settings; this is not a hermetic toolchain
or external-dependency certificate. These commands ran once per version:

| Stage | Source / release commit | Actual invocation record |
|---|---|---|
| Fresh build3 | 6853c9d7 / 87329ffe | [build release](../../experiments/common-tiff-stack/work/build-release-3.json) |
| Fixed fixture preparation | Same producer156 map / f946b842 | [prepare release](../../experiments/common-tiff-stack/work/prepare-release-1.json) |
| Twelve product runs | Same producer156 map / a101319c | [render release](../../experiments/common-tiff-stack/work/render-release-1.json) |
| Refused saved verifier1 | Same producer156 map / 747d9923 | [original verify release](../../experiments/common-tiff-stack/work/verify-release-1.json) |
| Corrected saved verifier2 | 5d5ce564 / f55d13ab | [verify2 release](../../experiments/common-tiff-stack/work/verify-release-2.json) |

The interpreter is
C:/Users/chris/AppData/Local/Programs/Python/Python312/python.exe with -I -S -B.
Product commands are the exact ordered manifest cases under
C:/dev/blog/death-of-software/projects/strehl/experiments/common-tiff-stack.
The environment fixes RAYON_NUM_THREADS=2, removes the listed STREHL_/M194H_ and
worker overrides, and uses offline Cargo. All merge settings and input/output
semantics are explicit in the closed manifests and source contract.

Actual build log contains Compiling strehl-cli, a unique non-test fresh:false
artifact and build-finished success:true. The copied executable is3186688
bytes/SHA256
67a044128cbd5bc230ac1d67e97fe4e2398d0d91be075632a62168a53b52c30e.
The executable is retained locally and is not committed or distributed.

Every product child has its expected exact exit, EOF and terminal Job active0.
Verifier2 final equals actual raw child output; child/controller both exit0,
no emergency termination or cleanup error. Its actual child Job CPU is0.484375
seconds plus parent sample1.390625; external whole wall2.0 seconds. These are
accounting observations, not a speed benchmark. The fixed tail and full original
failed allocations remain charged as recorded in verification_history.

All164 exact execution sources survive in the compositional source archive:
producer archive1 plus deltas2/3, then verification-source-2-delta.zip135706
bytes/SHA256
6c3d292b2e606cafc4270769a0b59c972916583fa9c0b81a44f913cea0da3a3d.
Before-write and readback equality cover5344883 source bytes. The archive is
the historical authority after later product edits.

## Rule checklist and next implementation

Rules1-3: u16 input storage, f32 arithmetic, one streamed frame/workspace and
injected variance are in common-stack::process and the actual consumed receipts.
Rule4: existing configured HardFloor merge; no raw-argmax analysis.
Rules5-7: identity common-RGB gauge, no fitted geometry or RAW buffer statistics.
Rule8: committed actual releases, exits and saved results above.
Rule33: build-3/child-00.log contains actual Compiling strehl-cli, fresh:false
and build-finished success:true; the copied executable hash matches.
Rules9-10,13,16-18,21,23,30,34,39: no sharpness/temporal-sigma, fitted calibration,
parameter sweep, timing comparison or scientific ratio; simulation scope stated.
Rules11-12,20,24,26,35-36: independent checker, actual destroyers, separate
interpretation review, powered mixture and off/on/placebo byte equality.
Rules14,32,45: no capture-tree or RAW decode/registration operation.
Rules15,19: explicit coordinate/color terms and kebab-case owned new files.
Rule22: this checklist links each applicable requirement to its code/record.
Rules25,28,31,31b,37,41,44: no numbered milestone allocation or SYNTHESIS fold.
Rules27,46-47,49: owned bounded processes, raw exact exits, full invocation and
environment, no peer-process termination or host-exclusivity claim.
Rules29,38,42-43: source-content review and the next-consumer proposal address
the one-file audit; exact-path commits checked against working bytes, original
source/failed outputs preserved; no unsupported absence or visual verdict.
Rule40: the common-consumer proposal cites M165, M189 and the output audit, but
a pre-commission mechanical prior_art.py run was not recorded in this packet.
That process gap is retained. Before the next sampler commission, root actually
ran prior_art.py sample_checked bilinear CatmullRom boundary clamp (exit0); its
M136 and clamp-default findings must accompany that next brief.
Rule48: no visual quality verdict.

ARGUED next task: investigate the checked sampler's source-derived high-edge
coordinate discrepancy before widening RGB geometry or input sizes. The
[prospective note](../../experiments/common-tiff-stack/work/next-sampler-boundary.md)
names the native consumer, grid, fixed failure-capable controls and repair
tradeoffs. It is still unexecuted. The low-level sampler is not used by this
identity RGB commission, so the finding does not explain these outputs.

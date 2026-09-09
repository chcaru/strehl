# M194h: sub-floor mass explains one sparse error, but the cutoff loses broader benefit

2026-09-08. **MEASURED and independently VERIFIED, development experiment complete.**
Evidence revision: `6d61340de1670b68a65fd5ee27dfd7a65dfc30a0`.
No SOTA axis or production quality change is admitted.

The fixed cutoff intervention reduced the selected primary red error from
43.687 to 0.040 DN. It also restored the predeclared secondary defect and worsened
every RGB fixed-window MSE relative to the pedestal arm. The causal question
succeeded; this global cutoff does not earn a product change. Keep HardFloor as
the default and advance the missing common-TIFF stack-to-image consumer.

## What was held fixed

[Root decision](../../experiments/m194h-pedestal-causality/experiment-decision.md)
and [preregister](../../experiments/m194h-pedestal-causality/preregister.md)
preceded execution. H is unchanged HardFloor; P is unchanged FloorPedestalV1.
P0 preserves P's actual above-floor weight bits and changes only E<=F weights
to positive zero before the actual weighted accumulation. Denominator calculation
is unchanged; denominator values change with the intervened weights. All-frame mean fallback, base band, exponent, injected noise, frame order,
geometry, gather, CFA inverse pyramid, InputRange hull, MHC, WB and writer remain
fixed. The hook is available only through the explicit ignored experiment test
and feature `m194h-pedestal-causality`; normal defaults do not change.

The input is the existing five-frame 320x240 u16 CFA flat seed743 and its existing
noise-free null. There is no new RAW decode or completed-matrix replay.
The consumer merges four CFA quad planes, then reconstructs native 300x226 RGB
at crop offset (10,8). Both sites are previously selected discovery cases.
The fixed native window is x=[104,216), y=[104,136), 3,584 pixels per channel.
Site errors are red-channel DN; window MSEs are DN squared in their respective
RGB channels after the common output conversion. Neither is expressed in RGB16
code values or CFA-plane displacement.

## Paired outcome

| Arm | Primary red (202,104), absolute error DN | Secondary red (205,113), absolute error DN | Window R MSE DN² | Window G MSE DN² | Window B MSE DN² |
|---|---:|---:|---:|---:|---:|
| H | 0.040251 | 117.174851 | 308.575865 | 293.879451 | 343.732151 |
| P | 43.686979 | 35.611106 | 191.094146 | 133.829836 | 210.848757 |
| P0 | 0.040251 | 117.174851 | 302.464460 | 284.911129 | 336.158181 |

**Metric failure direction:** MSE can reward flattening real texture. This flat
development case measures paired error, not texture preservation or overall
quality. One noisy realization supplies no repeat distribution, confidence
interval or temporal sigma. The selected sites are not independent replications.

P to P0 changes greater than 10 DN in absolute ideal error:

| Channel | Improved pixels | Worsened pixels |
|---|---:|---:|
| R | 61 | 320 |
| G | 25 | 362 |
| B | 65 | 317 |

The primary signed error moves from +43.686979 to -0.040251 DN. The secondary
absolute error worsens by 81.563745 DN. P0 exactly reproduces H at these two
pixels, but is not globally equivalent to H: the fixed-window values differ.
The common flat ideal is approximately (3000.000089,3000,2999.999928) DN;
the textured `scalar.npy` is not the flat ideal.

## Why this is causal evidence, and its limit

The independent reader checks every frame's actual classification, weight,
numerator, denominator, fallback and coefficient over the complete inverse
support and signed MHC dependencies. Its positive guard
`science.trace_consumer.primary_has_actual_removed_mass` is true.
At level0 index7296 alone, the intervention removes positive weight from frames
0,2,3,4, or 79.753940% of P's total weight there. This row has a nonzero inverse
coefficient and no mean fallback. Other levels also contribute; that percentage
is not the fraction of final pixel error explained.

The unchanged hull mediates the selected result. The primary CFA operand before
the hull is P=2282.684570 and H/P0=2249.643555. The same [2250,2313] input range
clamps H/P0 to2250. Near-zero final error therefore does not prove universal
ideal recovery by the cutoff. It proves the stated intervention reaches the
actual consumer and removes this selected excess under the fixed pipeline.

The saved checker rejected three actual corruptions: a classification word
flip, deletion of nonzero primary support, and doubling a positive P weight.
Restored rows/support and hashes match. These controls test the independent
reader's power; they do not calibrate the physical camera-noise constant.

## Executed population and independent completion

Exactly 26 component merges and 130 frame folds completed, plus the rejected
entry control. Exactly twelve render invocations completed in the original order:
noisy H off/on/placebo, P off/on/placebo, P0 off/on/placebo, then noise-free
H/P/P0 off. There was no parameter sweep or extra seed.

Whole-TIFF bytes match for each arm's off/on/placebo triplet. H and P also match
their archived M194g baselines; all three noise-free outputs match the old null.
Each noisy TIFF is 407,403 bytes:

| Arm | SHA256 |
|---|---|
| H | `a1b6be484b9f13914c95a03d60fb80ef02761b935f478ffb3eed8b9e18704874` |
| P | `36a995a53f842077bd9ffa0ad705a8da3af432c28c42a8da3793bce4513a8372` |
| P0 | `f04cf4568be2ced6406b2176b5015a6a9b20274b7a454bd0e8fed8d1549a9303` |

The [actual independent result](../../experiments/m194h-pedestal-causality/independent-check-1/result.json)
is 73,974 bytes, SHA256
`38ba525e7480887a4e9ae527aa122b03e2791edd66423fc1724bde560774dc83`.
It records `PASS_INDEPENDENT_SAVED_CONSUMER_CHECK_ONLY`,
`subject_complete=true`, `independent_complete=true`,
`verified_science_complete=true`, and `quality_go=false`.
The actual child log is byte-identical to that JSON. Actual wrapper and child
exits are0, direct-exit/EOF/drain complete, final owned Job active count0, with
no termination or cleanup errors. Actual whole-wrapper wall is4.672 seconds.
Resource observations establish completion, not a performance comparison.

A fresh reviewer who authored neither the hook nor scientific checker
[re-chose the interpretation](../../experiments/m194h-pedestal-causality/work/independent-result-review.md):
selected primary versus secondary versus the fixed all-RGB window. The narrower
mechanism survives; the apparent product conclusion reverses.

## Commands and retained revisions

Commands actually run, from repository root, using
`C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe`
and absolute script paths:

```text
python.exe -I -S -B experiments/m194h-pedestal-causality/capture-stage.py build
python.exe -I -S -B experiments/m194h-pedestal-causality/capture-stage.py components
python.exe -I -S -B experiments/m194h-pedestal-causality/capture-stage.py render
python.exe -I -S -B experiments/m194h-pedestal-causality/work/check-run.py --release experiments/m194h-pedestal-causality/work/independent-release-1.json --release-sha256 79a8aa4ae9f5fe97115475f8365683c418e331fdede80b4fa7812c9e9b096e09
```

The displayed paths are shortened; exact argv and raw streams are in the
committed external records. Build3 used `cargo test --no-run --locked --offline`
with the explicit feature, separate target directory and JSON compiler messages,
then copied both freshly compiled test executables and listed them. Actual
`Compiling`, `fresh:false` and successful build-finished records are retained.
The executed ignored tests are
`pyramid::m194h::controls::fixed_threshold_null_and_observer_controls`
and
`merge_cmd::known_scene_benchmark::noise_pupil_bridge::pedestal_causality::m194h_fixed_pedestal_case`.
Actual checker argv is in `independent-run-1/child-00.json`; it ran once.

| Evidence | Committed revision |
|---|---|
| Final scanner/build3 source | `c851dba0` |
| Successful build3 and component release | `830a74c5` |
| Component results and render release | `6740bf09` |
| All twelve renders/traces | `fbcb3e0b` |
| Independent release and producer-source equality | `750b9b7b` |
| Independent results/review and exact source archive | `6d61340d` |

Before any next implementation edit, all140 frozen source bindings
(5,005,692 bytes) were archived and verified before writing and after reading
the archive. [Archive receipt](../../experiments/m194h-pedestal-causality/work/frozen-source-3-archive.json)
binds the 5,048,639-byte ZIP and SHA256
`7d42366db16300b7c4419ddc855e539b3f61d5212bed33ab1e80438f0af6991f`.
This preserves exact dirty working bytes without importing unrelated edits into
their original Git paths. Compiled executables remain local and are not shipped.

Two failed builds and initial preparation refusal remain failures. Build1 had
a surviving owned process after compiler exit/EOF and was terminated within its
contract. Build2 returned FileNotFoundError during live scratch observation.
The latter historical cause remains unverified; a controlled disappearance
fixture commissioned the narrow scratch-only scanner correction. Windows file
identity controls retained full within-API checks while removing cross-API
ctime equality. Successful build3 and all later stages retain actual terminal
accounting. No failed charge was refunded or relabelled a pass.

## Executable discipline and decision

Relevant AGENTS checks were executed on their own consumer path:

- Rules1-7,10,15,23,32: existing u16 CFA inputs, f32 arithmetic, injected noise,
  no new geometry fit/aligned-frame buffer/RAW decoder, complete CFA consumer;
  no temporal-noise, speckle or bare alignment-pixel claim. No GPL source read.
- Rules8-13,17-21,24,30,34-36: fixed decision/preregister plus the exact component
  test; independent `cross_arm`, `metadata_faults` and `diagnostics` in
  `independent-verify.py`; exercised removed-mass guard, flat ideal, secondary
  and full window. No sharpness quality metric or self-calibration claim.
- Rules12,24: separately authored checker and saved result-interpretation review.
  Verification changed the assessed region, not only recomputed the same number.
- Rules16,27,33: no timing sweep; actual owned Job completion and fresh compile
  records. Build failures remain visible, with no inference from file silence.
- Rule26: actual off/on/placebo whole-TIFF equality for H, P and P0.
- Rules14,25,28-31b,37: no corpus-write/census or SYNTHESIS fold in this milestone.
  Exact-path commits bind source/evidence; report/program edits retain headings.
  Proposed facts receive no absolute numbers here.

**ARGUED program decision:** do not automatically promote the successful local
diagnosis into the previously contemplated seven-seed P0 quality arm. The
predeclared secondary and whole-window outcomes show the tradeoff that arm
would have to address. Close this experiment and implement the
[common-TIFF consumer](../../experiments/review-output-adapter/next-consumer-proposal.md)
under an explicit simulation-only RGB noise contract and known identity grid.
A future pedestal question must separately predeclare average-versus-sparse-tail
error and texture-collapse controls on independent repeats. Neither P nor P0
becomes the current default.

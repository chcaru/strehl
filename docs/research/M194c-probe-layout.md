# M194c — probe noise follows image coordinates

2026-09-07. **MEASURED and independently verified within the declared software
scope.** The measured gate-floor probe now assigns its existing random sequence
to consumed photosites in active-relative row order. Unused decoded-buffer
padding, origin, stride and odd trailing sensels no longer choose the noise
draws in the image. This repairs M194b's demonstrated storage dependence.

**Decision: accept the storage correction, with a recorded quality regression.**
The fixed flat fixture's full-stack green temporal variance increases **2.538%**,
crossing the prospective 2% engineering review trigger. A sparse adverse pixel
movement reaches **461 TIFF LSB / 104.447 post-WB DN inside the scored ROI**.
Neither result is waived or relabelled a pass. This is not a noise or image-quality
improvement, and no SOTA bar or default quality parameter changes.

The reason to accept the implementation is the independently demonstrated
invariant: equivalent image data must have the same result regardless of unused
storage. The old layout chose an arbitrary probe realization. Canonical packed
order preserves the old packed sequence and gives every equivalent layout that
same sequence; retaining one padded layout's favorable noise reading would not
establish a preferred physical model. This is an engineering tradeoff, not a
proof that its cost is negligible. The regression and isolated excursions remain
inputs to subsequent admission/probe work.

## Source boundary and prior work

M194b's benchmark and failed padding control are committed at
`444eb759be0358cda25e97d4375f977a039efe6a`. Its report, inputs, executable and
forty baseline TIFFs are preserved. M194c was allocated in AGENTS before
dispatch, and product edits waited for that commit.

The prior-art search and applicable records are listed in
[`preregister.md`](../../experiments/m194c-probe-layout/preregister.md):
BUILD-GATE/2/4, V-GATHER, M77, M69, M98, M48, M71, M189, ORCH-veiling,
M87, BUILD-SHARP, M111, M70 and A-prior-corpus, together with M194/M194b
and the relevant SYNTHESIS architecture/floor records. Their calibration,
quality and instrument refusals remain. This repair changes storage traversal,
not those models or their acceptance decisions.

Only `crates/strehl-cli/src/merge_cmd/gatefloor.rs` changes in product source.
Its final SHA-256 is
`bcea35986c73011c20d872bddc9c0ef3ea9354101259bd3952c16976bb1c9496`.
`Probe::run` calls a private helper using the existing validated full quad
geometry. The helper supplies a mutable iterator over the complete consumed
native extent to `fill_noise`. The RNG body, frame-index seed, Box-Muller spare,
mean/sigma, quantization/clamp, WB metadata, luma mean removal, denominator,
pooling, band limits, scaling and merge arithmetic are unchanged.

**VERIFIED by source comparison:** the helper introduces no full-frame array.
The existing clone remains. This is not a memory or speed measurement.
Both gather implementations consume complete quads; odd active tails remain
untouched and unconsumed. The source sequence uses full geometry, so choosing
an analysis Crop does not redefine the synthetic photosites.

The implementation author was implementation_audit. directional_detail
independently re-chose sample/layout/warp/WB and delivered-output controls.
root authored the fixed across-version comparison, independently checked by
roadmap_audit. The independent probe preregistration discloses that its final
write followed a source read of the new helper; its alternative choices and
semantic corrections preceded implementation. It is not represented as blind.

## Controls and limits

| Property | Evidence and falsifier |
|---|---|
| Packed lineage | Original fill function frozen verbatim; exact packed sequences match at independently chosen extents/seeds. The original traversal disagrees under relocated storage, proving the equality check can fail. |
| Consumed sites | Rechosen non-square buffers, odd origins/tails and poisoned unused addresses; every consumed value matches and every outside value remains unchanged. Changed seeds alter the sequence. Malformed storage refuses before writing. |
| Actual probe | Both native-plane and full-resolution gather processes; 160 independent layout comparisons across whole/Crop and nonlinear scale/rotation/translation placements agree by f32 bits. Seed/warp controls are live; WB changes beta on fullres and is inert on plane gather as expected. |
| Actual TIFFs | 48 independently decoded outputs exercise whole/Crop, both gathers, packed/relocated/odd-tail/poisoned layouts. Equivalent layouts match whole TIFF bytes and pixels; real source-site, broad image, noise-model, WB and warp changes remain live. |
| Fallback scope | Empty normal beta is exercised. Direct pooling/NaN injection is labelled separately. Corrected component controls show None/empty length fallback equality with a live finite-floor control. A raw NaN slice passed directly into the core is a fault input, not production's finite-prefix contract. |
| Version comparison | Same fixed 20 input/settings cases as M194b, producing 40 outputs; all 80 old/new TIFFs independently read. Eleven pure comparison checks, actual-TIFF offset/blur/color/noise controls, six supplementary-source corruptions and twelve coherently rehashed controller contradictions are recorded separately. |

Requested independent depths3/6 realize the same two measured betas on the
274x190 fixture. They are not independent realized-depth replications. Ordinary
valid measured levels have two descendants of extent at least8, so the small-band
NaN suggested in the first design cannot occur there: minimum measured extent29
leaves at least529 pooled samples, above256. Tiny valid images instead give an
empty beta. A synthetic plant validates these operations, not camera calibration.

The independently tried stats-on/placebo flags are **inert options on the
prepared Pyramid path**. Their byte identity does not prove active observer
non-perturbation. M194b's separately exercised confidence observer remains its
own evidence; this repair adds no new product diagnostic.

Full independent detail and raw records are in the
[probe review](../../experiments/m194c-probe-layout/independent-report.md),
[fixed-benchmark comparison review](../../experiments/m194c-probe-layout/independent-comparison-review.md) and
[author report](../../experiments/m194c-probe-layout/author-report.md).

## Fixed production comparison

All M194b producer files, synthetic coefficients, nonlinear frame-4 geometry,
settings, masks, targets and scoring functions remain byte-unchanged. The
consumer uses three bands, gate2, Catmull-Rom, two workers, measured floor,
full-resolution MHC and CameraLinear. This is the registered small development
fixture, not the default-seven-band or native-capture certificate.

Output remains 284x212 at canonical native offset(18,14), corresponding to
quad Crop(9,7,142,106). Every primary score uses canonical x[64,256),
y[64,176):21,504 pixels. Error units below are black-subtracted, post-WB
camera-linear DN. Temporal statistics use eight independent input-noise repeats;
uncertainty uses whole-repeat pairing, never a pixel-independence assumption.

| Green, full nine frames | M194b baseline | M194c |
|---|---:|---:|
| Flat temporal sigma | 13.5384 | 13.7092 |
| Plane temporal sigma | 9.75525 | 9.73595 |
| Noisy plane RMSE vs optical observation | 14.1822 | 14.1307 |
| Noisy plane RMSE vs ideal latent scene | 69.9162 | 70.1291 |

The flat full-nine temporal-variance ratios are R **1.021368**, G **1.025380**,
B **1.019181**. The green variance difference is **+4.65196 DN²**, with paired
delete-one-repeat jackknife SE **0.88654 DN²**. Its mean-MSE difference is
**+4.60825 DN²**, SEM **0.87045 DN²**. This is an observed regression, not
agreement with zero. Plane green temporal variance changes **−0.376083 DN²**,
jackknife SE **0.027486 DN²**, while ideal-target MSE increases
**29.82196 DN²**, SEM **0.19320 DN²**. Opposite signs on different quantities
cannot be pooled into one quality verdict.

Across all paired rows/targets/channels, ROI RMSE changes range from
**−0.215026 to +0.278286 DN**. No 1-DN RMSE or noise-off-wave-loss review
trigger fires. The 2% variance trigger does fire, and remains present in
[`comparison-2.json`](../../experiments/m194c-probe-layout/comparison-2.json).
These were prospective engineering review triggers, not new acceptance bars
for the SOTA scorecard. Small numerical shifts are not automatically evidence
of improved fidelity; M194b's finite numerical-accuracy restrictions still apply.

**The mean does not bound individual harm.** The largest observed movement is
red at canonical native(142,170), flat repeat709/full9, inside the fixed ROI:
**2997.01448 to 3101.46139 DN** against approximately3000 DN truth. The
104.446906-DN movement worsens that pixel's truth error. The independent
post-comparison diagnostic counts672 of64,512 ROI components moving by more
than10 DN in that pair; this descriptive threshold is not an added pass bar.
See `independent-comparison-extremes.json` for its coordinates and evidence.

Nineteen of40 outputs change;21 are whole-TIFF byte-identical, including all
twenty single-input outputs and the noise-off flat full stack. The two complete
M194c runs also produce identical whole TIFF bytes in every case. The second
run binds final test/reader corrections; it is not an independent noise replicate.

## Reproduction and evidence binding

Final controller SHA-256:
`460bcec07f4fb7df28af519b3a6becb4dc789ca55e571007d5b97bc418332bce`.
Final build record SHA-256:
`64975e805b77552f81158424de066bc26903170372af61b84cf394d6743e643f`.
Final 60-command run index SHA-256:
`71b2ba05ddc23fc78640aa1f9b53ea3b12ddac0f1fa955d1ee8cdf8428fda6ab`.
The exact build/render/score invocations, compiler/copy bytes and source maps
are recorded under `experiments/m194c-probe-layout/candidate-2/`.

```text
python -X utf8 experiments/m194c-probe-layout/run-candidate.py --out experiments/m194c-probe-layout/candidate-2
python -X utf8 experiments/m194c-probe-layout/compare-candidate.py --controller experiments/m194c-probe-layout/candidate-2/controller.json --controller-sha 460bcec07f4fb7df28af519b3a6becb4dc789ca55e571007d5b97bc418332bce --out experiments/m194c-probe-layout/comparison-2.json
```

Use fresh output paths on a rerun. The frozen M194b runner/scorer are reused,
not copied into a second implementation. A supplemental attestation binds the
new external Rust includes and exact root comparison/controller sources around
the whole build/run/score operation; the original reader does not itself check
those additional includes. The verifier checks their union with the original
compiler inputs, snapshots, exact commands, original producer identity, and
actual TIFFs. External trusted digests remain a provenance boundary, not an
authentication system for wholly fabricated records.

## Retained failures and final checks

- First compile: independent test digest formatting used an unsupported
  sha2 API. The failed log/source hashes remain in author-run-1.
- First fallback-power check: a direct BandMerge fixture reused the first
  frame's cached pyramid because it omitted `FrameWorkspace::next_frame()`.
  A proposed attenuation explanation was unconfirmed and is withdrawn.
- An additive checkerboard also failed through that same lifecycle mistake.
  The original omitted-reset case remains an explicitly named expected failure;
  the corrected additive arm changes only the API use and NaN contract, not
  gate/noise thresholds or scored inputs. It returns the known mean3052/2948
  under forced averaging and3110/2890 under selection. Both failed runs remain.
- One verifier run refused before tests because a subsequent rebuild replaced
  the original compiler-artifact path. Its pinned copy was unchanged. The
  terminal build was checked after compilation finished; the refusal remains.
- Root's first version comparison refused a tuple/list mismatch introduced by
  JSON serialization of the domain. It found zero numerical differences. The
  comparison now normalizes JSON containers, keeping exact scalar equality;
  `comparison-first-failure.json` retains the diagnostic. No score formula or
  tolerance changed. Earlier coordinate/include review corrections are recorded
  in `comparison-design-corrections.md`.

Final CLI tests: **136 passed,0 failed,2 ignored**, with visible recompilation.
The ignored fixture tests are invoked separately. Final author controls pass
four tests in each gather; independent controls pass five in each gather,
including the named expected-failure regression. Changed-line formatting and
Clippy pass with rebuild/checking evidence. The lint-only build stamp used to
force its check does not describe an image executable. Inherited full-file
formatting and unrelated repository lint debt remain outside this change.

No real RAW file, capture, holdout, historical certificate, scorecard or
SYNTHESIS fold changes. The source-only empty-beta debug-indexing observation
remains an unmeasured follow-up. The primary quality work now has actual-output
truth/noise evidence, including sparse adverse flat-pixel behavior, against which
to develop the admission change; this repair does not close that work.

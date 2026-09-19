# Independent placement-consumer review

## Source review

VERIFIED by source inspection, before root's numerical and photographic runs.
Reviewed correction implementation SHA256:
`fb123d6f37bb68add6ef0ca290ce7e473b8fdaaf7783dd176f9c98ac3ae6203c`.
Initial passing independent generated controls SHA256:
`2eb38421a270daaeb46eca310c51c92df80a13ca30ee250782e907af19f02727`.
Strengthened passing controls SHA256:
`3d3acd2ad2751be810d3bd2d1d552b41f77ced52988d961115abecec4c84531b`.
The verifier wrote these controls and did not build, run them, or read original
RAW files. Runtime results must come from root's separately recorded commands.
Root's first build rejected an array-map expression inside the verifier's
`json!` input. Computing that expression before the macro repairs test syntax;
no criterion, fixture value, production source, or image arithmetic changed.

The new direct-gather wrapper prepares the correction before either existing
CPU or GPU gather writes the destination, then applies the same prepared
correction afterward. Both actual merge and synthetic noise probe already enter
this wrapper. The probe's two-green-only output can therefore receive exactly
the same per-site geometry as the actual frame's green planes. The generated
controls separately compare those two invocations; source inspection alone is
not the corresponding numerical result.

The correction evaluates a separable cubic smoothstep at the full reference
native coordinate of each CFA site. Its first/last support sites have weight
zero; exactly 32 sites in from an edge the weight reaches one. Source-native
delta times weight enters the plane translation divided by two, before the
existing per-channel CA composition. It changes a source coordinate before one
Catmull sample; it does not blend two shifted images. MHC reconstructs a small
unaligned patch with its origin rounded down to an even native coordinate, so
the original active-area RGGB phase survives an odd decoded buffer origin.

The source bound includes both Catmull's floor-minus-one through floor-plus-two
stencil and MHC's further radius two. Finite coordinates and complete support
are checked while preparing the picks, before base destination assignment.
The patch includes floor-minus-three through floor-plus-four, with its upper
extent exclusive. Corrected output values are accumulated and checked before
any corrected sample is assigned. The patch uses the original u16 frame and
f32 arithmetic; no aligned image stack is stored and no private noise model is
introduced.

Configuration binds a canonical absolute source directory, frame count, native
geometry, filenames and all four original f64 transform words. Production
preflight validates every configured filename and transform against the map
before the merge. There is no correction for an absent entry or exact zero
delta. The feature remains default-off. It refuses unsupported interpolation,
directional demosaic, and the probe's separate identity-transform debug mode.

## Scope of the controls

The disabled runtime test enters the actual direct wrapper. Enabled numerical
tests enter the explicit configuration/CA preparation seam and its actual apply
method. Thus an enabled production environmental-dispatch or metadata-resolution
mistake remains a root runtime validation responsibility. The independent
uniform reference bypasses the new wrapper, using the existing full-frame CPU
MHC, Catmull and rounded sink. Independent expanded affine equations avoid
using that reference's transform arithmetic as the sole oracle.

Outside-support bit identity is an assertion about gathered planes. The complete
pyramid may propagate a local input change beyond that rectangle. Likewise,
putting the same correction into the noise probe preserves the consumer path,
but its band gains are spatial aggregates; this does not establish a calibrated
per-pixel noise estimate inside the small corrected area.

Photographic improvement, persistence through all seven bands and 299 frames,
transfer to another subject, and SOTA quality remain unverified by these
generated controls. No gradient magnitude is used as evidence of quality.

## Root's completed generated run

MEASURED by root; independently checked against the complete saved log,
invocation, source receipt and process result. The command was:

```powershell
experiments/full-context-placement/build-2/cli-tests.exe local_placement::independent_controls:: --nocapture --test-threads=1
```

All five tests passed in `controls-2/process.log`. The test executable is
SHA256 `e76e89133343aad4379c93cafe7b32b78696a8d15ca039c8b1fcccdf4d82f645`;
`build-2/process.log` records `Compiling strehl-cli`, then successful completion.
The invocation used eight Rayon threads and no STREHL environment overrides.
Source hashes agree with the reviewed implementation and controls above.

The affine case checked 114,288 zero-weight samples, 107,584 full-weight samples
and 44,516 transition samples. Wrong sign disagreed at 143,277 samples, doubled
translation at 139,055, and swapping the green phases at 38,025. Thus scope,
full-weight coordinate equivalence, transition behavior and the three negative
controls actually executed. All applicable independent affine predictions were
within one DN, and full-weight output equaled the uniform CPU gather exactly.

The fixed noise case changed 43,163 of 44,516 transition samples. Its pooled
output/input spatial variance was 0.8412271081947803, within the fixed sanity
bound. This is generated noise with known flat radiance, not a temporal noise
estimate from a photographed region or evidence of recovered detail. The
constant, disabled actual/probe entry, explicit zero, source immutability,
two-green equality, invalid support/nonfinite data and stack identity refusal
assertions all passed.

The bounded child tree exited zero with no cleanup errors and no active
processes. Wall time was 0.344 seconds and aggregate child CPU 0.296875 seconds;
these are one test run's accounting, not a performance comparison.

**Additional choice challenge, now discharged:** affine radiance cannot distinguish
two interpolation kernels that both preserve affine functions. The full-weight
equality assertion was therefore added to the already fixed noise fixture.
Supplemental patch text remains in `pending-noisy-core-control.txt`; it was
applied only after root released the completed chip pair's source freeze. This
is an additional discriminating input, not a changed tolerance.

## Strengthened result and relation to the photographed build

MEASURED by root and VERIFIED against the complete `controls-3/process.log`
and process receipt. The command was:

```powershell
experiments/full-context-placement/build-3/cli-tests.exe local_placement::independent_controls:: --nocapture --test-threads=1
```

All five strengthened tests passed. Every one of 107,584 full-weight noisy
samples equals the existing uniform shifted gather bit-for-bit, while 107,173
disagree with the unchanged gather. This supplies the previously missing
textured input and proves it exercises the treatment. All earlier affine,
scope, taper, negative-control and flat-noise counts and values reproduce.
The controls exit zero with no cleanup errors or active child processes;
bounded wall time is 0.359 seconds and aggregate child CPU 0.28125 seconds.
These remain operational accounting, not a speed comparison.

The strengthened test executable is SHA256
`46f784ec34b2c021857685eb0af374f1100be8605f3a08204b2966d73d5893b0`.
Comparing the recorded `build-2/sources.json` and `build-3/sources.json`, only
`independent-controls.rs` changed; the other nine listed inputs, including the
placement implementation, direct gather, merge consumer and demosaic sources,
have identical hashes. This establishes unchanged **recorded production
source inputs**, not an exhaustive snapshot of every dependency.

The production executables are **not byte-identical**. Build2, used for the
chip photograph pair, is SHA256
`ba7230b21c377dab74ec23cae29aee9f258003503d51784243522113900b52d7`;
build3 is SHA256
`4c620fd02854900175f63c73352a61d8602abea5f1810c7c2517190737eb46e1`.
Both receipts report 17,859,072 bytes. No binary-section investigation was
performed, so the executable hash difference is recorded without attributing
its cause. No production source edits were made for the strengthened test.

The generated controls now establish the fixed affine/noisy fixture's scope,
coordinate direction, phase, rounding, full-weight patch reconstruction
equivalence, transition sanity and source immutability. They still do not
establish alignment truth, photographic superiority, transfer to another
subject, or SOTA performance. Those require the separately reviewed image pairs.

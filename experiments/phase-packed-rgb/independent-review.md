# Independent review before the first generated screen

VERIFIED by source inspection and root's subsequently completed generated
screen. No photographic gain has been established. Root owns building/running
the independent controls.
The reviewed implementation is SHA256
`5c36cda805aab30347b23a657b57797273a714775964d8e535ba74545f6bfc9c`.
The fixed controls are SHA256
`f07dab1637bf4ac8381fc12f67a72fe216ff426fceb24ee30b934df5ca4c0b44`.
The root-approved acceptance choices and pre-run amplitude amendment are in
`independent-plan.md`.

## Distinction from prior closed experiments

This candidate keeps the existing single-frame MHC and Catmull arithmetic.
It preserves their missing-colour estimates through the actual focus merge,
then avoids remosaicing followed by another MHC. This is a different consumer
from September14's demosaic substitutions and joint RAW inverse. It is not a
novel demosaic or a super-resolution result. BUILD-DEMOSAIC's earlier one-pass
reference makes the idea plausible but already demonstrates mixed neutral,
true-colour and noise effects; its comparison against an oracle is not the
candidate's expected gain. V-GATHER does not support scoring this by chroma
high-pass magnitude, and M95's binned co-siting fix does not justify collapsing
the four native phases.

## Source choices checked

The first four plane slots retain R@00, G@10, G@01, B@11. The independent
literal channel/site lookup is `[[0,4,5],[6,1,7],[8,2,9],[10,11,3]]`.
Each missing colour uses its own colour's CA pull at the destination site's
native offset. Source interpolation stays in the original active-area gauge;
the even retained-patch origin preserves RGGB despite an odd decoded active
origin. Complete MHC radius-two plus Catmull floor-minus-one through
floor-plus-two support is required. Missing support refuses rather than using
unsupplied source values.

The baseline is the actual `BandWorker`. Each candidate fold borrows that
baseline's exact gathered green guide, injected variance and measured probe
beta, then calls the existing `BandMerge` with twelve planes at the same quad
geometry and configuration. The source checks equality of the known four
planes before folding and after collapse, and equality of admission fractions.
Thus extra RGB values cannot elect themselves into a different focus decision.
The independent controls additionally check the original u16 source hashes and
require actual selected fine-band content on the varying-focus fixture.

The generated comparison is bounded to small source frames and does not read
original RAW files. Its direct RGB normalization uses the existing rounded
sensor-value convention and inverse WB, then reapplies WB/range for output.
A separate actual `write_merged`/`develop_pixel` RGB16 witness is included so
the four-plane reference is not presumed identical merely from copied output
arithmetic. The independent truth scorer includes the actual full native crop
origin, and asserts the reached levels rather than labelling this a seven-band
whole-image test.

## Deliberately limited claims

The first source fixture is flat at each noise level/map combination. Known
truth errors, genuine-colour component recovery and negative metric controls
determine admission. The amplitude guard caps recovered signal at truth so
removing baseline contrast above truth is not called detail loss. Raw in-phase
and quadrature amplitudes remain reported. A passing unit-test process will
not itself admit the candidate: `screen.json` explicitly reports a separate
photographic-replay decision, including failures at either ISO.

The screen does not validate the camera noise constants, full-scene memory or
speed, every clipping/shadow regime, or actual photo quality. It shares an
injected noise model and tests the operator's handling of it. A passing screen
licenses one paired photograph; a failure closes this fixed configuration.
No new interpolation, iteration or threshold sweep is commissioned.

## First generated screen: admits a photographic replay

MEASURED by root; independently read from the complete JSON result and process
log. Command:

```powershell
experiments/phase-packed-rgb/build-1/cli-tests.exe phase_packed_rgb::independent_controls:: --nocapture --test-threads=1
```

The build records `Compiling strehl-cli`; the test executable is SHA256
`f2cd40535fa0ea1b4b82d4a361c44ceedfb5572c33662b7d1e994b28da8bcd49`.
Both tests pass. The CA/phase oracle checks all 217,500 gathered values exactly;
wrong phase disagrees at 18,116 plane positions and wrong colour at 18,125.
All 217,500 RGB16 samples from the baseline helper equal the actual product
writer. Known-site planes, source storage and shared-consumer assertions pass.
The small domain reaches four Laplacian bands plus an 8-pixel-high base, with
three finite measured probe gains followed by the existing fallback.

Independent interpretation is stronger than the minimum admission rule: every
fractional-map true-colour case improves **both** RGB and chroma truth error
by more than 5%, at both tested noise levels. This includes spatially varying
focus, where finest-band averaging fraction is zero and guides vary across
frames, so the test does exercise selection. The candidate/baseline RGB RMSE
ratios for low-frequency colour, mid-frequency colour and varying focus are:

| ISO | Low colour | Mid colour | Varying focus |
| --- | ---: | ---: | ---: |
| 100 | 0.642685 | 0.805379 | 0.844805 |
| 400 | 0.666162 | 0.807084 | 0.847397 |

The fractional colour components gain in-phase amplitude; the truth cap is
not rescuing a hidden colour-component loss. Even the uncapped guard passes
all colour cases. Coincident-map textured cases are nearly unchanged, not a
second independent instance of the fractional gain: their largest RGB error
ratio is 1.001844 and largest chroma ratio 1.002944. Neutral fractional cases
also lower truth error, while some in-phase amplitudes fall toward truth from
baseline excess contrast. Metric commissioning rejects grey/half-amplitude
destroyers and correctly admits removing a known 1.4-times contrast excess.

There is a noise tradeoff. Worst flat RGB error ratio is 1.004643 and worst
flat chroma ratio 1.078951, both in the ISO100 fractional case. All four flat
cases stay inside the fixed 1.25 guard. These are errors against a known flat
generated scene, not spatial SD mistaken for temporal camera noise. There is
one fixed pseudorandom realization at each noise level; no statistical
confidence or broad noise-distribution robustness is established.

The tree exits zero with no cleanup errors or active processes. Bounded wall
time is 2.765 seconds and aggregate child CPU is 3.40625 seconds. Those costs
describe the small generated experiment, not full-stack speed.

**Decision:** the fixed candidate earns its photographic replay. This is not
a photographic or SOTA claim. The whole-image adapter remains to be verified:
all twelve colour/site pulls need valid support or the explicitly existing
full-source edge behavior; the old four-site coverage is insufficient evidence
for eight additional sites. Baseline/candidate must share the same actual crop,
full pyramid context, tone, WB, original map and canonical frame reduction
groups. Tiling a source gather must not reset the output pyramid at tile edges.
The 1M-pixel saved-patch cap cannot simply stand in for that full-source check.

## Whole-image adapter audit and pending controls

**REVIEWED, not yet execution evidence:** the frozen full-source adapter is
`full-stack.rs` SHA256
`a5f9f7d63d5337751b9e531badbbf4ed65a4c130b7ff17a343b0da5e68d6ff2c`;
its include is in `implementation.rs` SHA256
`ebef117ce5837140647b2d828ebfcf80d04912c2b32248faa33f06f84d051e91`.
The full-source extension preserves the existing physical sensor-edge MHC
reflection and the existing checked Catmull sampler. It never applies saved
patch edge extension to an incomplete retained source. It checks all twelve
colour/site pulls at all four destination corners before gathering, then also
refuses any nonfinite or unsupported consumed sample. Similarity plus colour
CA remains affine, so the corner support bound covers the rectangle.

The active buffer origin is correctly separate from the CFA phase: source
addressing uses `active_row`, while CFA colour uses the local active x/y. This
matches the existing CPU consumer even with an odd decoded active origin. The
new generated test deliberately retains active origin (7,11), unequal row
stride and asymmetric extents. Its near-edge fractional/nonzero-CA crop is
compared against the existing full-source oracle at all twelve phases; the
strict saved-patch route is required to refuse that crop. Another fixed crop
has all four known CFA sites supported but an uncovered missing blue phase,
so the twelve-pull support requirement is live, not an assertion about an
always-interior fixture. The sampler's inclusive 1.5-pixel boundary and just
outside it are checked separately.

The actual photographic fold borrows the existing four planes, guide,
variance and measured beta from `BandWorker`, gathers only the missing eight
planes from the current unaligned original frame, and uses the same full
output pyramid in both arms. It checks known-four equality and admission
equality after collapse. Four-plane planning, rather than candidate memory
size, chooses both arms' canonical frame chunks. The first accumulator moves
into the retained slot; each subsequent chunk is absorbed on the right, with
scratch reset only between chunks. This matches the current production
reduction order. The new generated control uses three unequal chunks (2,2,1),
compares the helper with direct public-API absorption, and requires real
selection and unchanged original CFA. Its separate full-dimension planning
assertion is an arithmetic contract witness, not image-quality evidence.

Both photographic writers receive one common crop, WB, level range and
preselected tone/matrix; neither re-estimates tone from its own result.
`CoverMode::Crop` returns the original map placements unchanged, and the
adapter binds the supplied map by hash and stack identity. Four-plane output
uses the actual product demosaic writer, while twelve-plane output passes
interleaved camera RGB through the actual pixel developer and RGB16 writer.
The new small writer witness compares every emitted sample of both arms with
held development and requires that the tone setting actually change samples.

Controls were frozen before root's next build:
`independent-controls.rs` SHA256
`53af36a3ea12cbedf9375c162f11fce4eec34a410a05467dd2c229bdac5dd915`;
`independent-plan.md` SHA256
`6b3b593e8f0fb6512db44a18f209c2926ce410611d68d7d2224f95d8c069546c`.
The filter is `merge_cmd::phase_packed_rgb::independent_controls::` and now
contains four tests. **Execution pending:** the source review finds no
structural blocker, but does not claim these additions pass. The generated
screen's quality admission remains unchanged. A complete photographic pair
must stay within root's explicit memory/time bounds; this CPU adapter does
not establish SOTA speed or justify promotion before visual review.

## Executed full-source extension: screen-2

**VERIFIED:** `build-3/process.log` records a fresh `Compiling strehl-cli` and
successful release completion. The test executable is SHA256
`1db9da901994a1d6318c5e1b2e71c47d147831e26f4b3ecd1822878c367f90c8`.
The previous `build-2` failed before execution on missing type inference for
the independent planning closure. Root's sole control change was `|n|` to
`|n:usize|`, yielding control SHA256
`572d028a0d83214f9df8ac47634f04e703c855a93d96439a9c8534a5f0b240f9`.
No fixture, threshold or assertion changed. The frozen full-source and
implementation hashes above match `screen-2/invocation.json`.

Executed command, with the environment recorded in that invocation:

```powershell
experiments/phase-packed-rgb/build-3/cli-tests.exe phase_packed_rgb::independent_controls:: --nocapture --test-threads=1
```

All four tests pass. Full-source gathering equals the retained-patch route
at all 217,500 interior values. At the distinct sensor-edge crop, all 269,232
values equal the existing twelve-phase CA oracle. The support negative
control actually reaches nine uncovered missing-blue sites while all four
known CFA sites remain supported; the new adapter refuses it. Inclusive
sampler-boundary, just-outside and nonfinite cases pass, and original CFA
hashes remain unchanged. This supports the all-channel support choice; an
interior-only equality test would have missed its failure mode.

The three unequal chunks (2,2,1) preserve all 72,500 collapsed known-site
values exactly and agree with the independently written direct absorption
sequence. The full-dimension arithmetic plan uses 1,392,085,228 planning bytes,
four canonical chunks and 18 frames per chunk for the seventy-frame replay.
The deliberately wrong twelve-plane planner produces one chunk, so the
planning assertion distinguishes the grouping error it is intended to catch.
This arithmetic witness is not an additional image-quality result. Actual
selection occurs in the small varying-focus fixture. Both full-adapter
writers match held development at all 435,000 combined RGB16 samples, and
the tone setting is exercised rather than numerically inert.

The original 28 generated case records are exactly equal between screen-1
and screen-2 after parsing their JSON, including guides, source hashes,
variance hashes, beta and quality scores. The same fixed photographic gate
therefore remains admitted; the full-source additions have not changed its
stimuli or numerical result. The new evidence is structural coverage of the
whole-image adapter. The small writer witness uses camera-linear transfer
with held tone; the shared photographic sRGB matrix and transfer are verified
by source inspection, not claimed as an independently executed colour
calibration control.

`screen-2/process.json` records exit zero, clean cleanup, no remaining child
processes, 2.954 seconds bounded wall time, 3.625 seconds aggregate child CPU,
and 27,914,240 bytes peak job commit. These are small-control costs, not a
photographic performance claim. **Decision:** no structural blocker remains
for the authorized complete photographic pair. The generated domain still
has four Laplacian bands; full seven-band photographic quality, genuine
colour preservation and resource use remain to be judged from that pair.

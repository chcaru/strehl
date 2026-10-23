# Adaptive V4: larger corpus and native execution

2026-10-22. **Development candidate, not production approved.** A larger original
model now predicts image-specific fields substantially better than a constant
profile. That does not make the resulting treatment good: the first independent
blind review preferred unchanged insect and mineral photographs over the current
experimental rendering. No learned profile is enabled in the editor.

This follows the [earlier prototype](adaptive-distillation.md). The original
[V4 tools](../../experiments/adaptive-distillation/README.md) accept an external
cache and contain no teacher, private images, recovered code or learned weights.
The [native runtime](learned-profile-runtime.md) is separate from both inference
and photographic policy.

## Data and color contract

**VERIFIED locally:** 4,105 candidate sources were audited read-only; 4,104 decoded.
Exact source/decoded identities and perceptual similarities were joined with
capture-group metadata. The refined allocation contains 3,504 training entries,
501 validation entries and 99 reserved entries, across 54 connected groups.
Those contain 3,498, 499 and 92 distinct source-file hashes respectively.
Absence of a perceptual-hash match does not prove scene independence. All earlier
prototype test subjects are now development data, not fresh acceptance evidence.

Only training/validation inputs received new teacher labels: 4,822 training and
692 validation examples after controlled variants. Repeated views, stack frames
and augmentations are not extra independent scenes. Reserved sources were used
for identity auditing, not model selection or teacher-output evaluation.

The predictor input is explicit: encoded sRGB storage, FP32 inverse transfer,
Bradford BT.709/D65 to linear ProPhoto/D50, and two unchanged scalar mask channels.
The contract digest is
`63a26739adaa9ecf8be76c7ea91a1f85eeb97f75619c4ae0279060c7c666287a`.
This corrects the previous prototype's declared display-RGB research domain.
It does **not** turn camera JPEGs or developed TIFFs back into a RAW pipeline.
Most source images are embedded camera previews; masks are controlled geometric
variants, not production semantic segmentation. Encoded-first resizing differs
from resizing a linear RAW tapout. Native HDR input behavior is not established.
All five validation groups contain embedded previews, with no complete stack
renders or verified scene-linear masters. An inventory label containing `master`
does not establish a linear color domain: the existing cache processes those
training files through the same RGB8/sRGB path. The validation table therefore
does not establish fidelity on the editor's actual scene-linear source.

## Model and executed run

The student uses a depthwise image encoder, spatial context, global image
statistics, FP32 gain fields, training-only mean/PCA color tables and a learned
coarse residual. A bounded memory-mapped loader streams batches rather than
putting the entire cache on the GPU. Training/PCA identities and content hashes
bind fitted statistics to the data; checkpoints use restricted weights-only
loading.

**MEASURED:** 339,682 parameters and 1,400,932 buffer elements occupy 6,962,456
FP32 bytes. The ONNX model is 7,072,834 bytes. This candidate is larger than the
5,895,891-byte local teacher; quality was prioritized over the earlier compression
target. No claim calls V4 the smaller model.

The run completed 6,000 steps, batch 12, on an RTX 5090; validation selected the
last checkpoint. The private research trainer and packaged public trainer have
identical numerical code. Both exporters produced the same trained model bytes:
`7f92ef40abb45341b067a8a8b7c03e5c9a2da9138f8a1734d4c73e8afd4fa3c1`.

An independent curve audit found that the exposure-family validation ratio was
best at step 3,000 and was 1.87% worse at step 6,000. The joint score improved
only 0.093% from step 4,500 to 6,000. These development observations do not support
extending the run merely because the joint best checkpoint was the last one.

## Validation fidelity, not photographic quality

**MEASURED by the packaged evaluator:** 692 validation rows, five validation groups.
Error is averaged within sources, then groups equally. The constant comparator
is fitted from training outputs only. Gains are log2-ratio error; color is raw
table-value error. Exposure is in the model's EV-like output units; a scalar
prediction error is not a measured final-image brightness error.

| Output | Student RMSE | Training-mean RMSE |
| --- | ---: | ---: |
| SDR gain | 0.08483 | 0.25135 |
| SDR background color | 0.02590 | 0.04017 |
| SDR subject color | 0.02597 | 0.04017 |
| SDR sky color | 0.02706 | 0.04389 |
| SDR exposure | 0.40739 | 1.03845 |
| HDR gain | 0.05051 | 0.18784 |
| HDR background color | 0.01487 | 0.02164 |
| HDR subject color | 0.01459 | 0.02130 |
| HDR sky color | 0.01538 | 0.02177 |
| HDR exposure | 0.47851 | 1.06607 |

All ten aggregate comparisons also beat wrong-image assignments. Mean error can
hide a conspicuous local failure or little image-specific variation. The largest
SDR gain-table error is still 15.81 stops, and the largest exposure errors are
1.68 SDR and 1.53 HDR units. These tails are retained, not excused by the mean.

A separate occupied-coordinate probe used 501 unperturbed validation images and
an explicit simplified exposure policy. SDR gain-only RMSE was 0.04964 stops,
versus 0.31415 with another image's map. Including each model's own exposure
raised total-correction RMSE to 0.36038; HDR was 0.56149. These measurements omit
color tables and use cached resolution. They cannot prove full-resolution
photographic fidelity or safety at coordinates reached by later edits.

## Native operation and packaging checks

**VERIFIED:** public PyTorch-to-ONNX comparisons passed all ten outputs. A separate
Rust/Tract 0.23.9 [native probe](../../experiments/adaptive-distillation/native-probe/README.md)
executed the trained model on a complete-photo predictor
input and agreed with ONNX Runtime within `rtol=2e-4, atol=2e-5`; maximum gain
difference was 7.28e-6. Its translated NNEF version produced identical output
bytes without compiling the ONNX file parser.

**MEASURED, isolated development process:** 24 warm NNEF calls had median
59.07 ms on the local CPU. This is not an app-latency or universal performance
claim. It excludes decoding, input preparation, full-image composition and
display. The native compositor's separate full-photo checks are documented in
the runtime report. No comparison of differently threaded runtimes is presented
as a speedup.

The public runner completed a synthetic ten-step train/export/evaluate sequence
with deliberately nonfinite test labels left unread. Independent controls reject
cross-split aliases, wrong color domains, invalid fields and changed cache files.
The public trained export's hash matches the research export, and the packaged
validation evaluator reproduces the table above. No reserved V4 test rows were evaluated.

```text
python experiments/adaptive-distillation/input-contract.py
python experiments/adaptive-distillation/runner-guard-smoke.py
python experiments/adaptive-distillation/student-v4.py
python outputs/ai-adaptive-production/smoke-v4-public.py
python experiments/adaptive-distillation/export-v4.py --cache outputs/ai-adaptive-production/cache-v4-linear --checkpoint outputs/ai-adaptive-production/v4-linear-development/best.pt --output outputs/ai-adaptive-production/public-v4-linear-export
python experiments/adaptive-distillation/evaluate-v4.py --cache outputs/ai-adaptive-production/cache-v4-linear --checkpoint outputs/ai-adaptive-production/v4-linear-development/best.pt --training-means outputs/ai-adaptive-production/v4-linear-development/training-means.pt --output outputs/ai-adaptive-production/public-v4-linear-evaluation.json --device cuda
```

The `outputs` paths are ignored local receipts, not downloadable fixtures.

## Open production boundary

The current simplified renderer applies exposure, gain, identity tone and color
tables. Static investigation established that the native reference pipeline also
has camera-dependent exposure compensation and nonlinear highlight handling
before color tables. A model-output match through the simplified renderer cannot
establish equivalence to the complete reference pipeline.

### Independent photographic decisions

**VERIFIED by independent visual review:** three development panels used whole
photographs followed by fixed native regions, anonymous candidates and duplicate
baselines. These are subjective photographic judgments, not universal quality
measurements. The reviewer recorded observations before receiving the identities.

- The first panel covered six photographs. Unchanged versions were preferred on
  all four developed macro subjects. Lifting the two dark interiors was useful,
  but a bright sign lost separation between its white arrow and cyan background.
- Fixed clamp and highlight-shoulder alternatives did not visibly repair those
  failures. No threshold was selected from this result.
- A gain-only treatment subtracting median log gain within a preregistered
  luminance region was more restrained, but
  did not establish useful spatial adaptation beyond simpler controls. The
  unchanged opal and neutral slide remained preferred. Several deliberately
  shifted fields introduced their own discontinuities; beating those damaged
  controls cannot establish meaningful scene correspondence.

One fine teacher/student preference reversed between panels even though all 36
corresponding whole/crop RGB arrays were byte-identical. That ranking was
withdrawn as reviewer uncertainty. A suspected new mark on the slide was also
withdrawn after native-resolution inspection found the mark in the baseline.
The robust macro rejection remains; neither correction is hidden to strengthen it.

A fourth, separately frozen panel used the actual 7032 by 4688 scene-linear insect
master. Eight arms included the saved current result and duplicate, direct-linear
display, both predictors at two fixed exposure-allocation endpoints, and a
scalar-only tone control. All eight whole photographs and 48 fixed native crops
were reviewed before identities were revealed. The current result and duplicate
were preferred. The teacher versions remained too bright/vivid; the student
versions were too subdued. Neither pair had a dependable improvement from
moving positive exposure into the nonlinear stage. The scalar-only control was a
viable flatter alternative, but did not beat the preferred current photograph.

This last experiment preserved the gain-query brightness scale while changing
only the declared linear/nonlinear exposure split. Both endpoints used the same
extrema cap, negative-input policy and color tables. Independent synthetic review
caught and fixed a near-black extrema error before rendering. The final synthetic
checks covered 210 channel-permuted cases; original source and frozen fields were
unchanged after complete-photo rendering. The experiment establishes sensitivity
under its explicit policy, not the unknown native exposure allocation or a
general quality result. The independent photographic review found no rescue on
this development image, so it does not justify enabling an AI profile.

### Paired input-domain check

**MEASURED:** a fixed selection of three distinct RAW source hashes from each of
the five existing validation groups compared the exact cached preview, the same
preview decoded before linear resampling, and a neutral clipped LibRaw RGB16
proxy. All 15 source hashes were unchanged. The proxy changes color, tone, WB,
scaling, decoder and possibly crop as well as transfer behavior; it is neither
an Adobe input nor the application's unclipped master.

The broad prediction that linear RAW inputs would make every head worse was
not supported. Relative to the linearly resampled preview, median per-source
error improved for both gain heads and all six color heads. Exposure errors
worsened on 9 of 15 SDR and 10 of 15 HDR sources, with three groups worse and
two better in each branch. A separate actual scene-master insect retained a
1.49416 SDR and 1.08991 HDR scalar discrepancy. It was not pooled into the RAW
pairs. These are predictor-output units, not measured final-image EV errors.

An independent review used per-source medians, group signs and absolute errors
against fixed means and same-group donors. It also checked RMSE where one-sided
residuals made a cyclic permutation's MAE equal by arithmetic. Some mean and donor
comparisons still fail. These results support neither a uniform domain-failure
explanation nor a claim that additional training will fix the photograph.

The commissioning controls passed; swapping red/blue and decoding after resize
both failed as intended. A nonconstant black/white fixture distinguishes the
correct linear result 0.5 from the incorrectly ordered result about 0.214.

Executed local investigations (private images and model remain ignored):

```text
python outputs/ai-adaptive-production/render-six-photo-native.py
python outputs/ai-adaptive-production/probe-shoulder.py
python outputs/ai-adaptive-production/anchored-gain-probe.py --commission
python outputs/ai-adaptive-production/anchored-gain-probe.py
python outputs/ai-adaptive-production/paired-domain-probe.py --commission
python outputs/ai-adaptive-production/paired-domain-probe.py --commission --sabotage-channel-swap
python outputs/ai-adaptive-production/paired-domain-probe.py --commission --sabotage-decode-after-resize
python outputs/ai-adaptive-production/audit-paired-domain.py
python outputs/ai-adaptive-production/scene-rolloff-probe.py --commission
python outputs/ai-adaptive-production/scene-rolloff-probe.py --commission --sabotage-identity
python outputs/ai-adaptive-production/scene-rolloff-probe.py --rois outputs/ai-adaptive-production/scene-rolloff-rois.json --output outputs/ai-adaptive-production/photographic-probes/scene-rolloff-v1
```

The paired probe's frozen plan and results are retained with its local receipt.
The three sabotage commands intentionally return failure.

### Native application reference

**VERIFIED:** a copied camera RAW now has three actual Lightroom Local exports:
Adobe Color, Adaptive Color Amount 100, and Adaptive Color Amount 0. All are
7008 by 4672 uint16 ProPhoto RGB TIFFs with matching geometry, ICC and represented
non-profile settings. The original and copied RAW still match the prior SHA256.
The synthetic scene-linear DNG was not eligible for Adaptive on this installation;
changing its filename or tags would not establish equivalence to a camera RAW.

The optional zero arm matters: Adobe Color and zero-strength Adaptive are distinct
renderings. Default RAW sharpening and color noise reduction remain in all three
arms. These exports are rendered SDR references, not scene-linear input tensors.
They also differ in geometry from the stack master and another decoder's output.

**MEASURED / independent photographic review:** on this one RAW, the neutral
RAW-derived teacher input is substantially closer to the native saved gain/color
fields than the developed-TIFF input. Whole-photo renders using the RAW proxy
and either predicted or native saved fields form a plausible approximation group,
but none reproduces the reference's color, transitions and texture in the inspected
native-scale regions. The
current student remains too dark. This narrows the input/rendering investigation;
it does not establish exact native input recovery, a winning exposure policy,
generalization, or production quality. The earlier rejection on already-developed
stack inputs remains valid for that different processing path.

The public read-only reference validator and its 20 synthetic adversarial tests
are in `experiments/adaptive-distillation/validate-native-reference.py` and
`test-native-reference.py`. The tests and the actual three-arm validation were
run by both the author and an independent reviewer. Metadata checks establish a
declared export contract, not authenticated provenance or photographic quality.
Private photographs, model assets and per-image native payloads remain ignored.

Scene-linear and already-developed inputs require separate acceptance. Remaining
work includes an accepted photographic policy and reference rendering contract,
real semantic masks, fresh-scene review, UI/recipe integration, and end-to-end
interaction tests. More training photos alone do not close those gaps. No learned
profile is promoted, no release is created, and the reserved final test remains
unevaluated.

### Complete-stack references and the next photographic gate

**VERIFIED locally:** the earlier ineligible RGB DNG is no longer the only
reference route. A private experiment preserves the actual merged floating-point
CFA samples in DNG, with camera calibration from a matching native RAW donor.
Lightroom Local offered Adaptive Color for these complete-stack inputs. This is
not relabeling developed RGB as camera RAW. Independent checks compare every
sample and all four CFA phases with the stored merge output, including fractional
values and values above the nominal sensor white. Above-white merge values are
not, by themselves, evidence of recovered highlight information.

A bounded development pilot now has three complete stacks and six matched native
exports: Adaptive Amount 0 and 100 for each stack. The exports are full-resolution
7032 by 4688 RGB16 ProPhoto TIFFs. Each pair holds the represented development and
export settings fixed except Amount. Default RAW sharpening and color noise
reduction remain present in both arms. The input files are disposable copies;
source RAW hashes and hidden-inclusive folder inventories were rechecked after
each wrapper build. Native Local opened only disposable merged copies. These
private exports and camera-specific metadata are not shipped with Strehl.

The frozen five-arm comparison contains the default Strehl photograph, its exact
duplicate, both native exports, and the unchanged rank-eight student. Four native
400-pixel regions per photograph were selected from the default result before
candidate inspection. The independent reviewer freezes whole-photo observations
before inspecting these regions, and freezes the final judgment before seeing
the identities. Native and baseline RGB16 data are transformed through their ICC
profiles before quantizing the review images; an independent adversarial control
uses a synthetic color fixture to expose precision lost by the earlier
quantize-before-transform presentation path. It does not quantify that loss in
the earlier photographs or invalidate their qualitative rankings.

This gate asks whether the proposed targets are worth learning. A brighter or
more saturated photograph does not establish improved detail, denoising, or
useful spatial adaptation. The complete pipelines also differ in camera color
and tone processing, so preference alone cannot identify which operation helped.
All three subjects already belong to development/training groups; the reserved
final test remains unevaluated. If useful local treatment is not repeatable, native
Amount 100 must not become a compulsory training target. Unchanged is a valid
outcome. Proceeding requires useful local value on at least two subjects without
consequential new damage on the third. Duplicate inconsistency or disagreement
makes the pilot inconclusive. Passing this bar leads to an independently checked
representation capacity experiment against a matched global control, before
further training.

Executed private tools and receipts are under
`outputs/ai-adaptive-production/stack-target-utility-v1/`: `pilot-plan.json`,
`build-merged-dng.py`, `independent-merged-audit.py`,
`independent-native-pair-audit.py`, `render-frozen-rank8.py`,
`build-blind-panel.py`, and the per-scene frozen reviews. Completed integrity and
presentation evidence is in `independent-native-final-audit.json` and
`independent-panel-audit-v2/receipt.json`. These are local evidence paths, not
downloadable fixtures or a production feature. No new training was performed
during this pilot, and no learned editor profile is enabled by it.

**Independent photographic result: the frozen utility gate failed.** All fifteen
whole photographs and sixty fixed native crops were reviewed before unblinding;
the duplicate baseline was tied correctly on all three subjects. Adaptive 100
was preferred on the seed stack. Adaptive 0 was preferred on the garnet, with a
reservation about conspicuous shared fine rim texture. The unchanged Strehl
photograph was preferred overall on the opal; Adaptive 0 gave more readable
reflection gradation but a darker, less luminous whole image. Adaptive 100 made
the opal's support distracting and its body milky. The student was also too pale
and exposed objectionable background texture there.

The independent decision receipt is `independent-pilot-decision.json`. Even
granting the seed result the most favorable interpretation, it supplies only one
supporting subject. This is a completed negative gate, not duplicate inconsistency
or an inconclusive run. There is no progression to the conditional capacity fit
or new training on these targets. Amount 0's useful observations do not license
silently substituting a mixture of per-scene winning targets. None of these SDR
preferences establishes native HDR display quality or evaluates a separate HDR
preset with additional contrast and color adjustments.

### The user's HDR preset is a separate reference question

The supplied favorite preset uses HDR, Adaptive Amount 125, and additional
contrast, vibrance and saturation. It was not the neutral SDR recipe above.
A separate private experiment applies that complete preset to disposable merged
CFA copies, with a matched Amount 0 arm. Its scope is reference acquisition and
encoding validation; it does not change the failed SDR decision or authorize
training against a mixture of whichever targets happened to win.

**VERIFIED for the checked native export:** full-resolution floating-point TIFF
uses linear Rec.2020 with 1.0 corresponding to 203 nits. The encoding conclusion
combines the actual ICC, an explicit native PQ companion, the published Adobe
reference-white contract, and a fixed-scale prediction. The stricter preregistered
requirement that every component agree within two 16-bit PQ codes **failed**:
three of 98,898,048 components exceeded that tolerance. Independent localization
found tiny blue values, with a maximum localized absolute discrepancy below
0.000017 nits. The failure remains recorded; no correction was fitted and no
tolerance was relaxed. It does not establish bit-identical cross-format rendering.
The PQ companion's legacy ICC curves must not be mistaken for its CICP-declared
HDR encoding or used as an SDR conversion for this comparison.

**Independently verified:** default Strehl HDR references for the same three
complete stacks apply each master and its stored display placement exactly once. All
296,694,144 developed float samples were checked against an independently
implemented calculation, including negative and above-white values. The separate
lossy AVIF companions retain their original transport-test results: two failed
the maximum-error bar and one passed. The comparison consumes the verified float
images, not those compressed companions. The native favorite's global contrast
and color controls differ from Strehl's defaults: this compares complete
pipelines, not an isolated Adaptive effect.

A private comparison viewer uses the existing native HDR presenter, common
203-nit white and a common display-peak policy, with synchronized zoom and pan.
It refuses an inactive HDR display rather than silently substituting SDR. Its
color conversion, signed-float resizing, input rejection, and GPU output were
independently commissioned; physical display calibration and photographic
preference are separate questions. The initial generic float-resize path failed
a negative/above-white fixture and was replaced before photographs were shown.
This instrument is not an enabled Adaptive profile or a production quality result.

Private commands, fixed plans, source bindings, failures and independent receipts
are retained under `outputs/ai-adaptive-production/favorite-hdr-reference-v1/`.
The reserved final test remains unevaluated. No new model training or profile
promotion follows from these encoding checks.

### User preference on the HDR references

On October 22, the user reported tentative favorites before the candidate
identities were disclosed: Chia B, Garnet A, and Opal A. The frozen manifest and
key were checked independently; both viewer versions use identical labels.
The native viewer log records HDR active during navigation through all three
subjects. This establishes the reported display state, not physical calibration.

| Subject | Selected treatment |
| --- | --- |
| Chia | Complete favorite HDR preset, Adaptive Amount 125 |
| Garnet | Complete favorite HDR preset, Adaptive Amount 0 |
| Opal | Complete favorite HDR preset, Adaptive Amount 0 |

Amount 0 retains Lightroom's native RAW, profile, white-balance and HDR rendering
and the preset's other contrast and color controls. It is not an unprocessed
baseline. All three selected candidates came from that native pipeline; these
preferences do not isolate which rendering component made the difference.

The next investigation should include a Strehl control for the preset's basic
contrast and color treatment before attributing the native preference to a
learned rendering model; the two applications' slider scales are not presumed
equivalent. Evaluate a consistent HDR base-rendering target separately from
optional Adaptive treatment. The choices do not justify using
Amount 125 universally, silently mixing per-scene winners into training targets,
or fitting a scene selector from three examples. Intermediate amounts and unseen
subjects remain untested. The user supplied favorites rather than a complete
ranking or defect analysis. The earlier SDR rejection and the disabled learned
profile remain unchanged.

The exact statement and decoded choices are preserved privately in
`favorite-hdr-reference-v1/user-hdr-preference-2026-10-22.json`.

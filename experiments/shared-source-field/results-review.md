# Independent result review: fixed shared-source field rejected

2026-09-19. full_context_placement inspected root's frozen receipts/logs only;
no rerun, RAW read, parameter change or candidate photograph. **MEASURED:
`photographic_replay_admitted=false`. Close this exact unary/four-path/fallback/
whole-AC recipe. No complete70-frame run is warranted under its charter.**

Root's fresh build1 succeeded in131.219 seconds. The recorded command was
`build-1/cli-tests.exe merge_cmd::shared_source_field::independent_controls::
--nocapture --test-threads=1`. Both Rust tests completed successfully in1.61
seconds (job wall1.906 seconds); success means controls/screen completed, not
quality admission. The source-binding receipt reports sources unchanged.

| Native truth window | ISO100 candidate/baseline RGB RMSE | ISO400 ratio |
| --- | ---: | ---: |
| False fan | 1.108485 | 1.019284 |
| Compact core | 1.860667 | 1.751951 |
| Glint depth boundary | 0.992826 | 0.994778 |
| Near real texture | 0.998071 | 0.998297 |
| Genuine coloured radial detail | 0.985230 | 0.996728 |
| Thin near line | 1.112555 | 1.066107 |

The fully exercised ISO100 glint is sufficient to reject: the required fan
ratio was<=.95, and the core also fails the<=1.10 nonregression guard. The
ISO100 thin near line independently fails that same guard. The other listed
windows pass their registered bars; no isolated positive window overrides the
joint decision. Off/constant-green fallback and wrong-source destroyer were
actually exercised.

## Re-chosen interpretation and limits

**This is not measured core erasure.** Core template recovery remains roughly
1.03–1.05 in both arms, and the truth-capped amplitude guard passes. Yet RGB
error grows86%/75%, and core chroma error grows47%/38%. Thin-line template
amplitudes also increase rather than collapse. Thus the additional error is
not explained by loss of the measured template amplitude; a claim that the
core was blurred away would overstate the result. This is why amplitude or
sharpness alone could have falsely approved the candidate. The present
receipt does not decompose the added error into bias, shape, noise or seams.

**ISO400 does not provide a second clean fan-specific rejection.** Its baseline
fan RMSE .003400573 and unmerged wrong-late fan RMSE .003701471 are both below
the required2x flat baseline error (.004441566). The fixture therefore records
`fixture_exercised=false`. Preserve its observed ratios without strengthening
the causal claim. ISO100 meets the separation requirement and already fails.

Five-source noisy flats at both ISOs have alpha0 everywhere and exact baseline
output. The70-source ISO100 identity flat passes with RGB ratio1.000002357 and
chroma ratio1.000003590, but35/18125 quads activate weakly; it is practically
unchanged, not bit-identical. This tests the fixed deep-stack null and shows
no material extra error there. It does not prove universal noise safety or
calibration, nor isolate an N effect: the five-source noisy flats used
fractional pulls, whereas this70-source null used identity.

Genuine radial detail improves modestly and passes, with only496/18125 quads
activated at ISO100 and354 at ISO400. The constant-green colour-only placebo
is noiseless identity and deliberately falls back exactly to the baseline.
Those positives establish limited non-destruction/fallback behavior, not
recovery of the weak colour missed by previous methods or reliable ownership
near arbitrary conflicting green structures.

The mechanical records have zero path/membership/replay oracle discrepancy,
.000732422 DN all-ones/shared-base discrepancy, live four positive and four
negative clamp witnesses,14899 changed covered samples and11084 exact-zero
samples. These support correct implementation of the chosen rule. They do
not establish that its green unary identifies the surface responsible for a
late ray. The previously noted bounded-message/unary-gap argument is a
plausible limitation, not an observed attribution of these errors: per-pixel
source costs and reconstruction components were not retained for such a
diagnosis. Do not infer a penalty/threshold adjustment from this failure.

The fixtures are analytic positive blur examples, not a calibrated optical
simulation of this lens, and baseline/candidate share an injected noise model.
The conclusion is narrow but decisive for advancement: this fixed rule fails
its intended truth benefit and causes avoidable truth error in an exercised
scene. It does not close all coherent source selection. Full-scene timing,
memory, photographic quality and SOTA performance remain unmeasured here.

## Bindings

| Receipt | SHA256 |
| --- | --- |
| controls-1/output/screen.json | 460ed3045c650ac1a8bf3a9819ccc8999b2b1a2e9bcee1ad7fd4abb2ea053d0f |
| controls-1/process.json | 2104b437ec0843ff4d292b40218ab5b572e83300dc4ac2b8091406fb41b6a2a2 |
| controls-1/bindings.json | 56aa8a3c11cd1069b1ada7ef3f38e7feb859e18a9e3fdc46377c723f5cc48455 |
| controls-1/process.log | 235575095198c8a71f38d0a1465bb97864f286d5c73cd14942e5ed1d0a7498ba |

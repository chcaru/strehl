# Image-quality work on the September captures

2026-09-14. The priority is actual RAW photographic quality. Further speed-only development is deferred. Original captures are read only; capture metadata, commands, selected source footprints and outputs are retained here.

## Completed intervention

Implemented an explicit `strehl align --peak-refinement quadratic --out <map>` option. The existing NCC routine separately refines x and y; the candidate retains their mixed curvature with a guarded 2x2 solve. It reuses existing scores, with no new image interpolation. Default alignment stays separable; ambiguous, poorly conditioned or unsupported peaks use the original result. Automatic map caching is unchanged.

The fresh core build and existing 33 alignment regression tests pass. Nine independent literal positives, ten refusals and 48 actual NCC cases pass the prospective controls. Same-focus RMS falls from0.021468 to0.006623 and0.025208 to0.005534 reference-plane pixels (plain/warped). Every content group's RMS and maximum improves, including unequal blur, exchanged depth and noise.46 of48 individual errors improve; two mixed-depth cases worsen slightly. Near-flat local timing meets the fixed overhead bound. These are measured synthetic placement results, not a percentage improvement in photographic sharpness. See ../alignment-quadratic-peak/independent-results.md.

## Actual105-RAW photograph

The new 3d-printer-piece-cpl stack is the first current capture consumed in full. Baseline command: `python -I -B experiments/quality-september14/baseline.py`. Candidate command: `python -I -B experiments/quality-september14/candidate.py`. Both use105 originals DSC00001..DSC00105, middle reference52 and a freshly solved map. Both photographs use the identical held renderer and preset, with only the explicit map and output path changed. The candidate map comes from the newly compiled CLI; its parser control also passes.

Both place105/105 and render6840x4560 RGB16 at native origin(96,64). The mapping change has median maximum-corner displacement0.215642 and maximum0.626799 reference52 CFA-plane pixels; this is treatment size, not a truth-referenced placement error. Baseline alignment/render cost21.078/36.172s; candidate21.687/34.438s. These single observations are operational costs, not comparative speed evidence.

Root and an independent viewer inspected five matched native crop pairs: junction, letter edge, fibre, diagonal surface and dark cavity. **No clear visible improvement or regression is established.** Fine-strand paths, separation and edge continuity look unchanged; cyan/magenta bright-point fringes remain. The dark cavity is a visual low-texture control, not a calibrated noise measurement. Tone is image-derived and changes slightly (black0.00856->0.00858, white0.35904->0.35776); brightness/gradient changes therefore cannot establish a detail gain. See photographic-verdict.md and comparison-1/comparison.json for the exact rectangles and display.

Retain the inexpensive refinement as experimental. Do not promote this photograph as a visible quality gain or change the default. No further threshold/field sweep is commissioned for it.

## Source diagnosis and next decision

The first source check used the identity-reference middle original and two independent RAW decoders, which agreed over5,643,456 sensels. The source already contains coloured bright-point structure, and is defocused at several target regions. It cannot establish fusion-only colour creation or best-focus detail loss. See source-review.md. Three additional sparse originals were also defocused at the chosen features. A bounded full-105-frame locator then found focused fibre originals around index 39 and junction originals around index 41. The locator demonstrated first that noise can outrank detail, so its score only chooses originals for visual review. Independent decodes of the selected patches agree. The independent reviewer found no clearly separated or continuous source structure missing from the stack in these two regions; colour around bright points remains a candidate for identical-development comparison. See focused-source-verdict.md.

Five newly added groups were inventoried; only first/middle/last embedded JPEGs were viewed for orientation in each, and three files per group had selected EXIF read. That does not make the remaining RAW data a fully consumed scoring population. Camera metadata in those samples confirms ILCE-7CM2, reported200mm/f5.6, ISO100, manual3000K and stabilizationOff. Full electronic shutter, polarizedKL1500LCD light and capture technique are owner-supplied context; EFCSOff does not independently prove shutter mode.

## Reproduction

Core source/control builds: `python -I -B experiments/alignment-quadratic-peak/build.py`, then `run.py` in the same directory. Full CLI build: `python -I -B experiments/native-pyramid-profile/build.py --gpu-gather --output-dir experiments/alignment-quadratic-peak/build-cli-1`. Both compile logs contain fresh crate compilation. The full application build cost151.328wall/289.4375childCPU seconds; the core build34.969wall/38.203125CPU; generated numerical work6.109summedwall/5.953125CPU. No original RAWs are involved in the generated controls. Source hashes and executable hashes are in the build receipts; baseline/candidate commands and environment are saved beside each output.

## New checker and chip baselines

MEASURED operational runs: `python -I -B experiments/quality-september14/checker-baseline.py` aligned all 150 tiny-checker originals in 32.422 s and rendered in 49.422 s. Output is 7012 x 4672, native crop origin (10,8), reference index 75. `chip-baseline.py` aligned all 299 exposed-chip originals in 74.344 s and rendered in 92.187 s. Output is 6500 x 4332, native origin (266,178), reference index 149. These are single operational observations, not comparative speed claims. Both use their own maps, the same held renderer and the same preset as the printer baseline.

VISUALLY OBSERVED: the checker keeps separate cells and continuous edges. Its reference original already carries cyan/magenta edge fringes, so their existence cannot establish a merge defect. No clearly resolved source edge or separation was found missing in the reviewed regions. The rawpy and rawler patches match exactly; see checker-source-verdict.md. The chip contains substantial genuine colour and fine diagonal patterns, making it a useful colour-preservation control. Its region named dark-flat contains faint lines; the name does not establish a featureless noise target.

The first/middle/last preview inventory is now supplemented by full RAW consumption of printer, tiny checker and chip only. The larger checker and slide2 still have only the recorded preview/metadata use in this work.

## Next stage-local comparison

An actual-consumer, test-only observer will compare nominated focused-source CFA patches, the gathered patches and the collapsed merge with identical white balance, chromatic correction and fixed rendering tone. This removes the different-developer confound. It retains small patches and uses the existing writer; it does not change the default product algorithm.

The candidate of colour-difference interpolation around unchanged Malvar green is **prior work**, not a new algorithm: docs/research/M95-cdiff.md already measured it. It improved chromatic numbers slightly but missed the registered luminance bar and was visually indistinguishable. Its implementation is a cheap control only; it is not justification for another open-ended demosaic campaign.

## Matched source and reconstruction results

VERIFIED: the new test-only source observer preserves complete printer TIFF bytes when enabled, disabled and given a different placebo region (common SHA256 29c2028c25bcafb25d4f1c3105de7b1f91abfdae1035cec154bd0c01242a08a6). The independent verifier also checked every merged patch against the full replay, re-chose asymmetric subregions, rejected a wrong-origin control, and independently reproduced 150,544 normalized chip CFA samples from the retained second decoder. `matched-source-verify.py` and matched-source-verification.json carry the commands and checks. Actual source, gathered and merged stages share fixed tone, first-frame WB and the product colour matrix.

VISUALLY OBSERVED: the chip's focused pale-circuit source already develops dotted rail edges through MHC; the merge changes them further. Source and gathered/merged images differ in CA correction, and source-to-merge differences are not ground truth. The exact saved-patch developer now reproduces all captured MHC TIFF samples before it writes an alternative. This lets subsequent local reconstructions be compared without another RAW decode or full merge. The example-only build completed in 8.062 s; the earlier compile-only helper refused cargo build before launching any child, and that refusal is retained.

Three small reconstruction experiments remain diagnostic only. Q uses fixed green-only quincunx interpolation and colour differences: it visibly reduces some rail zipper patterns but loses neutral diagonal detail and worsens flat chroma truth error. C averages directional costs spatially and blends green directions continuously before the same colour-difference interpolation: it restores Q's lost diagonal detail and avoids the old hard-selector noise increase, but still loses genuine coloured detail. D keeps MHC red/blue and changes only green: it has no RGB-RMSE regressions against shipped MHC in the fixed test set, yet worsens chroma truth error in some coloured cases. None is promoted.

These distinctions matter: the fixed numerical table compares both shipped MHC and the unshipped MHC-CDIFF arm. A failure against the better comparator per case is not necessarily a regression against shipping MHC. D's 16 failures are all against MHC-CDIFF; its increased chroma error is a separate reason for caution. Conversely, better total RGB error does not prove better colour. The independent scripts retain the flat tests, genuine-colour and phase destroyers, alias counterexample and prior results. Their runtimes were approximately one CPU second per additional arm; no further RAWs were decoded.

The next comparison used a fixed published residual-interpolation implementation rather than further variants in this family. Source licence and units were checked before execution. Its reference clips to 8-bit range, which is inappropriate for these WB-applied RAW values: the retained chip patches exceed 2.7 in a nominal white-normalized channel. The explicit f32 adaptation preserves that headroom and leaves clipping to the unchanged product developer.

## Published RI: local appearance gain, serious truth losses

MEASURED: `ri-screen.py` produced three chip stage comparisons in ri-comparison-2 and six printer comparisons in ri-comparison-3, each after exact baseline product-pixel equality. Root and independent reviewer see more continuous long chip rails and less dotted colour breakup. Printer fibres and the junction show no obvious continuity or separation gain/loss. That local appearance benefit does not establish general detail preservation.

The independent continuous-scene controls reject this RI configuration: twelve eligible cases regress against shipping MHC at both trim12 and trim32, including genuine-colour content. At trim32, an independent-colour diagonal case has RGB RMSE0.04827 versus MHC0.00904. Flat noise improves, but does not offset the colour failures. `ri-upstream-two-cases.py` re-ran two failures using untouched upstream float64 code in a separate process: both persist. The independent-colour loss is0.04827051 versus0.00904464; a neutral diagonal loss is0.05190637 versus0.01780456. The f32/unclipped adaptation changes the latter's magnitude, not the underlying regression. No Rust port or default promotion is made.

The initial actual-patch attempt refused a known-sample error at the reference algorithm's outermost border. Replicated residual borders duplicate known R/B contributions there. Explicit CFA-parity-preserving reflect padding32/cropping32 corrects that boundary handling without relaxing the roundoff guard. Independent controls verify every returned measured sample and show central padded/unpadded agreement within2.98e-8. Failed first runs remain recorded; boundary correction does not repair the independent truth failures.

## Captured saturation and the next RAW-native route

MEASURED: `chip-clip-census.py` counts465 exact16383 samples in the fixed384x384 pale-circuit source ROI, all green (228G1,237G2). They coincide with bright rails/crossings. Blue's value above2.7 after WB is headroom, not a count of clipped blue sensels. Captured pinning is present; it is not established as the sole cause of colour breakup. The current pyramid path does not retain original saturation provenance. Simply rejecting clipped contributors risks replacing sharp highlights with darker blurred observations, a prior measured failure.

Direct joint CFA reconstruction is the next implementation question. It can use several frames' measured colour samples before individual interpolation. A targeted prior-work review found no actual direct multi-frame CFA reconstruction consumer; the old PHASE final disposition was NOT ROBUST, and M193 tested the existing MHC/gather/pyramid path. See joint-cfa-decision.md for the fixed first falsifier, scope, alternatives and independent controls. Existing-map diversity is only prospective geometry, not a placement-accuracy or image-quality claim.

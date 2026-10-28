# Independent observer control review

2026-10-27. **VERIFIED from saved producing receipts:** the observer preserves the tested fits, decisions and input bytes, and the fixed generated discriminator separates its planted anisotropy from symmetric defocus. This supports collecting the missing real observations. It does not establish a weevil placement error, a useful replacement warp or photographic improvement. The complete actual 299-source observation was still running when this first section was written.

## What the controls establish

The [core receipt](../../../outputs/raw-quality-2026-10-27/insect-placement-controls-core-1/output/core-screen.json) passes unchanged observer off/on result bits, tile census/coordinates, selected-pass bookkeeping and input preservation. Flat-stage and coarse refusals remain explicit. The boundary fixture actually reaches `FinePassFailedRetained`: the second pass has only one correlated tile after the right-edge expanded patches fail; pass0 is retained. This is executed branch coverage, not an inference from source.

All 35 predeclared sites correlate in the four geometric cases. Their first-pass vectors are scored **before** outlier removal:

| Fixed case | Signed planted-field amplitude | Vector RMS error, guide pixels |
| --- | ---: | ---: |
| Sharp fixed geometry | −0.000184 | 0.007132 |
| Symmetric defocus, fixed geometry | 0.002133 | 0.037490 |
| Known anisotropic movement | 1.003402 | 0.051772 |
| Same movement plus symmetric defocus | 1.000417 | 0.096247 |

The positive limits remain [0.75,1.25] and 0.35 guide pixels; the null signed-amplitude limit remains 0.20. Null mean-displacement limits also pass. The defocus null loses one tile in the aligner's later MAD pass, but that tile remains in the reported 35-site discriminator. The fixed translated-patch control separately produces one recorded outlier. Thus neither positive nor negative conclusion depends on selecting only clean survivors.

The wrong-coordinate foil halves measured displacement in a copied trace and passes it through the same scorer. It fails both positives: amplitudes 0.5017/0.5002 and vector RMS 0.5874/0.5922 guide pixels. This checks a meaningful direction of coordinate failure; it is not a second fitted reference.

The [CLI receipt](../../../outputs/raw-quality-2026-10-27/insect-placement-controls-1/output/screen.json) retains all ten pair attempts from five guides, exactly the three textured edges, the three-frame connected component with cycle rank1 and two explicit refused frames. Ordinary/observed edge bits and the actual normal-solve map match exactly. The labelled-u16 test invokes actual `green_luma`; the R/B-to-green-slot substitution traverses that same consumer and fails against the literal green expectation. Original u16 and guide bytes remain unchanged. The static repeated textures test observer consistency, not extra acquisition information or deep-track accuracy.

## Limits on interpretation

The generated field is one high-contrast analytic texture, one anisotropic displacement and one symmetric blur amount with fresh noise added after blur. The signed template is similarity-orthogonal only on the complete symmetric 35-site grid; the scorer correctly refuses an incomplete population. Its pass is not a general calibration of NCC uncertainty, an occlusion test, a radial-distortion detector or proof that all defocus biases are harmless. Defocus already raises local vector scatter in the null. No curved focus-breathing track is qualified by these pair-only controls.

Guide displacement is in half-native pixels; multiply displacement by two without adding an origin. The green guide's physical centroid is (2u+0.5,2v+0.5). The fit-center remains the actual `tx+tile/2`, relative to `W/2,H/2`, rather than the template sample centroid. Neither a source-i guide coordinate nor its grid ordinal is automatically a common anchor149 subject point. The completed real trace must still be transported through the correct pull/inverse convention and checked for overlapping physical support before a sliding-pair comparison.

Initial all-pair summaries may reveal censorship, scatter or an unstable measurement population. They cannot by themselves assign a residual to an insect hair. Crossed spans1,8,32 and different pair midpoints need common physical and focus support; otherwise the prescribed outcome remains **UNIDENTIFIABLE**. A fitted field explaining the same NCC vectors would not be independent placement truth.

Root's [core command](../../../outputs/raw-quality-2026-10-27/insect-placement-controls-core-1/process.json) and [CLI command](../../../outputs/raw-quality-2026-10-27/insect-placement-controls-1/process.json) used the fresh build1 test executables, exact ignored test names, `--nocapture --test-threads=1`, and exited0 with no cleanup errors or remaining processes. Core wall time was1.766s/15,544,320bytes peak job commitment; CLI0.469s/7,065,600bytes. The CLI internal measurement pool used two workers. These are instrument costs, not competitive stacking speeds. Complete generated f32 fields and fixed native PGM displays are retained beside the core receipt; the available image viewer rejected PGM, so this review makes no visual-quality claim or newly rendered preview. No numerical job, RAW read, threshold change or source modification was performed during this results review.

## Actual 299-source observation: instrument preserved, geometric cause unresolved

**VERIFIED from saved receipts:** the [complete observation](../../../outputs/raw-quality-2026-10-27/insect-placement-observe-1/output/receipt.json) retains all2,340 pairs and224,640 fine tiles, including26 core refusals. There are2,314 edges; all299 sources remain placed in reference149. Original inputs and guide bytes are unchanged, and four additional real off/on pair fits agree exactly. The [historical comparison](../../../outputs/raw-quality-2026-10-27/insect-placement-observe-1/output/historical-map-comparison.json) preserves all299 placement bits and both diagnostics: held-out3.358753 and cycle1.553985 guide pixels. The complete alignment text also has the held map's SHA256 `4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225`. These are consistency checks, not an external geometric reference.

Root's [saved command](../../../outputs/raw-quality-2026-10-27/insect-placement-observe-1/process.json) ran the exact ignored test `align_cmd::insect_placement_observer::observe_complete_weevil_alignment` with the fresh CLI executable SHA256 `471767227c8e449fe3c4019a8127e72f905c7bd784567093ac01c3d77e2f5214`, four alignment workers and unchanged saved configuration. Exit0,139.250s,10,139,885,568bytes peak job commitment, no cleanup errors or remaining processes. The actual configuration uses one fine pass,128-guide-pixel tiles, a12x8 grid, radius6 and unwarped tiles. Thus the real run does not exercise the retained-later-pass branch; that coverage comes from the generated control.

The [descriptive census](../../../outputs/raw-quality-2026-10-27/insect-placement-summary-1/output/summary.json) and [all-correlated CSV](../../../outputs/raw-quality-2026-10-27/insect-placement-summary-1/output/signed-residuals.csv) make a materially changing measurement population visible:

| Predeclared span | Pair attempts | Correlated tiles | Low contrast | Search-border peaks | MAD outliers | Final residual RMS x/y, all correlated | Final RMS x/y, survivors |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
|1|298|14,008|14,569|31|916|0.364/0.259|0.088/0.098|
|8|291|13,645|14,233|58|327|0.839/0.905|0.752/0.863|
|32|267|8,400|13,081|4,004|102|2.063/2.484|2.028/2.437|

RMS units are guide pixels in each source-i-to-j pair. `Border` means the correlation maximum lies at the search-window boundary; it does **not** mean the image footprint is outside the frame. All three spans have zero `Oob` tiles. All26 pair refusals occur at spans96/128. The growing residuals and search-border count can reflect displacement, changed visible texture or defocus-sensitive matching; their aggregate trend does not identify which. The near-zero mean of final survivor residuals is constrained by fitting, not evidence of unbiased physical placement. Likewise, throwing away short spans or choosing the clean survivors would change the question and repeats a known-harmful direction.

The CSV reconstructs descriptive f64 residuals from saved f32 observations and saved f64 similarities. It is not an exact decomposition of the original f32 scalar RMS. No anchor transport is performed by this first census, whose `crossed_physical_support` is explicitly `UNASSESSED`. **Current decision: no correction or lens law is supported by this summary.** This is not a rejection of the observer branch: root has separately released a no-fit map-transport/footprint census for fixed spans1,8,32 and all96 tile locations. Its result remains to be reviewed before deciding whether a crossed comparison exists.

The already inspected [31-source timeline](../weevil-through-focus-support/observation.md) provides bounded photographic context: seam50–70, scales80–100, thorax90–110, hairs140–160 and blue joint110–140. These are broad visible focus neighborhoods, not calibrated depths or tile-level sharpness labels. Their exact source crops were correspondence locators with source-scale and rounding differences; no equal-footprint or missing-source-structure claim was established. The forthcoming footprint census must therefore retain failed matches and establish conditional overlap before these observations can even help interpret a fixed tile. Geometric overlap alone will still not prove the matcher followed the same structure through focus. No new numerical job, RAW read, crop search or quality claim was made for this independent review.

## Completed conditional transport: enough for a bounded stability test, not a warp diagnosis

**VERIFIED:** the [support census](../../../outputs/raw-quality-2026-10-27/insect-placement-support-1/output/support.json) accounts for all856 declared pairs and82,176 tile slots. Every reference-i footprint has positive intersection with its fixed same-ordinal anchor149 template. The minimum source fraction is0.7440, template fraction0.7250 and IoU0.5803; mean IoU is0.8860/0.8878/0.8933 for spans1/8/32. These are continuous observations, not a newly chosen acceptance threshold. Identity, literal inverse/center, translated-overlap and disjoint controls pass; wrong-direction and wrong-center foils fail. Saved inputs remain bound and unchanged. Root's command is retained in the receipt; the bounded job exited0 in3.765s with18,984,960bytes peak commitment and no RAW reads.

This removes the particular objection that equal grid ordinals could have entirely unrelated image support. It does **not** establish equal support: the polygons are reference-i sample cells transported by the same held map under investigation. They do not describe the actually matched moving-j patch, a defocus footprint, or visibility. Pairwise overlap with the template is not a proof of one jointly shared sharp structure throughout the bracket.

I reopened the complete sources60,100,150, then the already exported native384 seam/thorax/hair witnesses. No crop or display was regenerated. They confirm different focus states at separated subject regions: dorsal scales/seam around60, thorax around100 and upper leg/hairs around150. The fixed anchor tile geometry and saved status census give concrete potential sites:

| Tile ordinal; guide origin | Photographic context, without a new correspondence claim | Span1/8 correlated counts | Span32 census |
| --- | --- | --- | --- |
|15;(967,385)|Substantial overlap with the upper-leg shaft/hair witness; the patch contains both surface texture and its boundary|298/298;291/291|132Ok,135Border; two later outliers|
|41;(1548,963)|Upper texture within the seam witness; do not name it a seam-edge measurement, because the displayed diagonal seam lies mostly below this tile|298/298;291/291|210Ok,57Border|
|56;(2420,1252)|Partial overlap with the right side of the thorax witness; no whole-tile structure identity has been commissioned|298/298;291/291|47Ok,154Border,66LowPeak|

These locations were examined from the existing photographic witnesses and literal grid geometry, not selected for residual direction or small error. The complete span1/8 populations at these sites provide a useful crossed *observational* comparison across focus positions. The span32 failures remain an adverse population, rather than a reason to replace the sites or drop long-span failures. The observed high overlap is therefore a reason to retain a narrowly scoped stability question, not to reject the whole investigation as geometrically unsupported.

**Independent decision:** the present evidence is sufficient to test one predeclared field's **held predictive stability of measured NCC vectors** under different focus states. It is **UNIDENTIFIABLE as physical placement error or a lens law at this point**. The most useful constrained next step, if root selects a concrete field hypothesis, is a single saved-data test at these fixed photographic regions using spans1/8, all correlated vectors and the recorded refusal/outlier flags; retain span32 as the adverse readout. Freeze the field/null and non-overlapping acquisition train/held split before inspecting its signed result. Do not randomly split tile rows that share source images. A stable result must also survive the photographic question of what structure occupies both patches; successful prediction of these same matcher measurements alone cannot answer that question. Failure should close that specific field hypothesis without a wider basis, span or crop search.

No richer warp, alignment correction, source ranking or new full render is justified by this report alone. Neither the source photographs nor this unchanged observer are improved stack outputs. The unresolved softness and halos, the failed prior reconstructions, and the requirement for a complete photographic comparison remain unchanged.

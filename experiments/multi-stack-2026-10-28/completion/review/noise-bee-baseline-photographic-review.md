# Fixed-focus bee baseline: independent full-photo review

**VERIFIED inspection,2026-10-28.** All four complete-scene overviews and all36 frozen native384x384 witnesses were inspected: passA, passB, equal Repeat and precision Repeat. The reviewed results preserve recognizable eye facets, hairs, antenna edges, highlight shapes and defocused structure within these witnesses, without an obvious new ghost or color defect. No visible noise reduction or new detail benefit is established by this baseline. This is a photographic preservation result, not an absolute noise/SNR measurement and not closure of the intended useful repeat outcome.

## Artifact and comparison identity

The output root is `outputs/multi-stack/completion/noise-bee-repeat-01`. Every arm has7004x4668 native pixels, canvas `[7,5,3502,2334]` in quads, zero reported invalid output pixels and the same render-bound alignment SHA256 `373bb1c08f4bf8606a63a3d28e746ba00fc062046c8248d54599f4cad300c3c7`. The four runs exited0 using product16 CLI SHA256 `0b7dfc0eaa0593b8981c2fd8d979013fa60ef6407f08fd3f6bd4c240aa6977e5`. Each retained command, environment and sampled-resource receipt is `outputs/multi-stack/completion/noise-bee-repeat-{pass-a,pass-b,equal,precision}-run-01/receipt.json`; no engine or RAW operation was launched by this reviewer.

The declared recipe is8workers/16GiB, CatmullRom,7bands, gate2, agreement4sigma, SoftPower exponent2, Mean base/fallback, zero added exposure, no primary and no original-CFA reconstruction. Development reference pass0 is common. Precision alone enables independent-guide precision weights with equal-observation focus selection; contribution diagnostics are enabled for both combined arms. Within-pass source gathering/selection already averages according to the ordinary engine, so the16-source controls are not single exposures.

PassA and passB each consume16 acquisitions as16 singleton groups. Both32-source combined arms have28 groups: only4 two-source groups and24 singletons. Therefore this baseline does not test a full32-frame burst average or even16 admitted cross-pass pairs. Coefficient admission can also choose ordinary fallback; group counts are not delivered independent sample counts or a variance calculation. Near-equal exposure/noise makes precision-versus-equal a secondary near-null comparison; repeat-versus-both16-source controls is the relevant photographic question.

## Display and exact frozen witnesses

Reviewed `noise-bee-repeat-inspect.py`: it reads the complete float32 linear masters, uses fixed per-channel black0.00033/white0.38858 and sRGB transfer for every arm, and never adjusts per-arm contrast. This transform was frozen from passA before combined output inspection. Its whole-scene1:4 subsample followed by overview fit is orientation only; all detailed comparisons use exact384x384 display pixels without resampling. The reviewer checked the36 PNG SHA256s against the inspection receipts and exact equality of crop origins, dimensions and display settings across all four arms. Complete master digests are retained in those author-produced receipts; this review did not rehash the large masters or rerun the producer's full finite scan.

| Witness | Native output origin `[x,y]` | Observation across all four arms |
| --- | --- | --- |
| Dark background |[841,2404]|Very dark, sparse colored points persist; the fixed display has limited noise sensitivity here.|
| Upper background |[5447,318]|Same near-black limitation; no visual sigma or zero-noise conclusion.|
| Antenna shaft |[2318,2531]|Defocused shaft, circular highlights and crossing hairs remain comparable.|
| Eye facets |[3710,2292]|Facet pattern and contrast remain recognizable; no established extra separation or erased pattern.|
| Dark eye |[3598,2568]|Low-contrast facet transition preserved; no clear noise advantage established.|
| Brow hairs |[3577,1752]|Bright strands and dark gap boundaries remain comparable, without a newly obvious duplicate edge.|
| Chin hairs |[3535,3098]|Fine diagonal strands and colored highlights remain comparable.|
| Defocused body |[1966,3487]|Smooth gradients and blurred hair structures persist; smoothness alone cannot establish noise reduction.|
| Specular face |[4231,1795]|Dark reflective transition and bright strand remain comparable; no demonstrated recovery claim.|

Add `[14,10]` to these origins to recover the full active-sensor origin. Witnesses were fixed from embedded-preview physical locations before candidate review. No witness was moved, dropped, contrast-enhanced or selected from the differences. The complete overviews also showed the same overall field, focus extent, tone and body structure. These observations do not establish equality at every full-resolution pixel or prove the absence of small artifacts outside the frozen witnesses.

## Consequence for the next matching experiment

Retain these exact outputs as the sparse-pair baseline. An uncertainty proxy based on native residual/lever arm and cycle disagreement may nominate more one-to-one cross-pass candidates, but it is not a calibrated geometry sigma or evidence of physical focus equivalence. Maximum-cardinality matching must only use independently admitted PSF/photometry-compatible edges and leave uncertain sources as singletons. Require actual matching-plus-core controls for fine genuine focus sweeps with almost unchanged scale, flat-only evidence, local blur/lighting changes, wrong-period correspondence, high-noise selection bias and pass/source-order changes. Spatial calibration/selection footprints must remain disjoint from the observer's measurement/reference footprints, including every nonzero interpolation and guide/filter tap.

A later positive statistical result must retain both physical-time targets and all frozen Q/V-qualified masks; midpoint improvement alone can be caused by noiseless drift. A candidate-minus-constituent difference, background spatial standard deviation or larger pair count cannot supply the missing noise claim. The separately commissioned two-state temporal-risk assay remains necessary. No real R/M assay is authorized by this review document.

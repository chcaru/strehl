# Independent HDR photographic review

VERIFIED visual review, 2026-10-28, root/independent_review. This reviewer did not implement the HDR calibration or fusion. The review follows [the pre-image frozen plan](hdr-photographic-review-plan.md) and [mapped witness receipt](hdr-roi-mapped-frozen.json). Root alone scheduled renders. No RAW decode, engine run, parameter fitting, witness reselection, or product edit was performed in this review.

## Decision and incremental claim

The accepted two-pass HDR output preserves the short exposure's visible QR, bar, bright-dot, and radial-star structure where the six-second-only control blurs, halos, or flattens it. The two frozen original-clipping core witnesses show faint regular texture in the long-only output that is absent or much less visible in the short-only and fused outputs. There is no gross missing chart field, canvas inconsistency, new broad seam, or obvious new color break in the complete fused overview.

Against the complete 2.5-second-only control, however, the fused result has no clear additional detail, shadow improvement, or noise benefit in these witnesses. Several high-contrast edges look slightly softer in fusion. The low-contrast dots and lower radial spokes are broadly similar across arms. This is a successful, bounded two-exposure capability demonstration and a visible improvement over the six-second-only rendered result. It does not establish an incremental photographic advantage over the best complete single-exposure control, recovered physical resolution, temporal-noise improvement, or a reason to promote a new default.

The successful 2.5s/6s pair must not erase the refused three-pass 1s/2.5s/6s case. Its retained photometry evidence, including focus-related flare and incompatible local radiometry, still limits the scope of the method. Spatial holdout agreement is a bounded constant-gain check, not proof of physical focus correspondence or universal exposure calibration.

## Complete artifacts, common basis, and inspection coverage

All three complete float masters and photographs exist. The preparation helper checked finite masters and dimensions, then produced full 6928 by 4620 common-display PNGs. I inspected each complete scene through its 1400 by 934 overview in both predeclared displays, and inspected all twelve native 384 by 384 witnesses for each of the three arms in both displays: six complete-scene overviews plus 72 native crops. Overview resizing is for orientation only; the native crops are integer pixel slices with no spatial resampling. The saved readback receipts bind the full images, crops, source float regions, ICC, dimensions and transform.

| Arm | Build | Selected sources | Fusion groups |
| --- | --- | ---: | ---: |
| slide-hdr-pair-6 | c149e52834fc-multi-stack-candidate6 | 126 | 77 |
| hdr-short-7 | c149e52834fc-multi-stack-candidate7 | 61 | 61 |
| hdr-long-7 | c149e52834fc-multi-stack-candidate7 | 65 | 65 |

VERIFIED from saved metadata: all arms use the exact same serialized 126-source warpmap, SHA256 a8afec6897a6be67df7b0fc04071fc352e239443eb8685302c2b49c830552c08, and canvas [26,17,3464,2310] in plane pixels. Every corresponding source's measured luma/color beta, probe counts, calibrated gain, path/pass identity, coverage and clipping fields equal those in the fused report. All arms report zero invalid output pixels. The controls' development_reference_pass is 1, matching the fused anchor. The output WB is [2.7392578125,1,1.560546875] and the matrix is identical. This closes the different-WB control confound identified before image viewing. Candidate7 adds prefetch and the explicit control WB fix; individual source operators and gains were not re-fitted for this review. Build and renderer-source identities are retained, rather than pretending the executable builds are identical.

The two displays were fixed before viewing the fused output: black 0, white 4, contrast 0.55, with exposure gain 1 and 0.25 respectively. The same previously commissioned soft-toe/gamut/sRGB implementation and ICC were applied to every arm. Neither transform uses an arm's auto-tone metadata. The second display is a fixed additional two-stop reduction; it gives the same qualitative findings and does not reveal a hidden fused advantage. These constants are deliberately not an optimal fit to this scene.

The frozen landmark transfer uses measured geometry only to place broad chart witnesses in the common six-second anchor gauge. It is not independent placement truth. Origins were rounded once using the saved rule before output viewing. The three clipping witnesses were selected from original six-second middle-source block counts with deterministic tie breaks, rather than from favorable output pixels. No crop was moved after inspection.

## Native observations

Each row below was inspected in both displays for long-only, short-only and fused outputs. Origins are shared native full-image coordinates; all squares are 384 pixels wide and high. These are visual observations, not measured resolution or noise estimates.

| Frozen witness | Origin x,y | Long-only comparison | Fused versus short-only |
| --- | --- | --- | --- |
| gray-ramp-middle | 957,416 | Dust/marks are less defined and the gray transition is softer. | Closely similar structure; no established noise advantage. |
| adverse-flare-p12 | 4157,1565 | Bright corner structures above the chart border are blurred. | Border remains continuous, short structures retained; no obvious new seam. Does not validate the refused third exposure. |
| qr-white-black-grid | 3957,415 | White-grid edges and small marks are softer. | Both retain corners and small marks; no clear fused increment. |
| qr-corner-boundary | 4657,1165 | Strong blur, broad halo and tonal plateaus around the nested square. | Both preserve the square geometry; fused edges look slightly softer. |
| large-radial-star | 5857,615 | Wedge boundaries are blurred/haloed. | Fused follows short-only wedges, with slight edge softness possible. |
| fine-resolution-bars | 5157,1815 | Bars are strongly blurred, with colored fringes. | Both preserve separation; some fused boundaries are less crisp than short-only. |
| bright-dot-field | 558,2015 | Broad halos and inner plateaus disrupt round dot boundaries. | Short-only and fusion retain the round boundaries; neither proves an extra fused benefit. |
| low-contrast-dot-field | 3957,3115 | Broadly similar to both other arms. | No clear extra fine structure or noise benefit. |
| lower-radial-spokes | 1257,4115 | Broadly similar spokes and colored edge fringes. | No clear added line separation; residual fringes remain. |
| clipped-core | 44,894 | Faint regular texture/banding is visible in this largely flat field. | Short-only and fusion are more uniform. Flatness cannot establish recovered detail. |
| blue-clipped-core | 556,894 | Similar faint regular texture in the largely flat field. | Short-only and fusion are more uniform; no fine-detail recovery certificate. |
| clipped-boundary | 1580,830 | Broad low-frequency variation and texture remain. | Short-only and fusion retain the gradient and look closely similar. |

## What the clipping evidence establishes

MEASURED upstream original-u16 evidence, independently read here from the retained derived block-count report: the central 64 by 64 sensor block in each of clipped-core and blue-clipped-core has [0,1024,1024,1024] clipped sites in R/G1/G2/B, out of 1024 sites per color, in the six-second middle source DSC00047.ARW. The clipped-boundary block has [0,1023,1024,0]. These are sensor facts, not display-white inference. They describe those blocks in that physical source; they do not assert that every pixel of every 384-square or every long-pass frame is clipped.

VERIFIED actual consumer census: all 61 short sources have full canvas coverage of 8,001,840 plane pixels and zero clipped original footprints. Therefore uncensored short evidence is available everywhere in the delivered canvas, including the frozen clipping blocks. All 65 long sources have the same full coverage but each reports 422,476 to 639,517 clipped footprints; the sum is 35,569,229 across sources, not unique output pixels. Corresponding support fields are identical in the controls. This uses the real accepted pair's full census, rather than importing the older 1s-middle opportunity calculation as proof of 2.5s support.

These reports establish source availability, not the exact local band weights in the delivered image. There is no retained per-pixel/per-band contribution receipt for the frozen witnesses. The proven clipping cores are also mostly flat, so their more uniform fused appearance does not demonstrate recovered fine structure. The sharper QR, star, bar and dot witnesses show preservation relative to the long-only output, but this bounded review has not established co-located original clipping and admitted short-band contribution at every one of those edges. Acquisition/focus differences and clipping may both affect the long-only blur. It would be incorrect to attribute every visible difference exclusively to clipping or to call these comparisons a resolution measurement.

Accordingly, the supported language is: the complete two-pass result handles this clipped-long/unclipped-short capture pair without losing the short exposure's visible chart structure and reduces the visible long-only artifacts in the frozen clipped fields. An incremental detail or noise gain over the short-only full result remains UNVERIFIED. No additional campaign is required to report this bounded result honestly.

## Commands, identities, and preparation failures

The successful display command was run from the isolated multi-stack checkout, with OMP_NUM_THREADS=1, OPENBLAS_NUM_THREADS=1 and MKL_NUM_THREADS=1, and returned exit 0:

    python -X faulthandler -I experiments/multi-stack-2026-10-28/review/prepare-hdr-displays.py

It reads existing complete masters; it does not decode RAW or invoke the engine. [prepare-hdr-displays.py](prepare-hdr-displays.py) contains the exact preconditions and source receipt comparisons. Successful artifacts are exclusively under hdr-displays-complete. Two earlier wrapper failures are preserved: missing ICC beside the transform file, then a dictionary supplied where the helper required a ROI list. The first produced no PNG; the second did not produce completed readbacks. Those directories are not used as evidence. The fixes copied the already frozen ICC and supplied the existing list; no display constant or witness changed.

The metadata-only binding command returned exit 0:

    python -X faulthandler -I experiments/multi-stack-2026-10-28/review/bind-hdr-photographic-review.py

[hdr-photographic-review-binding.json](hdr-photographic-review-binding.json), SHA256 6498edd1bfed49ec37bc3aa0973b584cb9495463360c39346b6bf06a49783ebc, binds all six successful display readbacks, their full-image and crop hashes, master hashes, source builds, support census, and pre-image freezes. The pre-image freeze SHA256 is 012d3809c843d9a5491d89b2c028c0363d6d22d93767d327efeda10869f1b301; mapped ROI SHA256 is 3042ba14c828a6c44cb391ac1d79f4014108fbcd4cd5f7c44763abe19db7ef71. Preparation timings and render elapsed fields are not a performance comparison.

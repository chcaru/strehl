# Independent photographic review: garnet104 rendering factorial

VERIFIED visual inspection on 2026-09-25 of all four complete 1617px overviews and all eight frozen unresampled 384px tiles in `experiments/quality-september25/garnet-render-views-1/receipt.json`. I also independently selected and inspected a blue/red protection tile at output `[2970,2500,384,384]` in every arm. Its images and receipt are in `independent-garnet104-blue-views/`; conversion is the same rounded RGB16/257 with retained ICC, no local tone or resampling. Full master dimensions are 6524x4348.

The root's retained `replay-garnet104-1/completion.json` and output receipt bind one identical full 183-source cache, unchanged resolved development, current full RGB16+ICC equality against the delivered master, and observer on/off equality. This is a rendering comparison; it does not test a changed merge or alignment.

**Verdict: none of these three alternatives establishes a useful image-quality improvement on garnet104. Do not promote this factorial as a glare or artifact fix.**

| Arm | Independent observation |
| --- | --- |
| Current | Broad diagonal bright reflection with two conspicuous hard rectangular magenta/cyan-edged islands in the white-facet tile. Red facet texture and the separately chosen blue arc provide colour/detail protection targets. |
| Sensor rolloff off | No visible repair of the broad reflection or rectangles. All three inspected 384px preview files are byte-identical to current, and the whole overview is also identical. This does **not** assert full RGB16 equality: the retained master pixel hashes differ. |
| Shoulder | The rectangles and their coloured boundaries persist. The bright facet does not disclose convincing additional interior texture or gradation at native scale. Small glints in the red control and blue/red boundary become visibly brighter/whiter-looking; that is a change in rendering, not evidence of more real detail. The blue arc remains coloured. |
| Both | The rectangles and bright patch persist. Native appearance is close to the shoulder arm; it does not reveal a clear detail or colour benefit over current. The separately chosen blue arc remains present and coloured. |

The complete views retain the same overall red mineral, black field, extent and obvious bright reflection. Any small global tonal differences are insufficient to judge native structure; all artifact and fine-colour findings above come from the 384px unresampled views. The additional tile deliberately crosses a strong blue/red boundary and bright red glint, rather than choosing another neutral region where colour damage would be hidden.

The broad reflection has support in original RAW witnesses already recorded in `quality-september25/minerals/diagnosis.md`; deleting it is not an acceptance target. The rectangular islands lack corresponding hard geometry in the three sampled original CFA witnesses, but that limited sampling does not localize the fault. Every factorial arm retains `Render::clip_highlights`; therefore persistence across these arms cannot prove an upstream merge origin. The forthcoming stage probe should locate the first stage that creates the discontinuity before a repair is chosen.

No white-count, gradient, or brightness-lowering score was used to rank quality. No claim is made about high-highlight noise safety or exact original hue truth. No new RAW was decoded, no new stack rendered, and no production source changed for this review.

## Addendum: prewriter CFA cache localizes the rectangular geometry

VERIFIED independently from the newly saved `quality-september25/garnet-cache-planes/{r,g1,g2,b}.npy/.png` and root's `inspect-garnet-cache.py`. The complete saved cache SHA256 is `591746c200ee9b92c3a1446f78f22286944504ba46095e2b56985abe246c696d`. Re-read binary and all four plane hashes agree with metadata. Every NPY crop is bit-identical to the corresponding cache slice, and every PNG is pixel-identical to the declared fixed display transform. The independent receipt is `quality-september25/garnet-cache-planes/independent-check.json`.

Coordinate mapping is correct: native output `[4668,1858,384,384]` selects compact quad slice `[2334,929,192,192]`. Including the saved CFA crop origin `[127,85]` gives full-gauge quad origin `[2461,1014]`. The cache stores four contiguous little-endian f32 planes ordered R,G1,G2,B with geometry3262x2174, after `BandMerge::finish` and before `Merged::value`, WB, MHC, matrix, highlight treatment, tone, and gamut mapping. The actual cache writer and consumer source paths were reviewed to establish that ordering.

Visually, the two corresponding dark rectangular notches are already present in these 192-site unresampled CFA-plane views, clearest with straight boundaries in G1/G2, also visible in R and B. This is new evidence that **the rectangular geometry exists upstream of the writer**, superseding the earlier factorial-only inability to localize it. Later rendering may amplify the magenta/cyan appearance; the cache alone does not identify whether gathering, band weighting/reconstruction, or output hull handling first created the geometry. The three original-source witnesses remain insufficient to prove its absence across all183 inputs.

The previews use `sqrt(clamp(value/15871))*255`, where15871 is the recorded-container maximum16383 minus black512. This differs intentionally from nominal white15360 minus black512 =14848 used in the saved levels. The root's original `at_sensor_span` label is ambiguous and is being clarified to values at/above the container-minus-black threshold. Counts on merged floating-point values cannot prove original RAW clipping because interpolation or merge overshoot can cross that threshold. Neither count is used in the geometric diagnosis.

The next useful observation is upstream within the merge. No additional writer-stage run is needed to establish where this geometry already exists.

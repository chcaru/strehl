# Independent bright-boundary attribution

**Observed:** at all three fixed QR/Siemens sites, the conspicuous broad gray
spread appears in the complete merged result while the nominated original
and gathered sources have substantially cleaner dark regions. The gathered
versions do not introduce that broad pattern into these sources. This is a
useful reconstruction witness, unlike the earlier small-bar sites; it is
neither a candidate improvement nor a general claim about mineral glare.

I inspected the complete current overview, pale149 first, all21 fixed native
raw/gathered/merged panels, and the separate G1/G2 views for all six structured
nominees. No region, source, display setting or metric was changed.

| Fixed output-native region | Source ordinals | Stage observation |
|---|---|---|
| QR upper [3700,490,384,384] | 83,85 | Original and gathered isolated white squares have slightly soft, colored edges, but the surrounding black gaps remain comparatively uniform. Merged retains more definite square edges while adding broad polygonal gray surrounds. The same spread fills dark corners beside the larger connected white shape in the lower half. It is distinct from the narrow magenta/cyan source fringe. Both nominees support this comparison. |
| QR lower [3900,900,384,384] | 92,94 | The dark interval beneath the broad white rule and the gaps around the lower vertical white elements are clean in both gathered witnesses apart from narrow edge softness. Merged adds a broad gray band below the rule and rounded/polygonal spread around the lower elements. Some upper source features remain defocused, so neither nominee is full-patch truth; nevertheless the identified dark-gap difference is present in both comparisons. |
| Siemens contact [5260,750,384,384] | 58,60 | Both original and gathered views retain a recognizable central meeting point, with largely uniform dark wedges and narrow colored boundaries. Merged preserves the junction but places broad gray fans inside the dark wedges, especially rightward and downward from the center. The wide interior gradation is not just a shifted or doubled thin edge. Both neighboring sources show the same qualitative absence of that merged pattern. |
| Pale [792,600,384,384] | 149 | The previous pale-field result repeats: merged has finer granularity and faint point structure. It is not a calibrated flat or temporal-noise reference and cannot establish that every added point is false. It does not explain the strongly shape-dependent spread at the other sites. |

The separate green phases show the same cleaner original dark gaps/wedges;
the conclusion does not depend on a G1-only feature or on interpreting colored
fringes as gray spread. Their pitch2 monochrome display is supplementary,
not a replacement for the matched product-rendered witnesses.

## What this establishes

The same final development is used for raw, gathered and merged witnesses.
Only gathered and merged share exact reference-grid coordinates. Their
comparison shows an unwanted broad contribution in the assembled result
relative to the inspected, plausibly focused input neighborhoods. This does
not require assuming that raw source-centered patches are registered.

**Inference, not isolated cause:** multi-source reconstruction is now the
useful next intervention point. Retaining blurred contributions from other
focus positions is consistent with the result. The six selected originals
do not prove that all299 inputs lack this spread, and the comparison does
not isolate terminal Mean, coarse AC selection, placement of other sources,
or their interaction. In particular, calling terminal Mean the demonstrated
cause would exceed the evidence. The broad pattern is not created by the
gather of these six nominees, but this does not exonerate alignment everywhere.

Any next reconstruction comparison must preserve the identifiable white
edges and the earlier fine bar/letter separations while cleaning these dark
regions. Darkening or smoothing the whole image would not establish a fix.
These are three planar printed-pattern witnesses, not validation on flowers,
deep occlusions or minerals.

## Evidence and full output

Root executed the prepared command:

```text
python -I -B -X faulthandler experiments/slide2-bright-boundary/render.py --locator experiments/slide2-bright-boundary/locate-1 --out experiments/slide2-bright-boundary/render-1
```

The complete299-source observer-on render succeeded and equals the retained
current observer-off result in every RGB16 sample and whole TIFF byte. The
full6476x4316 TIFF is `render-1/on/output/replay.tiff`, SHA256
`24c66183ae94df908eb4a8662fc4b032532b7721655dfcc867e9a7d59b4f655b`;
the complete native PNG and labeled overview are also retained. No second
observer-off render or candidate algorithm was run.

All seven locator-u16-to-actual-observer CFA comparisons differ by zero f32
bits at the exact padded sensor origins. All merged panels equal their full
output slices; the wrong-origin controls differ. Selected original content
and all original metadata remain unchanged. The source nominations remain
scalar-focus suggestions with a demonstrated noise failure, not quality
truth. Saved native views and receipts, not new scans or numerical scores,
support this review.

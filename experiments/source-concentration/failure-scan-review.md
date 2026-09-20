# Independent real-scan failure characterization

**The unmodified rule produces no source nominations in either retained field.**
The separately authorized descriptive scan therefore supplies no selective
detector success to take forward. Preserve the synthetic radial rejection and
close this fixed rule without threshold changes. This is not evidence that
source morphology is generally unusable, or that the photographed compact
source witnesses were wrong.

MEASURED complete denominator:124 tracks, comprising63 in dark-inclusion and61
in facet-edges. All124 are refused:114 have `no-eligible-frame`, seven have
`unstable-immediate-neighbours`, and three have `no-stable-contraction`.
The complete table is `failure-review-1/all-seeds.md`; no unmatched seed or
unsuccessful track is omitted.

Across8680 frame/track records, recorded eligibility reasons include centroid
displacement7433 times, measurement-disk boundary contact6031, insufficient
relative peak5284, ambiguous identity4078, insufficient relative mass2199,
display-ceiling contact1307, unknown radius878, no positive peak519 and singular
covariance359. These reasons overlap, and nearby tracks/source frames are
correlated. The counts describe refusals, not independent trials, physical
defect prevalence or calibrated confidence. In particular, display-ceiling
contact does not establish original RAW saturation.

## Fixed-location checks

Nearest-seed distances are coordinate descriptions, not component association.
All three nearest seeds are retained for each evaluation point in the summary.

| Evaluation point | Nearest seed | Distance, native px | Eligible frames | Result |
| --- | --- | ---: | ---: | --- |
| Facet core(2624,2906) |(2613,2899)|13.038|0|No eligible frame|
| Facet fixed fan(2602,2945) |(2619,2947)|17.117|0|No eligible frame|
| Dark core(3080,2150) |(3071,2159)|12.728|0|No eligible frame|
| Dark fixed fan(3102,2203) |(3083,2211)|20.616|0|No eligible frame|
| Visible dark tail, identified after repair failure(3080,2212) |(3083,2211)|3.162|0|No eligible frame|
| Nearby structure(3240,2070) |(3259,2045)|31.401|0|No eligible frame|

The original fixed fan points remain alongside the subsequently identified
visible tail; the latter did not replace them. Expected source neighbourhoods
28/33 and nearby-structure25 are visual witnesses, not exact label truth.

The nearest facet-core and facet-fan tracks record centroid displacement and
display-ceiling contact in all70 sources. The nearest dark-core track records
disk-boundary and display-ceiling contact in all70. These are active image
components, not missing image support: the original source context was expanded
and verified by the runner. The rule frequently does not isolate a complete
local feature within its fixed geometric conditions on this scene.

The seed only3.162native pixels from the visible dark tail provides a useful
check against blaming every failure on seed placement. It has no positive
local contrast peak in46 frames, including retained witnesses25,28,33 and35.
At52 and69, it has a positive component but is refused for disk-boundary contact,
centroid displacement and display-ceiling contact. Its reported centroids lie
upstream at approximately(3089.96,2179.36) and(3083.78,2182.94), rather than at
the seed(3083,2211). Thus the fixed rule does not produce an accepted trajectory
linking this late bright extension to an earlier compact source. No claim of
connected-component membership is made from its rectangular bounds.

There is one partially eligible track near the dark core: seed(3097,2139),
20.248native pixels away. Its eligible frames are18–21 and33–38, but it still
fails stable contraction. The other nine partly eligible tracks likewise fail
the frozen temporal conditions. No alternative radius minimum is promoted as
a nomination, and no source image is selected for a new repair.

## Scope and provenance

No additional source views were needed: there are no nominated source indices
to validate, and the retained near-target records already explain the relevant
refusals. This review does not reuse zero nominations as evidence of image
quality or safely functioning automatic correction; no image was changed.

Executed independent summarization command:
`python -X faulthandler experiments/source-concentration/summarize-failure.py --input experiments/source-concentration/failure-scan-1/receipt.json --output experiments/source-concentration/failure-review-1`.
It read the completed receipt only, verified all70 indices per track and retained
all124 seeds. `summary.json` binds the input and helper; its SHA256 is
`ca02e24e6cb4f3a10eb158571720b00bfc898c9e3990842a53a27187a1bd91c9`.
The complete table SHA256 is
`22422fbb9d3e33a08fc658d46e95525b7c08287fc55835b68be0d3fdff995509`.
No locator, threshold, source image, control or consumer was edited or rerun.

# Slide2 actual-source attribution — prepared before a candidate

Root executes `python -I -B -X faulthandler experiments/quality-september20/slide2-source.py`.
Default fresh output `slide2-source-1`; no overwrite. This author prepares only.
No RAW, replay, source verdict or image-quality verification is run by the author.
The prior completed baseline's existing PNG was read and cropped without resampling
solely to select these landmarks; its original TIFF is unchanged.

Use all299 DSC00001..DSC00299 originals and reference149/DSC00150.ARW. The frozen
map is7712a5eb7f74001485bc69b9d9721fe1bde4c0aa8099e28ddf703ede8069c14a.
Output6476x4316, crop quad[139,93,3238,2158], hence native sensor offset[278,186].
Every region is384native pixels square in cropped output coordinates:

| Name | x,y | Pre-source photographic target |
|---|---|---|
| medium-bars |2592,1584|Separated printed horizontal/vertical bars, small numerals and intersections|
| fine-bars |3576,1710|Small central line groups and slanted annotation endpoints|
| lettering |2772,2106|Letter strokes/holes in the lp/mm caption and nearby rule|
| pale-control |792,600|Pale low-detail field; not asserted to be a calibrated flat or temporal-noise reference|

These are selected from overview and native baseline crops before any candidate.
They are near the middle reference's printed plate in its previously inspected
embedded preview, not established best-focus source sites. A blurred source is
inconclusive; no automatic source search or parameter change follows in this task.

Reuse retained raw-affinity-support/build-1/cli-tests.exe,
SHA561adc89912d59966f60d9c77aba8633b456668dc1a71d338a1121309eabf3dc.
All137 recorded source hashes matched at preparation. Concurrent later CA edits
must not be mislabeled as this executable's source or spuriously require a rebuild:
run-time binding is the immutable executable, its historical source manifest and
build receipts. The matched-source hook is unchanged at093e25703bd86a303c95edbc557c253359365557d396364baa7dbdb9b6782111.
No affinity/local-placement/fine-support intervention is enabled. Invoke only
`merge_cmd::matched_source_tests::matched_source_actual_consumer`, not other tests.

The original TIFF description gives six-decimal tone(.005475,.476094,.55), not
the original automatic f32 bits. Therefore create a NEW explicit matched pair:
one observer-off and one observer-on complete render with this same pinned tone,
same executable, map, native GPU gather, seven-band consumer, gear-selected CA,
WB, matrix and developer. Require every RGB16 sample AND complete TIFF bytes
equal between this pair. Record differences from the retained automatic baseline
as provenance only, not a quality gain. Do not falsely assert historical identity.

The observer emits actual original149/gathered/merged CFA, actualMHCcameraRGB and
product-developed TIFFs. PAD4 yields392square; trim exactly4 to native384 PNGs,
retaining the full image's ICC. Raw is source-centred/even-rounded with no CA/warp;
only gathered and merged share exact reference coordinates. Compare them for a
specific missing printed separation/stroke. Brightness, edge colour or stipple
alone cannot establish true detail recovery or loss. No different LibRaw developer.

All four merged interiors must equal their independently addressed full-image
slices, including a second16pixel trim; x+2 wrong-location lookup must differ.
Previous printer observer-off/on/placebo evidence covers this same hook, while
this new pair supplies stack-specific output neutrality. Full master TIFFs and
native PNG/overview are retained and linked; an eventual gain requires whole images.

Each replay has900s wall/7200s CPU/12GiB committed and16MiB log bounds,8threads.
Metadata for all originals (hidden/system files included) must match the prior
full baseline before/after. Root already hashed all originals before/after that
baseline; no additional11GB content sweep is claimed here. Source/map/executable/
configuration manifests are bound and unchanged. Diagnostic rendering is small
postprocessing; no aligned frame volume or new algorithm is introduced.

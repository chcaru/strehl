# Complete chip decision: no meaningful photographic gain

MEASURED and independently VISUALLY REVIEWED. The complete 299-frame pair
finishes successfully, but neither root nor the independent reviewer identifies
a meaningful photographic improvement. Keep CA-before-MHC experimental/off.
Do not spend an optimization or parameter campaign on this fixed recipe.
Its generated reconstruction gains remain valid within their stated scope;
they did not earn promotion on this photograph.

The command actually run was:

```text
python -I -B -X faulthandler experiments/ca-before-mhc/full-run.py full --build experiments/ca-before-mhc/build-3-driver-fixed --screen experiments/ca-before-mhc/controls-2 --cost experiments/ca-before-mhc/cost-1 --out experiments/ca-before-mhc/full-1
python -I -B -X faulthandler experiments/ca-before-mhc/inspect-full.py
```

Source/runner checkpoint is commit `1b711cec`; the later inspection script adds
one region chosen independently from the baseline alone. Build-3 compiled fresh,
then its wrapper caught an in-flight Python display-driver edit. The retained
driver-only rebind proves every compiled source and executable byte unchanged;
it adds ICC preservation and fixes the master-path receipt. This history is
explicit, not a claim that the original build wrapper completed cleanly.

Admission was the original operator controls plus the separate eight-case live
colour qualification. All eight pass. The original 20-case screen reproduces
byte-for-byte and remains refused for weak baseline component recovery. See
qualification-results-review.md; none of those results is reclassified here.

Both arms consume every original in uncapped-IC-chip-cpl, with the same map,
anchor149 gauge, optical profile, seven-band merge, canonical four chunks,
development and fixed tone. Common crop is `[141,97,3234,2150]` quads, native
origin `(282,194)`, output 6468x4300. All 299 decoded active-u16 input hashes
agree between arms; each original source remains unchanged during its fold.
Original metadata and the selected source149 full-file binding remain unchanged.
Every consumed candidate site passes actual finite-coverage checks. Both outputs
retain the same ICC profile. This is a fresh common-context baseline, not a crop
of an older completed pyramid.

Current/Before job wall times were 118.906/202.141 seconds. Peak job committed
memory was 3,250,200,576/3,584,204,800 bytes. These are one ordered pair's observed
costs, not an alternating-sweep speed comparison; committed process memory is
not total GPU allocation. The predeclared job limits were respected.

Root inspected both complete fields and seven native pairs. The broad colour,
framing and visible structures are similar. The prominent central coloured
stipple, cyan/magenta rims, bright-contact bloom and rail contamination remain.
Some fine texture changes are visible, but no newly resolved opening or clearly
improved boundary is identified. The independent reviewer reaches the same
bounded no-gain decision and finds no obvious new structural regression. No
gradient-energy or image-difference score is used to turn change into quality.
See photographic-review.md. These observations do not prove that CA ordering is
irrelevant on every scene or that the fixed delivered-image profile is optical
truth; they reject this recipe as the next promoted chip improvement.

Current TIFF SHA256:
`c69db8e95e4f26df43632d453027770d1e52baae150ebe0e0916b47fd68f74b4`.
Before TIFF SHA256:
`916f9d79e37fbf9ed8440a07cbc68a754bde4b46d36d21bab2c724929873ebc5`.
RGB16 pixel hashes and source evidence are in full-1/completion.json and each
arm's output/receipt.json. Native review views are lossless slices of the
complete display images, checked on both sides of every pair.

Complete baseline:

![Current complete stack](C:/dev/blog/death-of-software/projects/strehl/experiments/ca-before-mhc/full-1/current-overview.png)

Complete candidate:

![Before complete stack](C:/dev/blog/death-of-software/projects/strehl/experiments/ca-before-mhc/full-1/before-overview.png)

[Baseline RGB16 master](C:/dev/blog/death-of-software/projects/strehl/experiments/ca-before-mhc/full-1/current/output/image.tiff)
and [candidate RGB16 master](C:/dev/blog/death-of-software/projects/strehl/experiments/ca-before-mhc/full-1/before/output/image.tiff).
Native whole-field PNGs are current-whole.png and before-whole.png alongside
the overviews. Both complete images and masters were shown to the owner.

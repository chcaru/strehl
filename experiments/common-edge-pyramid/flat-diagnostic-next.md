# Flat-slide attribution: concrete next action

SOURCE REVIEW / ARGUED recommendation, 2026-09-26. **Run one focused-original
nomination pass on slide2 next, using the existing locator and native patch
developer. Do not run another source149 comparison or infer geometry from the
overview.** This audit ran no RAW decode, image metric, fit, merge or build.

## Which photograph and which evidence

The latest complete slide2 pair found is
`experiments/quality-september20/slide2-source-1/{off,on}/output/replay.tiff`,
6476x4316, TIFF SHA256
`6d79e5996493afee9e3d7ba6edc6dc37c2d4983750efc0369ec880f810feb5ca`.
Both consume all299 `DSC00001.ARW` through `DSC00299.ARW` in
`D:/personal/macro/requests/misc-diagnostic/high-res-calibration-slide-2-cpl`.
Reference is149, native crop origin(278,186), seven AC levels. Its map is
`quality-september20/slide2-baseline-1/slide2.warpmap.txt`, SHA256
`7712a5eb7f74001485bc69b9d9721fe1bde4c0aa8099e28ddf703ede8069c14a`.
The older automatic master is `slide2-baseline-1/slide2.tiff`; it is a distinct
tone/binary reference, not byte-identical to the explicit pair.

`slide2-source-results.md` and the independent `slide2-source-review.md` establish
complete observer-off/on identity and exact crop addressing. They establish
neither a doubled-edge cause nor per-frame geometric accuracy: source149 is too
defocused at the medium/fine bars, and no resolved source149 feature was found
lost. The alignment's end-to-end/cycle diagnostics are not per-frame truth.
Root's newly observed broad ghosts around the QR/Siemens target motivate work;
this audit does not turn an overview observation into native causal evidence.

Do not confuse this with the **chip**, which has all299 source TIFFs under
`experiments/chip-competitor/run-1/developed/DSC00001.tiff` through
`DSC00299.tiff`, from `D:/personal/macro/requests/misc-diagnostic/uncapped-IC-chip-cpl`.
The latest rejected intercept pair is
`chip-focus-intercept/native-full-1/output/{baseline,candidate}.tiff`,6500x4332.
Its separate CA comparison uses6468x4300 and a different crop origin.
`chip-source-support/run-1/output` already retains mapped128px source strips:
contact sources136/143 and scratch sources206/213 carry recognizable detail.
The independent review reports apparent registered contour movement but cannot
separate geometry, defocus, demosaic, CA-off proxy and display effects. Do not
repeat that strip experiment or revive the failed Gaussian/intercept recipes.

Actual chip placement evidence exists elsewhere: the fixed green registrar on
sources146..153 measured source-native vertical corrections -3.4735..+3.6113px
in global reference149, with held guide-error ratios about.493..702. The actual
full299 seven-band local-placement comparison gave a modest independently seen
rail/crossing improvement. These measurements concern the chip rail patch,
not slide2 or its QR target. The later differential-blur discriminator failed
its pure-translation control before reading photographic arrays; it provides
no attribution. The star transfer remained photographically null even after
focused-source nomination.

## Cheapest executable nomination scope

The bounded path inventory found only source149's four raw/gathered TIFF patches
for slide2, plus the three-source orientation JPEG panel at
`quality-september14/orientation-1/high-res-calibration-slide-2-cpl.jpg`.
No complete per-source slide2 TIFF series was found in the relevant retained
outputs; its original directory contains299ARWs only. The chip exports cannot
be substituted. Thus another TIFF proxy scan cannot answer slide2's question.

Adapt `quality-september19/star-focus-locator.py` to slide2's bound map/inventory
and the **existing** medium-bars[2592,1584,384,384] and
fine-bars[3576,1710,384,384] output windows. One sequential299-original read
handles both windows; retain only each nominee's nine-neighbour original-u16
patches, never an aligned image volume. Reuse the unchanged G1 nomination score,
its noisy-flat failure demonstration, sigma2 smoothing of the scalar temporal
curve, and five spaced native nominees per retained neighbourhood. No new
calibrated sharpness score or focus-plane fit. Copy RAW patches before closing
RawPy and verify each nominated anchor against the existing independent decoder.
Reuse the actual observer's normalization/development golden before display.
Source149's retained patches provide an exact source-coordinate check. A score
peak is a nomination only; independent native inspection must identify an actual
bar separation or contour. No nominal middle-frame substitution.

The decoder, ordered-MHC/developer parity seam and rolling-patch implementation
already ran on star sand. Its259-frame pass cost133.438s historically; that is
context, not a promised slide runtime. A300s wall/2GiB bounded one-pass job is
a reasonable prospective allowance. The wrapper is currently hard-coded to
star geometry; it needs a small slide adapter, not an unchanged command rerun.
`slide2-source.py` also explicitly asserts every observed frame is149 and must
not be misrepresented as already accepting arbitrary nominees.

## The one downstream counterfactual

Once real focused landmarks are confirmed, test **original geometry versus one
fixed independently checked local correction, with the original canonical
per-source/per-band weights frozen**. Keep all299 originals, reference149,
seven bands, coefficient consumer, terminal policy, hull, crop and tone fixed.
Use disjoint portions of the resolved bars for the existing green translation
fit and held placement check; no bound/window sweep. Root/source author confirm
that the old `BandWorker` fields can feed corrected-coefficient `add_fields` in
one streamed pass, without an N-frame cache. That combination is a prospective
adapter, not an already commissioned frozen-weight experiment. The existing
`STREHL_LOCAL_PLACEMENT_FILE` full consumer is tested, but alone recomputes focus
weights and therefore is not this isolated comparison.

A complete matched full pair with a formerly doubled edge becoming one preserved
edge would establish that correcting geometry is sufficient at that site even
under unchanged source choices. If independently checked focused-source
positions agree yet the full merge still invents the second edge, investigate
merge mixing/support next. A failed fit or unchanged picture is inconclusive;
it cannot prove that all geometry is correct. Show both complete masters and
native<=400px controls for any benefit. Nomination is the next authorized useful
action; there is no fix claim or reason for another long calibration protocol.

Prior-art command run: `python -I -B experiments/ORCH-drift-check/prior_art.py
slide checker ghost alignment doubling`. Relevant SYNTHESIS facts18,1250,
1407-1410 were read. Old gradient-energy/edge-doubling explanations are not
slide evidence: fact1250 retracts a magnification-confounded visual premise,
and M97b's literal doubled-step control halves Tenengrad. V-DRIFT's planted
misregistration proves that detail metrics can be fooled, not that slide2's
current defect has that cause.

# Independent illuminant-aware color review

2026-09-25. **MEASURED comparison completed; no clearly useful photographic
gain from this fixed 3000 K arm.** Do not promote it as a quality improvement
or treat changed saturation as recovered color. Its arithmetic controls pass,
and the real metadata are available, but those are different questions.

I reviewed both complete overviews before all seven frozen native pairs
(fourteen unresampled 384-square PNGs). I also read the metadata and cached
receipts, the resolved development records, the control log and flat-propagation
record, and the complete view inventory. No new crop, RAW decode, render,
metric, parameter change or numerical experiment was made in this review.
Exact executed executable commands and process outcomes are retained in
`controls-1/process.json`, `metadata-1/process.json` and `cached-1/process.json`.
The complete cached writer job ran from `build-2/cli-tests.exe` with
`merge_cmd::illuminant_aware_color::cached_pair --exact --ignored --nocapture
--test-threads=1`, using its bound config. Its 3.750 seconds is an operational
cost, not a focus-stack speed benchmark.

## Photographic observations

The complete opal keeps its shape, broad cyan body, pink flashes and bright
reflection. The candidate shifts the blue/purple areas toward cyan without
revealing clearly additional gradation. The broad bright veil remains. The
complete marigold becomes somewhat warmer and more orange. Bright areas look
more yellow-orange, but the duplicated/soft hairs and petal-edge veils remain.
Neither complete view establishes a spatial repair.

| Frozen pair | Independent visual judgment |
| --- | --- |
| Opal reflection `[3628,1658,384,384]` | The slanted bright bands and small distinctions inside the reflection remain visible in both. No clearly new band, facet or useful highlight gradation appears. Cyan surroundings change slightly. |
| Opal colour-control `[2128,2228,384,384]` | Blue becomes more cyan; the pink/purple transition at the left looks slightly less distinct. Fine irregular texture, pale marks and the dark point remain. This is a hue/separation tradeoff, not an improvement established by greater saturation. |
| Marigold fan-core `[3230,3000,384,384]` | Warmer orange rendition; the same separated, doubled and soft hair traces remain. No recovered hair or better separation from the petal veil. |
| Marigold ring-upper-left `[3184,2954,384,384]` | The same hanging upper hairs, petal surface and fan overlap remain, with a warmer field. No useful new boundary detail. |
| Marigold ring-lower-right `[3276,3046,384,384]` | Existing overlap and blurred hair shapes persist; color change does not clarify the structure. |
| Marigold rim-hairs-control `[1436,1596,384,384]` | Bright peach-yellow surface becomes stronger yellow-orange. Hair shapes and fine surface texture remain, but I do not see newly distinct gradation. |
| Marigold inner-bud-control `[4320,1540,384,384]` | Slightly warmer bud and shadow, with the same small dimples/highlights and boundary. No useful structural change. |

I do not see an obvious new geometric fringe in these fixed views. That is a
limited visual observation, not a claim of unchanged chromatic error everywhere.
The targets contain real texture; none is a photographic flat-noise measurement.
Without a physical color reference, neither rendition can be declared more
color-accurate from these appearances.

## Receipt and interpretation checks

Both first-frame metadata captures admit exactly the exposed A and D65
calibrations, with the actual consumed WB, D65 selection and level bits matching
their complete caches. Both use warm fraction `0.9144210526315789` at the
declared 3000 K coordinate. That temperature is an experimental assumption from
the owner's setup, not a measured spectral or color-temperature calibration.
The reciprocal WB neutral is not a second independent neutral measurement.

The complete current writer and pinned rewrite pass RGB16/ICC identity against
the bound current masters at native sizes 6792x4528 (opal) and 6268x4176
(marigold). Both candidate records change only `matrix_bits` in resolved
development. Exposure, tone parameters, ceilings and sensor top are identical;
cache hashes remain held. The cached phase reads no originals. I identified
and reported the earlier runner's redundant original-file hashes before
execution; the executed route instead inherits its bound metadata artifacts.

Fixed parameters do not imply identical per-pixel downstream responses.
The sensor pin test and rolloff weight depend on unchanged inputs/ceilings,
but the rolloff's neutral luminance depends on the new matrix. Tone gain sees
new post-matrix luminance and gamut-map branches/blends can change. The rendered
difference therefore includes those existing responses to the matrix. It is
not a separately established highlight repair.

All four numerical controls pass. In their synthetic flat population the
candidate/baseline RGB variance ratios are 1.169059, 1.358060 and 1.858054,
matching independently predicted propagation to relative error below 6.4e-6.
These are variance ratios for that synthetic matrix/noise population, not
photographic noise factors, sigma ratios, or a quality pass. A color transform
can legitimately change covariance; neutral preservation alone is likewise
insufficient to establish color quality.

The candidate TIFF identities are:

- Opal: `17593d71f857f3915ca6df38b5a469ad6a675b7c3495e0195de1900b340a8071`.
- Marigold: `b867b3d66cc4b8d473b475933a8993391c0f1d7cebad36bf7db74e7dc1ce922c`.

The cached receipt SHA256 is
`017174bf369c29502daf28523459da0937375121801e344a4e10c29f85eb2e4a`.
Complete TIFF masters and full JPEGs remain in `cached-1/output` and `views-1`,
respectively. This fixed intervention does not meet the registered useful
color/gradation benefit. Close the arm without a temperature/saturation sweep
or a claim of glare recovery, spatial ghosting removal, or absolute accuracy.

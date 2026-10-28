# Complete flat60: reject the direct-pixel candidate

**VERIFIED visual observation:** the complete candidate has firmer apparent contours, but creates conspicuous colored contour bands, triangular shading and mottled interiors across the chart. It does not convincingly resolve the finest bars or lower radial convergence. This is an unsuccessful photographic trial, even on the near-planar diagnostic. Do not carry this exact recipe to weevil or promote it. The source-retention question remains useful; this result does not reject every direct or spatially coherent reconstruction method.

Both complete6932x4620 images were viewed first, then all eight frozen384x384 pairs with identical native origins. Complete B/C and source30 context were then revisited, followed by their existing native QR/star witnesses. No additional crop, export, fit, retone or metric was made for this photographic review.

| Complete output | Full JPEG | Full-resolution master | Linear master |
| --- | --- | --- | --- |
| Canonical | [Complete photograph](../../../outputs/raw-quality-2026-10-27/native-pixel-flat-views-1/baseline/complete-stack.jpg) | [RGB16](../../../outputs/raw-quality-2026-10-27/native-pixel-full-1/output/baseline-master.tiff) | [RGB32](../../../outputs/raw-quality-2026-10-27/native-pixel-full-1/output/baseline-linear.tiff) |
| Candidate | [Complete photograph](../../../outputs/raw-quality-2026-10-27/native-pixel-flat-views-1/candidate/complete-stack.jpg) | [RGB16](../../../outputs/raw-quality-2026-10-27/native-pixel-full-1/output/candidate-master.tiff) | [RGB32](../../../outputs/raw-quality-2026-10-27/native-pixel-full-1/output/candidate-linear.tiff) |

## All frozen native witnesses

Each listed origin is in the delivered6932x4620 master; all rectangles are384x384. Full views were1920x1280 orientation displays. Native observations below establish the defects.

| Witness / origin | Candidate versus canonical |
| --- | --- |
| Gray field,1460,400 | Broadly similar weak step and fine mottling. No major noise improvement or new calibrated noise claim. |
| QR boundary,4200,780 | Firmer-looking contours come with strong purple inset bands, triangular corner shading and irregular dark interiors. These are much more objectionable than the baseline's soft shoulders. |
| Central fine bars,2670,2020 | Existing groups persist, but no convincing new smallest-bar separation. Dark inter-group areas and broad white regions gain mottling/colored contours. |
| Central micro target,3850,2040 | Fine groups remain soft. New broad purple wedge-shaped shading appears between radial leader lines and around numerals. |
| Right bars,5700,1900 | Existing bars remain distinct; large letters and the white square acquire enclosing purple/dark rims and irregular interior marks. Apparent local contrast is not clean recovery. |
| Upper-right star,5260,20 | The same wedges persist with firmer boundaries, but pronounced triangular purple shading and colored crease-like marks appear inside previously smoother wedges. |
| Bottom radial center,1280,4236 | Outer spokes look somewhat firmer. The broad unresolved pale convergence disk and dark center remain; no extra center spokes are established. |
| Dot field,4600,3400 | Circle contours are somewhat firmer, but their interiors acquire irregular colored specks/patches and the surrounding field appears more structured. Existing bright speck remains. No temporal-noise attribution is made from this textured target. |

All exact pairs and their TIFF siblings are bound in the [display receipt](../../../outputs/raw-quality-2026-10-27/native-pixel-flat-views-1/display-receipt.json); representative severe failures are [candidate QR](../../../outputs/raw-quality-2026-10-27/native-pixel-flat-views-1/candidate/qr-block-boundary.png), [candidate micro target](../../../outputs/raw-quality-2026-10-27/native-pixel-flat-views-1/candidate/central-micro-target.png) and [candidate star](../../../outputs/raw-quality-2026-10-27/native-pixel-flat-views-1/candidate/upper-right-star.png). No witness was removed or moved after seeing results.

## Source and competitive context

The [complete B/C workflow comparison and masters](../../raw-quality-2026-10-26/flat-comparator/photographic-review/independent-results.md) remain relevant. B shows compact existing QR/dot/wedge contours with cleaner interiors than this candidate, although strong red/cyan fringes and unresolved fine groups remain. C has broad luminous shoulders of its own. Neither licenses the candidate's new colored interior structures.

The [retained source30 observation](../../raw-quality-2026-10-26/flat-comparator/source-support/results.md) also retains compact contours. Re-viewed source30 [QR](../../raw-quality-2026-10-26/flat-comparator/source-support/crops/source-030-qr-block-boundary.png) and [star](../../raw-quality-2026-10-26/flat-comparator/source-support/crops/source-030-upper-right-star.png) lack the candidate's prominent inset purple/triangular interior pattern. This supports the original source-retention question without asserting any single source as an optical or quality ceiling.

Source30 and vendor inputs are developed before fusion without CA warp; vendor geometry is independent. Native baseline/candidate both retain the same actual gather, profile, map, crop, WB and development. Thus native-pair changes follow this reconstruction intervention, but the source/vendor comparisons do not isolate placement, CA resampling or a particular physical source of every fringe. Native reference30 has active-origin offset(50,34); vendor/source full extents are7032x4688, with previously recorded mapped crop origins and unmeasured local scale differences.

## Execution and identity

**VERIFIED receipts:** all60 sources unchanged; canonical RGB16 and linear RGB32 pixels exactly reproduce the held baseline. RGB16 file hashes differ because file metadata differs, so this is explicitly pixel identity. Both arms use the same fixed held tone and ICC; display conversion is `(value+128)//257`, without sharpening. The [complete receipt](../../../outputs/raw-quality-2026-10-27/native-pixel-full-1/output/receipt.json), SHA256 `7a9b00c4d84040e04ca0da2808bb586a072b1d5ff0a40097f746dbac1983bb79`, binds complete sensor/RGB masters,60 frame/weight identities and input preservation. Candidate RGB16 SHA256 is `fe19bb94d7aecb6f2de4455a6cce520705102c4d01abff971245ba7896350a74`.

Root ran `outputs/raw-quality-2026-10-27/native-pixel-build-1/cli-tests.exe merge_cmd::native_pixel_fusion::full::flat60_complete_observation --ignored --exact --nocapture --test-threads=1`, executable SHA256 `2dad4b2ef2a6a5a03781f2fcfeccd2ef1cc42c1102002893ceafadcbf223b403`, with four workers and rounded GPU gather/probe. [Process receipt](../../../outputs/raw-quality-2026-10-27/native-pixel-full-1/process.json): exit0,57.016s,3,999,551,488-byte peak job commitment, terminal accounting and no cleanup error. This paired diagnostic cost is not a production speed ranking. The [generated far/coarse failure](independent-results.md) remains in force; the full flat result independently rejects photographic usefulness without needing a weevil run or parameter rescue.

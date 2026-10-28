# Flat60: support in fixed developed sources

**VERIFIED visual observation:** the clearer existing QR corners, dot contours and upper-star wedge boundaries seen in Helicon B are already present in developed source30. Source15 preserves their topology but is much softer. The central fine-bar witness does not support an additional smallest-bar resolution gain: neither nominee exposes a defensible separation missing from the two stack outputs. In fact, native and B clarify some bars beyond these two nominees. This is evidence for retaining available edge structure, not evidence that stacking always loses detail or that the capture has reached an optical ceiling.

All five complete source views were inspected first. [Nominees](nominees.json) then froze indices15 and30, before any native source crop was viewed. Source30 had coherent chart structure across the whole view;15 supplied an earlier-focus companion. There was no per-feature source maximum, score, subsequent frame search or relocation. Both fixed nominees were inspected at all four fixed witnesses alongside the existing native and B crops.

| Index / native-developed source | Complete source view,1617x1078 orientation only | Full-resolution RGB16,7032x4688 |
| --- | --- | --- |
|0 / DSC00016 | [Complete view](overviews/source-000.png) | [Master](../../../../outputs/raw-quality-2026-10-26/flat-1s-tiff-export/frames/DSC00016.tiff) |
|15 / DSC00031 | [Complete view](overviews/source-015.png) | [Master](../../../../outputs/raw-quality-2026-10-26/flat-1s-tiff-export/frames/DSC00031.tiff) |
|30 / DSC00046 | [Complete view](overviews/source-030.png) | [Master](../../../../outputs/raw-quality-2026-10-26/flat-1s-tiff-export/frames/DSC00046.tiff) |
|45 / DSC00061 | [Complete view](overviews/source-045.png) | [Master](../../../../outputs/raw-quality-2026-10-26/flat-1s-tiff-export/frames/DSC00061.tiff) |
|59 / DSC00075 | [Complete view](overviews/source-059.png) | [Master](../../../../outputs/raw-quality-2026-10-26/flat-1s-tiff-export/frames/DSC00075.tiff) |

The complete native/B/C photographs and their full-resolution masters remain in the [full-workflow review](../photographic-review/independent-results.md). No new stack or improvement is claimed here.

## Original-pixel observations

Every rectangle below is384x384. Source coordinates are active-pixel coordinates in that developed source, not vendor coordinates. PNGs retain original pixel spacing and ICC; exact RGB16 TIFF siblings accompany them.

| Fixed witness | Native baseline / source15 / source30 origins | Observation and source evidence |
| --- | --- | --- |
| QR block boundary |4200,780 /4255,806 /4250,814 | Source30 has compact square corners and the same open gaps, including the long lower boundary. These structures are also visible, softly, in15. B's clearer contour therefore has source support; no additional block or gap is established. Native is smoother and its edges softer here. [15](crops/source-015-qr-block-boundary.png), [30](crops/source-030-qr-block-boundary.png). |
| Central fine bars |2670,2020 /2718,2052 /2720,2054 | Source30 retains larger triplets and weak modulation in small groups;15 is softer. Native and B clarify several groups beyond these nominees, while the smallest patterns remain ambiguous. No source-only finer separation is established. Two selected frames cannot set a resolution ceiling for60 inputs. [15](crops/source-015-central-fine-bars.png), [30](crops/source-030-central-fine-bars.png). |
| Upper-right star |5260,20 /5319,42 /5310,54 | Source30 already has individually separated outer wedges and compact radial boundaries, with conspicuous red/cyan rims. Source15 strongly blurs them. Native has weaker fringes but softer boundaries; B retains clearer existing boundaries. The convergence remains mixed; no extra center spokes are established. [15](crops/source-015-upper-right-star.png), [30](crops/source-030-upper-right-star.png). |
| Dot field |4600,3400 /4657,3438 /4650,3434 | Source30 already has compact circular contours and the small bright inter-dot speck. Both persist softly in15. B's clearer contours have source support; colored rims are present in30 too. Native suppresses much of the fringe and fine texture while retaining the dots and speck. This is not a calibrated noise comparison. [15](crops/source-015-dot-field.png), [30](crops/source-030-dot-field.png). |

## Gauge, provenance and limits

**VERIFIED:** the frozen native map locates context only. Baseline reference30 uses active offset(50,34). For each native witness center, `q=C+a*(p-C)+2b`, with `C=(3516,2344)`, gives its source center. The source crop origin is rounded to an integer; no pixel is warped, rotated, rescaled or CA-corrected. Source15 scale is1.0047376971, rotation−0.0001972492rad and native translation(0.44027,−1.40476)px. Its largest coordinate-rounding error is0.44318px. Source30 is numerical identity with retained f64 gauge roundoff. These are map values and crop-rounding facts, not independently measured placement accuracy. Vendor geometry remains separately mapped in the prior review; local physical widths are not normalized.

The developed sources use native MHC, fixed first-source WB and the exact fixed native tone, without CA warp; they are not direct original-CFA observations. Native stacks RAW with CA on before development; B consumes those developed, CA-off sources. Their operation order differs. Source support cannot isolate fusion, geometry, CA resampling or rendering as the cause of edge differences, and the stronger colored fringes cannot be attributed solely to B.

**VERIFIED execution:** `python -B -X faulthandler experiments/raw-quality-2026-10-26/flat-comparator/source-support/run-bounded.py overviews` and the same command with `crops` exited0 with clean terminal accounting. Each job had60s/2GiB bounds and single-thread BLAS settings. Observed wrapper times/peak job memory were3.953s/314,286,080bytes and1.000s/45,838,336bytes. These are export receipts, not stacking performance results. No RAW file was opened and no fit or PSF inference was run.

The [overview receipt](overviews/receipt.json), SHA256 `65fceabe9dfaa94ab4999be9e4996f1b9f2623a17e3123fc89fe025a5c5ac0f4`, and [crop receipt](crops/receipt.json), SHA256 `1d77e56b47a93f426b639c26b7f6ab2f63b8f3c6a92a258a0612bd2969a33017`, bind commands, exporter, saved map, witnesses, source identities and pre/post source TIFF hashes/stat. All selected TIFFs stayed unchanged. Eight crop TIFFs were read back and checked against exact source subarrays; PNGs were checked against `(RGB16+128)//257`, with the original ICC retained. The original RAW identities are copied provenance from the completed60-frame export, not new decode checks.

**ARGUED next use:** this supports a full-photograph native trial that better retains already available edge structure while preserving the existing fine-bar separations and lower fringe burden. It does not justify indiscriminate high-frequency amplification, winner selection, an optical-limit conclusion or another source-search campaign. The bounded observation is closed without retuning or additional nominees.

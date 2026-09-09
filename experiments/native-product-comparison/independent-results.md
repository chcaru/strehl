# Independent review of the actual coffee-bean photographs

2026-09-09. **VERIFIED execution and viewing scope; qualitative observations, no SOTA or competitive ranking.** This reviewer inspected the runner and its explicit resource amendment before execution, then the saved process/output/viewing records, both complete overviews, and all four delivered 1:1 crop pairs. No product run, RAW decode, new image metric, competitor-source inspection or parameter change by this reviewer.

## Completed work and retained intervention

Both workflows consumed all 105 ordered coffee-bean captures (DSC00016 through DSC00120). Native consumed RAW directly with the held rounded experimental handoff, complete reference-52 map, crop coverage and photographic sRGB output. Its log confirms 105 placed, zero refused, all 105 folded, and a compact crop at plane origin (62,41). The fork consumed the corresponding existing Lightroom Linear Rec.2020 TIFFs, performed its own alignment, and explicitly selected NVIDIA GeForce RTX 5090 OpenCL. Source/executable identity and the distinction between native map reuse and fresh fork alignment remain binding.

| Observed process | Wall seconds | Owned job CPU seconds | Peak job commit bytes | Outcome |
| --- | ---: | ---: | ---: | --- |
| Native RAW workflow | 50.063 | 305.078125 | 2,838,089,728 | Complete, 6784x4524 RGB16 |
| First fork attempt, 16 GiB cap | 16.203 | 128.90625 | 17,750,953,984 | Our monitor terminated it; no comparator TIFF |
| Amended fork attempt, 40 GiB cap | 99.766 | 802.3125 | 25,536,389,120 | Complete, 7008x4672 RGB16 |

The first fork log was still making progress. Its receipt explicitly records attempted/successful termination for the committed-memory limit, not an engine crash. The declared one-time amendment retained its log and costs, checked 55,838,638,080 bytes available RAM, and ran only the fork in a fresh directory. I independently compared plans: all 210 RAW/TIFF metadata records and native/fork/map/DLL bindings match; the sole argv difference is the output path. Both completed jobs exit zero with no error or cleanup error, terminal accounting present, and no termination. The two fork attempts together consumed 115.969 wall seconds and 931.21875 owned CPU seconds; the failed attempt is not discarded from program cost.

These are observed workflow costs, not a speed ranking. Native excludes its historical map solve; fork includes alignment but excludes unknown Lightroom development time. There is one completed run per workflow, different input development, and an intervened failed attempt. The 331,289,798 retained primary TIFF bytes remain below the combined 512 MiB limit.

## Viewing and independent choice of diagnostic

The native TIFF embeds the stated sRGB ICC profile; the fork has no ICC profile but its executed command explicitly requests sRGB. Neither output reports a nondefault orientation. The viewing receipts apply rounded 16-bit/257 conversion to intended sRGB8, with Lanczos downsampling only for the labelled overviews. The four 512x512 crop pairs retain 1:1 pixel sampling and use separately chosen integer rectangles. Their shared landmarks are approximate, not registered pixels.

Native tone rendering is active: black 0.020049, white 1.165917, display contrast 0.550. Lightroom development and fork colour/contrast compensation differ. In the overviews the fork's paper highlights appear substantially brighter, while the native view shows more paper shading and fibres. This alone prevents treating less visible background structure in the fork as successful removal or better noise handling. It also prevents a brightness or contrast preference from becoming an algorithm-quality claim.

I independently requested the gray left-background pair after viewing the overviews, to challenge an interpretation based on the fork's near-white background. Its native crop shows a distinct elongated dark mark; the fork crop also contains faint, more diffuse marking. The observations establish a visible native symptom. They do not establish that the mark is absent from the capture, identify corresponding pixels in the fork, or show a competitive loss.

The other pairs do not provide a clearer competing structural defect:

- **Front texture:** both show irregular ridges and fine bright flecks, with pronounced brightness/contrast differences. Greater contrast can strengthen both real texture and artifacts; these crops do not select a winner.
- **Central crack:** common light fragments and occluding structures remain recognizable, but their offsets within the rectangles differ substantially. The pair cannot establish missing, doubled or displaced fine structure by coordinate comparison.
- **Outer edge:** both edges are soft. I do not see an unmistakable native-only doubled boundary or chromatic rim that would displace the background symptom as the next target.

The region choice is exploratory and adverse, not representative sampling or a quantitative quality score. No spatial standard deviation was substituted for temporal noise, and no sharpness statistic was used as evidence of quality.

## Decision and next discriminating work

**Investigate the visible native background strokes first. Their cause and competitive significance remain unproven.** No cleaner native structural failure emerged from these four pairs. Keep captured scene structure, sensor-fixed marks, and warp/fusion effects as competing explanations. Before reading source crops, freeze one visible stroke and a nearby clean low-detail control; inspect a small fixed series of original RAW crops and distinguish persistence in sensor coordinates from persistence in scene coordinates under the held map. The original-data observation can reject hypotheses that this photograph comparison cannot. A shifted-coordinate control needs a live unshifted correspondence witness so a null result is interpretable. This is a bounded diagnosis using the actual captures, not a reason to rerender both whole workflows or start another synthetic optimization sweep.

## Evidence bindings

Saved output bindings were audited as receipts; this review did not repeat large TIFF hashing or decoding. Native full-TIFF SHA256 `411f3bb79fcee3aecbf27899d036e785b92469e53b21b0b339e82d65cd5c6e87`, decoded pixels `e6c8d7ada22b7bd0f944bf8e554600d6c209f37e80dad1e35aa0968c5c8664cb`. Fork full-TIFF `137ab09a78af02594afe360b77a52fa2f1c3096bc5fb0a6ac16b50a667b019d4`, decoded pixels `edc93c718a9f323aa31e3f328f07e34edfba535d6bd5e34b6c6fb78b95cb31ca`.

- [Original plan and preserved attempt](run-1/plan.json); [native receipt](run-1/native-output.json); [failed fork process](run-1/fork-process.json).
- [Amended plan](fork-2/plan.json); [amendment receipt](fork-2/amendment.json); [completed fork receipt](fork-2/fork-output.json).
- [Native overview](run-1/native-overview.png), [fork overview](fork-2/fork-overview.png), [background](view-1/background.png), [front texture](view-1/front-texture.png), [central crack](view-1/central-crack.png), [outer edge](view-1/outer-edge.png).
- [Exact viewing rectangles](view-1/regions.json), independently hashed SHA256 `eeb69752325b175ea2006488c8125d48df61e8096312db57a3e6d0ba711d02cf`.

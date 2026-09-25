# Garnet numerical repair: independent photographic review

2026-09-25. Reviewer: pipeline_audit, who did not author the numerical fix or execute its RAW jobs. Inspected both complete1617px orientation views and both frozen384px native regions in `garnet-numeric-fix-views-1`. The source receipt binds the full6524×4348 RGB16 masters and common ICC.

**Visible result:** the two hard, axis-aligned magenta/cyan borders interrupting the white facet are gone. The surviving dark material now follows the surrounding curved and diagonal structure. This agrees with the independently localized band-2 negative-infinity footprint, rather than being a crop selected after finding a benefit. The broad white reflection remains severe. Neither that glare nor the general dense bright surface sparkle is repaired by this change. The complete image appears essentially unchanged at overview scale. The red protected region appears unchanged at native scale; quantitative RGB16 differences below show that it is not literally byte identical.

The correct scope is **repair of arithmetic-generated rectangular color artifacts**. This is not a glare fix, depth-boundary/occlusion-halo solution, or SOTA quality admission.

## Numerical attribution

Root's corrected183-frame run completes in114.266s and its census has finite values throughout. Its per-source gathered planes, guide, variance, band energy, noise floors and selection weights match the historical source evidence; canonical chunk plan and threads also match. The historical cache replays to the original full image exactly.

The old reconstruction had4,343 nonfinite CFA sites across four planes before hull. Of these,2,081 final cached samples change after repair; the others still legitimately land on the same lower source bound despite the now-finite internal reconstruction. The largest repaired value changes by14,862.7793DN. The15,858 changed samples outside the old nonfinite footprint differ by at most0.0000038146973DN; none exceeds0.001DN. These tiny changes are consistent with the anticipated subnormal-product rounding cost of the binary rescaling. Their count is not evidence of widespread image changes or improved detail.

The writer automatically derives tone from its merged input. An independent explicit-f32 reconstruction of its sampled-quad/color/tone arithmetic exactly reproduces the old writer's already-recorded tone bits. Applying it to the fixed cache gives:

| Anchor | Old | Corrected cache reconstruction |
| --- | ---: | ---: |
| Black | -0.0001595082285348326 | identical |
| White | 0.6156594157218933 | 0.6164247989654541 |
| Contrast | 0.550000011920929 | identical |

Old bits are `[3106357674,1058905051,1057803469]`; reconstructed new bits are `[3106357674,1058917892,1057803469]`. Only130 of144,926 sampled luminances change, but that changes the99.9th-percentile white anchor. The nominal placement-gain ratio is0.9987586722, about0.1241% lower. The new anchors are **cache-derived and baseline-bit-commissioned**, not a new direct writer-observer capture; the two actual writer logs independently agree at their printed precision.

This accounts for the broad small RGB changes:19,816,225 output pixels differ in at least one RGB16 channel, but the whole-image median absolute channel difference is1code and the99th percentile is27codes. In the frozen red control, mean code change is−8.43351 and every changed code is lower; in the separately chosen dark corner `[256,256,384,384]`, mean code change is−0.429337. No reduction in display noise or contrast caused by this tiny dimming earns quality credit. The white-facet changes include the actual repaired artifacts and cannot be summarized as a tone shift alone.

Command run, reading frozen caches/master outputs only and taking about1.4s:

```
python experiments/garnet-spatial-trace/analyze-fixed-garnet.py
```

Result: `experiments/garnet-spatial-trace/garnet-finite-and-tone-attribution.json`. It binds both caches by file hashes, verifies held metadata, reconstructs old tone bits against the actual prior observer, derives the new anchors without rounded-log guesses, and uses the complete old bad-site coordinates to distinguish repaired from already-finite regions. A repeat refuses to overwrite the existing result. Root attempted that repeat and retained the original successful artifact. No RAW was read and no image was edited by this analysis.

The remaining harsh white reflection is a separate priority. This successful arithmetic correction should be delivered and retained as a regression; it should not absorb the broader quality program or justify claiming the current stack satisfactory.

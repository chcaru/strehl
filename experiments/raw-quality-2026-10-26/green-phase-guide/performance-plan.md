# Exact probe-work omission, conditional on photographic value

**VERIFIED source audit / ARGUED next implementation.** No build, RAW read, numerical execution or change to the running candidate. If its complete photograph is not useful, do not optimize this research recipe merely because it is expensive.

The smallest follow-on is to reuse the existing **green-output-only GPU gather for the16 noise draws**, keeping the actual photographic gather unchanged. Current `full_gather` requests `warp_frame_fullres_into_planes::<false>` and four destination planes. `green_laplacians` consumes only G1/G2. `STREHL_PROBE_GATHER=green` in the current invocation affects the canonical probe; it does not override this explicit new full-RGB helper. The extra R/B destination work is therefore real in this recipe.

## Evidence and prior search

Actual source-only search commands from the repository root, each exit0:

```powershell
python -I -B scripts/research.py search --any 'green probe' 'GPU gather' 'probe reuse' --limit 6
python -I -B experiments/ORCH-drift-check/prior_art.py 'green probe reuse' 'GPU gather'
python -I -B experiments/ORCH-drift-check/prior_art.py green probe
```

The phrase-based mechanical search found no report match; the shorter search surfaced M194c probe-layout and V-GREEN. Actual retained sources/results read include [native-green-probe/results.md](../../native-green-probe/results.md), its [independent review](../../native-green-probe/independent-review.md), [native-gpu-gather/device-native-results.md](../../native-gpu-gather/device-native-results.md), [optimized-results.md](../../native-gpu-gather/optimized-results.md), and the existing GPU integration/library. Green-only output omission already preserved complete CPU photographs in its own allocation; Device256 later preserved complete CPU-reference outputs with actual green-only calls. Those historical speed percentages cannot be transferred to the present16-draw experiment. Earlier Parallel256 results also demonstrate that GPU dispatch alone did not guarantee elapsed-time improvement.

[Cost2 invocation](../../../outputs/raw-quality-2026-10-26/green-phase-cost-job-2/invocation.json) ran the frozen ignored source149 cost test with four threads, GPU `device`, rounded planes and CA-off. Its [saved receipt](../../../outputs/raw-quality-2026-10-26/green-phase-cost-job-2/output/cost.json) reports6.0348974 s for the16-draw probe interval,7.2307282 s guide/fold,0.6697248 s canonical fold and8.1515768 s processing. [Process accounting](../../../outputs/raw-quality-2026-10-26/green-phase-cost-job-2/process.json) reports15.031 s whole process and6,567,747,584 bytes peak job commit. These are one saved execution, not a benchmark of alternative implementations. The probe interval includes noisy-source construction, gathers, Laplacians and accumulation; it does not isolate shader time. The6.03 s must not be called pure GPU gather cost.

## One minimally scoped next patch

Add a probe-only helper returning two compact planes, with offsets `[(1,0),(0,1)]`, and call the existing `warp_frame_fullres_into_planes::<true>` using the same rounded mode, full geometry, crop and transform. Factor `green_laplacians` to accept two green slices; the signal path passes the current actual planes1/2, while the probe path supplies the two new outputs. Preserve the exact mean expression `0.5*(G1+G2)`, ordinary band operator,16 seeds, pair order and `NoiseEnergy` accumulation. Keep the frozen full-RGB helper as the explicit comparison arm; do not edit its archived source.

This uses the existing `gpu_rounded_planes::<true>` / `run::<true>` path. The current GPU library allocates one reconstructed full-resolution green plane instead of three RGB planes and skips R/B destination sampling. The CPU compact destination arrays fall from four to two. The present packed GPU output/readback remains full-sized, so this first patch must not promise halved transfer volume. Do not write a new shader, color sampler, geometry planner or covariance estimator for this step.

**All four original CFA channels remain load-bearing.** Full source noise generation, WB, black/white values, original active origin/stride and complete u16 upload remain unchanged. Green MHC at non-green locations depends on source R/B values. Removing source R/B, generating only green noise, warping separate approximate green grids, or reusing the same noise realization across draws would change the estimator. Do not replace16 draws with fewer draws or a deterministic variance approximation under an optimization label.

The exact commissioning seam is already present: compare all16 consumed G1/G2 arrays, their six fine-band variance arrays, matched/candidate field hashes and collapsed outputs against the frozen full-RGB path. Reuse the existing generated screen and one source149 full-size cost fixture; preserve the R/B-only impulse coupling destroyer from native-green-probe. Require complete three-arm CFA/RGB16/linear identity on the bounded source fixture. Only then time both orders with the same held original/map and actual route markers. Independent review must challenge stale output and omitted source-R/B dependencies. A new synthetic quality campaign is unnecessary for an exact work-omission patch.

## Other repeated work, subsequent only if needed

| Current work | Semantics-preserving opportunity | Boundary |
| --- | --- | --- |
| Fresh `WarpScratch`, compact output vectors and cloned buffers for every draw | Reuse one probe scratch/output allocation across the16 draws; keep active writes and all read-before-write rules identical. | Scratch is about9 bytes per full quad in its current definition; output and clone costs are separate. Current GPU context already persists through a mutex, so do not claim repeated context creation. |
| `noisy_source` validates the same variance array and computes its square root on every draw | Prevalidate once and retain f32 sigma for that original, while keeping the same RNG stream, expression order, rounding and u16 refusal. | Preserve exact source codes; do not change normal generation, source identity or padding behavior. This is a separate patch after the two-output route. |
| `GpuGather::run_inner` allocates source/RGB/descriptor/output/staging buffers per call | A source-scoped reusable device workspace can retain capacities and immutable geometry parameters. | Source pixel uploads cannot be reused: every noisy draw is different. Device256 is already enabled; moving coordinate construction to GPU is already done. Buffer reuse must retain explicit coverage initialization and avoid stale rows/tails. |
| Fine-band CPU pyramids and pair-difference accumulation after every readback | Later GPU resident green-band/probe accumulation could reduce readbacks. | Higher scope: exact smooth/reduce/expand tap and f32 order, pair summation order, rounding and kernel boundaries need explicit equivalence. Do not fuse/reassociate reductions or replace mean-G Laplacians by averaged phase Laplacians merely because they agree algebraically. |

Caching whole coordinate fields for all16 draws would consume substantial extra memory; the current Device256 strip planner already avoids host-coordinate uploads. Reusing fixed small parameters or scratch is preferable before adding a retained full-field cache. Removing the matched-mean full arm would reduce research overhead but would also remove the complete photographic estimator-control comparison; that is not an exact acceleration of the present three-arm experiment.

**Recommendation:** if the complete image earns retention, implement only the existing green-output gather dispatch first, with exact preservation and same-executable RGB reversion. There is no measured speedup for this proposed patch, and no change is authorized to the presently running full photograph.

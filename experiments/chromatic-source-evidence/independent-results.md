# Independent interpretation of chromatic evidence

2026-09-25. **MEASURED: reject this operator's route to full photographs.** The generated screen completed; the candidate did not qualify. It sacrifices a genuine focused neutral highlight to chromatic source evidence, while failing the intended spill-improvement test. No RAW render, threshold relaxation or new stimulus search is warranted for this recipe.

## Executed evidence

Root's fresh `build-1/cli-tests.exe` ran filter `merge_cmd::chromatic_source_evidence::independent_controls:: --nocapture --test-threads=1`. `controls-1/process.json` records exit 0 and 16.75 s wall time; the log records all four tests passed and eight image cases completed. `controls-1/completion.json` verifies unchanged source bindings. Screen SHA256: `d6a19bb6230a13f2bab0aa1a4a8191d92634ae537a6111ae9f3e3765049d3e32`.

These are distinct outcomes: `mechanical_pass=true`, `quality_pass=false`, `positive_exercised=false`, `wrong_source_destroyer_exercised=true`, `candidate_qualified=false`, and `photographic_replay_admitted=false`. Successful test execution is not quality acceptance.

The source controls establish co-site projection, common-mode cancellation, paired covariance handling, normalization, literal local zeros, natural zero-union fallback and finest-band preservation. Actual image comparisons retain injected noise, u16 rounding, gathered CFA samples and source hashes; each source's sixteen probe draws are checked against the actual gather. Forced Off and NoChroma image arms are exact. The separate pure union control, rather than NoChroma's explicit bypass, exercises natural fallback. None of this independently calibrates the shared noise model.

## Photographic falsifiers

Ratios below are candidate error divided by baseline error in the frozen native windows. Lower error alone can reward erased detail; the independent bounded template-retention guard is therefore also required.

| Case / window | RGB error | Green error | Chroma error | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Flat, ISO100 | 1.01219 | 1.00076 | 1.03529 | Inside the fixed 5% damage bar, not a noise improvement. |
| Flat, ISO400 | 1.01260 | 1.00144 | 1.03597 | Same limited result. |
| Veil outside, ISO100 | 1.03879 | 1.04406 | 1.00340 | Positive stimulus exercised, but neither required 5% RGB nor chroma improvement occurs. |
| Veil outside, ISO400 | 1.02790 | 1.03471 | 0.98143 | Does not meet the improvement bar; the intended positive is also unexercised. |
| Genuine unclipped highlight core, ISO100 | 1.50691 | 2.32121 | 0.56928 | Severe loss of real focused structure despite lower chroma error. |
| Genuine unclipped highlight core, ISO400 | 1.50490 | 2.28305 | 0.57662 | The same structural failure at the second noise level. |
| Clipped neutral glint, outside core, ISO100 | 0.73954 | 0.75028 | 1.04174 | RGB/green error improve, but all three texture components fall below the 98% retention requirement. |

The unclipped core `[112,110,133,132]` was added before any build or measurement to protect the genuine focused neutral highlight already present in the frozen scene. It changes neither the scene nor the operator or error bars. The baseline's core template recovery is live: `[0.88867,1.01237,0.95646]` at ISO100. The candidate falls to `[0.66816,0.67145,0.65938]`; ISO400 is similar. The improved chroma-error number is therefore precisely the wrong standalone conclusion: removing real neutral structure can make a colour-error measure look better. The candidate cannot be called a glare fix.

For ISO100 the outside-window baseline RGB error 0.006633 exceeds twice flat error 0.001127, and its positive signed RGB bias 0.001655 exceeds that flat error; the intended stimulus is active. At ISO400 the signed bias 0.001626 is below flat error 0.002257, so that positive cannot qualify. This limitation does not excuse the separately exercised core damage or the ISO100 failure. No stronger glare or lower noise is substituted after seeing the result.

The clipped neutral scene exercises actual pre-WB active-u16 clipping, with R/G1/G2/B pinned counts `[3,6,6,0]`. Outside its irrecoverable core, template recovery falls from `[0.93512,0.93140,0.94471]` to `[0.88719,0.89478,0.90272]`. That is real texture damage in this constructed case, even though RGB error falls. It is not evidence that the user's mineral captures clip, and the irrecoverable core was not scored as recoverable truth.

Neutral fine structure, crossed thin depths, genuine coloured rays and adjacent texture pass the fixed damage/retention bars. The rays show RGB error 0.95493x; this single protected case does not offset the failed mandatory cases. The deliberately wrong source damages adjacent texture (RGB error 0.017468 versus baseline 0.004459, recovery about 0.47–0.52), so that protection has power to reject.

## Scope and next decision

Even the N=5 flat cases admit chromatic evidence at 571 and 634 coarse-band sites, respectively, and change 777 and 850 source weights. Noise and CFA/interpolation colour differences are not evidence of genuine chromatic subject structure merely because a source passes this union. The neutral-detail scene also has nonzero admission. These small-stack results do not qualify an any-source union on hundreds of frames; the preregistered deep-source-count concern remains. It need not be investigated to reject the present failed recipe.

The result rejects unconditional chromatic replacement of coarse-band source evidence. It does not establish that RAW colour information is useless, identify the cause of actual mineral glare, or license clipping/source selection changes on photographs. Preserve the explicit generated refusal and move to a materially different intervention rather than tune this failed screen.

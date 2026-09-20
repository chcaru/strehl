# Independent supplementary qualification and cost review

VERIFIED from root's retained executions, without another build, GPU call or RAW read. The separate eight-case qualification passes and supports the already scoped complete photographic comparison. It does not turn the original screen into a pass: `controls-2/output/screen.json` and `screen-1/output/screen.json` have identical SHA256 `769305780eb7e9611776171413684e2eedcecdbf52894e568fba2d2d2435018c`, including `photographic_replay_admitted=false`. That original high-frequency qualification remains inadequate because its baseline R/B components did not reach the frozen 0.5 liveness bar.

The new carriers are exactly (0.09, 0.07, 0.10) cycles/native pixel, with the same phases, amplitudes, noise, transforms and focus-width function. All eight individual cases pass the unchanged 0.5 liveness, 0.98 truth-capped retention and 1.05 RGB/chroma error guards. Ratios below are Before/current; smaller error is better.

| Scene | ISO | Transform/crop phase | RGB error ratio | Chroma error ratio |
| --- | --- | --- | --- | --- |
| Fine colour | 100 | Identity | 0.68614 | 0.60110 |
| Varying focus | 100 | Identity | 0.71817 | 0.68940 |
| Fine colour | 100 | Fractional/shifted | 0.85333 | 0.85856 |
| Varying focus | 100 | Fractional/shifted | 0.85320 | 0.86839 |
| Fine colour | 400 | Identity | 0.69075 | 0.60477 |
| Varying focus | 400 | Identity | 0.72295 | 0.69242 |
| Fine colour | 400 | Fractional/shifted | 0.85224 | 0.85767 |
| Varying focus | 400 | Fractional/shifted | 0.85357 | 0.86838 |

Re-choosing the interpretation around actual signal retention, rather than the admission boolean: current R/G/B in-phase amplitudes span 0.75579–0.82538 / 0.93162–0.98259 / 0.78817–0.86001. Before raises R by 6.05–13.50% and B by 0.97–4.30%; G changes by −0.2040% to +0.0081%. This is a live retention test, not the original weak-baseline test repeated. No channel exceeds truth amplitude; Before still attenuates some genuine components (minimum R 0.83042, B 0.80655), so the result is improved reconstruction within this scope, not full recovery.

Both independent error measures also improve: RGB error falls 14.64–31.39%, and R−G/B−G error falls 13.16–39.89%. Error RMS can reward smoothing when noise dominates; in-phase projection can miss unrelated errors and overcontrast. The retained half-detail, desaturation and extra-blur controls close those particular shortcuts here: half-detail recovers approximately 0.5, desaturation approximately 0.333, and the added binomial blur recovers only (0.85125, 0.90709, 0.81941), all rejected by the unchanged retention guard. The overcontrast control checks truth-capped retention rather than demanding preservation of manufactured contrast. The finest band is actively selecting in the varying-focus cases (`averaged_fraction[0]=0`), rather than returning an unchanged all-frame mean.

The fractional cases show smaller gains than identity and deserve equal weight. Staged-after is exactly current in identity, where its common second pull samples integer sites; that coincidence is expected. In fractional fine-colour cases it slightly worsens RGB/chroma (roughly 1.005–1.011 times current), while Before improves both. Fractional varying-focus staged-after has only a small improvement (roughly 0.996–0.999). This argues against explaining the Before gain simply by adding a second RGB resampling. It is not a blur-matched proof: original same-colour CFA and RGB lattices have different interpolation support. The source/profile plant also validates an operator under supplied CA/noise, not optical or noise calibration.

All three tests passed in root's `controls-2/process.log` (5.703 s process wall, 5.39 s test harness). The complete original screen's unchanged receipt retains zero-CA exactness, actual-probe transfer changes, source immutability and staged-after green/probe identity. The supplement records original source hashes and finite actual per-arm beta values; it does not replace the injected noise model. Qualification JSON SHA256: `7d4ce77c2740d6a2d348bed2de6c6a0c917d54ad2ad599a778b9aca68512a512`.

The single-source cost run also clears its fixed feasibility bar. Both arms consume source149, crop [141,97,3234,2150], native output 6468×4300, the same original active-u16 hash, map, tone/WB bits and canonical chunk plan. Before changes R/B known-site hashes while G1/G2, guide, variance and beta stay exact at this reference/identity common transform. Thus the cost arm is live; unchanged green/probe at this one transform is not proof that they remain unchanged throughout a transformed stack. Original metadata and source bindings are reported unchanged.

Current/Before source-phase times are 1.10575/1.62458 s; the frozen estimate `299*source_phase + finish + 120` gives 451.12/606.24 s, below 1500 s. Process wall is 2.640/2.390 s, CPU 4.656/6.125 s, and peak job committed memory is 2,720,473,088/3,058,991,104 bytes. These are one-source feasibility observations, not a speed comparison: differing setup/write costs already reverse the total-wall ordering. They neither establish complete-stack peak memory nor replace actual full-run limits and coverage checks. Cost receipt hashes are current `b1f9933b32671a1088de74aa08a7e4ba01ca052043e07e75137f6452f77b9558` and Before `bf1e57fc043992f1b78c02cd3e0d116ffc77fe486ac94fc11730b2b8404c71d4`.

Build provenance is explicit: build-3 compiled successfully, then its wrapper caught a Python driver edit. `build-3-driver-fixed/driver-binding.json` retains that event and binds the corrected ICC/view driver; it records all compiled source and executable bytes unchanged. This is a driver-only rebinding, not a claim that the original wrapper completed cleanly. No photographic quality result is included in this review; the complete pair must decide whether the synthetic colour gain transfers without losing real detail or manufacturing colour.

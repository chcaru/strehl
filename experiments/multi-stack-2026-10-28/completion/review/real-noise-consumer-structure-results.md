# Structure observer: commissioned controls and real Q/V census

MEASURED / VERIFIED research checkpoint. This does not establish real RGB noise gain or photographic improvement. The earlier real chart23R/B repeatability result and the complete insect flat-gate negative remain unchanged. No new real R, W or M signal was read.

## Fixed roles and scope

Use the six299-frame insect windows with bases36,76,116,156,196,236 and the same nine previously frozen128quad witnesses. Within each pass/window Q=[0,4,8], V=[1,5,9], R=[-2,2,6,10], W=[-1,11], M=[3,7]. The roles are globally disjoint. Q fits a fixed quadratic with zero residual degrees of freedom; only V challenges its prediction. R fits a separate fixed quadratic with one residual degree of freedom. Neither count provides a calibrated model-error bound.

`real-noise-consumer-structure-model.rs` streams three derived coefficient fields, exact original-tap squared norms, and three withheld residual fields. It retains full3×3 temporal covariance induced by shared Q predictions. The covariance uses a Q-only, locally constant expected-signal plug-in; this is explicitly an approximation, including same-photon denominator dependence. It never estimates a new camera law from observed residuals. The fixed gate is mean whitened energy/3 <=1.35 with complete support on each32×32 CFA block. This is a commissioned consistency gate, not a chi-square probability: spatial samples share interpolation support. No iid-pixel confidence interval is reported.

The synthetic operator uses original u16 CFA, the measured curved placements, exact applied optics, gain for signal and gain² for variance, then the production RegionSampler. Color texture contains independent two-dimensional components up to1.11radians/quad, materially above the earlier low-frequency sinusoid. The source is streamed, not an aligned-frame volume. Quantization is actually executed; covariance retains the existing camera model without fitting a correction to the probes.

## Operator and qualification controls

`rn-sw-tests-run-02` passed5/5: independent public-sampler impulse tap norms; actual RegionSampler impulses with scale, rotation and distinct CFA sites; negative-weight original clipped-tap refusal through the Gate call path; correlated covariance direction; zero/near-singular covariance refusal. `rn-sr-tests-run-03` passed7/7 after adding exact independent-R quadratic weights and the actual blur wrapper's flat/2-D impulse checks.

Flat-first `rn-sw-flat-01`, then full `rn-sw-all-01`, used seeds64..67, windows36/236, both real pass geometries,1200DN and200DN levels. Each level has576 component-block observations; these are correlated within acquisitions and not576 independent repetitions.

| Signal |1200DN accepted/576|200DN accepted/576|Mean energy1200/200|
|---|---:|---:|---:|
|Flat|576|576|1.00049 /1.00320|
|Colored quadratic evolution|576|576|1.00079 /1.00348|
|Cubic mismatch|0|576|1.57761 /1.09787|
|Nonquadratic focus envelope|0|576|1.86707 /1.14512|
|Temporal amplitude step|0|0|4.84090 /1.63500|
|1.5quad horizontal,0.9quad vertical shift|0|0|5.30621 /1.71215|
|Clipped originals|0|0|No complete support|

The low-DN cubic/focus false acceptances are a material power limitation. The cutoff was not changed. Passing the gate cannot certify stationary signal, correct temporal interpolation, or unbiased target prediction.

## Independent-R actual-core controls

`real-noise-consumer-structure-consumer.rs` copies the already exercised four-arm core invocation: individualpass0, individualpass1, equal Repeat and precision Repeat with EqualObservation focus reference. W is disjoint from Q/V/R/M and is fixed for both measurement states. R is never used to choose weights or masks. Every Q/V-qualified component pixel is scored in every arm, including delivered fallback; an invalid delivered pixel fails the run rather than being dropped. All arms at a state use the same R realization.

The two pass targets are identical by construction in these synthetic controls. The reference averages separate per-pass R predictions for that reason only. This assumption has **not** been established for real insect passes.

Corrected flat-first `rn-sr-flat-02`, then `rn-sr-all-02`, use seeds80/81 and windows36/236: four synthetic acquisition units per exposure/level/mode, with two correlated M states3/7 and four correlated output components. Both gain1/1 Repeat and a declared synthetic gain2.5335414/1 HDR arm are tested. This is not a new real HDR measurement. Build `rn-sr-b03` executable SHA256 `ed12b1d67d1f579cf881c179e207fb3749f382b13a41219855d606867e434f50`; exact actual product16 library hashes are in its build receipt. Full run exited0 in21.25s with34.6MB sampled private memory,4workers,0cache reads and0RAW decodes. Timings were concurrent and are not performance claims.

|Quadratic textured arm|Independent-R risk delta vs equal|Known-truth risk delta|Known signal projection|
|---|---:|---:|---:|
|Repeat precision,1200DN|-0.002|-0.002|0.99069|
|Synthetic HDR precision,1200DN|-33.859|-33.969|0.99053|
|Synthetic HDR precision,200DN|-221.130|-221.696|0.98956|
|Synthetic HDR strong blur,200DN|-415.639|-380.674|0.72632|
|Synthetic HDR mild blur,200DN|-385.250|-380.486|0.95007|
|Synthetic HDR shifted output,200DN|1894.717|1895.631|0.81375|
|Synthetic HDR constant output,200DN|4920.148|5015.066|0|

Risk alone does not establish structure retention: strong blur can reduce both true MSE and independent-R risk while removing about27% of the planted high-frequency response. The separate fixed0.95..1.05 projection diagnostic rejects strong blur, constant and shifted outputs; mild blur lies near its declared tolerance boundary. Precision retains approximately0.989..0.991. No amplitude or fitted mean correction was used to rescue these transfer measures. On a truly flat signal, constant/blurred outputs correctly have lower risk; that is why the textured controls are required.

Known cubic mismatch at200DN remains Q/V-admitted. It produces substantial reference error and biases the risk difference: e.g. synthetic-HDR strong-blur independent risk+258.06 versus known-truth-259.92. This false-negative demonstrates that independent photons alone do not remove reference-model bias. Small sign changes near zero are also visible in flat shifted controls. Full acquisition-unit rows and ranges are preserved in `real-noise-consumer-structure-risk-summary-02.json`; aggregate agreement is not per-pixel risk calibration.

The first risk replay (`rn-sr-all-01`) is invalid and retained as failed harness evidence. A new smoothing wrapper passed box_mean's scratch and destination in reverse, producing horizontal sums instead of means and scaling W. Impossible flat/foil values exposed it before any real R/M read. `rn-sr-b02/sources` preserves that source. The corrected wrapper is explicitly tested on constant fields and2-D impulses. Earlier paired chart code called box_mean correctly and is unaffected.

## Real Q/V-only census

Root authorized only Q/V reads after the preceding control checkpoint. `rn-sc-01` retains all nine witness regions, six windows, four CFA components and both passes, using the independently audited historical cache reader. Protocol and exact168 role/source identities were written before reading signals. The72 loaded Q/V IDs are disjoint from all96 R/W/M IDs. Historical acceptance verifies the exact audited decoder/lock equivalence, immutable source identity/stamps, cache envelope and complete header/payload digest; no relabel, cache write or decoder fallback occurs. Original freshness here remains stamp-based, not a new full RAW rehash.

`rn-sc-run-01` exited0:7.16s concurrent,204.8MB sampled private memory,4worker ceiling,72cache hits,0RAW. Exact executable SHA256 `05b9a0b329e096b042d355174392b9db6fa3c5a01b3cdea9ba4db6626b564b3c`. Current optics match the frozen capture calibration exactly. Source/library postchecks and role-disjoint proof are in `real-noise-consumer-structure-census-summary-01.json`.

|Base|R|G1|B|G2|All four/81 blocks|
|---|---:|---:|---:|---:|---:|
|36|81|78|79|81|78|
|76|72|61|64|60|60|
|116|79|62|71|67|62|
|156|70|65|72|64|63|
|196|80|79|81|80|78|
|236|81|81|81|81|81|
|Total/486|463|426|448|433|422|

This is predictable local temporal evolution, not unchanged appearance. Q-only predicted block means expose a second limitation before risk reads: median maximum cross-pass gaps at the two M states are R20.9,G152.1,B30.2,G253.2DN, while median predicted signal levels are approximately80,177,92,185DN. P95 gaps are105,247,90,246DN. Same ordinal across independently captured passes does not establish the same focus state or latent image. No new compatibility cutoff was fitted and no supported mask was pruned using these numbers.

Consequently an averaged real-R target cannot silently stand for common truth. Any real replay must first distinguish per-pass target risk/appearance tradeoff from noise reduction, or use an independently commissioned focus-correspondence choice. Existing geometry and gains were fitted earlier using shared data, so even disjoint current roles yield conditional, approximately unbiased risk only under the frozen-model assumptions. Real R/M replay remains pending independent review and root scheduling.

## Reproduction and next boundary

All commands actually run, source/library hashes, environment and resource samples are in the named `outputs/multi-stack/completion/*-run-*` and build receipt directories. The command driver is `experiments/multi-stack-2026-10-28/run-command.py`; standalone links use `completion/sr/build-roi.py` with the actual product16 fingerprint. Do not label the reused fingerprint63ce8e1d9f947ed6 as product14: release builds overwrite that path, and the content hashes bind this work.

The analysis command is `python experiments/multi-stack-2026-10-28/completion/review/real-noise-consumer-structure-risk-analysis.py outputs/multi-stack/completion/rn-sr-all-02 experiments/multi-stack-2026-10-28/completion/review/real-noise-consumer-structure-risk-summary-02.json`. Its fixed transfer criterion was written before nonflat results were opened and retained unchanged after the wrapper repair. No product engine/UI change is made by this observer checkpoint, and P1/H2 are not closed as real RGB/noise gain.

## Independent review corrections and latest bound controls

The independent review found that the new synthetic W-guide path had propagated only center support through its17×17 filter. This boundary issue is repaired in the research harness: gather a144quad original region with an8quad halo, keep the same absolute signal origin, propagate every filter dependency with complete_support, filter, then crop the128quad guide. A center-valid but halo-invalid poison is refused. With an entirely missing guide, the actual precision consumer's output arrays match equal Repeat bit for bit. `rn-sr-tests-run-04` passes9/9; `rn-sr-flat-03` then `rn-sr-all-03` bind the corrected source. Executable SHA256 `0b1e56b2983dd6787b5d6601b0eb61661d37af70e419707d862cda74e630eb0a`. The full corrected control run exited0 in18.20s with34.9MB sampled private memory. Its complete numerical rows and component/state ranges are in `real-noise-consumer-structure-risk-summary-03.json`. Earlier all-valid controls are not claimed to have identical whole arrays after changing the cropped guide's edge extension. Q/V-only results never use W and are unaffected.

The next controls use exact nominated asymmetric bases106/97 and separate R trajectories for each pass. `real-noise-consumer-structure-risk-paired.rs` includes common quadratic signals, unequal quadratic signals, equal-mean opposite texture,0.85relative temporal focus slope, pass-label permutation and blue-only output blur. Seeds90/91, both exposure arms and200DN were fixed before the run. Four core output arms are exercised; optional-primary engine overrides are **not** exercised. Fields therefore say `vs_target_single_pass`, and each target's own single-pass output is its comparison baseline. Every component/state row and all core averaging/fallback counters are retained.

`rn-sp-flat-02` then `rn-sp-all-02` exit0; full run7.11s concurrent,40.9MB sampled private memory. Build `rn-sp-b02`, executable SHA256 `8ef601879fdee9ee944ec623a2a3e60002dd842ce357e73e9d29b64322998cf7`. Numeric rows are exactly equal to the earlier control01 after renaming the misleading primary label; diagnostics were additive. Pass permutation changes precision output by at most0.0004883DN, below the predeclared0.005DN limit. Exact source snapshots and linked-library digests are retained.

The controls demonstrate why separate targets matter. Equal-mean opposite texture has almost zero common projection after equal merging, but both own-pass targets show excess independent-R risk of about+5775/+6134DN² (known truth+5822/+6197). In the unequal HDR case, precision improves target0 but harms target1: the latter's independent risk rises+497DN² versus+490known truth. These are appearance tradeoffs, not a single common-noise result. A blue-only blur leaves other components near0.99projection but drops B to about0.721; all component/state ranges remain visible. The opposite-texture Repeat control invokes46738 precision coefficients and40558 ordinary fallback coefficients across the recorded whole-pyramid runs, so observed behavior is not attributed solely to successful averaging. No row or spatial mask is selected using these output diagnostics.

## Independently nominated matched-focus real negative

The original same-ordinal design was not a physical-focus identity claim. A read-only audit of118 saved scale-proposed pairs finds ordinal offsets ranging-12..+3, median-8. The sealed local focus evidence is stronger but spatially limited: ROI0 previously nominated centers110/101, while another ROI has different candidates. A descriptive fit over537 jointly qualified ROI0 quad sites gives slope0.920, residual0.694ordinal, and median width ratio0.900 with p10–90range0.563–1.488. These are not calibrated focus-step units and were not used to fit a new transfer mapping.

A separate protocol froze ROI0 centers110/101, bases106/97, and exact Q/V/R/W/M IDs before new reads. Domainquad969,1029,128,128 has nine32quad scored blocks that exactly tile the old sealed sensor rectangle1970,2090,192,192. No center or witness was chosen from new risk or candidate output. Earlier focus/geometry work saw some acquisitions, so current roles are disjoint, not globally unseen photons.

Root authorized only twelve Q/V reads. `rn-sm-01`/`rn-sm-run-01` completes with12validated historical-cache hits,0RAW,0R/W/M. The short run completed between resource samples; its sampled1.5MB value does **not** estimate actual peak memory. The128MiB cache and bounded observer workspace remain below the configured2GiB ceiling. Build `rn-sm-b02` executable SHA256 `1bd459dd2cc33b52c5e971eba3f3c989bdb43a2e995acbdf0351c3dfea718c8a`.

Joint support is5R,0G1,1B,0G2 of9blocks: **zero all-CFA blocks**. Green median whitened energies are approximately2.26/4.42 across passes, versus the unchanged1.35 cutoff. Q-only per-site prediction RMS differences reach190–591DN for green, with systematic signed block means approximately-135..-329DN. The per-site differences, signs and both passes' diagnostics are retained; no mean-only compatibility gate was applied.

This is a model/instrument limitation at this independently nominated sharp region, not proof that the capture set is unusable or repeat fusion impossible. No R/M replay was run on its empty all-CFA mask, no stronger polynomial or relaxed threshold was chosen, and the earlier same-ordinal census and chart positive remain unchanged. See `real-noise-consumer-structure-matched-summary-01.json` and `real-noise-consumer-structure-pairing-audit-01.json`.

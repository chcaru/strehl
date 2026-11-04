# Independent repeat compatibility and matching review

Status: active completion review, 2026-10-28. This checkpoint reviews experiment-only algorithms and distinguishes the strict compatibility instrument from a separately labelled native grouping proposal. It does not qualify a real pair, certify an optical PSF, or establish photographic improvement.

## Reviewed source and executed evidence

- noise-bee-repeat-compatibility.rs: SHA256 4bd08921c4e0d3d7264935b0097f8ef09d2fe1e2451ac92727faef7f98a9736b, including the identity-envelope correction.
- noise-bee-repeat-matching.rs: SHA256 a94d77a65ede99e58c10a85e276a6bbc5d4e2d250ea7da50d869686375e3e356.
- noise-bee-repeat-compatibility-design.md: SHA256 1b408faf4cfde936108cc9653189d302d08cb82cf1e343222b0f4511fc80c08b.
- VERIFIED from retained receipts: nb-compat-b04 compiled the above compatibility source; noise-bee-compatibility-controls-run-03 executed outputs/multi-stack/completion/nb-compat-b04/noise-bee-repeat-compatibility.exe --test-threads=4 --nocapture, exit 0, 8 tests passed. Executable SHA256 e5016d4f2eb7e1fa16bbb7e8291e3e9abcce7973b8381cbff0ce04411b98a143. The noisy same-signal census admitted 11/16 and retained 5/16 Unknown. These are author-run controls independently inspected, not an independent re-execution.
- MEASURED independent arithmetic control: python experiments/multi-stack-2026-10-28/completion/review/compatibility-identity-counterexample.py, exit 0, one process, standard-library Gaussian arithmetic, no RAW/image/engine/build inputs. Source SHA256 a6db0f1a2e176b6c6ada6d131059431998219ae5b53b2c773cdeab77e894f228; complete result in compatibility-identity-counterexample.json. This reproduces the old statistic and corrected identity projection, not the Rust producer call path.

## Concrete estimator gap found and corrected

The original joint gate evaluated Euclidean energy of high/mid/low, even though the stated target was native equal-mean MSE. Identity is the sum of those bands. Its variance is the sum of every covariance entry; neither three individual diagonal gates nor the Euclidean joint gate preserves the stated native loss fraction after recombination.

The independent witness uses actual integer-phase separable binomial taps on a 5 by 5 original-site footprint. Source 1 has center 100 DN, eight inner neighbors 10,000 DN, and sixteen outer sites 100 DN. Source 2 adds 20 DN at the center only. Known Gaussian shot variance equals each site's signal; 1,024 independent footprints, fixed seed 117. The old three upper loss ratios are 0.25434, 0.23758, and 0.11234; joint upper ratio is 0.20110. Both reciprocal AC transfer intervals lie wholly inside 0.95 to 1.05. The old decision therefore admits this pair.

Yet the true identity ratio is 400/220 = 1.81818: native equal averaging worsens average own-state MSE by 45 DN squared. The separately computed identity interval is 1.81049 to 2.43263. This illustrates how neighboring noise can cancel in identity while remaining large in each filtered band.

The corrected source accumulates sum(x)-sum(y) and sum_all(Cx+Cy) at lines 233-240, and requires its own loss envelope at lines 299-303. This closes the demonstrated estimator gap. Corpus also added a cross-band cancellation control. A future exact primitive bridge should carry the heterogeneous original-site witness through the actual sampler; the independent Python arithmetic is not that bridge.

The design prose should explicitly include this identity check. Its claim about the joint three-band covariance should not suggest that Euclidean joint energy already equals native identity error.

## Interval, reference, and power assessment

DERIVED: the implemented upper/lower inversion is algebraically consistent with the stated noncentral Gaussian quadratic envelopes. The conservative row-sum spectral bound can reduce power but does not by itself overstate information. Negative inversion discriminants become Unknown. Cross-signal polarization retains the signed interval, and reciprocal transfer requires positive lower signal energy. Flat, weak, or ambiguous evidence therefore cannot become a low-cost compatible edge. The own-state-average reference is essential: the same inequality does not license a primary-specific target or unequal precision estimator.

This remains conditional on injected covariance and exact original-footprint independence. Frozen-guide error, shared fitted geometry, quantization, source nomination, and sensor-model error are not covered by the ideal Gaussian calculation. t=log(100) is not a real-data 99 percent certificate. Multiple tails, four colors, two patches, many candidate edges, and assignment selection also preclude inheriting a single per-pair error probability for the chosen matching.

A patch-level energy/transfer result is an aggregate result on the declared sampled points. It can miss a small local disagreement dominated by stronger texture elsewhere. Stable defocus may pass while remaining defocused. Three binomial bands are not the product's seven pyramid bands; they cannot authorize arbitrary coefficient substitution or an SR sharpness claim. Those distinctions are substantive, not merely naming.

Retain full finite-power censuses. The initial failed expectation that every noisy same-signal seed must pass was appropriately preserved; changing that test to an explicit 11/16 versus 5/16 census does not establish a high-power instrument. Commission negative boundaries and complete candidate graphs before using this as a real edge classifier. A low-power instrument must not silently forbid a different native estimator experiment that already has its own local agreement/fallback rules.

## Matching review

ARGUED from source: the residual network implements successive shortest augmenting paths using Bellman-Ford, with reverse negative-cost arcs, unit capacities, and bounded nonnegative input costs. This supports maximum cardinality followed by minimum total cost. Canonical content-hash orientation and stable sorted insertion make equal-cost tie handling independent of caller order and pass labels. Unknown/Incompatible edges do not enter the graph. The 64-per-pass limit rejects the whole supplied component rather than truncating it.

No source-level optimality defect was identified. The current 2 by 2 reroute/min-cost fixtures and structured 64 by 64 case should be supplemented by an exhaustive small-graph oracle, varied costs and ties, absent/Unknown/Incompatible edges, and pass/source/edge permutations. This is an implementation verification request, not a reason to invent a failure.

Resource scope is bounded: at most 128 sources, 4,096 candidate pairs, 130 residual vertices, 64 augmentations, and bounded integer costs. The reservation is conservative for the large structures. One literal contract defect remains: assign() calls allocating validate() before checking the budget, so the error text at line 175 saying no allocation is false. Either preflight a coarse reservation first or say no graph allocation; the existing validation allocations are small and bounded.

The graph primitive only checks that receipt hashes are nonzero. Its caller must bind both receipts to this exact pair, map/domain, guide, operator, noise/gain model and policy, and must retain all candidate/refusal records. Costs and proxy radii need recorded provenance. A scale uncertainty proxy nominates; it does not establish equal PSF or stationarity. Maximum cardinality intentionally chooses more proposals before preferring lower cost; do not call the result optimal photographic quality.

## Legitimate separate native grouping experiment

A bounded experiment may broaden geometric proposals while retaining the existing product's local coefficient agreement and fallback. It need not first satisfy the stricter all-band compatibility instrument. Use an explicit GeometryProposal type/label: do not fabricate Compatible receipts, RepeatCompatible source evidence, or SR admission.

Keep every original source and unmatched singleton; preserve map, canvas, resampler, noise model, local gates and primary semantics. Archive old/new assignments. Use frozen geometry-only costs rather than the same noisy coefficient residual subsequently presented as a gain. Compare the existing four-pair result, broader deterministic matching, and all-single/no-group controls under the same complete-scene display and frozen native witnesses.

The material coupling is regrouping's change to group mean/variance and cross-group focus weights. Slightly defocused pairs can pass a local coefficient agreement gate yet soften the output. Commission the actual matching-to-core path with flat first, a genuine fine focus sweep, small blur/shift/brightness changes, clipping, unequal noise, and source/pass permutation. Retain clean-arm signal transfer and both-own-state risk alongside conditional variance. More pairs or lower variance alone does not close the photographic outcome.


## Follow-up checkpoint: matching oracle and real-guide diagnostic

VERIFIED: the matching source is now SHA256 847c2a9bfd98ef13da72efa87a14f633797fcc7397f84e2984f7861560ecd722. The error says no graph allocation, resolving the wording issue. The new exhaustive test enumerates all 512 three-by-three edge-presence graphs under six fixed cost patterns, compares cardinality and total cost with an independent recursive enumeration, and checks unchanged results after pass/source/assessment permutation. Missing edges cycle through absent, Unknown and Incompatible. Retained receipt noise-bee-matching-controls-run-02 executes outputs/multi-stack/completion/nb-match-b02/noise-bee-repeat-matching.exe --test-threads=4; exit 0, 10/10 pass; executable SHA256 2cebdd2203b10f368fd30fc944fe2745550bbc40ae39c5c153ab54c06bdc1086. This closes the requested pure-matcher implementation check. The separate newly added CLI matcher still needs its own caller controls.

VERIFIED read-only diagnostic: noise-bee-repeat-compatibility-real.rs SHA256 bae827107538ca6388dae141b29cb09c18575fadefda2a8e5f690ab18f57899b matches nb-guide-b02's build receipt. Retained command is outputs/multi-stack/completion/nb-guide-b02/noise-bee-repeat-compatibility-real.exe outputs/multi-stack/completion/noise-bee-repeat-01/equal outputs/multi-stack/completion/noise-bee-repeat-01/source-cache outputs/multi-stack/completion/noise-bee-repeat-01/inputs/protocol.json outputs/multi-stack/completion/nb-guide-01. noise-bee-compatibility-guide-run-01 records exit 0, 23.2644 seconds, sampled 284,549,120 private bytes, executable SHA256 838fcd25c19f1a5d80abe18fbffb9a443f2f865da5c4222493d3082744e47951. Four cache hits and zero RAW decodes. These timings are run provenance, not a comparative performance result.

All eight patch/color scopes retain 256 points with no support refusal. Upper-forehead R/B are Unknown and G1/G2 Incompatible; lower-body-hairs is Incompatible in all four colors. Every product/SR admission remains false. Actual target-tap disjointness and all guide-original footprints are retained. No PSF or noise-gain conclusion follows from this diagnostic.

The caller's target-to-guide coordinate chain is consistent with the primitive: target original quad plus CFA site, inverse target color pull about the full quad center, guide color pull, then subtract the same CFA site before strict Catmull interpolation. Distinct Q content identities and original-receipt chain are explicit. Any missing/clipped support prevents whole-patch evidence, rather than pruning individual points.

Before real admission, this new closure needs its own nonidentity/CA/heterogeneous linear-field oracle and a negative-weight guide-tap clipping/missing-support plant; primitive-only tests do not exercise the guide closure. Shared noisy Q values predict variances, so the resulting covariance is a plug-in model rather than a known deterministic covariance. The diagnostic correctly preserves that limit.

## Separate CLI geometry-proposal source checkpoint

Read-only inspection of session-repeat-proposals.rs and its session-consumer/session-cmd integration finds: default flag false; explicitly GeometryProposal report plus legacy assignments; SR/no-group/only-pass/reproducibility conflicts; source-content uniqueness and canonical ties; whole bounded source count; 64 MiB reservation included in merge and transfer planning. The complete 128-source triangle census is bounded and fits this conservative reservation. No default numerical path change was identified by source inspection.

Requested routing fix: validate the resolved session's two-pass and declared per-pass source bounds before original preparation/alignment, rather than only in render() after expensive work. A one-pass/large Repeat request with the hidden flag bypasses the ordinary route and currently fails late. The later source checkpoint closes this routing issue: session-consumer.rs checks exactly two declared passes and at most64 sources each immediately after manifest resolution, before read_metadata, source hashing or alignment. Also retain that gap/radius cost rewards uncertainty; it is a declared proposal heuristic, not confidence. No full-photo candidate or actual matching-to-core benefit is established at this checkpoint.


## Independent CLI oracle and actual-consumer checkpoint

The reviewer authored only crates/strehl-cli/src/session-repeat-proposals-oracle-tests.rs, SHA256 7ed159b16e7fa6d37377bb62def576c6f0dc217ffb3d02b5710edd0cc6f4f608. Its oracle enumerates 64 partial assignments directly, independently of residual-graph machinery. It covers all 512 three-by-three graphs, eight cost patterns (including ties and private-solver integer stress), three raw partition permutations, feasibility and original uniqueness. A separate all-512-graph plan test checks exact canonical content ties under pass/source/edge permutations. The weak-leverage foil deliberately shows that increasing RMS/leverage broadens nominations without becoming compatibility evidence.

VERIFIED: root registered the file as a direct test child and ran cargo test --locked -p strehl-cli repeat_proposals -- --test-threads=4. Receipt repeat-proposals-controls-02 shows fresh Compiling, exit 0, 8 tests passed including all three independent tests. This is independent test authorship with orchestrator-scheduled execution, not an independent photographic result. Existing unrelated example warnings remain; no strict-lint success is claimed.

The actual consumer harness repeat-proposal-consumer-controls.rs produces eight original-u16 sources one at a time, calls the real native sampler, preparation, group and session merge, and uses the planned four pairs. Its graph is a supplied mechanical fixture, not an alignment/uncertainty calibration. The references are noiseless outputs of actual clean all-single and separate-pass consumers, not per-band argmax or independent latent truth.

VERIFIED readback: repeat-proposal-consumer-run-01 completed exit 0, 17.6212 seconds, executable SHA256 4227bf14b77e9bf3e299e53bdcf73d1496cd53cacd11453ce7f2cda2f5eafe58. repeat-proposal-consumer-01.json retains all 594 rows: 11 cases, six arms, clean plus eight noisy seeds. No condition was silently omitted.

Independent arithmetic on retained rows matches the reported tradeoffs. Relative to the same clean all-single reference, noisy stationary proposal MSE ratios are 0.614 to 0.737 across CFA colors; clean stationary transfer is 1. Fine-focus-offset and contrast attenuation have clean transfer 0.95777 and 0.93520 respectively, despite some lower noisy MSE. Unequal-variance proposal MSE is 1.333 to 1.366 times all-single. These outcomes prohibit a generic quality or default-promotion claim.

A common-reference null can hide shared damage. In the blue-contrast case, both proposal and all-single are unchanged relative to each other but have clean B transfer 0.89999 to clean pass A (MSE 112.26). Primary A improves that only to 0.91865 (MSE 77.24). In the brightness case proposal is +10 DN versus pass A while primary A restores zero offset. In the clipped fixture proposal already matches clean pass A; clean clipped pass B is not a latent truth target for recovered highlights.

The first harness's blur/focus fixtures attenuate all sinusoidal components equally, so they are contrast/focus-response plants, not actual PSF convolutions. Its per-seed MSE rows are not per-pixel temporal variance outside flat cases. Root retained this checkpoint and is adding frequency-dependent PSF/spatial-focus controls, an unclipped sentinel and explicit temporal moments. These are refinement of the observer's scope; the existing adverse results remain.


## Consumer02 review before the full-photo experiment

VERIFIED: repeat-proposal-consumer-build-02 executable SHA256 f0b21d2ca258b291e09903ba75a73e5f103d0d539195abeef1730d22dcba93a1 produced both outputs. Commands retained in repeat-proposal-consumer-psf-run-02 and repeat-proposal-consumer-original-run-02 respectively invoke that executable with repeat-proposal-consumer-psf-02.json psf and repeat-proposal-consumer-original-02.json. Both exit 0; 378 PSF rows and 594 original rows are complete. These runs used four workers and briefly overlapped; elapsed times are provenance, not comparative performance.

Independent standard-library readback confirmed every old field in all 594 prior rows is exactly retained. The updated producer accumulates pointwise Welford moments over eight seeded acquisitions. I separately checked MSE = squared error of the temporal mean + 7/8 sample temporal variance for every target/pass and CFA component, rather than only the analyzer's averaged targets. It holds within the stated f32 tolerances; it is not asserted as exact floating-point equality.

The new PSF response multiplies each of the three known sine components by its exact continuous Gaussian frequency response. The two-depth fixture explicitly prescribes local PSFs and does not model physical occlusion. The unclipped consumer sentinel closes the clipped-reference ambiguity: clean proposal matches it with zero MSE, zero mean difference and unit transfer.

Adverse outcomes remain visible. Clean PSF-blur transfer is 0.96434 relative to all-single and 0.94105 relative to pass A. B-only PSF blur is unchanged relative to all-single while both share B transfer 0.94105 relative to pass A. PSF focus-sweep and fine-offset transfers relative to all-single are 0.99978 and 0.99708. The original unequal-variance risk regression remains in the retained rows.

No new methodological barrier was found to a research-only full-photo comparison of legacy grouping, broader geometry proposals and all-single controls under the frozen source/map/domain/display and all nine native witnesses. This supports conducting the bounded experiment, not a generic quality conclusion. The flag remains off by default; source compatibility, SR admission and optical sharpness are not established by these controls. Full outputs and target-specific signal tradeoffs must decide the photographic result.

## Dedicated guide-closure controls and exact diagnostic replay

The requested closure controls are now present in noise-bee-repeat-guide-predictor.rs, SHA256 f78858fcc008726ab00bf234a83f7f7a6bb8fb4a6394c313583534cba8c98a2b. Independent source inspection confirms that the expected-value oracle uses absolute sensor coordinates and direct 2 by 2 inversion rather than calling the predictor's apply_at path. It covers all four CFA sites, nonidentity scale/rotation/color pulls and two different linear guide fields. Negative-weight Catmull clipping, missing border, wrong full gauge and temporal extrapolation refuse.

VERIFIED receipt noise-bee-guide-predictor-controls-run-01 executes outputs/multi-stack/completion/nb-predict-b01/noise-bee-repeat-guide-predictor.exe --test-threads=4, exit 0, 3 tests passed, executable SHA256 50008fb412b4127752f2c880cfb4fd2e06803bc9dfcd7111e3850099b631d04a. The actual caller uses the extracted helper. The retained nb-guide-02/equivalence.json records all eight diagnostic rows and source identities exact and all eight footprint files byte-identical to nb-guide-01. The replay executable is 5da41347be99519d2e7de79179a53f4e3781033a8f509eefb8f2365b8931702f, run noise-bee-compatibility-guide-run-02, exit 0. Buffered serialization changed elapsed operational time; the one-second runner floor precludes treating that as a numerical-performance result.

These controls close the identified coordinate/support implementation obligation for this diagnostic. They do not make the shared noisy guide a known deterministic covariance or establish real compatibility. All product/SR admissions remain false.

## Oracle precision ablation: conditional benefit and target tradeoff

VERIFIED receipt review: repeat-proposal-precision-flat-run-01 and repeat-proposal-precision-full-run-01 both invoke outputs/multi-stack/completion/np-precision-b01/repeat-proposal-precision-controls.exe, SHA256 680bf21001c936c0d5d99e32813c57367f3d33d9e07b6ab27c38dbb09cd56017, with the corresponding output JSON and flat/full selector. Both exit 0 with RAYON_NUM_THREADS=4. The flat run precedes the full census. Full elapsed time 44.393 seconds and sampled private memory 40,828,928 bytes are provenance, not comparative performance.

The causal arm retains memberships, original noisy samples, local agreement and primary/fallback behavior while changing the precision prediction to the exact source-dependent latent signal. EqualObservation supplies the same unweighted group observation to focus selection. These deterministic oracle predictions are deliberately independent of the noisy target samples; they are not a calibrated or measured real guide. The normal seven-band path and a separate zero-band flat control are distinguished.

Independent source and retained-row review supports the stated limited conclusion. In the unequal-variance common-signal fixture, per-color precision risk is 0.602 to 0.640 times equal grouping and 0.816 to 0.862 times all-single, with clean transfer 1. The zero-band variance control agrees with the injected quantized plant within 1.40 percent. Equal-noise stationary precision equals equal grouping. Ninety missing-guide checks retain exact output bits and ordinary decision counters; precision and missing-prediction counters appropriately differ. The prior shared summaries and counters match exactly for 270 original and 216 PSF rows; old full image arrays were not retained, so that equivalence is not an all-array claim.

The adverse PSF result remains. Equal-noise blur still attenuates clean signal by about 5.89 percent relative to the sharper pass. With unequal noise and PSFs, precision lowers sharper-target risk to 0.503 to 0.553 times equal but raises blurrier-target risk to 1.025 to 1.184 times equal. Choosing the blurrier pass as primary does not guarantee preservation: primary is the disagreement fallback, not an unconditional target constraint. Averaging the two target risks would conceal this tradeoff.

This closes a causal explanation for the earlier unequal-noise regression under exact model predictions. It does not establish real-guide calibration, partial-guide halo correctness in this particular harness, generic photographic improvement, or compatibility/SR admission. The separately retained full photographs and actual guide/fallback controls remain necessary for those claims.

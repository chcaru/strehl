# Native sensor-transfer protocol: final choice review

2026-09-09. **ACCEPT METHODOLOGY SOURCE, with the limits below.** This clears the cohesive protocol and checker design for implementation/source review. It does not clear the unapplied producer patch, concrete independent checker, builds, controls or RAW execution. No scientific data, decoder, simulation, candidate, test or build was executed during this review.

I authored the initial RAW-priority/ISO160 subset recommendation and proposed the pair-contrast/frame4 and phase-support alternatives during source review. I therefore disclose participation in those choices; I am not an independent numerical corroborator of them. The protocol and producer have separate authors. This review challenged their definitions and failure directions before any result existed. The earlier [source-choice review](source-choice-review.md) remains the detailed source rationale.

## What is now defensible

The fixed27-source population and central128x128 quad Crop remain unchanged. The native consumer retains four Laplacian bands plus base, actual injected model, current gather/MHC/WB/CA and policy. A placed identity Similarity is not declared an effective all-channel identity. Reusing a no-map physical predictor requires actual green equality and source-supported effective transformation provenance. Source codes, signed and clamped quantities, native normalization and physical-model comparisons remain separate.

The main paper statistic uses two disjoint contrasts and frame4 as the independent signal witness; all-five variance is sensitivity only. Dark uses11 pairs and all22 as sensitivity. Pair and all-frame results share inputs and are not independent replications. Sixteen fixed spatial blocks and pair contributions describe dispersion without pretending that every correlated pixel supplies another temporal degree of freedom. Frame4 prediction uncertainty and unavailable profile-parameter uncertainty are explicit. Conditional scalar intervals do not become a whole-crop or physical-model PASS.

The predictor and observed consumer now address different, correctly named questions. Temporal variance of actual band coefficients is smoothed to the energy scale; scene mean energy is reported separately. The independent diagonal model composes the literal spatial operator and coalesces repeated boundary addresses before squaring coefficients. This can disagree with the scalar-white-beta approximation without proving incorrect sensor gain. Actual L/E/V/weight arrays are distinguished from floor and threshold-side quantities DERIVED from their operands. The eight support/phase strata retain boundaries and the tiny k3 support population; k3 receives no inferential claim and its beta is a not-attempted white fallback, not a failed actual probe measurement.

## Nuisance choices and their failure directions

The fixed paper screens are acceptable **as limited premise screens**. They read independently decoded inputs and do not use the tested noise law, measured variance, selected weights or outputs to select favourable sites. Headroom is all-sites/all-five; illumination uses fixed source rectangles and absolute/relative limits; gross motion checks nine offsets of coarse box means. The fixed textured shift witness and low-texture refusal test whether that screen has the claimed limited power. No brightness or registration correction is applied to the scientific arrays after a failure.

This is deliberately weaker than proving stationarity. The motion screen can miss small shifts or periodic ambiguities; the illumination screen can miss smaller changes, and noise can trigger refusal. Non-trigger therefore means only no detection at those fixed screens. A refusal or low-texture result stops the affected physical paper interpretation while preserving admissible dark/implementation observations. The two capture blocks' different time/state/release mode remain visible; neither is fitted or subtracted into the other. These limits prevent the nuisance screen from becoming a circular calibration gate.

The binary32 operation-order contract, exact basic-array comparison and separately bounded log/exp comparison are reasonable prospective implementation requirements. They still need source/compiler confirmation and actual private controls; no numerical tolerance was selected from sensor output. Exact f32 outputs and whole native-writer TIFFs are both required for observer witnesses, so quantization cannot hide a floating perturbation.

## Pre-data errors caught and corrected

These were errors or proof gaps in proposed controls, **not measured sensor defects**.

| Finding | Corrected source contract and powered check |
| --- | --- |
| A16-DN frame4 change was ambiguous by a factor of two at green variance. | Each photosite prediction changes by16g; equal-gain green variance changes by8g. Primary pair variance is unchanged. Group07 states both quantities explicitly. |
| Multiplying gain by4 was conflated with multiplying total variance by4. | Group08 separates immutable gain/RN identity faults from the literal `q -> 4q` normalization destroyer. Only the latter requires the measured/predicted ratio to become one quarter. |
| Positive excess was claimed to imply positive weight universally. | The exact p2 multiplication can underflow to zero; p1 has its own separately labelled source-only witness. Their comparisons are exact binary32 bits, including zero. The looser log/exp bound applies only to that branch. Group18 includes tiny-positive underflow, zero-ratio/clamped-exp and upper-clamp witnesses, plus positive-factor4 and zero-to-minimum-subnormal faults. Multiplying zero by4 is explicitly not a power test. |
| Inverting a CDF and checking against that same CDF did not independently commission the half-integer branch. | Group19 now checks six external df4/11/21 quantile cells, plus the independent analytic df2 relation. Omitted half-integer terms and a wrong df4 starting branch must fail the same external-reference predicate. Internal inverse residual remains numerical consistency only. |

I independently checked the [primary NIST chi-square table](https://www.itl.nist.gov/div898/handbook/eda/section3/eda3674.htm), which labels cumulative probabilities. Its `.025/.975` values are df4 `(0.484,11.143)`, df11 `(3.816,21.920)` and df21 `(10.283,35.479)`. The adopted0.0005001 allowance respects the table's three-decimal precision; it is not a claim of1e-10 external accuracy. The protocol author separately read both table tails. No quantile was simulated or fitted to candidate outputs.

All20 groups remain fixed, with their listed variants/restorations. Actual portions of observer/exercise groups remain pending until real native artifacts exist; synthetic controls cannot fabricate real gate use. A missing actual zero/positive class is NOT_EXERCISED for that claim rather than erasure of unrelated decode/dark results. Concrete checker source must literalize the structured/textured witnesses in groups12/14 before its hold; reusing the already fixed group15 field is sufficient and requires no new data or group.

## Traversal, witnesses and remaining work

The accepted nine paired invocations contain50 native original decodes,100 actual folds,50 real full-native gathers and50 synthetic full-native probe gathers; the separate independent decoder covers27 originals once. Existing BandGain startup adds nine initializations/288 compact white fields. Eighteen collapsed f32 payloads and18 actual existing `write_merged` TIFFs follow those finished routes without additional folds/decodes. These are source-derived traversal counts requiring actual accounting, not measured runtime figures.

Observer off/on/placebo and feature-off comparisons cover the five-paper and **first-two-dark** populations. They do not establish whole22-dark output neutrality. Both f32 and TIFF whole-byte checks are mandatory within each declared witness; no no-map/placed-identity output equality is required. The direct actual `t_site` callback is the correct proposed map seam; a second metadata resolution would not observe what the gather used.

Producer patch/adapter review remains OPEN: verify callback placement and read-only behaviour, feature-off boundaries, actual plane-cache reads, source/Frame lifetime and first-decode reuse, writer settings, complete arrays, publication bounds and the truthful traversal. Independent checker implementation review remains OPEN: verify literal fixtures, same-predicate faults/restorations, decoder ownership/addresses, finite arithmetic/quantile code, terminal/refusal association and bounded publication. Root's subsequent build/control/RAW releases remain separate. This methodology acceptance supplies no reason to expand the crop, input population, policy arms or provenance tooling.

## Exact reviewed versions and preparation scope

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| `independent-protocol.md` | 38811 | `e3c527d2d012e56877dd1b5992237191fb988eed957234664a37fab781585ec4` |
| `independent-checker-design.md` | 12541 | `a68987a11679835034699454e8c5bf669b8c4da336b9e1685feb057aa810e6f0` |
| `source/implementation-contract.md` | 12933 | `6f69881609b856956afd78deb9f0028b28f2ed36f98398438d14bfbfb4e0f25e` |

The implementation contract was reviewed for interface/traversal agreement, not treated as proof of the unapplied patch. Its writer/startup delta was read after the earlier11807-byte version. This review used targeted local source/report reads, the same current `select_weight` source branch, and two bounded primary NIST HTML views. It did not repeat the broad prior-art query or inspect external implementation source. The final three-file authentication read64,285 bytes, in addition to prior targeted reads. The existing64MiB-read/4MiB-retention/60CPU/120-active-process-wall preparation grant remains the authority; exact cumulative CPU was not instrumented and is not claimed. The report alone is newly published and read back below64KiB. No live crate, capture, old evidence or committed review was edited; root owns commits.

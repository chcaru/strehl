# M163 — M10 uncertainty-instrument repair

## Verdict

**Gap 3 is repaired and commissioned in a standalone M10 checker. M10 itself
remains UNMEASURED because gaps 1 and 2 remain.**

The registered M10 value decision is exactly invariant to its named
uncertainty product. On one deterministic 20,000-pixel fixture, reported,
all-zero, all-infinite, and random uncertainty each left the same seven value
quantities, the same PASS, and the same canonical result SHA-256:

`3a07606bd833ccea2392054424370d36ec98da6cb1d8cff481eed4a5483d5945`.

The value tuple, in scorecard order, was:

| Quantity | Value | Written bar | Result |
|---|---:|---:|---|
| valid target fraction | `1.000000` | `>=0.99` | PASS |
| rank correlation | `0.999500` | `>=0.99` | PASS |
| median absolute error | `0.116674` step | `<=0.5` | PASS |
| p95 absolute error | `0.365313` step | `<=1.0` | PASS |
| ruler slope error | `0.010000` | `<=0.05` | PASS |
| flat-null p95 range | `0.200000` step | `<=0.5` | PASS |
| synthetic layer confusion | `0.005000` | `<=0.01` | PASS |

The repaired decision retains those seven bars and adds five uncertainty
vetoes. The calibrated fixture passes. Zero, infinity, random uncertainty,
a 1.25x uncertainty-scale disturbance, and a 1.50x depth-error degradation all
fail. Replacing a 0.50x under-reported uncertainty field with the calibrated
field changes FAIL to PASS and lowers the proper score.

This is commissioning, not a scored M10 result. No protected or development
RAW was opened.

## Provenance correction: what M161 actually established

There was no pre-existing executable M10 checker against which M161 could have
run substitutions:

- M161 describes itself as a read-only document audit that ran no stack or
  benchmark (`docs/research/M161-bar-feasibility.md:13-16`).
- The later ratification explicitly says the claim that M161 replaced
  uncertainties “describes an experiment M161 did not run”; it proved a
  functional invariance of the written verdict
  (`docs/research/M161-m3-ratification.md:210-214`).
- The baseline score implementation defines only `measure_m1` and `measure_m2`
  (`experiments/SCORECARD-BASELINE/measure.py:88,172,213-269`), and its verifier
  reads only those axes (`experiments/SCORECARD-BASELINE/verify.py:49-63`).
- Its frozen capability record says
  `stack_help_mentions_depth_output: false`
  (`experiments/SCORECARD-BASELINE/out/RUN-MANIFEST.json:9-14`).

`experiments/M163-m10-uncertainty/audit.py` measures zero pre-M163 M10 decision
implementations, one Python/Rust source containing `depth_sigma_um` (the M84b
truth-map producer), and five containing `sigma_z` (the A5 phase-zero
experiments). None is an M10 decision. The audit intentionally exits 1 rather
than throwing.

To make the assignment executable without pretending an absent product exists,
M163 transcribed the registered seven-value decision into
`score_legacy`. This is the first executable zero/infinity/random reproduction,
not retroactive evidence that M161 ran one.

The orchestrator-owned `docs/OWNER-ACTIONS.md:746-749` still repeats the
incorrect experimental attribution to M161. It should say that M161 proved the
formal invariance and M163 performed the first executable substitution.

## Defect location

The original defect is a specification-to-decision drop:

- M10 says ordering, scale, **and uncertainty** must survive external truth
  (`docs/proposals/2026-09-sota-scorecard.md:1264-1269`).
- The exact computation then consumes only depth truth, converted depth,
  valid fraction, rank, point errors, slope, flat range, layer confusion, and
  boundary bias (`:1282-1300`).
- The success clause enumerates seven value bars and no uncertainty quantity
  (`:1302-1304`).

The executable reproduction is
`experiments/M163-m10-uncertainty/m10_checker.py:67-81`:
`score_legacy` accepts `reported_uncertainty` but never reads it. This mirrors
M161's formal identity
`V(z_hat, sigma_z) = V(z_hat, sigma_z')`
(`docs/research/M161-bar-feasibility.md:390-399`).

There is no earlier source line where uncertainty was overwritten or defaulted,
because the pre-M163 checker did not exist.

## Repair

The repair is
`experiments/M163-m10-uncertainty/m10_checker.py:102-259`.
`score_repaired` now conjuncts the unchanged seven-value decision with an
uncertainty decision that requires:

1. finite, non-negative reported one-sigma uncertainty at every depth-valid
   pixel;
2. nominal 95% interval coverage in `[0.93, 0.97]`;
3. empirical/predicted variance ratio in `[0.90, 1.10]` in at least 9 of 10
   predicted-uncertainty deciles;
4. median reported 95% half-width `<=0.5` focus step; and
5. p95 reported 95% half-width `<=1.0` focus step.

The coverage and decile bars reuse M9's already frozen calibration tolerances
(`docs/proposals/2026-09-sota-scorecard.md:1247-1249`). The width guards reuse
M10's existing median/p95 point-error magnitudes. They prevent all-infinite
intervals from passing. Mean Gaussian CRPS is also reported as a proper
directional score, but it is not given an invented pass threshold.

One unweighted origin is removed before uncertainty scoring. Candidate
uncertainty cannot move that fit. Independent local/repeat truth uncertainty is
combined in quadrature with candidate uncertainty. Correlated ruler-angle,
pitch, perspective, and focus-scale uncertainty must instead remain a nuisance
envelope on the existing value arms; treating it as thousands of independent
pixel errors would be pseudoreplication.

The machine-readable definition is
`experiments/M163-m10-uncertainty/instrument-definition.json`.

## Gap 2 product contract forced by the repair

For M10 to be scoreable, the future product must supply:

- a physical-depth plane in micrometres;
- a co-registered per-pixel **one-standard-deviation** uncertainty plane in
  micrometres, not a unitless confidence or interval width;
- an explicit validity mask and grid/coordinate metadata; and
- the capture-model provenance needed for the checker to convert depth,
  candidate uncertainty, and independent local truth uncertainty to the same
  focus-step equivalent.

The candidate uncertainty must exclude reference uncertainty; the checker
combines independent local terms. Every depth-valid pixel must have finite,
non-negative uncertainty. Missing, NaN, or infinite values fail rather than
being omitted.

Current Strehl advertises neither required numeric plane: source preflight found
`0/2` (`depth_map` and `sigma_z_map`) and therefore returns FAIL at the repaired
input-contract preflight. This is not a scored M10 failure; it is gap 2.

## Commissioning

The fixture has 20,000 canonical target pixels. It is non-degenerate:
all 20,000 residuals are non-zero, residual standard deviation is
`0.182577` step, and reported sigma spans `0.126144` to `0.234146` step from
p05 to p95.

### Zero / infinity / random

| Uncertainty input | Legacy | Repaired coverage | Deciles in `[0.90,1.10]` | Median / p95 95% half-width (step) | CRPS (step) | Repaired |
|---|---|---:|---:|---:|---:|---|
| calibrated report | PASS | `0.949250` | `10/10` | `0.353675 / 0.458917` | `0.101205` | PASS |
| all zero | PASS, identical hash | `0.000000` | `0/10` | `0 / 0` | `0.142968` | FAIL |
| all infinity | PASS, identical hash | N/A | `0/10` | N/A | N/A | FAIL |
| random `[0.01,0.80]` | PASS, identical hash | `0.920300` | `0/10` | `0.801334 / 1.492742` | `0.137551` | FAIL |

Thus the repaired zero/infinity/random null moves both quantities and verdict.
The infinite case remains a normal FAIL result rather than throwing.

### Movable null

Multiplying every calibrated reported sigma by `1.25`, with the same depth
errors, moves:

- coverage `0.949250 -> 0.985400`;
- passing deciles `10/10 -> 0/10`;
- median half-width `0.353675 -> 0.442094` step;
- p95 half-width `0.458917 -> 0.573647` step;
- CRPS `0.101205 -> 0.102703` step; and
- verdict `PASS -> FAIL`.

This proves the null is neither frozen nor degenerate.

### Planted degradation

Multiplying every depth residual by `1.50` while holding uncertainty fixed
moves:

- median/p95 point error
  `0.116674 / 0.365313 -> 0.175010 / 0.547970` step;
- coverage `0.949250 -> 0.811300`;
- passing uncertainty deciles `10/10 -> 0/10`;
- CRPS `0.101205 -> 0.156590` step; and
- verdict `PASS -> FAIL`.

All seven old value bars still pass after this plant. The new uncertainty veto,
not an unrelated legacy threshold, catches the degradation.

### Planted improvement

Holding the depth estimate fixed, replacing a deliberately under-reported
`0.50x` sigma field with the calibrated field moves:

- coverage `0.676400 -> 0.949250`;
- passing deciles `0/10 -> 10/10`;
- CRPS `0.109187 -> 0.101205` step; and
- verdict `FAIL -> PASS`.

The interval widths increase, correctly: the instrument rewards calibration,
not merely narrower claims.

## Bar and present disposition

Relative to the written M10 success clause, the repair is **HARDER**:

- existing value bars retained: `7/7`;
- existing thresholds loosened: `0`;
- new uncertainty vetoes: `5`.

The calibrated synthetic fixture passes both the old and repaired decisions.
The zero, infinity, and random substitutions pass the old decision and fail the
repaired one. No path is made easier.

Current Strehl supplies `0/2` required numeric product planes and therefore
**FAILS the repaired product preflight**. It remains **UNMEASURED**, not a
scored M10 failure, because no eligible product or fresh physical truth exists.

## Relationship to the other M10 gaps

1. **Gap 1 remains:** M154's admissible nominal angle band is
   `[10.014357, 10.516727] deg`, while the existing record has no bounded
   uncertainty. All three old ruler stacks are burned and may only be used for
   development. M163 did not use them.
2. **Gap 2 remains:** the stacker emits no physical depth or `sigma_z` product.
   The product contract above is the part this repair now makes concrete.
3. **Gap 3 is repaired in the checker:** uncertainty is mandatory and changes
   the decision. Integration awaits gap 2; scoring awaits both gaps 1 and 2.

The old Ask 2d heading calling its capture “the whole of M10” was **not
accurate**. The current owner-action text is already corrected to “One of three
things M10 needs” and explicitly retracts the old heading
(`docs/OWNER-ACTIONS.md:688,739-744`). That capture can close gap 1 only; it
cannot create the depth-plus-uncertainty product or integrate this uncertainty
decision.

## Reproduction

From the `strehl` repository root:

```powershell
python experiments\M163-m10-uncertainty\audit.py
# Expected exit 1: no pre-M163 production/baseline M10 implementation.

python experiments\M163-m10-uncertainty\test_m10_checker.py
python experiments\M163-m10-uncertainty\commission.py
python experiments\M163-m10-uncertainty\verify_results.py
```

The unit suite runs four tests. Commissioning and result verification exit
zero. Canonical measurements are in
`experiments/M163-m10-uncertainty/commission.json`.

## Residual doubt

This repair commissions the uncertainty logic on deterministic synthetic data;
it does not validate a future producer's uncertainty model. The added M10
uncertainty thresholds are a disclosed tightening derived from existing M9 and
M10 thresholds, not yet text merged into the orchestrator-owned scorecard.
Physical scoring still requires the fresh metrology-backed unit, an independent
focus-step conversion, a real depth-plus-uncertainty product, and a frozen
sampling/aggregation plan that handles spatial correlation.

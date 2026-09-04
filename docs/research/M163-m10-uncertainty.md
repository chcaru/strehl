# M163 — M10 uncertainty-instrument reproduction

## Verdict

**STOPPED: the requested executable null cannot be reproduced because no
executable M10 decision exists.**

This is not a zero/infinity/random result. It is a correction to the premise of
the assignment:

- M161 describes itself as a **read-only document audit** that ran no stack or
  benchmark (`docs/research/M161-bar-feasibility.md:13-16`).
- The later M161 ratification explicitly says that the claimed substitution
  “describes an experiment M161 did not run”; M161 proved only a functional
  invariance of the written verdict
  (`docs/research/M161-m3-ratification.md:210-214`).
- The baseline score implementation contains exactly two `measure_m*`
  functions, `measure_m1` and `measure_m2`, and constructs only `m1` and `m2`
  results (`experiments/SCORECARD-BASELINE/measure.py:88,172,213-269`).
- Its verifier reads exactly those same two axes
  (`experiments/SCORECARD-BASELINE/verify.py:49-63`).
- Its frozen capability probe reports
  `stack_help_mentions_depth_output: false`
  (`experiments/SCORECARD-BASELINE/out/RUN-MANIFEST.json:9-14`).
- The baseline report therefore says both “no depth product” and “M9/M10 have no
  compatible product to check”
  (`docs/research/SCORECARD-BASELINE.md:34,50-52`).

Per the lane instruction, failure to reproduce the claimed executable null is a
major finding and work stops before repair or commissioning.

M10 remains **UNMEASURED**. The written scorecard does have the formal omission
M161 identified, but this lane did not establish that an implemented checker is
blind: there is no implemented checker to exercise.

## Independent audit

Run from the `strehl` repository root:

```powershell
python experiments\M163-m10-uncertainty\audit.py
```

The expected exit is `1`, representing a fail-closed instrument audit rather
than a Python exception. The run made these measurements:

| Quantity | Measured result |
|---|---:|
| tracked Python/Rust files containing the registered M10 decision terms | `0` |
| scorecard-baseline `measure_m*` functions | `2` (`measure_m1`, `measure_m2`) |
| axes consumed by the scorecard-baseline verifier | `2` (`m1`, `m2`) |
| frozen CLI help advertises a depth output | `false` |
| tracked Python/Rust files containing `depth_sigma_um` | `1` |
| tracked Python/Rust files containing `sigma_z` | `5` |
| executable M10 implementations found | `0` |

The one `depth_sigma_um` source is
`experiments/M84b-ruler-metrology/src/17-depthmap.py`. It **produces an
external truth uncertainty map** at lines 521-527; it is not an M10 candidate
checker. The five `sigma_z` sources are the A5 phase-zero depth-field
experiments listed in `audit.json`; none implements the registered M10
pass/fail tuple.

The substitution outcomes are consequently:

| Replacement | Result |
|---|---|
| all zero | `NOT_RUN` — no M10 decision accepts the field |
| all infinity | `NOT_RUN` — no M10 decision accepts the field |
| deterministic random values | `NOT_RUN` — no M10 decision accepts the field |

These are deliberately not reported as unchanged measurements.
`experiments/M163-m10-uncertainty/audit.json` is the canonical machine-readable
record.

## Where the omission actually is

There is no source line at which a candidate uncertainty field is dropped,
overwritten, or defaulted. The omission is in the registered specification:

- M10 says ordering, scale, **and uncertainty** must survive external truth
  (`docs/proposals/2026-09-sota-scorecard.md:1191-1194`).
- Its exact computation then enumerates only the depth truth construction,
  depth-unit conversion, valid fraction, rank, point errors, slope, flat range,
  layer confusion, and boundary bias
  (`docs/proposals/2026-09-sota-scorecard.md:1207-1225`).
- Its success clause contains no uncertainty quantity
  (`docs/proposals/2026-09-sota-scorecard.md:1227-1229`).

M161 expresses that textual omission as
`V(z_hat, sigma_z) = V(z_hat, sigma_z')`
(`docs/research/M161-bar-feasibility.md:390-399`). That identity is a valid
reading of the specification, not the result of substituting values into code.

The production side is absent too. The current CLI exposes election,
effective-sample-count, and centrality-confidence maps, but no physical-depth or
`sigma_z` product (`crates/strehl-cli/src/main.rs:520-587`). This agrees with
the frozen capability result above.

## Why no repair is committed

An executable repair needs two things the repository does not yet define:

1. a candidate-product contract carrying `z_hat`, `sigma_z`, a validity mask,
   units, grid, and provenance; and
2. frozen numerical acceptance rules for uncertainty calibration.

M161 proposes nominal interval coverage, calibration by predicted-uncertainty
decile, and a proper score or width guard
(`docs/research/M161-bar-feasibility.md:410-414`), but it does not freeze their
thresholds. Choosing those thresholds in this lane would create a new bar,
not repair code to an existing one. M144 likewise identifies how geometric
truth uncertainty can flip the existing point and slope arms, but does not
define a candidate-`sigma_z` acceptance rule
(`docs/research/M144-reference-uncertainty.md:557-575`).

The existing ruler also cannot furnish a future score: M154 found its angle
uncertainty unbounded and its unit already burned
(`docs/research/M154-m10-angle.md`, sections “Verdict” and “Consequence for
M10”). That does not prevent synthetic commissioning of a future checker, but
it does prevent claiming a current physical-depth score.

The next valid action is an orchestrator-owned specification decision that
freezes the uncertainty-product schema and numerical calibration/width rules
while retaining every existing M10 value bar. Only then can an implementation
be repaired or created and subjected to the required movable null, planted
degradation, and planted improvement.

## Requested disposition

| Item | Result |
|---|---|
| Reproduced the void | **NO** — zero/infinity/random were each `NOT_RUN`; executable M10 implementations found: `0` |
| Defect location | **Specification omission**, `2026-09-sota-scorecard.md:1207-1229`; no code location exists |
| Repair | **NOT PERFORMED**, per the mandatory stop rule |
| Null now moves | **NOT TESTED** |
| Planted degradation | **NOT TESTED** |
| Planted improvement | **NOT TESTED** |
| Bar | **UNDETERMINED**; no numerical uncertainty bar is frozen, so harder/identical/easier cannot honestly be computed |
| Current code under repaired M10 | **UNMEASURED, not PASS**; compatible depth-plus-uncertainty products found: `0` |
| Residual doubt | The formal omission is real. Whether a future executable checker would be blind cannot be tested until one exists. |

# M135 per-capture comparison checker preregistration

Status: **FROZEN BEFORE COMPARISON-CHECKER OUTCOME GENERATION; PHYSICAL RULE
UNBOUND**

## 1. Purpose and non-result

M138 requires a binary `detail_pass`, a stable hashable rule, and a
single-capture applicability decision. The estimator-level M135 API does not
currently provide that interface. It emits continuous coordinates and typed
eligibility states, while the only comparison rule is prose in the research
report.

This preregistration closes the software-interface gap without claiming that
the physical instrument exists. `comparison-contract.json` and
`comparison_checker.py` freeze the decision vocabulary, payload checks,
bootstrap bars, and output schema. `comparison-binding.json` remains
`UNBOUND`. Therefore the only claim-bearing current result is
`INSTRUMENT_UNBOUND`, never `DETAIL_PASS`.

Pressure from M138 is not evidence. No Phase-1 output may tune this rule, and
failure of physical M135 commissioning must leave M138 blocked.

## 2. Decision vocabulary

The checker returns exactly one status:

- `DETAIL_PASS`: applicable, physically bound, valid, and every hard
  non-inferiority gate passes;
- `DETAIL_FAIL`: applicable, physically bound, valid, and at least one detail
  gate fails;
- `NOT_APPLICABLE`: the capture ID is absent from the frozen M135 capture
  ledger;
- `INSTRUMENT_UNBOUND`: no physically commissioned M135 binding exists; or
- `INSTRUMENT_INVALID`: a registered capture, binding, payload, flat control,
  or bootstrap record is malformed or ineligible.

`detail_pass` is `true` only for `DETAIL_PASS`, `false` only for
`DETAIL_FAIL`, and `null` for all other statuses. A consumer may not coerce
`null` to `false`. For a capture listed in M138's detail ledger,
`NOT_APPLICABLE`, `INSTRUMENT_UNBOUND`, and `INSTRUMENT_INVALID` block
inference; they are not candidate failures.

## 3. Per-capture input

The decision unit is one capture. Cross-capture averaging is forbidden.

The physical payload generator must use the same independently captured
`R1/R2` truth for candidate and legacy and must retain at least `64`
registered sites. The role set adds mode-specific candidate and legacy
`Y1/Y2`, shared `flat_R1/flat_R2`, and mode-specific candidate and legacy
`flat_Y1/flat_Y2`. The featureless sentinel is constitutive, not an optional
validation record.

The binding freezes, per capture:

- site-manifest hash;
- independent-reference-manifest hash;
- flat-sentinel-manifest hash;
- tone-witness hash; and
- extraction-configuration hash.

It also freezes the physical preregistration, physical commissioning,
payload-generator, and estimator hashes. A payload must match every value
exactly.

## 4. Eligibility and mandatory flat control

Candidate and legacy must each have core status `OK`, finite point
information, and the M135 flat status `NO_DETAIL`. The checker recomputes the
three flat decisions from supplied numeric ratios:

```text
J_TR(flat) / J_TR(detail)                         <= 0.10
P_rep(reference_flat) / P_rep(reference_detail)  <= 0.25
P_rep(output_flat) / P_rep(output_detail)         <= 0.10
```

Any failure is `INSTRUMENT_INVALID`, not `DETAIL_FAIL`, because the detail
instrument did not establish specificity on that capture.

## 5. Frozen comparison rule

The payload contains `10,000` paired-site bootstrap replicates generated with
seed `20260902` on this capture only. The bound generator must derive them from
raw M135 inputs or a separately reproducible certificate payload. The checker
does not accept confidence limits or a Boolean supplied by the producer; it
recomputes quantiles with NumPy's `linear` method.

The candidate receives `DETAIL_PASS` iff all are true:

```text
Q05(J_candidate / J_legacy)                         >= 0.98
Q05(T_candidate,k / T_legacy,k)                     >= 0.98
                                                    for all 16 cells k
Q95(U_candidate - U_legacy)                         <= 0.02
```

No gate compensates for another. Equality passes. These are preservation
bars, not superiority claims: M138 asks whether its noise change preserves
detail relative to legacy. A separate M1-ahead claim still requires the
stronger rule in the M135 research report.

The `0.98` information bar is the scorecard's registered comparator-retention
bar. The per-cell transfer `0.98` and unexplained-fraction `0.02` vetoes were
already stated in M135 before this consumer interface. No Phase-1 output
exists, and none informed these values.

## 6. Commissioning battery frozen before execution

The checker self-test must prove:

1. the checked-in unbound binding returns `INSTRUMENT_UNBOUND`;
2. a capture outside a synthetic bound ledger returns `NOT_APPLICABLE`;
3. an exact null returns `DETAIL_PASS`;
4. a planted genuine improvement returns `DETAIL_PASS` with larger continuous
   coordinates;
5. an information defect returns `DETAIL_FAIL`;
6. a one-cell transfer defect returns `DETAIL_FAIL`;
7. an unexplained-repeatability defect returns `DETAIL_FAIL`;
8. a failed candidate flat null returns `INSTRUMENT_INVALID`;
9. a failed legacy flat null returns `INSTRUMENT_INVALID`;
10. missing, short, non-finite, wrong-seed, unpaired, wrong-frequency,
    wrong-angle, and wrong-hash payloads return `INSTRUMENT_INVALID`;
11. exact boundary values pass and one representable step beyond each boundary
    fails; and
12. the result exposes the checker and contract hashes and never accepts a
    producer-supplied `detail_pass`.

No threshold may change after this self-test. A code defect requires a
committed amendment before replacement output.

## 7. Required M138 amendment

M138 commit `7fb925bf` cannot bind the final M135 interface unchanged:

1. its required M135 inputs omit all mandatory flat-sentinel roles;
2. its required outputs omit the `flat_control` record and the non-binary
   applicability/instrument statuses;
3. `arm_passes` consumes producer-supplied Boolean values instead of invoking
   the bound checker on certificate payloads;
4. a false Boolean currently participates in Phase-1 refutation, so coercing
   an inapplicable or invalid instrument to false would violate M138's own
   calibration-versus-candidate distinction;
5. it binds only the checker hash, not the comparison-contract or payload-
   generator lineage; and
6. its pinned M135 estimator hash and source range predate the mandatory-flat
   API.

The M138 amendment should require one checker payload per capture in its exact
detail ledger, invoke M135, require `DETAIL_PASS`, and route every other M135
status to `BLOCKED_DETAIL_INSTRUMENT` or `INSTRUMENT_INVALID` as appropriate.
It must add the flat roles and bind the contract, checker, generator, physical
preregistration, and physical commissioning hashes before candidate output.

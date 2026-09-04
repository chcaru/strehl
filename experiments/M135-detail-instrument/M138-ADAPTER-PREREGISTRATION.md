# M135 → M138 executable adapter preregistration

**Status:** frozen before adapter outcome generation  
**Rule ID:** `m135-m138-adapter-v1`  
**Interface schema:** `m135-m138-checker/v1`

This amendment freezes the thin executable adapter by which M138 consumes the
already-frozen `m135-detail-pass-v1` comparison checker. It does not alter the
detail estimator, the comparison statistic, or any valid-input threshold.
`comparison_checker.py` remains the sole authority for one-capture
`DETAIL_PASS`, `DETAIL_FAIL`, `NOT_APPLICABLE`, `INSTRUMENT_UNBOUND`, and
`INSTRUMENT_INVALID` decisions.

Physical binding is still `UNBOUND`. The adapter can be interface-commissioned
with synthetic, test-only bindings, but no output from that exercise is a
physical M1 value or a Phase-1 verdict.

## 1. Invocation

M138 invokes exactly:

```text
python -I m138_adapter.py --m138-commission REQUEST
python -I m138_adapter.py --m138-evaluate REQUEST
```

The adapter refuses non-isolated Python. Successful invocations emit one
canonical, key-sorted JSON object to standard output. Request-level refusal
emits no standard output, emits one machine-readable refusal object to standard
error, and exits nonzero.

## 2. Evaluation request

The exact envelope is:

```json
{
  "schema": "m135-m138-evaluate-request/v1",
  "capture_ids": ["capture-id"],
  "artifacts": [
    {"path": "payloads/capture-id.json", "sha256": "<64 lowercase hex>"}
  ],
  "binding_hashes": {
    "checker_bundle_manifest_sha256": "<64 lowercase hex>",
    "environment_manifest_sha256": "<64 lowercase hex>",
    "physical_preregistration_sha256": "<64 lowercase hex>",
    "comparison_rule_sha256": "<64 lowercase hex>"
  },
  "comparisons": [
    {
      "capture_id": "capture-id",
      "payload": {
        "path": "payloads/capture-id.json",
        "sha256": "<64 lowercase hex>"
      }
    }
  ]
}
```

Every capture ID is nonempty and unique. `comparisons` has exactly one row per
capture, in `capture_ids` order. The referenced payload is an
`m135-detail-comparison-payload-v1` object whose internal `capture_id` must
equal the row ID. Cross-capture averaging is forbidden.

Every payload reference must also appear byte-for-byte in the top-level
`artifacts` list. Artifact paths use relative POSIX syntax, may not contain
`.`/`..`, and must resolve beneath the request directory. The adapter opens and
SHA-256-verifies every declared artifact before adjudication.

## 3. Evaluation output and fail-closed mapping

The output has M138's exact common hash fields plus:

```json
{
  "detail_state_by_capture": {
    "capture-id": "DETAIL_PASS"
  },
  "detail_pass_by_capture": {
    "capture-id": true
  }
}
```

The mapping is frozen:

| Core status | M138 state | Boolean entry |
| --- | --- | --- |
| `DETAIL_PASS` | `DETAIL_PASS` | `true` |
| `DETAIL_FAIL` | `DETAIL_FAIL` | `false` |
| `NOT_APPLICABLE` | `INSTRUMENT_INVALID` | absent |
| `INSTRUMENT_INVALID` | `INSTRUMENT_INVALID` | absent |
| `INSTRUMENT_UNBOUND` | process refusal | no output map |

Thus only internally valid decisions create Booleans. A flat detailed ROI,
missing flat control, malformed payload, lineage failure, or inapplicable
capture can never become `false`. The state ledger still contains every
requested capture, so M138 can distinguish “no verdict rendered” from a valid
detail failure.

## 4. Commissioning request

The exact envelope is:

```json
{
  "schema": "m135-m138-commission-request/v1",
  "artifacts": [{"path": "...", "sha256": "..."}],
  "binding_hashes": {
    "checker_bundle_manifest_sha256": "...",
    "environment_manifest_sha256": "...",
    "physical_preregistration_sha256": "...",
    "comparison_rule_sha256": "..."
  },
  "controls": {
    "physical_null": {"payload": {"path": "...", "sha256": "..."}},
    "pre_noise_blur": {"payload": {"path": "...", "sha256": "..."}},
    "pre_noise_optical_improvement": {
      "payload": {"path": "...", "sha256": "..."}
    },
    "missing_flat_control": {"payload": {"path": "...", "sha256": "..."}},
    "hash_mutation": {
      "artifact": {"path": "...", "sha256": "..."},
      "mutated_sha256": "<deliberately wrong 64-lowercase-hex digest>"
    }
  }
}
```

All comparison controls are independently adjudicated by the frozen core.
Their frozen gates are:

- `physical_null_stays_null`: core status is `DETAIL_PASS`; the 5th and 95th
  percentiles of the information-ratio bootstrap contain `1.0` and lie wholly
  in `[0.95, 1.05]`;
- `pre_noise_blur_lowers_information`: core status is `DETAIL_FAIL` and the
  information-ratio 95th percentile is strictly below `0.90`;
- `pre_noise_optical_improvement_raises_information`: core status is
  `DETAIL_PASS` and the information-ratio 5th percentile is strictly above
  `1.10`;
- `missing_flat_control_refuses`: the core returns `INSTRUMENT_INVALID`
  specifically because a mode flat control is missing; and
- `artifact_hash_mutation_refuses`: the same artifact verifier used on real
  request artifacts rejects the deliberately wrong digest.

The output `controls` object contains exactly M138's five required names. A
false control is a commissioning failure, not a scored detail decision.
Malformed controls, an unbound instrument, or unrelated internal invalidity
cause process refusal rather than a fabricated control result.

## 5. Bound hashes and runtime

Before either mode runs, the adapter independently verifies:

1. its frozen adapter contract by canonical JSON SHA-256;
2. the frozen core contract and estimator identity;
3. the checker bundle and every file reference in it;
4. the exact Python/NumPy/platform environment and isolated-Python flag;
5. all four request `binding_hashes`;
6. the physical preregistration hash against the physical M135 binding; and
7. every request artifact.

The checker bundle contains the adapter, core checker, estimator, contracts,
binding, environment manifest, and this preregistration. A later physical
binding must update and re-freeze the bundle before any candidate output.

## 6. Predeclared adapter self-test

The self-test may create and remove scratch files only beneath this experiment
directory. It copies the frozen bundle, supplies a test-only physical binding,
and invokes that copy through `python -I`. It must exercise:

1. valid pass and valid fail decisions in one request;
2. byte-identical repeated successful output;
3. a flat detailed ROI with no Boolean;
4. missing-flat internal invalidity with no Boolean;
5. an unregistered capture with no Boolean;
6. all five commissioning controls in both reward and refusal directions;
7. request artifact hash mismatch with nonzero exit and empty standard output;
8. supplied-Boolean rejection;
9. duplicate-capture rejection; and
10. unbound-runtime refusal with nonzero exit and empty standard output.

Any change after the first behavioral execution requires a numbered amendment,
a new checker-bundle hash, and a complete rerun. Syntax parsing and environment
inventory are not outcome generation.


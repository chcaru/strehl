# M155 independent adversarial review of M138 W1 gate

- Lane: M155
- Subject: `experiments/M138-w1-gate-audit/adjudicate.py`
- Claimed repair: `6703da99168332724f179bda0499d1ebd7652d86`
- Reviewed source SHA-256: `be5e90deec8796748b3a2daa50b2aba8a708cf62481e0fc80e8f23e4e751f9b6`
- Platform: Windows_NT, Python 3.12.10, Ruff 0.15.4
- Verdict: **SEND BACK**

## Claims tested

1. Every emitted `PHASE1_GO` has complete development and holdout achieved-effect objects.
2. Every reported per-capture/per-plane power ratio is computed from the same bytes whose SHA-256 was accepted.
3. Missing, submitted, and incomplete effect material fail closed.
4. W1 GO is mechanically scoped away from scorecard M2.
5. `delta_required=UNBOUND` is explicit and is never defaulted.
6. A future bound minimum requires a physical candidate-independent pilot, adequate power at both 64 and selected sites, and observed `U_j <= (1-delta_required)^2`.
7. The self-test and Ruff pass, and the reported guard mutations are real.

## Verdict summary

The ordinary synthetic happy path emits the advertised effect object, current unbound state does not default a minimum, the M2 marker is machine-readable on that path, the bound ceiling uses the dimensionally correct square, the self-test passes, and Ruff passes. Those facts do not establish the universal claims.

Five demonstrated defects require return:

1. An unvalidated contract verdict map can turn any refusal or workflow state into `PHASE1_GO`; the CLI then exits 0. One fixture emits GO with no achieved effect, and another emits GO with development only.
2. Hash checks return paths, then JSON readers or extractors reopen those paths. A controlled legal interleaving changes a registered `R=1.5` holdout refutation into `PHASE1_GO` reporting `R=0.5` from replacement bytes.
3. A bound pilot can reuse the scored candidate and legacy outputs as its purported four independent bursts and is accepted.
4. The code computes power at 64 and selected sites but enforces only selected-site power. A binding with 64-site lower bounds near 0.58 and selected-site lower bounds above 0.98 is accepted against a 0.95 target.
5. Submitted sibling effect fields and a submitted `scorecard_m2.licensed=true` object are not in the denylist, are accepted in development evidence, and still produce GO.

The mutation result is also weak: 39 of 261 production decision guards caused a named check to go red; 222 survived. The inert control stayed green. Of 44 guards owned by commit 6703da99, 9 were killed and 35 survived.

## Demonstrated defects

### CRITICAL: contract-controlled verdict names bypass GO validation and exit semantics

`validate_contract` never fixes the six verdict strings. `adjudicate_result` copies `contract["verdicts"]` before validation (`adjudicate.py:2308-2311`), uses those strings on early-return and exception paths (`:2323-2328`, `:2420-2438`, `:2490-2503`), and calls `validate_go_output` only on the ordinary success path. `main` returns failure only when the final string is literally `INSTRUMENT_INVALID` (`:4083-4086`).

Reproduction from a frozen synthetic binding:

```text
{"reason": "[Errno 2] No such file or directory: ...no-such-result.json", "schema": "m138-adjudication/v2", "verdict": "PHASE1_GO"}
exit_code=0
```

Mapping `awaiting_holdout` to GO produced:

```text
{"awaiting_as_go_exit":0,"verdict":"PHASE1_GO","effect_phases":["development"]}
```

This directly refutes both the universal GO effect requirement and fail-closed exit behavior.

### CRITICAL: hash-then-reopen consumes unverified temporal evidence

`checked_ref` hashes a path and returns only the path (`adjudicate.py:413-436`). `checked_json_ref` then calls `load_json(path)` (`:439-446`), which opens the path again (`:143-150`). Scored source/output paths are similarly hashed in `parse_noise_cells` and then reopened by the extractor subprocess (`:1128-1188`, `:983-1032`).

`race_noise_output.py` wraps the real `sha256` only to pause after it has returned the registered digest, atomically replaces the path from another execution context, then lets the unmodified adjudicator continue. It does not forge a digest or a checker response.

Observed:

```text
{"barrier_used":true,"deterministic_interleaving":{"holdout_max_upper":0.5,"holdout_r":0.5,"verdict":"PHASE1_GO"},"registered_sha256":"c9fad36e0f820857efc6450f901e1a1090964a79d277a853c3b9e61ab99f89a9","replacement_completed":true,"replacement_sha256":"2b6aff555fe97a3c1af0873987accc3e116da16926e1864b4a7c0f97e74915f0","stable_registered":{"holdout_max_upper":1.5000000000000002,"holdout_r":1.5,"verdict":"PHASE1_REFUTED_HOLDOUT"},"stable_replacement":{"verdict":"INSTRUMENT_INVALID"}}
exit_code=1
```

The registered bytes scientifically refute holdout. Static replacement refuses. Replacement after successful hashing emits GO and reports the replacement effect. Therefore the reported effect is not bound to the registered hash.

### HIGH: the future pilot is not enforced as candidate-independent

`parse_noise_pilot` checks only uniqueness within the pilot (`adjudicate.py:1553-1650`). `verify_noise_binding` runs before the result evidence is loaded and retains no source path/hash set for comparison with scored evidence (`:1697-1811`).

The fixture reused all eight scored candidate/legacy output paths as the four pilot bursts for development and holdout. It changed only the self-declared source identity strings enough to make them unique. The bound contract was accepted:

```text
{"exit_code":0,"verdict":"PHASE1_GO","development_binding":"BOUND","required_rms_reduction":0.2,"required_power_ratio_upper":0.6400000000000001,"development_R":0.5,"holdout_R":0.5}
```

This violates the preregistered physical, candidate-independent requirement at `corrected-gate-preregistration.md:512-525`.

### HIGH: 64-site power is computed but never enforced

The preregistration requires the 95% Wilson lower power bound to reach 0.95 at both 64 and selected sites (`corrected-gate-preregistration.md:524-526`). The code computes both (`adjudicate.py:1785-1798`) but checks only `selected_power` (`:1799-1802`).

Observed full frozen-binding validation:

```text
{"at_256":{"development":0.9826831366745974,"holdout":0.9895419965959273},"at_64":{"development":0.5900640939364422,"holdout":0.5781360936462266},"binding_accepted":true,"target":0.95}
exit_code=0
```

### MEDIUM: sibling supplied-effect fields are accepted instead of refused

The denylist contains `simultaneous_confidence_interval` but not the actual output field names `simultaneous_confidence_lower` and `simultaneous_confidence_upper`; it also omits `minimum_guaranteed_rms_reduction` and `scorecard_m2` (`corrected-gate-contract.json:280-299`). Development and holdout evidence have no exact top-level key check after recursive denylist scanning (`adjudicate.py:2379-2395`, `:2440-2453`).

Observed:

```text
{"case":"supplied-unlisted-effect","exit_code":0,"verdict":"PHASE1_GO","has_achieved_effect":true,"emitted_m2_licensed":false}
{"case":"supplied-m2-claim","exit_code":0,"verdict":"PHASE1_GO","has_achieved_effect":true,"emitted_m2_licensed":false}
```

The submitted values are ignored rather than used, but the explicit claim was that supplied effect evidence fails closed. It does not.

## Mutation audit

### Counting rule

I counted statement-level executable production decisions: every `if`, conditional expression, and comprehension filter in the adjudicator and CLI. I excluded fixture builders and `run_self_test` itself so the audit mutates the subject rather than its oracle. This yields 261 guards: 255 `if`, 3 conditional expressions, and 3 comprehension filters. Including helper/test decisions and 53 self-test assertions gives 317 syntactic predicates.

Each production guard was replaced independently with `(False and (original_expression))` in a temporary copy. Every replacement had a unique full-line anchor with anchor count exactly one; missing or duplicate anchors hard-failed. Mutants were compiled directly from current source bytes, not from `.pyc`. The exact 101-tau self-test grid was retained. Unchanged fake checker/extractor subprocess results were cached only by the hashes of the executable, request, and every artifact byte string referenced by that request. Exact stock-process spot checks covered IDs 119-125 and 168-173 and matched the full audit outcomes.

### Required numbers

1. Total production guards/predicates: **261**.
2. Guards mutated: **261**.
3. Mutations producing a specifically named red check: **39**.
4. Inert control stayed green: **YES**.

Coverage: **39/261 = 14.94%**; **222/261 survived**. Repair-owned subset: **9/44 = 20.45%** killed.

The implementer-reported narrow mutations are genuine: invalid-plus-Boolean, unknown-state, and missing mandatory GO effect each exited 1, and the inert edit exited 0. Adjacent guards were not covered. Exact examples:

```text
M135 IDs 119-125: 4 killed, 3 survived; inert=true
effect IDs 168-173: 1 killed, 5 survived; inert=true
```

Every killed mutant is tied in `mutation-results-labeled.json` to a concrete `run_self_test` assertion line, a concrete initial refusal reason, or the exact completion-banner check.

## Other claims

- **Self-test and Ruff:** confirmed. Self-test exited 0 with its complete banner; Ruff printed `All checks passed!` and exited 0.
- **Canonical missing/supplied/incomplete evidence:** confirmed for a missing arm noise reference, a submitted `achieved_effect`, and a missing R plane. All emitted `INSTRUMENT_INVALID` and exited 2. Missing holdout emitted only `AWAITING_HOLDOUT`, with development effect, and exited 0.
- **Current unbound minimum:** confirmed. The checked contract has `UNBOUND` plus null requirement/pilot/value. Injecting `required_rms_reduction=0.0` emitted `INSTRUMENT_INVALID`; it was not treated as a default.
- **Bound decision ceiling:** confirmed. The code and output use `(1-delta_required)^2`; delta 0.2 produced power-ratio ceiling 0.64. This is dimensionally coherent because R is a temporal-power ratio and RMS ratio is its square root.
- **M2 structure on the ordinary path:** confirmed. GO carries `scorecard_m2.licensed=false` and `SHIPPING_COMPARATOR`; changing the output to true is rejected by `validate_go_output`. No downstream executable consumer of `PHASE1_GO` was found. The verdict-map defect nevertheless permits emitted GO objects that bypass this validator.

## Commands and outputs

Key commands are reproduced in the lane response. Reproducible builders and probes are under `experiments/M155-w1-review/`. `capture_fixture.py` first creates the synthetic frozen fixture from the production self-test without editing M138 files.

## Gaps

- The checked contract is still `DRAFT_PENDING_THIRD_INDEPENDENT_REVIEW`; there is no real frozen corrected-gate result. All GO fixtures are synthetic.
- Thirty-two uncontrolled atomic-replacement attempts on Windows yielded only the registered verdict or hash refusal. The deterministic post-hash interleaving proves exploitability, but this review did not estimate the natural race frequency.
- The same hash-then-reopen form exists for checker/extractor executable paths, bundle JSON, cost JSON, and other artifacts. I demonstrated temporal request/output consumption, not a separate executable sentinel payload.
- No Linux/macOS host was available.
- Per instruction, I did not run M12, Cargo, or decode RAW files.


# M180 detail-route adjudication — preregistration

Status: **FROZEN BEFORE FIRST EXECUTION**

## 1. Question and scope

This lane asks whether the M164/M168 opening supports a presently admissible
detail route. It does not invent a new score, relax M167, or read any capture.
The registered disposition is:

```text
UNDECIDED_REFERENCE_ROUTE_OPEN_PHYSICAL_UNMEASURED
```

if and only if all of the following are true:

1. the output-only opposite-label collision reproduces;
2. M164 and M168 retain their assumption-qualified wording;
3. a featureless target is blind to DC-preserving blur and USM;
4. a marginal generative prior cannot distinguish a faithful draw from an
   independent hallucinated draw, while an independent reference can;
5. the committed M135 truth-reference estimator retains its planted defect,
   planted improvement, blur, USM, averaging and flat-control results;
6. the committed M164 reference-dominance gate passes a legitimate plant,
   rejects a weak cell without compensation, and catches the
   improvement-shaped common-mode defect;
7. the M167 blinded canary remains rejected, A6 remains unavailable, and the
   frozen M167 interface still requires a separately preregistered
   reference-bearing schema;
8. the archive-only reference route remains closed; and
9. the physical reference chain and production dominance manifest remain
   uncommissioned/blocked.

Passing establishes an open **conditional** route, not an admitted
instrument. Any missing source, malformed artifact, changed source sentence,
or failed predicate is RED.

## 2. Registered verification checks

`verify.py` must emit these 23 named checks:

1. `collision_operator_valid`
2. `collision_labels_opposite`
3. `featureless_blur_usm_blind`
4. `marginal_prior_collision`
5. `reference_breaks_collision`
6. `m164_output_only_scope`
7. `m168_distribution_free_scope`
8. `m135_estimator_commissioned`
9. `m135_blur_defect_direction`
10. `m135_improvement_direction`
11. `m135_usm_not_rewarded`
12. `m135_postblur_transfer_veto`
13. `m135_averaging_veto`
14. `m135_flat_common_mode`
15. `dominance_legitimate_moves`
16. `dominance_no_compensation`
17. `dominance_improvement_shaped_defect`
18. `m167_canary_bites`
19. `m167_a6_fail_closed`
20. `m167_reference_schema_pending`
21. `archive_route_closed`
22. `pchip_is_enabler_only`
23. `physical_route_uncommissioned`

The headline disposition is derived from the conjunction. `verify.py` must
read the primary JSON artifacts and independently execute the finite models;
finding numbers in this Markdown file does not count.

## 3. Registered mutation commission

`commission.py` will copy inputs into lane-local `work/`, never mutate a live
source, and plant exactly one full-line replacement per case. It must hard
error unless the old line occurs exactly once. One substantive mutation
targets each registered check. A mutation is killed only when:

1. `verify.py` exits nonzero;
2. the named target check is false; and
3. the emitted disposition is not the registered baseline disposition.

The inert mutation changes only `inert_note` in `model-fixtures.json`; it
survives only if all 23 checks and the disposition remain unchanged.

Counts are reported separately:

- checks run;
- substantive mutations planted;
- substantive mutations killed; and
- inert controls survived.

No wall-clock predicate is permitted.

## 4. Frozen finite model

`evidence/model-fixtures.json` defines:

- the M168 five-sample impulse and row-stochastic smoother;
- opposite latent-world labels;
- a featureless vector;
- faithful and independent-hallucination Bernoulli marginals; and
- whether the external reference shares the latent draw.

The fixture is explanatory evidence only. It is not a candidate metric or an
M167 admission packet.

## 5. Decision boundary

The registered baseline remains `UNDECIDED`, rather than `ROUTE_FOUND`,
because estimator-level synthetic success cannot substitute for:

- a frozen sufficient complete-`S` scored-path reduction;
- physically measured per-cell reference information/transfer dominance;
- disjoint calibration and common-mode controls;
- a frozen M167 reference-bearing blinded interface; and
- independent A6 capability isolation.

It is not `ROUTE_CLOSED` because an independent reference changes the joint
observation law and therefore removes the specific M164 collision on its
qualified, powered support.


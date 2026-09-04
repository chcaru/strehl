# M164 M2 candidate contract

Status: **IMPLEMENTATION CANDIDATE; INDEPENDENT M167 ACCEPTANCE REQUIRED**

`instrument.py` is the M164-owned candidate implementation. The
`commission.py` battery is author-generated development evidence only. It is
not the acceptance authority and must not be used to waive, replace, tune, or
reinterpret M167's frozen battery.

## Public API

```python
from instrument import ArmInputs, Admission, evaluate_arm, compare_arms
```

Each `ArmInputs` array has shape `[sites, cells]` and may contain real or
complex linear-light coefficients:

- `reference_a`, `reference_b`: independent M1 truth-reference halves on the
  coded target;
- `detail_output_a`, `detail_output_b`: independent candidate-mode output
  halves on the same coded sites;
- `flat_reference_a`, `flat_reference_b`: independent truth-reference halves
  on concealed featureless sentinels;
- `flat_output_a`, `flat_output_b`: corresponding candidate-mode output
  halves on those sentinels; and
- `frequencies`: one frequency in cycles/native pixel per cell.

`Admission` is mandatory. A numeric arm result is refused unless M1 is already
admitted, the M165 pattern map and external PCHIP tone witness passed, repeats
are independent, the complete M2 band is present, and the target has frozen
nonperiodic lineage.

`compare_arms` additionally requires a declared M164 verdict. A fire returns
`INADMISSIBLE_COMMON_TRANSFER`; a missing or unknown verdict fails closed.

## Direction

`evaluate_arm` reports:

```text
quality_score = -mean(log(EIN(k)))
```

Higher is better. `compare_arms` reports:

```text
Q_EIN = exp(mean(log(EIN_candidate(k)/EIN_comparator(k))))
```

Lower is better. They are the same ordering.

The candidate must return no number on a flat-as-detail input. A common
nonzero per-cell postfilter leaves the score unchanged. M167 decides whether
those and all other required adversarial properties actually hold.

## Scope

This coefficient-level API is intentionally separate from image extraction.
The production extractor must be frozen before score data, must cover the
complete `0.15–0.35 cyc/native px` band and all channels, and must bind both
arms to the same sites, references, tone witness, calibration lineage and
mode settings.


# M135 independent verification

Status: **VERIFIED — no defects reported**

A read-only `ultracode:ultra-verifier` independently inspected the M135
report, source, freeze history, and artifacts.

It ran:

```text
python experiments/M135-detail-instrument/commission.py
python experiments/M135-detail-instrument/audit_report.py
git diff HEAD -- experiments/M135-detail-instrument/ docs/research/M135-detail-instrument.md
git status --short -- experiments/M135-detail-instrument/ docs/research/M135-detail-instrument.md
```

It also independently:

- reproduced postfilter invariance at machine precision;
- checked all 22 final gates;
- exercised all missing-lineage paths;
- confirmed all 32 permutation maps were distinct derangements;
- checked the freeze commits were path-scoped;
- checked the historical and current FRC rulings;
- compared all `RESULTS.md` values with `commission.json`;
- sampled more than 15 verbatim source quotations and all citation ranges.

Verdict: the mathematics, code, challenge outcomes, citations, path scope, and
conditional feasibility wording were verified. No high-confidence defect was
reported.

This verifies the estimator-level work. It does not replace the physical
reference/extraction commissioning required before M1 admission.

# M138 adapter amendment 3 — verify before local import

**Frozen before rerun:** yes  
**Affected file:** `m138_adapter.py`

Post-pass source review found an ordering defect in the adapter bootstrap. The
adapter hash-verified its bundle before processing either M138 mode, but Python
had already executed the sibling `comparison_checker.py` through the
module-level import loader. M138's outer adjudicator verifies the complete
bundle before launching the adapter, so its registered path was protected, but
the standalone adapter did not independently provide the verification order
claimed by its preregistration.

This amendment defers both the local core import and NumPy import until after:

1. the adapter contract's canonical hash is checked;
2. every checker-bundle member is opened and SHA-256 verified; and
3. the runtime environment is matched using standard-library package metadata.

Only then is the already-verified core loaded. The request schema, output-state
mapping, commissioning bars, core source, and all valid-input arithmetic are
unchanged.

The amendment-2 25/25 result is preserved as
`m138-adapter-verification-run3-pre-bootstrap.json`. The complete 25-check
battery and byte-stability replay must run again under the amended bundle.

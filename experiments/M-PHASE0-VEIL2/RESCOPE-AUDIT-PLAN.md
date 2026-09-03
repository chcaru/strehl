# M-PHASE0-VEIL2 re-scope audit plan

**Frozen:** 2026-09-02, after preliminary corpus discovery and before formal
scoring. The exploratory reruns that located missing predecessor artifacts are
not scored below.

## Question and bias

Does the evidence cited by `2026-09-phase0-triage.md` establish proposal A2's
stack-induced base/coarse pedestal mechanism strongly enough to license a
default-off Rust prototype?

**Bias direction:** toward `SURVIVES_AUDIT` and building. The owner explicitly
wants phase 0 to pay out in Rust, and A2 is plausibly high value. This bias can
only make weak predecessor evidence look sufficient, so every gate below is
fail-closed.

## Evidence and fixed gates

The audited claim is the complete causal chain: two physical depths share a
pixel; the merge selects detail from one; its base/coarse reconstruction comes
from the other; changing that reconstruction removes the pedestal without
merely changing tone or sharpness. A commissioned two-peak classifier alone
does not commission that chain, and reading `BaseBand::Mean` in source does not
measure its causal contribution.

All seven gates must pass:

1. **Direct mechanism:** retained artifacts or reproducible inputs must link the
   selected detail, base/coarse coefficients, and master pedestal. An
   intervention on the nominated component or an equivalent causal contrast is
   required.
2. **Commissioning:** the mechanism instrument—not merely a focus-curve
   classifier or drift helper—must have a positive control, null, and planted
   sign/wrong-component defects that all went RED.
3. **Cancellation resistance:** at least one load-bearing predicate must use
   fixed external truth or independently generated data and must not share the
   treatment code it checks.
4. **Reproducibility and standing:** real-data artifacts must be available or
   reproducible now; no retraction, explicit limitation, or newer commissioned
   result may invalidate the inference.
5. **Tone/contrast exclusion:** the conclusion must be invariant to strictly
   increasing intensity remaps, including per-image positive affine scaling,
   or be read by an ordinal instrument. A sign/class flip is failure.
6. **Defocus exclusion:** a comparable single-depth defocus plant or real null
   must stay quiet. Merely observing two response peaks is insufficient.
7. **Diffraction exclusion:** the A2 endpoint must be separated from aperture
   scaling on a real aperture ladder; citing a common aperture or a diffraction
   study of another endpoint is insufficient.

## Decision

`SURVIVES_AUDIT` requires 7/7. Any failure yields
`STOP_DO_NOT_BUILD`; Part 2 is then prohibited by the re-scope order. The audit
will report every gate, not stop recording after the first failure.

## Formal record

`src/rescope_audit.py` will read the cited corpus and machine records without
importing the predecessor or VEIL2 producer modules. It will record source
commit order, artifact availability, independently derived VEIL2 arithmetic,
the monotone positive-gain witness, and predecessor rerun exit/output.

`src/check_rescope_audit.py` will independently validate the record and
commission itself with in-memory plants for a false all-pass verdict, a hidden
missing artifact, a tone-flip suppression, and a reversed commit order.

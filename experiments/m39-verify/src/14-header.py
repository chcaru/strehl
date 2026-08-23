import io
p = r'C:\dev\blog\death-of-software\projects\strehl\docs\research\M39-verify-detail-metric.md'
lines = io.open(p, encoding='utf-8').read().split('\n')
assert lines[0].startswith('# M39'), lines[0]
assert lines[6].strip() == '---', repr(lines[6])
header = """# M39 - independent verification of the M38 detail metric

**Verifier:** independent agent. Not the author of `merge_cmd.rs`, `merge.rs` or M38.
The brief was to try to FALSIFY the claims, not to confirm them.
**House rule:** every statement below is labelled MEASURED / DERIVED / ARGUED.
**Evidence:** `experiments/m39-verify/src/01..13-*.py` -> `experiments/m39-verify/out/*`.
No existing repo file was modified; this file and `experiments/m39-verify/` are the only
things written.

## Verdicts at a glance

| Claim | Verdict | One-line reason |
|---|---|---|
| **A** noise confounds `mean\\|grad\\|`, same sign as blur | **CONFIRMED**, 2 qualifications | Demonstrated both directions on real data: argmax raises `mean\\|grad\\|` +5.04% on a **flat** ROI; the plain mean drops it -60.3% with zero blur. But the correction removes only the *model-predicted* noise, and it is an RMS. |
| **B** -45% -> -4.6% / -3.6% | **CONFIRMED**, wider error bar | Independent numpy re-implementation reproduces **every cell of both 6-gate tables to 4 dp**. But the figures carry a +/-2 pp band from the noise-model scale, which M38 does not state. |
| **C** `2*s_i^2 + s_{i+1}^2 + s_{i+w}^2` is exact | **CONFIRMED** | Derived from scratch, same coefficients; 4e6-trial Monte Carlo agrees to 0.2% while three sum-preserving rivals miss by 24-39. One precondition (pixel independence) is unstated and violated by the roadmap. |
| **D** fact 24 carries the same confound reversed | **CONFIRMED in direction**; 1.253x **COULD NOT VERIFY** | argmax raises `m2` +6.42% / +5.09% and raises noise 1.0739x, measured together. But 1.253x belongs to M2's `ring(1,3)`, not the shipped Tenengrad; the right factor for today's operator is ~1.07x, making the noise share ~22%, not ~83%. |

**Biggest single finding:** the positive control M38 never ran. The corrected metric reads
the *known-bad* plain 22-frame mean at **-48.4% / -13.0%** against the gated merge's
**-4.6% / -3.6%** (§5.1). Invariant 2 does discriminate. Raw `m2` does not (-45.5% vs
-60.3%, a factor of 1.3).

**Biggest single defect:** the correction leaves the selection-induced excess noise in
place, and I show it crediting a **flat** ROI with **+35.5% detail** (§5.2).
"""
out = header.split('\n') + lines[6:]
io.open(p, 'w', encoding='utf-8', newline='\n').write('\n'.join(out))
print('ok, lines =', len(out))

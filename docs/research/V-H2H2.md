# V-H2H2

Lane report. Measurement and falsification of the pyramid merge's fine-scale
behaviour, plus commissioning of the instruments used to judge it.

Binary for every number below unless stated otherwise:
`632987418AD84E58B66F373FD993F18A8846F03D612E65E6F043BCBEF9E1C1B8`,
`strehl 0.0.0 (b7bbaaa2e2af)`. No `--auto-exposure` in any arm.

## 1. The confidence exponent at depth. MEASURED.

Subject `bee-1-cpl`, N=299, `--srgb`, clip 0.0411 to 0.0425 percent on all four
masters. Scored with `experiments/ORCH-drift-check/contrast_ms.py` and the
rescale-correction bracket in `experiments/V-H2H2-MOTTLE/corrected.py`.

Acuity is read at 0.17 to 0.25 cyc/px. On this subject that band is qualified
SIGNAL: the measured signal/noise boundary is 0.48, and all twelve fine
sub-bands pass with the worst at R = 3.63.

| arm | flat 0.25-0.50 | acuity EDGE 0.17-0.25 | null coarsest EDGE |
| --- | --- | --- | --- |
| S100 | 0.8015 | 0.9939 | 1.0016 |
| S1000 | 0.8052 | 0.8854 | 1.0040 |
| K (gate floor 4x) | 0.0937 | 1.0028 | 1.0013 |

All three nulls sit inside the 0.005 tolerance, so all three comparisons are
valid. Both exponent strengths remove the same flat-site amplitude while S1000
costs roughly nineteen times the acuity: the benefit saturates by strength 100,
the cost does not.

The cost is measured. The benefit is not quotable, because this subject
qualifies the flat band as signal too, so a reduction there cannot be called a
grain win without a flat-site-restricted qualification that nobody has run.

## 2. I falsified my own claim. MEASURED.

I had argued the exponent was structurally dead and called that argument
independent of band, subject and depth. The mechanism is that `select_weight`
returns zero on non-positive excess before it consults the exponent, so wherever
the gate has already reduced the candidate set to one frame the exponent cannot
act.

Pre-registered before rendering: flat effect at or above 0.95 at every strength.

Measured: 1.0019 at N=79, and 0.805 at N=299. The falsifier fired. At N=299 many
more frames clear the gate in a flat region, the candidate set does not collapse,
and the exponent has authority it lacked shallow. The mechanism survives; the
scope claim does not, and is withdrawn.

## 3. `contrast_ms.py` fails a planted null. MEASURED.

`experiments/V-H2H2-MOTTLE/commission_ms.py`, four planted arms with answers
fixed before the run.

| arm | true answer | measured | |
| --- | --- | --- | --- |
| gain, B = A x 1.0327 | 1.000 every band | 1.0010 | pass |
| offset, B = A + 16.69 DN | 1.000 every band exactly | 0.9696 every band | FAIL |
| blur, sigma 1.0 | below 1, worse fine | 0.4757 / 0.6330 / 0.9857 | pass |
| unsharp 0.5 | above 1 | 1.3290 / 1.2189 / 1.0086 | pass |

Cause: the instrument computes a rescale from the median ratio and multiplies
B's pixels by it, which scales every high-pass amplitude identically. A DC
offset is annihilated by every filter in the bank, so the true answer is exactly
1.000 at every band; the instrument returned its own rescale factor instead. The
bias enters every band including the one used as the instrument null.

The inverse is exact, ratio divided by scale, verified on the offset arm. Real
arms differ by both a gain component and a non-gain component, so the truth is
bracketed between raw and corrected. Report both ends, never one.

## 4. Polarity audit of my own harness. MEASURED.

`experiments/V-H2H2-MOTTLE/commission_grid.py` runs `griddiag.py` through its
shipped entry point against copied sources. Sensitivity 6 of 6, specificity 2 of
2, eight arms all correct. Arms cover reversal, deletion, and innocuous prose
that must be rejected.

It exposed one real hole. The claim that the full-resolution planes are built,
sampled and dropped was checked by confirming the locals are declared.
Declarations do not forbid escape. What forbids escape is the return type, which
is a scalar. The conclusion was true but untested.

`potency_grid.py` is the control that makes that six of six mean anything: it
takes the harness as committed before the fix, changes no check, and runs the
identical mutation. Pre-fix reads green and is blind; the worktree reads red and
catches; both read green on clean input.

The mutation guard also refused an ambiguous plant on its first real use, because
the target expression occurs twice in the file. An inert plant and a dead
instrument produce the same green.

## 5. Byte-freeze coverage of the shipping backend. VERIFIED, NOT MINE.

The orchestrator asked me to state this cleanly. It is not my finding and I did
not establish it; recording what I verified so the claim rests on evidence rather
than on attribution.

Measured in `crates/strehl-cli/tests/byte-freezes.tsv`: three non-comment lines,
being one header and two data rows. Rows naming the pyramid backend: zero. Rows
naming the estimator backend: one.

The harness states it itself. `byte-freeze.rs:522` says both rows pass
`--merge estimator` explicitly. Lines 547 and 548 say the harness hardcodes
`--merge estimator` and that a given variable exists only on the pyramid backend,
"which is `DEFAULT_MERGE_BACKEND`". Line 574 anticipates "the day a pyramid row
is added".

So the suite freezes bytes only on a backend that is not the default. The claim
is true. It was also known to whoever wrote those comments, so it is an
acknowledged gap rather than a discovery.

I did not modify this file at any point. Its last committing lane was
BUILD-GATE-PRINT.

## 6. Per-subject band qualification. MEASURED.

The signal/noise boundary is a property of the subject, so the direction of a
flat-band reduction is not fixed. `experiments/V-H2H2-MOTTLE/requalify.py` maps
the scoring bands onto measured sub-bands by overlap and refuses any band that
straddles the boundary rather than rounding it.

Boundary for `112MSDCF` is 0.20, from thirty tiles with a far-8 control agreeing
everywhere at or above 0.05. That makes the correct acuity band 0.08 to 0.17 on
that subject, where it qualifies at R = 5.255, and not the finer band.

On `bee-1-cpl` and `dry-erase-marker-head-cpl` every scoring band qualifies as
signal, so there is no qualified noise band and the two-sided criterion collapses
to the acuity side alone.

The asymmetry that governs which claims transfer: a whole-frame noise result
transfers to flat sites a fortiori, because flat sites are less structured than
average. A whole-frame signal result does not transfer to flat sites at all.

## Kept artifacts

None. Every scratch directory for this lane has been deleted and every number
cited above is in this report as text. The binary is reproducible from
`b7bbaaa2` and every render is reproducible from the committed scripts.

## Unfinished

Not started, and the first thing to pick up: the seven new stacks with thinner
focus slices. Thinner slices raise per-frame focus contrast, which is the exact
term deciding whether the gate collapses the candidate set to one frame, which is
the mechanism behind the N=79 to N=299 reversal in section 2. Command is
`experiments/V-H2H2-MOTTLE/depth.ps1` with the stack path changed. Hypothesis:
the exponent's flat-region authority shrinks as slices thin, and the N=299 result
does not survive a step-1 stack.

Also open: a flat-site-restricted band qualification on `bee-1-cpl`, which is what
decides whether section 1's flat column is grain or signal. My spectral check of
the absolute flat column leans noise at the finest pair, 1.93 against 2.36 for
white noise and 1.34 for inverse-square structure, but two of five adjacent pairs
lean the other way. Indicative, not decisive.

## Unverified

The return-type check in section 4 was written, fixed and controlled by one
author, me. `corrected.py`'s argument handling was repaired after it was found
ignoring its inputs, and that repair has no polarity audit. `requalify.py`,
`commission_ms.py`, `twoside.ps1` and `rescore_ms.ps1` have never been
polarity-audited at all.

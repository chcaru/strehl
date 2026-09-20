# Independent convergence interpretation

MEASURED by root in convergence-2; independently reviewed from saved scores,
receipts and histories without fitting, rendering or model edits. The original
screen remains rejected. All three final states were measured successfully,
but every arm still fails the combined fixed quality/prediction requirements.
Score SHA256: `7af5c79a280684c4cabe90087d081464fdda6b1250ee07fe07b95b67afb48516`.
The actual command is retained in convergence-2/invocation.json; process wall
time is9.016s, distinct from the internal7.031s diagnostic time.

The fixed recipe was followed. Training indices remain0,1,3,4,5,7,8; the model,
controls and original observations/checkpoints remain bound unchanged. Actual
evaluation counts are4,105,105 for flat, far-only and layered, within the200 cap;
optimizer iterations are1,100,100. Gradient-storage conversions are live at
8,105,210, with exact logical-value assertions throughout. All returned states
are accepted finite states, and final objectives describe the actual returned
parameters. Convergence-1's zero-iteration storage refusal remains separate.

| Arm | RGB truth RMS before -> final (DN) | Bright held-out RMS before -> final (supplied sigma) | Final parameter-gradient maximum |
| --- | --- | --- | --- |
| Flat/two-layer | 8.675 -> 8.683 | No bright samples | 0.0000791 |
| Far-only/far-only | 291.117 -> 187.396 | 9.466 -> 4.891,43 samples | 0.01518 |
| Layered/two-layer | 235.112 -> 209.057 | 4.280 -> 2.826,41 samples | 0.04650 |

The far-only row compares the same one-layer arm before and after continuation.
The scorer's `original_case_quality` field contains the old two-layer case
summary, so its247.56DN must not replace the291.12DN historical one-layer
reference. This correctly specified one-layer improvement shows that unfinished
optimization contributed to the original bright error without needing uncertain
layer visibility as an explanation. Its bright residual nevertheless remains
above1.75sigma.

Layered core/ridge/crossing RGB errors improve from1064.73/473.94/848.92 to
931.73/419.08/747.27DN. All original image truth bars still pass; the protected
ridge components are0.938–0.989. Glint components1.032–1.053 are overshoot,
not recovery of more than100% of real detail. The component lower-bound checks
cannot penalize that direction; absolute RGB truth error supplies the necessary
countercheck. Held focus0.25 global RMS1.128 conceals the failed bright subset;
focus0.75 has no bright samples and slightly worsens globally to1.295. Neither
held-out view has censored samples. These observations do not establish broad
saturation recovery or selective rejection of physical-model mismatch.

Both structured arms remain nonstationary at the declared1e-4 maximum-gradient
bar. Far-only objective falls6.03481->5.80175 as data NLL decreases and prior
increases: a realized data/regularity tradeoff, not proof of the optimum's bias.
Layered objective falls7.71157->6.99647, with data and prior both still falling
in the final closures. Its final gradient maximum is actually larger than its
starting0.03386. A lower objective or better image therefore does not justify
calling the remaining bright error unavoidable prior bias, physical error, or
converged failure. The fixed iteration budget ended with useful descent left.

Flat is different: after one step it satisfies the declared raw-parameter
tolerance, yet RGB/chroma error8.683/12.357 remains well above mean6.018/8.368
and the restricted far-only inverse5.606/7.776. The tiny continuation worsens
both errors while lowering the objective by0.0000101; held predictions remain
near1sigma. Thus the actual stopping predicate plus good forward prediction
does not protect the pinhole output. This supports investigating latent
compensation/output regularity rather than expecting this continuation to cure
flat noise. It does not prove a global optimum, exact nullspace, or stationarity
in radiance coordinates: the predicate is parameterization- and tolerance-bound.
The earlier measured opposing sheet errors remain relevant evidence, not a
unique attribution to opacity.

**One bounded causal followup:** use the existing flat observations and saved
two radiance sheets, fix alpha to the known constant truth0.35, and optimize
only the sheets under the unchanged likelihood, image priors and fixed solver
budget. Record the conditioned starting output as well as the final output;
retain the original flat RGB/chroma and prediction bars. This single oracle
ablation removes spatial opacity freedom without adding a stronger prior or
changing the data. Improvement would implicate that freedom; persistent noise
would retain radiance ambiguity/output regularity as the next question. It is
a mechanism diagnostic, not an automatic reconstruction or admission test.

The independent64-versus1024 pupil adequacy failure still blocks real-RAW
application. These are known-optics generated reconstructions, not comparisons
against the canonical full stacker and not evidence of SOTA performance.

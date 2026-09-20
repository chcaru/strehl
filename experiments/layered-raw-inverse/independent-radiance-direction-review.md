# Independent radiance-direction source review

SOURCE-REVIEWED, not executed by this reviewer. No blocking issue remains for this bounded diagnostic. It can distinguish a locally opposed, truth-improving radiance direction from remaining descent at the saved state; it cannot establish an optimum or qualify a reconstruction for photographs.

The probe restores the exact accepted visibility-1 layered checkpoint and checks its saved fields, pinhole, and objective. Near radiance, far radiance, and the fixed alpha buffer remain unchanged. Only scalar `t` is differentiated. The proxy adds `t * (D / dn_scale)` to normalized far radiance, preserving the original fields exactly at zero while representing a physical-DN direction in real arithmetic. Nonfinite or negative perturbed radiance refuses; no clamp changes the experiment. The unchanged likelihood uses only the seven training observations, streamed individually. Data and original-prior derivatives are kept separate, with no optimizer or held-out fitting input.

The independent export correctly divides the frozen delivered glint template by `1-alpha` once to obtain the FAR-layer direction. Supplying the delivered template directly would have applied transmission twice. The second direction is this same far-layer vector shifted exactly 20 pixels right with zero fill. Its interpretation is descriptive: a displaced perturbation need not worsen an imperfect reconstruction. Neither direction is selected from the fitted image.

The scorer checks actual saved positive and negative images against the literal delivered increment `base +/- .001 * (1-alpha) * D`, using the declared gamma-16 f32 roundoff bound. This supplements derivative consistency with a check that sign, amplitude, units, and transmission reach the saved image. Base output must equal the checkpoint exactly. Existing truth scores and components are evaluated on the saved images; no new quality threshold is inferred from the arithmetic bound.

Autograd and centered finite differences are compared separately for data, prior, and total at the fixed step and tolerance. A disagreement or an unresolved near-zero sign must remain inconclusive. A positive objective derivative is evidence against this particular direction only when its actual positive image improves independent truth. Lower error and a component closer to one should be distinguished from merely increasing component amplitude. A supported adverse prior derivative would identify local prior pressure, not prove that it alone explains the full reconstruction error or that the unfinished solver has reached an optimum.

The final wrapper passes the required `--source` argument, and both plans agree with that CLI. It prepares directions before probing, binds all sources/checkpoint inputs, checks immutability between stages, and runs the scorer afterward. No author or reviewer execution is claimed. Root owns the bounded run; real-photo admission remains false.

Reviewed SHA256 bindings:

- `radiance-direction.py`: `a9d5039f0b5aa905e859a23b3a652040e2fec4c3f843440e7054b03533eff209`
- `radiance-direction-plan.md`: `ea3762b33819842fe380f1f75e67be3b6752a6924d8cee04fdbde3a4f4b842db`
- `radiance-direction-controls.py`: `358a7f3c0edc4b9255a01d4a7ea9b74df50cdd72af7bb88b026974d5228ffa6b`
- `radiance-direction-independent-plan.md`: `6527c86fabe0da005afe1d78ac01fab2a7b5e9f11d906480532114318d313e04`
- `run-radiance-direction.py`: `a3a0a585266dd23b55017f8109dbb7e23e82ae3ad33f0197687b0fe2fdfda9b6`

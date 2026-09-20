# Unchanged-objective numerical continuation

Prospective, 2026-09-19. The fixed160-step first screen remains failed. This
separate diagnostic distinguishes unfinished optimization from the unchanged
model/prior's limitations; it is neither an optimizer/quality sweep nor renewed
optical or photographic admission. Author writes only this plan and
`convergence.py`, executes nothing and does not score the output.

Restore exactly three retained states, in this fixed order:
`screen-1/output/flat/two-layer`, `far-only/far-only`, `layered/two-layer`.
Read original saved `observations-u16.npy`; retain the model/configuration,
training indices0,1,3,4,5,7,8, original injected noise, priors, support, CFA and
oracle geometry unchanged. `torch.load(weights_only=True)` loads parameters
strictly; reconstructed fields must be bit-equal to the old saved arrays.
Initialization is the existing training-only disabled fit, then overwritten by
the saved checkpoint. A facade refuses held-out or non-scalar input reads.
File hashes may read immutable bytes for provenance; those bytes do not enter
initialization, objective, optimization or stopping.

One L-BFGS invocation per arm: learning rate1, strong-Wolfe line search,
max_iter100, max_eval140, history10, tolerance_grad1e-4, tolerance_change1e-9.
No retries, restarts, alternative schedules or best-truth/best-heldout choice.
Backpropagate one current original observation at a time, in the frozen source
order, then the existing prior once. The optimizer receives the sum of the same
per-frame mean losses and prior; gradients remain f32. A detached f64 scalar
reports their sum to the line search without altering derivative arithmetic.

Evaluate the loaded state independently: old Adam history159 describes the
pre-final-update state, not this checkpoint. Independently evaluate the actual
returned state after L-BFGS as well. These count in a hard200 actual-evaluation
cap; at most199 may occur before the reserved final monitor. Preserve every
successful closure's data NLL, prior, total, raw parameter gradient maximum/L2
and elapsed time, plus optimizer n_iter/func_evals. Failed closures are errors,
not passing omissions; attempted and completed evaluations are counted separately.
A cap/line-search/nonfinite failure is numerical refusal;
the final state is then explicitly not certified as an accepted line-search
iterate. Never select another state using truth.

Only final max-absolute gradient<=1e-4 at an accepted finite state is called
`stationary_gradient`, explicitly in normalized softplus/logit parameters.
Small change, small step, an iteration limit or a lower objective with a larger
gradient is not convergence.
Normal returns with larger gradients are `nonstationary_return`; optimizer
counts do not silently imply which internal stopping condition fired.
No latent uniqueness, radiance-space stationarity, physical calibration or
output-quality claim follows even from the gradient predicate.

Save each final state, reconstruction and receipt under the same case/arm
subpaths. Generate expected-CFA predictions for held-out optical indices2/6
only after optimization and final monitoring, without reading held-out values.
The independent scorer owns all later truth/held-out comparisons. Bind model,
original controls/design, checkpoint receipts/states/arrays and original u16
files before/after; changes refuse completion. Root owns a bounded process run,
targeting180seconds for the three arms, and retains a timeout as failure.

Command for root (not run by author):
`python convergence.py --source screen-1/output --out convergence-1/output`.
Use the experiment directory as working directory and the previously bound
CUDA Python runtime. This command never reads camera RAW files or renders a
full photograph.

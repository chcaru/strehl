# Independent constructive source-weight check

Prospective, 2026-09-26. The seven retained learned-band-guide test cases are now
explicitly fitted to their known truth. They are no longer held-out validation.
Only nonnegative AC source weights change (exponential underflow may give zero);
all four original coefficient planes,
terminal Mean, finite synthesis, InputRange hull and final MHC remain fixed.
A successful feasible reconstruction demonstrates headroom for this consumer.
An unsuccessful finite optimization proves no ceiling and does not identify the
mean base, hull, features, optimizer or predictor as the cause. Neither outcome
authorizes another photograph or a learned-model retry.

Before oracle fitting, the same fixed 1024-step/.03 Adam solver (epsilon1e-15), zero-logit start
and final-only output must recover two known-feasible prescribed-weight targets:
retained Flat N5 first, then Curved N9. Each initial full-RGB MSE must exceed
1e-12 and final MSE must be at most .10 of initial. Targets are actual retained
prescribed consumer outputs, not sharpness scores or manufactured inverse labels.
The independent checker replays saved final weights through the frozen consumer;
complete CFA/RGB parity bars stay .02 DN/5e-6, including borders. It recomputes
initial/final MSE and checks receipt values within 1e-6 relative plus 1e-12 absolute.

At uniform logits, the checker independently obtains the full RGB-MSE gradient
to each prescribed target. With direction -gradient/max(abs(gradient)) and fixed
epsilon .01, central finite difference must agree with the autodiff directional
derivative within 5% relative. The gradient and directional derivative must be
nonzero and finite. The positive-direction step must lower the objective and the
opposite step must raise it. This rejects wrong direction and disconnected
gradients; it is not a proof of global convergence. No epsilon/target rescue.

The scientific checker reuses all original native windows, truth errors and
joint near/far/intercept retention decisions. Its small independent NumPy port
reconstructs only the analytic score templates and their fixed 7-tap blur, not
source frames. Before judging fits, all seven canonical/uniform score rows must
match retained native replay: errors/bias within 2e-7, coefficients/conditioning
within 2e-4, template SD within 2e-7; availability and decisions match exactly.
The independently rebuilt truth must match saved truth within 2e-7. The known
truth must pass and erased near/far, added .10 noise and erased-image destroyers
must fail this same final scorer. These checks commission the new readout, not
new physical fixtures or sensor calibration. Flat cases are evaluated first.

The two existing positive windows require at least 5% RGB-RMSE improvement over
the better canonical/uniform reference. Every existing window keeps RGB, green
and chroma error within 1.10 of both; every eligible coefficient (reference >=.5)
keeps 90% bounded recovery. Low-reference components remain explicitly
unqualified. Absolute errors reject overshoot/noise/offset which a projection
can reward. All results and coefficients are retained, including failures and
the distinction between beating uniform and beating canonical. The full-image
MSE being minimized does not replace these localized safeguards.

Commands: `independent-check.py check-commission --commission C/output --dataset D
--out Q`; `independent-check.py check --dataset D --predictions O/output/predictions.json
--out R`. They save commission.json/screen.json with input hashes. Root owns
execution and process/source binding. No original RAW, full image, code/default
change, deployable source-selection rule, speed or SOTA claim is made.
This exact small consumer has three AC levels on an 80x72 quad crop; production
photographs use seven AC levels at a different relative PSF/support scale.
Neither a successful tiny witness nor an unsuccessful search diagnoses the
production terminal Mean as an occlusion-halo/glare cause or ceiling.

Commission-check-1 stopped before judgments at template parity: NumPy's f32
vector exp rounded the scalar blur taps at distance1/2 differently by one ULP.
The clipped truth maximum was 3.5762787e-7; even Flat was .25 versus the native
.2499999702. The assertion stayed 2e-7. Only the seven scalar tap evaluations now
use math.exp on the f32 argument, rounded to f32, independently matching UCRT
expf at all seven taps. A read-only diagnostic then gave exact Flat truth and
maximum <=1.1920929e-7 across all seven cases. Source arrays, fitted weights,
targets and scoring bars are unchanged; the original failed check is retained.

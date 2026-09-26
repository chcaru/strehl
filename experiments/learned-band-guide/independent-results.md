# Independent scientific decision: fixed learned band guide

2026-09-26. **Reject this checkpoint; no photograph or tuning.** The learner
substantially improves on uniform averaging in focused regions, but both fixed
positive windows are worse than canonical. Genuine bright detail and weak colour
also regress. Passing the flats does not compensate for those losses.

The prospective viability check was meaningful: exact truth passed all seven
held judgments, the four required destroyers failed, and separate near/far,
glint and colour references exercised their protections. Low uniform near/glint
recovery was recorded as unqualified rather than making perfect output fail.
Thus this rejection is not a repeat of the VST core's impossible qualification.

VERIFIED from saved training/replay records: the fixed 1024 updates completed in
14.46094s of fitting, using the final checkpoint only. The train and native replay
processes exited zero with terminal accounting and no cleanup errors. The
commands are retained in `train-1/process.json` and `replay-1/process.json`.
Replay used the exact `replay_dataset` test. No new run was made for this review.
Model SHA256 is
`0388e4e2af9ff852dc19f0af716ae93642284c9499b68618d1cf747e3d341935`.
The reviewed `replay-1/output/screen.json` SHA256 is
`1f3e67c0d20fbb7a3381d86ce8fc9de20267c56689da04fd3fb43ae5d0cb8c23`.

Actual learned-model Python/native parity passes on all seven held cases:
maximum CFA error0.00292969DN, RGB error3.57628e-7, weight error6.91414e-6.
Source gathers, canonical outputs and terminal base remain exact. Those small
port differences do not explain the much larger measured reconstruction errors.
The learned output differs from uniform, and rotating its source weights is
live and rejected; this is an exercised learned consumer, not a zero-head result.

MEASURED RGB truth-RMSE ratios, learned/reference (lower is better):

| Fixed window | Learned/canonical | Learned/uniform |
| --- | ---: | ---: |
| Flat N5 | 0.90910 | 1.03345 |
| Flat N9 | 0.76180 | 1.05608 |
| Curved bright occlusion positive, N9 | 1.47747 | 0.36885 |
| Near-fine/far-coarse positive, N5 | 1.09696 | 0.33066 |
| Genuine unclipped glint core | 2.45170 | 0.20583 |
| Weak-colour component window | 1.10377 | 0.58215 |

Both flats pass all fixed error bars, although uniform still has lower error.
On the thin-depth positive, learned green near/far recoveries are0.9545/0.9332,
versus canonical1.0085/0.9371 and uniform0.3738/0.9061. The model retains both
depths and passes preservation; it is not a categorical fine/coarse starvation
failure. Nevertheless its RGB error rises from0.00518630 to0.00568918 versus
canonical instead of giving the required5% reduction.

Curved-occlusion RGB error rises0.01136408 ->0.01679014 versus canonical while
remaining far below uniform0.04552057. Chroma improves against canonical, but
RGB/green regress strongly. The local far-template references are below .5
(uniform is even negatively correlated), so those particular retention checks
are unqualified. Do not turn them into a new eligible-detail-loss measurement.
Large uniform near coefficients also illustrate why template projection alone
can credit structured boundary error; absolute truth errors remain decisive.

The glint shows the targeted tradeoff directly: outside-core RGB error improves
about5.8% versus canonical, but true-core error rises0.00372711 ->0.00913775.
Green glint recovery falls0.9810 ->0.8995. That still clears the prospective90%
relative retention bar, yet the absolute core error fails substantially. It is
not acceptable glare removal merely because surrounding spread is reduced.
The clipped-glint surround has near-canonical RGB error but chroma is1.17247x
uniform, failing the two-reference protection; clipped-core recovery was not
claimed or scored.

Weak-colour component chroma error is1.16668x canonical. Red/blue near recovery
falls0.8578/0.8543 ->0.7722/0.7733; the weaker green near component also falls
0.7238 ->0.6465, below its90% relative bar. Smoother green error and a large gain
over uniform therefore do not establish colour preservation.

This closes the fixed737-parameter feature/model/training recipe under the
declared generated ISO100 holdout. It does not refute learned source scoring
generally, establish high-ISO safety, calibrate the camera, explain photographic
glare, or validate299/488-frame inference. The short training time is feasibility
evidence only. No additional checkpoint, feature/threshold rescue or full-image
run is justified by this result.

# Independent execution review

2026-09-26. **VERIFIED: the saved fixed experiment is mechanically admissible;
its candidate is not nominated.** No repeat experiment, revised model, threshold
or fixture was used for this audit. The separate scientific interpretation is
`independent-results.md`, owned by opal_headroom.

The fresh build log contains `Compiling strehl-cli`; its 185.625s process completed
successfully. The retained test executable is SHA256
`6c785e7ce0d065d8be6369a3e6a1d3287d7a07d4fe8c223c884745c45b1e6fe4`.
I rehashed all 84 build-bound source files and that executable: every saved hash
and size still matches. Arithmetic, export and replay each executed the one exact
declared test and passed. All seven build/process receipts have exit 0, no process
error, terminal accounting and no cleanup error. Saved process wall times were
arithmetic .594s, export 31.203s, Python commission 7.250s, training 17.469s,
inference 3.953s and native replay 2.234s. These tiny generated timings establish
completion within budget, not a full-stack speed claim.

**VERIFIED pretraining admission:** all seven exact-truth oracle judgments pass;
all four required erased-near, erased-far, added-noise and erased-image destroyers
fail. Both fixed positive windows have reference errors above twice their same-N
flat controls and live canonical/uniform differences (.1754813 and.0918844 max
RGB). Fixed near, far, glint and red/blue colour witnesses are live. In particular,
canonical green near/glint recovery is 1.00855/.98102 although uniform is only
.37376/.39897: the latter is correctly unqualified local retention, not a
permanent failure for perfect truth. All four pretraining flags and their exact
conjunction are true. The runner checked and bound that receipt before training.

**VERIFIED isolation/checkpoint:** the manifest has 12 disjoint training and 7 held
cases. The training branch loads only the twelve training paths; its recorded
case hashes match those paths in order. Held paths are listed in the manifest but
their tensors/truth do not enter training or checkpoint selection. All 418 exported
array hashes and all 19 inference case/array hashes match their saved receipts.
The single fit used seed 137, Adam .001, 1024 fixed steps and the final checkpoint,
with no held-out stopping decision. Fit time 14.46094s is below 300s; reported peak
CUDA allocation 156370944 bytes. The last logged loss is explicitly before the
last update, not a separately measured final-checkpoint loss. Model SHA256 is
`0388e4e2af9ff852dc19f0af716ae93642284c9499b68618d1cf747e3d341935`.
Commission, model, dataset, inference and current training-source hash links agree.

**VERIFIED consumer/arithmetic:** all twelve training cases matched actual native
uniform and prescribed nonconstant-weight CFA/RGB exactly, including boundaries;
77 hull-clamp events were recorded across those comparison arms. All seven held
nonzero-model replays preserve exported source/gather metadata, features, truth,
canonical/uniform results and terminal base. Maximum Python/native discrepancies
are 6.91414e-6 in weights, .0029296875DN in CFA and 3.57628e-7 in RGB, within the
frozen 2e-5/.02DN/5e-6 bounds. Zero head equals uniform exactly.

The separately authored arithmetic checks have live rejection power: nonzero
single-tap oracle error 5.96046e-8 versus an incorrect-border discrepancy .00906169;
wrong separately averaged visibility differs by .00873408 max/.000431631 RMS.
All three pupil forms preserve a constant within 2.98023e-8. Source-set permutation
and whole-set duplication are exact on frozen feature tensors; this is not a
RAW/probe-reseeding or independent-noise claim. Original active-u16 flat variance
ratios span .997558–1.045079 with distinct source draws and excluded sentinels.
These checks commission noise injection/order, not physical camera calibration.

**VERIFIED decision logic:** I independently reconstructed every saved window's
1.10 error and eligible 90% component conditions from the receipt, both 5% positive
conditions and the final conjunction. Both flat cases pass. Near/far preservation
passes but its required positive fails; curved, unclipped glint, clipped-adjacent
and weak-colour preservation fail. The positive RGB errors are .01679014 against
canonical .01136408, and .00568918 against canonical .00518630. Learning is live;
the fixed two-source weight rotation changes RGB by .10916665 and is rejected.
Thus mechanical_pass=true, scientific_pass=false and candidate_nominated=false
are consistent. photographic_replay_admitted=false is preserved. No photograph,
production/default change or architecture-wide learned-method refutation follows.

Executed commands are retained in each `*-1/invocation.json`; the decisive ones
are `train.py train --dataset export-1/output/dataset.json --out train-1/output
--commission commission-1/output` (with the saved absolute paths and isolated
Python flags) and the retained executable's exact
`merge_cmd::learned_band_guide::independent_controls::replay_dataset` test, using
`replay-1/config.json`. Screen SHA256:
`1f3e67c0d20fbb7a3381d86ce8fc9de20267c56689da04fd3fb43ae5d0cb8c23`.

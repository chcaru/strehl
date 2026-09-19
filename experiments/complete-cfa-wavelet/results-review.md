# Independent result decision

**VERIFIED from root's saved run: admit one bounded boundary/composed-gather
check; do not admit photographic replay.** I reviewed the frozen implementation,
independent guard choices and all32 saved cases. No build, numerical experiment
or RAW read was performed by this reviewer.

Bindings: implementation `188e024fbe6fa162d67dc865a974230507259364250ff0b34e49256f53b9ab25`;
controls `731aeb039650c1fd91567e6fbf11642ca9cd0fdf5ce7ee0a25fe02937a716d5e`;
plan `66f877cd92d09293e1443d0873f7ccb4019bee83f395a43fa7c00eadf81ee45f`;
`controls-1/output/screen.json` `34ccc611cf3e2441c4c173116b6b0a13797fb21af9c08dbfc61688a75fc6c6bd`.
Root ran `build-1/cli-tests.exe merge_cmd::complete_cfa_wavelet::independent_controls:: --nocapture --test-threads=1`.
Both tests passed after the recorded fresh compile; the receipt preserves
source identity. Observer on/off RGB and all eight collapsed-plane hashes agree.

The guard choices have rejection power. Full256x256 native output is scored,
without a favorable interior trim. Nonweak structured components must recover
at least0.5 of truth and RGB error must be at most0.70 of the base-only
destroyer, independently of a potentially poor baseline. Exact, grey,
half-amplitude and overcontrast controls exercise the metric choices. Flat
error is compared with both baseline and fixed single source. Weak red uses
predetermined focused source2, not a per-pixel winner; its feasibility and
positive own-red evidence are exercised. Error can reward smoothing and
amplitude can reward overcontrast; their joint guards matter.

The saved outcomes are narrower than a general colour improvement:

| Fixed case family | Candidate/baseline RGB RMSE | Relevant absolute observation |
| --- | --- | --- |
| Flat |0.81164–0.81908|1.01910–1.02438 of direct source-mean error;0.45505–0.45738 of fixed single-source error|
| Genuine colour, equal/varying focus |0.99954–1.00043|Smallest recovered component0.63931; RGB error0.56854–0.57332 of base-only destroyer|
| Coarse neutral |0.85404–0.90911|Recovered components0.99021–1.01000; prior coarse collapse is absent here|
| Weak red, warm WB |0.90774–0.91093|Recovered red0.64597–0.64836 of truth, versus0.70951–0.71236 in fixed focused source|

Weak red retains91.01–91.05% of that focused-source component: only about one
percentage point above the90% guard. Retain this exact guard at the next seam.
Thousands of own-red-positive coefficients still receive zero aggregate
weight; those diagnostic counts are not an output detail-loss fraction.
Ordinary genuine-colour cases are essentially unchanged, with varying-focus
chroma error up to1.00509 times baseline. Flat and weak-red gains satisfy the
benefit rule; ordinary colour does not independently demonstrate improvement.

The geometry correction is essential to interpretation. Actual BandWorker
reaches four detail bands plus8x8 base; candidate reaches seven plus1x1 DC.
Their exponent ramps also differ. The controls assert and retain those sizes.
This supports the complete consumer, not a wavelet-only causal attribution.
Whole-domain scoring closes the discarded-border loophole, but every analytic
scene repeats at exactly the candidate's256-native wrap period. Varying focus
modulates local carrier amplitude; it is not a physical occlusion convolution.
Thus neither natural boundaries nor the photographed highlight fans are tested.

**Next scope, ARGUED:** keep all thresholds and the operator fixed. First add
one nonperiodic coloured detail/depth-edge fixture, deliberately with unequal
opposite borders, to the same small domain. Score both the whole output and
the predetermined opposite-edge region; retain flat and weak-red controls.
This can reject wrap-induced source mixing before paying for a photo. Name
the boundary rule explicitly; there is no complete-depth trim that removes it.
If reflection/padding is proposed, repeated original sites are correlated and
must be coalesced before squared norm, not counted as independent noise.

Then commission one fixed fractional pull through the actual original-u16
MHC/Catmull consumer, including asymmetric crop phase and explicit CA, with an
integer identity placebo. Predict each complex coefficient's noise from the
composed original-site influence, checked against independent end-to-end
impulses. Propagating gathered point variances as independent is insufficient:
neighboring pulls share original samples. Keep input normalization/clamping
in the comparison explicit; a linear covariance check needs an unclipped
fixture. No fractional full-image adapter, parameter sweep or photographic
quality claim is admitted until these two concrete seams pass.

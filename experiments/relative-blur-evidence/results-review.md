# Independent adequacy and refusal review

2026-09-19. **GO only for one fixed descriptive retained-source check; no
source-ordering, ownership or fusion admission.** The root-run20-record screen
passes its generated algebra/model-adequacy bars in9.453 seconds. It does not
establish a statistical focus-order discriminator.

The positive is useful within its declared family: held-out per-plane RMS is
about0.00009–0.00012 DN; reverse is122–195 DN. The fixed crossed-depth ridge
fails at138–893 DN despite an essentially exact training Gaussian fit. Its
continuation and the no-glint twin also fail, and the noisy positives remain
near5 DN. This is evidence that held-out structure can reject an explanation
which fits the training core. The spectral fan, gain-only and explicit clipping
controls refuse. It is not evidence that real glints share this Gaussian model.

Re-choosing the interpretation exposes a limit in the original status check.
Noisy-flat seed48271 is `compatible` both ways with maximum sigmas7.9978 and
7.9947, while seed99173 is `refused` both ways because maxima7.99964 and7.99914
cross the fixed7.999 numerical boundary. Both pairs have held-out errors near
5 DN, far below the30-DN allowance. A sigma-bound refusal is missing model
evidence, not evidence that one source is less sharp. Optimizer exhaustion,
unsupported context and clipping likewise cannot be the losing direction.

Root explicitly authorized one extra bounded independent test before real
interpretation. Seeds2027,48311,90217,314159 were fixed in flat-refusal-plan.md
before execution. The unchanged model and all original noise/mask settings
ran in4.797 seconds under a20-second owned-job limit,4.734375 CPU seconds,
133,726,208 bytes peak job committed memory. All four pairs are compatible in
both directions; errors span about4.93–5.20 DN and no held-out mismatch occurs.
**The suspected false-exclusive result was not reproduced in these four
seeds.** That is not proof of safety: blur estimates remain close to the cap,
and a failure of an optimizer or bound has no physical direction regardless
of which seed encounters it. No model, tolerance or original result was changed.

For the separately scoped real check, permit disjoint target fit/held pixels
with source-stencil overlap only if it is declared. Held target values still
do not enter the fit, but shared noisy source samples couple the residuals;
there is no calibrated significance or likelihood. Freeze facet28→69,
dark33→69, nearby25→33 and reverses, core training and separate tail/structure
held regions. Report raw-DN prediction/residual fields, per-plane errors,
covariance and exact refusal reasons without a compatibility threshold or
donor label. This can expose failure of the limited local explanation cheaply.
Success cannot prove ownership; failure may arise from depth mixture, spectral
or asymmetric spread, clipping, placement, or the narrow Gaussian family.

| Binding | SHA256 |
| --- | --- |
| model.py | 4a40f8b201e5baaf47597203b8031e896bb68c0b005e2b09082d8b6adc739e0c |
| controls-1/output/screen.json | 20a8982465ca776ed5bcbaaaf915c55c0738c668e5841197461925f0edddc7d5 |
| flat-refusal-stress.py | 6cecb2ea2fcf34872d8d8c4c6258d36c4b84f0da01f759b1e9b54e0203d28745 |
| flat-refusal-plan.md | aaa7cfd964d13101a6e2f56bda76faab20bc23b7e4b359ad6df30d7b7f5d390b |
| flat-stress-1/screen.json | d634f51c608833daea2cf220e90112a1f4fb8da9524569d49f289086c00c4c0c |
| flat-stress-1/process.json | c1a4ee388d222158ff90ed25bfbf67f331ef738594e4b6fa835b11fd302b9195 |

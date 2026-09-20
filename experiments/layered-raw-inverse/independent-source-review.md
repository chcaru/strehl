# Independent source and choice review

SOURCE-REVIEWED before execution. No blocker remains for the declared generated
utility screen. This is a fixed two-layer, known-depth/known-optics reconstruction
test; it does not establish empirical optical calibration, automatic depth,
canonical stacker superiority, photographic improvement or SOTA. This reviewer
authored neither numerical model nor independent controls and ran neither.

Frozen checkpoints:

| File | SHA256 |
| --- | --- |
| model.py | 5710146ffcf463de85e317050bc81357922965d6006c7b4cf311f4d80d8ee512 |
| design.md | 079c9e2ef5e4113c1202d4435b1cac7d5dfcbc482b7ebd20e7ca72e86446f9a1 |
| independent-controls.py | 6915c024dbbfaa0e0d912ecba1a22075aabce6ef29c845f0e586472be60815ec |
| independent-plan.md | 94e65319535b3744882431f14975e5b9b5f2da7f0093c818ed8d006bb6997408 |

The forward operator samples premultiplied near radiance and coverage together,
samples far radiance at its own depth on the same pupil ray, composes visibility,
then averages rays. This order is materially different from multiplying already
averaged visibility and far radiance. The independent SciPy implementation and
wrong-order destroyer can distinguish them. RGGB sampling occurs after this
camera-linear forward image and supplied PSF; the likelihood never demosaics its
u16 observations. Both model paths use native pixel centres, not quad units.
Maximum displacement12 plus Gaussian radius3 plus bilinear support1 is covered
by margin16. SciPy nearest and Torch zero boundary extensions cannot enter that
interior. Actual production gather, CA and geometric uncertainty are outside
this first test, rather than presumed equivalent.

The supplied64-point pupil is identical between independently implemented
forward paths. A separate1024-ray comparison tests integration adequacy and
does not silently change the observations used for fitting. Same-discrete
forward disagreement over0.1DN stops before optimization; continuum disagreement
is reported separately and blocks a real-RAW license without making discrete
reconstruction utility uninterpretable. This predata separation avoids blaming
the inference model for unresolved pupil quadrature.

The Gaussian likelihood includes injected shot/read variance and the declared
1/12DN-squared quantization approximation. Original digital16383 is censored
at the half-code boundary16382.5;15360 is not substituted. Positive radiance may
exceed the censor ceiling. The independent literal loss witness includes the
same declared quantization term but computes its own expected difference.
Training-interior saturation must actually occur, and at least one training
view must have an entirely uncensored protected glint core. These qualifications
prevent a vacuous censor control or a positive requiring only pinned inputs.
The normal-tail approximation is not Poisson-exact or empirically calibrated.

Seven whole training observations alone enter initialization, normalization,
optimization and donor-bound choice. Withheld observations2/6 are not used for
latent or PSF initialization. The actual input facade rejects their access and
whole-array conversion during fitting, and its deliberate illegal-read control
must fire. Poisoning held values must preserve initialization exactly. Optimized
history/output equality is appropriately not required: CUDA backward reductions
may be nondeterministic, and elapsed time cannot be identical. Independent
source hashes check immutability. The donor bound uses noiseless training
predictions to choose a whole RGB donor, then copies its noisy developed value;
it is a truth-informed comparator, not an implementable election.

The initial normalized image prior was too weak to act at the likelihood's DN
noise scale. The predata replacement measures RGB gradient norm in units
b=sqrt(2*V(2048DN)), about30.7DN at the supplied ISO100 model. Its small-gradient
precision is about1/941DN-squared versus observation precision about1/470 at
that reference, before axis/sheet/CFA normalization. This is a chosen regularity
scale tied to supplied noise, not a measured distribution of scene gradients.
The objective averages frames and image support and averages radiance sheets;
it is explicitly normalized penalized likelihood, not an unqualified summed-MAP
claim. Alpha/radiance compensation remains nonidentified despite the coercive
term. Success concerns rendered sharp radiance, not correct alpha recovery.
The final predata cosine rate0.03 to0.001 keeps160 steps in both arms and reduces
avoidable final-step oscillation; iteration-limit results are not convergence
certificates, and no result licenses a subsequent schedule sweep.

Quality guards include flat first, reconstructed pinhole RGB, separate component
retention, heldout per-plane/bright/dim prediction and a matched far-only scene.
The fixed far-depth comparator is deliberately restricted, not the best possible
single-layer fit. The new component-only ridge segment[39,31,63,41] avoids the
glint: using the wider ridge template alone could credit blocking a bright
highlight while losing real coloured filaments. Wide RGB regions are retained,
and the half-component/wrong-colour metric controls remain necessary. Low
prediction error alone can reward an incorrect latent or excess smoothing;
truth/component guards therefore remain independently binding. Angular
illumination is a diagnostic model mismatch, not a guarantee that every
violation will be detected by an automatic adequacy rule.

All amendments above precede the first numerical result. No frozen author file,
fixture or threshold was changed by this reviewer, and no tests, builds, RAW
reads or additional experiment were executed.

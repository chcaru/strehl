# Adaptive continuous kernels: different estimator, no ready focus consumer

**SOURCE-VERIFIED / DERIVED, 2026-10-27. No-go for immediate implementation or
full-stack deployment.** This is a genuinely different reconstruction prior,
but the available method does not supply the missing focus admission, injected
noise contract or runnable all299 model. No implementation source, dependency,
checkpoint, image or RAW data was downloaded or executed for this review.

## What the primary method actually provides

The [primary paper](https://people.csail.mit.edu/cjbisc/burst/burst_paper.pdf),
sections3.1-3.6, uses original scalar CFA values at continuous aligned locations.
A demosaicked, unaligned RGB stack supplies encoder features, not output values.
For output pixel/channel, its learned kernel takes offset, sample-color one-hot
and a latent code. Weights can be negative; normalization is
`sum(f*w)/(sum(abs(w))+1e-7)`. The radius is4 output pixels. A3N-channel encoder
is trained on five-frame translated synthetic bursts with signal-dependent
Gaussian noise and an image L2 loss. It specifies no injected inference-time
sensor-variance/covariance input. Reported inference uses nearest-sample search
and adaptive sample truncation; it is not a demonstrated299-frame streaming
consumer. The [official project page](https://people.csail.mit.edu/cjbisc/burst/)
currently routes its Code link back to itself. No licensed implementation or
trained checkpoint was located through that link; the supplementary fetch was
unavailable because of its size. This review uses the accessible primary paper.

## The decisive focus-bracket distinction

**Derived from the declared kernel inputs:** at coincident same-color sample
positions, sharp and blurred frames receive identical kernel weights. The
signal path is therefore a spatial filter of their temporal mean, conditioned
on the whole burst's encoder features. The encoder can change that filter, but
cannot assign distinct weights to coincident frames through this interface.
This is an admission limitation, not a proof that learned restoration is
impossible. Nonzero breathing/jitter does not become a validated focus cue.

The needed adaptation is therefore not replacing a fixed kernel with an MLP.
It requires source-conditioned, frequency-dependent focus/visibility admission
that retains simultaneous near fine and far coarse content. Adding source
features or per-band kernels changes the trained model and training task;
five-input selection or scalar whole-value blending does not solve this.
There is no bounded pretrained adapter to propose now.

## Why the old failures still matter

- The [positive original-CFA kernel trial](C:/dev/blog/death-of-software/projects/strehl/experiments/native-cfa-kernel/results.md)
  softened complete-chip rails and scratches. Learned signed, cross-color rows
  are a real difference from those positive kernels, so that result does not
  reject this family. Conversely, arbitrary row shape is not evidence of true
  structure or preserved independent color.
- The [joint Lanczos experiment](../../quality-september14/joint-cfa-lanczos-verdict.md)
  exposed a signal/noise tradeoff; the [deflated band inverse](../joint-cfa-local-fit/constant-deflation/results.md)
  still failed flat chroma. A learned reconstruction prior could choose a
  different completion, but original samples alone do not certify its output.
  No Sony-calibrated uncertainty or noise-gated selection follows from training
  on randomized noise. Reused inputs induce correlated output channels/bands.
- The [strict variance-cap proposal](../joint-cfa-local-fit/identifiability/operator-proposal.md)
  was closed because its reference ceiling could force genuine detail to zero.
  This method does not inherit that particular cap, and cannot inherit a noise
  guarantee in its place. Signed absolute-sum normalization is neither convex
  averaging nor automatic constant/color reproduction.
- [Native whole-value fusion](../native-pixel-fusion/photographic-review.md)
  failed the complete flat photograph, in addition to the known near-fine/
  far-coarse control. A focus-bracket adaptation must address both issues;
  ordinary sharpness-consistent burst performance does not do so.

The useful transferable idea is to condition a direct original-sensel output
operator on a separate guide while preserving exact sample locations. Its
focus-bracket admission, independent-color behavior, sensor-cell integration,
noise accounting and practical complete-image cost remain unsolved here.
Do not open a new training/framework effort or claim native photographic gains
from this paper alone. Root can revisit only when a lawful runnable model and
a concrete focus-aware operator exist; that is not the current state.

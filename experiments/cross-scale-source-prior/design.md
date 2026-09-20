# Fixed coarse-band source prior

ARGUED counterfactual, not a depth estimator or a quality result. The native
coarse bands can favour a different source mixture from fine detail. This one
test conditions their existing weights on normalized finest-source support.
It does not revive the rejected radius32 energy pool or categorical Potts rule.

For the actual current source guide, injected variance and beta, let w[i,k]
be the existing gated SoftPower weight. In supplied source order, accumulate
the f32 field D=sum_i w[i,0]. There is no epsilon or new noise estimate.
Define z=1[D>0], and p[i]=w[i,0]/D where D>0, otherwise p[i]=1/N.
Let G^k be repeated **existing** pyramid::reduce: binomial5, replicate borders,
even decimation in the cropped output-quad gauge, including odd dimensions.

- Band0 weights and weighted accumulators remain canonical.
- For AC k>=1, if G^k(z)==0, retain w[i,k] literally; otherwise use
  w'[i,k]=w[i,k]*G^k(p[i]) in f32.
- Mixed supported/unsupported footprints retain the unsupported pixels' uniform
  1/N shares. Do not divide by G^k(z), remove these pixels, or normalize after
  pooling. Source normalization happens **before** spatial reduction.
- Existing coefficient accumulation, every unweighted fallback sum, terminal
  mean, and InputRange hull remain unchanged. If all new weights vanish, the
  original per-band mean fallback applies. Reconstructed fine appearance can
  still change through other bands and the final hull; unchanged band0
  accumulators are not an image-quality guarantee.

Two actual-consumer passes keep only D, its binary-support pyramid, small
hash/beta receipts and the normal merge state. Pass two reruns the same rounded
GPU gather and actual probe, verifies known4/guide/variance/beta and every
canonical weight hash against pass one, and reduces one source's p at a time.
No aligned/source/weight volume is retained. Original storage remains u16;
all image and weight arithmetic remains f32. The generated adapter is bounded
to70 frames and512 native pixels per dimension, no optical CA profile, supplied
similarities and crop, and unchanged camera/MHC development. It is not a full
RAW adapter or a default production mode.

Off and Neutral are explicit exact canonical replay placebos. Neutral means
a literal all-one multiplier, not rounded uniform 1/N multiplication. A
commissioning-only forced-source wrapper replaces **coarse** weights by1 for
one supplied index and0 otherwise, retaining band0/base/hull; it is never used
to nominate a source. No diagnostic toggle or private estimator is introduced.

The core diagnostic bridge only compares private accumulator bits. Root owns
the feature-gated include and CLI test include; the author does not run tests,
builds or RAW. Independent controls own truth fixtures and acceptance bars.
Necessary destroyer: fine near-depth texture over genuine coarse far-depth
structure, where this prior can wrongly veto the far surface. Flat noise,
thin coloured detail, radial detail, blur spread and phase sensitivity remain
image controls. A passing small screen would only license a separately scoped
complete photograph. The Helicon comparison does not establish its mechanism.

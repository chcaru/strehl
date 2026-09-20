# Independent source and choice review

Read-only review, 2026-09-19; no execution by this reviewer. **Admit the fixed
generated controls, not a photograph or production change.**

Reviewed implementation6e54f3a15bbd8613daa219bcd27a379b5430c8add55f7341ba04d19bc0ce7b92,
transformf7f183ddb875043c60c7cb458ad72ec1819ae6ff1ae773c336fcedc26bdd99c3,
probe4856b680ed258dbf55e5e7650d7bc2b4159eb523aa2da9e3dcf26cb84feb67f1,
bridge d5cd1032c30c5e9700def70fd935ed85a5e45a232644e1a0f643b62cabb4219d.

The actual baseline worker supplies the signal four-plane tuple. Probe draws
start in the original active u16 buffer, use explicit [R,G1,G2,B] variance
routing at original DN, then the actual GPU rounded MHC/Catmull consumer.
The source-space simulation therefore preserves repeated source contributions
and cross-colour effects without a diagonal gathered-noise approximation.
Independent pairs accumulate squared complex differences divided by16.
Output WB squared is applied once to each plane's energy and propagated floor;
energies are summed, not coefficients. One shared directional weight multiplies
all four complex values. Smoothing occurs within each declared subband.

The extension copies whole CFA-plane identities, with explicit central offsets.
Tiny cyclic taps and complex LL are retained to1x1; rectangular one-axis
continuation omits nonexistent detail orientations. The mean fallback includes
terminal DC; reconstruction crops before the original per-sample hull. Actual
baseline113x101 reaches three AC bands and15x13 mean base, whereas candidate
128x128 reaches seven and1x1. Controls assert that difference; this cannot be
called an isolated wavelet-basis comparison.

The observer flag changes only witness/bias accumulation. Source hashes,
separately gathered known4 hashes, baseline guide hashes and diagnostics
on/off final hashes will test the actual route. Their equality is unmeasured
until root runs the controls. The held-out64 reference never enters fusion.

Limitations are binding: the floor is conditional on the noisy supplied
source and the existing quantized Gaussian generator, not a new camera
calibration. Eight pairs have substantial Monte Carlo uncertainty. The
band-level comparison uses variability across complete independent draws,
not the misleading count of correlated pixels. Reflection can still create
an unequal cyclic join, so full-domain and fixed edge/corner errors are
guarded. The local varying-focus fixture is a falsifiable image model, not a
physical occlusion or specular-light model. Both ISOs and fixed warps must
retain weak-red detail and coarse structure; lower flat error alone cannot
admit the candidate. Source inspection found no blocker to this bounded test.

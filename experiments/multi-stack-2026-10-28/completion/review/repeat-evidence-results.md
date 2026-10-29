# Original-CFA linear repeat observations

## Scope

**VERIFIED mechanism, not a photographic result.** `strehl-core::repeat_evidence`
is an additive, bounded original-CFA observation primitive. Ordinary stacking
does not call it. A caller supplies the original content identity, separate
R/G1/B/G2 plane, full-guide color pull, injected noise model, linear gain and a
frozen expected-signal callback for every original tap. The callback's guide
identity, uncertainty and dependencies remain the caller's responsibility.

Each fixed spatial filter is composed with the bilinear or Catmull-Rom sampler
in physical sensor coordinates. Repeated original-site coefficients are summed
before reading pixels or evaluating noise. Zero-net coefficients have no read,
clipping or guide dependency. Missing active support, clipped effective taps,
unknown guide expectations and nonfinite arithmetic refuse the observation.
Signed below-black samples and signed cross-band covariance are retained. The
returned exact original-site list permits overlap checking between observations.
It does not assert independence of fitted geometry, shared guides or fixed pattern.

The default helper returns high=identity-L1, mid=L1-L2 and low=L2. L1 is separable
`[1,2,1]/4` at sensor offsets -2,0,2; L2 is its convolution with itself,
`[1,4,6,4,1]/16` at -4,-2,0,2,4. These are defined filters, not an assertion that
their bands equal every band of the product's multiscale fusion operator.

## Controls and actual commands

All receipts below are under `outputs/multi-stack/completion`. Each command ran
through `experiments/multi-stack-2026-10-28/run-command.py`, with native Windows
permissions, `CARGO_BUILD_JOBS=4` and `GIT_WORK_TREE` set to this checkout. Full
commands, logs, host load, process resources and native exit codes are retained.

`repeat-evidence-controls-04` ran:

```text
cargo test --locked -p strehl-core repeat_evidence -- --test-threads=4
```

**VERIFIED:** fresh `Compiling`, exit0,11/11 tests;5.103seconds wall time and
551,354,368bytes sampled peak private memory. This is test/build resource usage,
not a full-image performance claim. Controls include four native CFA positions,
negative signal, half-phase signed Catmull taps, an independent coalesced-filter
oracle, exact original-dependent heterogeneous variance, gain squared, full
sensor gauge under scale/rotation/translation, cancellation before any read,
source/plane overlap identity, unknown support, clipped negative-weight taps,
short rows, same-pixel-count wrong geometry, exact budget boundary, and8,192
independent original-sample Rademacher draws against predicted covariance.

The independent analytic one-dimensional overlap oracle uses a custom length5
sensor-stride1 filter. Its coalesced weights are `[-1,12,42,12,-1]/64` and its
variance norm is1027/2048. This differs deliberately from the shipped helper's
sensor-stride2 bands. Catmull half-phase norm is41/64 per axis. Neither control
assumes bit-identical arithmetic to sequential resampling: coalescing changes
floating point summation order while preserving the specified linear operator.

`repeat-evidence-controls-01` is retained as a failed9/10 test. The fixture
incorrectly assumed the selected three binomial bands necessarily have a
negative covariance entry. An explicit negative-identity band now exercises
`cov(identity,-identity)=-var(identity)`. Production arithmetic was not changed
to make that assertion pass. Independent review also found a missing same-full-
geometry check; it was added with a pre-read wrong-shape control before03/04.

`repeat-evidence-clippy-02` ran:

```text
cargo clippy --locked -p strehl-core --all-targets --no-deps --message-format=json -- -D warnings
```

**VERIFIED limitation:** fresh `Checking`, exit101. The structured audit in
`repeat-evidence-lint-audit-02.json` maps all43 unique diagnostics to unchanged
remote-main spans. No new repeat-evidence diagnostic remains. The first lint
receipt found one new test-only range-loop warning; the iterator correction is
included in the freshly rebuilt04 controls. Strict repository clippy is not
reported as passing. New source/test files pass scoped rustfmt.

Independent source review is in `repeat-evidence-primitive-review.md`. No
compatibility threshold, focus peak, PSF certificate, repeat eligibility or
reconstruction result is produced by this primitive. Actual estimator controls
and original-capture integration consume it separately.

# Independent saved-colour-error source review

SOURCE-REVIEWED; no execution by this reviewer. No material blocker remains for the bounded read-only diagnostic.

The implementation forms the same signed R-G/B-G truth errors as the frozen chroma score, casting the saved f32 image and truth to f64 before subtraction. It uses the complete supported `[16:80,16:80]` square for every arm and phase. This is scalar error accounting on saved outputs, not changed candidate image arithmetic. No irregular core/ridge region is trimmed to fit the blocks; their existing local scores remain separate evidence.

The nested block-constant spaces satisfy P4 subset P2. Thus `E-P2`, `P2-P4`, and `P4` are mutually orthogonal; splitting the last into signed global mean and its zero-mean remainder does not add DC twice. The code checks both energy identities per error coordinate with fixed roundoff bounds. Each circular shift retains all4096 original samples. It changes the basis, including artificial opposite-boundary neighbours, rather than registering or resampling an image. The four parity origins are dependent sensitivity checks and do not exhaust all16 origins of a4×4 grid. Total energy must remain invariant even when component attribution changes.

The independent oracle enumerates modulo coordinate groups without the author's roll/reshape/repeat path. Constant signed bias, native checker, aligned four-pixel blocks and smooth sines distinguish DC, fine, middle and varying coarse contributions. The shifted-block case explicitly requires changed attribution. The overlapping-residual negative deliberately double-counts a nonzero middle component and must fail conservation. This supplies rejection power beyond reconstructing a total from the same terms. Input-array immutability is checked.

Actual-output verification covers all six flat/layered-by-arm records, exact source/truth hashes and support, every component at all four phases, and independently retained scalar chroma results. The root wrapper runs commissioning before decomposition and verification, binds the previous immutable source chain plus saved inputs, and matches the declared CLI. No fitting, forward model, image correction, new metric threshold or quality decision is introduced.

Interpret fine and coarse labels only as this basis's allocation of squared truth error. Block-common variation is not synonymous with signed colour bias, and fine error is not proof of CFA aliasing or an optical nullspace. Circular-boundary/phase sensitivity is not independent replication. A decomposition may guide a later causal test; it cannot revise the rejected Cauchy result or license smoothing genuine colour.

Reviewed SHA256 bindings:

- `colour-error-decomposition.py`: `4043b4b52c06904084832cd54603fb1e4a086fd3f8930808f4aad391741ed906`
- `colour-error-decomposition-plan.md`: `ab3b29a872272b1b00463f8ad79cbddebd0441ee9a6e68ca3019678b57065690`
- `colour-error-controls.py`: `b6322d22e8f727309c1a91cf1490af4a23071c58d95f8b4d1c6810b3e6e0acda`
- `colour-error-independent-plan.md`: `50803995c74cd93ae30f1e6629c86b825f1bc65ebafba83de43959efd344cb00`
- `run-colour-error.py`: `865e0c13ad7b10c4af1b6ac4beb1672dd06f026f5572edf20ade7f9f64f4a1a6`

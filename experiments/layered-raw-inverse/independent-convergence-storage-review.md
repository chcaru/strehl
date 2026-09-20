# Independent review of the gradient storage correction

2026-09-19. Read-only source and saved-receipt review; no execution by this
reviewer. The corrected script is ready for the unchanged bounded continuation.

All three convergence-1 receipts record the same incompatible-stride `.view`
error, zero optimizer iterations, and identical original/final state hashes.
Their initial and final objectives are also identical. This run provides no
optimization or additional image-quality evidence; its numerical refusal is
retained.

The correction in convergence.py is confined to gradient storage and its
receipt fields. After the existing finite-gradient check and all backward
calls, each gradient is copied to contiguous storage. Its logical flattening
must compare exactly equal before and after that copy, then the contiguous
gradient replaces the old gradient. The already-computed gradient norms still
describe those same logical values. Every evaluation records the actual number
of noncontiguous gradients converted; the arm receipt totals those counts.
Root should require a positive count to establish that the failed path was
actually exercised. No image arithmetic, gradient value, latent parameter,
objective, source order, optimizer setting, stopping predicate, or quality bar
has changed.

The prior independent-convergence-review.md remains the review of the numerical
recipe and scorer. This amendment changes only its convergence.py source
binding from `5f60810974fb791819d78402530a42b516f90cc14acf8ec489c03619df2c88e0`
to `e755e29ec5494714818fae9c61428e6c10d085c2e2d2fd78e2959998c58df468`.
The convergence plan remains `85b6b28d067b1448257b5b46a447d10476846bc22a2636f9f0463200dbc62de6`
and scorer remains `ed396953a185a545733192588230e81eb458cb517e1b405f1fd7fe87ace7ff94`.
The model is still the original frozen `5710146f...` implementation. The
original screen rejection and separate physical-quadrature failure remain.

# Independent source review before quality execution

Root reviewed Curie's K=0 target, metadata reader, fixed quality metrics and private instrument runner by source on 2026-09-07. No target or instrument computation was run by this review.

ARGUED: the target applies each layer's affine moment and Fourier integral on the same clipped unit cell as visibility, and uses the complementary polygon integral for background. It retains native coordinate phase. The separate-alpha and centre-mask private arms can fail the coupled affine oracles. The independent ten-cell verifier uses a separately implemented analytic x integral and adaptive y integration; its values remain required before scoring. Local target controls alone grant no quality admission.

ARGUED: the temporal reader estimates across eight repeats at each site, using the sample divisor seven. Delete-one M2 subtracts (8/7)*(sample-mean)^2 and then uses divisor six. The finite-repeat bias decomposition is explicitly arithmetic, retains negative estimates and is not corroboration. Wave fits solve the joint two-frequency design with rank/condition guards and separately report residual error, so an orthogonal extra component defeats coefficient-only agreement. Flat controls precede wave claims.

ARGUED: masks are in the consumer's native gauge, require the fixed74-pixel supported window, and use strict endpoint-background clearance including the two-pixel demosaic support. Sparse comparisons preserve signed errors and native row-major tie order; the percentile uses ceil(.999*N)-1. The controls include a spike outside the display window, opposing bias and equality at the ten-DN threshold.

ARGUED: the independent TIFF fixtures change dimensions to11x7, use both byte orders and multiple strips, then exercise a legal193x17 image that the retired128-width guard rejects. File integrity and the actual changed green sample are tested separately. The root-authored parser was independently reviewed by Curie; this runner is independently reviewed here.

Limits: the shared IO module is initially loaded before its own release verifier. Root's command launcher binds all sources before starting, and each released invocation uses a fresh bytecode cache; the verifier then checks the exact source set and saves copies. Tracked allocation limits cover named ndarray backing owners, not process RSS. Metadata and output accounting include persistence checks; last recorded timing is not process-exit timing. Actual private controls and the separately admitted target remain necessary.

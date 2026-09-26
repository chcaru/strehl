# Fixed-front temporal radiance intercept: small falsifier first

Root scope, September25. The complete chip-focus-radiance average visibly
reduces broad coloured spill but fails native fine-detail retention. Test one
different estimator with its exact saved front, schedule and Gaussian width:
the intercept of a weighted quadratic through each CFA channel's observations.
This is local polynomial regression, not new mathematics or a calibrated PSF.
The prior fine-band prediction is narrower than a valid radiance model; that
limitation and the failed coarse-band proxy remain in force.

Use delta=(t-z)/sigma, q=exp(-delta^2/2), and solve the three normal equations
for constant, linear and quadratic terms. Return the constant at delta=0.
Image arithmetic and persistent sufficient statistics are f32. The four CFA
channels share geometry; original observations remain unchanged. A streaming
consumer stores moments, not an aligned frame volume. Skip zero q before
multiplying powers of delta. No width, degree, schedule, ridge, source-subset,
clipping or fallback variants. Numerical refusal applies to the whole candidate.

Signed weights are unavoidable and can create overshoot/noise. The normalized
moment matrix must have infinity-norm condition <=1e4, and mass on each side
of z must be >=1% of total. The independent reviewer freezes additional
propagated-noise and photographic-adversary bars before execution. A noiseless
quadratic reproduction is an arithmetic identity, not image-quality evidence.

First compile the exact operator in a small standalone Rust experiment using
cached dependencies. Test independent flat noise first, then the unchanged
nonquadratic sinusoid from chip-focus-radiance and a contact/depth adversary.
Wrong-front, erased-detail, range and ill-conditioned cases must have power to
reject. Passing permits further consumer commissioning only: no canonical
native or photographic quality claim follows from this plane-array screen.
Failure closes this fixed estimator without a rescue sweep.

Author source_trace owns operator.rs; trace_review owns preregistration and
controls; root owns runner, execution and decision; opal_headroom reviews the
runner and prior-art/claim choices. No full adapter or RAW pass is commissioned
before this screen. No production changes or SYNTHESIS fold.

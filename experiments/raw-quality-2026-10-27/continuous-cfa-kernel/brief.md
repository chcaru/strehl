# A continuous original-sample reconstruction candidate

2026-10-27. Bounded primary-paper and prior-evidence review, no execution yet.

The complete current V3 photograph exists, but its preliminary full/native
inspection has not revealed a substantial gain: several hairs are better
separated, scale softness and colored contours persist, and the quiet background
has new curved traces. Independent photographic review is still pending.
Developed-RGB fusion is not the requested native RAW endpoint.

Question: does Biscarrat et al.'s 2026 Adaptive Continuous Kernel Networks
provide a materially different, implementable original-sensel reconstruction
route for focus brackets, or only another fixed-sharpness burst estimator?
Primary sources: https://people.csail.mit.edu/cjbisc/burst/ and
https://people.csail.mit.edu/cjbisc/burst/burst_paper.pdf . The project page's
small-PDF and Code links currently return the project page; do not infer that
code or trained weights are available. Inspect a repository license before
opening implementation source, if a genuine official repository is found.

Root ran unified searches for kernel prediction/burst denoising and Adaptive
Continuous Kernel, then the mechanical checker for both. Targeted Markdown
search found the older B-algorithms-sota discussion but no exact new-method
entry. The old report explicitly warns that constant-sharpness burst training
does not establish focus-bracket behavior. M83 and REVIEW retain the limits of
transferring jitter-based burst results. These are load-bearing caveats.

Read the actual method, not only its project-page abstract. Compare it with
the rejected positive anisotropic CFA gather, noisy joint Lanczos, free RGB
band-residual/constant-deflation and strict-variance-cap local fit. The changed
question must identify an actual estimator difference, not merely the phrase
continuous coordinates or use of a neural network.

Cfa-residual owns `method-audit.md`: one concise source-derived decision with
native input/output quantity, use of any coarse RGB guide versus output sample
data, noise/covariance treatment, focus/occlusion assumptions, model availability
and exact unresolved adaptation. A scalar convex whole-value weight must face
the already established near-fine/far-coarse counterexample. A learned prior
must face independent colored structures and out-of-distribution noise/blur.
Do not claim that training or positive weights prevents fabricated detail.

Integration-review owns `independent-decision.md` after reading that audit:
challenge whether there is a genuinely different implementable next consumer
and whether it can be tested photographically within a practical bounded run.
An explicit no-go or missing runnable model is a useful answer. No open-ended
literature survey, new package/model download, training, GPU/RAW job, source
change or photographic promotion is released. Root selects any implementation
only after this short decision and the complete current photograph verdict.

# Independent free-visibility result review

MEASURED from root's `free-visibility-1` receipts and frozen scorer; no refit or threshold change by this reviewer. The fixed matrix recipe fails overall qualification. `matrix_all_in_family_checks_pass=false` and `selective_adequacy_demonstrated=false`. All eight arms completed; this is a measured quality failure, not an incomplete instrument.

| Case | Free Huber whole RGB / chroma RMSE, DN | Free matrix whole RGB / chroma RMSE, DN | Matrix disposition |
| --- | ---: | ---: | --- |
| Flat | 16.680 / 25.169 | 16.896 / 25.650 | Fails all four absolute/fixed-reference flat guards |
| Layered | 74.140 / 64.308 | 62.623 / 44.583 | Fails three fixed-reference image guards; held-out passes |
| Far-only | 74.444 / 33.602 | 53.724 / 11.624 | Image, component and held-out checks pass |
| Angular mismatch | 166.939 / 66.959 | 92.167 / 52.967 | Held-out refusal; not selective qualification |

Flat is decisive. Matrix passes its 1.05 comparison with equally budgeted free Huber, but both are substantially worse than the unchanged mean (6.018/8.368) and filtered fixed-alpha visibility (5.020/7.016). The matrix's held-out global residuals remain 1.002/1.022 normalized RMS and all available strata pass. Thus adequate prediction residuals do not protect the delivered flat image, and selecting only the free-Huber comparator would conceal the failure. The old pinhole flat errors also remain high: 43.348/44.221 RGB DN for original/matrix. The fixed optical consumer attenuates harm without removing it.

The layered matrix arm improves all fixed same-budget free-Huber comparisons. Core RGB/chroma is 275.782/112.210 versus free Huber311.654/162.009; ridge is 123.018/73.088 versus144.861/108.281. Its bright held-out residual improves from2.45262 to1.21829 and passes. But the predeclared fixed-alpha Huber limits still reject core RGB (reference251.453), ridge RGB (110.209), and ridge chroma (63.066). Core chroma passes against114.651. These three failures cannot be averaged away by whole-image gain or reclassified as success against a weaker comparator.

Known-alpha matrix's previous target-specific layered success was much better still: whole22.787/34.237, core65.562/94.199 and ridge34.075/49.660. That comparison identifies the practical gap when visibility must be estimated, while the current paired Huber arm isolates the prior change under the same free-state protocol. It does not prove a unique physical opacity or identify one latent failure mechanism: the mask/radiance coupling and optimization trajectory both differ from the oracle intervention, and the exact representation gauge alone cannot explain a changed delivered image.

Layered matrix glint recovery [0.99798,0.99728,0.99860] and ridge [0.98613,1.00009,1.00478] pass the capped component requirements. The small green/blue ridge overshoots receive no extra detail credit. Their coexistence with ridge chroma failure again demonstrates why projections cannot replace image-error guards.

The far-only null supplies a genuine positive result for this particular guard set. Matrix passes all whole/core/ridge RGB/chroma comparisons with both the actual restricted historical single-depth fit and current free Huber, retains glint recovery0.9775–0.9815, and passes the43-sample bright residual at1.25543. Free Huber passes the image bars but fails bright residual2.98373. Because the true ridge template is zero, this result uses fixed-region errors to check invented foreground structure; it makes no nonexistent ridge-recovery or correct-mask claim. The historical single-depth comparator is restricted and not a best-possible method.

Angular mismatch remains refused even though matrix global held-out RMS1.134/1.443 passes: the43-sample bright stratum is2.62609, above1.75. Free Huber's bright residual is4.50887 and its second global residual1.89768 also fails. Matrix reduces error but its glint projection overshoots by about3.8–4.1%. This is not selective adequacy because matched flat/layered cases failed their required image tests; no automatic gate was implemented. No held-out censored samples occurred in these arms.

The actual commission verifies live logit derivatives (maximum6.73e-5, independent discrepancy4.62e-12), and receipts confirm identical original160 starts, all three trainable parameters, unchanged sources and only the seven training indices. All eight fits reach1000 iterations, use1012–1030 actual completed evaluations, and return accepted finite states. Every final raw-parameter gradient exceeds1e-6: matrix flat0.000272, layered0.007710, far-only0.009061 and mismatch0.002550. Final objectives are still changing near the budget boundary. No optimum or convergence claim follows; lower likelihood or a changed prior total is not evidence of image quality. No continuation or threshold rescue is justified by this screen.

The fixed recipe is rejected. Known optics, supplied depths and unresolved64/1024 pupil disagreement remain; this run supplies no real-RAW or SOTA admission. Pure pupil-integration commissioning remains a separate numerical question and cannot retrospectively repair these free-visibility failures. Whole-scene visual review is separate from this receipt-based interpretation.

Bindings: scored result SHA256 `e7f0815720f33d308cb98bf3cbb69f65dd0b806a1af8eb57328dfaea32db16d4`; fitter `6279275e8ac30d833b555bf3a8326d1a82f55ca4ef74debc7368955fab0a23a1`; controls `1320de1e738d7cc3fcd19c0536e27cd41efe572783ab1bb18bb91dd26c6362a2`.

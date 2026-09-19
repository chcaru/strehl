# Independent source audit

Reviewed implementation SHA256
`8e13d3891b93d30d6c5ed870bb74cc67fb857051f31c6b816c51e115f9065ef2`
against the charter. No code edits, builds, numerical controls or RAW reads
were performed by this reviewer.

**Blocking finding, before execution:** the adapter asserts
`level_sizes(128,128,7).len()==8`, but production `level_sizes` stops at
`MIN_LEVEL_EXTENT=8` (`pyramid.rs:139`). Its actual sizes are
`[128,64,32,16,8]`, so this assertion necessarily refuses every generated
consumer call. The actual BandWorker has four Laplacian bands and an 8x8 base
on this domain, despite requesting the seven-band cap. Its weight exponent
schedule uses the reached four-band count. The candidate has seven complex
detail levels and a 1x1 DC, with `exponent_at(k,7)`.

Required correction: assert/report the real baseline dimensions and preserve
the production stopping rule. State both reached depths and their exponent
schedule difference in the charter/results. This remains an actual-consumer
comparison, not a matched-depth ablation. The absolute truth guards are needed
alongside relative scores. Author, root and controls owner were notified.

**No other blocking defect found by inspection:**

- The tiny 2/4-axis cyclic paths retain the old tap, phase and accumulation
  order. Synthesis parity makes its division by two exact even for negative
  wrapped indices. Numerical old-operator agreement and tiny unitarity remain
  independent controls, not facts established by this reading.
- Nested top-left LL rectangles remain complex. Analysis shrinks from128 to2;
  inverse visits the rectangles in reverse order. Packed detail regions cover
  all coefficients except index0, which alone receives the mandatory mean DC.
- Original-index kernel composition adds each stage's complex paths modulo128
  before squared norm. Its powers-of-two offsets account for repeated wraps;
  no scalar LL variance recursion is used. Two-dimensional propagation remains
  separable onto the original independent CFA variances.
- Explicit `[R,G1,G2,B]` noise mapping, original-site identity checks, WB-squared
  summed energies/floors, shared colour weights and the diagnostic-only switch
  retain the reviewed all-CFA arithmetic. No aligned-frame collection is added.

Periodic analysis, clamped smooth5/baseline and current MHC have different
boundary behavior; complete depth has no uncontaminated local trim. Passing
the proposed controls would not establish natural-image boundary handling,
fractional-gather covariance, optical validity or photographic improvement.

Final admission awaits the baseline-geometry correction and a fresh source
hash. The independent controls were still being authored during this review.

## Correction accepted after the first review

The corrected implementation SHA256
`188e024fbe6fa162d67dc865a974230507259364250ff0b34e49256f53b9ab25`
replaces the impossible assertion with the actual baseline sizes
`[[128,128],[64,64],[32,32],[16,16],[8,8]]` and exposes them in the comparison.
The independent controls assert and save these dimensions. The candidate
operator is unchanged; the comment encoding repair has no arithmetic effect.
This resolves the source blocker. Acceptance was sent to root before its
build; this report amendment was deferred until the run's source validation
finished, as requested.

Root's fresh build and two saved passing controls now establish the bounded
operator checks discussed above. See `results-review.md` for the independent
choice review and the decision: admit only the next boundary/composed-gather
check, with no photographic admission and no matched-depth attribution.

# M135 slide commissioning amendment 2

Status: **FROZEN AFTER REPLACEMENT RUN 2 WENT RED AND BEFORE RUN 3**

The frozen physical preregistration and all numerical data bars remain
unchanged.  `commission-run2-failed.json` is preserved at SHA-256
`c42b4d64d3162a700fdcf389368871b18ae3b7c4d8aace03b9dc8874648fe7a0`.

Three controls remained red:

1. The revised timestamp plant still tied two timestamps, so filename order
   remained a legal tiebreak and the mutation still had no power.  Make all
   three timestamps distinct.
2. Moving a quadrilateral vertex onto its diagonal remained convex under
   OpenCV's predicate.  Move it outside the opposite edge; the load-bearing
   convexity test is unchanged.
3. Two separately converged ECC calls differed by `0.0012604` in one raw
   matrix element despite `0.9999886` correlation and `0.0751 px` recovery
   error.  Matrix-element equality is not the consumer.  Replace the
   ineffective near-zero `sin(pi*x)sin(pi*y)` distractor with an actual
   Nyquist checker, and gate its effect as the maximum mapped-point
   displacement in native pixels (`<0.05`), which is the coordinate consumed
   by patch extraction.  The registered low-pass stop remains `0.06
   cyc/native px`, and the separate exact-zero spectral-mask control remains
   mandatory.

No selector was removed and no scientific failure was converted to a pass.

# Alignment-gate correction after the first RED

The first Amendment-1 gate used maximum quadrant component range
`<=0.05 quad pixel` as a proxy for the scorecard's geometry rule. It read
0.07 on light pass 1 and 0.10 on light pass 2, so it went RED before any FRC
was retained.

Audit against the now-authoritative literal in
`2026-09-sota-scorecard.md` §1.5 found that proxy was not the specified
quantity. The scorecard says **non-translation residual `<=0.10 output px
RMS`**, not maximum range. Quad-green coordinates are two native pixels, so
the correct fixed statistic is:

```
2 * sqrt(mean((dy_quadrant-dy_global)^2 +
              (dx_quadrant-dx_global)^2))
```

This correction is in the direction that could rescue FRC and is therefore
called out explicitly. Recomputing it from the already stored shifts, before
changing the checker, gives 0.064031 native pixel on pass 1 and **0.107703
native pixel on pass 2**. Thus the authoritative statistic still goes RED,
but only 7.7% beyond its hard bar.

Before trusting that marginal failure, the corrected checker must itself be
commissioned on (a) a pure external analytic translation and (b) an external
piecewise-translation plant whose known local RMS is above 0.10 native pixel.
The plant must go RED. An independent spatial-domain subpixel estimator must
also agree on the real pass-2 decision; disagreement files NOT ROBUST. No FRC
may be calculated while this gate remains RED.

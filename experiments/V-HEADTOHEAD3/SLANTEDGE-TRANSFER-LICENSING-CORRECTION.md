# V-HEADTOHEAD3 — transfer licensing correction

**Recorded after the first adjudicated outcome and before regenerating corrected
artifacts.**

Independent final verification found that two cross-grid diagnostics violated
the frozen statement that nothing above 0.25 cycles/native-pixel may be read or
reported.  `R0` used the image-fitted PMax0 scale `1.002`, extending its
comparator mask to `0.250500`; `S40` used PMax40 scale `1.003`, extending it to
`0.250750`.  Those two numerical readings are withdrawn and replaced by
`UNLICENSED_GT_0.25`.

This correction does not change any result used by the preregistered verdict.
`T0`, `M40`, `TS`, and `O40` each measure two images on one native grid with a
strict `[0.20,0.25)` mask.  In particular, the formal branch still depends only
on `T0` and `M40` and remains `UNRESOLVED`.  The corrected instruments do not
compute cross-grid `Q25` for `R0` or `S40`; the adjudicator requires both
withholding markers and commissions a numeric-leak mutant to RED.

Consequently this arm cannot numerically re-express strehl/PMax0 on the
requested sharpening-matched cross-grid comparison.  `TS` remains a licensed
within-strehl sensitivity reading, but no preregistered strehl-rung
reproduction verdict exists.  No threshold, site, operator, licensed
single-grid statistic, bootstrap seed, or formal interpretation rule changes.

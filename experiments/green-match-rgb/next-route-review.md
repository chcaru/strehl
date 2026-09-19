# Next-route decision: adjacent-scale source support

**READ-ONLY FINDING: no exact prior empirical test located; do not treat that as
evidence it will work.** Mechanical searches used separate arguments:
`prior_art.py cross-scale parent consistency support coherence` and
`prior_art.py cross-band interscale persistence multiscale`, followed by targeted
local report/source searches. No candidate code, RAW read or experiment was run.

The nearby precedents answer different questions:

- BUILD-HULL sections14.10/15 proposes shared cross-band weights as ARGUED.
  Its actual `commission_bands.py` C5 uses one image-global source-weight vector
  to commission a hull detector; it does not test local parent support or quality.
  Its real near-uniform-weight null is likewise not a parent–child intervention.
- BUILD-BLEND retains separate per-band evidence and varies exponents/coarse
  averaging. V-GATHER section12.12 explicitly leaves its cross-band hypothesis
  untested. M9 studies regularizer/support coupling, not octave agreement.
- The retained MIT comparator's consistency2 repairs same-scale directional
  disagreement and spatial ordinal extrema; it has no parent–child scale vote
  (`fine-support-guidance/external-consistency-review.md`).
- The current radius32 candidate replaces finest evidence with a broad spatial
  mean: ISO100 fan error1.125616x and compact-core recovery0.410–0.423 reject it.
  Phase-packed RGB retains every original source weight and is a photographic
  null for these fans. Neither tests adjacent-scale source support.

**One concrete untested candidate, ARGUED:** retain current finest weight
`w0(k,x)` and multiply it by the same frame's bounded parent support:
`w0' = w0 * U(r1/(1+r1))`, where
`r1 = max(E1-F1,0)/max(F1,1)` and `F1=gate*beta1*variance1`.
`E1` is existing smoothed squared band1 energy; `U` is the existing positive
pyramid expansion onto band0 coordinates. Bands1+, base, colour coefficients,
noise injection and normal fallback remain unchanged. This is one adjacent
octave's local support, not radius32 pooling, a copied hard donor, propagation
to every band, or multiplication of two exponent8 weight fields. It fits one
streamed frame's existing pyramid; no aligned-frame collection is needed.

**Strongest failure/control:** genuine narrow-band fine texture can have almost
no band1 signal, especially beside a stronger coarse feature at another depth.
The rule can then erase correct compact detail or route it to the mean. A fixed
fine-carrier/depth-step negative control must expose that case and retain actual
truth error plus truth-capped component recovery; flat noise runs first. Reuse
the rejected candidate's compact-core and real coloured-ray gates as well.

**Priority restraint:** current actual ancestry is not an affirmative premise.
Dark-fan band0 favours69, but band1 favours57/61, still late fan-bearing captures;
facet-fan band1 instead favours0/1/2/6. Those are leading indices, not complete
source support. High parent SNR may make the bounded multiplier almost unity.
Do not commission a full photograph on index disagreement alone or claim this
route selects compact sources. Root should decide only after the current
green-match screen; this note identifies an untested bounded rule, not a win.

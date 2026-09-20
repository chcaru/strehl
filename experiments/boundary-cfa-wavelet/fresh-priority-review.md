# Fresh priority: shared source membership before more wavelet engineering

**ARGUED recommendation:** spend the next production-sized quality experiment
on one automatic spatial source-membership field shared across reconstructed
detail, rather than another independent per-band weight variant. First require
one small actual-consumer screen, then one complete70-frame pair. This is a
choice of the next falsifiable hypothesis, not an established automatic fix.

The boundary-wavelet refusal is not evidence that its output generally harms
the baseline: the current review reports relative RGB/boundary guards passing,
with fractional red recovery much better than baseline but just below the
absolute focused-source retention bar. Preserve that result accurately. The
reason to change priority is photographic relevance and remaining cost: the
full-image extension still needs its deeper transform/CA/noise path commissioned
and currently prescribes16 additional gathers/transforms per source
(`complete-cfa-wavelet/next-design.md`).

The measured vitamin-C failure is different. Late sources contain real, strong
fan structure; the actual finest-band observer strongly favours a late source
at a frozen fan point. A better noise floor or another transform need not reject
that signal. Helicon B is visibly more compact than its C arm and current
Strehl, although differing development/alignment prevent causal attribution to
its advertised depth-map method. The corrected spatial donor photograph now
shows direct local headroom: source33 removes most of the long downward column
when support actually covers it, retaining the compact contact and nearby
source25 detail. The right branch remains. These observations support testing
source consistency, not claiming that depth smoothing is the explanation.
See `helicon-current/comparison-plan.md`, `helicon-current/depth-route-audit.md`,
`donor-consistency/corrected-results-review.md`, and the current
`docs/proposals/2026-09-quality-path.md`.

## One concrete bounded prototype

Use **categorical source-cost regularization followed by soft whole-AC replay**:

1. Reuse each actual `BandWorker`'s finest-band smoothed Laplacian energy E and
   existing injected floor F. Form a dimensionless source preference
   `s=(E-F).max(0)/(E+F)`, with zero for a zero denominator, and unary cost
   `D=1-s`. These are heuristic costs, not calibrated probabilities. Do not
   refit sensor noise or claim frame index measures physical depth.
2. Apply a four-direction scanline Potts aggregation to these categorical
   costs: retaining the previous source label costs zero; changing to any
   other label pays the same penalty. Weight that penalty by edges of one
   held baseline guide, shared by every source. The recurrence is
   `L_r(p,k)=D(p,k)+min(L_r(p-r,k), min_j L_r(p-r,j)+P(p,r))-min_j L_r(p-r,j)`.
   Combine directions with the unary counted once. This propagates categorical
   support along paths instead of averaging numerical frame indices or pooling
   image energy over another larger box. Freeze one penalty rule and one soft
   cost width before execution; neither is an optical constant.
3. Convert near-minimum aggregated costs to normalized nonnegative soft source
   memberships. Stream those memberships through the already commissioned
   `SpatialDonor::add_source/finish` arithmetic in
   `donor-consistency/spatial-donor.rs`: reconstruct each source's entire AC
   contribution first, use the same membership for all four CFA planes, retain
   the baseline terminal base and actual input hull. Do not Gaussian-reduce
   memberships independently into a new band election. Keep noise-gated
   averaging and explicit baseline fallback in unsupported/ambiguous regions;
   never substitute a raw hard donor map or the legacy estimator backend.

The existing class stores at most eight oracle masks. A whole-image adapter
must stream source memberships and accumulate sums/denominators, not allocate
one full mask plus pyramid for every donor. Scalar source costs may need a
bounded cost-volume allocation or replay; budget that explicitly before the
70-frame run. The reusable seam is the consumer arithmetic, not a claim that
an automatic label solver already exists.

This minimal unary deliberately reuses green evidence. It cannot discover
weak-colour-only focus; the fallback must preserve existing colour there.
Green-supported nearby structure can still steal genuine red/blue detail.
That limitation is a reason to retain the existing varying-focus true-colour
and weak-red controls, not to replace the unary with an uncommissioned
per-channel noise approximation. The core hypothesis can fail: a confident
late fan may remain preferred after Potts aggregation, or the spatial prior
may erase a real thin feature. A smoother label map alone is never success.

## Prior losers constrain the test

- `BUILD-ELECT.md` sections11–16: coherent wrong-depth collars and near-hard
  colour joins survived alternative focus statistics. `BUILD-BLEND.md`,
  “The index field this arm never forms” and “Am I masking rather than
  fixing?”, explains both the seam improvement and persistent coarse-energy
  ambiguity. Do not restore the old whole-pixel argmax/estimator.
- `M13-window-depth-measured.md` and
  `fine-support-guidance/candidate-independent-results.md`: generic spatial
  borrowing can erase compact cores and cross depth. The fixed radius32 rule
  lost roughly58–59% of core recovery. Potts is a different intervention, not
  permission to tune that window again.
- `M65-election-gate-measured.md`: changing labels can leave actual admission
  largely unchanged. Confirm live output memberships and full-AC consumption.
  `M96-election-margin.md` and `M63-bimodality.md`: coherence, decisiveness and
  extra focus peaks do not establish correct ownership.
- `V-DILUTE.md`: do not increase exponent or narrow admission to fix a supposed
  deep-stack dilution. `source-concentration/results-review.md` and
  `failure-scan-review.md`: the failed radius-ordering locator cannot supply
  seed labels for this experiment.

Reuse flat-first, true-colour/varying-focus, thin/radial detail and close-depth
controls; add no new framework or sweep. Require both source weights and the
wrong-source control to affect the actual consumer. If admitted, judge the
complete vitamin-C output, both dark branches, facet core, nearby detail and
smooth fields against the held baseline and Helicon B. No manual coordinates
or donors enter this automatic arm. Stop after that whole-image decision rather
than growing another local-oracle campaign. No implementation, experiment,
original RAW read, or new quality measurement was performed for this review.

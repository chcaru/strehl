# Complementary sparse focus sampling — independent photograph review

**VERIFIED / observed positive:** combining the two six-source pitch32/offset16 passes fills real focus gaps that neither half covers alone. The complete 6788 × 4524 result is coherent, and the preregistered native witnesses preserve recognizable content from both better-focused halves. This is a bounded interleave benefit on this tilted target, not resolution beyond a properly sampled full sweep or independent-repeat noise gain.

The most decisive witnesses are `even32-good-2` (paired bars/digits substantially smeared in offset16, retained in even32 and combined), `offset16-good-1` (radial spokes/central spot blurred and colored in even32, preserved in offset16 and combined), and `offset16-good-3` (line fan, labels and fine bar groups blurred in even32, retained in offset16 and combined). The remaining three witnesses show the predicted preservation of edge/dust/low-contrast surface structure, but increased visible grain by itself is not counted as recovered detail. The dense182 ordinary reference confirms the expected scene structure; it has a different fitted and cover-scaled gauge, so no cross-gauge pixelwise score or difference was used. The combined output is not claimed superior to dense182.

All four complete compositions were inspected under the same first-half-only fixed display. Six native384 witnesses × four arms (24 crops) were inspected in paste-only 784 × 820 boards. No obvious new seam, displaced duplicate edge, missing area or large color break appeared in this bounded review. Existing halos and unresolved finest groups remain. Complete masters are finite and read back at expected geometry; complete PNGs, native crops and per-artifact SHA receipts are retained under `outputs/multi-stack/completion/pitch32-independent-review`.

## Selection and controls

The input design uses exactly twelve original files already staged from one182-frame physical sweep: 0,32,…160 and16,48,…176. Original content hashes are distinct and copied bytes/stamps rechecked; no RAW decoding was performed by the reviewer. Pitch8 had shown little benefit because measured local focus widths were typically5.63/5.67 original frames (p10≈3.21,p90≈9.2). That failure is retained in the prior review.

Before any new candidate photograph was viewed, the selector read only SHA-bound dense-half focus maps. Both usable flags must hold; primary modes converted to original acquisition ordinals must agree within the larger width; **both** estimates must independently place the good half within0.5 own width and the bad half beyond2 own widths. Positive cases in both directions and inconsistent, broad and invalid counterexamples were exercised first. It found87,292 even-good and74,711 offset-good quad pixels, then ranked8-connected areas and froze3 native witnesses each way. Qualifying support fills5.5–22.6% of these broad384 crops, reported rather than implying the entire square qualifies. Local width is a three-sample shape descriptor, not uncertainty or physical depth calibration.

After only the new first-half locator was viewed, witness centers were transferred without image fitting through a shared original acquisition: old dense-half index48 = new reference3 = ordinary dense index96, checked by SHA. Exact saved f64 placements, native `(u-0.5)/2` guide convention, canvas offsets and ordinary cover scale0.9676287511847108 were used. Null/known-translation controls checked direction. Mean pixel center is origin+191.5; final origins round by floor(x+0.5), at most0.5sensor pixel. Fitted-map transfer fixes the review gauge, not physical registration truth.

Frozen receipts:

- `pitch32-focus-witnesses.json`: `1e4fa556606ca6d326df79341348409aaf5dc70acb1c38bb96cbcf723abf74f5`.
- `pitch32-rois-frozen.json`: `b59d2a4b097b7cb1d574a2934ae96a5ceda042083c690c01c98cf806cc5796bf`.
- `interleave-pitch32-inputs/preparation.json`: `4255fbacbcf5fb7f86cdf4ccb50ac70dcbb4bfc537baed2289729992e75af571`.

The first-half display was independently commissioned against **every** encoded photograph channel: zero differing channels, maxu16delta0. No per-arm contrast or sharpening adjustment was made.

Commands actually run (saved-file analysis only; numerical libraries limited to one worker):

```powershell
python -X utf8 experiments/multi-stack-2026-10-28/completion/review/prepare-pitch32-interleave.py
python -X utf8 experiments/multi-stack-2026-10-28/completion/review/select-pitch32-witnesses.py
python -X utf8 experiments/multi-stack-2026-10-28/completion/review/prepare-pitch32-displays.py control
python -X utf8 experiments/multi-stack-2026-10-28/completion/review/map-pitch32-witnesses.py
python -X utf8 experiments/multi-stack-2026-10-28/completion/review/prepare-pitch32-displays.py all
```

Root scheduled the actual complete12-source engine render; reviewer did not rerun it. This reviewer authored some shared focus/precision/UI fixes but did not author this interleave consumer or the alignment solve. The selection/reference/photograph conclusions were independently challenged rather than inferred from implementation checks.

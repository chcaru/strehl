# Pitch-eight interleave photographic review

**VERIFIED / observed:** complete 6808 × 4536 combined and both 23-source controls were read back as finite RGB32 masters and prepared under one first-half-only display transform. The first-half encoded display reproduced its photograph TIFF with **zero differing channels**. All four complete compositions (including the separate-gauge ordinary182 reference) and nine native384 witnesses per arm were inspected. No obvious new seam, missing region or color discontinuity appeared. **No clear new resolved detail advantage over both constituent halves was demonstrated.** The combination generally resembles the better local half; some bar/radial edges differ slightly, but the same unresolved fine groups, halos and merged radial core remain. Flat appearance alone does not establish temporal-noise reduction.

The source design is causal undersampling of one physical sweep: ordinals 0,8,…176 and 4,12,…180. These are disjoint originals but not an independent repeat-noise acquisition. Dense182 is a useful full-workflow reference with its own map and gauge; its approximate landmark crops are not pixel-registered truth. No cross-gauge differences or numerical sharpness score were used.

The first-half locator was the only new image viewed before freezing `pitch8-rois-frozen.json` (SHA256 `6af231008f588c2cb11f17dfa5d71bb0847644d89803ce05208da5b7d1f1b61c`). Nine broad preregistered scene regions were retained: flat gray, QR grid/corner, fine radial labels, bars/grid, two dot fields and lower radial spokes. Every witness is a native 384 × 384 slice, without resampling. Four-up boards are 784 × 820, paste-only; overviews are orientation only. Display and complete/crop SHA receipts are retained under `outputs/multi-stack/completion/pitch8-independent-review`; board layout and digests are in `native-comparisons/layout.json`.

Commands actually run (one thread for numerical libraries, no RAW decode or engine invocation):

```powershell
python -X utf8 experiments/multi-stack-2026-10-28/completion/review/prepare-pitch8-displays.py control
# First-half locator inspected, then immutable ROI receipt written.
python -X utf8 experiments/multi-stack-2026-10-28/completion/review/prepare-pitch8-displays.py all
```

**ARGUED implication:** the failure to demonstrate a gain is not permission to omit interleave. A near-planar target can remain adequately sampled even at this spacing. The next positive test should be selected from actual focus-support/width evidence before viewing a candidate: regions whose best-focus intervals fall between one half’s samples, with distinct surface depths and a dense union reference. A stronger sampling gap needs to be demonstrated in a control, not inferred from source count. The current result establishes a complete interleave capability and a limited photographic comparison, not an interleave quality gain.

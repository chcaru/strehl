# Export receipt and pixel-support audit

2026-10-27. VERIFIED read-only audit of the completed export. This verifies the evidence being shown, not a photographic improvement, omitted-detail finding or capture limit. No RAW, fitting, focus metric or new export was executed by this reviewer.

Root ran:

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-27/weevil-through-focus-support/run-bounded.py --run-id 1
```

The recorded child command invokes `export-source-views.py --out` with the fresh `outputs/raw-quality-2026-10-27/weevil-through-focus-support-1` directory. It completed exit0 in27.469s, peak committed job memory316,207,104bytes, terminal accounting true, no cleanup errors, within120s/2GiB and one library thread. This is an export cost, not full-workflow stacking performance.

The final receipt SHA256 is `2ada612f0cacdbeecb9cae937935503a2a4f3171b40608ca8325af8875baeafe`; whole-view receipt SHA256 is `659ddbd694e4bf70fabe0140b19d4d2323638425bd0b57b6d00f55b23e6e085b`. All31 indices are exactly0,10,...,290,298, in that order. Each ordinal matches its frozen export row, filename `DSC(index+1).tiff`, output hash/length and original-RAW identity metadata. Reading that identity metadata does not open the RAW. Current cached-source size/mtime matches the pre-export record; root's frozen exporter performed the full pre/post source hashes. This audit did not repeat the roughly6GB source census.

There are31 individual complete1617x1078 orientation views,155 available384x384 native crops, four whole-source contact sheets and four sheets for each of five witnesses. No crop was unavailable or relocated. Process-log order and file timestamps both confirm every complete view and `whole-views.json` preceded the first crop export. These checks establish export order; human whole-view inspection remains a separate action.

All31 original TIFF headers are single7032x4688 RGB16 images. Every crop TIFF and PNG has the original literal ICC and expected384x384 dimensions; individual crops are unresampled. Independently rehashed377 output/dependency bindings with no mismatch. For all five witnesses at source0,150 and298, read-only sample checks establish exact equality between saved crop TIFFs and their literal source subarrays, plus exact PNG conversion `(RGB16+128)//257` and ICC equality. The other140 subarray equality checks are performed by the audited producing path.

The pinned map explicitly states reference149 and reference-to-source placements. Re-evaluating all155 centers using complex arithmetic confirms `q=C+a(p-C)+2b`, with `C=(3516,2344)` and the native baseline crop offset(68,46). No inverse-map substitution or source-index shift occurred. Reference149's retained bits are `[3ff0000000000000,bc00000000000000,3ca0000000000000,0000000000000000]`; tiny gauge roundoff is preserved, not replaced with exact identity. Largest absolute center-rounding residual is0.499016px. The following sampled source-native origins are exact:

| Frozen witness | Source0 | Source150 | Source298 |
| --- | --- | --- | --- |
| upper-leg-hairs |1866,663|1888,686|1897,694|
| turquoise-scales |2171,1372|2188,1386|2194,1388|
| thorax-texture |4603,2606|4588,2606|4572,2596|
| elytron-seam |3012,1999|3018,2006|3017,2002|
| blue-joint |2738,875|2748,896|2749,902|

The31-step sampling can miss a narrow informative interval. Similarity mapping locates corresponding context, without proving equal physical footprints or accurate local placement; source pixels are never warped. Original source development precedes merging and differs from the native stack's postmerge development. Contact sheets are resized navigation aids. Those limitations remain attached to any interval nomination or source-supported observation. No evidence-integrity blocker was found.

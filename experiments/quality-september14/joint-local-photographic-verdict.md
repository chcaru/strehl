# Local-coordinate intervention: native chip crop

VERIFIED by independently viewing `joint-local-comparison-1/render/{old-map-eight,local-map-eight,mhc}-native.png` at native 328-pixel size and reading its `heldout.json`.

The local-coordinate correction improves some visible structure over the old-map eight-frame reconstruction: the dark cores of the long vertical rails are narrower and more distinct, and boundaries between horizontal ladder segments are clearer. However, periodic cyan/blue stipple remains conspicuous, becoming stronger along several rail edges and in the lower yellow field. The result does not look cleaner than the MHC anchor. This is evidence for a useful local placement correction, not a successful photographic replacement.

Both image arms consume the same eight retained frames146–153; boundary-limited frame145 is excluded from both. The reported intervention changes inverse coordinates by `-delta_source/a` while retaining original CFA values and supplied noise. Six-frame reconstruction arms additionally omit frames147 and151: their common-observation R/G/B RMSE improves from .056016/.093813/.143448 with old coordinates to .023055/.058862/.084890 with local corrections.

Those held-out frames participate in low-pass registration, so the latter comparison validates reconstruction conditional on the fitted geometry; it is not independent end-to-end holdout. Eight-frame predictions include the predicted observations and are not held-out evidence. Error can favour blur, hence the separate native-image verdict.

Corrected phase diversity remains to be checked. The present evidence does not isolate the remaining periodic defects to phase conditioning, focus/PSF mismatch, noise amplification or any single cause. No further PSF test or new RAW read was performed for this review.

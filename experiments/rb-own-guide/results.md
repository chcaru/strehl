# R/B own guidance: useful colour evidence, failed full-render admission

MEASURED, 2026-09-19. One fixed ten-case actual-consumer screen completed.
Independent review rejects this complete operator because flat noise and
developed-green errors fail. It also confirms substantial guide-specific colour
headroom: both positive scenes improve against the matched-estimator green
control, with live source weights, recoverable true components, and a harmful
swapped-guide control. This is generated-image evidence, not a photograph or a
demonstration that axial colour focus causes the real vitamin-C artifacts.

Executed commands (Python 3.12):

```text
python -I -B experiments/rb-own-guide/run.py build --out experiments/rb-own-guide/build-1
python -I -B -X faulthandler experiments/rb-own-guide/run.py controls --build experiments/rb-own-guide/build-1 --out experiments/rb-own-guide/controls-1
```

Fresh compilation completed in 142.093 seconds. The exact test completed in
3.250 seconds, peak job committed memory 393,760,768 bytes, one passed test,
`SCREEN_COMPLETE`, and `photographic_replay_admitted=false`. Noise arithmetic,
covariance/routing destroyers, original input hashes, canonical identity, input
hull, terminal means and diagnostic on/off output hashes pass. All source and
executable bindings match. Screen SHA256:
`5bae9a282349905a2d7dc391a55ced39e19f0eda9c6d24ec75706f96c3ed7cb3`.

| Scene / ISO | Own RGB RMSE / canonical | Own RGB RMSE / matched green | Disposition |
| --- | --- | --- | --- |
| Flat / 100 | 1.4650 | 1.3391 | Noise guard fails |
| Colour focus offset / 100 | 0.1901 | 0.1904 | Developed-green guard fails |
| Colour-only / 100 | 0.4370 | 0.4275 | Developed-green guard fails |
| Flat / 400 | 1.4561 | 1.3336 | Noise guard fails |
| Colour focus offset / 400 | 0.2639 | 0.2645 | Developed-green guard fails |
| Colour-only / 400 | 0.4495 | 0.4329 | Developed-green guard fails |

These are errors against independent known image truth, paired with true
component retention; lower error alone can reward smoothing. Flat chroma error
is 1.5130/1.4998 times canonical at ISO100/400, and about 1.378 times matched
green. Thus changing the noise-floor estimator does not alone explain the
own-guidance noise penalty. No decomposition of noise-selection causes was run.

Both collapsed CFA greens are exact in every arm, but final MHC uses R/B data
when interpolating green. Offset-scene delivered-green errors become 1.9182
and 1.2622 times canonical at ISO100/400; colour-only green errors also rise.
This mechanically demonstrates output-channel coupling, not a partition of
that error into transferred noise versus altered scene detail. Genuine radial
detail misses its green guard at 1.1084 times canonical. Neutral detail,
crossed thin depths and the declared unsaturated regions near a clipped glint
pass. The glint contains nine original codes at16383; there is no claim of
recovering unknown clipped radiance.

Keep this fixed operator closed to full rendering and default promotion.
The next design may preserve canonical camera-RGB green while separately
controlling noisy R/B updates; it must retain these original failures, explain
its new mechanism and pass independent controls. See `results-review.md`.

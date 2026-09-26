# Fixed marigold placement: refused before full rendering

**MEASURED, root execution 2026-09-25:** `fit-1/result.json` reports `STOP_ANY_FIT_FAILED`, `full_pair_admitted=false`. The fixed anchor112, sources108–116 and native support `[3608,3252,392,392]` in ref244 gauge remain unchanged. No full-stack image was rendered, and no photographic improvement is claimed.

All eight non-anchor fits converged, stayed away from the existing ±4-native-pixel bound, and had positive fitted gains. Four failed the predeclared held-out prediction bar:

| Source ordinal | After/before held-out RMSE | Decision |
|---|---:|---|
|108|1.033118|Refuse|
|109|1.003972|Refuse|
|110|1.001694|Refuse|
|111|1.012554|Refuse|
|112|1.000000|Exact zero anchor|
|113|0.837938|Pass fit only|
|114|0.887945|Pass fit only|
|115|0.832773|Pass fit only|
|116|0.832883|Pass fit only|

Held-out error can decrease by matching defocus, so even the four improved values do not establish better geometric truth or image quality. The all-eight rule rejects this recipe; there is no subset, recentering, interval change or threshold revision. Minimum measured source training/holdout support gap was4.700456native pixels after accounting for guide, sampler, displacement and derivative footprints. The original known-shift, mild-blur and wrong-sign registrar controls passed; their full values remain in `fit-1/controls.json`.

Stage5.765s and fit2.453s wall time both ended normally within120wall/90CPU/2GiB bounds. Nine original file hashes matched the ordered recipe before extraction, and file size/mtime remained unchanged afterward. Anchor112's independently decoded432×434 original-u16 patch differed at zero sensels. This proves the retained decode comparison and initial content bindings, not a second post-run content hash audit.

Commands actually executed by root (workspace root; Python3.12 with `-I -B -X faulthandler`):

```text
experiments/marigold-local-placement/stage-fit.py stage --out experiments/marigold-local-placement/stage-1
experiments/marigold-local-placement/stage-fit.py fit --staged experiments/marigold-local-placement/stage-1 --out experiments/marigold-local-placement/fit-1
```

Each command saved its bounded child invocation/process receipt and completed source bindings. Per root's stop, no symlinks, whole-stack staging, local-placement configuration, writer exposure edit, new build or full render was created. This closes this fixed local-placement trial; it does not establish that the marigold geometry is accurate or that source152 hairs are unchanged under a hypothetical render.

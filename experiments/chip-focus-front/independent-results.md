# Independent focus-front prediction decision

MEASURED, 2026-09-25. The original two-band predictive gate failed and remains
failed. No native merge or photographic quality is qualified by this experiment.
All 42 fixed sites had temporal modulation; the single registered fit converged
without a registered bound. Insufficient coverage therefore does not explain
this refusal.

| Held-site prediction / constant-predictor error | Fine band | Coarse band | Bar |
| --- | ---: | ---: | ---: |
| Aggregate RMS ratio | 0.216691 | 0.383811 | <=0.50 |
| Site-ratio 90th percentile | 0.371581 | **0.795418** | <=0.75 |
| Lower-colour witness | 0.376171 | **0.874074** | <=0.75 |

Every fine-band bar passed, including all seven named witnesses and four held
spatial blocks. The coarse band failed the percentile and lower-colour bars;
passing its aggregate cannot erase these failures. The 19 training sites and
23 held sites were fixed spatially, and every named witness was held out.
Held-site amplitudes/offsets used even frames; odd frames were scored. Band1
fitted only its width at training sites with the fine-derived front and
schedule held. It is a second spatial-frequency prediction, not independent
sensor-noise evidence.

The independent controls had rejection power: the true nonuniform planar
positive passed (aggregate ratios 0.006842/0.010359), exact flat refused, noisy
flat lacked coverage, the genuinely two-dimensional bowl failed prediction
(0.956553/0.976798), and the two-depth mixture failed (0.717952/0.757595).
Shifting or reversing the fitted front also failed prediction. The positive
shares the fitted Gaussian family and commissions fitting only; its response
width ordering is not a physical model of these image bands.

ARGUED scope decision: the fine-band result supplies substantive, spatially
withheld predictive support for one separately declared native observation.
It does not reverse the original gate or establish correct source ownership.
The proxy uses toned RGB, CA-off development and interpolated 128-pixel tiles;
the native consumer uses CA-corrected gathered CFA. Texture-dependent response
width, local relief/occlusion inside a tile, and whole-field extrapolation can
all invalidate transfer. Coarse failure need not mean the chip is nonplanar.
The saved fine width 0.0224410234 is a latent response width, not calibrated
defocus, depth, or an optimal radiance-averaging bandwidth. Any new observation
must declare its own reconstruction, controls and full-image verdict.

VERIFIED instrument choices: extraction controls exercised crop/quad mapping,
source/channel addressing and spatial-only filtering. The metadata-only
reference-identity preflight initially failed because the pinned transform
was not bitwise identity. Its measured bound is 4.833584748946457e-13 native
pixels; the repaired preflight preserves its exact bits and whole-map hash,
with a fixed 1e-9 bound. No map normalization, photo-derived tile reselection,
response-family change, width sweep or gate relaxation followed the results.

Root executed the following under the bounded wrapper with the retained source
bindings (generated 1.984 s, extraction 54.25 s, fit job 0.656 s):

```text
python -I -B -X faulthandler experiments/chip-focus-front/independent-controls.py --model experiments/chip-focus-front/model.py --out experiments/chip-focus-front/controls-1.json
python -I -B -X faulthandler experiments/chip-focus-front/stage.py --out experiments/chip-focus-front/stage-1
python -I -B -X faulthandler experiments/chip-focus-front/fit.py --stage experiments/chip-focus-front/stage-1 --controls experiments/chip-focus-front/controls-1.json --controls-job experiments/chip-focus-front/controls-job-1 --out experiments/chip-focus-front/fit-1
```

Evidence: `controls-1.json`, `stage-1/receipt.json`, and
`fit-1/{receipt,model,judgment}.json`, with saved prediction arrays. Judgment
SHA256 is `b30dc11332170ce916cebbcdf8fd767c8fa0f3c24de58e52fb4fa85a9dbc8bee`;
model SHA256 is `9aa704e4cbea5f9193aa98e8d63c5abec3a983202a48c84e8d6a6da75a39c8fd`.
The receipt explicitly retains both predictive_proxy_admitted=false and
photographic_quality_admitted=false. These are proxy timings, not native speed.

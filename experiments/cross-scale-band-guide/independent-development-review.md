# First development fit: useful learning, remaining curved-colour tradeoff

MEASURED interpretation of root's `train-1/output/training.json` and
`check-1/output/screen.json`; no refit or new score run by this reviewer. All19
cases, including the former seven held cases, were trained/developer-visible.
There is no generalization, photographic or SOTA result. The historical learner
and oracle refusals remain unchanged.

The root-run commands are preserved exactly in `train-1/invocation.json` and
`check-1/invocation.json`: Python3.12 `-I -B -X faulthandler`, respectively
`train.py train` on the original19-case manifest and `independent-check.py check`
on that manifest, the saved model and saved inference. Training ran2048 steps
in105.6315s and selected step1536 by the declared complete development loss.
The selected objective is0.0597806 of its initial value. Both head and body
gradients were live. This is operational training time, not a speed benchmark.

All19 model-to-weight and weight-to-CFA/RGB replays are exact. Independent
commissioning exercised the complete ROI-inclusive loss and fixed clipped-core
mask. The scored failures are therefore scientific development failures, not
an inactive model or observed reconstruction mismatch.

| Known window | RGB RMSE / current | Chroma RMSE / current | Prospective result |
| --- | ---: | ---: | --- |
| Curved interior |0.71788|1.09541|Colour fails|
| Curved positive |0.72091|1.13113|Colour fails|
| Near-fine/far-coarse positive |0.85095|0.99653|Pass|
| Genuine glint core |0.87276|1.01027|Pass|
| Weak-colour components |0.87105|0.87217|Pass|

Both flats pass and remain essentially uniform averaging (RGB ratios
0.99978/0.99972 to uniform), rather than demonstrating a new denoising gain.
No eligible component-retention guard fails. That does not mean every component
improves: weak-colour green-near recovery falls0.72379 to0.67901, about6.2%,
while red/blue improve. Near/far and glint projections slightly above1 earn no
extra detail credit. Lower RGB can reward smoothing; these independent absolute
colour and component checks are what make the tradeoffs visible.

The curved positive chroma rises0.00486400 to0.00550183. This is actual colour
harm relative to current, not merely failure against the uniform reference.
RGB improves0.01136408 to0.00819244, so the development loss is choosing
a luminance/colour tradeoff. Its small chroma weight need not reproduce the
prospective colour protection. No photographic admission follows this fit.
Compared with the old737-parameter run, training exposure, loss and capacity all
changed; this result does not isolate signed/cross-scale evidence as the cause.

ARGUED revision2: warm-start the selected checkpoint and train on the expanded24
plus the known19, with unchanged architecture and optimizer. Change only the
chroma multiplier from0.5 to2.0 consistently in the global and fixed-ROI image
losses; retain the gradient, flat-KL, ROI-total coefficients, clipping convention
and every acceptance bar. This explicitly gives colour error comparable weight
to the large RGB term instead of relaxing its failing guard. Predict reduced
curved colour harm while retaining useful RGB margins; neither outcome is
guaranteed. Do not spend another fit on the old19 alone or use fresh challenge
results to choose this revision.

The late loss excursion after step1536 and partial recovery do not establish
convergence or justify more steps on the same data. Expanded independently drawn
case noise and physical texture/geometry diversity are the next uncertainty.
Keep the program's total20-GPU-minute/three-attempt limits. Only a frozen model's
fresh independent assessment can support a separately justified complete-photo
observation; a failed conjunction stays recorded as failed.

Bindings: training receipt
`459fa8021ee67999b9cab7c9d3299be27cf2be5e1fb247adeac8e1eea6624e2d`;
screen `b97da529a28124a7018813c589fbeced5a1c7b494215ff8b04a9e5f1a38d19c7`.

# Fixed bilinear native-grid reconstruction control

MEASURED by `python experiments/quality-september14/joint-cfa-controls.py > experiments/quality-september14/joint-cfa-controls-3.log`, frozen solver SHA256 `05fe15bece42cb44f667219c35423261358bc4b8c5b594b0c2630c545748b490`. No RAW reads. This tests a native 1x consumer, not super-resolution or the camera noise calibration.

The fixed consumer does not clear a broad image-quality bar. Independent chromatic detail improves on all six cases, but two neutral cases have higher RGB truth error than even the single anchor MHC. All six neutral cases fail the prospective RGB-or-chroma bar against the same-data nine-frame MHC/bilinear-gather mean. That mean is a diagnostic comparator, not the shipped Catmull-Rom gathering/merge path.

| Continuous scene | Joint RGB RMSE | Anchor MHC | Diagnostic nine-frame mean |
|---|---:|---:|---:|
| Neutral, x, .20 cycles/native pixel | .011771 | .006687 | .005741 |
| Neutral, oblique (.24,.18) | .025546 | .015631 | .015588 |
| Independent colour, x, .08 | .001632 | .009004 | .006431 |
| Independent colour, oblique (.24,.18) | .018139 | .071286 | .050694 |

Flat controls ran first. With the same two independent noise draws, fractional-phase joint RGB RMSE is .005667/.005642 versus .001403/.001427 for the diagnostic mean and .005158/.005060 for the anchor. The extra detail is not free of noise cost. Noiseless flat bias is below 3e-8. Noise is an injected synthetic WB-scaled Gaussian model, not evidence for camera calibration.

All nominal channels report CG convergence. Exact two-dimensional integer-phase sampling gives .001061 RGB RMSE for the fixed independent-colour oblique .30 case, fractional shifts .018139, coincident sampling .045851: conditioning alone cannot erase the forward interpolation model's error. Exact duplicated observations change the output by .000369 maximum because data/prior balance changes; this adds no information.

Controls have power: reversed maps increase the fixed chromatic case's RGB truth RMSE from .018139 to .092547, while the flat wrong-map placebo changes by less than 1e-6. Eight defocused observations mixed with one sharp anchor increase its error to .036841. The coincident .30/-.20 red-only alias pair has bit-identical CFA data and identical output, with errors .044879/.029003 against its two different native truths. Removing all blue data yields explicit NaNs and `NO_USABLE_OBSERVATIONS`.

Truth is evaluated continuously at the actual observation coordinates, independently of the solver's bilinear basis. RGB error penalizes biased contrast, phase shifts and manufactured texture; flat error exposes noise amplification. Neither data residual nor a contrast-only score is accepted as quality evidence. All outputs are compared at native coordinates with an eight-pixel interior trim.

Run 1 is invalid: my fixture used integer `full_like` coordinates for the native reference's constant green channel, truncating .35 to zero in chromatic truths. Run 2 fixes that defect by explicit floating coordinates. Run 3 preserves all run-2 nominal results exactly and adds an integer/floating-coordinate regression, known native truth/CFA consistency, and the promised flat wrong-map placebo. No solver or acceptance-bar adjustment was made.

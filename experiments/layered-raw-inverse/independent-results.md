# Independent first-screen interpretation

MEASURED by root in55.218s; independently reviewed without refitting or rendering.
The frozen screen rejects this prototype (`known_optics_utility_pass=false`),
but contains useful reconstruction evidence and does not close layered inversion.
Result SHA256:
`cb26cc5a5358ebc054e867c2da974717f7084f7b5144d7bbb0bdbae4bfb8a460`.
Root's exact command and execution are retained in `screen-1/invocation.json`
and `process.json`; input bindings and four case receipts are unchanged.

The layered scene passes every registered latent-image truth bar. Whole RGB
RMS is235.11DN versus496.88 for fixed-far and753.72 for the training mean;
core is1064.73 versus1786.24/3452.13, and crossing848.92 versus1532.73/2763.99.
Glint component recovery is0.837–0.855, while the protected glint-free coloured
ridge reaches0.915–0.939. These exceed the independently selected noisy-donor
components. This is more than suppressing the highlight: the separate real
filament protection passes. The comparators remain the restricted fixed-far
inverse and diagnostic mean/donor, not the product focus stacker.

Prediction rejects that same reconstruction. Held focus0.25 has global RMS
1.166 supplied sigma but bright41 samples read4.280, against1.75 allowed.
The global average would hide the target-relevant defect. At focus0.75 there
are no bright-subset samples; its1.276 global pass is not a second bright
confirmation. Held samples are all uncensored, so this failure cannot be
explained as mistakenly scoring a censored value against its ceiling. Exactly
one layered training site exercises censoring; this is a live but very small
saturation demonstration, not validation on broadly clipped photographic cores.

The far-only scene helps re-choose the explanation. Its two-layer result passes
the registered image comparison, yet bright43 held samples read6.738sigma.
The correctly specified fixed-far one-layer model is worse, at9.466sigma.
Thus unknown visibility or a wrong two-layer architecture is not necessary for
the bright prediction defect. Both optimization error and the shared regularity
penalty remain possible. The angular-illumination case fails global prediction
1.586/1.704 and bright10.004, while its glint and ridge components still look
good. This shows that good latent component scores do not guarantee forward
adequacy. Because in-family bright cases already fail, it does not establish
a selective physical-mismatch detector.

Flat performance is a separate failure: RGB/chroma RMS8.675/12.346DN against
mean6.018/8.368; the far-only inverse gives5.606/7.776. All flat heldout channels
nevertheless pass near1sigma. Read-only inspection of the saved two-layer state
on the fixed16:80 interior finds alpha0.132–0.885 and near/far disagreement
38.90DN RMS despite constant scene truth. Their weighted errors have negative
covariance in every colour. Composite mean bias is below0.3DN per colour, so
this is predominantly spatial error, not a global offset. This is concrete
latent compensation, consistent with weakly constrained directions that the
observations blur away; it does not prove an exact algebraic nullspace or that
all of the excess noise has one cause. A forward-residual pass alone cannot
protect the output's flat noise.

The histories do not establish convergence. From step140 to159, layered
two-layer data NLL drops4.01140→4.00548 and prior3.72001→3.70683 together;
gradient norm remains0.106. In the far-only scene's correct one-layer fit,
data drops4.05942→4.05114, prior1.98427→1.98400 and gradient remains0.271.
Flat two-layer objective is much closer to stationary (gradient0.00330),
although still moving. Declining data and prior together are evidence of
remaining descent, not evidence that the final error is the optimum's
regularization tradeoff. Conversely, nonzero parameter-gradient norm alone
does not quantify recoverable image quality. Strong-prior bias and finite-budget
underfit have not been separated.

Numerical optics are another distinct limit. Same64-ray independent forward
code agrees within0.043DN, so its implementation discrepancy cannot explain
multi-sigma held residuals. But64 versus1024 rays fails the frozen continuum
guard: crossing RMS1.069–1.678sigma, with one whole-domain value0.887.
That discrepancy is absent from this matched64-ray inference problem and
cannot excuse its failure; it independently blocks application to real optics.
Wrong visibility is a live233.78DN crossing destroyer. Source immutability,
actual training-only access and poisoned-heldout initialization checks pass.

**One next intervention:** a bounded solver-only convergence continuation of
the saved flat, layered and far-only fits, keeping the exact observations,
64-ray forward operator, likelihood, priors, parameterization and quality bars.
Use one predeclared line-search method with a fixed evaluation cap; do not change
the prior or optical family at the same time. Include the correctly specified
far-only arm, which removes visibility estimation as an explanation. Record
objective and stationarity as well as the original truth/prediction bars.
If substantial objective descent improves bright prediction, underfit was
load-bearing; if a demonstrably better-converged objective retains bright bias
or flat compensation, the next issue is the objective/parameterization rather
than more Adam steps. Neither outcome repairs this first result retroactively.
This is justified by the positive reconstructed detail and nonstationary
histories, not permission for an optimizer or prior sweep.

Saved-state inspection used only NumPy reads of `two-layer/reconstruction.npz`
and `truth-rgb-f32.npy`, slicing16:80 on both axes and computing alpha range,
near/far difference, composite mean error and weighted-layer error covariance.
No forward prediction, optimization, RAW read, image rendering or new acceptance
metric was executed by this reviewer.

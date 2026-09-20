# Independent composite-prior result interpretation

MEASURED by root in composite-1; independently reviewed from receipts, scores
and saved latent arrays, without refitting or rendering. The fixed replacement
fails every in-family case. All eight arms finish their1000 iterations but
remain nonstationary at1e-6; this rejects the bounded recipe, not either
objective's global optimum or the entire layered-reconstruction family.
Independent-score SHA256:
`3234da9d72352b995eddb8bf685ac425c612717bf802ef9b68aa456e2c413e48`.
The actual command is in composite-1/fit-process/invocation.json; fitting took
224.578s. Bindings, same starting states, training-only access, fixed evaluation
bounds and logical-gradient equality passed. Original model/controls remain
frozen, and no state was selected by its truth score.

Commissioning passes both opposed mechanisms. The new image penalty detects
opacity texture over constant sheets, but permits variable sheets whose
composite is constant. The actual fitted states exploit the second freedom.
This is not an implementation that accidentally omitted the new term: its
independent Huber values, live alpha derivative and unchanged one-layer gradient
all pass. These arithmetic controls do not establish a useful reconstruction.

Flat RGB/chroma RMS improves relative to the long original arm,
43.301/65.698 ->11.390/10.352DN, yet both absolute mean-reference guards fail.
The original160-step RGB error was8.675DN and mean is6.018DN. Re-choosing the
interpretation of the new11.390 is important: its per-colour mean errors are
[-8.173,-4.015,-15.226]DN. The RMS decomposition is10.243DN bias and4.983DN
mean-removed spatial variation. Original43.301 has only0.224DN bias. Thus the
replacement removes much of the noisy texture but substitutes biased radiance;
calling all11.390DN "flat noise" would conceal the failure direction. These
descriptive components do not replace the fixed absolute RGB/chroma bars.

Saved flat sheets substantiate latent compensation. On the same16:80 valid
interior, near/far disagreement grows from38.90DN RMS initially to131.08 with
the original prior and2412.29 with the replacement. Original alpha spreads
from approximately0.132–0.885 to0.000357–0.999896, while the sheet values remain
relatively modest. The replacement instead permits very different sheets,
including near values up to22732.75DN on this genuinely constant scene; their
weighted errors strongly oppose one another in every colour. The physical
flat truth does not identify a unique alpha, so disagreement with its chosen
0.35 is not itself a quality failure. The failure is their wrong delivered
radiance while observations remain plausibly fitted. Original flat held RMS
stays1.002/1.021sigma; composite1.166/1.179 also passes. Those forward passes
cannot certify the output.

The structured failure is much larger. Layered whole/core/ridge RGB error
changes260.55/1117.53/519.13 ->941.56/4331.20/1908.08DN. All paired protections
fail. Glint component recovery falls from1.006–1.022 (slight overshoot, not
extra real detail) to0.047–0.053; genuine filament recovery falls from
0.948–0.988 to0.239–0.362. Bright held residual is2.654sigma and the other
held view's global1.845 also fails. This is destruction of both the compact
highlight and separate real structure, not just successful fan suppression.

At the fixed planted glint centre(x45,y48), true alpha is0.04433 and true
pinhole RGB is about[28844,28299,24850]DN. Composite alpha reaches1 and the
delivered pixel becomes its near sheet,[2911,3335,3036]DN. Its hidden far value
there is[503,15982,80236]DN. Interior sheet disagreement is14867DN RMS, versus
1336 initially; near values reach371591DN. These are not claims that arbitrary
above-ceiling scene radiance is physically forbidden: latent radiance may
legitimately exceed the sensor ceiling. They show the wrong learned occlusion
and large hidden radiance on this known scene. The forward model integrates
shifted common rays; low pinhole contribution does not mean those hidden
fields make zero contribution to the finite-aperture observations. Exact
ray-by-ray attribution was not run, so the specific routes are not proved.

The far-only scene is an independent discriminator. It contains no foreground,
yet composite core alpha averages0.582 and reaches0.9999998 at the glint
centre. Its whole RGB error is1016.86DN versus174.85 for original, and held
bright/global checks fail. A real ambiguous occluder or angular illumination
mismatch is therefore unnecessary for this failure. Angular mismatch also
loses real detail; its improved bright residual cannot rescue its image or
the failed other held view.

Do not compare different objectives' TOTAL values as data fit. Layered
composite's within-arm prior falls5.396->0.689 while data NLL changes only
4.005->3.994, worse than paired original3.813. Far-only and flat composite do
improve training NLL more than original while worsening held prediction,
supporting overfitting through newly released latent degrees of freedom.
Original flat itself lowers total3.68207->3.65557 while amplifying output
error fivefold. These are observed harmful descent directions. Nonstationarity
prevents claims about the final optimum; it does not erase these actual harms
or justify another duration/penalty sweep.

**Next bounded causal mechanism:** freeze true alpha in the existing flat and
layered cases and solve only their two radiance sheets with the original sheet
prior, same saved starting sheets, observations and fixed1000-step solver.
Compare against the retained original-prior1000-step arms, retaining the
original absolute bars and paired detail protections. Record the conditioned
initial output so simply recomposing with the correct matte is distinguished
from fitting. This oracle intervention tests whether opacity freedom is
load-bearing; it neither clamps dynamic range nor tunes a penalty. A success
would justify an actual-RAW route that estimates/validates visibility from
focus diversity before conditional radiance reconstruction, rather than letting
every pixel invent opacity and hidden light jointly. It would not supply that
estimator or authorize a photographic run by itself. A failure would show that
fixing visibility is insufficient. The64/1024 pupil issue remains separate.

Supporting read-only inspection is saved in independent-composite-latents.json.
It loads only existing reconstruction.npz files and the frozen scene() truth;
f32 array differences/compositions and f64 summary reductions describe the fixed
valid interior, protected core/ridge and planted centre. No model prediction,
new quality gate, optimization, RAW read or image render was executed here.

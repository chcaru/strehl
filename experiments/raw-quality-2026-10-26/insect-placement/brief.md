# Fixed thorax paired-gap placement discriminator

2026-10-26. Root allocation `insect-placement`. **Prepared, unexecuted.** This is a possible geometric attribution test, not a photographic improvement or a license to apply a hand-selected warp. Only root schedules execution. Four decoder invocations cover exactly three unique originals: RawPy104/105/106 and one independent existing rawler-based decode of105.

## Frozen nomination before RAW fitting

Viewed the saved complete384-square `source-locator-1/thorax-texture-source-{104,105,106}.png` at native size. Their persistent bead/gap topology permits one conditional nomination attempt. All three source-native crop origins are `[4592,2608]`. These are zero-based source indices, corresponding to DSC00105/106/107.ARW. The original native frozen site is `[4520,2560,384,384]` in delivered reference149 coordinates, but these saved source crops retain each source's own scale and rotation.

- Feature A: dark gap near crop-local `(178,199)`, source105-native `(4770,2807)`. Nomination context `[128,160,128,128]`, saved as `nomination-a-context.png`.
- Feature B, held challenge: different dark gap near crop-local `(88,205)`, source105-native `(4680,2813)`. Context `[32,160,128,128]`, saved as `nomination-b-context.png`.

Both contexts are unchanged source105 PNG subarrays, with its ICC; they are visual nomination aids, not new measurements. Coordinates are approximate anatomical correspondence hypotheses, frozen before any RAW profile or numerical fit. Irregular boundaries or contaminating glints can still make the actual profile inadmissible. No coordinate, feature, threshold, interval or parameter sweep will rescue such a failure.

## Concrete observation

Use exact retained global-map transforms to map source105-native query positions through reference149 into sources104/106. Do not pretend all source crop pixels coincide because their rounded origins happen to match. Keep physical G1 `(1,0)` and G2 `(0,1)` at pitch2 separate. Bilinearly query only each phase's actual original u16 sensels; R/B cannot enter the sampler. This is a measurement consumer, not a new stack interpolation path. Arithmetic fields are f32, geometry f64, stored inputs u16. No aligned-frame volume is built.

For each nominated gap, use fixed horizontal and vertical profiles, offsets `[-16,16]` every0.25native pixels, averaging three parallel traces at tangent offsets `[-2,0,2]`. Oversampling does not create new information; noise replicas reuse the original physical sensels and therefore preserve interpolation correlation. Each profile uses its fixed central `[-1,1]` median as the gap level, outer `[-16,-12]` and `[12,16]` medians as the separate bright shoulders, and each side's halfway level as its edge. There must be exactly one correctly signed crossing inside each fixed edge window `[-10,-1]` and `[1,10]`. Missing/multiple crossings or insufficient contrast refuse the feature. No derivative maximum, phase correlation or photometric-residual ranking supplies correspondence.

Record left/right edge positions, midpoint and width separately. A common displacement of both sides is necessary for translation; opposite-sign widening is not. Feature A proposes a two-component center displacement; B and both independent phase lattices challenge it. Report source105-native displacement, then convert it by `a_i/a_105` to source-i-native correction units; these are not reference149 plane pixels. The sign convention is residual feature displacement in mapped source105 coordinates; a matching pull correction adds its source-i image under the relative linear transform.

The single injected sensor model is the baseline ISO100 Sony profile, `g=100/436.8 DN/e`, read noise4.20electrons, black512, variance `g*max(DN-black,0)+(4.20*g)^2`. Its known read-model/calibration limitations remain; no private noise estimate is fitted.64 fixed-seed native-sensel noise replicas give conditional model uncertainty, not measured temporal noise. All actual profiles and rejection reasons are saved. Geometry evidence requires center magnitude at least0.35native pixels and above3sigma plus0.20pixel mechanical allowance, consistent opposite-side displacements, consistent phases and held B, and a stable valid result on at least48/64 replicas. These engineering bounds do not imply a photographic gain or exclude smaller misplacement.

## Controls and stopping

Flat first must refuse invented edges. A known translated two-gap plant must recover `(0.75,-0.5)` within0.25native pixels in both phases. Fixed-center symmetric defocus must retain the center within0.20pixel while changing width, and cannot qualify as translation. A changed off-center glint with stationary geometry must not qualify through the held feature. Physical-phase affine ramps and a deliberately wrong phase address exercise coordinate correctness. The controls use known mathematical stimuli, not a model fitted to validate itself. Their failure closes this numerical recipe before real measurements; it does not justify changing the thresholds.

The numerical stage is bounded to60seconds wall after loading the small caches, at most four threads and4GiB under the root's existing Windows Job runner. It emits flushed phase/feature progress and a terminal result. A healthy running measurement is producing bounded profile/replica progress; a parseable partial JSON is not completion. No interval expansion or full render is authorized by this brief. If either feature or either phase refuses/disagrees, report inconclusive and retain both features.

Read prior `marigold-edge-origin/{model,independent-controls}.py` and independent results: their extrema controls establish coordinate/sign expressiveness only, with finite sampling error. They do not justify matching real multiple edge families. Read marigold-local-placement's held-fit refusal and the current farther-correspondence nomination stop. This test changes the subject to persistent close-focus scale gaps and uses fixed crossings, but does not waive those identification failures.

## Root commands, not yet executed

`python -B -X faulthandler experiments/raw-quality-2026-10-26/insect-placement/run.py stage --out <fresh-cache-directory>` performs only the allocated decodes/bindings. `... run.py measure --cache <cache-directory> --out <fresh-result-directory>` runs controls first, then the fixed photographic profiles. Root must wrap both with the existing bounded process controller and supply the stated memory/thread limits; only the measure stage gets the60second numerical cap. The script never writes inside the capture corpus.

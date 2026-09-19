# Independent decision: admit one paired photographic render

**MEASURED:** both ISOs pass the frozen generated screen, including the
pre-run green-zero-crossing guard. **Decision:** one complete 70-frame
vitamin-C comparison is justified. This is not default promotion, SOTA
evidence, or evidence that the photographed fans are fixed.

| Candidate/baseline RGB truth RMSE | ISO100 | ISO400 |
| --- | ---: | ---: |
| Flat | 0.935167 | 0.934155 |
| Neutral detail | 0.579204 | 0.592777 |
| Genuine coloured detail | 0.860425 | 0.810321 |
| Coloured varying focus | 0.887588 | 0.910344 |
| Varying-focus R/B error at fixed green zero crossings | 0.900729 | 0.925841 |

The benefit does not rely on the pre-run amendment allowing flat improvement:
both genuine-colour cases independently improve by more than 5% at each ISO.
Flat chroma error rises slightly, to 1.004556x/1.002519x, so the result is not
uniform improvement of every noise measure. Genuine-colour components improve
except for varying-focus red/blue at ISO400; the largest relative component
loss is 1.56% in red, within the 10% guard. Neutral amplitude falls from roughly
1.15–1.17 to 1.09 relative to truth, while RGB error decreases substantially.
The truth cap correctly avoids treating removed excess contrast as lost signal.

I rechecked the following choices rather than only the ratios:

- **Units and target:** actual `load_frame` builds green as 0.5*(G1+G2) from
  black-subtracted gathered source DN. The collapsed target uses that same
  expression on baseline G1/G2, before WB/range normalization or development.
  `luma_variance` supplies squared `green_luma_sigma` in DN squared, so the
  dimensional comparison is consistent. It remains an uncalibrated heuristic:
  variance of the correlated source-minus-target residual is not established
  by reusing the source guide variance. Measured per-band beta belongs to the
  baseline pyramid, not this pixel-intensity difference test.
- **Truth coordinates:** fixtures invert the supplied native pull around the
  full native centre with translation 2*b; scoring restores twice the quad crop
  origin before evaluating independent analytic truth. Odd decoded active
  origin is a storage offset, not a shift of truth. Non-unity WB is divided out
  in source generation and restored in camera-linear RGB. Source known-site
  slots equal the actual gather, and replay guide/variance hashes match the
  canonical baseline. No hidden tone or registered truth image is used.
- **Fallback and participation:** on the whole 18125-quad crop, varying-focus
  fallback is 938/91 quads (5.18%/0.50% at ISO100/400). Coloured stationary
  detail uses 2927/546 fallback quads (16.15%/3.01%). The rule is therefore live,
  not mostly an unchanged-baseline placebo. However, varying focus accepts
  exactly one source at 75.47%/66.85% of quads. Describe it as whole-tuple
  projection with selective averaging, not general multi-frame denoising of
  resolved detail. These counts cover the full crop; scored errors exclude its
  outer 24 native pixels, so they do not attribute improvement pixel by pixel.
- **Context-loss counterexample:** the 3838 fixed zero-crossing pixels are
  selected from clean analytic green phase, independently of candidate errors
  or acceptance. Their R/B error improves at both ISOs, so this particular
  frozen relative-risk test does not reject. The subset is defined at native
  truth pixels, not by an exact equality of the noisy two-site quad guide;
  passing it does not prove all equal-intensity contexts are safe. The depth
  fixture is a smooth focus gradient, not an occlusion boundary or transparency
  model.
- **Ordering and information limits:** all eight reversed replays reproduce
  candidate RGB exactly, as well as target, acceptance counts and per-source
  masks. The actual helper exercises inclusive boundary admission, rejection,
  zero variance and 24 bit-exact fallback samples. It also demonstrates two
  limitations: incompatible colours with identical green are averaged, and
  clipped red with matching green is admitted. Neither becomes a colour-safety
  or clipping-repair claim because the aggregate quality screen passes.

This comparison also changes representation: it retains co-sited source RGB
instead of final MHC reconstruction of the merged CFA. These results do not
separate that benefit from the green-target acceptance rule. The earlier
phase-packed work showed that a favourable generated representation result
can fail to remove the actual photographic defect; the full comparison is
therefore the next decision, not a validation formality.

The full adapter must retain the canonical baseline, held geometry/crop,
source-colour CA pulls, all-twelve-slot source support and common tone/WB.
Reuse the already-controlled full-source gather and rerun generated controls
after the bounded adapter extension. Keep acceptance-count evidence with the
photograph so unchanged fallback and single-source projection remain visible.
No new threshold, gate or source choice is requested here.

Evidence: `controls-1/output/screen.json`, SHA256
`6064b1a5c9f724904a81e188f4604658eed84456b3e48e6baa937c2f62b2215c`;
`controls-1/{invocation,completion,process}.json` and `process.log`.
Root ran `build-1/cli-tests.exe merge_cmd::green_match_rgb::independent_controls:: --nocapture --test-threads=1`:
two tests completed in 1.765 s job wall time. `build-1/process.log` contains a
fresh `Compiling strehl-cli`; executable SHA256
`4ad2b6d8462a64307278e178e72edcfd4410d7d8581f2db6d0a48d278ce0761a`.
Bindings confirm unchanged frozen controls/plan and implementation. This
review changed only this document and performed no new experiment or RAW read.

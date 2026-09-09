# Angular-spectrum scale prototype: rejected

2026-09-09. **MEASURED and independently reviewed:** close this fixed direction. Literal shift/identifiability controls pass and the radial/separable nulls refuse correctly, but the estimator gives confidently wrong scales on the fixed multiple-depth/window input. No production code or default changed.

All errors below are absolute log-scale errors multiplied by the original M103 CFA-plane half-diagonal,2112.853047px, relative to rung144. They are scale-equivalent placement errors in that gauge, not pixels in the512x512 analytic images. Seven rungs0,8,64,128,144,200,298 carry the existing curved track.

| Fixed arm | Ordinary accepted | Centred accepted | Ordinary mean / max error | Centred mean / max error |
|---|---:|---:|---:|---:|
| No blur | 0/7 | 6/7 | Not measured | 0.021041 / 0.041972, accepted subset only |
| Unequal radial blur | 0/7 | 6/7 | Not measured | 0.021410 / 0.040924, accepted subset only |
| Multiple depth + window | 7/7 | 7/7 | 8.260266 / 21.924637 | 13.042398 / 38.727694 |
| Radial null | 0/7 | 0/7 | Not applicable | Correct refusal |
| Separable-spectrum null | 0/7 | 0/7 | Not applicable | Correct refusal |

The first two centred arms refuse rung298. Missing ordinary errors cannot be treated as infinity; the tiny conditional centred errors are evidence of availability on six rungs, not the required complete quantitative advantage. In the multiple-depth/window arm, every non-reference centred estimate passes the confidence tests yet exceeds the fixed2px cap. At interior rungs128/200, centred errors are13.9295/23.2763 versus ordinary0.8179/7.5339. Re-choosing only interior, non-reference rungs retains the loss.

The radial-cancellation identity remains an algebraic result under a single radial convolution. The fixed violation changes depth mixture and spatial window together, so it cannot isolate their individual contributions. Confidence gates distinguish the commissioned information-loss nulls but do not certify this model assumption. A narrow successful control cannot rescue the failed consumer quantity.

Source c2cfd3bb6325acaf1fb800a94f96d77a058b0818 includes the frozen operator, independent controls, fixed design and runner. The actual command was:

~~~text
C:/Users/chris/AppData/Local/Programs/Python/Python312/python.exe -I -B experiments/alignment-angular-spectrum/run.py
~~~

One process completed all70 descriptor/rung rows after independent controls, with exit0 and clean terminal accounting. Cost was1.75s child wall,1.109375s owned CPU and52633600 bytes maximum Job committed memory. These are synthetic experimental costs, not native alignment speed. No RAW capture was decoded.

The [independent decision](decision.json), [review](independent-review.md), [all per-rung results](run-1/results.json) and [process receipt](execution-1/process.json) preserve the outcome. Do not retune the stimulus, spectrum support, window or confidence thresholds, or launch a native comparison of this variant.

Next: the separately allocated direct-plane handoff removes the current gather's redundant u16 write/read round trip into already existing f32 merge planes. Its rounded control must first preserve actual outputs; a separate unrounded precision hypothesis must earn any quality claim. See [next decision](next-decision.md). Existing native speed gains and SOTA status are unchanged.


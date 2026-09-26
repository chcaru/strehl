# Training-only preservation diagnosis

2026-09-26. **MEASURED by root:** `python
experiments/cross-scale-band-guide/independent-training-diagnosis.py --out
experiments/cross-scale-band-guide/training-diagnosis-1/output` completed in
1.672s. The JSON records exact invocation/input hashes. No fit, parameter search,
new target, fresh held pixels or photographic data were read by this diagnosis.
It reuses existing independent scoring and the pre-fit training annotation ROIs.

Training already contains the fine-contrast failure. At wavelength4 native
pixels, R/G/B recovery falls1.0475/.9834/.6862 to.8733/.8163/.5702, roughly
16.6–17.0% raw attenuation, while RGB error improves3.86%. At wavelength16,
recovery falls1.0093/1.0290/.9949 to.8900/.9005/.8660 (11.8–13.0% loss), while
RGB improves11.45%. At wavelength32 it falls.9389/.9448/.9315 to
.8376/.8416/.8321 (10.7–10.9% loss); RGB worsens2.46%. These fixed training
windows differ in size from the independent transfer windows; compare direction,
not their raw error magnitudes.

The whole training Gabor case contributes only1.229% of the selected43-case mean
loss. Its finest carrier's explicit ROI term contributes0.0808%, and the next
three0.0837%,0.0561%,0.0426%. These are the added ROI shares; the same pixels also
participate in global image/gradient terms. Independently recomputed total loss
matches the selected checkpoint. Relative to the warm start, Gabor loss rises
0.185% while the aggregate43-case loss falls21.53%.

The new training unclipped-glint case does **not** show the failed transfer
adjacent-detail effect: adjacent recoveries improve.8856/.9238/.8354 to
.9229/.9606/.8740 and RGB improves6.34%; core RGB improves27.21%. Training
clipped-adjacent RGB worsens2.70%, with only0.90–2.24% component reductions.
Do not claim the fresh unclipped failure has been reproduced in training.

The old known curved case remains a supervised tradeoff: selected-case loss is
10.05% above its warm-start value under the same revision2 objective, and positive
chroma error is1.13932 current. Thus aggregate checkpoint selection sacrifices
some existing supervised cases; this is not only a held-domain explanation.

**ARGUED choice for the final bounded revision:** add general local contrast
preservation against a truth-projected native-current reference capped to[0,1],
as a lower bound, while retaining RGB/chroma/gradient losses. Current B recovery
.6862 is not a proven representational ceiling, but forcing every color to unit
contrast could push an unsafe CFA/MHC compromise. The lower bound protects
demonstrated recoverability without preventing the image losses from improving
it. It is training-only; no inference comparator or photographic fallback.

With coefficient.001, a0.1 absolute projection deficit contributes1e-5 before
the mean over eligible windows/channels. This is not a uniform10% relative-loss
penalty. Gain and truth-orthogonal noise are blind directions of the one-sided
contrast term and must remain controlled by the complete image objective and
independent error tests. Preserve all earlier rejections. Any reused challenge
after this diagnosis is a known regression screen, not new independent evidence.

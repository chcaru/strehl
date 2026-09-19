# Complete periodic all-CFA screen

MEASURED: the frozen screen passes all eight scene purposes at both ISOs and
both crop phases (32 cases). This admits the next boundary/composed-gather
test only. It does not admit a photographic replay or production promotion.

Commands run from the repository with Python3.12:

```
python -I -B experiments/complete-cfa-wavelet/run.py build --out experiments/complete-cfa-wavelet/build-1
python -I -B experiments/complete-cfa-wavelet/run.py controls --build experiments/complete-cfa-wavelet/build-1 --out experiments/complete-cfa-wavelet/controls-1
```

Fresh core/CLI compile: build wall146.000s; two control tests wall3.625s.
These are process receipts, not comparative performance claims. Screen SHA256:
34ccc611cf3e2441c4c173116b6b0a13797fb21af9c08dbfc61688a75fc6c6bd.

Candidate/baseline RGB truth-error ranges across the four ISO/phase settings:

| Scene | Ratio |
| --- | --- |
| Flat | 0.8116–0.8191 |
| Horizontal | 0.8063–0.8969 |
| Vertical | 0.8119–0.9000 |
| Diagonal | 0.9418–0.9774 |
| Equal-focus genuine colour | 1.00025–1.00034 |
| Varying-focus genuine colour | 0.99954–1.00043 |
| Coarse neutral | 0.8540–0.9091 |
| Weak red, warm WB | 0.9077–0.9109 |

Error may reward smoothing; it is paired with truth-capped component recovery
and known destroyers. Coarse candidate components recover0.9902–1.0100 of truth.
Weak-red retention is91.01–91.05% of the predetermined focused source, narrowly
above the fixed90% guard. It is not evidence that weak chroma is generally safe.
Neutral diagonal amplitudes remain1.086–1.097: excess contrast remains a defect,
even though the combined error/detail guards pass. Genuine-colour RGB error is
effectively unchanged, not a colour-quality improvement claim.

Full complex roundtrip max4.81e-7; constant-plus-spike variance oracle max
1.29e-6; old one-level analysis/synthesis bit-exact. Observer on/off preserves
both RGB outputs and all eight collapsed CFA planes by hash. Original active
u16 routing and independent per-plane model mapping pass. This validates the
operator and supplied variance propagation, not real sensor calibration.

The baseline requests seven bands but reaches four detail bands and an8x8 base
on128x128; the candidate reaches seven and terminal1x1 DC. Their exponent ramps
therefore differ too. The baseline/smooth5 clamp while the transform wraps, and
the whole output includes MHC boundaries. This cannot isolate a wavelet-only
cause, prove natural-image boundary behavior, or prove fractional covariance.
The prior two-level rejection remains intact; fixtures here are periodic and
use different full-domain scoring. Do not attribute the cross-screen change
to decomposition depth alone.

Independent interpretation is in results-review.md. The next design must
address actual gathered original-sample reuse and natural boundaries before
the first complete RAW image from this candidate is eligible for review.

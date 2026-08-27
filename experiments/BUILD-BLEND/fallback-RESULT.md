# fallback.ps1 — RESULT

Commit of the scored binary: `27e4f72a` (my last pyramid commit: `e73c6d3f`).
`tweezers-cpl`, 100 frames, `--hard-max --gate 4 --base-mean --camera-linear`,
`STREHL_FIX_CA=off`, full-res 7040x4688.

## Verdict: all three repair arms FAIL. `mean` is the best of the four.

They raise amplitude and do not raise correlation. That is the exact failure
ORCH pre-declared an arm would be failed for.

| arm | 6-10 amp | 6-10 lag1 | notch amp | **notch r** | notch lag1 |
|---|---:|---:|---:|---:|---:|
| reference | 1.0 | 0.4437 | 1.0 | 1.0 | 0.7140 |
| **mean** | 1.1369 | 0.4584 | 0.4758 | **0.1191** | 0.5759 |
| best | 7.6255 | -0.0415 | 0.8869 | **0.1039** | 0.5261 |
| topk3 | 5.0619 | -0.0395 | 0.7706 | **0.1067** | 0.5392 |
| pow4 | 3.9329 | -0.0090 | 0.6944 | **0.1127** | 0.5581 |

Poles: synthetic i.i.d.-noise lag-1 +0.2107, strong-edge +0.8269.

Three readings, in order of how much they matter:

1. **Notch correlation does not move, and moves the wrong way.** r goes
   0.1191 -> 0.1039 / 0.1067 / 0.1127. Every repair arm is slightly WORSE
   correlated with the scene than the mean it replaced. Notch lag-1 agrees:
   0.5759 -> 0.5261 / 0.5392 / 0.5581. The amplitude that came back is not
   the scene's structure.
2. **The flat bins fail catastrophically, not marginally.** Amplitude 3.9x to
   7.6x, and lag-1 driven to ~0 -- *below* the i.i.d. noise pole of +0.2107.
   Producing something less correlated than white noise means salt-and-pepper:
   isolated extreme pixels. That is what a max over 100 noise samples is.
3. **Ordering is exactly as pre-registered.** best worst, topk3 middle, pow4
   least bad, on both ends. P2 and P3 confirmed.

## P4 REFUTED, and I retract the reasoning behind it

I argued `Power` would "degrade gracefully to the mean" in flat regions
because the weights go near-uniform there. It does not, and the reason is a
property of the estimator I should have seen before building it: **power
weights are scale-invariant.** Multiply every `|L|` by any constant and the
normalised weights are unchanged. So `Power` cannot distinguish flat noise
from faint structure at all -- it sees only the SHAPE of the across-frame
`|L|` distribution, and that shape is peaked in both cases, because noise
has a maximum too. The adaptivity argument was wrong. pow4's flat-bin
amplitude of 3.93x is the measurement of how wrong.

## P1 SPLIT: the structure statistics reproduce, the amplitudes do not

My `mean` control is the shipped default, so it should reproduce ORCH's
published hard-max numbers. It half does:

| quantity | ORCH | mine | |
|---|---:|---:|---|
| notch r(aligned) | 0.1156 | 0.1191 | reproduces |
| notch pyramid lag-1 | 0.5708 | 0.5759 | reproduces |
| 6-10 ctrl lag-1 | 0.4437 | 0.4437 | exact |
| bin counts 465/168/21/18/16/410/428 | — | identical | exact |
| **notch ampRatio** | **0.3292** | **0.4758** | does NOT |
| **6-10 ampRatio** | **0.9586** | **1.1369** | does NOT |
| `averaged` line | 47.9/36.8/9.9/0.3 | identical | exact |

Same ctrl, same tiles, same tile counts, same structural readings -- and
uniformly higher amplitude at low DN. My leading candidate is lateral CA:
ORCH's clean6 blend was rendered with `STREHL_FIX_CA` unset, and that default
FLIPPED between their pin and HEAD, so an arm rendered later with the variable
unset has CA correction ON. CA correction resamples, resampling smooths, and
smoothing lowers amplitude at the noise floor while leaving structure
statistics alone -- which is the exact signature above. I set it off
explicitly to match what the ctrl's own log records.

This does not change the verdict: every arm here was rendered under one
protocol, so the four rows are comparable to each other regardless.

## What the data actually points at

The sub-gate population is 47.9% of the finest band. The notch tiles are 18 of
1660. Any operator applied to the whole sub-gate population to rescue those 18
tiles will be dominated by the noise-floor pixels that make up nearly all of
it -- which is precisely what these three arms measure.

So the fallback is the wrong place to fix this. The discriminator has to be
ABSOLUTE, measured against the noise level, not relative across frames. The
merge already has exactly that quantity: `gate * beta * var`. The defect is
that it is a HARD threshold, and a hard threshold in an estimator produces a
cliff in the output -- which is what a notch pinned to an absolute DN across
four subjects with 4x different amplitude ranges IS.

The next arm should be a **soft gate**: a continuous weight that approaches
zero smoothly as SNR falls, so the sub-gate population and its fallback stop
existing as a separate case at all. Nothing to patch, no cliff to sit in.

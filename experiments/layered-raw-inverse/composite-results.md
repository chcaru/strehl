# Delivered-image prior: rejected fixed comparison

MEASURED,2026-09-19. This is a generated-original-CFA reconstruction test,
not an improvement to the user's photographs. Both original and replacement
objectives begin at identical saved160-step two-layer checkpoints. Only the
placement of the image Huber penalty changes. All original model/controls
remain frozen; the failed previous screens are not relabelled.

```
python -I -B -X faulthandler experiments/layered-raw-inverse/run-composite.py --out experiments/layered-raw-inverse/composite-1
```

The bound Python312 runtime ran independent commissioning first in2.219s,
eight paired fits in224.578s, and independent scoring in3.172s. These are
operational costs, not speed comparisons. Source/input/checkpoint bindings
remain unchanged. Independent-score SHA256:
`3234da9d72352b995eddb8bf685ac425c612717bf802ef9b68aa456e2c413e48`.

Commissioning detects the intended algebraic difference: unequal constant
sheets with varying coverage have essentially zero original image penalty and
0.0613973 composite penalty. A compensating pair with a constant delivered
image has1.89309 original penalty and about1.5e-11 composite penalty. The
one-layer prior and its live radiance gradient are exact. A deliberately wrong
coverage-independent average fails the control. These establish the formula,
not image quality or camera calibration.

| Case / measure | Original objective | Composite-image objective |
|---|---:|---:|
| Flat RGB RMS, DN | 43.3005 | 11.3904 |
| Flat chroma RMS, DN | 65.6983 | 10.3519 |
| Layered whole RGB RMS, DN | 260.5475 | 941.5590 |
| Layered core RGB RMS, DN | 1117.5350 | 4331.2004 |
| Layered ridge RGB RMS, DN | 519.1288 | 1908.0803 |
| Layered bright held residual, supplied sigma | 2.4149 | 2.6540 |
| Far-only scene whole RGB RMS, DN | 174.8468 | 1016.8595 |
| Far-only scene bright held residual, supplied sigma | 2.9575 | 3.5570 |

Every in-family composite case fails. Flat improves relative to this longer
original run but still misses mean6.01845/8.36762DN and the original absolute
flat RGB/chroma error bars. Layered fails every original image bar and every paired core/ridge/
component protection. Component scores could credit overshoot; whole/core/
ridge RGB error counter that failure direction. Here both error and retained
components reject it. Angular mismatch remains descriptive and also loses
detail; lower held residual there does not excuse its damaged image.

All eight fits reach1000 iterations and remain nonstationary under the fixed
1e-6 parameter-gradient criterion. This is a matched-budget implementation
failure, not a proof about either objective's global optimum. Longer original
fitting also worsens the flat image from8.675 to43.301DN while lowering its
objective; the earlier loose-gradient stop did not establish a stable solution.
Good flat held-out prediction remains compatible with a wrong pinhole image.

The replacement is closed: no photographic render, default change, new
regularization coefficient or duration sweep. Saved latent inspection and
independent interpretation are recorded separately. Numerical pupil accuracy
is still unresolved, but the matched64-ray failures occur without that mismatch;
more accurate pupil integration cannot explain them away.

Independent saved-array inspection in independent-composite-results.md shows
that composite flat error is mainly bias: bias RMS10.243DN and mean-removed
spatial RMS4.983DN. Neither is a temporal sensor sigma. At the layered glint
centre, composite alpha reaches1 against truth0.0443 and hides a large far-sheet
radiance behind a dim foreground. Thus the penalty can remove actual delivered
detail while permitting large unseen light levels. No global optimum is implied.
The next two-case diagnostic fixes known visibility and fits only radiances with
the original sheet prior; it changes no coefficient or optical parameter.

For direct visual inspection the following command generated complete96x96
scenes under the same fixed display transform and marked supported interior:

```
python -I -B -X faulthandler experiments/layered-raw-inverse/display-composite.py --source experiments/layered-raw-inverse/screen-1/output --comparison experiments/layered-raw-inverse/composite-1/output --out experiments/layered-raw-inverse/display-composite-1
```

Root inspected complete-layered.png. The replacement removes the compact bright
core and most filament length; the numerical rejection is visually substantial.
These are complete generated scenes, not photographic stack outputs.

# V-VEILCLAW — what makes the tarsus in `bee-3-cpl` look hazy

**Verdict: VEILING.** The through-focus response at those pixels has two peaks.
The claw was captured sharply (frame 288 of 299); the merge kept its detail but
sat that detail on the foreground layer's bright pedestal.

## The measurement

`probe.py` is `experiments/ORCH-drift-check/throughfocus_probe.py` with three
changes, all forced by how the first attempt went wrong:

1. Every window that is measured is also dumped to a contact sheet under one
   shared display curve. You cannot run it and not see what you measured. The
   first attempt reported a near-flat probe from a window that was sitting on
   blank paper.
2. A **null** window is mandatory alongside the control. The control proves the
   instrument responds; the null proves it can stay quiet. An instrument only
   ever shown to respond has not been shown to discriminate.
3. `curve.py` adds prominence-based peak detection. The original `verdict()`
   takes `argmax` and asks only whether it is interior, so it cannot see a
   second layer even though the two-layer case is the one its own docstring
   says matters most. On this data it reported `INTERIOR-PEAK frame#182`,
   which would have been read as a merge defect.

Windows, in master coordinates:

| window | box | contents |
| --- | --- | --- |
| probe | `y 2640:2830  x 2080:2270` | the tarsus/claw |
| control | `y 3120:3450  x 1880:2250` | the neighbouring claw, sharp at f243 |
| null | `y 100:400  x 6500:6900` | far corner, plain paper in every frame |

```
python probe.py --win 2640 2830 2080 2270 --ctl 3120 3450 1880 2250 \
                --nul 100 400 6500 6900 --frames 0:299:1 \
                --outdir <out> --tag clawtight
python curve.py <out>/clawtight.csv --plot <out>/clawtight-curve.png
```

Result, thresholds unchanged from the original probe:

```
CONTROL: SINGLE-PEAK  floor=83.3  frame#244 prom=0.24
NULL   : FLAT (no peak with prominence >= 0.10 of floor)
PROBE  : TWO-PEAK     floor=84.2  frame#182 prom=0.45   frame#288 prom=0.29
```

The window sheet shows what those two peaks are: at f171–f198 the box holds
sharp, thin **foreground** hairs on otherwise blank paper; at f285–f291 it holds
the **claw**, and the hairs have dissolved into the background. Two layers, one
set of pixels, 108 frames apart.

## Where the contrast went

`unmix.py` splits the claw box into a base (Gaussian, sigma 32 px) and a detail
residual, with every plane normalised by its own paper white:

| plane | base mean | base p5 | detail rms |
| --- | --- | --- | --- |
| f288 (resolved the claw) | 0.581 | 0.206 | 0.177 |
| f180 (resolved the hairs) | 0.892 | 0.835 | 0.047 |
| master | 0.802 | 0.669 | 0.104 |

`corr(master detail, f288 detail) = +0.852`, and `master ≈ 0.50 × f288` in detail
amplitude. `corr(master detail, f180 detail) = -0.035`.

So the selection found the right frame. The detail is the claw's own, at half
amplitude, on a pedestal much nearer the foreground layer's than the claw's.
That is the haze.

## Not measured

`strehl-core/src/pyramid.rs` documents `BaseBand::Mean` as the default: the base
residual is a plain mean across frames, and `DEFAULT_MEAN_COARSE = 0` leaves
every Laplacian band selected. That is a plausible route for a bright pedestal
under a dark background object, and it matches the base/detail split above, but
it is a **lead, not a finding**. `meanveil.py` tried to confirm it and could not:
its paper anchor drifts with the bracket's illumination and its fixed box does
not track the claw, so the comparison it produces is not trustworthy either way.

## Drift

`drift.py` registers a frame to the master by NCC. Within one frame the required
shift differs by more than 150 px between image regions and grows with distance
from the frame centre, so this is magnification change (focus breathing), not
rigid motion. At the claw it runs about 0.35 px/frame in each axis. A fixed pixel
window cannot follow a feature across the whole bracket; the probe boxes here are
sized to tolerate the drift over the span that matters and were checked by eye at
several indices.

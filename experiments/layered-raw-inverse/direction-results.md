# A local radiance-prior tradeoff, with unresolved derivative sign

MEASURED,2026-09-20. Read-only diagnostic of the saved fixed-visibility layered
state; no new fit, coefficient change or photographic render.

```
python -I -B -X faulthandler experiments/layered-raw-inverse/run-radiance-direction.py --out experiments/layered-raw-inverse/direction-1
```

Python312 preparation/probe/scoring processes take2.032/2.360/2.063s. The saved
state and all input bindings remain unchanged. The reproduced base pinhole is
bit-exact; base objective components equal the saved final monitor. Independent
score SHA256:
`b01435e6f06b0930a1b11a9ae8a597ba0a727541bad2374b3dd91dc91b762bdc`.

The supplied direction adds the independently known far-sheet glint in
physical DN. The separate placebo translates that vector20 native pixels in x
with zero fill. Near radiance and oracle alpha remain fixed. All negative-step
radiances stay nonnegative; no clipping or clamping is used. The scorer checks
the actual delivered increments for correct sign, units and one application
of visibility before measuring their image errors.

| True glint direction | Data NLL | Original prior | Total |
|---|---:|---:|---:|
| Base | 3.810100913 | 2.969465017 | 6.779565930 |
| Minus0.001 | 3.811213732 | 2.968419790 | 6.779633522 |
| Plus0.001 | 3.809095383 | 2.970538378 | 6.779633760 |
| Autograd derivative at zero | -1.059164066 | +1.059368849 | +0.000204783 |
| Centred finite derivative | -1.059174538 | +1.059293747 | +0.000119209 |

Every derivative agrees within the prospectively declared tolerance. However,
the total derivative is smaller than its0.00100041 tolerance: **its first-order
sign is unresolved**. Agreement is not a significant positive sign.

At the specified finite positive step, independent core RGB error improves
731.45691->730.33923DN, core chroma260.39317->260.33723DN and whole RGB
150.97138->150.74796DN. Every glint colour component moves closer to truth.
Data NLL decreases0.00100553 but prior increases0.00107336, leaving a measured
finite total increase0.00006783. Both finite signs raise total. These values
show a local tradeoff at this checkpoint, not the global optimum or an
explanation of all remaining error.

The displaced placebo is essential to the interpretation. It also has opposing
data/prior derivatives, roughly-0.21549/+0.21450, so that opposition alone does
not identify missing real detail. Its positive step leaves the fixed core and
glint components unchanged and slightly worsens whole RGB to150.97488DN.
Actual truth action distinguishes the useful direction from generic brightening.
The component direction could reward amplitude alone; RGB/chroma errors remain
separate and visible in the same frozen controls.

No source observation was withheld differently, no optimal step was selected,
and no held-out prediction improvement was measured. Existing flat/bright/image
and pupil-adequacy verdicts remain unchanged. The independent result review is
in independent-radiance-direction-results.md. A single noise-aware radiance
regularity definition is the next prospective implementation, keeping known
visibility and the original flat/detail/bright checks; this result licenses no
strength sweep or real-photo claim.

# Independent radiance-direction diagnostic

Root executes; neither author fits or runs this diagnostic. Prior failed image
and physical-adequacy decisions remain unchanged.

```text
radiance-direction-controls.py prepare --out <run/directions>
radiance-direction.py --source <screen-1/output> --checkpoint <visibility-1/output/layered/fixed-alpha> --directions <run/directions> --out <run/output>
radiance-direction-controls.py score --source <screen-1/output> --checkpoint <visibility-1/output/layered/fixed-alpha> --directions <run/directions> --diagnostic <run/output> --out <run/scored>
```

The independently exported physical far-sheet vector is the frozen layered
scene's `glint_template/(1-alpha)` in f32 camera RGB DN; alpha never exceeds .95.
Its spatial placebo shifts this vector exactly +20 native pixels in x with zero
fill, not wrapping. These are two separate 96×96×3 nonnegative directions, not
one mixed direction. No directions, amplitudes or coordinates are selected from
the observed reconstruction. Arrays, exporter, frozen model and truth generator
are hash-bound. Existing source arrays remain immutable.

The author restores the fixed-alpha checkpoint and evaluates each direction
at scalar steps -.001, 0 and +.001 without fitting or clamping. The independent
scorer requires the saved base to equal the checkpoint pinhole exactly, then
uses unchanged truth RGB/chroma, fixed core/ridge/whole regions, and glint and
glint-free filament components on all five images. Existing absolute bars are
reported, but this is not a new quality admission.

Before scoring, each exported image must match `base +/- .001*(1-alpha)*D`.
The per-channel tolerance is a conservative f32 roundoff bound
`gamma16*(abs(alpha*F)+abs((1-alpha)*B)+abs(delta)+1 DN)`, with
`gamma16=16*u/(1-16*u)` and unit roundoff `u=2^-24`. Sixteen operations cover
the normalized-to-DN construction, separate multiply/add paths, and independent
expected-image arithmetic. This scales with actual positive contributions;
it is not an image-quality tolerance. Unit/gain/sign or double-transmission
mistakes can fail it even when their own autograd check is internally correct.

Report whether plus improves core RGB, core chroma and per-channel distance of
glint recovery from one. A prior derivative opposing plus is not evidence of
harmful regularization unless the saved plus image actually improves the
relevant truth. Conversely, improved truth does not imply held-out prediction
improves, or authorize changing the prior. The author's data/prior/total
autograd and centred finite-difference checks are preserved separately in the
scored receipt; disagreement or inconclusive signs remain inconclusive.

The shifted direction checks spatial specificity. Do not require it to worsen
an imperfect reconstruction or force a positive story if both directions are
favoured. Component amplitude can credit correlated excess, so unchanged
RGB/chroma errors and the true coloured filament remain visible. Neither a
useful derivative nor its shifted comparison proves convergence, a global
minimum, RAW calibration or an automatic focus-stacking rule.

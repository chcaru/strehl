# Independent controls: spatial source-coordinate correction

These criteria are fixed before the full-stack photograph is run. They test the
placement consumer and its scope, not photographic quality or alignment truth.
The author of the correction does not author these numerical expectations.

The independent fixture uses unequal native width and height, an odd decoded
active origin, extra row padding, a nonidentity scale/rotation/translation, an
odd native support origin, and deliberately stronger nonzero red/blue CA than
the camera profile. These choices differ from the real chip crop. All source
pixels are generated u16 CFA; the original buffer must remain byte-identical.

1. Disabled and all-zero corrections must leave the existing direct gather
   bit-identical. A frame absent from the correction table also receives no
   correction. Nonzero controls must prove that samples actually changed.
2. No site outside the fixed support may change. In the inner full-weight region,
   corrected samples must equal the existing uniform shifted-map CPU gather
   exactly after its rounded sink. The uniform reference adds source-native
   delta/2 to the plane translation before the existing CA composition.
   Swapping green phases, reversing delta, or doubling delta must disagree.
3. The transition region must contain nonzero, nonunit weights. Independent
   scalar smoothstep weights and expanded coordinate equations predict a
   generated affine radiance plane to within one DN after rounding. A constant
   plane remains constant. Coordinates are evaluated at each destination CFA
   site's full native position; an odd support origin makes a quad-level weight
   distinguishable from a per-site weight.
4. A fixed seeded spatially white, zero-mean noise field supplies a flat control.
   Noise-only output is not called detail. Finite output, a conservative bound
   of 4 times input variance in the taper, and unchanged outside-support samples
   are required. This is an operator sanity bound, not a calibrated claim about
   temporal camera noise or a quality score.
5. NaN/infinite corrections or transform components, invalid support extents,
   and insufficient MHC plus Catmull source support must fail before destination
   assignment. Wrong source directory, frame count, transform bits, and geometry
   must refuse where their corresponding validation API is available.
6. A two-green-only invocation must exactly match those green samples in the
   four-plane invocation, including the taper. Source review must also verify
   that both actual and noise-probe call sites reach this same correction entry.

No gradient score is used. The full-weight uniform gather oracle could share a
geometry defect with the candidate; therefore the independent affine equations,
wrong-sign/factor-two controls, CFA reordering, and explicit support weights are
separate required checks. All controls are small generated data; no original
RAW files or full-stack reruns are required.

# Independent operator control, fixed before execution

This is one compact structural control for `measure_fields`, not a quality
screen or camera-noise calibration. Root owns builds, executions and RAW reads.
The fixed extra pooling radius is 32 quad pixels; no alternate radius is tested.

Use an asymmetric 257x251 generated green guide with independently varying
variance, then a 211x197 crop at even quad origin (18,22). Compare actual
production level0 Laplacian/energy, the explicitly injected beta0 floor, and
interior full-versus-cropped fields beyond a 48-quad margin. A crop shifted to
odd x origin (19,22) must measurably disagree in its finest Laplacian; otherwise
the phase assertion did not exercise the claimed failure. The source guide
and variance arrays must remain bit-identical after measurement.

Independently sum the returned energy and floor over the literal 65x65 box at
fixed interior and boundary points, intersecting the window with the image.
Compare with the API's pooled fields to relative tolerance 2e-6 (with unit
absolute scale floor), allowing its f32 row-sum intermediate. This can reject
the wrong pooling radius, zero-padding, duplicated edges, unpooled floor, or
pooling a normalized score instead of pooling both physical quantities.

A constant guide with constant variance must have zero fine energy and the
known injected floor everywhere, including boundaries. Doubling the entire
guide and quadrupling variance must multiply energy and floor fields by four;
this tests units and common input scaling, not the correctness of the sensor
noise calibration. Noisy/structured guide content must actually produce
nonzero energy and a changed pooled field. Invalid input refusal is checked
only against the author's explicit API contract. None of these controls
establishes that pooled fine energy chooses the right physical surface.

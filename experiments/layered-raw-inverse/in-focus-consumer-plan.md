# Separate fixed in-focus consumer of saved outputs

Prospective; author executes nothing. No fitter, prior, sigma choice, source
election or earlier result changes. This answers a new output question:
the same supplied common optical floor applied to an already composed pinhole,
rather than the original unblurred pinhole objective. Old rejections remain.

Call the frozen model._blur exactly once on each complete96x96 f32 latent
pinhole array: original truth, visibility-1 Huber, shot-prior-1, cauchy-1,
matrix-cauchy-1, and original screen-1 far-only comparator. Use the same supplied
float32 sigma.7 (stored value.699999988079071), normalized separable support
radius3, CUDAf32 and disabled convolution TF32. Saved pinhole fields already
compose coverage and radiance; do not reconstruct them from denormalized sheets
or blur layers independently. Preserve full arrays before the unchanged
supported64x64 scoring square and nested fixed local boxes. No cropped filtering.

The original sensor-derived mean and retained donor/oracle NPY files are copied
byte-for-byte, with no additional PSF. They already contain optical/source blur;
double filtering would handicap those comparators. The old donor choices stay
fixed and are not an optimal bound for this new target. Record their different
origin. No clipping, WB, tone, sharpening or per-arm normalization is applied.

Pure helper `apply_in_focus(image)` accepts finite f32 HWC RGB (axes>=7), including
signed component templates, and returns the same shape/type. Independent
commission checks exact fixed coefficients/support against a separate forward,
constant/impulse and in-focus one-layer witnesses, input immutability, and one
application. Root binds sources; receipt additionally hashes input files before/
after, input/output arrays, fixed PSF kernel and the original latent receipts.

Independent scorer applies the target/template transform consistently and
freezes its new guards before reading scores. Half-real-component loss, a
second identical PSF on the exact target, and surviving chromatic distortion
must remain rejectable. If those destroyers evade the chosen guards, stop the
instrument as inadequate; do not relax its bars or claim that smoothing solved
detail. Flat first, true colour/detail and whole native scene views remain
necessary. Equal target filtering narrows the frequency question honestly, but
does not calibrate optics, infer visibility, or demonstrate camera-image gains.

CLI `python in-focus-consumer.py --out <run/delivered>` uses fixed HERE inputs.
For flat/layered, export `<case>/<arm>-rgb-f32.npy` with arms truth, visibility,
shot, cauchy, matrix, far-only, mean-observed and donor-observed. result.json
records per-arm PSF application counts and immutable bindings. This is a
read-only alternate consumer, never retroactive pinhole or photo admission.

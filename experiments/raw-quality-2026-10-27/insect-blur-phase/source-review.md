# Root source review before first control execution

2026-10-27. SOURCE-VERIFIED, no producing code imported or executed. Root read
the complete reader and independently authored control worker/protocol; parsed
all three Python files with `ast.parse` using a read-only Python command.

The reader's Fourier frequencies are cycles per native pixel, with same-color
sampling pitch2. The positive sign in its local inverse-DFT score matches the
chosen moving-times-conjugate-reference cross-spectrum. Power2 acts on both
phasor and search ramp; output stays in native displacement units. Physical
origin difference is restored separately. The constructor and operations use
f32/complex64, TF32 off. Noise transport includes the shared arithmetic-mean
covariance before windowing. Batched peak/rival/Hessian calculations avoid a
GPU synchronization per output field. Thresholds remain fixed and heuristic.

The source reviewer initially caught a mismatch between the half-period control
seed128 and the first unexecuted narrow seed validator. Producer and independent
reviewer resolved it before execution: integer seeds through4096 are permitted,
phase evaluation uses the correct per-power period, and returned displacement
retains the declared seed. This intentionally demonstrates that a bad global
branch can yield a locally confident alias. It does not certify that branch.
Control scorer foils now call the actual headline error_record function.

The working-white admission guard is explicitly not a claim of physical RAW
saturation. The control scene is a separate continuous f64 oracle integrated
over sensels and acquired to u16; it is not a measured lens or pixel calibration.
Measured-map curvature supplies a declared synthetic trajectory only. Eight
out-of-model adversities report accepted errors without claiming a universal
occlusion detector. These limitations remain even if the fixed screen passes.

The independent reviewer owns final controls and source-release confirmation.
Root's wrapper archives exact executed local bytes and binds the held map and
Job helpers before launch. No actual-data/global-map/render job is released by
this review. No quality gain is claimed.

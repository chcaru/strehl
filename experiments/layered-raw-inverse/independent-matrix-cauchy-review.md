# Independent matrix-Cauchy source review

SOURCE-REVIEWED; no reviewer execution. No material blocker remains for the fixed commissioning and two-case comparison.

The implementation evaluates `logdet(I+JᵀJ/4)` through `log1p((||dx||²+||dy||²)/4+||dx×dy||²/16)`. Squared cross-product components avoid subtracting nearly equal Gram products. All derivatives remain live, with no SVD, fitted rotation, adaptive scale or added epsilon. Right/bottom forward differences are zero; scaling by sqrt(W/(W-1)) and sqrt(H/(H-1)) makes each full-domain squared-gradient mean equal its corresponding valid-edge mean. Consequently the global quadratic term matches original Huber's one-quarter sum of axis mean-squares. This does not preserve finite-loss values or every local boundary contribution.

The proposed mechanism is conditional. At strong oblique rank1, an added direction orthogonal in both colour and space retains curvature .5. A colour change sharing the existing spatial direction still has curvature .5/65 in the fixed amplitude16 control. This is a substantial remaining weakness, not a universal chroma correction. Conversely, penalizing an independent weak singular direction can suppress a genuine weak rank2 crossing; its prior has no ownership information. Strong rank2 also remains nonconvex. The saved fine-error allocation does not establish which situation caused the rejected image.

Commissioning meaningfully distinguishes these cases through actual first/second derivatives. The separate f64 eigensystem/determinant oracle checks the f32 cross-product value, with signed rank1/rank2 columns and RGB rotation. Rotation is a gradient algebra check, not proof that rotated radiance/likelihood remains physically admissible. The independent arbitrary-direction finite difference checks autograd. On the7×11 field, horizontal squared slope14 and vertical21 give expected amplitude curvature17.5/b², independently testing both rectangular factors against the old actual Huber path. Distinct near/far fields check sheet averaging and unchanged alpha/binary/flux terms. These controls establish operator behavior; they do not calibrate noise or prove reconstruction utility.

The fitting driver preserves original160 sheet parameters, the same independently exported fixed alpha, injected likelihood/censoring/optics and training-only reads. It retains the original remaining priors and L-BFGS settings, actual-evaluation cap, contiguous-gradient identity check and final-state/refusal handling. Independent scoring requires exact initial near/far/alpha/pinhole equality to visibility-1. There is no use of true radiance in fitting and no baseline rerun selected afterward.

Flat runs first with both original-mean and paired RGB/chroma guards. Layered retains all original image/component/held-out tests and the strict paired core/ridge **RGB and chroma** bounds. Every colour must meet the live capped component guard. Scalar Cauchy is descriptive only, and a lower differently defined objective cannot relax the original-Huber comparison. Returned-state acceptance and stationarity remain separate. The wrapper CLI and source/reference bindings match the reviewed scripts.

Any pass is limited to this known-alpha, known-discrete-optics screen and can precede only separately frozen stress work. It does not solve visibility, repair the continuum-optics mismatch, or admit a photograph. No review scope expansion or execution was performed.

Reviewed SHA256 bindings:

- `matrix-cauchy-prior.py`: `6555432834b543f5102899e4c21931c050ce6994b898e5b0ac74f38b03880b9a`
- `matrix-cauchy-prior-plan.md`: `c75c932c14471be2da7825d7a65688b4b14e88d2e354d47dbbd3e483417f29c3`
- `matrix-cauchy-controls.py`: `46dc99bf4acd698e80b2d495be199b3540e83f08bbc0152165ab38e69ecc61a1`
- `matrix-cauchy-independent-plan.md`: `3ddf2c8b553a0dfb0685051eabcee76ad3016bdff26e653f4cb6554fb62fe504`
- `run-matrix-cauchy.py`: `1b77ff39c61f6fc9c529ab7eafed53e5ab61950394797b4b1edf9d4900eb2033`

# Frozen independent adequacy/refusal controls

2026-09-19, before execution. Root is the executor. This is one fixed test of
`model.py`, not a new fusion method or source-ownership proof. No RAW reads,
camera calibration, tone adjustment or parameter sweep. Stop at the first
failed bar, retain the partial JSON, and do not repair the family to fit it.

Run `python -I -B -X faulthandler experiments/relative-blur-evidence/independent-controls.py --out experiments/relative-blur-evidence/controls-1`.
Suggested owned-process limits:120 wall seconds,180 CPU seconds,1 GiB committed
memory. Each frame is4x256x256; both optimizer directions reuse the author's
fixed start, bounds and support. All caller allowances below are frozen and
are not fitted noise or calibrated probabilities.

## Stimuli and bars

1. **Flat first:** exact800DN and identical structured frames must explicitly
   return `ambiguous`. Two independent5DN noisy flat pairs (seeds48271,99173)
   are evaluated in both directions: one `compatible` against one `refused`
   is a false exclusive directional acceptance and fails. Compatibility in
   both directions is allowed and does not order focus. A refusal/ambiguity
   is not interpreted as evidence of ownership. This distinction was fixed
   against the public API before any execution: compatibility is not a label.
2. **Useful held-out positive:** a literal independently rendered centred
   Gaussian (sigma6/2.5 quads,30 degrees, radius24) acts on a spot, textured
   oblique edge and separate compact coloured glint. Fit only the first two.
   Held-out glint RMS must be<=1DN in every plane, status `compatible`, and no
   sigma may reach7.99. Reverse must not be compatible and must exceed10DN in
   every plane: this explicitly proves the fixture can express an order.
3. **Mixed depths:** observations are `A + blur(B)` and `blur(A) + B` above
   the same800DN background. B is a narrow independently coloured modulated
   ridge crossing the glint's spread and continuing beyond it. Evaluate the
   same training fit separately on crossing and continuation: neither can be
   compatible. At least one crossing-plane RMS must exceed30DN, proving the
   destroyer is live. Repeat with the held-out glint removed while training
   and the real ridge remain. This twin also must not be compatible. Aggregate
   agreement dominated by the bright core cannot hide another depth's failure.
4. **Spectral fan outside the family:** apply normalized nonnegative centred
   three-lobe kernels, with red/blue lobe orientations differing. All use the
   fixed radius24 support. This input is actual forward spread but cannot be
   explained by one shared Gaussian; it must not be compatible. This is a
   model limitation, not permission to enlarge the fit family after failure.
5. **Both inputs noisy:** two fixed realizations independently perturb source
   and target by5DN and round to integer-valued samples, then rerun the entire
   fit and decision. The supplied per-plane RMS allowance is30DN (6 times the
   single-input sigma; deliberately conservative, not a likelihood). Positives
   must remain compatible; reverse and crossing must not. No fixed-fit
   antithetic proxy is used. This synthetic constant variance tests behavior,
   not actual A7C II noise or covariance after gather.
6. **Brightness/clipping:** a1.2x gain-only copy must not be compatible under
   the no-gain family; a supplied saturated-core authority must refuse its
   held-out convolution support. No saturation is inferred from developed
   white pixels. Exact input hashes must remain unchanged in each fit/evaluation.

Train cells and their entire49x49 square footprint are independently checked
to exclude the protected target. Masks are fixed by latent geometry. Prediction
uses valid source context; no padding is evaluated as original data. Ground
truth is retained as separate A/B component hashes. There is no manufactured
"detail" metric: residual is allowed only to test compatibility, and the
protected ridge tests the independent claim that this predicts a shared depth.

Passing all bars admits only consideration of a separately authorized retained
linear-source diagnostic. `actual_consumer_admitted` remains false even on a
green synthetic screen. Source ordering can reach fusion only after real
held-out compact-core and competing-depth evidence supports the limited model.
M115's PSF-scale/model failure and M87's residual-versus-truth failures remain
binding limits; see independent-brief.md.

# Fixed small operator API

Source preparation only; root owns execution. `sensor-operator.py` imports NumPy and
Torch but executes no fit at import. CPU f32 math, four caller-configured CPU
workers, at most seven original uint16 sources of at most128x128 sites. No RAW
decoder, RGB source image, GPU, prior, optical blur or full-photo adapter.

```python
config = Config(observed_hw=(128,128), shot4=(...), read4=(...),
                black4=(...), saturation=15360, device="cpu")
query = Query(original_xy, nodes_xy, footprint_weights)
source = Source(source_id, query, codes)
problem = prepare(sources, config, mode="candidate", metric_override=None)
result = fit(problem)
result.save(out_dir)
```

`read4` is read variance in DN squared; shot4 is DN/electron. The injected
variance is exactly `shot*max(code-black,0)+read`, matching the supplied product
NoiseModel; no added quantization variance or fitted/private noise. Acquisition
u16 rounding is a separately disclosed model approximation. Physical arrays use
R,G1,G2,B; the bridge must explicitly map the core's R,G1,B,G2 storage. Every
code at/above saturation refuses before solving. Below-black codes stay signed.

Query arrays: original_xy is int32[H,W,2], a contiguous physical x/y grid;
nodes_xy is float64[H,W,9,2] in latent coordinates; footprint_weights is positive
normalized float32[9]. Geometry is a supplied input, not fitted by the operator.
The controller must bind the known source-to-reference map and independently
check that these nodes integrate its original unit square, not a reference
square. The operator checks actual Lanczos support and RGGB physical parity.
No node extension/crop rescue. `codes` is uint16[H,W], copied immutable; IDs are
unique but literal duplicate arrays under distinct IDs are permitted for a
declared duplicate-control. Config fixes field_hw=(H+16,W+16), output_xywh=
(8,8,W,H). Latent x is Torch float32[H+16,W+16,3] in signal DN, HWC.

Commissioning seams:

- `Measurement(query,config).forward(x)` -> float32[H,W] signal DN, no black;
  `.adjoint(y)` -> float32 HWC. `.matrix` and `.transpose_matrix` are actual
  cached sparse producing operators. Rows are normalized after coalescing.
- `HaarPlan(observed_hw, origin_xy).forward(y)` -> one float32 vector;
  `.inverse(coefficients)` -> native2D; `.variance(v)` -> marginal variances
  using the same packing. `.bands` gives dicts phase/level/kind/shape/start/end;
  `.sizes` gives actual per-phase level dimensions. Detail order LH,HL,HH, then
  LL, phase-major. Original physical phase order R,G1,G2,B.
- `problem.source_operators` -> list of `(Measurement,HaarPlan)` tuples;
  `.observations`, `.variances`, `.metrics`, `.factors`, `.rhs` -> lists of f32
  tensors. `.metric_scale` is the one common max q after override; `.count` is
  total original sensel count. `forward(x)` and `adjoint(list)` are the actual
  weighted producing B and B-transpose. `.objective(x)` returns stable norm
  receipts for scaled/original objectives. No black in B or its adjoint.
- `prepare(...,mode="no-focus")` sets a=1 but retains V. `mode="full-value"`
  uses the design's one all-AC scalar per source including LL. Neither is a
  second candidate. `metric_override=1.0` sets TOTAL q=1 for Parseval mechanics;
  any positive finite f32 scalar is allowed for common-scale controls. Zero is
  rejected. No override in the candidate fit.
- `integrate_reference(x,config)` -> Torch float32[H,W,3] reference-unit-cell
  integrals, not point values, no tone/WB/matrix/clamp. This is the only RGB
  delivery integration; controls own fixed display and actual native comparator.
- `norm_pair(tensor_or_list)` -> `SquaredNorm`, with f32 mantissa/integer
  exponent, `.receipt()`, `.ratio(other)`, `.root_ratio(other)`;
  `.scaled(positive_f32)` multiplies the represented squared norm. It never
  forms an unscaled square. `.is_zero` handles the zero case explicitly.

`FitResult`: x, output (Torch f32), status string, converged bool, iterations int,
history list, evidence dict. `save` requires a fresh directory; saves complete
latent/output float32 NPY plus JSON, including finite refused output. Fit starts
zero, exactly64 maximum CGLS steps; true objective and true normal residual are
separately evaluated every iteration. Recursive CGLS residual is not silently
replaced. Monotonicity failure is retained, not smoothed by tolerance. No fit
qualification or photographic claim follows from a finite return.

Known limitations: finite small sparse matrices are retained for every view;
this is not the streaming full-image implementation. The free apron and
unobserved/nullspace coefficients are explicit, not identified radiance. Direct
support counts do not establish rank. All image reductions are f32; integer
binary exponents prevent scalar norm overflow without introducing a f64 solve.

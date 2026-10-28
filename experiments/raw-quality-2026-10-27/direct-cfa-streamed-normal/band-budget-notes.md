# Saved complete-photo band budget

2026-10-27. SOURCE PREPARATION ONLY. Root owns the300s/1200CPU-second,
16GiB-host/8GiB-CUDA, four-worker job. No author import, compilation, numerical
operation, RAW decode or run. Frozen reconstruction sources are unchanged.

```text
python -B -X faulthandler experiments/raw-quality-2026-10-27/direct-cfa-streamed-normal/band-budget.py --out <fresh workspace outputs directory>
```

Success is `COMPLETE_FULL299_BAND_BUDGET`, complete/source_count299/controls_pass,
with photographic_admission and quality_claim false. The per-source NDJSON and
completed mechanical files survive a later failure; incomplete is not a result.

## Exact retained inputs

The script binds the completed full-photograph receipt, constructor and fit
result by exact SHA, and reuses the frozen full worker's cache/map/order
validation. It checks the complete signed latent hash, original299 cache hashes
and headers, held geometry, levels, supplied noise bits, common qmax and N.
Source files and caches are hashed before/after; ARWs are neither opened nor
decoded. One original u16 memmap is consumed at a time. There is no all-source
coefficient, factor, residual, aligned or RGB volume.

## Mechanical first stage

Source149 uses its actual7032x4688 signed original codes and full seven-level
Haar plan. Compare all coefficients, separately per phase/level/kind, with the
frozen CPU Haar at the same full dimensions; compare the producing roundtrip
with input. A distinct coefficient vector `((index mod17)-8)/8` exercises the
transpose against the frozen CPU inverse, and the dot relation uses the actual
source and that vector. Parseval and exact level dimensions/odd carries are
reported. The first/middle/last coefficient values of every band are retained.
This is not merely an inverse of the same potentially permuted coefficients.

Forward/roundtrip/transpose field bars are normalized maximum1e-5 and RMS2e-6,
using reference max/RMS floored at1DN, as in the frozen measurement controls.
Normalized dot error is at most3e-6, with the sum of both Cauchy-Schwarz products
as denominator; Parseval relative energy error is at most3e-6. These are fixed
before execution. No quality threshold is added.

For sources0 and149, seven fixed4x4 original-sensor rectangles cover all four
corners, center and existing hair/thorax coordinates. The CPU `_matrix` receives
the exact full-field shape, original physical coordinates, GL3 sensor nodes and
held f64 affine. Its sparse forward rows consume the whole saved latent, with
no crop/rebasing. The function also creates an approximately800MB empty-row
sparse-transpose index array; it is immediately discarded, one source at a time.
There is no dense CPU matrix. Exact queries and actual/reference values are
saved. Both are checked with the same maximum/RMS bars.

An independently declared full-field, channel-coded affine ramp commissions
wrong-R/B-phase and +1-original-x origin foils through the actual GPU forward.
Correct ramp predictions must pass CPU rows, and both foils must fail those
same bars. The origin foil uses only the three interior rectangles so it cannot
claim power from an out-of-support edge refusal. Ramp checks are mechanical;
they do not replace the saved-X comparisons or supplied noise model.

## One all299 cache pass, no fitting or adjoint

For each original source, run the unchanged bands/variance/admission/mask code.
Compute saved `A(X)` and actual `A(ones)` together, then separately evaluate the
saved initial constant RGB field through A. **Do not assume finite-precision
`A(c)=c*A(ones)`.** This additional forward shares the current cache pass and is
included in runtime. It is not a new fit or an all-source residual volume.

For every physical phase/level/kind retain count, admitted support, omissions,
q min/max/sum, observed/predicted energies and cross-product, unweighted error,
error divided by the exact injected marginal DN variance, and actual weighted
error. Repeat error/energy for the constant-only reference. The weighted
residual uses the frozen order `(factor*d)-(factor*H(A(X)))`. Unweighted and
sigma error sums cover admitted coefficients; all omitted counts remain visible.
Variance is supplied temporal noise in DN squared, not spatial scene variance;
these correlated coefficients are not counted as independent likelihoods.

Also record actual `T=factor*H(A(ones))` energy and `T'b` per band. Low odd
carries can create nonzero constant detail coefficients. Mark nominal supports
truncated by the original phase extent, and the3x3 AC admission neighborhoods
touching them; report their q and T-energy contribution separately. This can
expose boundary/DC participation without declaring it the cause in advance.
Terminal LL remains separate from coarse AC. No quantiles are computed.

Source-band reductions are f32. Descriptive cross-source sums use Python float
on those scalars; the authoritative objective separately uses the frozen
`norm_pair.add` on complete source weighted residuals, in original order.
Per-source split-vs-whole, aggregate split-vs-whole and saved initial/final
objective reconciliation use the prospectively fixed allowance
`1e-7 + 5e-5*max(abs(reference),1e-12)`. Actual color Gram/T'b use the same relative
allowance with absolute1e-13 because their magnitudes are much smaller. None is
a changed solver convergence bar. Exact source support censuses and qmax must
match the bound fit receipt.

The result can identify which measured coefficient strata dominate this
objective and which remain unrepresented in saved X. It cannot establish a
spectral nullspace, a condition number, a correct photographic optimum, or a
preconditioner's eventual quality. A large q range alone proves none of those.
No parameter, objective, reconstruction or delivered photograph changes here.

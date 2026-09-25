# Numerator range correction: independent source and causal review

2026-09-25. Reviewer: pipeline_audit. Root authored the numerical correction and executes all Rust tests and photographic jobs. This review authored the separate five range controls; mineral_diagnosis reviews them. No RAW jobs or Rust executions were performed by this reviewer.

## Measured causal boundary

Root's actual 183-source garnet census completed all four planes. Observer-on and observer-off whole TIFF SHA256 both equal `80d2e3ea30d028ebf22b298977cbf113f46c368104fb057a8b8b79596af540b4`, pixel hash `87c8d5ba3fbaed2441fbcd241c7865c5d78a7e7081de0136e334f31d26b6520a`, and all four complete merged-plane hashes match. These are retained in `observer-identity-1/comparison.json` and the two completion receipts. The census SHA256 is `918f40337aabbdcd0c020efd56345dbbbdb18c83fbf2f64dd04031dd7f02907e`.

Only band 2 contains nonfinite numerators/resolved coefficients: negative infinity counts R12, G1 15, G2 14, B6. All denominators and unweighted sums are finite. The pre-hull reconstruction contains R1164, G1 1248, G2 1232, B699 negative infinities; the final output contains none. A finite output had concealed the failure.

DERIVED and checked against the recorded masks: the positive five-tap expand carries one band-2 coefficient at `(x,y)` onto the full-resolution CFA square `[4x-6,4x+6] × [4y-6,4y+6]`. The union of these squares has exactly the measured full-image nonfinite count for every plane. Within the independently frozen native region `[4668,1858,384,384]`, the predicted set equals the measured pre-hull set **at every site**. Every such site then equals the final lower InputRange bound, with none equal to the upper bound.

| Plane | Band-2 bad sites | Whole pre-hull bad sites | Frozen ROI bad sites |
| --- | ---: | ---: | ---: |
| R | 12 | 1164 | 787 |
| G1 | 15 | 1248 | 871 |
| G2 | 14 | 1232 | 855 |
| B | 6 | 699 | 478 |

The two main native support boxes are `[4788,1996,34,42]` and `[4876,2068,34,42]`. A third R/G component starts near `[4980,2092..2100]`, width26 and height26..34. These are CFA-site support boxes in native coordinates, not a claim that every demosaiced RGB channel is confined to the same box. MHC subsequently mixes nearby CFA sites.

The mask check was run as a read-only inline Python command against the frozen JSON. `check-frozen-masks.py` retains the same calculation for root/independent replay:

```
python experiments/garnet-spatial-trace/check-frozen-masks.py
```

It binds the census hash, requires the complete marker and all bad coordinates to fit in the untruncated first64 list, checks finite denominators/unweighted sums, compares the full-count and exact ROI footprint, and rejects a one-site translated mask. It neither creates an image nor reruns the merge. The set agreement establishes the source of these particular rectangular notches; it does not establish the source of every spatial ghost or specular highlight.

## Numerical proposal and limits

The minimal correction stores SoftPower `sum(w*(L/65536))` and resolves `(num/den)*65536`. All weights, admission, denominators and source ordering remain the same. Restore **after division**; restoring the numerator first recreates the overflow. HardMax stores a raw selected coefficient and must bypass both operations. Mean fallback and its unweighted sums remain unscaled.

DERIVED bounded argument: with at most1024 sources, each native gathered sample in the u16 domain, and capped weight at most `exp(80) ~= 5.5406e34`, the Laplacian coefficient magnitude is bounded by the input range under the positive normalized Gaussian filters, up to small f32 filtering roundoff. Both denominator and scaled numerator have magnitude at most about `5.674e37`, below `f32::MAX ~= 3.403e38` by about6x. Partial chunks and their absorb sums obey the same total-count bound. Ordinary p1/p2 branches lack the exponential cap but bounded native squared energy makes their weights much smaller than this maximum. This reasoning does not cover arbitrary f32-domain callers, arbitrary significance floors, or unbounded frame counts; BandMerge's general API does not enforce a1024 cap. It is a bound for the stated native workload, not an unconditional theorem about every caller.

Binary rescaling preserves normal mantissas and commutes with normal rounded arithmetic under the same operation order. It is **not universally bit-exact**: a product becomes subnormal or zero earlier, or a normalized quotient can underflow. At the general branch's minimum positive weight `exp(-80)`, the coefficient-domain quantum caused by one least f32 subnormal is roughly `2^-149 *65536 / exp(-80) ~=5.09e-6 DN`. The new control uses positive/negative1e-6 and1e-4 coefficients and bounds output error by1.1e-5DN. It explicitly does not claim that bound for arbitrary p1/p2 weights below the exponential floor. Any platform flushing subnormals would fail the1e-4 case, as intended.

The alternative of reducing the upper weight cap changes relative weights wherever only some donors hit the cap; it therefore changes selection and cannot be defended as the same numerical correction. Rescaling all weights instead makes the denominator's lowest weights subnormal and changes weight diagnostics. A dynamic block-floating sum or f64 numerator adds complexity or memory/precision changes; neither is necessary for this bounded failure. No speed claim is made before measurement.

## Live reader audit and patch review

Reviewed the actual minimal diff in `crates/strehl-core/src/pyramid.rs`: only SoftPower accumulation and positive-denominator resolution change arithmetic. Reset, construction and absorb sum scaled values consistently. HardMax's selected coefficient and comparisons, unweighted fallback, per-level/final hull, writer, and weights remain unchanged. The shared `resolve_soft_numerator` helper prevents mismatched experiment interpretation.

| Live reader | Required handling |
| --- | --- |
| `pyramid.rs` SoftPower finish | Restore after division; implemented. |
| `donor-consistency/core-bridge.rs` | Calls shared resolver; implemented. |
| `rb-residual-guard/core-bridge.rs` | Calls shared resolver; implemented. |
| `cross-scale-source-prior/core-bridge.rs`, `fine-support-guidance/core-candidate.rs` | Same-representation bit equality remains valid. |
| `rb-own-guide/core-bridge.rs`, M194d generated controls | Finite checks, zero injection and deliberate overflow sabotage remain meaningful; no coefficient division. |
| `garnet-spatial-trace/core-observer.rs` | Nonfinite counts remain valid. Raw numerator magnitudes now have scaled units. |
| `m194h-pedestal-causality/core-hook.rs` | Exports raw numerator bits; historical protocol needs an explicit scale/version for a future rerun. |

The M194h `independent-verify.py` lines715–718 reconstruct the legacy `w*L` sum and `num/den`. It is not used by this correction's jobs. Do not silently rewrite its old receipts or claim its old bitwise verifier validates a new run: a future run must version that interpretation. Archived source snapshots were excluded from the live-reader audit and must remain unchanged.

## Independent controls and acceptance

Root's pre-fix four tests had1pass and3fail, including the actual ISO100 noise-model case. The flat/midtone control passed. Two high-DN cases explicitly prove finite output can hide nonfinite internals; one identical-frame hull returns exact source pixels despite the bad sum. See `regressions-1/process.log`.

The separate `range-bound-controls.rs` adds five tests, not yet executed by its author:

1. Actual accumulate/absorb/finish for1024 bounded signed peak coefficients. Prescribed cached coefficients and capped weights test arithmetic only, not whether the focus measure produces that pair. The literal old product must overflow, current accumulator and pre-hull finish must be finite, serial and chunked results must each remain within2DN of65535DN.
2. Signed tiny coefficients at the exponential weight floor exercise actual subnormal storage, requiring the stated absolute error bound.
3. Normal finite SoftPower/Mean against legacy f32 weighted arithmetic, independent actual decomposition and actual one-frame weights. Full finish pixels, denominators and fallback sums must match bits.
4. HardMax with both base modes against the corresponding legacy selection oracle.
5. WeightedFromCoarsest (CLI sharp base) against legacy SoftPower bits; require positive base weights so the branch is exercised.

Controls share the current weight computation by design: they establish accumulator correctness and unchanged weights, not focus-selection quality or camera calibration. They cannot prove a SOTA photographic result. Root must run a fresh compile, the tests, complete corrected stacks with held per-source hashes and canonical plan/threads, then full-output independent review. Historical cache replay remains exactly tied to the user's original full image; candidate output is separately named and may differ.

Candidate adapter review found the historical replay RGB16/ICC and per-source hash checks sound. The review requested explicit equality of historical plan/threads because absorb grouping affects rounding. The author added that guard before root's frozen build; it is present at adapter.rs line228. No bound source was edited by this reviewer.

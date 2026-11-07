# Repeat-evidence primitive: independent contract and controls

**DERIVED / source-semantics review,2026-10-28.** Prepared before the new primitive's source checkpoint. No test build, RAW load or numerical producer run was performed here. This is not a compatibility threshold or PSF certificate. The reviewed existing contracts are `plane.rs` active-area RGGB coordinates, `reconstruction::sensor_pull`, `session-reconstruction-sampling.rs`, `align::sample_catmull_rom` and the injected `PlaneNoise::variance`.

## Linear observation and covariance contract

For band b and one acquisition, compose the fixed spatial filter and resampler into coefficients h_bk indexed by exact original acquisition/CFA-site identity. Coalesce repeated original sites before squaring. The observation is sum(h_bk * (raw_k-black_k)) in a declared exposure basis; covariance(b,c)=sum(h_bk*h_ck*v_k), including signed off-diagonals. With gain g, output means scale g and covariance g². Injected v_k comes from the frozen guide's expected black-subtracted signal at original site k, transformed into that source's exposure units. A center-only signal approximation across an edge must be labeled and separately commissioned; it is not the exact heterogeneous shot-noise covariance.

This covariance is conditional on fixed geometry, guide, source selection and the temporal independent-sensel model. Shared guide uncertainty, fitted geometry, camera fixed pattern and cross-acquisition dependence are not manufactured as independent temporal variance. The primitive should return the covariance and support identities, leaving singular/low-power compatibility decisions to its caller. Never invent diagonal independence between high/mid/low observations from the same pixels.

“Exact composed coefficients” and “bit-identical sequential f32 resampling/filtering” are different claims. Coalescing changes floating summation order; compare against an independent impulse oracle with a justified numeric tolerance unless arithmetic order is deliberately reproduced. Keep f32 product arithmetic and u16 storage. No aligned-frame volume is needed.

## Independent analytic witnesses

| Control | Expected observation | Failure exposed |
| --- | --- | --- |
| Identity gather at a native same-color site | One effective coefficient1; value raw-black; variance v for that site | Wrong CFA offset, black or active coordinate |
| Half-phase Catmull in one dimension | Taps[-1,9,9,-1]/16 and squared norm41/64; separable half/half norm(41/64)² | Wrong negative taps or bilinear substitution |
| Sensor-step1 low1=[1,4,6,4,1]/16 at an identity native CFA site | Coalesced original-plane1D taps[-1,12,42,12,-1]/64; squared norm1027/2048 | Incorrectly adding per-interpolated-sample variances without covariance |
| Same observation subtracted from itself | Zero effective coefficients/value/covariance, with raw dependency/read footprint policy explicit | Squaring before cancellation, fake independent samples |
| High=id-low1 and mid=low1-low2 | Signed cross-band covariance from shared original coefficients; PSD joint covariance within numeric tolerance | Treating bands independently or dropping negative coefficients |
| Constant and affine original signal, nonzero black | DC high/mid responses near numeric zero; low retains constant; signed below-black samples retained | Clamping measurements as if they were guide expectations |
| Known gain2 | Mean doubles, every covariance entry multiplies4 | Gain/noise unit mismatch |
| Heterogeneous frozen expected signal | Exact impulse covariance agrees with sum of site-specific variances; bright outer taps matter | Using center expected value across a kernel |

The low1 identity witness assumes the stated length5 sensor-step1 binomial. Low2 must separately declare whether it is length9 binomial or a dilated length5 kernel; both have radius4 but different transfer/covariance. Do not let radius alone define the operator.

## Geometry, support and adversarial input controls

- Use full active geometry and physical center `(quad_width+0.5,quad_height+0.5)`. G1/G2 share the green optical transform but retain different photosite positions. Test absolute odd-origin crop, rotation/scale, translation and nonzero distinct Red/Blue optical corrections against an independent physical sensor oracle. A self-consistent wrong gauge can pass synthetic tests.
- Compare effective coefficient identities against actual original impulse responses. Test two nearby output observations that share original sites, and separated observations whose complete transformed filter/interpolation supports are disjoint. Source ordinal alone is insufficient identity across a mixed cohort; bind original content/acquisition token and CFA site.
- Retain complete support, including negative Catmull taps and filter halos. A clipped negative-weight tap, unsupported active edge, tiny plane, partial row and nonfinite pull must refuse before an invented edge-clamped value is used. If a zero-net coefficient is removed, distinguish its effective influence from any original pixel actually read for clipping or another admission statistic; independence follows complete dependency, not merely the final algebraic coefficient set.
- Guide support must cover every predicted original site. Poison a halo-only guide dependency; missing or nonfinite guide must remain unknown, never silently become zero signal through `max(0)`. A finite negative expected signal may use the shared model's documented clamp, with that choice explicit.
- Validate source/noise/levels/gain/pull/guide bindings before source mutation or reads. Duplicate acquisition content, wrong noise units, wrong guide acquisition and geometry with the same number of pixels must fail.
- Check arithmetic overflow and maximum coefficient/point/patch counts before reserving buffers. A valid budget boundary succeeds, one byte below refuses before source access, and a deliberately counting QuadSource proves failure ordering. Preserve any declared sparse/read footprint budget rather than allowing adversarial transforms to expand into a full image accidentally.

A later compatibility consumer must commission thresholds on this actual primitive. Source count, a nonsingular covariance matrix or a passing phase Gram does not itself establish repeat PSF equivalence, sharpness or usable original-CFA reconstruction.

## First source checkpoint review

The initial implementation exposes fixed observations, original-site coefficients, covariance and explicit refusal categories only. It does not choose compatibility thresholds. Coefficients are composed in reference sensor coordinates, coalesced by original same-color site, then scaled by gain before values/covariance. Signed cross-band terms and site-specific injected expected signal are retained. Checked maximum8bands,256filter taps and32,768contributions bound the retained vectors; unstable in-place sorting allocates no additional proportional scratch. Nonfinite returned arithmetic refuses. These mechanisms match the intended conditional linear instrument; source tests include the independent half-phase and sensor-step1 lowpass analytic witnesses.

One contract issue was sent to root: the first source accepts `full_quad` different from the actual source geometry, whereas existing reconstruction and RegionSampler enforce the full-active gauge. A nonidentity transform can then use an incorrect center while yielding valid array accesses. For the current same-camera/full-active use, equality should be enforced and tested with same-length/different-shape geometry. If heterogeneous reference geometry is intentionally supported, the API instead needs an explicit, bound reference/source gauge contract and tests; it should not be accidental permissiveness.

The built-in bands are explicitly different from the custom stride1 analytic oracle: low1 is separable[1,2,1]/4 at sensor stride2, and low2 is its convolution[1,4,6,4,1]/16 at stride2. This has the requested2/4sensor radii but a different transfer from a length5 stride1 lowpass. Compatibility policy and receipts must bind the actual coefficients, not just radii or the word binomial.

Canceled sites are removed before any raw value, clipping statistic or expected-signal callback is read. Therefore the documented zero-dependency cancellation is defensible for this primitive; it is not the unsafe post-read erasure of a clipping/selection dependency. Its cancellation test checks zero source reads and a guide callback that would panic. The returned overlap helper describes effective original temporal-noise samples only. Shared guide and geometry dependencies still belong to the caller's complete evidence receipt.

The covariance Monte Carlo drives the actual observation function using independent original Rademacher draws, supporting the composed observer. Its stimulated sites come from the returned tap list, so it cannot independently detect an omitted tap outside that list. The independent analytic coalescing/gauge controls address some of that weakness; an impulse sweep over a predeclared enclosing rectangle, plus nonzero per-color optical composition at the caller, would strengthen the complete operator check. No measured camera calibration or PSF result follows from these plants. Test execution was owned by root and was still in progress at this review checkpoint.

## Reviewed checkpoint03: gauge issue closed

**VERIFIED source and root-run receipt.** The source now rejects `geometry != full_quad` before allocation, source access or expected-signal callbacks. The same-pixel-count128x32versus64x64 adversary exercises the failure. New controls also establish exact reservation-boundary success, one-byte-below refusal before reads, a clipped negative Catmull contributor and a short original row. The final reviewed source SHA256 values are `repeat-evidence.rs`=`f3ef338f749d0e7942195cbd4f78fac6915ee1d5dcbeb29ae486a3ff28a382d4` and `repeat-evidence-tests.rs`=`fd94d344b3388e2d0bc16194de510627ac6ec7ec711b342250acc2aa172d9c64`.

`outputs/multi-stack/completion/repeat-evidence-controls-03/receipt.json` records `cargo test --locked -p strehl-core repeat_evidence -- --test-threads=4`, exit0,7.1209seconds with4Cargo jobs. Its command log contains fresh **Compiling strehl-core** and all11primitive controls pass. The additional example invocations are filtered to zero tests and are not counted as exercised numerical controls. A separate existing research-wrapper unused-import warning remains; this is not a strict lint pass claim.

The first retained control failure assumed the three selected binomial bands must contain a negative cross-covariance. That sign is not a universal invariant. Replacing it with an explicit negative-identity observation makes the required analytic witness exact: cov(identity,-identity)=-var(identity), without changing production algebra. The original failed receipt remains evidence of the corrected test assumption.

No blocking source defect remains in the reviewed primitive checkpoint. Its use still requires the caller's guide/original/geometry provenance and actual compatibility commissioning. This approval covers the additive linear observation/covariance instrument, not repeat PSF certification, plateau source admission, a change in the ordinary merge, or photographic quality. The complete sparse impulse and distinct optical-composition witnesses suggested above are useful caller controls, not claimed executed by this review.

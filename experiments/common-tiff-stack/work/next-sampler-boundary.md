# Prospective checked-sampler boundary investigation

Status: DERIVED from source; no sampler, control, build, render or numerical checker executed. No observed image-quality defect or changed gate is claimed. Preserve the original common-TIFF source closure until its saved verification finishes; this note is outside that closure.

## Consumer and coordinate gauge

SYNTHESIS requires gathering at consumption, injected noise and truth in the consumer's gauge. The current identity common-RGB path folds one frame's planes into BandMerge without these resamplers. This finding does not explain its output.

`warpmap::gather_checked` (`crates/strehl-core/src/warpmap.rs:441`), reached by `gather_frame`, pulls reference coordinates into source coordinates without inversion. It calls `sample_checked`: Some means covered; None becomes NaN/false. The native full-resolution warp also calls the checked sampler at `crates/strehl-cli/src/align_cmd.rs:2113`: it transforms the CFA site's offset in plane units, then explicitly multiplies the source coordinate by two for the full-resolution source plane. Keep these grids distinct.

Fixtures use a scalar 128 x 96 plane, integer sample centres and that plane's sample-pitch units. Later RGB translation/crop uses RGB pixels without the CFA factor of two. No estimated real alignment, scale track or physical correspondence is tested.

## Source discrepancy

`Resampler::sample_checked` (`align.rs:2941`) admits each axis on [s-0.5, W-0.5-s], where s is the declared support. It promises refusal where support leaves the plane instead of clamping. The inner samplers clamp the coordinate before extracting its fractional phase:

| Sampler | Checked x domain | Inner x clamp | Accepted strip whose coordinate changes |
| --- | --- | --- | --- |
| Bilinear (2648) | [0.5, W-1.5] | [0, W-2] | (W-2, W-1.5] |
| CatmullRom (2688), clamped CatmullRom (2722), Lanczos2 (2873) | [1.5, W-2.5] | [1, W-3] | (W-3, W-2.5] |
| Lanczos3 (2817) | [2.5, W-3.5] | [2, W-4] | (W-4, W-3.5] |

The same discrepancy occurs in y. At W=128, respective x=126.25, 125.25 and 124.25 pass the checked bound but become 126, 125 and 124 internally. Their original stencils are array-valid: [126,127], [124..127] and [122..127]. A covered value can describe a different coordinate despite valid taps. This strip does not implicate Nearest.

Keep clamped CatmullRom's separate tap-range value limiter unchanged. Lanczos normalization does not establish exact affine reproduction.

## Fixed, fail-capable first commission

Freeze the finite control population, tolerances and source/binary bindings before execution. This is a public-API investigation, with no production render or parameter sweep.

1. **Literal affine truth for Bilinear and both cubic variants.** Use independently constructed F(x,y)=1000+8x+16y, with every stored value exactly representable. At each kernel's inner upper limit U, test U+1/4 and U+1/2 in x, y and both, keeping the other axis at an interior quarter phase. Compare to the literal F at the requested coordinate, not to the implementation's clamped coordinate. Propose absolute tolerance 1/32 code unit, subject to independent pre-release review; it is not measured precision. The held clamp loses 2 code units for a quarter-step in x and 4 in y by algebra. Require actual checked acceptance and a query strictly above U. On this ramp the requested value lies inside the stencil range; require raw/clamped cubic agreement here without claiming their nonlinear behavior is generally identical.

2. **Same-phase translated truth for Lanczos2/3.** Do not demand exact affine reproduction. Pair a high query (U+1/4,20+1/4) on F with an interior query (20+1/4,20+1/4) on G(x,y)=F(x+U-20,y). Corresponding stencil values and phases are identical, implying the same interpolation result at different addresses. Include the corresponding y and corner translations and half phases. First require the paired construction to agree at two interior locations. A wrong integer translation and a changed fractional phase are fixed destroyers; the checker must show they actually change the compared population. Compare actual values with a preregistered tight bound; the oracle does not reuse the producer's weights or assume exact first moments.

3. **Boundary population and nulls.** For every sampler, retain low-side boundary, interior fractional, last inner integer, exact checked upper boundary, just-outside, distant-outside and constant-plane cases. Use one-quarter-step probes on both sides of the declared limits. Constant response and integer identity are regression/null checks: alone they cannot reveal lost fractional phase. Require both accepted and refused populations, both high axes, and nonconstant slopes. Keep the checked-domain mask fixed unless a reviewed repair explicitly changes it.

4. **Nonfinite and tiny planes.** Test NaN and each signed infinity separately in each coordinate on finite data. The proposed checked contract is None before indexing, without panic; the current comparison-only guard does not explicitly enforce this, but no particular runtime outcome is claimed here. Use valid PlaneRef shapes 1x1, 1x7, 7x1, 2x2, 3x3, 4x4, 5x5 and 6x6 to cover support refusal and the existing inner fallback chains. Empty geometry must fail PlaneRef::new (align.rs:416). Preregister whether declared or fallback support governs checked admission. Preserve declared support initially; do not automatically widen it. Distinguish an outer refusal from an actually reached fallback. The 4x4 cubic/Lanczos2 and 6x6 Lanczos3 central half phases also have legal taps and this discrepancy.

5. **One public gather association.** Apply a fixed quarter-pixel reference-to-source translation through gather_checked on the same literal plane. Independently enumerate the support mask and compare coverage entries/count, NaN refusals and accepted values. Include opposite sign as a direction destroyer. Count alone cannot certify the consumer. No TIFF, RAW, model, estimated map or full merge is needed.

No production diagnostic is needed. If one is added, commission off/on/placebo output identity. Independent verification must re-choose boundary addresses/oracles, retain all outcomes and prove destroyers were reached.

## Repair decision to make after that evidence

**Narrowing checked acceptance** to the inner-clamp interval avoids mislabelled values but discards tap-valid coordinates. It changes coverage/crop and leaves unchecked sampling unchanged. Report lost positions if selected as containment; it is not interpolation correction.

**Repairing the inner coordinate handling** can preserve fractional phase for the final legal stencil while retaining bounded tap indices. This is the preferred investigation because the accepted high-side stencils already fit. It needs an explicit policy for unchecked outside-domain extension, exact integer endpoints and tiny-plane fallbacks. Merely raising a clamp endpoint can create an out-of-range stencil at its next integer. Preserve kernel coefficients, the cubic value limiter and interior/integer/null behavior; independently verify all affected kernels. A finite-coordinate guard is a separate, named contract repair.

Choose by declared value/coverage semantics, not by making an assertion green. Investigate this sampler contract before broadening common RGB. The previously proposed integer-translation/crop integration remains a later bounded step: exact gathers preserve input code/noise units, whereas fractional interpolation changes variance and spatial correlation and needs its own injected-noise contract. PROPHOTO_DISPROVED, real-map non-admission and unchanged defaults remain.

## Source identity and scope

Read source SHA256:
- align.rs: 6d33f0e24f21d4370ccd8df0bf618e54a5ad615b838bc265469b4f85051c2786
- warpmap.rs: 9d2198eeab5e8a941e297cf8fcd8a217d2454390220433ae19cc6b07e6fd721b
- align_cmd.rs: b3de7738151a6bc0500c66dd916f9fcb20cdb9be0bf698ad00425d3ebb397c69

No original source/result edits, SYNTHESIS fold or execution. A finite source/test release and independent review remain necessary.

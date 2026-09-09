# Next exact speed candidate: reconstruct and gather only probe greens

2026-09-09. Independent source review, not an implementation or timing result. Reviewed HEAD e416d6756b23b26b66cae93490253027beea9720 and the current files below. No production edits, compilation, decoding or numerical measurements were performed for this memo.

**ARGUED: proceed with one synthetic-probe-only green-output specialization.** Keep the complete source CFA mosaic and the existing green reconstruction arithmetic. Omit the unused reconstructed red/blue outputs and their destination gathers. The real-frame gather remains the full four-site path. Actual speed and bit identity remain UNVERIFIED until the proposed executable checks pass.

## Consumer boundary

`crates/strehl-cli/src/merge_cmd/gatefloor.rs:254` clones the complete Frame, fills all consumed photosites, calls the ordinary warp, then extracts only `BAND_PLANE_OFFSETS[1..3]`. Its luma is exactly `0.5 * (G1 + G2)`. Mean subtraction, pyramid construction, certified-band pooling, denominator and scaling follow; no subsequent probe consumer reads R/B destination values or the returned coverage fraction.

`crates/strehl-cli/src/align_cmd.rs:2011` currently builds a complete black-subtracted, WB-balanced mosaic, allocates rp/gp/bp, demosaics all three outputs, then independently samples four destination CFA sites. All channel reconstruction finishes before any destination write. Green reconstruction reads the source mosaic, never reconstructed rp/bp. Consequently removing R/B output work cannot remove a green input if the source mosaic is retained unchanged.

The smallest useful implementation is a crate-visible probe-specific dispatch at the current call site. Its plane-gather fallback should call the existing full plane path unchanged. For full resolution, share the current setup, geometry validation, WB, CA resolution and per-site sampling/write expressions with the real-frame path; specialize only output-plane production and selected destination sites. Avoid copying a second geometry/sampler implementation. Keep the old full probe path as an explicit comparison arm until tests and timing support retention. A partial helper must not claim four-site coverage: the probe does not need a returned fraction.

Add a small `demosaic_green_row` beside `demosaic_row` in `crates/strehl-core/src/demosaic.rs:337`. It must read the same directional/Malvar selection. For Malvar, output the known sample at green sites and call the existing `conv(..., &F_G)` at R/B sites; for directional, use the existing `green_directional` at R/B sites. Reuse these exact functions, tap order and arithmetic rather than algebraically equivalent formulas. This requires one full-resolution gp allocation instead of rp/gp/bp and avoids R/B-only stencil evaluations and destination sampling. Allocation-count reduction is DERIVED; peak memory and speed are unmeasured.

## Couplings to preserve

- **All four source CFA channels remain load-bearing.** F_G mixes R/B-site samples into green; directional green also reads the known R/B channel. Do not zero, omit, reseed, resize or separately normalize source R/B noise. Keep the current complete-row RNG stream.
- Keep the original frame path, WB coefficients, black/white levels, active origin, stride and full-grid geometry. Full-grid source reconstruction precedes the existing compact Crop extraction. No reduced-grid probe or fitted transfer factor is part of this change.
- Keep f64 transform coordinates and original `sample_checked` calls, site offsets, checked coverage, f32 inverse-gain/pedestal expression, rounding and u16 clipping. Keeping the multiply by green inverse gain avoids an unnecessary arithmetic edit.
- Resolve CA and compose green exactly as now, including refusals. Current `OpticalProfile::eps(Channel::Green)` is None, so compose returns the input bits unchanged. CA toggling cannot be claimed as a live green sensitivity control; path preservation still maintains guard/error behavior. This current source fact qualifies the broader historical module prose about four changed phases.
- WarpScratch is reused. Its final dst/cover will describe G2 instead of B; these arrays are private and overwritten before each site's reads. Exercise successive probe/real-frame calls anyway, including debug identity measurement, so a future accidental scratch-state dependency is caught.

## Small executable checks, with inputs that can fail

1. Compare green-row f32 bits against channel 1 of the original RGB row for both explicit demosaic arms. Include borders, non-square small dimensions, unequal channel values and signed values. A red/blue-only impulse must change reconstructed green at a red/blue site; a greens-only source sabotage must fail. Constant/identity-only fixtures cannot establish this coupling.
2. Compare exact warped G1/G2 u16 values against the full gather under fractional shifts plus scale/rotation, all offered resamplers, noninteger black levels, unequal and invalid WB, clipping/overshoot, uncovered borders, relocated/padded/odd-tail storage and whole/Crop consumers. Require actual covered and uncovered sites and a live fractional-site difference. Confirm every non-green destination and unused address remains unchanged in the specialized arm, then reuse its scratch for another ordinary full gather.
3. Reuse the existing actual probe and complete writer controls in `experiments/m194c-probe-layout/independent-tests.rs`; extend them to compare explicit full/green probe arms by beta bits and complete TIFF bytes. Keep seed, warp and fullres WB changes live. Also cover the directional override and unchanged plane fallback in separate processes where existing OnceLocks require it. No new runner or camera-noise campaign is needed.
4. Only after equality passes, use the existing alternating complete native render timer and independently read whole TIFFs. Include process startup and final write; reused map cost stays separately reported. Removing allocated planes is not itself a measured speedup, and the combined probe timer does not isolate the green substage.

## Prior decisions consulted

Actual command, exit 0: `Python312 -I -S -B experiments/ORCH-drift-check/prior_art.py "green-only probe" "partial channel gather" "gatefloor"`.

Read SYNTHESIS architecture and profile decision section 3.4.2, BUILD-GATE/BUILD-GATE-2, M130-crop-early and M194c-probe-layout, plus the current native-probe-fill results. BUILD-GATE-2's unity-WB/fake-path instrument changed the conclusion, so this specialization retains real metadata and complete source noise. M130 fixes full warp versus compact analysis coordinates; M194c fixes consumed-photosite ordering independently of storage. None authorizes fewer source channels or a smaller synthetic field. This proposal prunes only unused outputs of the existing algorithm; it introduces no new physical calibration or image-quality claim.

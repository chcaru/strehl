# One final independent-color spectral completion

2026-10-27. **DERIVED / PROPOSED, source only.** No code, imports, numerical
jobs, RAW reads or renders were run for this design. The unchanged full299
spectral photograph is still pending. Root must separately release any
implementation or execution; no current pilot, Rust or Cargo file changes.

## Decision and evidence

Test one final completion that interpolates each color on its own physical
lattice: a square passband for R/B and a diamond passband for combined G1/G2.
Do not inject another color's high-frequency correction. This is a fixed
bandlimited interpolator, not an optical inverse, a learned method or a claim
of new information. It makes a different, explicit prior choice from MHC and
the rejected directional/color-difference variants.

The [saved-stage audit](../native-spectral-fusion/pilot/analysis/stage-audit-results.md)
is the reason to test this narrow boundary. It measured substantial independent
R/G/B and green-diamond components in the final CFA, with larger attenuation
or cross-color terms at the subsequently inferred sites. Known-site differences
were at most 0.00033004 DN and all these saved CFA values were nonnegative.
The declared-basis fit is not general identifiability. Flat noise, shared-bin
selection loss and the red cancellation error already exist before completion;
this proposal cannot repair them.

The relevant negative results travel with this proposal:

- [M95-demosaic](../../../docs/research/M95-demosaic.md): even a linear
  interpolator creates alias error; band power and fitted per-bin gain do not
  establish fidelity. Its decoder-derived pseudo-truth is not exact truth.
- [M95-cdiff](../../../docs/research/M95-cdiff.md), sections 3-4: CDIFF's small
  gain was visually indistinguishable in the reported crop; CDIFF2 gained
  signal while worsening artifact and all-channel pixel error. Restoring known
  sites could conceal a broken green refinement.
- [BUILD-SHARP](../../../docs/research/BUILD-SHARP.md), sections 31 and 32.7:
  directional green plus color differences added defocus maze/noise and gave
  no actual fine-hair benefit; off-axis performance also deteriorated.
- [M104b](../../../docs/research/M104b-demosaic-lever.md), sections 5-6: no
  qualifying improvement on the historical grey ruler. Its old optical cutoff
  does not calibrate this teleconverter/code86 capture.
- [BUILD-DEMOSAIC](../../../docs/research/BUILD-DEMOSAIC.md) and
  [V-GATHER](../../../docs/research/V-GATHER.md): channel correlation can lower
  R-B high-pass power while increasing truth error; a stale source-noise gate
  is a separate mechanism. Neither quiet chroma nor linearity is a guarantee.
- Complete [vitamin](../../phase-packed-rgb/results.md),
  [chip](../../phase-packed-chip/full-results-review.md) and
  [weevil](../weevil-fusion-order/photographic-review.md) twelve-plane trials
  were photographic nulls. They retained per-source MHC, whereas this proposed
  completion consumes the one genuinely native final CFA.

## Exact finite operator

Input is one immutable H-by-W f32 final CFA of native unit-cell averages in
black-subtracted camera DN, its physical RGGB origin, and the held development
receipt. Preserve this input signed and byte-identical. Produce an ordinary MHC
baseline first with the existing developer. The candidate uses exactly the same
per-known-site max-zero, WB, exposure and level normalization, in the same
arithmetic order, that precedes MHC. This isolates completion; it does not also
change the writer's negative-input convention. Save both the original signed
CFA and the normalized CFA actually consumed.

1. For W,H >= 4, define a rectangular periodic extension with lengths
   Lx=2(W-1), Ly=2(H-1). An extended coordinate t maps to
   min(t mod L, L-(t mod L)). This reflects about the first/last pixel, without
   duplicating an endpoint. Both periods are even: reflection and the periodic
   seam preserve CFA parity. Use the recorded physical origin when labeling
   sites; do not independently reflect or recenter G1 and G2.
2. For color c, fill a real f32 Ly-by-Lx array with the extended normalized CFA
   at that color's sites and zero elsewhere. Green contains **both** green
   phases. The zeros are missing samples, not black observations.
3. Apply one real 2-D FFT with orthonormal normalization, complex64 spectrum.
   Frequencies are cycles/native pixel, fx=kx/Lx, fy=ky/Ly with signed wrapped
   indices. Use the following fixed, real, conjugate-symmetric multipliers:

   ```text
   s(f) = 2 for |f|<1/4; 1 for |f|=1/4; 0 otherwise
   HR(fx,fy) = HB(fx,fy) = s(fx)*s(fy)
   HG(fx,fy) = 2 for |fx|+|fy|<1/2;
               1 for |fx|+|fy|=1/2; 0 otherwise
   ```

   Compare boundaries with integer products, not an approximate float equality:
   R/B uses 4|k| versus L; G uses 2(|kx|Ly+|ky|Lx) versus LxLy.
   The boundary values split aliases equally, including Nyquist corners. Do
   not shift a phase to a quad center: its position is already encoded by the
   zero-filled physical lattice. There is no pixel-aperture deconvolution.
4. Inverse real FFT with the same shape/normalization and crop [0:H,0:W].
   Measure known-site error **before** restoring the exact original normalized
   values at that color's known sites. Report this pre-restoration null; the
   final overwrite cannot be used to conceal an incorrect transform.
5. Write the three completed camera channels directly through the existing
   matrix/development/tone/ICC writer. No remosaic or second MHC; no further
   sharpening, clamp, chroma smoothing, retone or content-dependent choice.
   Preserve negative/above-one completed camera and linear master values at
   the same points where the ordinary writer preserves MHC output.

This is code-ready as `complete(cfa, physical_origin, development) -> camera_rgb`
plus per-color pre-restoration diagnostics. Process colors sequentially;
arithmetic/storage are f32/complex64, with integer indices for mask decisions.
It does not need any source frames or a new noise estimate.

**DERIVED null:** each R/B alias quartet has multiplier sum 4, and each green
alias pair has sum 2. Therefore restriction of the completed periodic field to
its measured lattice is identity in exact arithmetic. Constants also reproduce.
In one square-lattice axis, s(f)+s(f+1/2)=2; multiplying the two identities
gives 4. For green, shifting by (1/2,1/2) exchanges diamond interior/exterior;
the boundary maps to the boundary and 1+1=2. Both shifts are exact integer FFT
indices because Lx,Ly are even, also when unequal. The physical phase factors
cancel when restricting back to that same measured lattice.
Missing sites reproduce the assumed finite-period bandlimited field, not an
arbitrary scene. Reflection makes a nonconstant affine ramp non-affine at the
boundary; global spectral tails can extend inward. Affine fixtures must report
that whole-field error rather than claim a nonexistent exact affine null or
hide the border. No trend subtraction or extra boundary mode is proposed.

## The unavoidable tradeoff, and the useful test

Neutral native frequency (0.30,0) and an alternative with G at (0.30,0), R at
(0.20,0), and B at (0.20,0) with opposite amplitude can give identical Bayer
samples, after accounting for the unit-cell sinc amplitudes. This operator
chooses the independent-color, within-lattice-band interpretation. It cannot
simultaneously promise neutral supra-R/B detail and arbitrary independent
chroma. It may therefore create false color on neutral fine hairs while
reducing MHC's cross-color leakage on genuine colored scales. That is a
prospective adverse result, not a reason to silently add a classifier or sweep.

The sharp passband is signed, global and potentially ringing. It is not a
positive/no-overshoot interpolator and not a denoiser. Although its fixed
completion is color-block-diagonal, the incoming fused noise can already be
correlated and data-dependent. Do not treat the single-source injected model
as a proved final-CFA covariance, divide it by 299, or use spatial texture SD
as temporal noise. The supplied acquisition model and existing noisy-flat
outputs remain the relevant empirical controls.

After explicit root release, the smallest discriminator reuses all ten saved
controls5 CFA fields byte-for-byte, with MHC and this completion under identical
development. Start constants and the two noisy flats. Retain known/inferred
site and all-channel truth errors, absolute signed component amplitudes and
false components, including the weak 8-DN green; never only lower-bound recovery.
Add only completion mechanics/omissions not supplied by those panels: parity
and Nyquist-boundary examples, center/edge impulses on each physical phase,
affine/border fields, and the identical-CFA
neutral/chromatic ambiguity pair. A wrong green square mask must fail the
green-diamond positive; a channel/phase permutation and doubled mask gain must
fail the actual pre-restoration/missing-site checks. Missing-site tests remain
necessary even when the known-site overwrite is exact. Quality failures are
retained separately from finite/shape/phase mechanics.

The photographic action, if root releases it, needs **no new 299-source run**:
complete the exact saved full candidate and uniform CFA fields after their
current job finishes. Reproduce their MHC masters first, then save full camera
RGB, linear and RGB16 candidate masters with common development. Follow the
[fixed whole-image/all-ten-witness protocol](prior-photo-constraints.md), keeping
native CA-off and B4/B8 references. A null or worse whole photograph closes
this fixed recipe. A useful weevil result still needs flat and second-insect
transfer before any general claim. No current photographic gain is asserted.

## Bounded implementation cost and stopping point

For 6896-by-4596, the extension is 13790-by-9190, about 126.7 million real
values. One real array and one half-spectrum are each about 0.51 GB; the final
three-channel output is about 0.38 GB. Sequential colors need three forward
and three inverse FFTs plus fixed masks/crops, independent of source count.
FFT workspace for these exact composite dimensions is **unmeasured**. A later
one-complete-field cost must include planning, temporary buffers and native
writers, under an explicit 8-GiB device/16-GiB host budget; refuse rather than
silently switch boundaries, tile windows or precision. This work cannot run
concurrently with the active full299 job without root scheduling.

This is a bounded diagnostic proposal, not a product recommendation. No external
implementation was consulted and no novelty is claimed for lattice spectral
interpolation. The exact mask/alias identities above define the independently
implementable operator; the photograph decides whether this prior is useful.

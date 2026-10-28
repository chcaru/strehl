# Fixed independent final-color controls

2026-10-27. Prospective source protocol, before any execution. Root alone runs
jobs after the active spectral full299 job terminates. No parameter sweep,
source resampling, new RAW decoding, learned model or extra noise estimate.

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-27/final-cfa-color/pilot/controls.py --out FRESH_OUTPUT --renderer-binding NEW_WRITER_BINDING_JSON --development-receipt HELD_DEVELOPMENT_JSON
```

Bounds: 300 s wall, 1200 s CPU, 12 GiB host, 8 GiB Torch allocated/reserved.
Four Torch CPU threads, one interop thread, CUDA f32/complex64, TF32 and autocast
off. NumPy f64 is used only for independent references and descriptive scoring.
Runtime/source/DLL/PTX bindings are preserved by the actual producer metadata.
Controls bind its source_dependencies, their own source/protocol, fixed saved
receipt and every opened array/receipt, held development and writer executable
before/after. Outputs are fresh and outside capture corpora.

Receipt status is `COMPLETE_FINAL_CFA_COLOR_CONTROLS`, with `complete`,
`controls_pass`, `quality_pass`, `saved_cases_quality_pass`, `inputs_unchanged`,
`quality_claim:false` and `photographic_admission:false`. Mechanical exceptions
retain a failed/incomplete receipt and produced artifacts. Complete scientific
failures retain every score and exit normally; they are not silently dropped.

## Fixed saved population and order

Use controls5 receipt SHA256
`c747fc882838b755a65683681ea4f9b17b338bdb7b56e39d27ee67a891677010` and all ten
cases, candidate and uniform CFA fields: constant colors, flat-noise-a,
flat-noise-b first; then neutral structure, independent RGB/8-DN green,
green-diamond, shared-bin conflict, red cancellation, near-fine/far-coarse and
crossed/glint/sign-inversion. No new source realization or selection is made.
The original fields are immutable 64-by-64 black-subtracted CFA at native
origin (256,256), with their own same-input MHC camera/master references.

Each field goes through actual `complete`, not a surrogate: normalized input,
pre-restoration known-site error, signed completed camera, upstream completion
receipt and complete native RGB16/linear output are retained. The new writer
consumes normalized camera values without a second WB/range/clamp/completion.
All twenty native outputs must complete and preserve exact camera bytes.

## Mechanics and causal foils

For every numeric comparison below, normalized max error is bounded by
`3e-6 * max(1,max(abs(reference)))`, and RMS by
`6e-7 * max(1,RMS(reference))`. The unit floor is normalized camera full scale;
it is not reused for tiny weighted normal operators or a DN noise claim.

- Independently implement a small full complex f64 direct DFT using explicit
  matrices, reflected source indices and scalar integer-frequency mask tests.
  No producer mask/FFT/helper supplies the reference. Compare actual pre-restore
  and final RGB for fixed signed fields of sizes 9x11, 10x12, 13x9 and 9x13 at
  all four physical origin parities. Compare complete rFFT masks exactly,
  including quarter-axis and diamond boundary bins. Exact restored known-site
  bits are a separate required null.
- Eight center/edge impulses cover R/G1/G2/B through the same direct oracle.
  No known-site overwrite can hide a faulty missing-site response.
- Native normalization is independently evaluated as sequential f32
  `max0 * WBcolor/WBgreen * 1 / f32(white-black)`, using exact held bits.
  Negative, zero, small and high DN values at both parity gauges must match
  bits. No reciprocal multiply or private black subtraction is substituted.
- A reflected-period-compatible green mode (0.3125,0.0625) on 17x17 must
  reproduce the complete analytic field. The actual `green-square`, `swap-rb`
  and `double-gain` producing foils must fail the same pre-restoration scorer.
  A corrupted inferred green sample must fail the same full-field scorer.
- Every saved-case known-site pre-restoration error must meet the numeric bar;
  restored sites and input CFA must remain bit-exact. The ordinary saved MHC
  RGB/chroma and dense component scores are independently reproduced to
  1e-7 DN before using them as the comparison reference.

The finite-compatible oracle tests the declared operator. Arbitrary phase,
step and affine fields also expose genuine boundary/prior error and are not
misrepresented as exact interpolation nulls.

## Descriptive quality flags, not photographic admission

For each saved arm, compare full RGB/chroma RMS with its own same-CFA MHC
reference: at most `1.15 * MHC + 0.5 DN`. Preserve the original candidate/uniform
scores and all six historical quality failures separately; a better completion
cannot retroactively turn the fused CFA's noise or alias failures into passes.

Signed nonzero component error must be at most `max(1 DN,0.20*abs(truth))`.
False-channel amplitude must be at most
`max(3 DN,0.10*largest absolute true amplitude for that component)`. Both loss
and over-recovery fail. The 8-DN green therefore permits 1.6 DN error, not an
unbounded amplification. Dense-camera rank is not independent CFA sampling
identifiability; the red alias case remains explicitly ambiguous.

Retain a 41x41 neutral 0.30-x mode and its independently colored 0.20-R,
0.30-G, opposite-sign 0.20-B alternative, with bit-identical CFA and output.
Score and save both incompatible full truths. This declares the prior choice;
simultaneously passing both truths is not a universal requirement or a hidden
release gate. No method can identify both from that same input.

Also retain complete 33x35 affine and neutral-step outputs at an odd physical
origin. Report whole-field RMS/max and overshoot, without discarding borders.
Their fixed descriptive quality flags require max error <=0.01 normalized
and overshoot <=0.005 normalized. These flags join the saved-case quality
summary; failure does not become a transform-mechanics failure.

Only passing mechanics can permit a later bounded full-field cost. Synthetic
quality remains separate: root may still release one complete photographic
diagnostic with all adverse results retained. The full-image and fixed-witness
decision, and any later flat/second-insect transfer, remain mandatory.

# M81 — estimation merge pre-registration

**Frozen before any M81 arm was run.** Existing M2, M15, M65, M70 and M77
artifacts were read as source material. No M81 composition of the M70 target
with the M77 spatial gate ladder, no M81 output image, and no acceptance score
had been computed when this file was committed.

Every claim below is labelled **MEASURED**, **DERIVED** or **ARGUED**. A number
belongs to the exact configuration printed beside it; no bar is transferred to
another frame count, subject, tile size or statistic.

## 1. Question and arms

The mechanism under test is:

1. measure the stack's gate-free spectral effective frame count,
   `n_spec = sum_k(P_k - sigma_k^2) / max_k(P_k - sigma_k^2)`, without clipping
   a negative per-frame term;
2. find the spatial gate `T*` whose realised mean admitted count equals
   `n_spec`;
3. run the existing 17×17-regularised winner field and noise-gated arithmetic
   mean at `T*`.

**Arm C (control):** the existing regularised gated mean at the explicit
`--gate 4`.

**Arm A (candidate):** the same code and inputs at the stack-calibrated `T*`.
Only the gate may differ. The focus operator, regulariser, noise model,
clipping policy, output encoding, ROIs and frame order are held fixed.

**No-ship rule:** Arm A must satisfy every fatal control below and beat Arm C on
all five named stacks. One loss, one unreadable stack, or one unavailable
acceptance instrument means the default remains unchanged. Results are still
reported.

## 2. Locked data and configuration

All inputs are read-only under `D:\personal\macro`. Frames are filename-sorted;
no `--limit`, `--srgb`, `--stats`, or non-default memory flag is used.

| stack / subject | N | flat ROI, plane px | detail ROI, plane px |
| --- | ---: | --- | --- |
| `wrapped-text-1` / wrapped label text | 130 | `32,1312,256,256` | `2208,672,256,256` |
| `109MSDCF` / acrylic paint strokes | 22 | `1440,416,256,256` | `1952,1056,256,256` |
| `coffee-bean` / coffee bean | 105 | `32,416,256,256` | `1312,416,256,256` |
| `foam` / coffee foam | 100 | `1312,288,256,256` | `160,1952,256,256` |
| `bee-1` / bee anatomy | 299 | `2720,1568,256,256` | `1952,672,256,256` |

These are M77's all-frame G0' ROIs. Their achieved contamination and stability
controls will be copied beside every result rather than silently treated as
passing.

The spectral instrument is the M70 configuration: **24** fixed-grid
green-quincunx patches, each **256×256 GQ samples**; **Welch tile 128**, 50%
overlap, periodic Hann window; bands `0.025–0.050`, `0.100–0.150`,
`0.150–0.200`, and `0.200–0.2762` sensor cycles/pixel. Textured patches have
low-band peak signal / median model variance at least **10**. The target is the
mean of the three mid-band medians. Thus `--tile` is **128 for the spectral
calculation**. The merge has no `--tile` flag. M77's ROI-selection tile is
separately **256** and is not the spectral tile.

The measurement invocation, with `<T*>` replaced only after calibration, is:

```powershell
strehl stack D:\personal\macro\<stack> `
  --gate 4 <T*> `
  --flat-roi <flat-x,y,w,h> `
  --detail-roi <detail-x,y,w,h>
```

The private evidence binary is built with Rust 1.98.0 MSVC and a private
`CARGO_TARGET_DIR`; its commit, size, SHA-256 and complete invocation are
recorded in the output JSON.

## 3. Architecture fixed before implementation

**Decision: multiple passes, not a focus volume.**

Pass 1 folds the regularised winner field and the 24-patch spectral sufficient
statistics. Pass 2 revisits the regularised focus fields and solves the
admission-threshold quantile that yields `n_spec`. A final pass at the solved
gate produces the estimate. The production path may temporarily pay an
additional pass if keeping the M80-owned command implementation untouched makes
that unavoidable; the report must distinguish conceptual passes from actual
decodes and may not call four decodes “two-pass”.

Per-pixel through-focus state remains the existing fixed-size sufficient
statistics: winner, adjacent triple, top four values and indices, floor, far
peak, and two posterior moments. It is independent of N. No `width × height ×
frames` focus volume is retained.

**ARGUED:** an arbitrary post-winner gate cannot be solved by a single bounded
fold unless it carries a quantile sketch of every frame's required admission
threshold. A second visit preserves O(workers) memory and the decoder's warm
60-frame cost is already MEASURED at 0.91 s. The admission quantile sketch is a
mergeable bounded histogram over non-negative finite `f32` thresholds; its
resolution is an implementation-accuracy parameter, not a subject-dependent
gate constant.

**Explicit refusal:** there is no spatially local spectral gate in this
milestone. M70 MEASURED up to a 1.202× change when its GQ patch side was halved
from 256 to 128 and validated no smaller window. M77 MEASURED within-frame
non-uniform admission; that is a limitation of this global candidate, not
permission to invent an unvalidated local estimator.

## 4. Fatal instrument controls

### S — spectral estimator

1. **S1, implementation reproduction.** On each of the five stacks, the Rust
   target must agree within **2% relative** with a fresh run of M70's corrected,
   unclipped Python implementation at the exact configuration in §2. A mismatch
   makes that stack unreadable.
2. **S2, positive plant.** On a calibrated static spectral burst with N = 41,
   recovered `n_spec/N` must lie in `[0.95, 1.05]`.
3. **S3, negative plant.** On calibrated independent noise with N = 41,
   `abs(n_spec) <= 1`. The deliberately broken variant that clips each
   `P_k-sigma_k^2` at zero before summing must fail S3. The mutation is applied
   by a Python byte-string edit and the planted bytes are read back before the
   test runs.
4. **S4, model sensitivity.** Recompute each target with the photon-transfer
   variance scaled by **0.950** and **1.093**, M70's MEASURED fact-29 range. The
   full target span divided by the nominal target must be `<= 1.20`.
   M70 MEASURED its window-bounded statistic moving 14% over this range and its
   unwindowed statistic becoming non-measurable on deep stacks. The 20% bar
   allows that measured windowed spread plus margin; failure is fatal because a
   “self-calibration” dominated by known calibration error is not calibrated.
5. **S5, admissibility.** The nominal target must be finite and in `[1,N]`, at
   least one patch must pass the texture rule, and the implementation must
   refuse an active area too small for 256 GQ samples.

### G — gate solve

1. **G1, monotonicity.** Realised mean `n_eff` must be non-decreasing with gate
   on every stack.
2. **G2, target hit.** A fresh run at `T*` must realise mean `n_eff` within
   **1% relative** of `n_spec`.
3. **G3, bracket.** The solve must be bracketed by measured admission counts,
   not extrapolated. A target outside the measured bracket is unreadable.
4. **G4, controls.** Gate zero must admit exactly one frame at every pixel, and
   a gate wider than every finite focus gap must admit all N. The histogram
   mutation that reverses its cumulative direction must make G1 or G2 fail; it
   is planted and read back with Python before execution.

## 5. Acceptance observables and bars

The currently shipped `RETENTION =
sqrt(raw_gradient^2-model_gradient^2)` is **forbidden**: M77 MEASURED it at
9.963× and 8.819× on flat ROIs whose sibling statistic read as pure noise.

The detail observable is M80's repaired order-statistic-aware signal-gradient
amplitude, and it may be used only if M80's own noise-only null and detail
positive control both pass. If that implementation is unavailable or either
control fails, M81 is **INDETERMINATE and ships nothing**; no substitute is
chosen after seeing Arm A.

For each stack let:

- `H(T)` be M77 invariant 1's flat-ROI high-pass SD at gate T;
- `D(T)` be M80's repaired detail signal amplitude at gate T;
- `Q(T) = D(T)/H(T)`, a detail-signal-to-flat-residual ratio.

All three are reported, including M77's achieved flat contamination. The
candidate beats the control on one stack only when all of these hold:

1. `Q(T*) / Q(4) >= 1.01`;
2. `D(T*) / D(4) >= 0.98` (no purchased noise win may hide detail collapse);
3. G2 passes.

The 1% score margin prevents numerical equality being sold as a win. The 2%
one-sided detail bar is retained on the same five subjects, N values and ROIs
for which M77 registered it; it is not exported elsewhere. The M81 verdict
requires this per-stack result on **5/5**, never a pooled average.

## 6. “Never worse than one frame” floor

Three distinct statements are kept separate:

1. **Structural, every real pixel:** the winner remains unconditionally
   admitted, so every output has `n >= 1`; no raw argmax is emitted.
2. **Model, every real pixel:** the reported per-pixel predicted sigma must not
   exceed the same noise model's single-frame sigma.
3. **Truth-referenced plant:** on the static-burst fixture, Arm A's RMS error
   against the known latent must not exceed the pooled single-frame RMS in any
   scored 16×16 block, over three fixed seeds. Gate zero must fail at least one
   block, proving the test can reject a selector.

M40 and M62 MEASURED that statement 1 does **not** prove statement 2 at a
singleton: max-over-N selection inflates noise, and the current model has no
measured term for it. Therefore any real-stack singleton fraction above zero is
reported as an **unpriced floor exposure**. Unless M80 supplies and validates a
usable order-statistic correction that closes it, such exposure is fatal to
shipment under the requested everywhere invariant. It may not be hidden behind
mean `n_eff`.

## 7. Decision table

| condition | consequence |
| --- | --- |
| any S, G, M80 instrument, or floor control fails | report the failure; default unchanged |
| any one stack misses any §5 clause | report that stack; default unchanged |
| all controls and all 5 stacks pass | wire automatic calibration as the omitted-`--gate` default; retain explicit `--gate 4` as the reproducible control |

No deconvolution, depth posterior, occlusion unmixing, robustness/outlier mask,
or local spectral estimator is in scope. A result that makes one necessary is a
finding, not permission to build it.

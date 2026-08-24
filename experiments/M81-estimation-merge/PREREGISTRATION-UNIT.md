# M81 — pre-registration B: the focus-noise unit hypothesis

**Frozen before the new gate ladder, textured-tile unit calibration, corrected
gate arm, or unit-portability score was run.** M81's first, now parked,
spectral-count-to-admission arm had already run and was reported at commit
`bcde55e`. M70 §22 and M69 are source inputs to this amendment, not outcomes of
it.

**MEASURED disclosure.** This is not a blind sequel. M69 has already published
stack-level response-noise estimates, M77 has published coarse gate ladders,
and M81's parked arm has published one solved gate per stack. Their qualitative
direction is visible. The new primary observable below is therefore a fresh,
exactly common `mean n_eff = 4.000` target on a denser ladder and a new
texture-gated response-noise calibration. Its bars are fixed from the proposed
mechanism and the dispatch's explicit 2× falsification line, not chosen from
the result.

## B1. Source correction and question

**MEASURED.** M70 §22.6 says its spectral `n_eff` counts informative frames and
was never measured as an optimal hard-admission target. M81 therefore parks,
rather than deletes, the old `spectral n_eff -> T*` experiment. Its values may
be reported as diagnostics but may not choose this arm's gate.

**MEASURED.** M69's opening verdict does **not** identify a 4.06× per-stack
scale correction. Its directly evaluated Part-II coarse, regularised response
has a 2.104× stack-level span over 12 synthetic-replicate latents, while its
Part-I P2 estimate has a 1.186× span. The 4.062× number is a within-operator
texture-scale sweep on a controlled plant; M69 attributes it to local gradient
direction coherence and reports within-stack dispersion too. M69 also says the
true response noise on a moving-focus real stack is not directly measurable
without a textured static burst.

**ARGUED hypothesis U.** Conditional on a per-stack scalar estimate `rho_i`,
where the true coarse regularised response-noise SD is
`rho_i * FOCUS_NOISE_SD`, the gate's unit may be the dominant source of
cross-stack dispersion. If so, a raw gate `T_i` required to hit one common
admission target should become portable after conversion to
`C_i = T_i / rho_i`.

**ARGUED limitation.** This arm tests that scalar-unit hypothesis; it does not
claim that `mean n_eff = 4` is optimal. It also cannot externally validate
`rho_i` against real sensor response noise because the static textured burst
M69 requires does not exist. A pass would therefore be necessary but not
sufficient for shipment. A refutation is decisive against this scalar repair.

## B2. Locked stacks, data, and invocations

All RAW inputs remain read-only under `D:\personal\macro`. Frames are
filename-sorted. No `--limit`, `--srgb`, `--stats`, output image, or non-default
memory flag is used. The merge has no `--tile` flag.

| Class | stack / subject | N | flat ROI, plane px | detail ROI, plane px | role |
| --- | --- | ---: | --- | --- | --- |
| MEASURED | `wrapped-text-1` / wrapped label text | 130 | `32,1312,256,256` | `2208,672,256,256` | sibling test + five-stack arm |
| MEASURED | `wrapped-text-2` / wrapped label text | 120 | — | — | sibling portability test only |
| MEASURED | `109MSDCF` / acrylic paint strokes | 22 | `1440,416,256,256` | `1952,1056,256,256` | five-stack arm |
| MEASURED | `coffee-bean` / coffee bean | 105 | `32,416,256,256` | `1312,416,256,256` | five-stack arm |
| MEASURED | `foam` / coffee foam | 100 | `1312,288,256,256` | `160,1952,256,256` | five-stack arm |
| MEASURED | `bee-1` / bee anatomy | 299 | `2720,1568,256,256` | `1952,672,256,256` | five-stack arm |

**ARGUED.** The sibling pair is the cleanest falsification because M70 P34
measures their through-focus response agreeing within 4.7%. The five original
M77 stacks are still mandatory and determine shipping generality.

The fresh ladder is:

```text
--gate 0 0.25 0.5 1 2 4 8 16 24 32 40 48 64 96 128
```

The exact ladder invocation is:

```powershell
strehl stack D:\personal\macro\<stack> `
  --gate 0 0.25 0.5 1 2 4 8 16 24 32 40 48 64 96 128
```

The paired five-stack invocation is:

```powershell
strehl stack D:\personal\macro\<stack> `
  --gate 4 <4*rho_i> `
  --flat-roi <flat-x,y,w,h> `
  --detail-roi <detail-x,y,w,h>
```

**ARGUED.** The common target is exactly `mean n_eff = 4.000`. It is a
diagnostic count, not a quality optimum: it lies inside every stack's possible
`[1,N]` range, is close to the two sibling spectral counts without equating to
either, and supports one cross-stack question without transferring a product
bar.

## B3. Texture-gated unit calibration

**ARGUED primary estimator.** The calibration uses M69's directly simulated
coarse, regularised response-noise method, restricted to M70-textured tiles:

1. Load M70's committed full-stack spectral record for the same stack.
2. Use its exact **24 fixed patches**, **256 GQ samples = 511 sensor pixels**,
   **Welch tile 128**, 50% overlap, periodic Hann, and low-band
   `peak signal / median model variance >= 10` texture rule.
3. For each passing centre, extract a 512×512 sensor-pixel square from the
   middle RAW frame. Flat patches are excluded, not assigned zero.
4. Generate **32** independent sensor-model replicates with deterministic seed
   `0x4d81_0000 + 256 * stack_ordinal + patch_index`.
5. Push every replicate through M69's shipped-chain reimplementation:
   green luma, 3×3 Sobel, 27×27 box, photon-transfer normalisation, and 17×17
   regularisation. Fold temporal variance with Welford; retain no replicate
   cube.
6. Apply M69 B3's frozen-latent debias and divide by the compiled
   `FOCUS_NOISE_SD`.
7. Define the stack scalar `rho_i` as the median of passing patch means.

**ARGUED readability controls.**

- At least **3** patches must pass the texture rule.
- Every calibration tile is 511 sensor pixels across, above M70 P35's
  255-sensor-pixel floor; `--tile` for this spectral classification is
  **128**.
- A four-seed, 48-replicate zero-signal temporal control must recover
  `rho` in `[0.98, 1.02]`.
- The passing-patch maximum/minimum scalar span must be `<= 2.0`. A larger span
  refutes the premise that one per-stack scalar is a usable unit.

**ARGUED sensitivity estimators.** The decision table also reports, but does
not tune against:

- M69 Part-II B3's directly simulated central-2048 coarse `rho_true`;
- M69 fact 13's post-hoc P2 central-2048 `rho_true`.

They are source sensitivity arms because M69 measures them disagreeing on two
of 12 stacks. Neither may silently replace a failed primary estimator.

## B4. Portability decision

For each stack, solve the fresh ladder for raw gate `T_i` at mean admission
4.000 by log-gate/log-`n_eff` interpolation between the adjacent measured
positive rungs. Extrapolation is forbidden.

**ARGUED controls.**

- Every ladder must be non-decreasing in `mean n_eff`.
- Feeding each solved gate back through its interpolation segment must recover
  4.000 within **1% relative**.
- A known power-law ladder plant must recover its exact solved gate within
  **0.1% relative**.
- On the algebra plant `rho = [0.5, 1, 2]`,
  `T = [2, 4, 8]`, division must recover `C = [4, 4, 4]`.

**ARGUED binary decision.**

- **U1, sibling falsification:** hypothesis U survives only if
  `max(C_i)/min(C_i) <= 2.0` on `wrapped-text-1/2`; a larger span refutes it.
- **U2, five-stack generality:** shipment additionally requires
  `max(C_i)/min(C_i) <= 2.0` across the five M77 stacks.
- The primary and both source sensitivity estimators are reported separately.
  Primary U1 or U2 failure is fatal; a sensitivity-arm reversal makes the
  result estimator-dependent and also blocks shipment.

**ARGUED.** The 2× line is deliberately generous relative to M70 P34's 4.7%
physics agreement. It is the dispatch's proposed falsification threshold and
leaves margin for M69's estimator disagreement and ladder interpolation. It is
not exported as a product-quality tolerance.

## B5. Corrected gate-4 candidate versus shipped gate 4

**DERIVED.** `Gate::tolerance = T * sqrt(2) * FOCUS_NOISE_SD` is linear. A
portable corrected-unit constant 4 is therefore emulated by the unchanged
binary at raw gate `4 * rho_i`.

**ARGUED arms.**

- Control C: shipped gate 4.
- Candidate U: gate `4 * rho_i`, using only B3's primary texture-gated scalar.

Use M80's repaired cross-fitted observable only when its global controls and
the stack's M77 flat precondition pass. Let `D` be M80 detail signal amplitude,
`H` M77 flat high-pass SD, and `Q = D/H`.

Candidate U beats control C on one stack only if:

1. `Q(U) / Q(C) >= 1.01`;
2. `D(U) / D(C) >= 0.98`;
3. the stack-specific M80 flat and detail preconditions pass.

**ARGUED.** Shipment requires these clauses on **5/5**, plus U1 and U2. An
unreadable stack is not a win. The old unrepaired `RETENTION` is forbidden.

## B6. Single-frame floor and architecture

**ARGUED.** The existing two-pass merge architecture remains: pass one elects
the regularised winner and pass two averages admitted frames. The gate-unit arm
requires no focus volume and no extra merge decode. The experimental unit
calibrator keeps one 512×512 tile and Welford state per worker, fixed in stack
depth; it reads one latent frame plus M70's precomputed texture classification.

**ARGUED.** This is not yet a deployable calibration architecture. M69 says the
real response-noise level requires a textured static burst, and the current
corpus has none. No production API is added unless the hypothesis and quality
arms pass and an externally valid estimator exists.

The floor remains:

1. every pixel admits at least one frame;
2. model-predicted sigma does not exceed its single-frame model value;
3. the already-committed M81 truth-referenced plant passes;
4. every real singleton fraction is reported. Any nonzero singleton exposure
   remains fatal because its max-over-N selection penalty is unpriced.

## B7. Negative control and no-ship rule

**ARGUED.** A Python byte-string mutation changes the unit conversion in the
algebra plant from division to multiplication. The harness must construct the
replacement as bytes, verify it by read-back, require exactly one self-test,
observe a nonzero exit, and restore the source byte-for-byte. A zero-test
success is rejected.

**ARGUED final decision.** Any texture, unit, interpolation, M80, paired-arm, or
floor failure means no ship. If all measured arms pass but no externally valid
real-noise calibration exists, report the conditional success and still do not
ship. The parked spectral-count arm remains evidence, never the fallback
candidate.


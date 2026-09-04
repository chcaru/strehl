# M164 — a common-transfer veto for output-only comparisons

**RULING: BUILT AND COMMISSIONED, WITH A HARD SCOPE BOUNDARY.**

M164 implements a one-sided admissibility gate. It asks whether the realized
difference between two registered, linear-light rendered outputs is predicted
almost completely by one frozen low-complexity common-transfer model on
spatial tiles withheld from the fit. If so, it returns
`INADMISSIBLE_COMMON_TRANSFER`. It never ranks the outputs.

The result closes the executable **transfer-veto half** of M1, M2, and M9 for
the registered smooth-LSI and period-2 resampling families. It does not create
the external truth reference M1 and M9 still need, does not turn M2's output
residual into physical noise, and is not a proof that every possible common
filter has been excluded.

All measurements below are development-only. No holdout was opened and no
axis was scored.

## 1. Why the unrestricted question is vacuous

There is a necessary restriction that was missing from the plain-language
brief.

For finite periodic images, if every Fourier coefficient of `A` is nonzero,
then

```text
H[k] = FFT(B)[k] / FFT(A)[k]
```

defines a circular convolution taking arbitrary `A` exactly to arbitrary
`B`. An unrestricted “does some LSI filter map A to B?” test therefore fires
on almost everything. It is as degenerate as a test that fires on nothing.

**DERIVED.** A useful veto must freeze a physically relevant, low-complexity
transfer family before reading outcomes. M164 froze two
(`experiments/M164-transfer-veto/PREREGISTRATION.md`, “Non-vacuity
restriction”):

1. a smooth zero-phase LSI family containing scalar gain, every
   dihedral-symmetric local orbit through radius 3, and ten Gaussian
   difference responses from `0.20` to `3.00 px`;
2. a period-2, radius-2 polyphase family for twofold interpolation/resampling.

This makes M164 a conservative witness. A fire is positive evidence of a
common transfer. A non-fire outside the registered families is not evidence
that no common transfer exists.

## 2. Statistic and decision

Let

```text
D = B - A.
```

M164 fits `D_hat = (K-I)A + c`, where `c` is a nuisance black offset and `K`
comes from one of the two frozen families. It partitions deterministic
stride-3 samples into alternating `64 x 64` macrotiles, fits on one parity,
scores the other, then reverses the split. The model must therefore predict
unseen locations; it cannot earn a fire by memorizing the compared pixels.

The primary quantities are:

```text
r_rel  = RMS(D - D_hat) / RMS(D)
r_abs  = RMS(D - D_hat) / one_u16_LSB
r_tile = held-out per-tile residual / difference
r_fold = disagreement between the two independently fitted transfer responses
```

The veto fires only when all seven frozen predicates pass:

```text
RMS(D)                         >= 0.50 LSB
RMS((K-I)A)                    >= 0.50 LSB
informative tiles              >= 8
r_rel                          <= 0.12
r_abs                          <= 0.75 LSB
q90(r_tile)                    <= 0.25
r_fold                         <= 0.20
```

The implementation is
`experiments/M164-transfer-veto/transfer_veto.py`; the constants and the
`_PreparedFamily.evaluate` conjunction are the executable definition.
Malformed, non-finite, too-small, and unquantified inputs return
`INSTRUMENT_INVALID`, never a pass.

## 3. Why a common scalar cannot disappear

M135 retired normalized correlation because, cell by cell,

```text
rho(KY1, KY2) = rho(Y1, Y2)
```

for every common nonzero scalar transfer
(`docs/research/M135-detail-instrument.md`, “The precise impossibility
result”). M9's normalized-coherence channel independently reached the same
failure (`docs/research/M161-bar-feasibility.md`, “the named empirical acuity
channel is exactly blind”).

M164 does not normalize the transfer magnitude away. The first model column is
`A` itself. Under a scalar transfer `B = gA`,

```text
D = (g - 1)A,
```

so the fitted coefficient is `g-1`, the held-out residual falls to the
quantization floor, and the nonidentity effect remains an explicit hard gate.
The nuisance offset cannot cause a fire by itself because the separate kernel
effect must exceed `0.50 LSB`.

**MEASURED.** A gain delta of `0.00018` (`0.018%`) fired on `12/12`
development crops; `0.00016` fired on `11/12`. At `0.00018`, median
`r_abs = 0.294248 LSB` and median `r_rel = 0.087157`
(`refinement.json`, `scalar_gain_combined`).

**VERIFIED independently from the family fit.** A direct two-column
least-squares oracle on a `g-1 = 0.001` plant recovered
`0.000999951846` with `0.288359 LSB` residual, and the veto fired
(`verification.json`, “independent scalar algebra”).

**MEASURED.** Every one of the `72/72` blur-plus-gain arms fired. Their median
held-out residual was `0.289082 LSB`, maximum `0.291481 LSB`; median
`r_rel = 0.000277195`
(`commissioning.json`, `blur_plus_gain.summary`).

## 4. Development substrate and provenance

The texture stimulus was twelve fixed `512 x 512` crops from two already
burned DELIVER-V6 masters:

- `coffee-bean.tiff`,
  SHA-256
  `F38CA50ED1A680FA4DBCDD8D0513BE538DD31634B4E89AC6A34885944790A2EC`;
- `113MSDCF.tiff`,
  SHA-256
  `4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F`.

Green was IEC-sRGB-decoded, robustly mapped once into fixed headroom, and
quantized to linear `u16`. The exact crop origins and derived crop hashes are
in `commissioning.json`, `crops`. The current instrument source hash bound
into all final artifacts is
`E6C44578CA5913E4BB7FA966BBF1CD945F0AB084E2EEB8754B75435CD86E853B`.

Run 1 was preserved before the clipping repair as
`commissioning-run1-pre-clipping-control.json`, SHA-256
`085BD87531018FFC50787DFD44E72E7D7F4B6FBA1C3E2F07FEA785752CC89844`.
The outcome-informed refinements were frozen explicitly in
`AMENDMENT-2.md` and `AMENDMENT-3.md` before their pixels were read.

## 5. Positive transfer controls

“Reliable threshold” means the weakest tested strength firing on all twelve
crops with every stronger eligible strength also firing on all twelve.

| plant | weakest reliable strength | immediately weaker result | threshold-arm measurements |
|---|---:|---:|---|
| Gaussian blur | **sigma `0.27 px`** | sigma `0.26`: `4/12` | `12/12`; median difference `3.533769 LSB`; median `r_abs 0.286322 LSB`; median `r_rel 0.080794`; worst `r_rel 0.112822` |
| USM, radius `1 px` | **amount `0.0035`** | amount `0.0030`: `11/12` | `12/12`; median difference `3.670218 LSB`; median `r_abs 0.284251 LSB`; median `r_rel 0.076938`; worst `r_rel 0.104714` |
| scalar gain | **delta `0.00018`** | delta `0.00016`: `11/12` | `12/12`; median difference `3.299285 LSB`; median `r_abs 0.294248 LSB`; median `r_rel 0.087157`; worst `r_rel 0.115284` |
| bilinear shift/inverse-shift resampling | **`0.001 px` displacement** | `0.0008 px`: `10/12` | `12/12`; median difference `3.372672 LSB`; median `r_abs 0.285790 LSB`; median `r_rel 0.084427`; worst `r_rel 0.117874` |

Sources:

- blur and gain: `refinement.json`, `gaussian_blur_combined` and
  `scalar_gain_combined`;
- sharpening: `final-refinement.json`,
  `original_contrast_unsharp_combined`;
- interpolation: `final-refinement.json`,
  `resampling_shift_combined`.

**MEASURED.** Gaussian blur fired `12/12` at every tested sigma from `0.27`
through `3.00 px`.

**MEASURED.** The original-contrast USM stimulus remained linear through
amount `0.20`, and every tested amount from `0.0035` through `0.20` fired
`12/12`. Run 1's amount `0.50` and `1.00` arms clipped: respectively `142`
samples across `7/12` crops and `3,606` samples across `11/12`. They were not
common linear transfers after clipping. The preregistered repair compressed
contrast without changing the veto, produced zero clipped samples, and fired
`12/12` from amount `0.02` through `1.00`
(`refinement.json`, `original_unsharp_clipping_audit` and
`clipping_free_unsharp_mask`). Thus the veto catches both weak linear USM and
strong clipping-free USM; it correctly does not call USM-plus-clipping an LSI
transfer.

**MEASURED.** The explicit twofold box-down/bilinear-up polyphase resample
fired `12/12`; median held-out residual was `0.289793 LSB` and median
`r_rel = 0.000271326`
(`commissioning.json`, `resampling.by_kind.box-down-bilinear-up-2x`).

## 6. Null is movable, not tautological

**MEASURED.** Exact identity returned `IDENTITY_EQUIVALENT` on `12/12`,
with difference RMS exactly `0.0 LSB`.

The non-degeneracy challenge added a smooth local `32-LSB` disk to `B`.
That moved the observed difference to median `2.552833 LSB`, but it was not a
common transfer: median `r_rel = 0.985478`, median held-out residual
`2.515760 LSB`, and the veto fired `0/12`
(`commissioning.json`, `identity` and `movable_null_disturbance`).

**VERIFIED.** Two source mutations prove both decision directions are live.
Forcing the conjunction false changed a Gaussian positive control from
`INADMISSIBLE_COMMON_TRANSFER` to `NOT_VETOED`. Forcing it true changed the
local-disturbance negative control from `NOT_VETOED` to
`INADMISSIBLE_COMMON_TRANSFER`. The verifier first asserted the mutation
anchor occurred exactly once
(`verification.json`, “bidirectional mutation controls”).

## 7. False positives on legitimate differences

The frozen negative battery used `144` comparisons, `48` in each family:

1. independent heteroscedastic noise realizations of one latent scene;
2. complementary local resolved-detail changes under randomized smooth masks;
3. spatially varying blur/sharpen renders whose local sign and strength
   changed across the image.

**MEASURED.** False fires were:

```text
independent noise             0 / 48
local resolved detail        0 / 48
spatially varying transfer   0 / 48
overall                       0 / 144 = 0.000%
```

The exact one-sided Clopper-Pearson 95% upper bound is **`2.058879%`**
(`commissioning.json`, `legitimate_differences`; independently re-derived in
`verification.json`, “aggregate re-derivation”).

This is a measured rate on the frozen development battery, not a universal
population rate over arbitrary rendering programs.

## 8. The mandatory planted improvement

Two different improvement constructions answer two different questions.

### 8.1 Fresh-noise optical improvement

For every crop and noise level `0, 0.25, 0.5, 1, 2, 4, 8, 16 LSB`, M164
formed:

```text
A = G_0.80(S) + fresh noise A
B = G_0.40(S) + fresh noise B.
```

External truth confirms that every `B` improved: its truth MSE divided by
`A`'s ranged from `0.025575` to `0.033453`, median `0.027380`.

**MEASURED.** The veto fired **`0/96`**, including `0/12` at zero added
noise. This sharper output was not predicted to the absolute residual floor
by either frozen post-transfer family
(`commissioning.json`,
`planted_improvement.fresh_noise_optical`).

### 8.2 A truth-improving common sharpening

The constructive ambiguity arm used:

```text
A = G_0.80(S)
B = A + 0.50 * (A - G_1.00(A)).
```

External truth again says `B` is genuinely better: `MSE(B,S)/MSE(A,S)` ranged
`0.410392–0.688455`, median `0.431755`. But `B` is also literally `A`
passed through a common USM.

**MEASURED.** The veto fired **`12/12`**. Median held-out residual was
`0.287930 LSB` and median `r_rel = 0.000837185`
(`commissioning.json`,
`planted_improvement.truth_improving_common_usm`).

**RULING.** An output-only veto cannot, in general, distinguish “mere
sharpening” from a sharpening that truth proves was an improvement. The same
observed pair satisfies both descriptions. M164 handles this honestly by
refusing the comparison. That is correct for an admissibility gate and means
the veto can reject a genuine improvement. It must never be described as a
quality metric.

## 9. What this changes for M1, M2, and M9

### M1 — detail

**PARTIAL UNBLOCK.** The executable veto half now exists for the registered
post-render family. It catches the exact common operations that defeated FRC,
FSC, normalized spectral SNR, magnitude-squared coherence, and NCC: blur,
USM, resampling, scalar gain, and blur-plus-gain.

M1 remains unscoreable until the independently sampled physical truth
reference, target, calibration lineage, and same-output binding in M135 exist.
M164 cannot supply those facts.

### M2 — noise

**PARTIAL UNBLOCK.** M159 measured the current flat-ROI residual rewarding
blur at `0.571215x`
(`docs/research/M159-noise-clause.md`, “Commissioning evidence and its
limit”). M164 now provides a same-output refusal when that reduction is
consistent with one of the registered common transfers.

It does not convert `R_box9` into physical noise, prove a target featureless,
or alter the adverse current `1.515208x` residual. A future M2 comparison
must bind the exact candidate/comparator bytes and settings to this veto.

### M9 — acuity

**PARTIAL UNBLOCK.** M164 supplies the missing post-transfer witness beside
M9's normalized repeatability channel. It does not make normalized coherence
measure acuity and does not supply the external truth needed to license the
acuity map.

**Overall assessment:** M164 genuinely unblocks the **implementation and
commissioning workstream** for the shared veto half of all three axes. It does
not, by itself, admit or score any of them.

## 10. Failure boundary and residual doubt

1. **Restricted family.** The full unconstrained LSI question is
   mathematically vacuous. A sufficiently exotic, long-support, asymmetric,
   spatially varying, or differently phased common operator may evade the
   frozen family. Non-fire is not proof of absence.
2. **Improvement ambiguity.** A genuine improvement implemented as a common
   filter is observationally indistinguishable from sharpening and is
   deliberately vetoed.
3. **Input contract.** Real use requires registered, linearized, same-grid
   outputs and a declared quantization step. Geometry or tone differences
   must be resolved before invoking the veto, not learned by it.
4. **False-positive scope.** `0/144` is strong commissioning evidence, but its
   one-sided 95% upper bound is still `2.058879%`, and the battery is planted
   rather than a random sample of all renderers.
5. **Verification authorship.** The fail-closed verifier is separately
   implemented and mutation-tested, but this lane authored both it and the
   instrument. A separate-author review remains desirable under repository
   rule 12.

## 11. Reproduction and verification

From `projects/strehl`:

```powershell
python experiments\M164-transfer-veto\commission.py
python experiments\M164-transfer-veto\refine.py
python experiments\M164-transfer-veto\final_refine.py
python experiments\M164-transfer-veto\verify.py
```

The verifier passed all seven groups:

- artifact JSON and finite-number parsing;
- source, amendment, input, and preserved-run hash binding;
- independent aggregate re-derivation;
- sharpening clipping attribution;
- independent scalar-gain algebra;
- fail-closed malformed-input behavior;
- bidirectional mutation controls.

The machine-readable verdict is
`experiments/M164-transfer-veto/verification.json: passed = true`.

## 12. Bottom line

**VERIFIED.** A non-degenerate common-transfer veto can be built without a
truth capture if its family is restricted before outcomes and its decision is
one-sided. This implementation catches weak blur, weak USM, scalar gain,
interpolation blur, twofold resampling, and blur-plus-gain while producing
zero fires on 144 registered legitimate differences.

**VERIFIED.** It is not fooled by the common scalar that killed the retired
statistics because it estimates the unnormalized transfer effect directly.

**VERIFIED.** It cannot tell a truth-improving common sharpening from a
cosmetic one. That limit is fundamental to the output-only observation, not
an omitted threshold.

**RULING.** The veto half of M1/M2/M9 is now available for the registered
transfer family. The truth half remains blocked on the owner's physical
capture, and no axis is scored.

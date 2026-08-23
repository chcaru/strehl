# M62 — pre-registration

**Written and committed before any arm was run.** Every number in §3 is an
expected value, not a measurement. The only things computed before this file was
written are plant properties (`out/01-latent-provenance.json`,
`out/02-fidelity.json`, `out/03-prereg-inputs.json`): the crop, the decode
round-trip, the model sigma, and the high-pass sd of the latent. No merge output
had been scored.

## 1. The plant

One real frame — `D:\personal\macro\109MSDCF\DSC00020.ARW`, frame 11 of 22, ISO
160, 17 May 2026, so **before** the circular polariser of fact 845. A 2048×2048
sensor crop at (y=1024, x=4096), RGGB-phased, is the **latent truth `L`**. It is
unclipped (max 2731 DN against a white level of 15360) and its binned green sits
at **1229.90 DN of signal**.

`N = 30` independent realisations are drawn as `Y_i = round(L + ε_i)` with
`ε_i ~ N(0, σ²(L − black))` per pixel, per CFA plane, in DN, clipped to the
14-bit container. Zero samples clipped.

## 2. Sensor constants — read from the crate, not retyped

Parsed at run time out of the built tree by `harness.constants()`, from
`crates/strehl-core/src/profile.rs`, `const A7C2: CameraProfile`, at the built
sha:

| constant | value | line |
| --- | --- | --- |
| `gain_divisor` | 436.8 | `profile.rs:229` |
| `base_iso` | 100.0 | `profile.rs:230` |
| `read_noise_e_low` | 4.20 | `profile.rs:231` |
| `read_noise_e_high` | 1.2392 | `profile.rs:232` |
| `second_base_iso` | 400.0 | `profile.rs:233` |
| black / white | 512 / 15360 | `noise.rs`, asserted present |

At ISO 160 that gives `g = max(160, 100) / 436.8 = 0.36630037` DN/e and
`RN_e = 4.20 e` (ISO 160 < 400), so `RN·g = 1.53846` DN and

```
σ²(S) = 0.36630037·S + 2.36686        (DN²)
```

Binned green `(G1+G2)/2` therefore carries a model sigma of **15.0479 DN** over
the measured ROI. **Everything here is in DN**, so facts 783–808's 2.174×
dark-signal step at ISO 400 — a labelling failure in the gain/read-noise split,
not an arithmetic error — cannot bite: it does not move any DN-domain
prediction, and this plant is at ISO 160 in any case, below `second_base_iso`.

## 3. The statistic, and why the shared-noise trap does not touch it

`L` is a real frame and so already carries one realisation of sensor noise:
`L = T + η`, `T` the noise-free scene. The `N` output frames all share `η`.

**Option (b) — keep it, and do the algebra.** Score against `L`, not against `T`:

```
Y_i − L      = ε_i                       Var = v
Ô − L        = (1/n) Σ_{i∈A} ε_i         Var = v/n     (A independent of ε)
```

`η` appears in neither residual. It is inside the definition of truth, so it
cancels identically rather than approximately, and the expected ratio of pooled
RMS residuals is **exactly √N**, with no ceiling and no correction term.

The trap is real, and it lands on every *other* reference choice:

| reference | expected ratio at N=30 |
| --- | --- |
| `L`, the defined latent (**this harness**) | **√30 = 5.4772** |
| `T`, the noise-free scene | `√[(v_T+v)/(v_T+v/N)]` = **1.3912** |
| box high-pass sd over a flat ROI (**the shipped CLI invariant**) | `√[(h²+G²v)/(h²+G²v/N)]` ≤ **1.3912** |

with `G = 0.99381` (`flat_ratio.rs::HP_NOISE_GAIN`) and `h` the high-passed true
scene. On *this* crop the latent's own high-pass sd is 59.9909 DN against a model
sigma of 15.0479 DN, so the CLI's own flat-ROI invariant is predicted to read
**1.0295** on a merge that is in fact achieving 5.4772. That is pre-registered as
a *prediction about the instrument*, not a defect of the merge.

`v_T` and `v` differ per pixel by `g·η` and agree in expectation; pooled over
891 136 ROI pixels the difference is ~0.002 %, which is why 1.3912 is quoted as a
single number.

Denominator: pooled mean-square residual over **all** `N` frames, never one
privileged frame (fact 441 measured a 1.60× swing from that choice). ROI is the
plane interior inset 32 px — the selection window radius is 13 and the
regulariser radius 8, so 21 px would suffice — giving 944×944 = 891 136 pixels.
Uncertainty is a 64×64 block bootstrap, 2000 draws.

## 4. Pre-registered expected values

`N = 30`, `√30 = 5.477226`.

| arm | what runs | pre-registered expectation |
| --- | --- | --- |
| **A0-k** | Python mean of the first `k` frames, `k ∈ {1,2,3,5,10,20,30}` | **exactly √k**: 1.0000, 1.4142, 1.7321, 2.2361, 3.1623, 4.4721, 5.4772 |
| **A1-t** | `strehl merge` on the burst at gate `t ∈ {0, 0.5, 1, 2, 4, 8, 16}` | `≤ √(mean n_eff)` printed by the same run, and `→ 5.4772` as `n_eff → 30` |
| **B1a** | constant selector: copy frame 0 at every pixel | **exactly 1.0000** |
| **B1b** | random per-pixel selector, uniform over 30 frames | **exactly 1.0000** |
| **B2** | `strehl stack` — the shipped unregularised argmax selector | **≤ 1.0.** Rule 4 puts raw argmax at 1.95–2.61× single-frame noise, so 0.38–1.00, and the essential prediction is *no noise reduction* |
| **B3** | `strehl merge --gate 0` — the shipped estimator configured as a selector | **≤ 1.0** |
| **T** | the CLI's own `--flat-roi` high-pass invariant on the same merged output | **1.0295**, ceiling 1.3912 |

Three independent noise seeds (0, 1, 2) for A0-30, A1 and B; the between-seed
spread is reported beside the block-bootstrap SE.

## 5. What makes the harness BROKEN rather than the merge bad

Declared now, so the verdict cannot be chosen after the fact:

1. **B1a or B1b outside 1.0000 ± 0.005.** The zero point is arithmetic. If a
   selector that copies one sample scores anything else, the statistic is wrong.
2. **B2 or B3 ≥ 1.05.** A harness that reports noise *reduction* for a selector
   has no power, and discipline 250's fourth un-failable check would be exactly
   what shipped.
3. **Any A0-k off √k by more than 1 %.** The ladder is arithmetic too; a miss
   means the estimator of the ratio is biased.
4. **A1 above √(mean n_eff) by more than the bootstrap SE.** No estimator can
   beat the average of the frames it admitted, so exceeding it means the
   reference or the ROI is wrong.

Failure of 1, 2 or 3 is reported as the finding, in the headline, ahead of any
number about the merge.

## 6. Also declared in advance

- Rule 34 applies and is **not** escapable: the noise is drawn from the same
  `g` and `RN_e` the merge gates with, so this plant validates the operator and
  is silent on the calibration. Arm C states what closes that and what does not.
- `strehl merge --limit 1` must reproduce the written frame to within the TIFF
  quantisation step (0.2266 DN). Already checked: max error 0.1133 DN, exactly
  half a step. If it had failed, nothing downstream would have been run.

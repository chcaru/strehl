# M62 — pre-registration, Arm D (real sensor noise)

**Written and committed before Arm D was run.** Arms A0/A1/B were already
measured at this point and are recorded in `out/04-arms.json`; nothing in Arm D
had been executed.

## Why this arm exists

Arm A's noise is drawn from the same `g` and `RN_e` the merge gates with, so
rule 34 applies without escape: it validates the operator and is silent on the
calibration. The corpus already contains a **real static repeat burst** that the
owner's §12 capture is not needed to obtain — the 242 dark frames arrive as 11
ISO groups of 22, and within a group nothing moves, nothing refocuses, and every
frame is a sample of the same latent. The latent happens to be the dark field
rather than a scene, and the exposure is 1/100 s rather than working exposure,
which is exactly fact 808's gap. But the noise is the sensor's own.

**Group: `D:\macro-dark-frames\118MSDCF`, ISO 100, 22 frames.** ISO 100 is the
profile's `base_iso` and sits in the low-gain mode, so `read_noise_e_low = 4.20`
governs and no part of the fact-783–808 ISO-400 labelling failure is in play.
First 2 frames discarded as stabilisation, as with every other use of the darks.
Set **A** = frames 2–11 (merged, `N = 10`), set **B** = frames 12–21 (truth).

## Statistic, and the two corrections it needs

`L̂ = mean(B)` is truth. It carries `v/10` of its own noise, and `A ∩ B = ∅`, so

```
E[MS(Y_i − L̂)]  = v + v/10          i ∈ A
E[MS(Ô  − L̂)]  = v·E[1/n] + v/10 + q²
```

`v̂` is the pooled within-`A` temporal variance and `q = 0.0654 DN` is the TIFF
quantisation sd, which matters here (0.32 DN of merged residual) and did not
matter in Arm A (2.75 DN). Both corrections are subtracted, both are reported
with their size, and the Python arm — which never touches a TIFF — carries only
the first. Fixed-pattern noise and every hot pixel are **constant across the
group**, so they sit inside `L̂` and cancel out of both residuals, exactly as the
frozen `η` does in Arm A.

## Pre-registered expected values

| arm | what runs | expectation |
| --- | --- | --- |
| **D1-k** | Python mean of the first `k` frames of `A`, `k ∈ {1,2,3,5,10}`, per CFA plane and on binned green | **exactly √k**: 1.0000, 1.4142, 1.7321, 2.2361, **3.1623** |
| **D1-σ** | pooled temporal sigma of one dark frame, per plane, against the profile | model is `RN_e·g = 4.20 × 100/436.8 = ` **0.96154 DN**. M4 §8.2 measured 0.9845–0.9866 DN at ISO 50/100, so **measured/model ≈ 1.025**, and the raw data's own 1 DN quantisation contributes 1/12 DN² of that |
| **D1-drift** | per-frame mean level across the group | flat. A trend means the latent is not static and D1 is void |
| **D2-g16** | `strehl merge --gate 16` on the same 10 frames, re-encoded with a pedestal | **√10 = 3.1623** |
| **D2-g0** | `strehl merge --gate 0` on the same frames | **≈ 1.0**, and this is the negative control repeated on real noise |

**A pedestal of +1230 DN is added to every pixel of every frame** before writing
D2's DNGs, because `write_merged` encodes `(raw − black).max(0)` and a dark
frame sits *on* the black level — half its samples would be clamped to zero and
the measurement destroyed. The pedestal is a constant, identical in every frame,
so it changes no temporal statistic. It puts the level at Arm A's 1230 DN of
signal, where the profile predicts a green-luma sigma of **15.05 DN** against a
sensor delivering about **0.68 DN**. That mismatch is deliberate and it is the
point: it is what a merge looks like when the calibration is 22× wrong. It
affects the gate and nothing else, and it is **not** a calibration test.

## What D can and cannot prove

- **Can:** whether the sensor's temporal noise is independent frame to frame.
  Correlated read-out noise, supply ripple or dark-current drift would put D1-10
  below √10, and Arm A is structurally incapable of showing it because Arm A's
  noise is drawn independent by construction.
- **Can:** whether the shipped merge reaches the arithmetic limit on noise it did
  not generate.
- **Cannot:** validate `g`. There is no signal, so the shot term never appears
  and only `RN_e·g` is exercised.
- **Cannot:** close fact 808. 1/100 s is not working exposure, and a dark field
  is not a scene.

## What makes D broken rather than the sensor bad

D2-g0 outside 1.00 ± 0.05, or any D1-k off √k by more than 2 %. Either means the
held-out-truth correction is wrong, and the arm is reported as broken.

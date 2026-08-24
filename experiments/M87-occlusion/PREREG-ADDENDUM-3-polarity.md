# M87 — Pre-registration addendum 3: the polarity falsifier

**Status: REGISTRATION. Written and committed BEFORE the measurement it
describes.** Addendum 2 is post-hoc and says so; this one is not.

**Provenance of the hypothesis.** Supplied by the orchestrator after my report
was committed (`af96687`), explicitly offered as *"a hypothesis to test, not as
a finding"*. I am treating it as such. It does not displace the registered
plan; it is folded in because it is cheap and because it can falsify the
mechanism the report already committed to.

> Pointer note: the orchestrator cited "discipline 572" for the
> hypothesis-not-finding rule. SYNTHESIS discipline 572 is the Jensen-inequality
> noise-gain defect (`1/sqrt(E[n])` vs `E[1/sqrt(n)]`), which is unrelated. The
> *instruction* stands on its own; only the citation is wrong. Logged under
> rule 15, same class as the M60/M63 and M6 pointer errors in §1 of the report.

---

## A3.1 What is being tested

The two-layer veiling model says the observation at a background pixel near an
occluding boundary is

```
I_k = alpha_k * (F conv PSF_k) + (1 - alpha_k) * (B conv PSF_k)
```

The orchestrator's falsifier is that the artifact should therefore **carry the
sign of `F - B`**, and should **reverse** when the contrast polarity reverses.

I accept the test and sharpen it. The model predicts more than a sign.

## A3.2 The derivation being registered (DERIVED, pre-measurement)

Let `d` be distance outward from the true silhouette, `k_F` the frame where the
foreground is sharp, `k_B` where the background is sharp.

1. **Near band** (small `d`): the focus field is dominated by the foreground's
   sharp edge, so the merge elects `k ≈ k_F` (MEASURED on the bee at step 11 —
   near-edge rank 0.675 vs far-field 0.429). At `k_F` the foreground blur is
   zero, so `alpha_{k_F}(d) = 0` outside the silhouette: the pixel is
   **unveiled but blurred**. Error vs truth is a *blur* error whose profile
   mean is ~0 because blurring preserves local mean.
2. **Veiled band** (intermediate `d`): the background's own focus peak still
   wins, so the merge elects `k ≈ k_B`; but at `k_B` the foreground is maximally
   defocused, so `alpha_{k_B}(d) > 0` and the pixel **is** veiled.
3. **Far field**: `alpha ≈ 0` for all `k`; no error.

So the signed error against ground truth is, to first order,

```
E(d)  =  merge(d) - truth(d)  ≈  alpha_{k_B}(d) * ( F̄ - B(d) )
```

This is the registered prediction, and it has three testable parts:

| # | prediction | what refutes it |
| --- | --- | --- |
| **N1 (sign)** | `sign(E)` over `d ∈ [3,40]` equals `sign(F̄ - B̄)` | E has the **same** sign in both polarity arms |
| **N2 (magnitude)** | `\|E\|` within a factor of 2 of the forward prediction `median_j[ alpha_{k̂}(d)·(F̄ - B_j(d)) ]` computed from **known** `alpha`, with no fitting | measured `\|E\|` < 25% of forward prediction |
| **N3 (shape)** | measured `E(d)` correlates with the forward-predicted profile, Pearson `r ≥ 0.5` across `d ∈ [0,64]` | `\|r\| < 0.5` |

N2 and N3 are the parts that matter. A sign test alone is weak: a coin has a
50% chance of passing it. N2/N3 use ground-truth `alpha` as a *forward* model
with zero free parameters, so they can fail even when the sign is right.

## A3.3 The arms

Levels are **swapped, not rescaled**, so both scenes contain the same two
luminance levels and near-identical global signal statistics. This is the
level-matching control the orchestrator asked for.

| arm | foreground | background | predicted `sign(E)` |
| --- | --- | --- | --- |
| `P_plus` | dark (`0.08`) | bright (`0.75`) | **negative** |
| `P_minus` | bright (`0.75`) | dark (`0.08`) | **positive** |

## A3.4 Confound controls (all registered here)

- **C-lvl** — level-matched swap as above.
- **C-sig** — repeat both arms with a **constant** focus normaliser instead of
  `green_luma_sigma`. This removes the signal-dependent nonlinearity in the
  focus measure entirely, and with it the fact-1064 class of explanation
  (noise model over-confident above 504 DN, −12.8% at 8000, so the bright side
  of every boundary is gated with a sigma that is too small). **If the sign
  flip survives C-sig it is not a gate artifact.**
- **C-gate** — arms run at pure selection (one frame per pixel), so the
  averaging gate cannot contribute.
- **C-mask** — profiles are taken from the **known** silhouette `m`, not from
  Otsu. The mask confound disclosed in addendum 2 D-mask cannot act here.

## A3.5 Real-data arm and its admission bar

A real reversed-polarity boundary is only admissible if it is a genuine
**occluding** boundary. A bright-on-dark *reflectance* edge at a single depth is
my placebo, not a polarity test, and the orchestrator's two suggestions (pale
thorax hairs against the darker body; the dark eye against pale hairs) are at
risk of being exactly that.

**Admission bar A:** the two sides must have median elected-frame separation
`|Δk| ≥ 20` frames (≈ the bee's own measured p10–p90 subject depth spread of 79
frames, so 20 is a quarter of it). Below that I will report the boundary as
**not usable** rather than treat a reflectance edge as an occlusion.

## A3.6 What each outcome means

| outcome | meaning |
| --- | --- |
| N1+N2+N3 all pass, both arms | veiling is the dominant mechanism; report §3 stands and gains a real test it could have failed |
| N1 passes, N2 or N3 fails | veiling is present but **not dominant**; a second mechanism carries most of the artifact |
| N1 fails (same sign both arms) | **veiling refuted as dominant cause.** The artifact is polarity-independent, which points at a selection/overshoot mechanism — the focus measure's own spatial support, or a winner-field discontinuity. The two-layer reconstruction should not be built into Rust |
| E ≈ 0 in the veiled band, artifact lives entirely in the near band | the halo is a **resolution** seam, not a **photometric** veil |

The last row is a real possibility that the orchestrator's framing does not
include, and it is registered here so that it cannot be discovered post-hoc.

## A3.7 Scope note on M85

M85's colour/resolution fix landed after `af96687`. It **cannot** move any
number in this report: every surviving measurement is computed from
`bee3-leg-luma.npy`, which `04-through-focus.py` builds by calling
`m87lib.read_planes` — the native Bayer green sites, black-subtracted. No
demosaic, no white balance, no colour matrix, no resample, no 2x2 bin, no
alignment. Only the discarded metric-v1 work (steps 01–03, 06–07) ever read a
rendered TIFF. This is verified, not assumed, and it is registered here before
the polarity result is known so it cannot be read as a convenient excuse.

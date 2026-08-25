# PRE-REGISTRATION — M120e: spatial smoothing of the per-frame weight field

**Written before any implementation or measurement exists. Committed first.**
Design only. M120 does not touch `crates/`; this is a proposal for whoever owns the
implementation.

---

## 0. Prior art gate (ORCH's precondition, rule 40)

`python experiments/ORCH-drift-check/prior_art.py weight smoothing spatial merge` returns
`M111-waxy-blobs.md` at score 160 with two PRIOR REFUSAL flags, plus M70, M95, M62, M91,
M60, M67, M77, M118, M97c.

**Searched for an existing refusal of *this* operator and did not find one.** The two
nearest neighbours are different objects:

| operator | what it smooths | status |
| --- | --- | --- |
| winner-field regulariser | the elected **index** (one scalar/pixel), before argmax | **shipped**; `SYNTHESIS.md:89` recommends it |
| `STREHL_SOFT_GATE` / M111 `softgate.rs` | the **admitted set/weights as a function of focus gap**, per pixel, independent of neighbours | **rejected 4×** |
| **this proposal** | the **K-vector of mixture weights, across space** | not found in corpus |

**The relevant M111 sentences, quoted as ORCH asked:**

- M111 §14 P3, on H7: *"`n_eff` high inside blobs — predicted high; `blobB` median **2.0**,
  `blobA` mean **1.77**, plane mean 81.9 — **REFUTED**."*
- M111 §14 P4: *"tightening the gate shrinks blobs — tightening makes it **worse**: gate
  0.25 → 97.30% of flat pixels elect, amplitude 1.264, visually the hardest arm —
  **REFUTED, wrong sign**."*
- M111 §15: *"The soft weight is the only direction left that does not move the default."*

**P3 is a direct, independent replication of M120 §31** (`R` vs `n_eff`, ρ = −0.7165,
p = 2e-07, narrow-admission windows R 2.714 vs broad 1.222). M111 measured `n_eff` ≈ 2
inside blobs against a plane mean of 81.9 a milestone before I did, while refuting a
different hypothesis. **M120 §31 should be recorded as a replication, not a discovery.**

---

## 1. Is it genuinely distinct from the soft gate? A structural argument, not an opinion

Write the merge at pixel `p` as `out(p) = Σ_k w_k(p)·f_k(p)`, `w_k(p) ≥ 0`, `Σ_k w_k(p) = 1`.

- The **soft gate** sets `w_k(p) = g(focus_k(p) − best(p))`. It depends only on `p`'s own
  through-focus response. It is a kernel along the **focus** axis.
- **This proposal** replaces `w` with `S ∗ w` (a spatial kernel `S` applied to each
  `w_k` across the image, then renormalised). It is a kernel along the **space** axes and
  leaves the focus axis untouched.

**The load-bearing property, and the reason this is not a blur:**

> `out(p)` remains a **convex combination of `{f_k(p)}` — the same pixel `p` in the input
> frames.** No neighbouring pixel's *value* ever enters. Smoothing the weights cannot
> transport detail across space, cannot create a value outside the per-pixel input range,
> and cannot produce a halo, because nothing is ever gathered from a neighbour.

A Gaussian blur of the output, by contrast, is `Σ_k S ∗ (w_k·f_k)`, which does mix
neighbouring **values**. These are different operators and the difference is exactly the
one M87's `STREHL_FIX_HALO` failure turned on.

**This does not make it safe.** Its real failure mode is *loss of focus selectivity*: as
`S` widens, `w` tends to spatial constancy, the merge tends to a plain mean of the
admitted set, and **focus stacking stops working**. That is what the controls below must
catch, and it is a different failure from blur, so it needs a different control.

## 2. Why the bound points here, and the endpoint that makes this honest

M120 §7 proves: for any **spatially constant** convex `w`, `Q ≤ 1.284` in a featureless
region. The shipped render reads `Q = 4.337`. Therefore the excess is produced by the
**spatial variation of `w`** — the exact quantity `S ∗ w` constrains. That is the whole
argument for this lever.

**But the endpoint is already measured, and it must be stated up front (M120 §23):** at
`S = ∞`, `w` is spatially constant, the merge becomes a plain mean, and a plain mean of
299 frames reads **0/40 windows over the kurtosis bar** with Laplacian RMS falling
92.6 → 33.0. **The fix provably works at one endpoint and provably destroys the photograph
at that same endpoint.**

**So the question is not "does weight smoothing fix the patchwork" — I already know it does
at `S = ∞`. The question is entirely whether a useful operating point exists.** This
pre-registration is therefore a **trade-curve measurement with a pre-declared acceptable
region**, not a point fix. Any result reported as a single radius is uninterpretable.

## 3. Estimator

Sweep `S` = Gaussian with σ ∈ {0, 2, 4, 8, 16, 32, 64, ∞} px (σ = 0 is the shipped arm;
σ = ∞ is the plain mean of the admitted set). At each σ, renormalise so `Σ_k w_k(p) = 1`.

Two scored quantities, both **dimensionless and gain-invariant** (M120 §29 withdrew an
absolute-Q comparison for exactly this reason):

- **`Q_flat`** — M120's `Q` over **featureless** ROIs. *Target: below **1.284**.*
- **`Q_tex`** — the same statistic over **textured, in-focus** ROIs. *This is the arm that
  kills it.*

Plus **`n_eff`** and the **elected-index entropy** per pixel, to confirm the operator is
doing what it claims and not silently reducing to admission-broadening.

## 4. Pre-registered bars — stated before any number exists

| # | gate | rule | verdict if failed |
| --- | --- | --- | --- |
| **G1** | flat-region fix | `Q_flat < 1.284` in **all** featureless ROIs | not a fix; report the best achievable `Q_flat` and stop |
| **G2** | **detail preservation (non-negotiable)** | `Q_tex` falls by **< 5%** vs shipped at the σ that first satisfies G1 | **it is a blur in disguise; reject** |
| **G3** | resolution | MTF50 on the resolution target falls **< 2%** | reject |
| **G4** | silhouette | halo ISO metric moves **< 1%** | reject — it has become `STREHL_FIX_HALO` |
| **G5** | distinctness | at the G1-satisfying σ, `n_eff` changes by **< 10%** | it reduced to the soft gate; reject under the standing 4× refusal |

**G2 is the arm I expect to fail**, and I am saying so in advance. If `Q_tex` and `Q_flat`
fall together in fixed proportion across the sweep, the operator has no selectivity and is
a blur wearing a hat. **A pre-declared direction:** the mechanism claims the weights vary
*spuriously* in flat regions (noise-decided argmax) and *meaningfully* in textured ones
(real focus differences). If that is true, `Q_flat` must fall **faster** than `Q_tex`.
**Registered discriminator: `(ΔQ_flat / Q_flat) / (ΔQ_tex / Q_tex) > 3` at the G1 radius.**
Below 3, I will report the operator as non-selective regardless of whether G1 passes.

## 5. Null

`S` applied to a **permuted** weight field — same marginals, neighbour relationships
destroyed by a random spatial permutation of pixel indices before smoothing, then unpermuted.
This has the same computational shape and the same per-pixel weight distribution but no
spatial coherence to exploit. **Registered: `Q_flat` must move < 2% under the null.** If the
null also fixes the patchwork, the effect is renormalisation arithmetic, not spatial
structure.

## 6. Placebo (rule 11)

Smooth a **frame-index-shuffled** weight field: apply `S` to `w_π(k)` for a fixed random
permutation `π` of the frame axis, then unshuffle. Spatial coherence is preserved exactly;
the correspondence between weight and frame is destroyed. **Registered: this must NOT fix
the patchwork** (`Q_flat` within 5% of shipped). If it does, the improvement comes from
weight-vector regularity alone and carries no information about which frame is right.

## 7. The detail control, spelled out because ORCH requires it

`STREHL_FIX_HALO` erased the bee's abdomen hairs while its own metric reported 72.9%
improvement (M87 §16.9: *"replaced by a smooth, milky, scalloped band … **It looks
worse.**"*). The generalisable failure is that **the metric did not measure the thing that
was destroyed.**

So, beyond G2/G3:

1. **Blur-Matched Fidelity**, M87's `56-bmf.py` design, reused verbatim: bisect a Gaussian
   until its COARSE-band suppression matches this operator's *exactly*, then compare FINE-band
   retention. **Registered: BMF > 2.0**, i.e. at matched coarse effect the operator must keep
   at least twice the fine structure a blur keeps. M87's halo correction scored 4.428; a
   value near 1.0 means "this is a blur".
2. **A named-feature arm.** The bee's abdomen hairs, at 1:1, before and after, shown to the
   owner. Registered in advance as a **veto**: if the hairs are visibly softened, the arm is
   rejected whatever the metrics say. This exists because M87's numbers were good and its
   picture was not.
3. **A non-occluding positive control** (M111 P50): a scene with the same thin bright
   structure and **no** occlusion. If the operator moves that scene as much as the real one,
   it is keying on silhouettes rather than on flat response.

## 8. What I predict, so it can be held against me

**ARGUED, not measured.** I expect **G1 to pass** at large σ and **G2 to fail there**, with
the selectivity ratio in §4 landing **between 1 and 3** — i.e. the operator will reduce the
patchwork but will not do so selectively enough to ship as a default. My reason: M120 §31
found the defect concentrated where `n_eff` is *small* (ρ = −0.7165), and those are
precisely the pixels near silhouettes where the weight field's spatial variation is
**real** rather than spurious. Smoothing cannot tell those two apart — the same
inability M87 hit, arriving by a different route.

**If that is right, the more promising lever is not smoothing `w` but fixing the *level*
the weights are mixing** — which is M122's `--photometric`, and which M120 §35 measures as
**better in its idealised form (−2.2%) than in its shipped fitted form (+9.5%)** on
`bee-3-cpl`. I would spend the next milestone there before here.

# M69 pre-registration 2 — the *fine* field's form

Written and committed **before any number in arms B1–B4 existed**. The original
`PREREGISTRATION.md` (commit `33f3565`) is left byte-identical; this is a second
binding record for a second question, not an edit of the first.

## Why there is a second one

M69's headline was that `FOCUS_NOISE_SD` should not be a constant: the same
operator's response noise spans **4.06×** on a controlled plant, driven by
gradient-*direction* coherence across the operator's support (M69 facts 18–19).
**That was measured on the coarse, regularised selection field only.**

SYNTHESIS facts 500 / 580 / 753 establish that the second constant,
`FINE_FOCUS_NOISE_SD = 0.090400`, is **correct as consumed** — its *scale* is
settled and measured to −0.000% by M45's Rust calibrator (fact 520). **Its
dispersion has never been examined.** The fine field differs from the coarse one
in exactly two respects, and I read both from source rather than assuming:

| | operator | window | normaliser | regulariser | constant |
|---|---|---|---|---|---|
| selection | Sobel `\|∇\|` | `WINDOW_RADIUS` = 13 (27×27) | `/σ(L)` | box r=8 (17×17) | `FOCUS_NOISE_SD` = 0.015214 |
| fine | Sobel `\|∇\|` | `FINE_WINDOW_RADIUS` = 2 (5×5) | `/σ(L)` | **none** | `FINE_FOCUS_NOISE_SD` = 0.090400 |

`focus.rs:250–259` (`compute_with_fine`) computes the gradient **once** and box-means it
twice, so the two fields are the same operator at two radii; `through_focus.rs:110–111`
states the fine field is consumed with **no** regulariser.

## The mechanism, stated without a sign

M69 fact 19 attributes the coarse field's dispersion to **gradient-direction
coherence across the operator's support**: where the deterministic gradient
direction is constant over the window, the `|∇|` responses add coherently and the
flat-field calibration — which assumes incoherent samples — misprices the noise.
The support falls from **29×29** (Sobel 3×3 ⊛ box 27×27, then ⊛ 17×17) to **7×7**
(Sobel 3×3 ⊛ box 5×5).

**Two consequences of that change act in opposite directions and I do not know
which dominates:**

- **(i)** A smaller support becomes direction-coherent at a *smaller* texture
  correlation length, so the coherent regime moves into the range of scales real
  macro texture actually occupies. This acts to *increase* dispersion.
- **(ii)** A smaller support averages fewer samples, so the response sits closer
  to the pointwise Rice limit, where the flat-field calibration is exact by
  construction. This acts to *decrease* dispersion.

**I predict neither.** The pre-registered observable below decides it. Removing
the regulariser is a third lever, and M69 fact 46 measured it to *widen* texture
dependence at radius 13 — but at radius 13 only, which is why B2 runs the full
2×2 rather than the fine cell alone.

## Arms

- **B1 — the crate's own calibration plant, 2×2.** `{radius 13, radius 2} ×
  {regulariser r=8, none}` on a 512×512 plane of pure iid N(0,1) with
  `unit_sigma_model()` (σ ≡ 1), 12 seeds. This is the configuration
  `merge.rs:1197` and `through_focus.rs:1052` calibrate in. **Control arm, not a
  result arm.**
- **B2 — the controlled texture sweep, 2×2.** M69 arm A3's plant *unchanged*:
  `SIZE = 512`, `NREP = 48`, `ELLS = [2, 4, 8, 16]`, the same 12-point `Z_GRID`,
  the same `make_latent` normalisation by `S_SOBEL`. Because `S_SOBEL` is
  radius-independent, `z = ν/s` means the same thing at both radii and the two
  fields are directly comparable on one latent.
- **B3 — the corpus.** Per-stack fine-field `ρ_true` over all 12 stacks, by the
  method of M69 arm A2/§6, comparable to M69 fact 13's coarse span of 1.186×.
- **B4 — pricing at the point of consumption.** What the measured dispersion does
  to `bimodality_sigma` (`through_focus.rs:614`) and to the shipped placebo cut
  (`merge_cmd.rs:1737–1746`).

## Observable

For each of the four cells, on the identical `(ℓ, z)` grid:

```
rho(ell, z) = SD_interior( field(latent(ell, z) + noise) ) / C
```

where `C` is that cell's own flat-plant constant from B1, so `rho` is a **ratio
of the same operator's output on two plants** and the constant cancels.

**Dispersion `D` = max(rho) / min(rho) over ℓ ∈ {2,4,8,16} at the largest z on
the grid (z = 40).** This is exactly how M69 fact 18 computed the coarse field's
**4.06×** (1.1386 / 0.2805), and D is quoted for all four cells.

## Registered decision rules

**E1 — is the fine field materially tighter than the coarse field?**
Comparator: `D` for `radius 2 / no regulariser` against the coarse shipped cell's
`D`, measured in the same run rather than quoted from fact 18.

- **TIGHT** if `D_fine < 1.5`
- **SAME-ORDER** if `D_fine ≥ 3.0`
- **INTERMEDIATE** otherwise — I will report the number and **not** award either
  verdict word.

**E2 — decomposition.** All four cells are reported whatever E1 says, so that the
radius lever and the regulariser lever are separated rather than confounded.

**E3 — corpus.** Fine-field per-stack `ρ` span over the 12 stacks, against the
coarse field's 1.186×. **Reported whatever it is; no bar attached**, because
M69's D2 already refuted the constant form on the coarse field via the
controlled arm and not via the corpus, and I will not attach a bar to a
comparator I have already shown is the weaker one.

**E4 — does any published conclusion move?** Procedure fixed in advance: read the
consuming milestone's instrument section and determine whether it consumes
`FINE_FOCUS_NOISE_SD` or `bimodality_sigma` at all. **If it does not, report it
immune and run no further arms against it** — rule 40.

## The outcome that would make me report the fine field safe

**`D_fine < 1.5` at E1.** In that case the fixed denominator in
`bimodality_sigma` is defensible on dispersion grounds, I will say so plainly,
and this will be the first constant in this project to survive a form check.
**That is a fully successful outcome and I have no stake in the alternative.**

## Controls, each with what it cannot separate

| id | control | bar | consequence if NOT MET |
|---|---|---|---|
| **K11** | B1's `radius 2 / no reg` cell reproduces `FINE_FOCUS_NOISE_SD` | within **2%**, the crate's own tolerance at `through_focus.rs:1229` | **B2's fine cells and B3 are VOID** — the instrument is not the shipped fine field |
| **K12** | B1's `radius 13 / reg 8` cell reproduces `FOCUS_NOISE_SD` | within **2%** | the whole 2×2 is void; the instrument is not the shipped operator at all |
| **K13** | B1's `radius 2 / reg 8` cell reproduces fact 500's `0.027613` | within **2%** | flagged; this is an *external* cross-check against a quantity measured three times independently (fact 769, M43/M52/M54) and a miss impugns my instrument, not theirs |
| **K14** | B1's `radius 13 / no reg` cell against fact 528's `0.018847` | **ratio** to the reg cell within **2%** of M45's 1.2391 | flagged. **Declared in advance:** M69's arm A8.1 read `0.019044` in this cell, `+1.05%` above M45's absolute value, while its *ratio* agreed to 0.28%. I therefore test the ratio, and a ~1% absolute offset is expected from plant configuration and is **not** a failure |

**What K11–K14 cannot separate.** All four compare my Python instrument against
constants produced by the crate's Rust instrument on a plant of the same
*description*. A shared error in the *description* — the operator, the Sobel
scaling, the normalisation order — would pass all four. They pin the
implementation, not the specification. M69's K2 (0.031% against the shipped
binary's own printed `n_eff` on real planes) is the control that pins the
specification, and it was run on the coarse field only.

## The circularity, named in advance

**Where it bites.** B1 is a direct comparison against `FINE_FOCUS_NOISE_SD` and
is therefore *not* independent of it. That is why B1 is declared a control and
not a result.

**Where it does not.** B2 and B3 are **ratios of the same operator's output on
two plants**. The constant cancels algebraically. Every dispersion number `D` in
this pre-registration would be unchanged if `FINE_FOCUS_NOISE_SD` were 0.05 or
0.5. This is the same structure as M69 fact 35 item 2, and it is why the
dispersion question is answerable while the *level* question is not.

**Where it bites and I cannot remove it.** B4 prices the effect against the
shipped placebo cut, which is itself derived from the same fine field. A change
in the fine field's dispersion moves both the statistic and its calibration, and
B4 will say which of the two it is quoting at every number.

## What this will not do

- **No file under `crates/` will be modified.** Every arm is measurement.
- I will not re-derive M69's coarse-field results, M62's acceptance-battery
  sensitivity (already priced by algebra in `M62-ruling-M64-addendum.md`), or
  any conclusion of the consuming milestone that E4 finds immune.
- I will not rule on whether `FINE_FOCUS_NOISE_SD` should change value. M69's
  §9 recommended against changing `FOCUS_NOISE_SD`'s value on a 1.5% corpus
  error; facts 500/580/753 have already settled this constant's scale far more
  tightly than that, and **the scale is not what I am asking about**.

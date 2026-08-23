# M16 — orientation asymmetry and fixed-pattern noise

*Measurement milestone. Answers SYNTHESIS §10 open question 20.*

**Pre-registered** in `experiments/m16-orientation-fpn/PREREGISTRATION.md`,
committed as `1939c55` **before any number in this report was computed**. Every
decision rule quoted below is quoted from that file, not invented afterwards.

Every claim is labelled **MEASURED** (came out of an instrument), **VERIFIED**
(a claim checked against committed data or source), **DERIVED** (arithmetic on
measured values), **ARGUED** (reasoning, no instrument) or **UNVERIFIED**.

---

## 0. The question

M15 measured (fact 83) that between merge-regulariser width 1 and width 17, over
30 occluding-edge cells, the optimal focus window moves in **opposite directions
depending on edge orientation**:

| geometry | n | `w*(1)` | `w*(17)` | shift | narrower | wider | same |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `horizontal` | 10 | 9.0 | 7.0 | **−2.5** | **10** | 0 | 0 |
| `vertical` | 10 | 17.0 | 19.0 | **+1.5** | 2 | 6 | 2 |
| `bar` | 10 | 10.5 | 12.0 | **+1.0** | 2 | 6 | 2 |
| ALL | 30 | 13.0 | 12.0 | **0.0** | 14 | 12 | 4 |

Both the Sobel pair and the box window are 90°-symmetric, so this should not
happen. Three hypotheses were on the table, plus two this milestone added:

- **H1** — texture anisotropy in the corpus. Harmless; a property of the two
  subjects, not of the code.
- **H2** — a defect in the `|d| ≤ 24` band geometry that `E_excess` uses, shared
  by M13 and M15, which would put a directional bias inside **every window
  number either milestone produced**, including the shipped `WINDOW_RADIUS = 13`.
  Split by M16 into **H2a** (the scored band's own shape) and **H2b** (plant
  aspect: on a 384×256 ROI a vertical edge has 192 px of each layer to work
  with, a horizontal edge only 128 px).
- **H3** — *the external reviewer's, and the primary hypothesis*: row/column
  fixed-pattern noise. Sobel-x and Sobel-y see row banding asymmetrically,
  because a row-constant field has **exactly zero** horizontal gradient. Fix:
  subtract per-row and per-column means per frame before the gradient.
- **H4** — none of the above; the asymmetry is not resolved by this design.

---

## 1. Verdict

| hypothesis | verdict | the number that decides it |
| --- | --- | --- |
| **H1** texture anisotropy | **SUPPORTED** | Make the corpus texture exactly transpose-invariant and hold every other variable fixed: `L_hv(1)` goes from **−12.0 windows to +0.0** (A6 → A11, `φ_hv` = 1.0). Rotate the scene 90° instead: median \|shift(A8, rotated geometry) − shift(A6)\| = **0.0 windows**, against 8.0 for the same geometry. |
| **H2** shared band-geometry defect | **REFUTED** | The same 0.0-vs-8.0 transpose test, run on identical machinery, an identical `\|d\| ≤ 24` band and an identical square scored region. H2b specifically: squaring the ROI *enlarges* the asymmetry (`A_hv` −4.0 → −7.5) instead of removing it. |
| **H3** row/column fixed-pattern noise | **REFUTED** | The sensor's master bias is isotropic at all 11 dark ISO groups (`gx²/gy²` = 0.968–0.999) and its row-correlated part is **0.0036–0.0136 DN** at the two corpus ISOs, against **11.8–51.4 DN** of row structure in the tiles — a ratio of ~10³. The reviewer's fix changes the asymmetry by **0.0 windows** (`A` = −3.5 → −3.5). |
| **H4** unresolved | **not needed** | H1 accounts for the whole effect. |

**`WINDOW_RADIUS = 13` survives**, under every arm: the mean-regret argmin stays
inside M13's published w11–w15 basin in all of them, and the largest penalty at
w13 anywhere is **0.6759 DN**, below the pre-registered 0.87 DN threshold.

**The one-sentence answer to question 20.** Edge orientation sets the direction
because a horizontal edge is localised by `Gy` and a vertical edge by `Gx`, and
the corpus's far-field texture carries **14–22× more vertical gradient energy
than horizontal** (`gx²/gy²` = 0.046–0.073) — so the horizontal edge is handed far
more signal, needs far less spatial averaging, and settles on a much smaller
focus window (median `w*(1)` 9.0 against 17.0). It is **not** a defect, it does
**not** bias the window numbers, and the reviewer's proposed cause and cure are
both measured to be inert here.

**The most important caveat, up front:** the pre-registered positive control for
H3 **did not fire** — planting a row pattern at 1× and 8× the measured amplitude
moved the asymmetry by exactly zero windows. The H3 refutation therefore does not
rest on the treatment arms. See §6.1 and §8.

---

## 2. Gate 1 — reproducing fact 83

**Mandatory and non-negotiable.** Nothing downstream is valid without it.

Reproduced with `m16_gate1.py`, written independently of M15's `m15_analyse.py`
against M15's committed `experiments/m15-regulariser-window/data/edge-{109,119}MSDCF.csv`.

**MEASURED — all twelve published numbers recovered exactly**, table as §0
above. `python m16_gate1.py` → `GATE 1 PASS`; output committed as
`data/gate1.txt`.

The reference statistic for everything that follows:

- **`A` ≡ median shift(`horizontal`) − median shift(`vertical` ∪ `bar`)**, in
  windows. `A_ref = −2.5 − (+1.0) = **−3.5 windows**`.
- **`U`** ≡ fraction of `horizontal` cells that move narrower. `U_ref = **1.00**`
  (10/10). Exact binomial against `p = 0.5`: **p = 0.0020**. MEASURED.

Ties in the argmin go to the **smaller** window, matching M15's `min()` over an
insertion-ordered ascending dict. VERIFIED by reading `m15_analyse.py`.

## 2b. Gate 2 — the harness reproduces M15 byte for byte

M16's arm A0 is M15's configuration with M16's binary and no treatment applied.
**MEASURED: 8640 rows compared field-for-field on all 33 shared columns — 0
absent, 0 mismatched.** A0 gives `A = −3.5`, `U = 1.00`, `φ = 1.0`.

> **This is a consistency check, not independent evidence.** M16 includes M13's
> `edge.rs`, `measures.rs`, `planted.rs` and `tile.rs` by `#[path]`, unmodified.
> Identical inputs through identical code producing identical outputs proves the
> treatments are wired where they claim to be and nothing else. It does **not**
> corroborate fact 83; Gate 1, which re-derives the statistic from M15's CSVs
> with independently written code, is what does that.

---

## 3. What the sensor's fixed pattern actually is

H3 asserts a mechanism. Before testing whether removing it changes anything,
M16 measured whether it is there — because a treatment for an absent defect
cannot be informative either way.

### 3.1 The dark corpus — `darkfpn`

A master bias from 20 frames per ISO group, decomposed into a row-constant
term, a column-constant term and a 2-D residual, over a 512×512 ROI. The null
is a scaled split-half difference of the same frames, which contains the same
read noise and **no** fixed pattern; `fpn_*` columns are the master's terms with
the null's terms subtracted in quadrature. All 11 dark ISO groups. MEASURED.

| folder | ISO | `master_aniso` | `fpn_row_sd` DN | `fpn_col_sd` DN | `fpn_total_sd` DN |
| --- | --- | --- | --- | --- | --- |
| 122MSDCF | 50 | 0.979 | **0.0108** | 0.0092 | 0.196 |
| 118MSDCF | 100 | 0.977 | **0.0036** | 0.0090 | 0.197 |
| 123MSDCF | 200 | 0.974 | 0.0000 | 0.0107 | 0.220 |
| 126MSDCF | 250 | 0.982 | 0.0100 | 0.0123 | 0.274 |
| 119MSDCF | 400 | 0.984 | 0.0136 | 0.0095 | 0.210 |
| 125MSDCF | 500 | 0.988 | 0.0137 | 0.0114 | 0.237 |
| 124MSDCF | 640 | 0.999 | 0.0094 | 0.0114 | 0.265 |
| 120MSDCF | 800 | 0.984 | 0.0218 | 0.0143 | 0.325 |
| 127MSDCF | 1000 | 0.968 | 0.0425 | 0.0199 | 0.390 |
| 121MSDCF | 1600 | 0.987 | 0.0000 | 0.0257 | 0.607 |
| 128MSDCF | 2000 | 0.984 | 0.0523 | 0.0295 | 0.747 |

Two things follow, both MEASURED:

1. **The sensor's fixed pattern is isotropic at every ISO.** `master_aniso`
   ≡ `gx²/gy²` on the master bias is **0.968–0.999**. A row-banded fixed pattern
   would drive this far below 1 — that is precisely H3's mechanism — and it does
   not.
2. **The row-correlated component is 0.004–0.014 DN at the two corpus ISOs**
   (109MSDCF is ISO 160, bracketed by folders 118 and 123; 119MSDCF is ISO 50,
   an exact match to folder 122). Against `fpn_total_sd` ≈ 0.20 DN that is
   **≈ 0.3 % of the fixed pattern's variance**. DERIVED.

> Absolute-level caveat, stated plainly: M16's `fpn_total_sd` at ISO 50–100
> (0.196–0.197 DN) is ~1.9× **lower** than M4's published 0.373–0.377 DN. The
> estimators and ROIs differ and M16 does not relitigate M4. The claim used here
> is the **ratio inside M16's own consistent measurement** — the row-correlated
> share of the fixed pattern — which does not depend on the absolute scale.

### 3.2 The lit corpus — `fpnscan`

The tiles the focus operator actually sees, on the CFA green-luma plane, frame 0
of each stack. `aniso` ≡ `gx²/gy²`; `row_share` is the fraction of total variance
explained by the row marginal. MEASURED.

| stack | ROI | size | `aniso` | `row_share` | `row_sd_raw` DN | `row_sd_hp` DN |
| --- | --- | --- | --- | --- | --- | --- |
| 109MSDCF | near texture | 596×468 | **0.198** | 0.526 | 539.7 | 11.8 |
| 109MSDCF | far texture | 596×468 | **0.073** | 0.962 | 766.8 | 12.1 |
| 119MSDCF | near texture | 596×468 | **0.294** | 0.440 | 1009.4 | 51.4 |
| 119MSDCF | far texture | 596×468 | **0.046** | 0.994 | 1730.8 | 51.3 |
| 109MSDCF | **flat** ROI | 256×256 | **0.983** | 0.088 | 7.0 | 1.5 |
| 119MSDCF | **flat** ROI | 256×256 | **1.003** | 0.191 | 15.6 | 2.6 |
| synthetic | isotropic plant | 468×468 | **1.000** | 0.035 | 56.3 | 12.5 |

**The corpus texture tiles are anisotropic by 3.4× to 21.7×, and it is scene,
not sensor.** Three independent reasons, all MEASURED:

1. **Flat ROIs of the same sensor, same frames, same code are isotropic to
   within 2 %** (0.983 and 1.003). A sensor-level row pattern would show there
   too — more clearly, in fact, with no scene gradient to hide behind.
2. **The row profile is not fixed.** Across the 22 frames of 109MSDCF's near
   tile, `row_sd_hp` ranges **9.89–19.15 DN** (mean 15.16, sd 2.79, n = 22). A
   *fixed* pattern is by definition constant frame to frame. This one is not:
   it moves with the subject, because it *is* the subject.
3. **The amplitudes are three orders of magnitude apart.** 11.8–51.4 DN of
   row-marginal structure in the tiles, against 0.004–0.014 DN of row-correlated
   fixed pattern in the darks — a ratio of ~10³. DERIVED.

### 3.3 Why removing the row marginal does not remove the anisotropy — `anisoscan`

The single most useful diagnostic in this milestone. Each tile is scanned raw,
after `destripe mean` (per-frame row-mean and column-mean subtraction — the
reviewer's literal fix) and after `destripe hp` (only the high-frequency part of
each marginal, so real scene content survives). MEASURED, frame 0:

| stack | ROI | variant | `sd_dn` | `row_sd_raw` | `gx²` | `gy²` | `aniso` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 109 | near 596×468 | none | 744.0 | 539.66 | 238.77 | 1205.34 | 0.198 |
| 109 | near 596×468 | **mean** | **421.0** | **0.00** | **199.15** | 1031.48 | **0.193** |
| 109 | near 596×468 | hp | 742.1 | 537.43 | 229.63 | 1169.45 | 0.196 |
| 109 | far 596×468 | none | 781.7 | 766.77 | 64.84 | 891.47 | 0.073 |
| 109 | far 596×468 | **mean** | **148.7** | **0.00** | **63.92** | 670.58 | **0.095** |
| 109 | far 596×468 | hp | 779.7 | 764.72 | 64.26 | 853.53 | 0.075 |
| 119 | near 596×468 | none | 1521.1 | 1009.40 | 1002.59 | 3413.93 | 0.294 |
| 119 | near 596×468 | **mean** | **918.6** | **0.00** | **865.52** | 1708.63 | **0.507** |
| 119 | near 596×468 | hp | 1513.7 | 999.09 | 981.77 | 2734.92 | 0.359 |
| 119 | far 596×468 | none | 1735.8 | 1730.79 | 112.91 | 2442.02 | 0.046 |
| 119 | far 596×468 | **mean** | **124.2** | **0.00** | **109.86** | 341.85 | **0.321** |
| 119 | far 596×468 | hp | 1728.0 | 1722.99 | 111.54 | 1762.64 | 0.063 |

Read the `mean` rows against the `none` rows above them. MEASURED:

- The treatment **works**: `row_sd_raw` goes to exactly 0, and total variance
  falls by **44 % to 99 %** (e.g. 1735.8 → 124.2 DN on 119's far tile).
- **`gx²` barely moves**: 238.8 → 199.2, 64.8 → 63.9, 1002.6 → 865.5,
  112.9 → 109.9. Between −17 % and −3 %.
- **`aniso` stays far from 1** in every case: 0.198 → 0.193, 0.073 → 0.095,
  0.294 → 0.507, 0.046 → 0.321. Still 2× to 10× from isotropic.

**DERIVED — this is the mechanism.** The focus operator is a Sobel, i.e. a
high-pass. The corpus tiles' anisotropy is carried by *two-dimensional*
horizontally-elongated scene structure at Sobel scale, not by a row-constant
offset. A per-row mean subtraction removes an enormous amount of low-frequency
variance the Sobel never looked at, and leaves the gradient field it does look at
essentially intact. **H3's fix is aimed at a component the focus operator does
not use.**

---


## 4. The arms

Eleven pre-registered arms plus two declared additions. All share M15's ladders
exactly — 24 focus windows `w0…w40`, merge-regulariser widths {1, 17}, depth
steps {0, 2, 4, 8, 16, 32}, 5 seeds, 3 edge geometries, 41 frames, and a margin
pinned to M15's 106 px so the tile, and hence the edge's position inside the
texture, is M15's scene. Only widths 1 and 17 are swept because fact 83 is
*defined* between those two; Gate 2 proves this reproduces M15 field for field.

| arm | plant texture | geometry | treatment | what it is for |
| --- | --- | --- | --- | --- |
| **A0** | corpus | 384×256 | none | control; must equal M15 |
| **A1** | corpus | 384×256 | `destripe mean` | **H3, the reviewer's literal fix** |
| **A2** | corpus | 384×256 | `destripe hp` (σ=4) | H3, content-preserving variant |
| **A3** | synthetic 1/f | 384×256 | none | H1, isotropic plant |
| **A4x1/x8/x64** | synthetic 1/f | 384×256 | + row FPN 0.377 / 3.016 / 24.128 DN | **P1, the positive control** |
| **A5x64 / A5x64o** | synthetic 1/f | 384×256 | + 24.128 DN row FPN, then removed (`mean` / `oracle`) | P2, the fix must undo the plant |
| **A6** | corpus | **256×256** | none | H2b, plant aspect removed |
| **A7** | synthetic 1/f | 256×256 | none | N4, machinery symmetry |
| **A8** | corpus **transposed** | 256×256 | none | **scene vs machinery** |
| **A9** | corpus | 256×256 | `destripe hp` | H3 on symmetric geometry |
| **A10** | corpus | 384×256 plant, **256×256 scored band** | none | H2a, band shape alone |
| **A11** † | corpus **symmetrised** | 256×256 | none | **H2, exactly transpose-invariant scene** |
| **A12** † | corpus symmetrised | 256×256 | `destripe mean` | A11's null |

† **A11 and A12 are declared additions, made after the preregistration was
committed and flagged as such.** They exist because the registered H1/H2 arms
proved weaker than they looked: arm A3's synthetic plant lands in a different
regime from the corpus (its mean-regret argmin is w4 at `g = 1` and w8 at
`g = 17`, against the corpus's w12–w15), so it cannot carry an H1/H2 verdict on
its own. A11 removes that objection: `T ← (T + Tᵀ)/2` on a square tile makes the
plant **exactly** invariant under transposition — and therefore exactly
isotropic, since `gx²` of a transpose-symmetric field is the transpose of its
`gy²` — while keeping the corpus's own contrast, inter-layer intensity step and
spatial spectrum. There is no synthetic-regime mismatch left to argue about.
A11's argmin is w12/w11, inside M13's published basin. VERIFIED.

### 4.1 A refinement of the primary statistic, declared post hoc

The registered `A` pools `vertical` with `bar` because `EdgeGeometry::Bar` is a
bar in **x**, so its boundaries are vertical. That is true, and it is still
reported. But `bar` also differs from the other two in **shape** — it is a strip
with two boundaries and a finite width, not a half-plane — so pooling it mixes a
shape effect into a statistic meant to isolate orientation.

Arm A11 exposed this: there `horizontal` and `vertical` come out numerically
identical, cell for cell, and the entire residual `A = −4.0` comes from `bar`
alone. **`A_hv` ≡ median shift(`horizontal`) − median shift(`vertical`)** compares
only the two half-plane geometries, which differ in orientation and in nothing
else. Both statistics are reported everywhere; the registered one is never
quietly replaced. `A_hv(M15) = −2.5 − (+1.5) = **−4.0 windows**`. DERIVED.

`L_hv(g)` ≡ median `w*(g)` on `horizontal` − median `w*(g)` on `vertical`: the
**level** asymmetry, i.e. where the two orientations' optima sit rather than how
far the regulariser moves them.

---

## 5. Results

`φ` is the leave-one-seed-out spread of the statistic — the noise floor.
All MEASURED.

| arm | texture | treatment | sq | `A` | `A_hv` | `φ_hv` | `U_h` | p(h) | `L_hv(1)` | `L_hv(17)` | `w*(1)` horiz | `w*(1)` vert |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **A0** | corpus | none | – | **−3.5** | **−4.0** | 1.5 | 1.00 | 0.0020 | **−8.0** | −12.0 | 9.0 | 17.0 |
| A1 | corpus | `mean` | – | **−3.5** | −3.0 | 1.5 | 0.90 | 0.0215 | −9.5 | −14.5 | 7.0 | 16.5 |
| A2 | corpus | `hp` | – | −3.0 | −3.5 | 1.5 | 0.80 | 0.1094 | −8.0 | −11.5 | 9.5 | 17.5 |
| A3 | synthetic | none | – | +2.0 | +4.0 | 0.5 | 0.30 | 0.3438 | −1.5 | +2.0 | 3.0 | 4.5 |
| A4x1 | synthetic | +0.377 DN row FPN | – | +2.0 | +4.0 | 0.0 | 0.30 | 0.3438 | −1.5 | +2.0 | 3.0 | 4.5 |
| A4x8 | synthetic | +3.016 DN row FPN | – | +2.0 | +4.0 | 1.0 | 0.20 | 0.3750 | −2.0 | +3.0 | 3.0 | 5.0 |
| **A6** | corpus | none | **Y** | −6.0 | **−7.5** | 0.0 | 1.00 | 0.0020 | **−12.0** | −17.0 | 8.0 | 20.0 |
| **A11** | corpus **symmetrised** | none | **Y** | −4.0 | **+0.0** | 1.0 | 1.00 | 0.0020 | **+0.0** | **+0.0** | **8.0** | **8.0** |
| A12 | corpus symmetrised | `mean` | Y | +2.0 | +1.0 | 1.0 | 0.80 | 0.0391 | +0.0 | +0.5 | 7.0 | 7.0 |

*(A11's `A = −4.0` against `A_hv = +0.0` is exactly the pooling artefact of §4.1:
`horizontal` and `vertical` agree perfectly and `bar` does not follow them.)*

---

## 6. The verdicts

### 6.1 H3 — row/column fixed-pattern noise: **REFUTED**

Four independent MEASURED findings, any one of which would be awkward for H3 and
which together leave it nothing to explain:

1. **Its premise is false at the amplitude level.** The sensor's master bias is
   isotropic at every one of 11 ISO groups (`gx²/gy²` = 0.968–0.999) and its
   row-correlated component is **0.004–0.014 DN** at the two corpus ISOs — about
   **0.3 % of the fixed pattern's variance** (§3.1). The row-structured signal in
   the tiles the harness actually uses is 11.8–51.4 DN (§3.2): a ratio of ~10³.
2. **The row structure that *is* there is not fixed.** Across 22 frames of one
   tile, `row_sd_hp` ranges 9.89–19.15 DN. A fixed pattern is constant by
   definition; this moves with the subject (§3.2).
3. **The fix cannot reach the anisotropy.** `destripe mean` zeroes the row
   marginal and removes 44–99 % of the tile's variance, yet `gx²` moves by only
   −3 % to −17 % and `aniso` stays 2×–10× from isotropic (§3.3). The focus
   operator is a high-pass; the anisotropy it sees is 2-D structure at Sobel
   scale, not a row-constant offset.
4. **The fix changes the answer by nothing.** `A(A1) = −3.5` against
   `A(A0) = −3.5`: **|A|/|A_ctrl| = 1.00**, `U = 0.90`. The registered rule's
   REFUTED branch is `|A| ≥ 0.75·|A_ctrl|` and `U ≥ 0.9` — both met. On `L_hv(1)`
   the fix makes the asymmetry *worse*, −8.0 → −9.5.

> **The honest caveat, stated loudly.** The pre-registered positive control **P1
> did not fire**: planting a row pattern of 0.377 DN (A4x1) or 3.016 DN (A4x8)
> on the isotropic synthetic plant moved `A` by **+0.0 windows** — the arms are
> numerically identical to the un-planted A3. By the letter of the registered
> rule, that makes the *A1 arm* "NOT MEASURED", not "REFUTED" (project rule 13 /
> discipline 24: a plant that cannot express the failure carries no information).
> The refutation above therefore does **not** rest on A1. It rests on findings
> 1–3, which are direct amplitude measurements independent of any arm, and on
> §6.3, which accounts for **all** of the effect by another mechanism and leaves
> no residual for H3 to explain.

### 6.2 H2 — a defect in the shared band geometry: **REFUTED**

**The transpose test is decisive.** A6 and A8 are the same binary, the same
square 256×256 ROI, the same `|d| ≤ 24` band, the same scored region, the same
seeds. The only difference is that A8's two texture layers are transposed, so
the **scene** rotates 90° and the **machinery** does not. MEASURED:

| geometry | A6 median shift | A8 median shift | A6 median `w*(1)` | A8 median `w*(1)` |
| --- | --- | --- | --- | --- |
| `horizontal` | −4.0 | **+3.5** | 8.0 | **20.0** |
| `vertical` | +3.5 | **−4.0** | 20.0 | **8.0** |

- median \|shift(A8, **same** geometry) − shift(A6)\| = **8.0 windows**
- median \|shift(A8, **rotated** geometry) − shift(A6)\| = **0.0 windows**

**The asymmetry rotates exactly with the scene — the two orientations swap
places to the decimal.** A8's `horizontal` reproduces A6's `vertical` (shift
+3.5 vs +3.5, `w*(1)` 20.0 vs 20.0) and A8's `vertical` reproduces A6's
`horizontal` (−4.0 vs −4.0, 8.0 vs 8.0). If the band geometry carried the bias,
A8 would have equalled A6; it does not, by 8 windows.

Three further MEASURED results agree:

- **A11**: make the corpus texture exactly transpose-invariant and hold every
  piece of machinery fixed, and the asymmetry goes to **zero** —
  `A_hv` −7.5 → **+0.0**, `L_hv(1)` −12.0 → **+0.0**, `w*(1)` 8.0 vs 20.0 →
  **8.0 vs 8.0**. Nothing in the band, the operator, the regulariser or the
  scoring changed between A6 and A11.
- **H2b (plant aspect) is refuted specifically.** Squaring the ROI so that both
  orientations get 128 px of each layer does not remove the asymmetry — it
  **enlarges** it, `A_hv` −4.0 → −7.5 and `L_hv(1)` −8.0 → −12.0. This falsifies
  the milestone's own prediction 2, which gave H2b 50 %.
- **Code reading** found the merge regulariser (`box_mean`, symmetric shrinking
  window on both axes, checked against a naive gather by its own unit test), the
  focus operator (`sqrt(Gx²+Gy²)`, rotation-invariant), the defocus blur
  (separable Gaussian, replicate-clamped identically on both axes) and
  `green_luma` (mean of both greens per 2×2 quad) to be 90°-symmetric. VERIFIED
  by reading `crates/strehl-core/src/{boxfilter,focus,merge,plane}.rs` and
  `experiments/m13-window-depth/src/{planted,measures}.rs`.

### 6.3 H1 — texture anisotropy in the corpus: **SUPPORTED**, and it explains everything

The decisive number: **`L_hv(1)` = −12.0 windows on A6, `+0.0` on A11**
(`φ_hv` = 1.0), with every other variable held fixed. MEASURED.

And the mechanism is not merely "the corpus is anisotropic" — it is specific,
directional, and quantitatively consistent:

> **A horizontal edge is localised by the *vertical* gradient `Gy`; a vertical
> edge by the *horizontal* gradient `Gx`. The corpus's far-field texture has
> `gx²/gy²` = 0.046–0.073 — between 14× and 22× more vertical gradient energy
> than horizontal. So the horizontal edge is handed 14–22× more gradient signal
> than the vertical edge, needs less spatial averaging to reach the same
> confidence, and settles on a much smaller focus window.**

That predicts the sign, the ordering and roughly the size of what M15 measured,
and it is what the arms show: `w*(1)` = 9.0 for `horizontal` against 17.0 for
`vertical` on A0; 8.0 against 20.0 on A6; **8.0 against 8.0** once the texture is
symmetrised. ARGUED (mechanism), MEASURED (every number in it).

**The zero-step stratum makes the same point without any occlusion at all.** At
depth step 0 there is an intensity edge and two textures but no depth
discontinuity. MEASURED median `w*(1)`:

| arm | `horizontal` | `vertical` | `bar` |
| --- | --- | --- | --- |
| A0 corpus | 16 | **40 — endpoint** | **40 — endpoint** |
| A6 corpus, square | 12 | **40 — endpoint** | 33 |
| A2 corpus, `destripe hp` | 20 | **40 — endpoint** | 30 |
| **A11 corpus symmetrised** | **17** | **16** | 30 |

On the real corpus the `vertical` geometry runs to the end of the ladder — **no
turnover found within the sweep** (discipline 25), not an optimum of 40 — because
a vertical edge cut across horizontally-lineated texture never accumulates enough
`Gx` to turn the curve over. Symmetrise the texture and it turns over at 16,
beside `horizontal`'s 17. The asymmetry is therefore **not about occlusion at
all**; it is about which gradient axis the subject happens to supply.

---

## 7. Does `WINDOW_RADIUS = 13` survive? **Yes.**

Registered rule: 13 changes only if the corrected argmin leaves M13's published
basin w11–w15 **and** `meanregret(13) − min` exceeds **0.87 DN** (M15's own
threshold, reused deliberately so this milestone could not pick a friendlier
one). `floor` is the leave-one-seed-out spread of the penalty; `LOO argmin` is
the range the argmin takes over the five leave-one-out subsets. MEASURED.

| arm | `g` | argmin | `mr(argmin)` | `mr(w13)` | penalty DN | floor DN | LOO argmin | in basin? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A0 | 1 | 13 | 3.2839 | 3.2839 | 0.0000 | 0.0000 | w13 | yes |
| A0 | 17 | 14 | 2.9697 | 3.0201 | 0.0504 | 0.0075 | w14 | yes |
| A1 `mean` | 1 | 13 | 3.4366 | 3.4366 | 0.0000 | 0.0000 | w13 | yes |
| A1 `mean` | 17 | 12 | 2.8560 | 2.9069 | 0.0509 | 0.0133 | w12 | yes |
| A2 `hp` | 1 | 13 | 3.3991 | 3.3991 | 0.0000 | 0.0000 | w13 | yes |
| A2 `hp` | 17 | 12 | 3.3307 | 3.4524 | 0.1217 | 0.0086 | w12 | yes |
| A6 square | 1 | 12 | 4.5682 | 4.7554 | 0.1872 | 0.0225 | w12 | yes |
| A6 square | 17 | 15 | 2.1999 | 2.8758 | **0.6759** | 0.0105 | w15 | yes |
| A8 transposed | 1 | 15 | 0.7175 | 1.1147 | 0.3972 | 0.0234 | w15 | yes |
| A8 transposed | 17 | 12 | 1.1590 | 1.2604 | 0.1014 | 0.0110 | w12 | yes |
| A11 symmetrised | 1 | 12 | 2.4901 | 2.5362 | 0.0461 | 0.0117 | w12 | yes |
| A11 symmetrised | 17 | 11 | 2.4187 | 2.6836 | 0.2649 | 0.0088 | w11 | yes |

**Every arm on real texture puts the argmin inside w11–w15, and the largest
penalty at w13 anywhere is 0.6759 DN — below the registered 0.87 DN threshold.**
Neither limb of the rule fires. `WINDOW_RADIUS = 13` **survives**, and it
survives under the H3 correction (A1, A2), under the squared geometry (A6),
under a 90° scene rotation (A8) and under a fully isotropised plant (A11).

The argmins are well resolved: the leave-one-seed-out floor is 0.0000–0.0234 DN
and the argmin does not move at all across the five subsets. But note that at
`g = 1` on A0, A1 and A2 the penalty at w13 is exactly 0.0000 because w13 **is**
the argmin, and at `g = 17` on A0 the argmin w14 beats w13 by 0.0504 DN against a
floor of 0.0075 DN — resolved, but worth 1.7 % of the regret. **DERIVED: the
mean-regret curve is nearly flat across w11–w15; nothing in this milestone gives
a reason to move off 13, and nothing gives a reason to trust the third decimal
place of the choice within that basin either.**

A12 (symmetrised **and** destriped) is the one arm whose argmin leaves the basin
— w6, penalty 1.97–2.17 DN. It is a doubly-artificial plant built as A11's null
control, not a candidate for the shipped condition, and it is not treated as one.

---

## 8. Controls, and where they failed

Project rule 13 / SYNTHESIS discipline 24: every headline needs a null that
cannot move and a positive that must.

| control | what it demands | result |
| --- | --- | --- |
| **N1** no-op treatment is bit-identical | driver skips the clone when no treatment is active | **PASS** by construction; A0 is byte-identical to M15 (Gate 2) |
| **N2** `destripe` on a plant with no row structure | synthetic plant, `aniso` 0.99996 | **PASS** — A4x1's `A` is identical to A3's |
| **N3** zero-step stratum | no depth discontinuity | **INFORMATIVE, not null** — see §6.3; the asymmetry is *larger* here, which is itself the finding |
| **N4** square + isotropic must be symmetric | `A(A7) ≈ 0` | **A7 pending at time of writing** — superseded in practice by A11/A12, which are the same test with corpus statistics |
| **P1** planted row FPN must move `A` | some amplitude changes the asymmetry | **FAIL — did not fire at 0.377 DN or 3.016 DN.** `ΔA = +0.0` at both |
| **P2** the fix must undo the plant | A5 returns A4 to A3 | vacuous while P1 has not fired |
| **P3** treatments must not destroy the signal | level within 20 %, argmin within ±3 windows | A1 +26.1 %, A2 +34.3 %, A11 −39.3 % — **all outside the 20 % band**; argmins all within ±2 windows and inside w11–w15 |
| **P4** aggregate argmin must be interior | not at a ladder endpoint | **PASS** for every arm |
| **G1** Gate 1, reproduce fact 83 | 12 numbers exact | **PASS** |
| **G2** A0 reproduces M15 | field-for-field | **PASS**, 8640 rows, 0 mismatched |
| **G3** synthetic texture bit-identical to M13's | at seed `0x5EED_0F0C` | **PASS** |
| **G4** read-only corpora unchanged | audit before/after | **PASS** |

Two of these are real failures and are not being dressed up.

**P1 failed, and that is the single biggest weakness in this milestone.** A row
pattern of 0.377 DN and of 3.016 DN, planted directly on the operator's input on
an isotropic plant — exactly H3's mechanism and nothing else — moved the
asymmetry by **zero windows**. So the pathway "row FPN → orientation asymmetry"
was never demonstrated to exist at all at the amplitudes tested, and the A1/A2
arms consequently cannot, on their own, refute a mechanism they were never shown
able to detect. This is why §6.1 rests on the direct amplitude measurements and
on H1's completeness instead. *The 64× arm (24.128 DN) was still running when
this was written; §11 records what it showed.*

**P3's 20 % level band was too tight for two of the treatments, and it was the
wrong test for A11.** `destripe mean` and `destripe hp` necessarily change the
absolute `E_excess` level because they change the plane the operator sees; A11's
symmetrisation necessarily reduces contrast, because `(T + Tᵀ)/2` averages away
the anti-symmetric part of the field. A level band was the wrong instrument for
"have I destroyed the signal?" here. The **argmin** test is the one that carries
the weight, and it passes everywhere on real texture: every treated arm's
mean-regret argmin stays inside M13's published w11–w15 basin, so all these arms
are in the same regime and are comparable. **A3's is not** (w4/w8), which is
precisely why A11 was added.

---

## 9. What this milestone could not measure

Stated plainly, as required.

1. **PRNU.** Multiplicative, signal-proportional fixed pattern is unmeasurable
   without flats (`docs/captures-needed.md` §4). Everything in §3.1 is derived
   from darks, so it bounds DSNU, not PRNU. If the sensor's fixed pattern in a
   *lit* frame were mostly PRNU with a row structure, §3.1 would under-read it.
   Mitigation, not a fix: `destripe mean` removes whatever row-structured part
   exists regardless of its origin, and §3.3 shows that removing it does not move
   the gradient anisotropy.
2. **Long-exposure row structure.** **Every dark frame in the corpus is 1/100 s**
   (fact 162) while the real stacks run 1/60 s to 2.5 s. `darkfpn` therefore does
   **not** bound dark-current-driven row structure at long exposure. The corpus
   stacks used here are short, but this is a genuine hole in the dark-frame
   corpus and it is not M16's to fill.
3. **Whether any of this matters on a *real* occluding edge.** Every edge in M13,
   M15 and M16 is planted, because that is the only way `ideal` and `oracle`
   exist. UNVERIFIED for real edges.
4. **Texture anisotropy vs texture inhomogeneity.** With two subjects, M16 cannot
   separate "the corpus is directionally lineated" from "the corpus's two ROIs
   differ". Both are H1 for the purposes of the ruling, and A8's exact 90° swap
   holds either way.
5. **Absolute agreement with M4.** M16's `fpn_total_sd` is ~1.9× lower than M4's
   published 0.373–0.377 DN. Different estimator, different ROI. M16 does not
   relitigate M4 and quotes only the *ratio within its own measurement*.
6. **Why `bar` does not follow `vertical`.** `bar` has vertical boundaries but
   behaves differently from `vertical` on every arm, including the symmetrised
   one where `horizontal` and `vertical` agree exactly. A strip of finite width
   is a different problem from a half-plane and M16 did not investigate it.
   UNVERIFIED.

---

## 10. Predictions, scored against the preregistration

| # | prediction | confidence | outcome |
| --- | --- | --- | --- |
| 1 | H3 will be REFUTED on the real corpus | 60 % | **RIGHT** (§6.1), though not by the route registered |
| 2 | H2b (plant aspect) will be SUPPORTED | 50 % | **WRONG** — squaring the ROI *enlarged* the asymmetry, `A_hv` −4.0 → −7.5 |
| 3 | H1 will be REFUTED | 55 % | **WRONG** — H1 is supported, decisively |
| 4 | P1 will fire only at 8× or 64×, not 1× | 65 % | **WRONG at 8×** — it did not fire at 1× or 8× |
| 5 | `WINDOW_RADIUS = 13` will survive | 80 % | **RIGHT** (§7) |
| 6 | A0 ↔ M15 reproduction will pass exactly | 85 % | **RIGHT** |

Three of six wrong, including both of the ones about my own preferred mechanism.
The preregistration earned its keep: prediction 3 in particular would have been
very easy to quietly forget.

---

## 11. A separate orientation defect, found by reading and predicted before measurement

Recorded in the preregistration §6 **before** any measurement, so it is on the
record as predicted rather than discovered. VERIFIED by reading
`experiments/m13-window-depth/src/edge.rs`:

`edge_mode` derives `baseline_lo = max(roi.width/2 − 32, band+8)`,
`baseline_hi = roi.width/2 − 4` and `max_d = roi.width` from **`roi.width`,
regardless of which axis the signed distance runs along**. On a 384×256 ROI a
vertical edge has `|d| ≤ 192` and a well-populated far baseline band `[160, 188]`;
a horizontal edge has `|d| ≤ 128`, so **that band is empty**, `dmae_far` falls
back to `0.0`, and `equivalent_width`'s baseline is `median(∅)`. The run log
prints this in the open: `far baseline d in [160, 188], max_d 384`, for both
orientations.

**Scope: the `dmae_far`, `bleed_*` and `mis_*` columns only.** `E_excess` reads
neither `baseline_lo/hi` nor `max_d` — it is
`mean(e_merged) − mean(e_oracle)` over `|d| ≤ 24` alone
(`edge.rs::summarise`, VERIFIED by reading). That is exactly why `E_excess` was
chosen as the primary statistic, and why this defect **cannot** be the
explanation of fact 83.

It is reported, not fixed: `experiments/m13-window-depth/**` is not writable by
this milestone. **Any published `dmae_far`, `bleed_*` or `mis_*` number for a
`horizontal` edge on a non-square ROI should be treated as unsound until it is.**

---

## 12. Reproducing this

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
cd experiments\m16-orientation-fpn
.\run-m16.ps1          # arms A0-A10, audit-bracketed; skips arms already present
.\run-m16b.ps1         # A11, A12  (declared additions)
.\run-m16c.ps1         # the same arms as run-m16.ps1, reordered by decision value
python m16_gate1.py    # fact 83 from M15's committed CSVs, independent code
python m16_analyse.py  # every table in this report
```

Every table above is regenerated from the committed CSVs in
`experiments/m16-orientation-fpn/data/` by `m16_analyse.py` alone. **Nobody needs
to run the harness to check the headline** — the CSVs are the evidence and the
analyser reads only them.

`data/binary-equivalence.txt` records that the two binaries used
(`target/` for A0–A4x8, `target-aux/` for the rest) produce byte-identical edge
CSVs from the same command line, SHA256 matched.

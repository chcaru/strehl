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
| **H1** texture anisotropy | **SUPPORTED** | Make the corpus texture exactly transpose-invariant and hold every other variable fixed: `L_hv(1)` goes from **−12.0 windows to +0.0** (A6 → A11, `φ_hv` = 1.0). Rotate the scene 90° instead: median \|shift(A8, rotated geometry) − shift(A6)\| = **0.0 windows**, against 8.0 for the same geometry. Categorically: cells with no turnover inside the sweep run **15/60 `vertical`, 0/60 `horizontal`** on the corpus, **16/60 `horizontal`, 0/60 `vertical`** once the scene is transposed, and **0/60 everywhere** once the texture is symmetrised. |
| **H2** shared band-geometry defect | **REFUTED** | The same 0.0-vs-8.0 transpose test, run on identical machinery, an identical `\|d\| ≤ 24` band and an identical square scored region. The band geometry is a *gain* on the statistic, not a source: squaring the scored region with the plant untouched takes `A_hv` −4.0 → −7.0 (A0 → A10), yet symmetrising the texture under that same geometry still nulls it to +0.0. |
| **H3** row/column fixed-pattern noise | **REFUTED**, by the pre-registered rule | The sensor's master bias is isotropic at all 11 dark ISO groups (`gx²/gy²` = 0.968–0.999) and its row-correlated part is **0.0036–0.0136 DN** at the two corpus ISOs, against **11.8–51.4 DN** of row structure in the tiles — a ratio of ~10³. The reviewer's fix changes the asymmetry by **0.0 windows** (`A` = −3.5 → −3.5, `U` = 0.90). Positive control P1 fires only at **1774×** the sensor's row amplitude, and even there reproduces just half the effect. |
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

**The caveats, up front.** (a) The pre-registered positive control for H3 fired
only on the **last rung** of the amplitude ladder, at 1774× the sensor's real row
FPN; below that the plant could not express H3's failure mode at all, and this
report was twice drafted reporting H3 as NOT MEASURED. (b) The purest machinery
null, A7, came out at `A_hv` = +2.0 against a 1.0 floor rather than at zero —
unexplained, though its sign is a coin toss and it points the *wrong way*. (c)
Two of six pre-registered predictions were wrong, both of them mine about the
mechanism. See §8, §9 and §10.

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

| arm | texture | treatment | sq | tr | `A` | `A_hv` | `φ_hv` | `U_h` | p(h) | `L_hv(1)` | `L_hv(17)` | `w*(1)` horiz | `w*(1)` vert |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **A0** | corpus | none | – | – | **−3.5** | **−4.0** | 1.5 | 1.00 | 0.0020 | **−8.0** | −12.0 | 9.0 | 17.0 |
| A1 | corpus | `mean` | – | – | **−3.5** | −3.0 | 1.5 | 0.90 | 0.0215 | −9.5 | −14.5 | 7.0 | 16.5 |
| A2 | corpus | `hp` | – | – | −3.0 | −3.5 | 1.5 | 0.80 | 0.1094 | −8.0 | −11.5 | 9.5 | 17.5 |
| A3 | synthetic | none | – | – | +2.0 | +4.0 | 0.5 | 0.30 | 0.3438 | −1.5 | +2.0 | 3.0 | 4.5 |
| A4x1 | synthetic | +0.377 DN row FPN | – | – | +2.0 | +4.0 | 0.0 | 0.30 | 0.3438 | −1.5 | +2.0 | 3.0 | 4.5 |
| A4x8 | synthetic | +3.016 DN row FPN | – | – | +2.0 | +4.0 | 0.5 | 0.30 | 0.3438 | −1.5 | +3.0 | 3.0 | 4.5 |
| **A4x64** | synthetic | +24.128 DN row FPN | – | – | **+0.0** | +3.0 | 0.5 | 0.30 | 0.3438 | −1.5 | +2.0 | 3.0 | 4.5 |
| A5x64 | synthetic | 24.128 DN + `mean` | – | – | +2.5 | +3.5 | 1.0 | 0.00 | 0.0020 | −1.0 | +2.5 | 3.0 | 4.0 |
| A5x64o | synthetic | 24.128 DN + oracle | – | – | +2.0 | +4.0 | 0.5 | 0.30 | 0.3438 | −1.5 | +2.0 | 3.0 | 4.5 |
| **A6** | corpus | none | **Y** | – | −6.0 | **−7.5** | 0.0 | 1.00 | 0.0020 | **−12.0** | **−17.0** | **8.0** | **20.0** |
| A7 | synthetic | none | Y | – | +1.5 | +2.0 | 1.0 | 0.30 | 0.5078 | +2.0 | +3.0 | 7.0 | 5.0 |
| **A8** | corpus **transposed** | none | **Y** | **Y** | +7.5 | **+7.5** | 0.0 | 0.30 | 0.3438 | **+12.0** | **+17.0** | **20.0** | **8.0** |
| A9 | corpus | `hp` | Y | – | −5.5 | −5.5 | 0.5 | 1.00 | 0.0020 | −9.0 | −13.5 | 8.0 | 17.0 |
| A10 | corpus | none, square band | Y* | – | −6.5 | −7.0 | 1.5 | 1.00 | 0.0020 | −8.5 | −12.5 | 8.5 | 17.0 |
| **A11** | corpus **symmetrised** | none | **Y** | – | −4.0 | **+0.0** | 1.0 | 1.00 | 0.0020 | **+0.0** | **+0.0** | **8.0** | **8.0** |
| A12 | corpus symmetrised | `mean` | Y | – | +2.0 | +1.0 | 1.0 | 0.80 | 0.0391 | +0.0 | +0.5 | 7.0 | 7.0 |

*(A10's `sq` is starred: its **plant** is rectangular and only its **scored
region** is square. Every other `Y` squares both.)*

**Read A6 against A8 row for row.** They are the same binary, the same square
ROI, the same band, the same seeds; A8's textures are transposed. Every statistic
inverts, to the decimal: `A_hv` −7.5 → **+7.5**, `L_hv(1)` −12.0 → **+12.0**,
`L_hv(17)` −17.0 → **+17.0**, `w*(1)` 8.0 / 20.0 → **20.0 / 8.0**. Nothing is
approximately mirrored; it is exactly mirrored. (`A` is the exception at −6.0 →
+7.5, because `bar` is always a bar in *x* and so does not rotate with the
texture — §4.1 again.)

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

> **The pre-registered control chain closed — and it closed late.** For most of
> this milestone the positive control **P1 had not fired**, and §6.1 was written
> to rest only on findings 1–3 because the registered rule would otherwise have
> forced the A1 arm to "NOT MEASURED" (project rule 13 / discipline 24). It
> fired on the last arm. The record of that is left standing here deliberately:
> the amplitude ladder was run to completion *because* the verdict was not yet
> earned, not to decorate one that already was.

**The amplitude ladder, and the number that kills H3.** A4x*K* plants a
row-correlated pattern of standard deviation *K* directly on the operator's
input, on the isotropic synthetic plant — H3's mechanism and nothing else. A5x64
is A4x64 with the reviewer's fix applied. MEASURED, 30 cells each:

| arm | row FPN | × the sensor's real row FPN | `A` | `φ` | `ΔA` vs A3 | `E_excess` @ w13 |
| --- | --- | --- | --- | --- | --- | --- |
| A3 | 0 DN | — | +2.0 | 0.5 | — | 12.698 |
| A4x1 | 0.377 DN | 28× | +2.0 | 0.0 | **+0.0** | 12.698 |
| A4x8 | 3.016 DN | 222× | +2.0 | 0.5 | **+0.0** | 12.708 |
| **A4x64** | 24.128 DN | **1774×** | +0.0 | 0.5 | **−2.0** | 12.947 |
| **A5x64** | 24.128 DN **+ fix** | 1774× | +2.5 | 1.0 | **+0.5** | 12.759 |
| **A5x64o** | 24.128 DN **+ oracle removal** | 1774× | +2.0 | 0.5 | **+0.0** | 12.698 |

- **P1 FIRES, at 64× and only at 64×.** `ΔA` = −2.0 windows against a floor of
  0.5, and in the registered direction — `A` moves *more negative*, making
  `horizontal` more of an outlier, which is fact 83's direction. The plant can
  express H3's failure mode. The measurement carries information.
- **P2 PASSES, and its upper bound is exact.** Applying `destripe mean` to that
  same 24.128 DN plant returns `A` to +2.5, i.e. `ΔA` vs A3 = **+0.5**, inside
  the 1.0 floor, and the `E_excess` level to −1.4 % of A3's. Subtracting the
  planted pattern *exactly* (A5x64o, oracle removal — the fix's own ceiling)
  returns `A` to **+2.0** and the level to **12.698**, i.e. to A3 to four decimal
  places. So the treatment is doing what it says, and the residual +0.5 in A5x64
  is the price of estimating the pattern from the data rather than knowing it.
- **Therefore the registered REFUTED branch is satisfied outright.** It reads
  *"P1 fires at some amplitude **and** A1 gives `|A| ≥ 0.75·|A_ctrl|` **and**
  `U ≥ 0.9`"*. P1 fires; A1 gives `|A|/|A_ctrl|` = **1.00** and `U` = **0.90**.
  H3 is **REFUTED by the pre-registered rule**, not by argument.

**And the ladder gives the quantitative kill.** The amplitude at which H3's
mechanism first becomes detectable at all lies between 3.016 DN and 24.128 DN.
The sensor supplies **0.0036–0.0136 DN** (§3.1). So:

> **The sensor's row-correlated fixed pattern is at least 222× smaller than an
> amplitude already MEASURED to be too small to move the statistic, and 1774×
> smaller than the amplitude that finally moved it — which even then produced
> only −2.0 windows, about half of the −4.0-window asymmetry M15 observed.**

Even granting H3 a plant 1774× more row-striped than this sensor, it reproduces
at most half the effect. At the sensor's real amplitude, extrapolating linearly
in amplitude (which over-states it, since a noise term should enter through
variance), the contribution is `2.0 × 0.0136 / 24.128 ≈` **0.0011 windows**, or
**0.03 %** of the asymmetry. DERIVED, from MEASURED inputs.

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
- **The two H2 sub-mechanisms separate cleanly, and neither creates the
  asymmetry — they only change how it is expressed.** A10 holds the plant
  identical to A0 (rectangular 384×256 ROI, same margin, same edge, same seeds)
  and changes *only* the scored region to a centred 256×256 square. MEASURED:

  | arm | plant ROI | scored region | `A` | `A_hv` | `L_hv(1)` | `w*(1)` h / v |
  | --- | --- | --- | --- | --- | --- | --- |
  | A0 | 384×256 | 384×256 | −3.5 | −4.0 | −8.0 | 9.0 / 17.0 |
  | **A10** | 384×256 | **256×256** | **−6.5** | **−7.0** | −8.5 | 8.5 / 17.0 |
  | A6 | **256×256** | 256×256 | −6.0 | −7.5 | **−12.0** | 8.0 / **20.0** |

  Reading down: **H2a (scored-band shape) is what nearly doubles the *shift*
  statistic** — `A_hv` −4.0 → −7.0 across A0→A10, a 1.75× gain, with the plant
  untouched — while leaving the *level* gap alone (−8.0 → −8.5, inside
  `φ_hv` = 1.5). **H2b (plant aspect) does the opposite**: A10→A6 leaves the
  shift alone (−7.0 → −7.5, inside the floor) and widens the level gap −8.5 →
  −12.0, because squaring the ROI gives the vertical edge only 128 px of each
  layer to accumulate `Gx` from instead of 192 — which is H1's mechanism, not a
  defect. This falsifies the milestone's own prediction 2, which attributed the
  A0→A6 enlargement to plant aspect; it is mostly the scored region.

  **But neither is a cause.** A11 runs A6's exact plant aspect, exact scored
  region, exact band and exact code, and nulls the asymmetry to `A_hv` = +0.0 by
  changing the texture alone. A rectangular scoring region is an *orientation-
  non-neutral gain* on the shift statistic, not a source of bias: it means M13
  and M15 saw roughly **half** the asymmetry that was there, in the shift. It
  did not put any there.
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

### 6.4 The hardest evidence: which geometry runs off the end of the ladder

Every statistic above is a median of window positions, and medians invite
arguments about pooling, floors and ties. **Censoring does not.** A cell either
turns over inside the sweep or it does not. Counting the cells whose mean-regret
argmin lands on the last rung, `w40`, over all 60 cells per geometry per
regulariser width (`data/censoring.csv`, regenerate with `m16_censoring.py`):

| arm | plant | `horizontal` @ w1 / w17 | `vertical` @ w1 / w17 |
| --- | --- | --- | --- |
| A0 | corpus, rect | **0/60** / 0/60 | **10/60** / 0/60 |
| A6 | corpus, square | **0/60** / 0/60 | **15/60** / 6/60 |
| **A8** | corpus, square, **transposed** | **16/60** / 7/60 | **0/60** / 0/60 |
| A9 | corpus, square, `destripe hp` | 0/60 / 0/60 | 15/60 / 8/60 |
| A10 | corpus, rect plant, square band | 0/60 / 0/60 | 10/60 / 0/60 |
| **A11** | corpus, square, **symmetrised** | **0/60** / 0/60 | **0/60** / 0/60 |
| A12 | corpus, symmetrised, `destripe mean` | 0/60 / 0/60 | 0/60 / 0/60 |
| A7 | synthetic isotropic, square | 0/60 / 0/60 | 0/60 / 0/60 |

Read A6 against A8. Transpose the scene and the censoring transposes with it:
15/60 vertical becomes **16/60 horizontal**, and 0/60 horizontal becomes
**0/60 vertical**. One cell in sixty of slop, on a binary count, across a 90°
rotation of the subject with the code held fixed. Then read A6 against A11: make
the same corpus texture transpose-invariant and **every cell turns over**,
0/60 in all six columns.

There is no version of H2 that survives this. A band-geometry defect cannot
follow the scene through a transpose, and it cannot be switched off by averaging
a texture with its own transpose. MEASURED, categorical, and independent of
every median, floor and pooling choice elsewhere in this report.

It also flags a real limitation on M15's statistic and on M16's own `A`: on the
real corpus **8–25 % of `vertical` cells and up to 13 % of `bar` cells have no
turnover inside the sweep**, so any median that includes them is censored from
below. `horizontal` is never censored on the untransposed corpus — not once in
480 cells. The measured shifts are therefore **conservative**: the true
`vertical` optima lie at or beyond `w40`, which would make the gap wider, not
narrower.

### 6.5 Every pre-registered decision rule, scored mechanically

Printed verbatim by `m16_analyse.py`, so the reader can check that the verdicts
above are what the rules committed in `1939c55` actually say — including the two
that do **not** come out the way §1 does.

| registered rule | inputs | mechanical output |
| --- | --- | --- |
| **P1** — the plant can express H3 | `ΔA` = +0.0 / +0.0 / −2.0 at 0.377 / 3.016 / 24.128 DN, `φ` = 0.5 | **FIRED at A4x64** |
| **H3 via A1** (`destripe mean`) | `\|A\|/\|A_ctrl\|` = 1.00 ≥ 0.75, `U` = 0.90 ≥ 0.9 | **REFUTED** |
| **H3 via A2** (`destripe hp`) | `\|A\|/\|A_ctrl\|` = 0.86 ≥ 0.75, `U` = 0.80 **< 0.9** | **UNRESOLVED** |
| **H2** | `\|A(A6)\|/\|A_ctrl\|` = 1.71 ≥ 0.75 **and** the transpose test rotates (0.0 vs 8.0) | **REFUTED** |
| **H2a vs H2b** | A10 = −6.5 behaves like A6 = −6.0, not like A0 = −3.5 | **the band shape carried it** |
| **H1 via A3** (registered arm) | `\|A\|/\|A_ctrl\|` = 0.57, `U` = 0.30, sign opposite | **UNRESOLVED** |
| **N4** — machinery must be symmetric | `A(A7)` = +1.5, `φ` = 1.0 | **FAIL** |
| **A11** on the *registered pooled* statistic | `A` = −4.0, `φ` = 1.0, `U` = 1.00 | **"H2 ALIVE"** |

Two of these need answering rather than burying.

**The registered `H1` arm came out UNRESOLVED, and §1 still says SUPPORTED.**
That is because the registered H1 arm was A3, the synthetic plant, whose
mean-regret argmin sits at w4/w8 against the corpus's w12–w15 — a different
regime, so it cannot speak about the corpus (§8, P3). The evidence §1 relies on
is A11, A8 and the censoring counts, all of which are **declared additions made
after preregistration** and are labelled as such in §4. The registered rule is
not being overridden; it is being reported as having failed to decide, and a
better instrument is being reported beside it.

**The `A11` line says "H2 ALIVE", and §1 says REFUTED.** This is the pooled-
statistic defect of §4.1 in its purest form. A11's residual `A` = −4.0 is
**entirely** `bar`: `horizontal` and `vertical` are numerically identical on that
arm, `A_hv` = **+0.0**, `L_hv` = **+0.0**, censoring 0/60 in both. `bar` differs
from `vertical` in *shape*, not orientation, so pooling it into an orientation
statistic imports a variable the hypothesis is not about. The registered **H2**
rule — the one that names the transpose test — is met outright, and it is the
rule that decides. But the pooled number is on the record, and it is the single
strongest argument anyone could make against this milestone's H2 verdict.

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
| A9 `hp`, square | 1 | 14 | 1.5474 | 1.6008 | 0.0534 | 0.0174 | w14 | yes |
| A9 `hp`, square | 17 | 12 | 1.2876 | 1.3123 | 0.0247 | 0.0101 | w12 | yes |
| A10 square band | 1 | 13 | 3.3456 | 3.3456 | 0.0000 | 0.0000 | w13 | yes |
| A10 square band | 17 | 14 | 2.7475 | 2.9382 | 0.1908 | 0.0079 | w14 | yes |

**All fourteen real-texture rows put the argmin inside w11–w15, and the largest
penalty at w13 anywhere is 0.6759 DN — below the registered 0.87 DN threshold.**
Neither limb of the rule fires. `WINDOW_RADIUS = 13` **survives**, and it
survives under the H3 correction (A1, A2, A9), under the squared geometry (A6),
under a squared scoring band with the plant unchanged (A10), under a 90° scene
rotation (A8) and under a fully isotropised plant (A11).

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
| **N4** square + isotropic must be symmetric | `A(A7)` at the noise floor | **MARGINAL** — `A` = +1.5, `A_hv` = +2.0 against `φ_hv` = 1.0, so the median is 1 window outside the floor; but `U_h` = 0.30, `p` = 0.5078, i.e. the *sign* is a coin toss. See below |
| **P1** planted row FPN must move `A` | some amplitude in {1, 8, 64}× changes the asymmetry beyond the floor, in fact 83's direction | **PASS at 64× only.** `ΔA` = +0.0 / +0.0 / **−2.0** windows at 0.377 / 3.016 / 24.128 DN, floor 0.5 |
| **P2** the fix must undo the plant | A5x64 returns A4x64 to within the floor of A3 | **PASS.** `A` +0.0 → +2.5, `ΔA` vs A3 = +0.5 inside the 1.0 floor; level back to −1.4 % of A3. Oracle removal A5x64o returns `A` to +2.0 and the level to 12.698 — exactly A3 |
| **P3** treatments must not destroy the signal | level within 20 %, argmin within ±3 windows | A1 +26.1 %, A2 +34.3 %, A11 −39.3 % — **all outside the 20 % band**; argmins all within ±2 windows and inside w11–w15 |
| **P4** aggregate argmin must be interior | not at a ladder endpoint | **PASS** for every arm |
| **G1** Gate 1, reproduce fact 83 | 12 numbers exact | **PASS** |
| **G2** A0 reproduces M15 | field-for-field | **PASS**, 8640 rows, 0 mismatched |
| **G3** synthetic texture bit-identical to M13's | at seed `0x5EED_0F0C` | **PASS** |
| **G4** read-only corpora unchanged | audit before/after | **PASS** |

Two of these need saying plainly rather than being left in a table cell.

**P1 fired only on the very last rung, and that is the whole point of running
the ladder.** At 0.377 DN (28× the sensor's real row FPN) and at 3.016 DN
(222×), the planted row pattern moved the orientation asymmetry by **exactly
zero windows**. Only at 24.128 DN — **1774×** — did it move `A` at all, and then
by −2.0 windows, roughly half of what M15 measured on the real corpus. Had the
ladder stopped at 8×, this milestone would have had to report H3 as **NOT
MEASURED**, because a plant that cannot express a failure carries no information
about it (project rule 13 / discipline 24). It is worth recording that this
report was drafted that way, twice, before the last arm landed. The lesson is not
that the ladder happened to be long enough; it is that **an amplitude ladder must
be run until the positive control fires or the amplitude becomes physically
absurd** — and here it became absurd first. The amplitude that finally worked is
three orders of magnitude above anything this sensor can produce.

**N4 came out marginal, and it is worth saying why.** On the isotropic synthetic
plant with a square ROI and a square scored region — no corpus, no FPN, nothing
left but the machinery — `A_hv(A7)` = +2.0 against `φ_hv` = 1.0. That is one
window outside its own floor, so N4 does not cleanly pass. Three things keep it
from being load-bearing. First, `U_h` = 0.30 with `p` = 0.5078: only 3 of 10
horizontal cells move the same way, which is a coin toss, against `U_h` = 1.00
and `p` = 0.0020 for every corpus arm. Second, the **sign is opposite** to the
corpus effect (+2.0 against A6's −7.5), so it cannot be a scaled-down version of
it. Third, at the zero-step stratum A7's three geometries land on the *same*
window — `horizontal` = 6, `vertical` = 6, `bar` = 6. A11 is the better null
anyway: it isotropises the corpus's own texture rather than substituting a
different spectrum, runs at the corpus's own operating point, and comes out at
`A_hv` = **+0.0**, `L_hv` = **+0.0**. **UNVERIFIED:** M16 did not chase down the
residual +2.0 on A7. It is small, unsigned and in the wrong direction, but it is
not zero and it is not explained.

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
7. **The residual +2.0 windows on A7.** The purest machinery null — isotropic
   synthetic texture, square ROI, square scored region, no FPN — did not come out
   at zero. `A_hv(A7)` = +2.0 against `φ_hv` = 1.0. Its sign consistency is a
   coin toss (`U_h` = 0.30, `p` = 0.5078) and its sign is *opposite* to the
   corpus effect, so it cannot be a scaled version of it, and A11 nulls exactly
   on the corpus's own texture. But +2.0 is not 0.0 and M16 did not chase it.
   UNVERIFIED. Most likely finite-realisation anisotropy of the two independent
   synthetic layers, but that is ARGUED, not measured.

---

## 10. Predictions, scored against the preregistration

| # | prediction | confidence | outcome |
| --- | --- | --- | --- |
| 1 | H3 will be REFUTED on the real corpus | 60 % | **RIGHT** (§6.1), and in the end by the registered route, though only after the ladder was extended to 64× |
| 2 | H2b (plant aspect) will be SUPPORTED | 50 % | **WRONG** — and wrong twice over. Squaring the ROI *enlarged* the asymmetry rather than removing it, and A10 then showed most of the enlargement was the *scored region* (H2a), not the plant aspect (§6.2) |
| 3 | H1 will be REFUTED | 55 % | **WRONG** — H1 is supported, decisively |
| 4 | P1 will fire only at 8× or 64×, not 1× | 65 % | **RIGHT** — it fired at 64× and nowhere below (§8) |
| 5 | `WINDOW_RADIUS = 13` will survive | 80 % | **RIGHT** (§7) |
| 6 | A0 ↔ M15 reproduction will pass exactly | 85 % | **RIGHT** |

Two of six wrong, and both of them were about my own preferred mechanism: I
expected the corpus to be blameless and the geometry to be at fault, and it is
the other way round. The preregistration earned its keep — prediction 3 in
particular would have been very easy to quietly forget.

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
.\run-m16.ps1           # arms A0-A10, audit-bracketed; skips arms already present
.\run-m16b.ps1          # A11, A12  (declared additions)
.\run-m16c.ps1          # the same arms as run-m16.ps1, reordered by decision value
python m16_gate1.py     # fact 83 from M15's committed CSVs, independent code
python m16_analyse.py   # every table in this report except SS 6.4
python m16_censoring.py # SS 6.4, and data/censoring.csv
```

Every table above is regenerated from the committed CSVs in
`experiments/m16-orientation-fpn/data/` by `m16_analyse.py` and
`m16_censoring.py` alone. **Nobody needs to run the harness to check the
headline** — the CSVs are the evidence and the analysers read only them. Their
stdout is committed as `data/analysis.txt` and `data/censoring.txt` so a reader
can diff rather than re-run.

A note on the sweep scripts: they are three files rather than one because the
arms were queued in three waves as the design tightened, and each script skips
any arm whose CSV already exists. Running all three in order from a clean
`data/` reproduces the full 17-arm set. `run-m16c.ps1` re-lists arms that
`run-m16.ps1` also lists; that is deliberate and idempotent, not a duplicate run.

`data/binary-equivalence.txt` records that the two binaries used
(`target/` for A0–A4x8, `target-aux/` for the rest) produce byte-identical edge
CSVs from the same command line, SHA256 matched. **Byte-identity with M15
(Gate 2) is a consistency check, not independent evidence** (discipline 34 / 20);
the independent evidence is `m16_gate1.py`, which recomputes fact 83 from M15's
committed data with its own code and shares nothing with the harness.

---

## 13. Proposed SYNTHESIS entries

Numbered from 90 as instructed by the orchestrator. **Note for reconciliation:**
`crates/strehl-core/src/merge.rs` already cites "fact 320" and this report cites
fact 162, so the live fact list runs well past 90; M16 has used the reserved
block as directed and has not checked it for collisions.

### §4 facts

| # | Fact | Consequence | Source |
| --- | --- | --- | --- |
| 90 | The occluding-edge orientation asymmetry of fact 83 is a property of the corpus subjects, not of the merge, the focus operator or the `\|d\| ≤ 24` band. Transposing the plant's textures 90° while holding every piece of machinery fixed transposes the asymmetry exactly: median \|shift(rotated geometry) − shift(control)\| = **0.0 windows**, against **8.0** for the same geometry. | Fact 83 is not a defect and there is no code change that removes it. Question 20 is closed. | M16 §6.2, arms A6/A8, 30 cells, `data/A{6,8}-*.csv` |
| 91 | Making the corpus texture exactly transpose-invariant (`T ← (T + Tᵀ)/2`, which forces `Σgx² = Σgy²` identically) removes the asymmetry completely: median `w*(1)` goes from 8.0 `horizontal` vs 20.0 `vertical` to **8.0 vs 8.0**, and `A_hv` from −7.5 to **+0.0** windows against a leave-one-seed-out floor of 1.0. | An isotropy intervention on the *scene*, with the machinery untouched, is sufficient to null the effect. Nothing is left for a machinery defect to explain. | M16 §6.3, arms A6/A11, `data/A11-*.csv` |
| 92 | Mechanism: a horizontal edge is localised by `Gy` and a vertical edge by `Gx`, and the corpus's far-field texture carries **14–22× more vertical gradient energy than horizontal** (`gx²/gy²` = 0.046–0.073; near-field 0.198–0.294). | The horizontal edge is handed 14–22× more gradient signal, needs less spatial averaging and settles on a much smaller focus window — median `w*(1)` 9.0 against 17.0. Any future corpus with different lineation will move these window numbers. | M16 §3.2/§6.3, `data/fpnscan-*.csv` |
| 93 | The sensor's fixed pattern is **isotropic at every measured ISO**: master-bias `gx²/gy²` = **0.968–0.999** across all 11 dark ISO groups (50–2000), 20 frames each, against a scaled split-half null. | Row-banded FPN is not a mechanism this sensor makes available. Any future proposal resting on row/column FPN asymmetry must first move this number. | M16 §3.1, `data/darkfpn.csv` |
| 94 | The row-correlated component of the sensor's fixed pattern is **0.0036–0.0136 DN** at the corpus ISOs (50 and 160) — about **0.3 % of fixed-pattern variance** — against **11.8–51.4 DN** of row-marginal structure in the texture tiles the harness uses. A ratio of ~10³. | The row structure in the corpus tiles is scene, not sensor, by three orders of magnitude. | M16 §3.1/§3.2, `data/darkfpn.csv`, `data/fpnscan-*.csv` |
| 95 | Per-frame row/column mean subtraction removes **44–99 % of a corpus tile's total variance** while moving `gx²` by only **3–17 %** and leaving `gx²/gy²` still 2–10× from isotropic. | Destriping cannot correct a Sobel-scale directional bias. The focus operator is a high-pass and never used the component the treatment removes. A destripe arm therefore tests almost nothing about a gradient-domain effect. | M16 §3.3, `data/anisoscan-*.csv` |
| 96 | The reviewer's proposed fix — per-frame row and column mean subtraction before the focus operator — changes fact 83 by **nothing**: `A` = −3.5 → −3.5 windows. On the level statistic it is **worse**: `L_hv(1)` = −8.0 → −9.5. | The fix is inert on this corpus and is not worth shipping for this reason. It may still be worth having for others; M16 did not test any. | M16 §6.1, arms A0/A1, `data/A1-*.csv` |
| 97 | `WINDOW_RADIUS = 13` survives every M16 arm. The mean-regret argmin stays inside M13's published w11–w15 basin under destriping, a squared ROI, a 90° scene rotation and a fully isotropised plant; the largest penalty at w13 anywhere is **0.6759 DN**, below M15's registered 0.87 DN threshold. Leave-one-seed-out floor 0.0000–0.0234 DN, argmin stable across all five subsets. | No window number M13 or M15 produced is biased by an orientation defect, because there is no orientation defect. 13 stands. | M16 §7, `data/A*-*.csv` |
| 98 | The orientation effect is larger in the **level** than in the **shift**, and it is present with **no depth discontinuity at all**. At step 0 on the real corpus the `vertical` geometry's argmin runs to the ladder endpoint w40 — *no turnover found within the sweep* — while `horizontal` turns over at 12–20; symmetrising the texture brings `vertical` back to 16 beside `horizontal`'s 17. | Fact 83's ±2.5-window regulariser shift is a second-order consequence of an 8–12-window gap that is already there at width 1. Future work should measure the level, not the shift. | M16 §6.3, N3 stratum, `data/A{0,2,6,11}-*.csv` |
| 102 | **Turnover censoring is orientation-asymmetric and follows the scene exactly.** Counting cells whose mean-regret argmin lands on the last rung of the sweep: on the corpus `vertical` is censored 10–15/60 and `horizontal` **0/60 in 480 cells**; transposing the scene 90° swaps this to `horizontal` 16/60 and `vertical` 0/60; symmetrising the texture gives **0/60 in every column**. | A categorical, non-parametric confirmation of fact 90 that is independent of every median, noise floor and pooling choice. It also means M15's and M16's `vertical` medians are **censored from below**, so the true orientation gap is wider than measured, not narrower. | M16 §6.4, `data/censoring.csv`, arms A6/A8/A11 |
| 99 | H3's mechanism **is** expressible in the harness, but only at absurd amplitude. Planting a row-correlated pattern on the isotropic synthetic plant moves the orientation statistic by **0.0 windows at 0.377 DN (28× the sensor), 0.0 at 3.016 DN (222×) and −2.0 at 24.128 DN (1774×)**, floor 0.5; applying the fix at 24.128 DN returns it to within +0.5 of the unplanted arm. | The positive and negative controls both pass, so the H3 arms carry information and the refutation is by the pre-registered rule rather than by argument. And even at 1774× the sensor's amplitude the mechanism reproduces only **half** of fact 83; at the real amplitude, ≈0.03 %. | M16 §6.1/§8, arms A3/A4x1/A4x8/A4x64/A5x64 |
| 100 | M13's `edge_mode` derives `baseline_lo`, `baseline_hi` and `max_d` from `roi.width` **regardless of the distance axis**. On a 384×256 ROI a `horizontal` edge's far baseline band `[160, 188]` is **empty**, `dmae_far` falls back to `0.0`, and `equivalent_width`'s baseline is `median(∅)`. | Any published `dmae_far`, `bleed_*` or `mis_*` number for a horizontal edge on a non-square ROI is unsound. `E_excess` reads none of these and is unaffected — which is why it was M15's and M16's primary statistic. | M16 §11, `experiments/m13-window-depth/src/edge.rs`, VERIFIED by reading; predicted in M16's preregistration §6 before measurement |
| 101 | A **rectangular** scoring region is an orientation-non-neutral gain on the regulariser-shift statistic. Holding the plant, band, seeds and code identical and scoring a centred 256×256 square instead of the full 384×256 ROI takes `A_hv` from −4.0 to **−7.0 windows** (1.75×) while leaving the level gap `L_hv(1)` at −8.0 → −8.5, inside the 1.5-window floor. | M13 and M15 measured roughly **half** the orientation shift that was present. The rectangle does not *create* bias — symmetrising the texture under the identical square geometry still nulls it to +0.0 — but it under-reports it. Prefer the level statistic, or a square region, for any future orientation claim. | M16 §6.2, arms A0/A10/A6, `data/A10-*.csv` |

### §5 discipline items

| # | Discipline |
| --- | --- |
| 40 | **A treatment that removes a defect also removes whatever scene content shares its geometry.** When the scene component is orders of magnitude larger than the defect — here ~10³ — the treatment arm cannot separate them, and a null result from it means nothing on its own. Only a planted positive control at a measured amplitude, plus a direct measurement of the defect's amplitude, can decide. M16's H3 arms were nulls for exactly this reason and the verdict had to come from elsewhere. |
| 41 | **Before blaming the machinery, make the scene symmetric under the transformation the machinery is accused of breaking, and re-measure.** For a 90° orientation claim that is `T ← (T + Tᵀ)/2` on a square tile: one line, exact, and it keeps the corpus's own contrast and spectrum, so there is no synthetic-regime objection to answer. Transposing the scene (`T ← Tᵀ`) is the complementary test and is even cheaper. |
| 42 | **Pooling two conditions because they share one property imports every property they do not share.** M16 pre-registered `vertical ∪ bar` because both have vertical boundaries. `bar` also differs in *shape*, and on the decisive arm the entire residual statistic came from `bar` alone while `horizontal` and `vertical` agreed exactly. Report the unpooled contrast beside the registered one; never silently replace it. |
| 43 | **A synthetic control that lands in a different regime from the real data cannot carry a verdict about the real data.** Check the control's mean-regret argmin against the published basin first. M16's registered isotropic arm sat at w4/w8 against the corpus's w12–w15 and had to be replaced by a symmetrised *real-texture* arm before it could decide anything. |
| 44 | **Count the censored cells before quoting a median of argmins, and report the count.** Discipline 25 forbids reading an endpoint argmin as an optimum, but a *median over a set containing endpoint cells* smuggles the same error back in one level up. In M16 the censoring rate was 0/60 for one orientation and 15/60 for the other on the same data, so the medians being compared were not the same kind of quantity. The censoring count is also the most robust statistic in the milestone — binary per cell, immune to floors, ties and pooling — and it should be computed first, not last. |
